import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = PROJECT_ROOT / "Web"
TEMP_ROOT = WEB_ROOT / "TempFile"
TEMP_POLICY_DIR = TEMP_ROOT / "policy"
TEMP_LOG_DIR = TEMP_ROOT / "log"
STATE_FILE = TEMP_ROOT / "state.json"

SUDO_PASS_FILE = WEB_ROOT / "Backbone" / ".sudo_pass"

CONTAINER_NAME = "openstack-policy-detection"
DOCKER_ENV = {"DOCKER_HOST": "unix:///var/run/docker.sock"}

DEFAULT_POLICY_NAME = "OSpolicy.yaml"
DEFAULT_LOG_NAME = "OSkeystone.log"

POLICY_EXPORT_PATH = "/etc/keystone/keystone_policy.yaml"
POLICY_CONTAINER_PATH = "/etc/openstack/policies/policy.yaml"
POLICYSET_DIR_CONTAINER = "/etc/openstack/policies/PolicySet"
POLICY_EXPORT_CONTAINER_PATH = "/tmp/keystone_policy_export.yaml"
POLICY_IMPORT_CONTAINER_PATH = "/tmp/web_policy.yaml"
LOG_DIR_CONTAINER = "/var/log/keystone"
LOG_FILE_CONTAINER = "/var/log/keystone/keystone.log"

CURRENT_USER_SCRIPT = "/root/Tools/script/CurrentUserSet.sh"
OPENSTACK_INIT_SCRIPT = "/root/Tools/script/OpenStackInitial.sh"
POLICYSET_SCRIPT = "/root/Tools/Policyset.py"

PIPELINE_SCRIPT = "/root/policy-fileparser/run_graph_pipeline.py"
STAT_CHECK_SCRIPT = "/root/StatisticDetect/StatisticCheck.py"
STAT_UNKNOWN_SCRIPT = "/root/StatisticDetect/UnkownStatisticCheck.py"
DYNAMIC_CHECK_SCRIPT = "/root/DynamicDetect/Authorization_scope_check.py"
EXTRACT_RBAC_SCRIPT = "/root/Tools/extract_keystone_rbac.py"
ROLEGRANT_SCRIPT = "/root/Tools/RoleGrantInfo.py"

HOST_INITIAL_SCRIPT = str(PROJECT_ROOT / "Tools" / "script" / "HostInitial.sh")
HOST_KEYSTONE_RESTART_SCRIPT = str(PROJECT_ROOT / "Tools" / "script" / "keystoneRestart.sh")
HOST_POLICYSET_SCRIPT = str(PROJECT_ROOT / "Tools" / "script" / "PolicySet.sh")

TEMP_POLICY_DIR.mkdir(parents=True, exist_ok=True)
TEMP_LOG_DIR.mkdir(parents=True, exist_ok=True)
TEMP_ROOT.mkdir(parents=True, exist_ok=True)
