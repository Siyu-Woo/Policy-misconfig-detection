import argparse
import csv
import re
import sys
from datetime import datetime
from pathlib import Path

from neo4j import GraphDatabase


DEFAULT_NEO4J_URI = "bolt://localhost:7687"
DEFAULT_NEO4J_USER = "neo4j"
DEFAULT_NEO4J_PASSWORD = "Password"
DEFAULT_PROJECTINFO = Path("/root/policy-fileparser/data/assistfile/projectinfo.csv")
DEFAULT_POLICY_DIR = Path("/etc/openstack/policies")


def _connect_neo4j(uri: str, user: str, password: str):
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            session.run("RETURN 1")
        print("✓ Neo4j 连接成功")
        return driver
    except Exception as exc:
        print(f"✗ Neo4j 连接失败: {exc}")
        raise


def _read_project_map(path: Path):
    mapping = {}
    if not path.exists():
        return mapping
    with path.open(newline="", encoding="ascii") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            name = row.get("project_name")
            proj_id = row.get("project_id")
            if name and proj_id:
                mapping[name] = proj_id
    return mapping


def _read_project_id_map(path: Path):
    mapping = {}
    if not path.exists():
        return mapping
    with path.open(newline="", encoding="ascii") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            name = row.get("project_name")
            proj_id = row.get("project_id")
            if name and proj_id:
                mapping[proj_id] = name
    return mapping


def _replace_project_names(expr: str, project_map: dict) -> str:
    if not project_map or not expr:
        return expr

    def repl(match):
        name = match.group(1)
        if name in project_map:
            return f"project:{project_map[name]}"
        return match.group(0)

    return re.sub(r"project:([A-Za-z0-9_.-]+)", repl, expr)


def _resolve_project_name(raw_name: str, project_map: dict):
    if raw_name in project_map:
        return raw_name, True
    for name, proj_id in project_map.items():
        if raw_name == proj_id:
            return name, True
    return raw_name, False


def _write_matrix_csv(path: Path, apis, roles, matrix):
    with path.open("w", newline="", encoding="ascii") as handle:
        writer = csv.writer(handle)
        writer.writerow(["api_name"] + roles)
        for api in apis:
            row = [api] + [matrix[api].get(role, 0) for role in roles]
            writer.writerow(row)


def graph_to_csv(args):
    driver = _connect_neo4j(args.neo4j_uri, args.neo4j_user, args.neo4j_password)
    project_id_map = _read_project_id_map(Path(args.project_map))
    if not project_id_map:
        print("提示: projectinfo.csv 为空或不存在，无法将 project_id 转为 project_name。")
    try:
        with driver.session() as session:
            records = list(
                session.run(
                    """
                    MATCH (p:PolicyNode)-[:HAS_RULE]->(r:RuleNode)
                    OPTIONAL MATCH (r)-[:REQUIRES_ROLE]->(role)
                    OPTIONAL MATCH (r)-[:REQUIRES_PROJECT|REQUIRES_PROJECT_ID]->(proj)
                    RETURN p.id AS api,
                           r.id AS rule_id,
                           collect(DISTINCT role.name) AS roles,
                           collect(DISTINCT proj.name) AS projects
                    """
                )
            )
    finally:
        driver.close()

    apis = set()
    roles = set()
    rules = []

    for record in records:
        api = record["api"]
        role_list = [r for r in record["roles"] if r]
        project_list = [p for p in record["projects"] if p]
        apis.add(api)
        roles.update(role_list)
        rules.append((api, role_list, project_list))

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    api_list = sorted(apis)
    role_list = sorted(roles)

    now_permit = {api: {role: 0 for role in role_list} for api in api_list}
    permit_by_project = {}

    for api, rule_roles, rule_projects in rules:
        if not rule_roles:
            continue
        if not rule_projects:
            for role in rule_roles:
                if role in now_permit[api]:
                    now_permit[api][role] = 1
            continue
        for project_id in rule_projects:
            project_name = project_id_map.get(project_id, project_id)
            if project_id not in project_id_map:
                print(f"提示: 未找到 project_id 对应名称，使用原值: {project_id}")
            if project_name not in permit_by_project:
                permit_by_project[project_name] = {
                    api: {role: 0 for role in role_list} for api in api_list
                }
            for role in rule_roles:
                if role in permit_by_project[project_name][api]:
                    permit_by_project[project_name][api][role] = 1

    now_permit_path = output_dir / "NowPermit.csv"
    _write_matrix_csv(now_permit_path, api_list, role_list, now_permit)
    print(f"已生成: {now_permit_path}")

    for project_name, matrix in permit_by_project.items():
        safe_name = str(project_name).replace("/", "_")
        path = output_dir / f"NowPermitin{safe_name}.csv"
        _write_matrix_csv(path, api_list, role_list, matrix)
        print(f"已生成: {path}")


def _read_csv_matrix(path: Path):
    with path.open(newline="", encoding="ascii") as handle:
        reader = csv.reader(handle)
        rows = list(reader)
    if not rows or len(rows[0]) < 2:
        raise ValueError(f"{path} 缺少有效表头")
    header = rows[0]
    roles = header[1:]
    api_rows = rows[1:]
    apis = [row[0] for row in api_rows if row]
    matrix = {}
    for row in api_rows:
        if not row:
            continue
        api = row[0]
        values = row[1:]
        matrix[api] = {}
        for idx, role in enumerate(roles):
            value = 0
            if idx < len(values) and values[idx].strip() == "1":
                value = 1
            matrix[api][role] = value
    return roles, apis, matrix


def _normalize_project_arg(value: str):
    if value is None:
        return None
    lowered = value.strip().lower()
    if lowered in ("", "none", "null"):
        return None
    return value.strip()


def _check_csv_alignment(paths):
    base_roles = None
    base_apis = None
    errors = []
    matrices = []
    for path in paths:
        roles, apis, matrix = _read_csv_matrix(path)
        matrices.append((roles, apis, matrix))
        if base_roles is None:
            base_roles = roles
            base_apis = apis
            continue
        if roles != base_roles:
            extra = sorted(set(roles) - set(base_roles))
            missing = sorted(set(base_roles) - set(roles))
            errors.append(
                f"{path} 角色列不一致 (缺少: {missing or '无'} / 多出: {extra or '无'})"
            )
        if apis != base_apis:
            extra = sorted(set(apis) - set(base_apis))
            missing = sorted(set(base_apis) - set(apis))
            errors.append(
                f"{path} API 行不一致 (缺少: {missing or '无'} / 多出: {extra or '无'})"
            )
    if errors:
        raise ValueError("\n".join(errors))
    return base_roles, base_apis, matrices


def csv_to_yaml(args):
    csv_paths = [Path(p) for p in args.csv_files]
    if not csv_paths:
        raise ValueError("未提供 CSV 文件")

    project_args = [_normalize_project_arg(p) for p in (args.projects or [])]
    if not project_args:
        if len(csv_paths) == 1:
            project_args = [None]
        else:
            missing = [str(p) for p in csv_paths]
            raise ValueError(f"以下文件未指定 project: {', '.join(missing)}")
    if len(project_args) != len(csv_paths):
        raise ValueError("CSV 文件数量与 project 参数数量不一致")

    none_count = sum(1 for p in project_args if p is None)
    if none_count > 1:
        raise ValueError("project 为空的文件不能超过 1 个")

    project_map = _read_project_map(Path(args.project_map))
    project_ids = []
    missing_projects = []
    for proj in project_args:
        if proj is None:
            project_ids.append(None)
            continue
        if proj not in project_map:
            missing_projects.append(proj)
        else:
            project_ids.append(project_map[proj])
    if missing_projects:
        raise ValueError(f"未在 projectinfo.csv 中找到: {', '.join(missing_projects)}")

    roles, apis, matrices = _check_csv_alignment(csv_paths)

    file_data = []
    for idx, path in enumerate(csv_paths):
        role_list, api_list, matrix = matrices[idx]
        file_data.append(
            {
                "path": path,
                "project_name": project_args[idx],
                "project_id": project_ids[idx],
                "roles": role_list,
                "apis": api_list,
                "matrix": matrix,
            }
        )

    output_path = Path(args.output)
    if output_path.is_dir():
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        output_path = output_path / f"Policy{ts}.yaml"
    if not output_path.suffix:
        output_path = output_path.with_suffix(".yaml")

    lines = []
    lines.append("# Auto-generated from CSV matrices")
    lines.append("")

    for api in apis:
        file_exprs = []
        for entry in file_data:
            allowed_roles = [
                role for role in roles if entry["matrix"].get(api, {}).get(role) == 1
            ]
            if not allowed_roles:
                continue
            roles_expr = " or ".join(f"role:{role}" for role in allowed_roles)
            if entry["project_id"]:
                expr = f"({roles_expr}) and project:{entry['project_id']}"
            else:
                expr = roles_expr
            file_exprs.append(f"({expr})")
        if file_exprs:
            combined = " or ".join(file_exprs)
            rule = f"role:admin or {combined}"
        else:
            rule = "role:admin"
        lines.append(f"{api}: \"{rule}\"")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="ascii")
    print(f"已生成: {output_path}")


def graph_to_yaml(args):
    driver = _connect_neo4j(args.neo4j_uri, args.neo4j_user, args.neo4j_password)
    project_map = _read_project_map(Path(args.project_map))
    try:
        with driver.session() as session:
            records = list(
                session.run(
                    """
                    MATCH (p:PolicyNode)-[:HAS_RULE]->(r:RuleNode)
                    RETURN p.id AS api,
                           r.expression AS expr,
                           r.normalized_expression AS norm,
                           r.name AS name
                    """
                )
            )
    finally:
        driver.close()

    policy_rules = {}
    for record in records:
        api = record["api"]
        expr = record["expr"] or record["norm"] or record["name"]
        if not expr:
            continue
        expr = _replace_project_names(expr, project_map)
        policy_rules.setdefault(api, []).append(expr)

    output_path = Path(args.output)
    if output_path.is_dir():
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        output_path = output_path / f"Policy{ts}.yaml"
    if not output_path.suffix:
        output_path = output_path.with_suffix(".yaml")

    lines = []
    lines.append("# Auto-generated from Neo4j policy graph")
    lines.append("")
    for api in sorted(policy_rules.keys()):
        rules = policy_rules[api]
        combined = " or ".join(f"({rule})" for rule in rules)
        lines.append(f"{api}: \"{combined}\"")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="ascii")
    print(f"已生成: {output_path}")


def build_parser():
    parser = argparse.ArgumentParser(description="Policy generation tools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_graph = subparsers.add_parser("graph-to-csv", help="从图数据库生成 CSV")
    parser_graph.add_argument("--neo4j-uri", default=DEFAULT_NEO4J_URI)
    parser_graph.add_argument("--neo4j-user", default=DEFAULT_NEO4J_USER)
    parser_graph.add_argument("--neo4j-password", default=DEFAULT_NEO4J_PASSWORD)
    parser_graph.add_argument("--project-map", default=str(DEFAULT_PROJECTINFO))
    parser_graph.add_argument("--output-dir", default=str(DEFAULT_POLICY_DIR))
    parser_graph.set_defaults(func=graph_to_csv)

    parser_csv = subparsers.add_parser("csv-to-yaml", help="从 CSV 生成 YAML")
    parser_csv.add_argument("--csv-files", nargs="+", required=True)
    parser_csv.add_argument("--projects", nargs="*")
    parser_csv.add_argument("--project-map", default=str(DEFAULT_PROJECTINFO))
    parser_csv.add_argument("--output", default=str(DEFAULT_POLICY_DIR))
    parser_csv.set_defaults(func=csv_to_yaml)

    parser_yaml = subparsers.add_parser("graph-to-yaml", help="从图数据库生成 YAML")
    parser_yaml.add_argument("--neo4j-uri", default=DEFAULT_NEO4J_URI)
    parser_yaml.add_argument("--neo4j-user", default=DEFAULT_NEO4J_USER)
    parser_yaml.add_argument("--neo4j-password", default=DEFAULT_NEO4J_PASSWORD)
    parser_yaml.add_argument("--project-map", default=str(DEFAULT_PROJECTINFO))
    parser_yaml.add_argument("--output", default=str(DEFAULT_POLICY_DIR))
    parser_yaml.set_defaults(func=graph_to_yaml)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except Exception as exc:
        print(f"错误: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
