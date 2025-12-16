#!/usr/bin/env python3
"""
高级别权限库维护脚本。
每条记录包含: id, api_name, policy_name, role, system_scope

支持的操作：
  - view:  查看所有记录
  - add:   新增记录
  - update:根据id更新指定字段
  - delete:根据id删除记录
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from typing import List, Dict

DATA_DIR = "/root/policy-fileparser/data/assistfile"
CSV_PATH = os.path.join(DATA_DIR, "sensitive_permissions.csv")

COLUMNS = ["id", "policy_name", "role", "project_name", "system_scope"]


def ensure_storage() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writeheader()


def read_records() -> List[Dict[str, str]]:
    ensure_storage()
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def write_records(records: List[Dict[str, str]]) -> None:
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(records)


def view_records() -> None:
    records = read_records()
    if not records:
        print("当前敏感权限库为空。")
        return
    for record in records:
        print(f"[ID {record['id']}] policy={record['policy_name']}, "
              f"role={record['role']}, project_name={record.get('project_name', '')}, "
              f"system_scope={record.get('system_scope', '')}")


def parse_multi_field(value: str) -> List[str]:
    if not value:
        return []
    tokens = []
    for part in value.replace("|", ",").split(","):
        part = part.strip()
        if part:
            tokens.append(part)
    return tokens


def merge_field(existing: str, additions: List[str]) -> str:
    values = set(parse_multi_field(existing))
    for item in additions:
        values.add(item)
    return ",".join(sorted(values)) if values else ""


def add_record(policy_name: str, role: str, project_name: str, system_scope: str) -> None:
    if not policy_name:
        print("✗ policy_name 不能为空")
        return
    records = read_records()
    additions_role = parse_multi_field(role)
    additions_project = parse_multi_field(project_name)
    additions_scope = parse_multi_field(system_scope)
    for record in records:
        if record["policy_name"] == policy_name:
            record["role"] = merge_field(record.get("role", ""), additions_role)
            record["project_name"] = merge_field(record.get("project_name", ""), additions_project)
            record["system_scope"] = merge_field(record.get("system_scope", ""), additions_scope)
            write_records(records)
            print(f"已更新策略 {policy_name} 的角色/作用域配置")
            return

    next_id = 1
    if records and records[-1]["id"].isdigit():
        next_id = int(records[-1]["id"]) + 1
    new_record = {
        "id": str(next_id),
        "policy_name": policy_name,
        "role": ",".join(additions_role) if additions_role else "",
        "project_name": ",".join(additions_project) if additions_project else "",
        "system_scope": ",".join(additions_scope) if additions_scope else "",
    }
    records.append(new_record)
    write_records(records)
    print(f"已新增记录 ID {next_id}")


def update_record(record_id: str, policy_name: str, role: str, project_name: str, system_scope: str) -> None:
    records = read_records()
    updated = False
    for record in records:
        if record["id"] == record_id:
            if policy_name is not None:
                record["policy_name"] = policy_name
            if role is not None:
                record["role"] = merge_field(record.get("role", ""), parse_multi_field(role))
            if project_name is not None:
                record["project_name"] = merge_field(record.get("project_name", ""), parse_multi_field(project_name))
            if system_scope is not None:
                record["system_scope"] = merge_field(record.get("system_scope", ""), parse_multi_field(system_scope))
            updated = True
            break
    if not updated:
        print(f"未找到 ID {record_id} 的记录。")
        return
    write_records(records)
    print(f"已更新记录 ID {record_id}")


def delete_record(record_id: str) -> None:
    records = read_records()
    new_records = [r for r in records if r["id"] != record_id]
    if len(new_records) == len(records):
        print(f"未找到 ID {record_id} 的记录。")
        return
    write_records(new_records)
    print(f"已删除记录 ID {record_id}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="敏感权限库维护工具")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("view", help="查看所有记录")

    add_parser = subparsers.add_parser("add", help="新增记录")
    add_parser.add_argument("--policy-name", required=True)
    add_parser.add_argument("--role", default="")
    add_parser.add_argument("--project-name", default="")
    add_parser.add_argument("--system-scope", default="")

    update_parser = subparsers.add_parser("update", help="更新记录")
    update_parser.add_argument("--id", required=True)
    update_parser.add_argument("--policy-name")
    update_parser.add_argument("--role")
    update_parser.add_argument("--project-name")
    update_parser.add_argument("--system-scope")

    delete_parser = subparsers.add_parser("delete", help="删除记录")
    delete_parser.add_argument("--id", required=True)

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "view":
        view_records()
    elif args.command == "add":
        add_record(args.policy_name, args.role, args.project_name, args.system_scope)
    elif args.command == "update":
        update_record(args.id, args.policy_name, args.role, args.project_name, args.system_scope)
    elif args.command == "delete":
        delete_record(args.id)
    else:
        raise SystemExit(f"Unknown command {args.command}")


if __name__ == "__main__":
    main()
