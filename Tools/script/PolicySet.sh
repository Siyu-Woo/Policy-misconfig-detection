#!/usr/bin/env bash
set -u

CONTAINER_NAME="openstack-policy-detection"
POLICY_DIR_CONTAINER="/etc/openstack/policies/PolicySet"
POLICYSET_SCRIPT="/root/Tools/Policyset.py"
HOST_POLICY_DIR="/home/wusy/LabProj/CloudPolicy/Policy misconfig detection/data/policy file/PolicySet"

print_ok() {
  printf "[OK] %s\n" "$1"
}

print_err() {
  printf "[Error] %s\n" "$1"
}

# 1) Validate exactly one policy file in container
mapfile -t policy_files < <(sudo docker exec -i "$CONTAINER_NAME" bash -lc "ls -1 ${POLICY_DIR_CONTAINER}/*.yaml 2>/dev/null")

if [ ${#policy_files[@]} -ne 1 ]; then
  print_err "Check the ${HOST_POLICY_DIR}"
  exit 1
fi

policy_file="${policy_files[0]}"

# 2) Copy policy into keystone policy file via Policyset.py
if sudo docker exec -i "$CONTAINER_NAME" bash -lc "source /opt/miniconda/etc/profile.d/conda.sh && conda activate base && python ${POLICYSET_SCRIPT} copy --src \"${policy_file}\""; then
  print_ok "Policy file copied"
else
  print_err "Failed to copy policy file"
  exit 1
fi

# 3) Restart Keystone/apache2 (host)
if ! sudo /home/wusy/LabProj/CloudPolicy/Policy\ misconfig\ detection/Tools/script/keystoneRestart.sh; then
  print_err "Failed to restart Keystone/apache2"
  exit 1
fi

print_ok "policy already set"
