#!/usr/bin/env bash
set -euo pipefail

readonly EXPECTED_OS="24.04"
readonly EXPECTED_DRIVER="580.159.03"
readonly EXPECTED_DOCKER="29.6.2"
readonly EXPECTED_COMPOSE="5.3.1"
readonly EXPECTED_TOOLKIT="1.17.8"

if [[ ${EUID} -ne 0 ]]; then
  printf 'ERROR: host validation must run as root\n' >&2
  exit 1
fi

# Fixed host path on the pinned Ubuntu image.
# shellcheck disable=SC1091
source /etc/os-release
[[ ${ID} == ubuntu && ${VERSION_ID} == "$EXPECTED_OS" ]] || {
  printf 'ERROR: expected Ubuntu %s\n' "$EXPECTED_OS" >&2
  exit 1
}

driver_version="$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | tr -d '[:space:]')"
gpu_name="$(nvidia-smi --query-gpu=name --format=csv,noheader | sed 's/[[:space:]]*$//')"
gpu_count="$(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l)"
[[ $driver_version == "$EXPECTED_DRIVER" ]] || {
  printf 'ERROR: NVIDIA driver mismatch: expected=%s actual=%s\n' "$EXPECTED_DRIVER" "$driver_version" >&2
  exit 1
}
[[ $gpu_count == 1 && ( $gpu_name == "NVIDIA L4" || $gpu_name == "NVIDIA A100-SXM4-40GB" ) ]] || {
  printf 'ERROR: exactly one approved GPU (NVIDIA L4 or A100-SXM4-40GB) is required\n' >&2
  exit 1
}
IFS=, read -r volatile_uncorrected_ecc aggregate_uncorrected_ecc < <(
  nvidia-smi \
    --query-gpu=ecc.errors.uncorrected.volatile.total,ecc.errors.uncorrected.aggregate.total \
    --format=csv,noheader,nounits
)
volatile_uncorrected_ecc="${volatile_uncorrected_ecc//[[:space:]]/}"
aggregate_uncorrected_ecc="${aggregate_uncorrected_ecc//[[:space:]]/}"
[[ $volatile_uncorrected_ecc =~ ^[0-9]+$ \
  && $aggregate_uncorrected_ecc =~ ^[0-9]+$ ]] || {
  printf 'ERROR: NVIDIA ECC counters are unavailable\n' >&2
  exit 1
}
((volatile_uncorrected_ecc == 0 && aggregate_uncorrected_ecc == 0)) || {
  printf 'ERROR: NVIDIA L4 reports uncorrectable ECC errors: volatile=%s aggregate=%s\n' \
    "$volatile_uncorrected_ecc" "$aggregate_uncorrected_ecc" >&2
  exit 1
}

docker_server="$(docker version --format '{{.Server.Version}}')"
compose_version="$(docker compose version --short)"
toolkit_version="$(nvidia-ctk --version | awk 'NR==1{print $NF}')"
[[ $docker_server == "$EXPECTED_DOCKER" ]] || {
  printf 'ERROR: Docker mismatch: expected=%s actual=%s\n' "$EXPECTED_DOCKER" "$docker_server" >&2
  exit 1
}
[[ $compose_version == "$EXPECTED_COMPOSE" ]] || {
  printf 'ERROR: Compose mismatch: expected=%s actual=%s\n' "$EXPECTED_COMPOSE" "$compose_version" >&2
  exit 1
}
[[ $toolkit_version == "$EXPECTED_TOOLKIT" ]] || {
  printf 'ERROR: NVIDIA Container Toolkit mismatch: expected=%s actual=%s\n' "$EXPECTED_TOOLKIT" "$toolkit_version" >&2
  exit 1
}

docker info --format '{{json .Runtimes}}' | jq --exit-status 'has("nvidia")' >/dev/null
printf 'host_runtime=valid os=%s driver=%s docker=%s compose=%s toolkit=%s gpu=%s uncorrectable_ecc=0\n' \
  "$VERSION_ID" "$driver_version" "$docker_server" "$compose_version" \
  "$toolkit_version" "${gpu_name// /_}"
