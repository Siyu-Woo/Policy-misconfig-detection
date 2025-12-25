#!/usr/bin/env python3
"""
提取 Keystone RBAC 日志中授权信息并导出为 CSV。

读取 /var/log/keystone/keystone.log，解析 RBAC 授权记录，输出字段：
时间、API 名称、用户 ID、项目 ID、system_scope、domain_id、授权结果。
结果写入 /root/policy-fileparser/data/assistfile/rbac_audit_keystone.csv，并在文件末尾添加生成时间注释。
"""

import argparse
import csv
import datetime as dt
import os
import re
from typing import Dict, Optional, List

LOG_PATH = "/var/log/keystone/keystoneCollect.log"
OUTPUT_PATH = "/root/policy-fileparser/data/assistfile/rbac_audit_keystoneCollect.csv"

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


def build_records() -> List[Dict[str, Optional[str]]]:
    pending: Dict[str, Dict[str, Optional[str]]] = {}
    results: List[Dict[str, Optional[str]]] = []
    if not os.path.exists(LOG_PATH):
        return results

    with open(LOG_PATH, "r", encoding="utf-8") as log_file:
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


def write_csv(records: List[Dict[str, Optional[str]]]) -> None:
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    fieldnames = [
        "timestamp",
        "api",
        "user_id",
        "project_id",
        "system_scope",
        "domain_id",
        "authorized",
    ]
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in records:
            writer.writerow(row)
    with open(OUTPUT_PATH, "a", encoding="utf-8") as csvfile:
        csvfile.write(
            f"# generated at {dt.datetime.utcnow().isoformat(timespec='seconds')}Z\n"
        )


def clear_log() -> None:
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "w", encoding="utf-8"):
        pass
    print(f"已清空日志: {LOG_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser(description="提取 Keystone RBAC 授权日志")
    parser.add_argument(
        "--clear-log",
        action="store_true",
        help="清空 /var/log/keystone/keystone.log",
    )
    args = parser.parse_args()

    if args.clear_log:
        clear_log()
        return

    records = build_records()
    if not records:
        print("File parsing completed")
        return
    write_csv(records)
    print("File parsing completed")


if __name__ == "__main__":
    main()
