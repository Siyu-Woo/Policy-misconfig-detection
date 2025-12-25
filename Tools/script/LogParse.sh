#!/usr/bin/env bash
set -u

print_ok() {
  printf "[OK] %s\n" "$1"
}

print_err() {
  printf "ERROR: %s\n" "$1"
}

if [ "${1:-}" = "--clear-log" ]; then
  if python /root/Tools/extract_keystone_rbac.py --clear-log >/dev/null 2>&1; then
    print_ok "Keystone log cleared"
    exit 0
  else
    print_err "Failed to clear Keystone log"
    python /root/Tools/extract_keystone_rbac.py --clear-log
    exit 1
  fi
fi

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

echo "Output: /root/policy-fileparser/data/assistfile/rbac_audit_keystone.csv"
