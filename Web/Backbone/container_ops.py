import re
from typing import Dict, Optional

from . import config
from .exec_utils import docker_container_status, docker_exec, docker_exec_simple, run_sudo
from .state import STATE


def get_container_status() -> Dict[str, str]:
    result = docker_container_status()
    status = result.stdout.strip() if result.ok else "unknown"
    return {
        "status": status,
        "error": result.stderr.strip() if not result.ok else "",
    }


def _parse_os_env(output: str) -> Dict[str, str]:
    env = {}
    for line in output.splitlines():
        line = line.strip()
        if not line.startswith("OS_"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key] = value.strip().strip('"')
    return env


def fetch_context(
    user: Optional[str] = None,
    project: Optional[str] = None,
    domain: Optional[str] = None,
) -> Dict[str, str]:
    cmd = "env | grep ^OS_"
    result = docker_exec(cmd, user=user, project=project, domain=domain, use_base_env=False)
    if not result.ok:
        return {
            "user": user or STATE.get("context", {}).get("user", "admin"),
            "project": project or STATE.get("context", {}).get("project", "admin"),
            "error": result.stderr.strip(),
        }
    env_map = _parse_os_env(result.stdout)
    context = {
        "user": env_map.get("OS_USERNAME", user or "admin"),
        "project": env_map.get("OS_PROJECT_NAME", project or "admin"),
        "domain": env_map.get("OS_USER_DOMAIN_NAME", env_map.get("OS_PROJECT_DOMAIN_NAME", "")),
        "scope": env_map.get("OS_SYSTEM_SCOPE", ""),
        "auth_url": env_map.get("OS_AUTH_URL", ""),
        "region": env_map.get("OS_REGION_NAME", ""),
    }
    STATE.update_context(context)
    STATE.save()
    return context


def switch_context(user: Optional[str], project: Optional[str], domain: Optional[str]) -> Dict[str, str]:
    return fetch_context(user=user, project=project, domain=domain)


def exec_terminal_command(command: str) -> Dict[str, str]:
    current = STATE.get("context", {})
    user = current.get("user")
    project = current.get("project")
    domain = current.get("domain")
    result = docker_exec(command, user=user, project=project, domain=domain, use_base_env=True)
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }


def restart_container() -> Dict[str, str]:
    logs = []

    def _run(label: str, cmd: list) -> bool:
        logs.append(f"== {label} ==")
        res = run_sudo(cmd, env=config.DOCKER_ENV)
        if res.stdout:
            logs.append(res.stdout.strip())
        if res.stderr:
            logs.append(res.stderr.strip())
        return res.ok

    _run("Host init", ["bash", config.HOST_INITIAL_SCRIPT])
    _run("Stop container", ["docker", "stop", config.CONTAINER_NAME])
    _run("Start container", ["docker", "start", config.CONTAINER_NAME])

    init_result = docker_exec_simple(f"{config.OPENSTACK_INIT_SCRIPT}")
    if init_result.stdout:
        logs.append(init_result.stdout.strip())
    if init_result.stderr:
        logs.append(init_result.stderr.strip())

    return {"log": "\n".join([line for line in logs if line])}
