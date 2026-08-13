#!/usr/bin/env bash
set -Eeuo pipefail

readonly STATE_DIR="/var/lib/hemovet-gpu"
readonly FAILURE_STATE="$STATE_DIR/bootstrap-failure.json"
readonly FAILED_UNIT="${1:-hemovet-gpu.service}"

if [[ ${EUID} -ne 0 ]]; then
  printf 'ERROR: GPU failure shutdown must run as root\n' >&2
  exit 1
fi

install -d -m 0700 "$STATE_DIR"
temporary_state="$(mktemp "$STATE_DIR/.bootstrap-failure.XXXXXX")"
cleanup() {
  [[ -z ${temporary_state:-} ]] || rm -f "$temporary_state"
}
trap cleanup EXIT

boot_id="$(cat /proc/sys/kernel/random/boot_id 2>/dev/null || printf unknown)"
failed_at="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
printf '{"schema_version":"hemovet.gpu-bootstrap-failure/v1","state":"shutdown_requested","unit":"%s","boot_id":"%s","failed_at":"%s"}\n' \
  "$FAILED_UNIT" "$boot_id" "$failed_at" >"$temporary_state"
chmod 0600 "$temporary_state"
mv -f "$temporary_state" "$FAILURE_STATE"
temporary_state=""

printf 'gpu_bootstrap_failure=shutdown_requested unit=%s boot_id=%s\n' \
  "$FAILED_UNIT" "$boot_id"
sync
systemctl --no-block poweroff
