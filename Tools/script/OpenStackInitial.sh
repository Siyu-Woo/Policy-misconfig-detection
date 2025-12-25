#!/usr/bin/env bash
set -u

print_ok() {
  printf "[OK] %s\n\n" "$1"
}

print_err() {
  printf "ERROR: %s\n\n" "$1"
}

retry_once() {
  local action="$1"
  local check_cmd="$2"

  eval "$action"
  if eval "$check_cmd"; then
    return 0
  fi
  return 1
}

# 1) Proxy env setup
if ! grep -q "http_proxy=\"http://172.17.0.1:20179\"" ~/.bashrc 2>/dev/null; then
  echo 'export http_proxy="http://172.17.0.1:20179"' >> ~/.bashrc
fi
if ! grep -q "https_proxy=\"http://172.17.0.1:20179\"" ~/.bashrc 2>/dev/null; then
  echo 'export https_proxy="http://172.17.0.1:20179"' >> ~/.bashrc
fi
if ! grep -q "no_proxy=\"localhost,127.0.0.1,::1\"" ~/.bashrc 2>/dev/null; then
  echo 'export no_proxy="localhost,127.0.0.1,::1"' >> ~/.bashrc
fi

# shellcheck disable=SC1090
set +u
source ~/.bashrc
set -u

if env | grep -q "http_proxy=http://172.17.0.1:20179" \
  && env | grep -q "https_proxy=http://172.17.0.1:20179" \
  && env | grep -q "no_proxy=localhost,127.0.0.1,::1"; then
  print_ok "Proxy env is set"
else
  # retry once by re-sourcing
  # shellcheck disable=SC1090
  set +u
  source ~/.bashrc
  set -u
  if env | grep -q "http_proxy=http://172.17.0.1:20179" \
    && env | grep -q "https_proxy=http://172.17.0.1:20179" \
    && env | grep -q "no_proxy=localhost,127.0.0.1,::1"; then
    print_ok "Proxy env is set (after re-source)"
  else
    print_err "Proxy env is not set; please re-run source ~/.bashrc"
  fi
fi

# 2) Load admin OpenStack env
set +u
if source /opt/openstack/envinfo/admin-openrc.sh >/dev/null 2>&1; then
  if env | grep -q '^OS_'; then
    print_ok "OpenStack admin env is loaded"
    env | grep '^OS_'
    echo ""
  else
    print_err "OpenStack admin env not found after sourcing"
  fi
else
  print_err "Failed to source /opt/openstack/envinfo/admin-openrc.sh"
fi
set -u

# 3) Service checks
ps aux | grep -E 'keystone|nova|glance|neutron|cinder|placement|apache|mysql|rabbitmq|memcached' >/dev/null 2>&1
print_ok "Process check command executed"

if service mysql status >/dev/null 2>&1; then
  print_ok "MySQL is running"
else
  echo "MySQL is not running; try restart once"
  if retry_once "service mysql restart" "service mysql status >/dev/null 2>&1"; then
    print_ok "MySQL is running after restart"
  else
    print_err "MySQL still not running after restart"
  fi
fi

if service rabbitmq-server status >/dev/null 2>&1; then
  print_ok "RabbitMQ is running"
else
  echo "RabbitMQ is not running; try restart once"
  if retry_once "service rabbitmq-server restart" "service rabbitmq-server status >/dev/null 2>&1"; then
    print_ok "RabbitMQ is running after restart"
  else
    print_err "RabbitMQ still not running after restart"
  fi
fi

if service apache2 status >/dev/null 2>&1; then
  if ss -lntp | grep -q ":5000"; then
    print_ok "Apache2 is running and listening on 5000"
  else
    print_err "Apache2 is running but 5000 is not listening"
  fi
else
  print_err "Apache2 is not running"
fi

http_code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5000/v3 || true)
if [ "$http_code" = "200" ]; then
  print_ok "Keystone endpoint returns 200"
else
  print_err "Keystone endpoint returned HTTP $http_code"
fi

# 4) OpenStack CLI checks
if openstack project list >/dev/null 2>&1; then
  print_ok "OpenStack project list succeeded"
else
  print_err "OpenStack project list failed"
fi

if openstack user list >/dev/null 2>&1; then
  print_ok "OpenStack user list succeeded"
else
  print_err "OpenStack user list failed"
fi

# 5) Conda + Neo4j
if [ -f /opt/miniconda/etc/profile.d/conda.sh ]; then
  # shellcheck disable=SC1091
  source /opt/miniconda/etc/profile.d/conda.sh
  if conda activate base >/dev/null 2>&1; then
    print_ok "Conda base environment is active"
  else
    print_err "Failed to activate conda base environment"
  fi
else
  print_err "Conda init script not found: /opt/miniconda/etc/profile.d/conda.sh"
fi

neo4j start >/dev/null 2>&1 || true
if neo4j status >/dev/null 2>&1; then
  print_ok "Neo4j is running"
else
  echo "Neo4j is not running; try start once"
  neo4j start >/dev/null 2>&1 || true
  if neo4j status >/dev/null 2>&1; then
    print_ok "Neo4j is running after restart"
  else
    print_err "Neo4j still not running"
  fi
fi

echo "Note: to apply admin credentials in the current shell, run:"
echo "source /opt/openstack/envinfo/admin-openrc.sh"
