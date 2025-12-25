#!/usr/bin/env bash
set -u

CONTAINER_NAME="openstack-policy-detection"

print_ok() {
  printf "[OK] %s\n\n" "$1"
}

print_err() {
  printf "ERROR: %s\n\n" "$1"
}

echo "[Host] Stopping supervisor/apache2 inside container"
if sudo docker exec -i "$CONTAINER_NAME" bash -lc "service supervisor stop 2>/dev/null || true; service apache2 stop"; then
  print_ok "Container services stopped"
else
  print_err "Failed to stop services inside container"
fi

print_ok "Keystone restart steps completed"
if ! sudo /home/wusy/LabProj/CloudPolicy/Policy\ misconfig\ detection/Tools/script/HostInitial.sh; then
  print_err "Host initialization failed"
  exit 1
fi
