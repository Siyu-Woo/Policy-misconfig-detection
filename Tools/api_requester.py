#!/usr/bin/env python3
"""
简单的 Keystone API 调用脚本。

功能：
  1. 默认使用当前 shell 已导入的 OpenStack 环境变量（Keystone 凭证）；
  2. 允许通过命令行重写 OS_* 变量（用户、密码、项目等）来切换身份；
  3. 通过 --api 参数指定要执行的 openstack 命令，默认执行 `openstack user list`。

示例：
  python api_requester.py
  python api_requester.py --api "openstack project list"
  python api_requester.py --api "openstack user list" --username demo --password secret \
      --project demo --user-domain Default --project-domain Default --auth-url http://127.0.0.1:5000/v3
"""

import argparse
import os
import shlex
import subprocess
import sys
from typing import Dict


def build_env(args: argparse.Namespace) -> Dict[str, str]:
    env = os.environ.copy()
    if args.username:
        env["OS_USERNAME"] = args.username
    if args.password:
        env["OS_PASSWORD"] = args.password
    if args.project:
        env["OS_PROJECT_NAME"] = args.project
    if args.project_domain:
        env["OS_PROJECT_DOMAIN_NAME"] = args.project_domain
    if args.user_domain:
        env["OS_USER_DOMAIN_NAME"] = args.user_domain
    if args.auth_url:
        env["OS_AUTH_URL"] = args.auth_url
    if args.region:
        env["OS_REGION_NAME"] = args.region
    if args.token:
        env["OS_TOKEN"] = args.token
    return env


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="执行指定 OpenStack CLI API（默认 openstack user list）"
    )
    parser.add_argument(
        "--api",
        default="openstack user list",
        help="要执行的 openstack 命令，默认 'openstack user list'",
    )
    parser.add_argument("--username", help="OS_USERNAME，默认使用当前环境变量")
    parser.add_argument("--password", help="OS_PASSWORD")
    parser.add_argument("--project", help="OS_PROJECT_NAME")
    parser.add_argument("--project-domain", help="OS_PROJECT_DOMAIN_NAME")
    parser.add_argument("--user-domain", help="OS_USER_DOMAIN_NAME")
    parser.add_argument("--auth-url", help="OS_AUTH_URL，例如 http://127.0.0.1:5000/v3")
    parser.add_argument("--region", help="OS_REGION_NAME")
    parser.add_argument(
        "--token",
        help="OS_TOKEN（少见，可用于无密码 token 调用，需要配合 --project 等）",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    env = build_env(args)
    cmd = shlex.split(args.api)
    try:
        result = subprocess.run(
            cmd, env=env, check=True, capture_output=False
        )
    except FileNotFoundError:
        print(f"未找到命令：{cmd[0]}，请确认已安装 openstack CLI 并在 PATH 中。", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as exc:
        print(f"命令执行失败，退出码 {exc.returncode}", file=sys.stderr)
        sys.exit(exc.returncode)


if __name__ == "__main__":
    main()
