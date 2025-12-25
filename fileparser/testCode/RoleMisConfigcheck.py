#!/usr/bin/env python3
"""低权限 API 错配给高权限角色检测（错误码12）。"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Set

from neo4j import GraphDatabase

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

DEFAULT_PROJECTINFO = Path("/root/policy-fileparser/data/assistfile/projectinfo.csv")
DEFAULT_ROLE_CONFIG = Path("/root/policy-fileparser/data/assistfile/role_level.json")

DEFAULT_ROLE_LEVELS = {
    "high_authorized": ["managerA", "managerB", "managerC", "managerD", "managerE"],
    "low_authorized": ["memberA", "memberB", "memberC", "memberD", "memberE"],
}


def connect(uri: str, user: str, password: str):
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            session.run("RETURN 1")
        return driver
    except Exception as exc:
        print(f"✗ Neo4j 连接失败: {exc}")
        return None


def load_project_map(path: Path) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    if not path.exists():
        return mapping
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            proj_id = (row.get("project_id") or "").strip()
            name = (row.get("project_name") or "").strip()
            if proj_id and name:
                mapping[proj_id] = name
    return mapping


def load_role_levels(path: Path) -> Dict[str, List[str]]:
    if path.exists():
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return {
            "high_authorized": list(data.get("high_authorized", [])),
            "low_authorized": list(data.get("low_authorized", [])),
        }
    return {
        "high_authorized": DEFAULT_ROLE_LEVELS["high_authorized"].copy(),
        "low_authorized": DEFAULT_ROLE_LEVELS["low_authorized"].copy(),
    }


def format_policy_rule(policy: str, lines: Any) -> str:
    if not lines:
        return policy
    if isinstance(lines, list):
        joined = ",".join(str(line) for line in lines)
        return f"【{joined}】 {policy}"
    return f"【{lines}】 {policy}"


def collect_policy_stats(session, project_map: Dict[str, str]) -> Dict[str, Any]:
    result = session.run(
        """
        MATCH (p:PolicyNode)-[:HAS_RULE]->(r:RuleNode)
        OPTIONAL MATCH (r)-[:REQUIRES_ROLE]->(role:ConditionNode)
        OPTIONAL MATCH (r)-[:REQUIRES_PROJECT_ID|REQUIRES_PROJECT]->(proj:ConditionNode)
        RETURN p.id AS api,
               p.policyline AS lines,
               r.id AS rule_id,
               collect(DISTINCT role.name) AS roles,
               collect(DISTINCT proj.name) AS projects
        """
    )

    stats: Dict[str, Dict[str, Any]] = {}
    line_map: Dict[str, Any] = {}

    for record in result:
        api = record["api"]
        roles = [r for r in (record["roles"] or []) if r]
        projects = [p for p in (record["projects"] or []) if p]
        if not roles:
            continue
        line_map.setdefault(api, record["lines"])

        project_ids = projects or ["default"]
        for project_id in project_ids:
            project_name = project_map.get(project_id, project_id)
            key = f"{api}@@{project_name}"
            entry = stats.setdefault(
                key,
                {
                    "api": api,
                    "project_name": project_name,
                    "roles": set(),
                },
            )
            entry["roles"].update(roles)

    return {"stats": stats, "lines": line_map}


def compute_counts(stats: Dict[str, Any], high_set: Set[str], low_set: Set[str]):
    rows = []
    for entry in stats.values():
        roles = set(entry.get("roles", set()))
        roles.discard("admin")
        high_roles = sorted(roles & high_set)
        low_roles = sorted(roles & low_set)
        total = len(high_roles) + len(low_roles)
        high_pct = (len(high_roles) / total * 100.0) if total else 0.0
        low_pct = (len(low_roles) / total * 100.0) if total else 0.0
        rows.append(
            {
                "api": entry["api"],
                "project_name": entry["project_name"],
                "high_roles": high_roles,
                "low_roles": low_roles,
                "high_num": len(high_roles),
                "low_num": len(low_roles),
                "high_pct": high_pct,
                "low_pct": low_pct,
            }
        )
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="低权限 API 错配给高权限角色检测")
    parser.add_argument("--policy", default="", help="策略文件路径")
    parser.add_argument("--neo4j-uri", default="bolt://localhost:7687")
    parser.add_argument("--neo4j-user", default="neo4j")
    parser.add_argument("--neo4j-password", default="Password")
    parser.add_argument("--project-map", default=str(DEFAULT_PROJECTINFO))
    parser.add_argument("--role-config", default=str(DEFAULT_ROLE_CONFIG))
    parser.add_argument("--output", default="console", choices=["console"])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    driver = connect(args.neo4j_uri, args.neo4j_user, args.neo4j_password)
    if not driver:
        sys.exit(1)

    role_levels = load_role_levels(Path(args.role_config))
    high_set = set(role_levels.get("high_authorized", []))
    low_set = set(role_levels.get("low_authorized", []))

    project_map = load_project_map(Path(args.project_map))

    try:
        with driver.session() as session:
            payload = collect_policy_stats(session, project_map)
            stats = payload["stats"]
            line_map = payload["lines"]
    finally:
        driver.close()

    rows = compute_counts(stats, high_set, low_set)
    api_set = {row["api"] for row in rows}

    found = 0
    for row in rows:
        if 80 <= row["low_pct"] < 100 and row["high_num"] > 0:
            api = row["api"]
            risk_roles = ",".join(row["high_roles"])
            print(f"Risk policy rule：{format_policy_rule(api, line_map.get(api))}")
            print(f"Risk Role：{api} should not assigned to {risk_roles}")
            print("")
            found += 1

    if found == 0:
        print(f"read {len(api_set)} policy rules，all APIs has proper assigned to Roles")


if __name__ == "__main__":
    main()
