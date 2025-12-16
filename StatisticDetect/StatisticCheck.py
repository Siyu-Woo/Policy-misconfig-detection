#!/usr/bin/env python3
"""策略图谱统计检测工具"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

from neo4j import GraphDatabase

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# 默认使用容器内挂载的敏感权限 CSV 路径，与 Tools/SensiPermiSet.py 保持一致。
# 如果在宿主机或其他路径执行，可通过 --perm-file 手动指定。
PERM_FILE = Path("/root/policy-fileparser/data/assistfile/sensitive_permissions.csv")

from Tools.CheckOutput import PolicyCheckReporter


def parse_multi_values(raw: str) -> List[str]:
    if not raw:
        return []
    tokens = []
    for part in raw.replace("|", ",").split(","):
        part = part.strip()
        if part:
            tokens.append(part)
    return tokens


def wrap_rule_expressions(expressions: List[str]) -> str:
    """将 rule 列表组合成 `(expr1) OR (expr2)` 的形式。"""
    cleaned = [expr.strip() for expr in expressions if expr and expr.strip()]
    if not cleaned:
        return "(policy rule missing)"
    if len(cleaned) == 1:
        return f"({cleaned[0]})"
    return "(" + ") OR (".join(cleaned) + ")"


def extract_policy_name(entry: Dict[str, str]) -> str:
    """从 CSV 记录中提取策略名称字段。"""
    for key in ("policy_name", "api_name", "API名称"):
        value = entry.get(key)
        if value:
            return value.strip()
    return ""


def short_policy_name(policy: str) -> str:
    """将 identity:xxx 形式转换为策略节点的 name（去掉前缀）。"""
    if not policy:
        return ""
    policy = policy.strip()
    if ":" in policy:
        return policy.split(":", 1)[1].strip()
    return policy


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Neo4j 策略统计检测")
    parser.add_argument("--neo4j-uri", default="bolt://localhost:7687")
    parser.add_argument("--neo4j-user", default="neo4j")
    parser.add_argument("--neo4j-password", default="Password")
    parser.add_argument("--perm-file", default=str(PERM_FILE))
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


def format_policy_rule(name: str, lines: Any) -> str:
    if not lines:
        return name
    if isinstance(lines, list):
        return "\n".join(f"line {line}: {name}" for line in lines)
    return f"line {lines}: {name}"


def load_sensitive_entries(path: str) -> List[Dict[str, str]]:
    if not os.path.exists(path):
        print(f"⚠ 高级别权限文件不存在: {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def check_wildcard_roles(session, reporter: PolicyCheckReporter) -> int:
    total = 0
    result = session.run(
        """
        MATCH (p:PolicyNode)-[:HAS_RULE]->(:RuleNode)-[:REQUIRES_ROLE]->(c:ConditionNode)
        WHERE toLower(c.type)='role' AND toLower(c.name)='*'
        RETURN DISTINCT p.name AS name, p.policyline AS lines, c.name AS cond
        """
    )
    for record in result:
        reporter.report(
            "4",
            policy_name=format_policy_rule(record["name"], record["lines"]),
            fault_info=f"role: {record['cond']}"
        )
        total += 1
    return total


def check_empty_rules(session, reporter: PolicyCheckReporter) -> int:
    total = 0
    result = session.run(
        """
        MATCH (p:PolicyNode)-[:HAS_RULE]->(r:RuleNode)
        WHERE NOT (r)-[:REQUIRES_ROLE|REQUIRES_SYSTEM_SCOPE|REQUIRES_PROJECT_ID|REQUIRES_USER_ID|REQUIRES_DOMAIN_ID|REQUIRES_TOKEN_DOMAIN_ID]->()
        RETURN DISTINCT p.name AS name, p.policyline AS lines
        """
    )
    for record in result:
        reporter.report(
            "5",
            policy_name=format_policy_rule(record["name"], record["lines"])
        )
        total += 1
    return total


def check_sensitive_scopes(session, reporter: PolicyCheckReporter, entries: List[Dict[str, str]]) -> int:
    """错误码 6：敏感策略缺少 system_scope 限制。"""
    targets = set()
    for entry in entries:
        policy_raw = extract_policy_name(entry)
        scope_values = parse_multi_values(entry.get("system_scope") or entry.get("SystemScope"))
        if not policy_raw or not scope_values:
            continue
        short_name = short_policy_name(policy_raw)
        if short_name:
            targets.add(short_name)

    total = 0
    for name in sorted(targets):
        result = session.run(
            """
            MATCH (p:PolicyNode {name: $name})-[:HAS_RULE]->(r:RuleNode)
            WITH p, collect(DISTINCT r.expression) AS exprs
            OPTIONAL MATCH (p)-[:HAS_RULE]->(:RuleNode)-[:REQUIRES_SYSTEM_SCOPE]->(c:ConditionNode)
            WITH p, exprs, count(c) AS scope_cnt
            WHERE scope_cnt = 0
            RETURN DISTINCT p.name AS name, p.policyline AS lines, exprs
            """,
            name=name,
        )
        for record in result:
            reporter.report(
                "6",
                policy_name=format_policy_rule(record["name"], record["lines"]),
                original_expr=wrap_rule_expressions(record["exprs"] or []),
            )
            total += 1
    return total


def check_sensitive_projects(session, reporter: PolicyCheckReporter, entries: List[Dict[str, str]]) -> int:
    """错误码 7：敏感策略缺少 project 限制或过宽。"""
    policy_map: Dict[str, Dict[str, Any]] = {}
    for entry in entries:
        policy_raw = extract_policy_name(entry)
        project_values = parse_multi_values(entry.get("project_name") or entry.get("ProjectName"))
        if not policy_raw or not project_values:
            continue
        short_name = short_policy_name(policy_raw)
        if not short_name:
            continue
        info = policy_map.setdefault(
            short_name,
            {"raw": policy_raw, "allowed": set(), "display": []},
        )
        for value in project_values:
            lower = value.lower()
            info["allowed"].add(lower)
            if value not in info["display"]:
                info["display"].append(value)

    total = 0
    for name, info in policy_map.items():
        allowed = [item for item in info["allowed"] if item]
        if not allowed:
            continue
        result = session.run(
            """
            MATCH (p:PolicyNode {name: $name})-[:HAS_RULE]->(r:RuleNode)
            WITH p, collect(DISTINCT r.expression) AS exprs
            OPTIONAL MATCH (p)-[:HAS_RULE]->(:RuleNode)-[:REQUIRES_PROJECT_ID]->(c:ConditionNode)
            WITH p, exprs, [proj IN collect(DISTINCT toLower(c.name)) WHERE proj IS NOT NULL] AS projects
            WHERE size(projects)=0 OR ANY(proj IN projects WHERE NOT proj IN $allowed)
            RETURN DISTINCT p.name AS name, p.policyline AS lines, exprs
            """,
            name=name,
            allowed=allowed,
        )
        project_placeholder = info["display"][0] if info["display"] else "%(project_id)s"
        for record in result:
            reporter.report(
                "7",
                policy_name=format_policy_rule(record["name"], record["lines"]),
                project_placeholder=project_placeholder,
                original_expr=wrap_rule_expressions(record["exprs"] or []),
            )
            total += 1
    return total


def check_sensitive_roles(session, reporter: PolicyCheckReporter, entries: List[Dict[str, str]]) -> int:
    """错误码 8：敏感策略被普通角色使用。"""
    policy_map: Dict[str, Dict[str, Any]] = {}
    for entry in entries:
        policy_raw = extract_policy_name(entry)
        role_values = parse_multi_values(entry.get("role") or entry.get("Role"))
        if not policy_raw or not role_values:
            continue
        short_name = short_policy_name(policy_raw)
        if not short_name:
            continue
        info = policy_map.setdefault(
            short_name,
            {"raw": policy_raw, "allowed": set(), "display": []},
        )
        for value in role_values:
            lower = value.lower()
            info["allowed"].add(lower)
            if value not in info["display"]:
                info["display"].append(value)

    total = 0
    for name, info in policy_map.items():
        allowed = [item for item in info["allowed"] if item]
        if not allowed:
            continue
        result = session.run(
            """
            MATCH (p:PolicyNode {name: $name})
            OPTIONAL MATCH (p)-[:HAS_RULE]->(:RuleNode)-[:REQUIRES_ROLE]->(c:ConditionNode)
            WITH p, [role IN collect(DISTINCT toLower(c.name)) WHERE role IS NOT NULL] AS roles
            WHERE size(roles)=0 OR ANY(role IN roles WHERE NOT role IN $allowed)
            RETURN DISTINCT p.name AS name, p.policyline AS lines
            """,
            name=name,
            allowed=allowed,
        )
        allowed_display = ", ".join(info["display"])
        info_msg = f"Policy {info['raw']} should limit roles to [{allowed_display}]"
        for record in result:
            reporter.report(
                "8",
                policy_name=format_policy_rule(record["name"], record["lines"]),
                api=info["raw"],
                fault_info=info_msg,
            )
            total += 1
    return total


def main() -> None:
    args = parse_args()
    driver = connect(args.neo4j_uri, args.neo4j_user, args.neo4j_password)
    if not driver:
        return
    reporter = PolicyCheckReporter()
    entries = load_sensitive_entries(args.perm_file)
    with driver.session() as session:
        count = session.run("MATCH (p:PolicyNode) RETURN count(p) as c").single()["c"]
        if count == 0:
            print("Neo4j 中暂无策略节点。")
            return
        total = 0
        total += check_wildcard_roles(session, reporter)
        total += check_empty_rules(session, reporter)
        total += check_sensitive_scopes(session, reporter, entries)
        total += check_sensitive_projects(session, reporter, entries)
        total += check_sensitive_roles(session, reporter, entries)
        if total == 0:
            print("✓ 检测完成，未发现潜在问题。")
        else:
            print(f"✓ 检测完成，共发现 {total} 条潜在风险。")


if __name__ == "__main__":
    main()
