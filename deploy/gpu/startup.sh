#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
boot_id="$(cat /proc/sys/kernel/random/boot_id)"
boot_marker="/run/hemovet-gpu/reconciler-boot-id"
install -d -m 0755 /run/hemovet-gpu
reconcile_mode=()
if [[ ! -f $boot_marker || $(<"$boot_marker") != "$boot_id" ]]; then
  temporary_marker="$(mktemp /run/hemovet-gpu/.boot-id.XXXXXX)"
  printf '%s\n' "$boot_id" >"$temporary_marker"
  chmod 0600 "$temporary_marker"
  mv -f "$temporary_marker" "$boot_marker"
  reconcile_mode=(--boot)
fi
printf 'hemovet_gpu_startup=begin boot_id=%s boot_authorized=%s\n' \
  "$boot_id" "$([[ ${#reconcile_mode[@]} -eq 1 ]] && printf true || printf false)"
"$script_dir/configure-nvidia-runtime.sh"
"$script_dir/quarantine-legacy.sh"
"$script_dir/reconcile-release.sh" "${reconcile_mode[@]}"
printf 'hemovet_gpu_startup=ready boot_id=%s\n' "$boot_id"
