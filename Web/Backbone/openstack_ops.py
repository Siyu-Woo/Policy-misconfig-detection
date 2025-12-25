import json
from typing import Dict, List

from .exec_utils import docker_exec


def _run_openstack_json(cmd: str) -> List[Dict[str, str]]:
    result = docker_exec(cmd, user="admin", project="admin", use_base_env=True)
    if not result.ok:
        return []
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return []


def collect_env_overview() -> Dict[str, List[Dict[str, str]]]:
    users = _run_openstack_json("openstack user list -f json")
    projects = _run_openstack_json("openstack project list -f json")
    domains = _run_openstack_json("openstack domain list -f json")
    return {"users": users, "projects": projects, "domains": domains}


def collect_env_options() -> Dict[str, List[str]]:
    overview = collect_env_overview()
    users = [item.get("Name") for item in overview.get("users", []) if item.get("Name")]
    projects = [item.get("Name") for item in overview.get("projects", []) if item.get("Name")]
    domains = [item.get("Name") for item in overview.get("domains", []) if item.get("Name")]
    users.sort()
    projects.sort()
    domains.sort()
    return {"users": users, "projects": projects, "domains": domains}
