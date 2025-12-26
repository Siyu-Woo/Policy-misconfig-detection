#!/usr/bin/env bash
set -u

print_err() {
  printf "ERROR: %s\n" "$1"
}

usage() {
  cat <<'USAGE'
Usage:
  /root/Tools/script/OpenStackCLI.sh <number> [number...]

Numbers:
  0  openstack token issue
  1  openstack project list
  2  openstack user list
  3  openstack role list
  4  openstack service list
  5  openstack domain list
  6  openstack user set --email newmail@example.com --description "adminset2 member" member
  7  openstack project set --description "adminset proj" demo-project
  8  openstack user set --email newmail@example.com --description "readerset2 member" member
  9  openstack project set --description "readerset proj" demo-project
 10  openstack project list --long
 11  openstack user list --long
USAGE
}

if [ $# -eq 0 ] || [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 0
fi

exit_code=0
for idx in "$@"; do
  cmd=()
  case "$idx" in
    0) cmd=(openstack token issue) ;;
    1) cmd=(openstack project list) ;;
    2) cmd=(openstack user list) ;;
    3) cmd=(openstack role list) ;;
    4) cmd=(openstack service list) ;;
    5) cmd=(openstack domain list) ;;
    6) cmd=(openstack user set --email newmail@example.com --description "adminset2 member" member) ;;
    7) cmd=(openstack project set --description "adminset proj" demo-project) ;;
    8) cmd=(openstack user set --email newmail@example.com --description "readerset2 member" member) ;;
    9) cmd=(openstack project set --description "readerset proj" demo-project) ;;
    10) cmd=(openstack project list --long) ;;
    11) cmd=(openstack user list --long) ;;
    *)
      print_err "Unknown number: $idx"
      exit_code=1
      continue
      ;;
  esac

  printf "[RUN %s] %s\n" "$idx" "${cmd[*]}"
  if ! "${cmd[@]}"; then
    exit_code=1
  fi
done

exit "$exit_code"
