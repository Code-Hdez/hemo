#!/usr/bin/env bash
set -Eeuo pipefail

readonly REGISTRY="us-central1-docker.pkg.dev"
readonly TOKEN_URL="http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
readonly EMAIL_URL="http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email"
readonly EXPECTED_SERVICE_ACCOUNT="hemovet-prod-runtime@project-5b36701c-f44f-4c03-a12.iam.gserviceaccount.com"
readonly DOCKER_CONFIG_DIRECTORY="${HEMOVET_PROD_DOCKER_CONFIG:-/run/hemovet-prod/docker-config}"

if [[ ${EUID} -ne 0 ]]; then
  printf 'ERROR: Artifact Registry authentication must run as root\n' >&2
  exit 1
fi

install -d -m 0700 "$DOCKER_CONFIG_DIRECTORY"
service_account="$(curl --fail --silent --show-error \
  --connect-timeout 3 --max-time 10 \
  --header 'Metadata-Flavor: Google' \
  "$EMAIL_URL")"
if [[ "$service_account" != "$EXPECTED_SERVICE_ACCOUNT" ]]; then
  printf 'ERROR: production runtime identity is not authorized\n' >&2
  exit 1
fi
token_json="$(curl --fail --silent --show-error \
  --connect-timeout 3 --max-time 10 \
  --header 'Metadata-Flavor: Google' \
  "$TOKEN_URL")"
access_token="$(jq --exit-status --raw-output \
  'select(.token_type == "Bearer") | .access_token | select(length > 20)' \
  <<<"$token_json")"
unset token_json

printf '%s' "$access_token" | DOCKER_CONFIG="$DOCKER_CONFIG_DIRECTORY" \
  docker login --username oauth2accesstoken --password-stdin "$REGISTRY" \
  >/dev/null
unset access_token
printf 'artifact_registry_auth=ok registry=%s credentials=metadata_token\n' \
  "$REGISTRY"
