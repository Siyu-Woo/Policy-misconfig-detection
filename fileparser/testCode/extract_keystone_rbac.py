#!/usr/bin/env python3
"""
提取 Keystone RBAC 日志中授权信息并导出为 CSV。

读取 /var/log/keystone/keystone.log，解析 RBAC 授权记录，输出字段：
时间、API 名称、project_name、user_name、用户 ID、项目 ID、system_scope、domain_id、授权结果。
project_name/user_name 通过 EnvInfo 的 projectinfo.csv/userinfo.csv 进行映射；缺失则填充 UKProj{n}/UKUser{n}。
结果写入 /root/policy-fileparser/data/assistfile/rbac_audit_keystone.csv，并在文件末尾添加生成时间注释。
"""

import argparse
import csv
import datetime as dt
import os
import re
from typing import Dict, Optional, List

LOG_PATH = "/var/log/keystone/keystone.log"
OUTPUT_PATH = "/root/policy-fileparser/data/assistfile/rbac_audit_keystone.csv"
ENVINFO_DIR = "/root/policy-fileparser/data/assistfile/EnvInfo"
USERINFO_PATH = os.path.join(ENVINFO_DIR, "userinfo.csv")
PROJECTINFO_PATH = os.path.join(ENVINFO_DIR, "projectinfo.csv")

RBAC_PATTERN = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)\s+\d+\s+\w+\s+"
    r"keystone\.common\.rbac_enforcer\.enforcer\s+\[(?P<context>[^\]]+)\]\s+RBAC:\s+"
    r"(?P<message>.*)$"
)
API_PATTERN = re.compile(r"`([^`]+)`")


def parse_context(context: str) -> Dict[str, Optional[str]]:
    parts = context.split()
    while len(parts) < 8:
        parts.append("-")
    system_scope, req_id, user_id, project_id, domain_id, *_ = parts
    return {
        "system_scope": None if system_scope == "None" else system_scope,
        "request_id": req_id,
        "user_id": None if user_id in ("-", "None") else user_id,
        "project_id": None if project_id in ("-", "None") else project_id,
        "domain_id": None if domain_id in ("-", "None") else domain_id,
    }


def parse_line(line: str) -> Optional[Dict[str, str]]:
    match = RBAC_PATTERN.match(line.strip())
    if not match:
        return None
    timestamp = match.group("ts")
    context = parse_context(match.group("context"))
    message = match.group("message")
    api_match = API_PATTERN.search(message)
    api = api_match.group(1) if api_match else ""
    is_authorizing = "Authorizing" in message
    is_result = "Authorization" in message and not is_authorizing
    success = None
    if is_result:
        success = "granted" in message.lower()
    return {
        "timestamp": timestamp,
        "api": api,
        "message": message,
        "is_authorizing": is_authorizing,
        "success": success,
        **context,
    }


def load_id_map(path: str, id_key: str, name_key: str) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    if not os.path.exists(path):
        return mapping
    with open(path, "r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            id_val = (row.get(id_key) or "").strip()
            name_val = (row.get(name_key) or "").strip()
            if id_val:
                mapping[id_val] = name_val or id_val
    return mapping


class UnknownNameResolver:
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        self.counter = 0
        self.mapping: Dict[str, str] = {}

    def resolve(self, key: str) -> str:
        if key in self.mapping:
            return self.mapping[key]
        self.counter += 1
        name = f"{self.prefix}{self.counter}"
        self.mapping[key] = name
        return name


def annotate_names(
    records: List[Dict[str, Optional[str]]],
    user_map: Dict[str, str],
    project_map: Dict[str, str],
) -> None:
    unknown_user = UnknownNameResolver("UKUser")
    unknown_project = UnknownNameResolver("UKProj")
    for entry in records:
        user_id = entry.get("user_id") or ""
        project_id = entry.get("project_id") or ""

        if user_id:
            entry["user_name"] = user_map.get(user_id) or unknown_user.resolve(user_id)
        else:
            entry["user_name"] = unknown_user.resolve("<none>")

        if project_id:
            entry["project_name"] = project_map.get(project_id) or unknown_project.resolve(
                project_id
            )
        else:
            entry["project_name"] = unknown_project.resolve("<none>")


def build_records(log_path: str) -> List[Dict[str, Optional[str]]]:
    pending: Dict[str, Dict[str, Optional[str]]] = {}
    results: List[Dict[str, Optional[str]]] = []
    if not os.path.exists(log_path):
        return results

    with open(log_path, "r", encoding="utf-8") as log_file:
        for raw_line in log_file:
            parsed = parse_line(raw_line)
            if not parsed:
                continue
            req_id = parsed["request_id"]
            if parsed["is_authorizing"]:
                pending[req_id] = {
                    "timestamp": parsed["timestamp"],
                    "api": parsed["api"],
                    "user_id": parsed["user_id"],
                    "project_id": parsed["project_id"],
                    "system_scope": parsed["system_scope"],
                    "domain_id": parsed["domain_id"],
                    "authorized": "",
                }
            elif parsed["success"] is not None:
                entry = pending.pop(req_id, None)
                # 如果未捕获对应的 Authorizing 行，使用当前记录补充
                if entry is None:
                    entry = {
                        "timestamp": parsed["timestamp"],
                        "api": parsed["api"],
                        "user_id": parsed["user_id"],
                        "project_id": parsed["project_id"],
                        "system_scope": parsed["system_scope"],
                        "domain_id": parsed["domain_id"],
                    }
                entry["authorized"] = "yes" if parsed["success"] else "no"
                results.append(entry)

    # 对还未匹配到结果的记录，默认标记为未知
    for entry in pending.values():
        if not entry.get("authorized"):
            entry["authorized"] = "unknown"
        results.append(entry)

    return results


def write_csv(records: List[Dict[str, Optional[str]]], output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fieldnames = [
        "timestamp",
        "api",
        "project_name",
        "user_name",
        "user_id",
        "project_id",
        "system_scope",
        "domain_id",
        "authorized",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in records:
            writer.writerow(row)
    with open(output_path, "a", encoding="utf-8") as csvfile:
        csvfile.write(
            f"# generated at {dt.datetime.utcnow().isoformat(timespec='seconds')}Z\n"
        )


def clear_log(log_path: str) -> None:
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "w", encoding="utf-8"):
        pass
    print(f"已清空日志: {log_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="提取 Keystone RBAC 授权日志")
    parser.add_argument(
        "--log",
        default=LOG_PATH,
        help="指定日志文件路径，默认 /var/log/keystone/keystone.log",
    )
    parser.add_argument(
        "--output",
        default=OUTPUT_PATH,
        help="指定输出 CSV 路径，默认 /root/policy-fileparser/data/assistfile/rbac_audit_keystone.csv",
    )
    parser.add_argument(
        "--clear-log",
        action="store_true",
        help="清空日志文件（与 --log 指定路径一致）",
    )
    args = parser.parse_args()

    if args.clear_log:
        clear_log(args.log)
        return

    records = build_records(args.log)
    if not records:
        print("File parsing completed")
        return
    user_map = load_id_map(USERINFO_PATH, "user_id", "user_name")
    project_map = load_id_map(PROJECTINFO_PATH, "project_id", "project_name")
    annotate_names(records, user_map, project_map)
    write_csv(records, args.output)
    print("File parsing completed")


if __name__ == "__main__":
    main()
