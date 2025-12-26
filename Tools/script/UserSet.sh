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

ENVINFO_DIR="/root/policy-fileparser/data/assistfile/EnvInfo"

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
      cat <<'EOF'
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

EOF
    fi

    if openstack user show newuser >/dev/null 2>&1; then
      cat <<'EOF'
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

EOF
    fi

    if openstack user show manager >/dev/null 2>&1; then
      cat <<'EOF'
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

EOF
    fi

    if openstack user show member >/dev/null 2>&1; then
      cat <<'EOF'
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

EOF
    fi
  } > "$adminset"
}

usage() {
  cat <<'USAGE'
Usage:
  /root/Tools/script/UserSet.sh [--newuser] [--manager] [--member] [--user <name>] [--password <pwd>]
  /root/Tools/script/UserSet.sh --delete [--newuser] [--manager] [--member] [--user <name>]
  /root/Tools/script/UserSet.sh --list

If no user flags are provided, all three users will be handled.
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

# 2) Parse targets
TARGETS=()
MODE="create"
DO_LIST="no"
PASSWORD="MyPass123"
while [ $# -gt 0 ]; do
  case "$1" in
    --list)
      DO_LIST="yes"
      shift
      ;;
    --delete)
      MODE="delete"
      shift
      ;;
    --password)
      PASSWORD="${2:-}"
      shift 2
      ;;
    --user)
      if [ -z "${2:-}" ]; then
        print_err "--user requires a name"
        usage
        exit 1
      fi
      TARGETS+=("$2")
      shift 2
      ;;
    --newuser|--manager|--member)
      TARGETS+=("${1#--}")
      shift
      ;;
    *)
      print_err "Unknown option: $1"
      usage
      exit 1
      ;;
  esac
done

if [ ${#TARGETS[@]} -eq 0 ]; then
  TARGETS=("newuser" "manager" "member")
fi

show_user_info() {
  local user="$1"
  local name id
  name=$(openstack user show -f value -c name "$user" 2>/dev/null) || return 1
  id=$(openstack user show -f value -c id "$user" 2>/dev/null) || return 1
  printf "name=%s id=%s" "$name" "$id"
}

write_openrc() {
  local user="$1"
  local password="$2"
  local openrc_path="${ENVINFO_DIR}/${user}-openrc.sh"

  mkdir -p "$ENVINFO_DIR"
  cat <<EOF > "$openrc_path"
export OS_USERNAME=$user
export OS_PASSWORD=$password
export OS_USER_DOMAIN_NAME=Default
export OS_PROJECT_NAME=admin
export OS_PROJECT_DOMAIN_NAME=Default
export OS_AUTH_URL=http://127.0.0.1:5000/v3
export OS_REGION_NAME=RegionOne
EOF
}

create_user() {
  local user="$1"
  local password="$2"
  local domain="Default"

  if [ "$user" = "admin" ]; then
    print_err "Refuse to create admin user"
    return 1
  fi

  if info=$(show_user_info "$user"); then
    print_exist "User already exists: $info"
    return 2
  fi

  create_output=$(openstack user create --domain "$domain" --password "$password" "$user" 2>&1)
  if [ $? -ne 0 ]; then
    print_err "Failed to create user: $user"
    echo "$create_output"
    return 1
  fi

  if info=$(show_user_info "$user"); then
    print_create "$info"
    write_openrc "$user" "$password"
    return 0
  else
    print_err "User created but failed to fetch info: $user"
    return 1
  fi
}

delete_user() {
  local user="$1"

  if [ "$user" = "admin" ]; then
    print_err "Refuse to delete admin user"
    return 1
  fi

  if ! info=$(show_user_info "$user"); then
    print_err "User not found: $user"
    return 1
  fi

  delete_output=$(openstack user delete "$user" 2>&1)
  if [ $? -ne 0 ]; then
    print_err "Failed to delete user: $user"
    echo "$delete_output"
    return 1
  fi

  printf "[Delete] %s\n" "$info"
  if [ -f "${ENVINFO_DIR}/${user}-openrc.sh" ]; then
    rm -f "${ENVINFO_DIR}/${user}-openrc.sh"
  fi
}

DID_MUTATE="no"

if [ "$DO_LIST" = "yes" ]; then
  if openstack user list; then
    print_ok "User list completed"
  else
    print_err "Failed to list users"
  fi
else
for user in "${TARGETS[@]}"; do
  echo "---- $user ----"
  if [ "$MODE" = "delete" ]; then
    if delete_user "$user"; then
      DID_MUTATE="yes"
    fi
  else
    create_user "$user" "$PASSWORD"
    if [ $? -eq 0 ]; then
      DID_MUTATE="yes"
    fi
  fi
  echo ""
done
fi

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
