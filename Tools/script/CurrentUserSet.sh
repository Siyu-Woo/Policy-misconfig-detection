#!/usr/bin/env bash
set -u

print_ok() {
  printf "[OK] %s\n" "$1"
}

print_err() {
  printf "ERROR: %s\n" "$1"
}

usage() {
  cat <<'USAGE'
Usage:
  source /root/Tools/script/CurrentUserSet.sh [--user <admin|newuser|manager|member>] [--project <project>] [--domain <domain>]

Notes:
  - If no args, switches to admin.
  - If only --project is provided, only OS_PROJECT_NAME/OS_PROJECT_DOMAIN_NAME are updated.
USAGE
}

# Warn if not sourced
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  print_err "This script should be sourced to update current shell env"
  print_err "Example: source /root/Tools/script/CurrentUserSet.sh --user admin"
fi

USER_NAME=""
PROJECT_NAME=""
DOMAIN_NAME=""

while [ $# -gt 0 ]; do
  case "$1" in
    --user)
      USER_NAME="${2:-}"
      shift 2
      ;;
    --project)
      PROJECT_NAME="${2:-}"
      shift 2
      ;;
    --domain)
      DOMAIN_NAME="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      return 0 2>/dev/null || exit 0
      ;;
    *)
      print_err "Unknown option: $1"
      usage
      return 1 2>/dev/null || exit 1
      ;;
  esac
 done

if [ -z "$USER_NAME" ] && [ -z "$PROJECT_NAME" ] && [ -z "$DOMAIN_NAME" ]; then
  USER_NAME="admin"
fi

# Update user-related env vars if user is provided
if [ -n "$USER_NAME" ]; then
  case "$USER_NAME" in
    admin)
      export OS_USERNAME=admin
      export OS_PASSWORD=admin
      export OS_PROJECT_NAME=admin
      export OS_USER_DOMAIN_NAME=Default
      export OS_PROJECT_DOMAIN_NAME=Default
      export OS_AUTH_URL=http://localhost:5000/v3
      export OS_IDENTITY_API_VERSION=3
      export OS_IMAGE_API_VERSION=2
      export OS_INTERFACE=internal
      ;;
    newuser)
      export OS_USERNAME=newuser
      export OS_PASSWORD=MyPass123
      export OS_USER_DOMAIN_NAME=Default
      export OS_PROJECT_NAME=demo-project
      export OS_PROJECT_DOMAIN_NAME=Default
      export OS_AUTH_URL=http://127.0.0.1:5000/v3
      export OS_REGION_NAME=RegionOne
      ;;
    manager)
      export OS_AUTH_URL=http://127.0.0.1:5000/v3
      export OS_IDENTITY_API_VERSION=3
      export OS_REGION_NAME=RegionOne
      export OS_INTERFACE=internal
      export OS_USERNAME=manager
      export OS_PASSWORD=MyPass123
      export OS_USER_DOMAIN_NAME=Default
      export OS_PROJECT_NAME=demo-project
      export OS_PROJECT_DOMAIN_NAME=Default
      ;;
    member)
      export OS_AUTH_URL=http://127.0.0.1:5000/v3
      export OS_IDENTITY_API_VERSION=3
      export OS_REGION_NAME=RegionOne
      export OS_INTERFACE=internal
      export OS_USERNAME=member
      export OS_PASSWORD=MyPass123
      export OS_USER_DOMAIN_NAME=Default
      export OS_PROJECT_NAME=demo-project
      export OS_PROJECT_DOMAIN_NAME=Default
      ;;
    *)
      print_err "Unknown user: $USER_NAME"
      usage
      return 1 2>/dev/null || exit 1
      ;;
  esac
fi

# Update project-related env vars if project is provided
if [ -n "$PROJECT_NAME" ]; then
  export OS_PROJECT_NAME="$PROJECT_NAME"
  export OS_PROJECT_DOMAIN_NAME=Default
fi

if [ -n "$DOMAIN_NAME" ]; then
  export OS_USER_DOMAIN_NAME="$DOMAIN_NAME"
  export OS_PROJECT_DOMAIN_NAME="$DOMAIN_NAME"
fi

print_ok "Current user: ${OS_USERNAME:-unknown}"
print_ok "Current project: ${OS_PROJECT_NAME:-unknown}"
