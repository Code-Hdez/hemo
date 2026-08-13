#!/usr/bin/env bash
set -euo pipefail

readonly REGISTRY="us-central1-docker.pkg.dev"
readonly TOKEN_URL="http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"

if [[ ${EUID} -ne 0 ]]; then
  printf 'ERROR: Artifact Registry authentication must run as root\n' >&2
  exit 1
fi

docker_config_dir="${HEMOVET_GPU_DOCKER_CONFIG:-/run/hemovet-gpu/docker-config}"
install -d -m 0700 "$docker_config_dir"

token_json="$(curl --fail --silent --show-error \
  --connect-timeout 3 --max-time 10 \
  --header 'Metadata-Flavor: Google' \
  "$TOKEN_URL")"
access_token="$(jq --exit-status --raw-output \
  'select(.token_type == "Bearer") | .access_token | select(length > 20)' \
  <<<"$token_json")"
unset token_json

printf '%s' "$access_token" | DOCKER_CONFIG="$docker_config_dir" \
  docker login --username oauth2accesstoken --password-stdin "$REGISTRY" \
  >/dev/null
unset access_token
printf 'artifact_registry_auth=ok registry=%s credentials=metadata_token\n' "$REGISTRY"
