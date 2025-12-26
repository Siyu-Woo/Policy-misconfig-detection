#!/usr/bin/env bash
set -u

print_ok() {
  printf "[OK] %s\n" "$1"
}

print_exist() {
  printf "[Exist] %s\n" "$1"
}

print_create() {
  printf "[Create] %s\n" "$1"
}

print_err() {
  printf "ERROR: %s\n" "$1"
}

print_delete() {
  printf "[Delete] %s\n" "$1"
}

update_adminset() {
  local adminset="/root/Tools/AdminSet.md"
  local ts user_info role_info project_info

  ts=$(date '+%Y-%m-%d %H:%M:%S')
  user_info=$(openstack user list -f value -c Name -c ID 2>/dev/null | awk '{printf "- %s (id=%s)\n", $1, $2}')
  role_info=$(openstack role list -f value -c Name -c ID 2>/dev/null | awk '{printf "- %s (id=%s)\n", $1, $2}')
  project_info=$(openstack project list -f value -c Name -c ID 2>/dev/null | awk '{printf "- %s (id=%s)\n", $1, $2}')

  if [ -z "$user_info" ]; then
    user_info="- (none)"
  fi
  if [ -z "$role_info" ]; then
    role_info="- (none)"
  fi
  if [ -z "$project_info" ]; then
    project_info="- (none)"
  fi

  {
    printf "# 用户信息\n更新时间：%s\n%s\n\n" "$ts" "$user_info"
    printf "# 角色信息\n更新时间：%s\n%s\n\n" "$ts" "$role_info"
    printf "# 项目信息\n更新时间：%s\n%s\n\n" "$ts" "$project_info"
    printf "# 环境变量更新\n"

    if openstack user show admin >/dev/null 2>&1; then
      cat <<'EOF_ENV'
- admin（密码为 `admin`，默认域 Default，默认项目：admin）
  ```bash
  export OS_PASSWORD=admin
  export OS_PROJECT_NAME=admin
  export OS_USER_DOMAIN_NAME=Default
  export OS_PROJECT_DOMAIN_NAME=Default
  export OS_AUTH_URL=http://localhost:5000/v3
  export OS_IDENTITY_API_VERSION=3
  export OS_IMAGE_API_VERSION=2
  export OS_INTERFACE=internal
  ```
  ```bash
  source /opt/openstack/envinfo/admin-openrc.sh
  ```

EOF_ENV
    fi

    if openstack user show newuser >/dev/null 2>&1; then
      cat <<'EOF_ENV'
- newuser（默认域 Default，默认项目：demo-project）
  ```bash
  export OS_USERNAME=newuser
  export OS_PASSWORD=MyPass123
  export OS_USER_DOMAIN_NAME=Default
  export OS_PROJECT_NAME=demo-project
  export OS_PROJECT_DOMAIN_NAME=Default
  export OS_AUTH_URL=http://127.0.0.1:5000/v3
  export OS_REGION_NAME=RegionOne
  ```
  ```bash
  source /opt/openstack/envinfo/newuser-openrc.sh
  ```

EOF_ENV
    fi

    if openstack user show manager >/dev/null 2>&1; then
      cat <<'EOF_ENV'
- manager（默认域 Default，默认项目：demo-project）
  ```bash
  export OS_AUTH_URL=http://127.0.0.1:5000/v3
  export OS_IDENTITY_API_VERSION=3
  export OS_REGION_NAME=RegionOne
  export OS_INTERFACE=internal
  export OS_USERNAME=manager
  export OS_PASSWORD=MyPass123
  export OS_USER_DOMAIN_NAME=Default
  export OS_PROJECT_NAME=demo-project
  export OS_PROJECT_DOMAIN_NAME=Default
  ```
  ```bash
  source /opt/openstack/envinfo/manager-openrc.sh
  ```

EOF_ENV
    fi

    if openstack user show member >/dev/null 2>&1; then
      cat <<'EOF_ENV'
- member（默认域 Default，默认项目：demo-project）
  ```bash
  export OS_AUTH_URL=http://127.0.0.1:5000/v3
  export OS_IDENTITY_API_VERSION=3
  export OS_REGION_NAME=RegionOne
  export OS_INTERFACE=internal
  export OS_USERNAME=member
  export OS_PASSWORD=MyPass123
  export OS_USER_DOMAIN_NAME=Default
  export OS_PROJECT_NAME=demo-project
  export OS_PROJECT_DOMAIN_NAME=Default
  ```
  ```bash
  source /opt/openstack/envinfo/member-openrc.sh
  ```

EOF_ENV
    fi
  } > "$adminset"
}

usage() {
  cat <<'USAGE'
Usage:
  /root/Tools/script/RoleSet.sh [--role <name>]...
  /root/Tools/script/RoleSet.sh --delete [--role <name>]...
  /root/Tools/script/RoleSet.sh --list

If no roles are provided, defaults to: reader member manager
USAGE
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 0
fi

# 1) Check current OS_* env
echo "[INFO] Current OS_* env:"
env | grep '^OS_' || true
if [ "${OS_USERNAME:-}" != "admin" ]; then
  print_err "权限不足，需要切换admin"
  exit 1
fi
print_ok "Admin credentials confirmed"

# 2) Parse args
ROLES=()
MODE="create"
DO_LIST="no"
while [ $# -gt 0 ]; do
  case "$1" in
    --delete)
      MODE="delete"
      shift
      ;;
    --list)
      DO_LIST="yes"
      shift
      ;;
    --role)
      if [ -z "${2:-}" ]; then
        print_err "--role requires a name"
        usage
        exit 1
      fi
      ROLES+=("$2")
      shift 2
      ;;
    *)
      print_err "Unknown option: $1"
      usage
      exit 1
      ;;
  esac
 done

if [ "$DO_LIST" = "yes" ]; then
  if openstack role list; then
    print_ok "Role list completed"
  else
    print_err "Failed to list roles"
  fi
  exit 0
fi

if [ ${#ROLES[@]} -eq 0 ]; then
  ROLES=("reader" "member" "manager")
fi

show_role_info() {
  local role="$1"
  local name id
  name=$(openstack role show -f value -c name "$role" 2>/dev/null) || return 1
  id=$(openstack role show -f value -c id "$role" 2>/dev/null) || return 1
  printf "name=%s id=%s" "$name" "$id"
}

create_role() {
  local role="$1"

  if [ "$role" = "admin" ]; then
    print_err "Refuse to create admin role"
    return 1
  fi

  if info=$(show_role_info "$role"); then
    print_exist "$info"
    return 2
  fi

  create_output=$(openstack role create "$role" 2>&1)
  if [ $? -ne 0 ]; then
    print_err "Failed to create role: $role"
    echo "$create_output"
    return 1
  fi

  if info=$(show_role_info "$role"); then
    print_create "$info"
    return 0
  fi
  print_err "Role created but failed to fetch info: $role"
  return 1
}

delete_role() {
  local role="$1"

  if [ "$role" = "admin" ]; then
    print_err "Refuse to delete admin role"
    return 1
  fi

  if ! info=$(show_role_info "$role"); then
    print_err "Role not found: $role"
    return 1
  fi

  delete_output=$(openstack role delete "$role" 2>&1)
  if [ $? -ne 0 ]; then
    print_err "Failed to delete role: $role"
    echo "$delete_output"
    return 1
  fi

  print_delete "$info"
  return 0
}

DID_MUTATE="no"
for role in "${ROLES[@]}"; do
  echo "---- $role ----"
  if [ "$MODE" = "delete" ]; then
    if delete_role "$role"; then
      DID_MUTATE="yes"
    fi
  else
    create_role "$role"
    if [ $? -eq 0 ]; then
      DID_MUTATE="yes"
    fi
  fi
  echo ""
done

update_adminset
print_ok "AdminSet.md updated"

if [ "$DID_MUTATE" = "yes" ]; then
  if python /root/Tools/RoleGrantInfo.py >/dev/null 2>&1; then
    print_ok "Env info updated"
  else
    print_err "Failed to run /root/Tools/RoleGrantInfo.py"
    python /root/Tools/RoleGrantInfo.py
  fi
fi
