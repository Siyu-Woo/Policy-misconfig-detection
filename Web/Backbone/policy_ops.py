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


def list_policy_files() -> List[str]:
    return _list_files(config.TEMP_POLICY_DIR)


def choose_default_policy_file() -> Optional[str]:
    default = config.TEMP_POLICY_DIR / config.DEFAULT_POLICY_NAME
    if default.exists():
        return config.DEFAULT_POLICY_NAME
    files = list_policy_files()
    return files[0] if files else None


def _timestamped_name(prefix: str, suffix: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{stamp}{suffix}"


def export_policy() -> Dict[str, str]:
    result = docker_exec(
        f"python {config.POLICYSET_SCRIPT} export --dst {config.POLICY_EXPORT_CONTAINER_PATH}",
        user="admin",
        project="admin",
        use_base_env=True,
    )
    dest = config.TEMP_POLICY_DIR / config.DEFAULT_POLICY_NAME
    if not result.ok:
        return {"error": result.stderr.strip() or "export failed"}
    docker_cp_from_container(config.POLICY_EXPORT_CONTAINER_PATH, str(dest))

    backup_name = _timestamped_name("OSpolicy", ".yaml")
    shutil.copyfile(dest, config.TEMP_POLICY_DIR / backup_name)

    STATE.set_current_file("policy", config.DEFAULT_POLICY_NAME)
    STATE.reset_policy_parse()
    STATE.save()
    return {"file": config.DEFAULT_POLICY_NAME, "backup": backup_name}


def import_policy_file(filename: str, content: bytes) -> str:
    target = config.TEMP_POLICY_DIR / filename
    if target.exists():
        filename = _timestamped_name(Path(filename).stem or "policy", ".yaml")
        target = config.TEMP_POLICY_DIR / filename
    target.write_bytes(content)

    shutil.copyfile(target, config.TEMP_POLICY_DIR / config.DEFAULT_POLICY_NAME)
    STATE.set_current_file("policy", config.DEFAULT_POLICY_NAME)
    STATE.reset_policy_parse()
    STATE.reset_checks()
    STATE.save()
    return config.DEFAULT_POLICY_NAME


def apply_policy_to_container(host_file: str) -> Dict[str, str]:
    docker_cp_to_container(host_file, config.POLICY_IMPORT_CONTAINER_PATH)
    result = docker_exec(
        f"python {config.POLICYSET_SCRIPT} copy --src {config.POLICY_IMPORT_CONTAINER_PATH}",
        user="admin",
        project="admin",
        use_base_env=True,
    )
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}


def parse_policy_file(path: Path) -> List[Dict[str, str]]:
    content = path.read_text(encoding="utf-8", errors="ignore")
    rows = []
    for idx, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        name, rule = line.split(":", 1)
        name = name.strip().strip('"').strip("'")
        rule = rule.strip().strip('"').strip("'")
        if not name or not rule:
            continue
        rows.append({"line": idx, "name": name, "rule": rule})
    return rows


def ensure_policy_in_container(path: Path) -> None:
    docker_exec_simple("mkdir -p /etc/openstack/policies")
    docker_cp_to_container(str(path), config.POLICY_CONTAINER_PATH)


def run_policy_pipeline() -> str:
    result = docker_exec(
        f"python {config.PIPELINE_SCRIPT} --show-policy-statistic",
        user="admin",
        project="admin",
        use_base_env=True,
    )
    return result.stdout + ("\n" + result.stderr if result.stderr else "")


def restart_keystone() -> Dict[str, str]:
    result = docker_exec_simple("service apache2 restart")
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
