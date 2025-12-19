#!/usr/bin/env python3
# coding: utf-8
"""
简单的 Keystone policy 管理脚本。

功能：
 1. 复制策略文件：从 /root/policy-fileparser 下指定文件（默认 policy.yaml）复制到 /etc/keystone/keystone_policy.yaml
 2. 新增/合并策略规则：为指定 API 添加 role/project 条件，已存在则用 (原规则) or (新规则) 合并
 3. 删除策略：移除指定 policy
 4. 导出策略：将 /etc/keystone/keystone_policy.yaml 导出到指定路径
 5. 关闭自定义策略：修改 /etc/keystone/keystone.conf，将 [oslo_policy] 中 policy_file 置空以回退默认策略

执行完变更后，会提醒重启 Keystone（Apache）。
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from typing import Dict, Any

try:
    import yaml
except ImportError:
    print("缺少 PyYAML，请先安装：pip install pyyaml", file=sys.stderr)
    sys.exit(1)


DEFAULT_SRC = "/root/policy-fileparser/policy.yaml"
TARGET_POLICY = "/etc/keystone/keystone_policy.yaml"
KEYSTONE_CONF = "/etc/keystone/keystone.conf"


def load_policy(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
        if not isinstance(data, dict):
            raise ValueError(f"策略文件格式错误: {path}")
        return data


def save_policy(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def backup(path: str) -> None:
    if os.path.exists(path):
        shutil.copy2(path, path + ".bak")


def copy_policy(src: str, dst: str = TARGET_POLICY) -> None:
    if not os.path.exists(src):
        raise FileNotFoundError(f"源文件不存在: {src}")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    backup(dst)
    shutil.copy2(src, dst)
    print(f"已复制策略文件: {src} -> {dst}")


def build_condition(role: str | None, project: str | None) -> str:
    if role and project:
        return f"(role:{role} and project_id:{project})"
    if role:
        return f"role:{role}"
    if project:
        return f"project_id:{project}"
    raise ValueError("新增条件需至少提供 role 或 project")


def add_policy(name: str, role: str | None, project: str | None) -> None:
    policy = load_policy(TARGET_POLICY)
    new_cond = build_condition(role, project)
    if name in policy:
        orig = str(policy[name]).strip()
        if orig:
            policy[name] = f"({orig}) or ({new_cond})"
        else:
            policy[name] = new_cond
        print(f"已合并策略 {name}: {policy[name]}")
    else:
        policy[name] = new_cond
        print(f"已新增策略 {name}: {new_cond}")
    backup(TARGET_POLICY)
    save_policy(TARGET_POLICY, policy)


def delete_policy(name: str) -> None:
    policy = load_policy(TARGET_POLICY)
    if name in policy:
        backup(TARGET_POLICY)
        policy.pop(name)
        save_policy(TARGET_POLICY, policy)
        print(f"已删除策略 {name}")
    else:
        print(f"未找到策略 {name}，无需删除")


def export_policy(dst: str) -> None:
    if not os.path.exists(TARGET_POLICY):
        raise FileNotFoundError(f"策略文件不存在: {TARGET_POLICY}")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(TARGET_POLICY, dst)
    print(f"已导出策略到 {dst}")


def disable_policy(conf_path: str = KEYSTONE_CONF) -> None:
    if not os.path.exists(conf_path):
        raise FileNotFoundError(f"未找到 keystone.conf: {conf_path}")
    backup(conf_path)
    lines = []
    in_block = False
    modified = False
    with open(conf_path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("["):
                in_block = stripped.lower() == "[oslo_policy]"
            if in_block and stripped.lower().startswith("policy_file"):
                lines.append("policy_file =\n")
                modified = True
            else:
                lines.append(line)
    if not modified and in_block:
        lines.append("policy_file =\n")
    with open(conf_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"已在 {conf_path} 禁用自定义 policy_file（回退默认策略）")


def print_restart_hint() -> None:
    print("\n请重启 Keystone 以生效，参考命令：")
    print("service supervisor stop 2>/dev/null || true  # 守护进程关闭")
    print("service apache2 stop")
    print("service apache2 start\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Keystone policy 管理工具")
    sub = parser.add_subparsers(dest="cmd", required=True)

    cp = sub.add_parser("copy", help="复制策略文件到 /etc/keystone/keystone_policy.yaml")
    cp.add_argument("--src", default=DEFAULT_SRC, help="源策略文件，默认 /root/policy-fileparser/policy.yaml")

    addp = sub.add_parser("add", help="为指定策略添加 role/project 条件（合并为 OR）")
    addp.add_argument("--name", required=True, help="策略名（API 名称）")
    addp.add_argument("--role", help="角色名，例如 admin/reader")
    addp.add_argument("--project", help="项目 ID 或占位符，例如 %(project_id)s")

    sub.add_parser("disable", help="禁用自定义 policy_file，回退默认策略")

    delp = sub.add_parser("delete", help="删除指定策略")
    delp.add_argument("--name", required=True, help="策略名（API 名称）")

    exp = sub.add_parser("export", help="导出 /etc/keystone/keystone_policy.yaml")
    exp.add_argument("--dst", required=True, help="导出目标路径，默认建议 /root/policy-fileparser")

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        if args.cmd == "copy":
            copy_policy(args.src)
        elif args.cmd == "add":
            add_policy(args.name, args.role, args.project)
        elif args.cmd == "delete":
            delete_policy(args.name)
        elif args.cmd == "export":
            export_policy(args.dst)
        elif args.cmd == "disable":
            disable_policy()
        else:
            print("未知命令")
            sys.exit(1)
        print_restart_hint()
    except Exception as exc:
        print(f"操作失败: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
