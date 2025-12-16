#!/usr/bin/env python3
"""
统一执行身份子图与策略子图构建的辅助脚本。

使用流程：
    1. 确保已在容器内加载 OpenStack admin 凭证（source /opt/openstack/envinfo/admin-openrc.sh）。
    2. 在容器中运行本脚本（建议激活 Miniconda base 环境）。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Dict, Any
import re

# fileparser 本目录下的模块
from policypreprocess import process_policy_file
from policy_parser import PolicyRuleParser
from openstackpolicygraph import PolicyGraphCreator
import openstackgraph as osg

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from Tools.CheckOutput import PolicyCheckReporter  # noqa: E402
from output_control import set_general_output_enabled  # noqa: E402

DEFAULT_SERVICES = ["keystone", "nova", "placement", "neutron", "cinder", "glance"]


def run_openstack_command(command: List[str], silent: bool = False) -> None:
    """执行 openstack CLI，打印标准输出/错误。"""
    if not silent:
        print(f"\n$ {' '.join(command)}")
    subprocess.run(command, check=True, stdout=None if not silent else subprocess.DEVNULL,
                   stderr=None if not silent else subprocess.DEVNULL)


def fetch_identity_and_credentials(services: Iterable[str], silent: bool = False) -> None:
    """
    调用 openstack CLI 查询各组件的 service/endpoint 信息，帮助确认凭证是否可用。
    默认会查询 keystone/nova/... 等服务，可通过 --services 参数定制。
    若只想查看单个组件，可在命令行提供 --services keystone 之类的参数。
    """
    commands = [
        ["openstack", "project", "list"],
        ["openstack", "user", "list"],
    ]
    for svc in services:
        commands.append(["openstack", "service", "show", svc])
        commands.append(["openstack", "endpoint", "list", "--service", svc])
    for cmd in commands:
        run_openstack_command(cmd, silent=silent)


def build_identity_graph(neo4j_uri: str, user: str, password: str, show_token_info: bool = False) -> None:
    """调用 openstackgraph 读取 Keystone 数据并写入 Neo4j。"""
    osg.NEO4J_URI = neo4j_uri
    osg.NEO4J_USER = user
    osg.NEO4J_PASSWORD = password
    osg.set_token_output_verbose(show_token_info)
    manager = osg.OpenStackNeo4jManager()
    try:
        users, roles, projects, assignments = manager.read_data_from_openstack()
        if not users or not roles or not assignments:
            raise SystemExit("OpenStack 数据不足，跳过身份子图导入。")
        mappings = manager.generate_tokens_from_assignments(users, roles, assignments)
        manager.create_neo4j_graph(mappings)
        if show_token_info:
            unique_tokens = {m['token_id'] for m in mappings}
            print(f"[Token Info] total tokens: {len(unique_tokens)}, mappings: {len(mappings)}")
            sample = mappings[:3]
            for record in sample:
                user_name = record['user'].name
                role_names = ", ".join(a['role'].name for a in record['role_assignments'])
                print(f"  - {user_name} -> {role_names} (token {record['token_id'][:8]}...)")
            if len(mappings) > len(sample):
                print(f"  ... {len(mappings) - len(sample)} more mappings")
        print("✓ 已写入身份子图 (User -> Token -> Role)")
    finally:
        manager.close()


def build_policy_graph(policy_paths: List[Path], neo4j_uri: str, user: str, password: str,
                       show_policy_debug: bool = False, show_check_output: bool = False,
                       show_stats: bool = False) -> None:
    """解析策略文件并写入策略图。"""
    reporter = PolicyCheckReporter()
    error_count = 0
    def report_issue(code: str, **kwargs: Any) -> None:
        nonlocal error_count
        if show_check_output:
            reporter.report(code, **kwargs)
        error_count += 1
    raw_policies: Dict[str, str] = {}
    policy_metadata = {}
    for path in policy_paths:
        if not path.exists():
            print(f"⚠ 警告：策略文件不存在 {path}，跳过")
            continue
        data = process_policy_file(str(path))
        print(f"读取 {len(data)} 条策略：{path}")
        for name, info in data.items():
            raw_policies[name] = info['expression']
            policy_metadata[name] = {
                'file': info.get('file', str(path)),
                'lines': info.get('lines', []),
                'raw_entries': info.get('raw_entries', [])
            }

    parser = PolicyRuleParser()
    parser.extract_rule_definitions(raw_policies)

    def unit_signature(unit: Dict[str, List[str]]) -> str:
        if not unit:
            return "@"
        parts = []
        for key in sorted(unit.keys()):
            values = unit.get(key, [])
            norm_values = sorted({str(v) for v in values if v})
            if norm_values:
                parts.append(f"{key}:{'|'.join(norm_values)}")
        return " AND ".join(parts) if parts else "@"

    policy_dict = {}
    for name, expr in raw_policies.items():
        if parser._is_rule_definition(name, expr):
            continue
        parsed = parser.parse_single_policy(name, expr)
        if parsed is None:
            print(f"⚠ 跳过解析失败的策略：{name}")
            continue
        if show_policy_debug:
            print(f"[Policy Parse] {name}: {expr}")
        if name not in policy_dict:
            policy_dict[name] = {
                'expressions': [],
                'metadata': policy_metadata.get(name, {'file': '', 'lines': [], 'raw_entries': []}),
                'unit_signatures': []
            }
        policy_dict[name]['expressions'].append(expr)
        units = parser._extract_minimal_units(parsed) or [{}]
        unit_signatures = []
        for unit in units:
            unit_signatures.append(unit_signature(unit))
        policy_dict[name]['unit_signatures'].extend(unit_signatures)

    def normalize_expression(expr: str) -> str:
        expr = re.sub(r'\s+', ' ', expr.strip())
        expr = re.sub(r'\band\b', 'and', expr, flags=re.IGNORECASE)
        expr = re.sub(r'\bor\b', 'or', expr, flags=re.IGNORECASE)
        return expr

    def check_policy_duplicates() -> None:
        for policy_name, data in policy_dict.items():
            metadata = data.get('metadata', {})
            raw_entries = metadata.get('raw_entries', [])
            if len(raw_entries) > 1:
                normalized = [
                    (entry['line'], normalize_expression(entry['value']))
                    for entry in raw_entries
                ]
                unique_rules = {rule for _, rule in normalized if rule}
                policy_line_info = "\n".join(
                    f"line {entry['line']}: {entry['value']}" for entry in raw_entries
                )
                if len(unique_rules) == 1:
                    # same rule repeated
                    target_entry = raw_entries[-1]
                    delete_target = f"line {target_entry['line']}: {target_entry['value']}"
                    report_issue(
                        "1",
                        policy_name=policy_line_info,
                        target=delete_target
                    )
                elif len(unique_rules) > 1:
                    suggestion = " or ".join(sorted(unique_rules))
                    report_issue(
                        "2",
                        policy_name=policy_line_info,
                        suggestion=suggestion
                    )

            # check duplicate rules within same policy definition
            unit_signatures = data.get('unit_signatures', [])
            signature_counts = {}
            for sig in unit_signatures:
                signature_counts[sig] = signature_counts.get(sig, 0) + 1
            repeated_units = [sig for sig, count in signature_counts.items() if count > 1]
            if repeated_units:
                suggestion = " or ".join(sorted(signature_counts.keys()))
                line_info = ", ".join(str(line) for line in metadata.get('lines', []))
                detail_lines = [
                    f"line {entry['line']}: {entry['value']}" for entry in raw_entries
                ] or [policy_name]
                policy_details = detail_lines
                report_issue(
                    "3",
                    policy_name="\n".join(policy_details),
                    fault_unit="\n".join(repeated_units),
                    suggestion=suggestion
                )

    check_policy_duplicates()

    creator = PolicyGraphCreator(uri=neo4j_uri, user=user, password=password)
    try:
        creator.create_policy_graph(policy_dict)
        stats = creator.get_graph_statistics() if show_stats else None
        if show_stats and stats:
            print("✓ 已写入策略子图，统计信息：")
            for key, value in stats.items():
                print(f"  {key}: {value}")
    finally:
        creator.close()

    total_policies = len(policy_dict)
    if error_count == 0:
        print(f"策略读取完成。read {total_policies} policy rules，all Meet configure safety baseline")
    else:
        print(f"策略读取完成。read {total_policies} policy rules，{error_count} configure are improper")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OpenStack 身份/策略图构建脚本")
    parser.add_argument(
        "--services",
        default=",".join(DEFAULT_SERVICES),
        help="需要检查的服务类型，逗号分隔。默认: %(default)s",
    )
    parser.add_argument(
        "--policy-files",
        default="/etc/openstack/policies/keystone-policy.yaml",
        help="策略文件路径，逗号分隔，默认读取容器挂载目录内的 keystone-policy.yaml",
    )
    parser.add_argument(
        "--neo4j-uri",
        default="bolt://localhost:7687",
        help="Neo4j Bolt URI，默认 %(default)s",
    )
    parser.add_argument(
        "--neo4j-user",
        default="neo4j",
        help="Neo4j 用户名，默认 %(default)s",
    )
    parser.add_argument(
        "--neo4j-password",
        default="Password",
        help="Neo4j 密码，默认 %(default)s",
    )
    parser.add_argument(
        "--skip-identity",
        action="store_true",
        help="只解析策略，不构建身份子图",
    )
    parser.add_argument(
        "--skip-policy",
        action="store_true",
        help="只构建身份子图，跳过策略解析",
    )
    parser.add_argument(
        "--show-token-info",
        action="store_true",
        help="输出读取 token 的摘要信息",
    )
    parser.add_argument(
        "--show-policy-debug",
        action="store_true",
        help="输出策略解析过程与结果",
    )
    parser.add_argument(
        "--show-check-report",
        action="store_true",
        help="输出策略错误检测信息",
    )
    parser.add_argument(
        "--show-policy-statistic",
        action="store_true",
        help="输出策略写入后的统计信息",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    services = [svc.strip() for svc in args.services.split(",") if svc.strip()]
    policy_files = [Path(p.strip()) for p in args.policy_files.split(",") if p.strip()]

    show_general = args.show_token_info or args.show_policy_debug or not args.show_check_report
    set_general_output_enabled(show_general)

    def announce_step(step: str, detail: str, verbose: bool, start: bool = True) -> None:
        if verbose:
            prefix = "\n" if step != "1" and start else ""
            if start:
                print(f"{prefix}=== 第 {step} 步：{detail} ===")
        else:
            status = "开始" if start else "完成"
            print(f"[Step {step}] {detail}{status}")

    step1_detail = "获取身份/凭证信息"
    announce_step("1", step1_detail, show_general, start=True)
    fetch_identity_and_credentials(services, silent=not show_general)
    announce_step("1", step1_detail, show_general, start=False)

    if not args.skip_identity:
        identity_verbose = show_general or args.show_token_info
        step2_detail = "构建身份子图"
        announce_step("2", step2_detail, identity_verbose, start=True)
        build_identity_graph(
            args.neo4j_uri,
            args.neo4j_user,
            args.neo4j_password,
            show_token_info=args.show_token_info,
        )
        announce_step("2", step2_detail, identity_verbose, start=False)

    if not args.skip_policy:
        policy_verbose = show_general or args.show_policy_debug or args.show_check_report or args.show_policy_statistic
        step3_detail = "解析策略并构建策略子图"
        announce_step("3", step3_detail, policy_verbose, start=True)
        build_policy_graph(
            policy_files,
            args.neo4j_uri,
            args.neo4j_user,
            args.neo4j_password,
            show_policy_debug=args.show_policy_debug,
            show_check_output=args.show_check_report,
            show_stats=args.show_policy_statistic,
        )
        announce_step("3", step3_detail, policy_verbose, start=False)

    print("\n✓ 全部任务完成")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(f"\n✗ 命令执行失败: {exc}", file=sys.stderr)
        sys.exit(exc.returncode)
