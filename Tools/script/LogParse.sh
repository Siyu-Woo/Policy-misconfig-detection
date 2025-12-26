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
  /root/Tools/script/LogParse.sh
  /root/Tools/script/LogParse.sh --clear-log
  /root/Tools/script/LogParse.sh --export-log <dir|file>
USAGE
}

EXPORT_DIR=""

while [ $# -gt 0 ]; do
  case "$1" in
    --clear-log)
      if python /root/Tools/extract_keystone_rbac.py --clear-log >/dev/null 2>&1; then
        print_ok "Keystone log cleared"
        exit 0
      else
        print_err "Failed to clear Keystone log"
        python /root/Tools/extract_keystone_rbac.py --clear-log
        exit 1
      fi
      ;;
    --export-log)
      EXPORT_DIR="${2:-}"
      if [ -z "$EXPORT_DIR" ]; then
        print_err "Missing export directory"
        usage
        exit 1
      fi
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

if python /root/Tools/RoleGrantInfo.py >/dev/null 2>&1; then
  print_ok "RoleGrantInfo updated"
else
  print_err "Failed to run /root/Tools/RoleGrantInfo.py"
  python /root/Tools/RoleGrantInfo.py
  exit 1
fi

if python /root/Tools/extract_keystone_rbac.py >/dev/null 2>&1; then
  print_ok "RBAC audit log extracted"
else
  print_err "Failed to run /root/Tools/extract_keystone_rbac.py"
  python /root/Tools/extract_keystone_rbac.py
  exit 1
fi

if [ -n "$EXPORT_DIR" ]; then
  EXPORT_PATH="$EXPORT_DIR"
  if [ "${EXPORT_DIR##*.}" = "log" ]; then
    EXPORT_PATH="$EXPORT_DIR"
    mkdir -p "$(dirname "$EXPORT_PATH")"
  else
    EXPORT_PATH="${EXPORT_DIR%/}/keystone.log"
    mkdir -p "$(dirname "$EXPORT_PATH")"
  fi
  if cp -a /var/log/keystone/keystone.log "$EXPORT_PATH"; then
    print_ok "Keystone log exported: $EXPORT_PATH"
  else
    print_err "Failed to export Keystone logs"
    exit 1
  fi
fi

echo "Output: /root/policy-fileparser/data/assistfile/rbac_audit_keystone.csv"
