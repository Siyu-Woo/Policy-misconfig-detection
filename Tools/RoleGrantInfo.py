#!/usr/bin/env python3
# coding: utf-8
"""
收集 Keystone 中 user/project/role 及授权关系，输出至 CSV。

生成文件（容器内路径）：
  - /root/policy-fileparser/data/assistfile/userinfo.csv   (user_id,user_name)
  - /root/policy-fileparser/data/assistfile/projectinfo.csv (project_id,project_name)
  - /root/policy-fileparser/data/assistfile/roleinfo.csv   (role_id,role_name)
  - /root/policy-fileparser/data/assistfile/rolegrant.csv  (user_id,user_name,project_id,project_name,role_id,role_name)

权限不足时会打印错误并建议使用 admin 凭证。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Dict, List, Tuple

ASSIST_DIR = "/root/policy-fileparser/data/assistfile"
USER_CSV = os.path.join(ASSIST_DIR, "userinfo.csv")
PROJECT_CSV = os.path.join(ASSIST_DIR, "projectinfo.csv")
ROLE_CSV = os.path.join(ASSIST_DIR, "roleinfo.csv")
ROLEGRANT_CSV = os.path.join(ASSIST_DIR, "rolegrant.csv")


def run_json(cmd: List[str]) -> List[Dict[str, str]]:
    """以 JSON 格式执行 openstack 命令并返回列表."""
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        return json.loads(out)
    except subprocess.CalledProcessError as exc:
        print(f"命令失败: {' '.join(cmd)}", file=sys.stderr)
        print(exc.output, file=sys.stderr)
        print("建议使用 admin 凭证重试。", file=sys.stderr)
        return []
    except json.JSONDecodeError as exc:
        print(f"解析 JSON 失败: {exc}", file=sys.stderr)
        return []


def write_csv(path: str, rows: List[Tuple[str, ...]], header: Tuple[str, ...]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    import csv

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def collect_users() -> Dict[str, str]:
    data = run_json(["openstack", "user", "list", "-f", "json", "-c", "ID", "-c", "Name"])
    mapping = {item["ID"]: item["Name"] for item in data if "ID" in item and "Name" in item}
    write_csv(USER_CSV, [(uid, name) for uid, name in mapping.items()], ("user_id", "user_name"))
    return mapping


def collect_projects() -> Dict[str, str]:
    data = run_json(["openstack", "project", "list", "-f", "json", "-c", "ID", "-c", "Name"])
    mapping = {item["ID"]: item["Name"] for item in data if "ID" in item and "Name" in item}
    write_csv(PROJECT_CSV, [(pid, name) for pid, name in mapping.items()], ("project_id", "project_name"))
    return mapping


def collect_roles() -> Dict[str, str]:
    data = run_json(["openstack", "role", "list", "-f", "json", "-c", "ID", "-c", "Name"])
    mapping = {item["Name"]: item["ID"] for item in data if "ID" in item and "Name" in item}
    write_csv(ROLE_CSV, [(rid, name) for name, rid in mapping.items()], ("role_id", "role_name"))
    return mapping


def collect_assignments(users: Dict[str, str], projects: Dict[str, str], roles: Dict[str, str]) -> List[Tuple[str, str, str, str, str, str]]:
    rows: List[Tuple[str, str, str, str, str, str]] = []
    user_ids = list(users.keys())
    project_ids = list(projects.keys())

    for uid in user_ids:
        for pid in project_ids:
            # 查询用户在项目上的角色
            assignments = run_json(
                [
                    "openstack",
                    "role",
                    "assignment",
                    "list",
                    "--user",
                    uid,
                    "--project",
                    pid,
                    "--names",
                    "-f",
                    "json",
                    "-c",
                    "Role",
                ]
            )
            if not assignments:
                continue
            for item in assignments:
                role_name = item.get("Role")
                if not role_name:
                    continue
                role_id = roles.get(role_name, "")
                rows.append(
                    (
                        uid,
                        users.get(uid, ""),
                        pid,
                        projects.get(pid, ""),
                        role_id,
                        role_name,
                    )
                )
    return rows


def main() -> None:
    users = collect_users()
    projects = collect_projects()
    roles = collect_roles()

    if not users or not projects or not roles:
        print("获取用户/项目/角色信息失败，终止。", file=sys.stderr)
        sys.exit(1)

    assignments = collect_assignments(users, projects, roles)
    if not assignments:
        print("未发现任何角色授权记录（可能缺少权限或没有授权）。")
    write_csv(
        ROLEGRANT_CSV,
        assignments,
        ("user_id", "user_name", "project_id", "project_name", "role_id", "role_name"),
    )
    print(f"已生成 {len(assignments)} 条授权记录 -> {ROLEGRANT_CSV}")


if __name__ == "__main__":
    main()
