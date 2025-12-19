#!/usr/bin/env python3
"""基于 Keystone RBAC 审计日志的授权范围检查。"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from neo4j import GraphDatabase

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from Tools.CheckOutput import PolicyCheckReporter

DEFAULT_AUDIT_FILE = "/root/policy-fileparser/data/assistfile/rbac_audit_keystone.csv"
DEFAULT_TEMP_FILE = "/root/policy-fileparser/data/assistfile/rbac_audit_keystone_temp.csv"
DEFAULT_ROLEGRANT_FILE = "/root/policy-fileparser/data/assistfile/rolegrant.csv"
FALLBACK_ROLEGRANT_FILE = "/root/policy-fileparser/data/assistfile/rolegrant.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="授权范围检查（基于 RBAC 审计日志）")
    parser.add_argument(
        "--audit-file",
        action="append",
        default=[DEFAULT_AUDIT_FILE],
        help="审计 CSV 文件路径，可重复传入多个",
    )
    parser.add_argument(
        "--rolegrant-file",
        default=DEFAULT_ROLEGRANT_FILE,
        help="rolegrant.csv 路径",
    )
    parser.add_argument(
        "--temp-out",
        default=DEFAULT_TEMP_FILE,
        help="生成的临时 CSV 输出路径",
    )
    parser.add_argument("--neo4j-uri", default="bolt://localhost:7687")
    parser.add_argument("--neo4j-user", default="neo4j")
    parser.add_argument("--neo4j-password", default="Password")
    return parser.parse_args()


def connect(uri: str, user: str, password: str):
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            session.run("RETURN 1")
        return driver
    except Exception as exc:
        print(f"✗ Neo4j 连接失败: {exc}")
        return None


def normalize_api(api: str) -> str:
    api = (api or "").strip()
    if not api:
        return ""
    api = re.sub(r"\(.*\)$", "", api)
    return api.strip()


def parse_policy_key(api: str) -> Tuple[Optional[str], Optional[str]]:
    api = normalize_api(api)
    if ":" not in api:
        return None, None
    policy_type, policy_name = api.split(":", 1)
    return policy_type.strip(), policy_name.strip()


def load_rolegrant(path: str) -> Tuple[Dict[str, str], Dict[Tuple[str, str], List[str]]]:
    user_map: Dict[str, str] = {}
    role_map: Dict[Tuple[str, str], List[str]] = defaultdict(list)

    if not os.path.exists(path) and os.path.exists(FALLBACK_ROLEGRANT_FILE):
        path = FALLBACK_ROLEGRANT_FILE

    if not os.path.exists(path):
        print(f"⚠ rolegrant.csv 不存在: {path}")
        return user_map, role_map

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            user_id = (row.get("user_id") or "").strip()
            user_name = (row.get("user_name") or "").strip()
            project_id = (row.get("project_id") or "").strip()
            role_name = (row.get("role_name") or "").strip()
            if user_id and user_name:
                user_map[user_id] = user_name
            if user_name and project_id and role_name:
                key = (user_name, project_id)
                if role_name not in role_map[key]:
                    role_map[key].append(role_name)
    return user_map, role_map


def load_audit_rows(paths: Iterable[str]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for path in paths:
        if not os.path.exists(path):
            print(f"⚠ 审计日志不存在: {path}")
            continue
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows.extend(reader)
    return rows


def build_temp_rows(
    audit_rows: List[Dict[str, str]],
    user_map: Dict[str, str],
    role_map: Dict[Tuple[str, str], List[str]],
) -> List[Dict[str, str]]:
    temp_rows: List[Dict[str, str]] = []
    for row in audit_rows:
        authorized = (row.get("authorized") or "").strip().lower()
        if authorized != "yes":
            continue
        api = normalize_api(row.get("api") or "")
        if not api:
            continue
        user_id = (row.get("user_id") or "").strip()
        project_id = (row.get("project_id") or "").strip()
        user_name = user_map.get(user_id, "")

        role_names = role_map.get((user_name, project_id), [])
        if not role_names:
            temp_rows.append(
                {
                    "api": api,
                    "user_name": user_name,
                    "project_id": project_id,
                    "role_name": "",
                }
            )
            continue

        for role in role_names:
            temp_rows.append(
                {
                    "api": api,
                    "user_name": user_name,
                    "project_id": project_id,
                    "role_name": role,
                }
            )
    return temp_rows


def write_temp_file(path: str, rows: List[Dict[str, str]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["api", "user_name", "project_id", "role_name"]
        )
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: List[Dict[str, str]]) -> Counter:
    counter: Counter = Counter()
    for row in rows:
        key = (
            row.get("api", ""),
            row.get("user_name", ""),
            row.get("role_name", ""),
            row.get("project_id", ""),
        )
        counter[key] += 1
    return counter


def print_summary(counter: Counter) -> None:
    for (api, user, role, project), count in counter.items():
        print(f"{api} | {user} | {role} | {project} | {count}")


def format_policy_rule(name: str, lines) -> str:
    if not lines:
        return name
    if isinstance(lines, list):
        return "\n".join(f"line {line}: {name}" for line in lines)
    return f"line {lines}: {name}"


def combine_rule_expressions(expressions: List[str]) -> str:
    cleaned = [expr.strip() for expr in expressions if expr and expr.strip()]
    if not cleaned:
        return "(rule expression missing)"
    if len(cleaned) == 1:
        return cleaned[0]
    return " OR ".join(cleaned)


def check_unused_rules(driver, summary: Counter, reporter: PolicyCheckReporter) -> int:
    total = 0
    policy_map: Dict[Tuple[str, str], set] = defaultdict(set)

    for (api, _user, role, project), _count in summary.items():
        policy_type, policy_name = parse_policy_key(api)
        if not policy_type or not policy_name:
            continue
        policy_map[(policy_type, policy_name)].add((role, project))

    with driver.session() as session:
        for (policy_type, policy_name), pairs in policy_map.items():
            all_rules = session.run(
                """
                MATCH (p:PolicyNode {type: $type, name: $name})-[:HAS_RULE]->(r:RuleNode)
                RETURN DISTINCT r.id AS id, r.expression AS expr, p.policyline AS lines, p.name AS pname
                """,
                type=policy_type,
                name=policy_name,
            )
            all_rules_list = list(all_rules)
            matched_ids = set()

            for role_name, project_id in pairs:
                if not role_name or not project_id:
                    continue
                result = session.run(
                    """
                    MATCH (p:PolicyNode {type: $type, name: $name})-[:HAS_RULE]->(r:RuleNode)
                    MATCH (r)-[:REQUIRES_ROLE]->(role:ConditionNode {type: 'role', name: $role})
                    MATCH (r)-[:REQUIRES_PROJECT_ID]->(proj:ConditionNode {type: 'project_id', name: $project})
                    RETURN DISTINCT r.id AS id
                    """,
                    type=policy_type,
                    name=policy_name,
                    role=role_name,
                    project=project_id,
                )
                matched_ids.update(record["id"] for record in result)

            for record in all_rules_list:
                if record["id"] in matched_ids:
                    continue
                policy_display = f"{policy_type}:{policy_name}"
                reporter.report(
                    "10",
                    policy_name=format_policy_rule(policy_display, record["lines"]),
                    api=policy_display,
                    rule=(record["expr"] or "").strip() or "(rule expression missing)",
                )
                total += 1

    return total


def check_untracked_policies(driver, summary: Counter, reporter: PolicyCheckReporter) -> int:
    total = 0
    policy_keys = set()
    for (api, _user, _role, _project), _count in summary.items():
        policy_type, policy_name = parse_policy_key(api)
        if policy_type and policy_name:
            policy_keys.add((policy_type, policy_name))

    with driver.session() as session:
        result = session.run(
            """
            MATCH (p:PolicyNode)-[:HAS_RULE]->(r:RuleNode)
            RETURN p.type AS type, p.name AS name, p.policyline AS lines,
                   collect(DISTINCT r.expression) AS exprs
            """
        )
        for record in result:
            key = (record["type"], record["name"])
            if key in policy_keys:
                continue
            policy_display = f"{record['type']}:{record['name']}"
            rule_expr = combine_rule_expressions(record["exprs"] or [])
            reporter.report(
                "11",
                policy_name=format_policy_rule(policy_display, record["lines"]),
                api=policy_display,
                policy=f"{policy_display}: {rule_expr}",
            )
            total += 1
    return total


def main() -> None:
    args = parse_args()
    user_map, role_map = load_rolegrant(args.rolegrant_file)
    audit_rows = load_audit_rows(args.audit_file)
    temp_rows = build_temp_rows(audit_rows, user_map, role_map)
    write_temp_file(args.temp_out, temp_rows)

    summary = summarize(temp_rows)
    print_summary(summary)

    driver = connect(args.neo4j_uri, args.neo4j_user, args.neo4j_password)
    if not driver:
        return
    reporter = PolicyCheckReporter()
    check_unused_rules(driver, summary, reporter)
    check_untracked_policies(driver, summary, reporter)


if __name__ == "__main__":
    main()
