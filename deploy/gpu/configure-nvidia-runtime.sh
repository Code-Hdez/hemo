#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
  printf 'ERROR: NVIDIA runtime configuration must run as root\n' >&2
  exit 1
fi

install -d -m 0755 /etc/cdi
install -d -m 0755 /run/hemovet-gpu
temporary_cdi="$(mktemp /run/hemovet-gpu/nvidia-cdi.XXXXXX)"
staged_cdi="$(mktemp /etc/cdi/.hemovet-nvidia.XXXXXX.tmp)"
trap 'rm -f "$temporary_cdi" "$staged_cdi"' EXIT

# nvidia-ctk appends `.yaml` when --output does not already end with that
# suffix. A temporary file inside /etc/cdi can therefore become visible to
# CDI discovery before it is installed and make the registry ambiguous. Keep
# generation outside the discovery directory and install through a non-YAML
# staging name on the same filesystem so the final rename remains atomic.
nvidia-ctk cdi generate >"$temporary_cdi"
chmod 0644 "$temporary_cdi"
if [[ ! -f /etc/cdi/nvidia.yaml ]] || ! cmp --silent "$temporary_cdi" /etc/cdi/nvidia.yaml; then
  install -m 0644 "$temporary_cdi" "$staged_cdi"
  mv -f "$staged_cdi" /etc/cdi/nvidia.yaml
  printf 'nvidia_cdi=updated\n'
else
  printf 'nvidia_cdi=unchanged\n'
fi

# Remove only transient files emitted by the affected earlier HemoVet bundle.
# They are not valid installed specs and otherwise conflict with nvidia.yaml.
for stale_cdi in /etc/cdi/.nvidia.yaml.*.yaml; do
  [[ -e $stale_cdi ]] || continue
  rm -f -- "$stale_cdi"
done
nvidia-ctk cdi list | grep -F 'nvidia.com/gpu=all' >/dev/null
