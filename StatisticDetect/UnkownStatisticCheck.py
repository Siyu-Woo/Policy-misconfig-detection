#!/usr/bin/env python3
"""策略图谱高低权限错配统计检测工具"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Set

from neo4j import GraphDatabase

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from Tools.CheckOutput import PolicyCheckReporter

DEFAULT_PROJECTINFO = Path("/root/policy-fileparser/data/assistfile/projectinfo.csv")
DEFAULT_OUTPUT_DIR = Path("/root/policy-fileparser/data/assistfile")
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
    mapping = {}
    if not path.exists():
        print(f"⚠ projectinfo.csv 不存在: {path}")
        return mapping
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            proj_id = row.get("project_id")
            name = row.get("project_name")
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


def save_role_levels(path: Path, data: Dict[str, List[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)


def format_policy_rule(policy: str, lines: Any) -> str:
    if not lines:
        return policy
    if isinstance(lines, list):
        return "\n".join(f"line {line}: {policy}" for line in lines)
    return f"line {lines}: {policy}"


def parse_roles(raw: str) -> List[str]:
    if not raw:
        return []
    roles = []
    for part in raw.replace("|", ",").split(","):
        part = part.strip()
        if part:
            roles.append(part)
    return roles


def handle_roles_command(args) -> None:
    config_path = Path(args.role_config)
    levels = load_role_levels(config_path)

    if args.list:
        print(json.dumps(levels, ensure_ascii=False, indent=2))
        return

    level_key = "high_authorized" if args.level == "high" else "low_authorized"
    current = set(levels.get(level_key, []))

    if args.add:
        current.update(parse_roles(args.add))
    if args.remove:
        current.difference_update(parse_roles(args.remove))
    if args.set_roles is not None:
        current = set(parse_roles(args.set_roles))
    if args.clear:
        current = set()

    levels[level_key] = sorted(current)
    save_role_levels(config_path, levels)
    print(json.dumps(levels, ensure_ascii=False, indent=2))


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
                    "high_roles": set(),
                    "low_roles": set(),
                },
            )
            entry["roles"] = entry.get("roles", set())
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


def write_csv(rows: List[Dict[str, Any]], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    path = output_dir / f"RoleStatistic{ts}.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "api",
                "project_name",
                "high_authorized_num",
                "high_authorized_percent",
                "low_authorized_num",
                "low_authorized_percent",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row["api"],
                    row["project_name"],
                    row["high_num"],
                    f"{row['high_pct']:.2f}",
                    row["low_num"],
                    f"{row['low_pct']:.2f}",
                ]
            )
    return path


def run_check(args) -> None:
    driver = connect(args.neo4j_uri, args.neo4j_user, args.neo4j_password)
    if not driver:
        sys.exit(1)

    role_levels = load_role_levels(Path(args.role_config))
    high_set = set(role_levels.get("high_authorized", []))
    low_set = set(role_levels.get("low_authorized", []))

    project_map = load_project_map(Path(args.project_map))

    reporter = PolicyCheckReporter()
    try:
        with driver.session() as session:
            payload = collect_policy_stats(session, project_map)
            stats = payload["stats"]
            line_map = payload["lines"]
    finally:
        driver.close()

    rows = compute_counts(stats, high_set, low_set)
    output_path = write_csv(rows, Path(args.output_dir))
    print(f"已生成: {output_path}")

    for row in rows:
        api = row["api"]
        project_name = row["project_name"]
        high_pct = row["high_pct"]
        low_pct = row["low_pct"]
        high_num = row["high_num"]
        low_num = row["low_num"]

        if 80 <= low_pct < 100 and high_num > 0:
            reporter.report(
                "12",
                policy_name=format_policy_rule(api, line_map.get(api)),
                api=api,
                roles=",".join(row["high_roles"]),
                low_roles=",".join(row["low_roles"]),
                project_name=project_name,
            )
        if 80 <= high_pct < 100 and low_num > 0:
            reporter.report(
                "13",
                policy_name=format_policy_rule(api, line_map.get(api)),
                api=api,
                roles=",".join(row["low_roles"]),
                project_name=project_name,
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="高低权限错配统计检测")
    subparsers = parser.add_subparsers(dest="command")

    check_parser = subparsers.add_parser("check", help="执行统计检测")
    check_parser.add_argument("--neo4j-uri", default="bolt://localhost:7687")
    check_parser.add_argument("--neo4j-user", default="neo4j")
    check_parser.add_argument("--neo4j-password", default="Password")
    check_parser.add_argument("--project-map", default=str(DEFAULT_PROJECTINFO))
    check_parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    check_parser.add_argument("--role-config", default=str(DEFAULT_ROLE_CONFIG))
    check_parser.set_defaults(func=run_check)

    role_parser = subparsers.add_parser("roles", help="管理高低权限角色集合")
    role_parser.add_argument("--role-config", default=str(DEFAULT_ROLE_CONFIG))
    role_parser.add_argument("--level", choices=["high", "low"], required=True)
    action = role_parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--list", action="store_true", help="查看角色配置")
    action.add_argument("--add", help="新增角色，逗号分隔")
    action.add_argument("--remove", help="删除角色，逗号分隔")
    action.add_argument("--set-roles", help="覆盖设置角色，逗号分隔")
    action.add_argument("--clear", action="store_true", help="清空角色列表")
    role_parser.set_defaults(func=handle_roles_command)

    args = parser.parse_args()
    if not args.command:
        args = parser.parse_args(["check"])
    return args


def main() -> None:
    args = parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
