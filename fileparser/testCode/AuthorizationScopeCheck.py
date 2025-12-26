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


DEFAULT_AUDIT_FILE = "/root/policy-fileparser/data/assistfile/rbac_audit_keystone.csv"
DEFAULT_TEMP_FILE = "/root/policy-fileparser/data/assistfile/rbac_audit_keystone_temp.csv"
DEFAULT_ROLEGRANT_FILE = "/root/policy-fileparser/data/assistfile/rolegrant.csv"
DEFAULT_PROJECTINFO_FILE = (
    "/root/policy-fileparser/data/assistfile/EnvInfo/projectinfo.csv"
)
FALLBACK_ROLEGRANT_FILE = "/root/policy-fileparser/data/assistfile/rolegrant.csv"
FALLBACK_PROJECTINFO_FILE = "/root/policy-fileparser/data/assistfile/projectinfo.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="授权范围检查（基于 RBAC 审计日志）")
    parser.add_argument(
        "--policy",
        nargs="+",
        default=[],
        help="策略文件或目录路径（保持与 run_graph_pipeline 用法一致）",
    )
    parser.add_argument(
        "--parsed-logs",
        nargs="+",
        default=[DEFAULT_AUDIT_FILE],
        help="解析后的 RBAC CSV 路径",
    )
    parser.add_argument(
        "--rolegrant-file",
        default=DEFAULT_ROLEGRANT_FILE,
        help="rolegrant.csv 路径",
    )
    parser.add_argument(
        "--projectinfo-file",
        default=DEFAULT_PROJECTINFO_FILE,
        help="projectinfo.csv 路径",
    )
    parser.add_argument(
        "--temp-out",
        default=DEFAULT_TEMP_FILE,
        help="生成的临时 CSV 输出路径",
    )
    parser.add_argument("--neo4j-uri", default="bolt://localhost:7687")
    parser.add_argument("--neo4j-user", default="neo4j")
    parser.add_argument("--neo4j-password", default="Password")
    parser.add_argument("--output", default="console", choices=["console"])
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


def load_project_map(path: str) -> Dict[str, str]:
    project_map: Dict[str, str] = {}
    if not os.path.exists(path) and os.path.exists(FALLBACK_PROJECTINFO_FILE):
        path = FALLBACK_PROJECTINFO_FILE
    if not os.path.exists(path):
        print(f"⚠ projectinfo.csv 不存在: {path}")
        return project_map
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            project_id = (row.get("project_id") or "").strip()
            project_name = (row.get("project_name") or "").strip()
            if project_id and project_name:
                project_map[project_id] = project_name
    return project_map


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


def format_policy_rule(name: str, lines) -> str:
    if not lines:
        return name
    if isinstance(lines, list):
        joined = ",".join(str(line) for line in lines)
        return f"【{joined}】 {name}"
    return f"【{lines}】 {name}"


def _normalize_rule_roles(roles: List[str]) -> List[str]:
    cleaned = [r.strip() for r in roles if r and r.strip()]
    return cleaned


def _normalize_rule_projects(projects: List[str]) -> List[str]:
    cleaned = [p.strip() for p in projects if p and p.strip()]
    return cleaned


def _has_project_wildcard(projects: List[str]) -> bool:
    for proj in projects:
        if proj == "*" or "%(" in proj:
            return True
    return False


def _has_role_wildcard(roles: List[str]) -> bool:
    return any(r == "*" for r in roles)


def _unique_preserve(items: List[str]) -> List[str]:
    seen = set()
    output = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output


def check_unused_rules(driver, summary: Counter, project_map: Dict[str, str]) -> int:
    total = 0
    policy_map: Dict[Tuple[str, str], set] = defaultdict(set)

    for (api, _user, role, project), _count in summary.items():
        policy_type, policy_name = parse_policy_key(api)
        if not policy_type or not policy_name:
            continue
        policy_map[(policy_type, policy_name)].add((role, project))

    with driver.session() as session:
        for (policy_type, policy_name), pairs in policy_map.items():
            policy_display = f"{policy_type}:{policy_name}"
            all_rules = session.run(
                """
                MATCH (p:PolicyNode {type: $type, name: $name})-[:HAS_RULE]->(r:RuleNode)
                RETURN DISTINCT r.id AS id, r.expression AS expr, p.policyline AS lines
                """,
                type=policy_type,
                name=policy_name,
            )
            all_rules_list = list(all_rules)
            matched_ids = set()

            for role_name, project_id in pairs:
                if not role_name or not project_id:
                    continue
                if role_name.lower() == "admin":
                    continue
                result = session.run(
                    """
                    MATCH (p:PolicyNode {type: $type, name: $name})-[:HAS_RULE]->(r:RuleNode)
                    MATCH (r)-[rel_role]->(role:ConditionNode {type: 'role', name: $role})
                    WHERE type(rel_role) STARTS WITH 'REQUIRES_ROLE'
                    MATCH (r)-[rel_proj]->(proj:ConditionNode {type: 'project', name: $project})
                    WHERE type(rel_proj) STARTS WITH 'REQUIRES_PROJECT'
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
                # 获取该规则的角色/项目条件
                rule_detail = session.run(
                    """
                    MATCH (r:RuleNode {id: $rid})
                    OPTIONAL MATCH (r)-[rel_role]->(role:ConditionNode {type: 'role'})
                    WHERE type(rel_role) STARTS WITH 'REQUIRES_ROLE'
                    OPTIONAL MATCH (r)-[rel_proj]->(proj:ConditionNode {type: 'project'})
                    WHERE type(rel_proj) STARTS WITH 'REQUIRES_PROJECT'
                    RETURN collect(DISTINCT role.name) AS roles,
                           collect(DISTINCT proj.name) AS projects
                    """,
                    rid=record["id"],
                ).single()
                roles = _normalize_rule_roles(rule_detail["roles"] if rule_detail else [])
                projects = _normalize_rule_projects(rule_detail["projects"] if rule_detail else [])

                if not roles or not projects:
                    # 当前检查只针对同时具备 role + project 的规则
                    continue

                role_any = _has_role_wildcard(roles)
                project_any = _has_project_wildcard(projects)

                filtered_roles = [r for r in roles if r.lower() != "admin"]
                if not filtered_roles and not role_any:
                    continue

                used_pairs = {
                    (role, proj)
                    for (api, _user, role, proj), _count in summary.items()
                    if api == policy_display and role and proj and role.lower() != "admin"
                }

                matched = False
                for role, proj in used_pairs:
                    role_ok = role_any or role in filtered_roles
                    proj_ok = project_any or proj in projects
                    if role_ok and proj_ok:
                        matched = True
                        break
                if matched:
                    continue

                project_labels = []
                for proj in projects:
                    if proj == "*" or "%(" in proj:
                        project_labels.append("any")
                    else:
                        project_labels.append(project_map.get(proj, proj))
                project_labels = _unique_preserve(project_labels)
                role_labels = _unique_preserve(filtered_roles) if filtered_roles else ["any"]

                policy_lines = record["lines"]
                print(
                    f"Risk policy rule：{format_policy_rule(policy_display, policy_lines)}"
                )
                print(
                    "Risk Info："
                    f"{policy_display} is not being used by the assigned {','.join(role_labels)}/ in the assigned {','.join(project_labels)}"
                )
                print("")
                total += 1

    return total


def main() -> None:
    args = parse_args()
    user_map, role_map = load_rolegrant(args.rolegrant_file)
    project_map = load_project_map(args.projectinfo_file)
    audit_rows = load_audit_rows(args.parsed_logs)
    temp_rows = build_temp_rows(audit_rows, user_map, role_map)
    write_temp_file(args.temp_out, temp_rows)

    summary = summarize(temp_rows)

    driver = connect(args.neo4j_uri, args.neo4j_user, args.neo4j_password)
    if not driver:
        return
    total = check_unused_rules(driver, summary, project_map)
    if total == 0:
        with driver.session() as session:
            rule_count = session.run(
                "MATCH (r:RuleNode) RETURN count(r) as c"
            ).single()["c"]
        print(f"read {rule_count} policy rules，all has proper authorization scope")


if __name__ == "__main__":
    main()
