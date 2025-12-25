import csv
import io
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from . import config
from .exec_utils import docker_cp_from_container, docker_cp_to_container, docker_exec, docker_exec_simple
from .state import STATE


def _list_files(directory: Path) -> List[str]:
    if not directory.exists():
        return []
    files = [p for p in directory.iterdir() if p.is_file()]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return [p.name for p in files]


def list_log_files() -> List[str]:
    return _list_files(config.TEMP_LOG_DIR)


def choose_default_log_file() -> Optional[str]:
    default = config.TEMP_LOG_DIR / config.DEFAULT_LOG_NAME
    if default.exists():
        return config.DEFAULT_LOG_NAME
    files = list_log_files()
    return files[0] if files else None


def _timestamped_name(prefix: str, suffix: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{stamp}{suffix}"


def export_log() -> Dict[str, str]:
    dest = config.TEMP_LOG_DIR / config.DEFAULT_LOG_NAME
    docker_cp_from_container(config.LOG_FILE_CONTAINER, str(dest))

    backup_name = _timestamped_name("OSkeystone", ".log")
    shutil.copyfile(dest, config.TEMP_LOG_DIR / backup_name)

    STATE.set_current_file("log", config.DEFAULT_LOG_NAME)
    STATE.reset_log_parse()
    STATE.save()
    return {"file": config.DEFAULT_LOG_NAME, "backup": backup_name}


def import_log_file(filename: str, content: bytes) -> str:
    target = config.TEMP_LOG_DIR / filename
    if target.exists():
        filename = _timestamped_name(Path(filename).stem or "keystone", ".log")
        target = config.TEMP_LOG_DIR / filename
    target.write_bytes(content)

    shutil.copyfile(target, config.TEMP_LOG_DIR / config.DEFAULT_LOG_NAME)
    STATE.set_current_file("log", config.DEFAULT_LOG_NAME)
    STATE.reset_log_parse()
    STATE.reset_checks()
    STATE.save()
    return config.DEFAULT_LOG_NAME


def ensure_log_in_container(path: Path) -> None:
    docker_exec_simple(f"mkdir -p {config.LOG_DIR_CONTAINER}")
    docker_exec_simple(f"chown keystone:keystone {config.LOG_DIR_CONTAINER}")
    docker_exec_simple(f"chmod 750 {config.LOG_DIR_CONTAINER}")
    docker_cp_to_container(str(path), config.LOG_FILE_CONTAINER)
    docker_exec_simple(f"chown keystone:keystone {config.LOG_FILE_CONTAINER}")
    docker_exec_simple(f"chmod 640 {config.LOG_FILE_CONTAINER}")


def _read_container_csv(path: str) -> List[Dict[str, str]]:
    result = docker_exec_simple(f"cat {path}")
    if not result.ok:
        return []
    data = result.stdout
    reader = csv.DictReader(io.StringIO(data))
    return [row for row in reader]


def parse_rbac_log() -> Dict[str, List[Dict[str, str]]]:
    docker_exec(
        f"python {config.ROLEGRANT_SCRIPT}",
        user="admin",
        project="admin",
        use_base_env=True,
    )
    docker_exec(
        f"python {config.EXTRACT_RBAC_SCRIPT}",
        user="admin",
        project="admin",
        use_base_env=True,
    )

    rbac_rows = _read_container_csv("/root/policy-fileparser/data/assistfile/rbac_audit_keystone.csv")
    user_map_rows = _read_container_csv("/root/policy-fileparser/data/assistfile/userinfo.csv")
    project_map_rows = _read_container_csv("/root/policy-fileparser/data/assistfile/projectinfo.csv")

    user_map = {row.get("user_id"): row.get("user_name") for row in user_map_rows}
    project_map = {row.get("project_id"): row.get("project_name") for row in project_map_rows}

    parsed = []
    for row in rbac_rows:
        timestamp = (row.get("timestamp") or "").strip()
        if not timestamp or timestamp.startswith("#"):
            continue
        user_id = (row.get("user_id") or "").strip()
        project_id = (row.get("project_id") or "").strip()
        parsed.append(
            {
                "timestamp": timestamp,
                "api": row.get("api", ""),
                "user_name": user_map.get(user_id, user_id),
                "project_name": project_map.get(project_id, project_id),
                "authorized": row.get("authorized", ""),
            }
        )
    return {"rows": parsed}
