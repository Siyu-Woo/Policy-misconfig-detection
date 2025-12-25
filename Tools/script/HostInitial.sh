#!/usr/bin/env bash
set -u

PROJECT_DIR="/home/wusy/LabProj/CloudPolicy/Policy misconfig detection"
CONTAINER_NAME="openstack-policy-detection"

cd "$PROJECT_DIR" || exit 1

echo "[Host] Project dir: $PROJECT_DIR"
echo "[Host] Request sudo privileges (may prompt once)"
if ! sudo -v; then
  echo "[Host] ERROR: sudo authentication failed"
  exit 1
fi

echo "[Host] Ensure socat is available"
if ! command -v socat >/dev/null 2>&1; then
  echo "[Host] socat not found, installing via pip"
  pip install socat
fi

if ! sudo ss -lntp | grep -q ":20179"; then
  echo "[Host] Start socat on 20179"
  sudo nohup socat TCP-LISTEN:20179,fork,reuseaddr TCP:127.0.0.1:20171 \
    >/tmp/socat-20179.log 2>&1 &
  sleep 1
fi

if sudo ss -lntp | grep -q ":20179"; then
  echo "[Host] Port 20179 is listening"
else
  echo "[Host] ERROR: Port 20179 is not listening"
fi

export DOCKER_HOST=unix:///var/run/docker.sock
echo "Container is Ready"
echo "[Host] Initialization completed"
echo "Next: sudo docker start openstack-policy-detection"
echo "Then: sudo docker exec -it openstack-policy-detection bash"
