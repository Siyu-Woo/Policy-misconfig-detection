#!/usr/bin/env bash
set -u

print_ok() {
  printf "[OK] %s\n" "$1"
}

print_err() {
  printf "ERROR: %s\n" "$1"
}

print_info() {
  printf "%s\n" "$1"
}

usage() {
  cat <<'USAGE'
Usage:
  /root/Tools/script/RoleGrant.sh --add --user <user> --project <project> --role <role>
  /root/Tools/script/RoleGrant.sh --remove --user <user> --project <project> --role <role>
  /root/Tools/script/RoleGrant.sh --list --user <user> --project <project>

Examples:
  /root/Tools/script/RoleGrant.sh --add --user newuser --project demo-project --role reader
  /root/Tools/script/RoleGrant.sh --remove --user newuser --project demo-project --role reader
USAGE
}

MODE=""
USER_NAME=""
PROJECT_NAME=""
ROLE_NAME=""
DO_LIST="no"

while [ $# -gt 0 ]; do
  case "$1" in
    --add)
      MODE="add"
      shift
      ;;
    --remove)
      MODE="remove"
      shift
      ;;
    --list)
      DO_LIST="yes"
      shift
      ;;
    --user)
      USER_NAME="${2:-}"
      shift 2
      ;;
    --project)
      PROJECT_NAME="${2:-}"
      shift 2
      ;;
    --role)
      ROLE_NAME="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      print_err "Unknown option: $1"
      usage
      exit 1
      ;;
  esac
 done

if [ -z "$USER_NAME" ]; then
  print_err "Missing --user"
  usage
  exit 1
fi
if [ -z "$PROJECT_NAME" ]; then
  print_err "Missing --project"
  usage
  exit 1
fi
if [ "$DO_LIST" = "no" ] && [ -z "$ROLE_NAME" ]; then
  print_err "Missing --role"
  usage
  exit 1
fi
if [ "$DO_LIST" = "no" ] && [ -z "$MODE" ]; then
  print_err "Missing --add or --remove"
  usage
  exit 1
fi

# 1) Load admin credentials
if ! source /opt/openstack/envinfo/admin-openrc.sh >/dev/null 2>&1; then
  print_err "Failed to source /opt/openstack/envinfo/admin-openrc.sh"
  exit 1
fi
print_ok "Admin credentials loaded"

# 2) Grant or revoke role
if [ "$DO_LIST" = "yes" ]; then
  if openstack role assignment list --user "$USER_NAME" --project "$PROJECT_NAME" --names; then
    print_ok "Role assignment list completed"
  else
    print_err "Failed to list role assignments"
  fi
  exit 0
elif [ "$MODE" = "add" ]; then
  if openstack role assignment list --user "$USER_NAME" --project "$PROJECT_NAME" --names -f value -c Role 2>/dev/null | grep -qx "$ROLE_NAME"; then
    print_info "[Exist] role already granted"
  else
    if openstack role add --user "$USER_NAME" --project "$PROJECT_NAME" "$ROLE_NAME" >/dev/null 2>&1; then
      print_ok "Role granted"
    else
      print_err "Failed to grant role"
      openstack role add --user "$USER_NAME" --project "$PROJECT_NAME" "$ROLE_NAME"
      exit 1
    fi
  fi
else
  if openstack role assignment list --user "$USER_NAME" --project "$PROJECT_NAME" --names -f value -c Role 2>/dev/null | grep -qx "$ROLE_NAME"; then
    if openstack role remove --user "$USER_NAME" --project "$PROJECT_NAME" "$ROLE_NAME" >/dev/null 2>&1; then
      print_ok "Role revoked"
    else
      print_err "Failed to revoke role"
      openstack role remove --user "$USER_NAME" --project "$PROJECT_NAME" "$ROLE_NAME"
      exit 1
    fi
  else
    print_info "Not grant"
  fi
fi

# 3) Update assistfile info
if python /root/Tools/RoleGrantInfo.py >/dev/null 2>&1; then
  print_ok "RoleGrantInfo updated"
  print_info "Updated: /root/policy-fileparser/data/assistfile/rbac_audit_keystone.csv"
else
  print_err "Failed to run /root/Tools/RoleGrantInfo.py"
  python /root/Tools/RoleGrantInfo.py
fi
