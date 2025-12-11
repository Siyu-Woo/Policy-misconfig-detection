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
from typing import Iterable, List

# fileparser 本目录下的模块
from policypreprocess import process_policy_file
from policy_parser import PolicyRuleParser
from openstackpolicygraph import PolicyGraphCreator
import openstackgraph as osg

DEFAULT_SERVICES = ["keystone", "nova", "placement", "neutron", "cinder", "glance"]


def run_openstack_command(command: List[str]) -> None:
    """执行 openstack CLI，打印标准输出/错误。"""
    print(f"\n$ {' '.join(command)}")
    subprocess.run(command, check=True)


def fetch_identity_and_credentials(services: Iterable[str]) -> None:
    """
    调用 openstack CLI 查询各组件的 service/endpoint 信息，帮助确认凭证是否可用。
    默认会查询 keystone/nova/... 等服务，可通过 --services 参数定制。
    若只想查看单个组件，可在命令行提供 --services keystone 之类的参数。
    """
    run_openstack_command(["openstack", "project", "list"])
    run_openstack_command(["openstack", "user", "list"])
    for svc in services:
        run_openstack_command(["openstack", "service", "show", svc])
        run_openstack_command(["openstack", "endpoint", "list", "--service", svc])


def build_identity_graph(neo4j_uri: str, user: str, password: str) -> None:
    """调用 openstackgraph 读取 Keystone 数据并写入 Neo4j。"""
    osg.NEO4J_URI = neo4j_uri
    osg.NEO4J_USER = user
    osg.NEO4J_PASSWORD = password
    manager = osg.OpenStackNeo4jManager()
    try:
        users, roles, projects, assignments = manager.read_data_from_openstack()
        if not users or not roles or not assignments:
            raise SystemExit("OpenStack 数据不足，跳过身份子图导入。")
        mappings = manager.generate_tokens_from_assignments(users, roles, assignments)
        manager.create_neo4j_graph(mappings)
        print("✓ 已写入身份子图 (User -> Token -> Role)")
    finally:
        manager.close()


def build_policy_graph(policy_paths: List[Path], neo4j_uri: str, user: str, password: str) -> None:
    """解析策略文件并写入策略图。"""
    raw_policies = {}
    for path in policy_paths:
        if not path.exists():
            print(f"⚠ 警告：策略文件不存在 {path}，跳过")
            continue
        data = process_policy_file(str(path))
        print(f"读取 {len(data)} 条策略：{path}")
        raw_policies.update(data)

    parser = PolicyRuleParser()
    parser.extract_rule_definitions(raw_policies)

    policy_dict = {}
    for name, expr in raw_policies.items():
        if parser._is_rule_definition(name, expr):
            continue
        parsed = parser.parse_single_policy(name, expr)
        if parsed is None:
            print(f"⚠ 跳过解析失败的策略：{name}")
            continue
        policy_dict.setdefault(name, []).append(expr)

    creator = PolicyGraphCreator(uri=neo4j_uri, user=user, password=password)
    try:
        creator.create_policy_graph(policy_dict)
        stats = creator.get_graph_statistics()
        print("✓ 已写入策略子图，统计信息：")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    finally:
        creator.close()


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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    services = [svc.strip() for svc in args.services.split(",") if svc.strip()]
    policy_files = [Path(p.strip()) for p in args.policy_files.split(",") if p.strip()]

    print("=== 第 1 步：获取身份/凭证信息 ===")
    fetch_identity_and_credentials(services)

    if not args.skip_identity:
        print("\n=== 第 2 步：构建身份子图 ===")
        build_identity_graph(args.neo4j_uri, args.neo4j_user, args.neo4j_password)

    if not args.skip_policy:
        print("\n=== 第 3 步：解析策略并构建策略子图 ===")
        build_policy_graph(policy_files, args.neo4j_uri, args.neo4j_user, args.neo4j_password)

    print("\n✓ 全部任务完成")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(f"\n✗ 命令执行失败: {exc}", file=sys.stderr)
        sys.exit(exc.returncode)
