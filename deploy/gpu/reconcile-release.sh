#!/usr/bin/env bash
set -Eeuo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bundle_root="$(cd "$script_dir/../.." && pwd)"
readonly STATE_DIR="/var/lib/hemovet-gpu"
readonly RELEASES_DIR="$STATE_DIR/releases"
readonly APPLIED_MANIFEST="$STATE_DIR/applied-release.json"
readonly PREVIOUS_MANIFEST="$STATE_DIR/previous-release.json"
readonly PENDING_MANIFEST="$STATE_DIR/pending-release.json"
readonly FAILED_STATE="$STATE_DIR/failed-release.json"
readonly COMPOSE_FILE="$bundle_root/docker-compose.gpu.yml"
readonly CONTRACT="$script_dir/runtime_contract.py"
readonly BUNDLE_MANIFEST="$script_dir/bundle-manifest.sha256"
readonly METADATA_URL="http://metadata.google.internal/computeMetadata/v1/instance/attributes/hemovet-gpu-desired-release"
readonly DOCKER_CONFIG_DIR="/run/hemovet-gpu/docker-config"

boot_mode=0
manifest_source=""
while (($#)); do
  case "$1" in
    --boot) boot_mode=1; shift ;;
    --manifest-file) manifest_source="$2"; shift 2 ;;
    *) printf 'ERROR: unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
done
if [[ ${EUID} -ne 0 ]]; then
  printf 'ERROR: release reconciliation must run as root\n' >&2
  exit 1
fi

install -d -m 0700 "$STATE_DIR" "$RELEASES_DIR"
install -d -m 0755 /run/hemovet-gpu
exec 9>/run/lock/hemovet-gpu-reconcile.lock
flock --nonblock 9 || {
  printf 'ERROR: another GPU reconciliation is active\n' >&2
  exit 1
}

temporary_dir="$(mktemp -d "$STATE_DIR/.reconcile.XXXXXX")"
cleanup() {
  find "$DOCKER_CONFIG_DIR" -type f -delete 2>/dev/null || true
  rmdir "$DOCKER_CONFIG_DIR" 2>/dev/null || true
  find "$temporary_dir" -type f -delete 2>/dev/null || true
  rmdir "$temporary_dir" 2>/dev/null || true
}
trap cleanup EXIT

desired_manifest="$temporary_dir/desired.json"
if [[ -n $manifest_source ]]; then
  install -m 0600 "$manifest_source" "$desired_manifest"
else
  curl --fail --silent --show-error --connect-timeout 3 --max-time 10 \
    --header 'Metadata-Flavor: Google' "$METADATA_URL" \
    >"$desired_manifest"
  chmod 0600 "$desired_manifest"
fi

python3 "$CONTRACT" validate \
  --manifest "$desired_manifest" --bundle-manifest "$BUNDLE_MANIFEST"
desired_id="$(python3 "$CONTRACT" field --manifest "$desired_manifest" --bundle-manifest "$BUNDLE_MANIFEST" --name release_id)"
runtime_reference="$(python3 "$CONTRACT" field --manifest "$desired_manifest" --bundle-manifest "$BUNDLE_MANIFEST" --name runtime.reference)"
bind_address="$(curl --fail --silent --show-error \
  --connect-timeout 2 --max-time 5 --header 'Metadata-Flavor: Google' \
  'http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/ip')"

current_id=""
current_release_dir=""
if [[ -f $APPLIED_MANIFEST ]]; then
  current_id="$(python3 "$CONTRACT" historical-field \
    --manifest "$APPLIED_MANIFEST" --name release_id)"
  current_release_dir="$RELEASES_DIR/$current_id"
fi
running_container="$(docker ps --quiet \
  --filter name='^/hemovet-gpu-ollama-1$' --filter status=running)"
if [[ -n $current_id && $desired_id != "$current_id" \
  && -n $running_container && $boot_mode -ne 1 ]]; then
  install -m 0600 "$desired_manifest" "$PENDING_MANIFEST"
  printf 'release=deferred current=%s desired=%s reason=runtime_running\n' \
    "$current_id" "$desired_id"
  exit 0
fi

"$script_dir/validate-host.sh"
if [[ $desired_id == "$current_id" && -n $running_container ]]; then
  healthy=0
  for _ in $(seq 1 60); do
    health="$(docker inspect \
      --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
      hemovet-gpu-ollama-1 2>/dev/null || true)"
    if [[ $health == healthy ]]; then
      healthy=1
      break
    fi
    sleep 5
  done
  [[ $healthy == 1 ]] || {
    printf 'ERROR: existing Ollama health deadline exceeded\n' >&2
    exit 1
  }

  validation_arguments=(
    --manifest "$desired_manifest"
    --env-file "$current_release_dir/compose.env"
    --metrics-output "$STATE_DIR/last-validation.json"
  )
  validation_action="validate_only"
  if ((boot_mode)); then
    validation_arguments+=(--run-inference)
    validation_action="boot_inference"
  fi
  "$script_dir/validate-runtime.sh" "${validation_arguments[@]}"
  printf 'release=already_applied id=%s action=%s\n' \
    "$desired_id" "$validation_action"
  exit 0
fi

export HEMOVET_GPU_DOCKER_CONFIG="$DOCKER_CONFIG_DIR"
"$script_dir/authenticate-artifact-registry.sh"
pull_succeeded=0
for attempt in 1 2 3; do
  if DOCKER_CONFIG="$DOCKER_CONFIG_DIR" docker pull "$runtime_reference"; then
    pull_succeeded=1
    break
  fi
  printf 'runtime_pull=retry attempt=%s\n' "$attempt" >&2
  sleep $((attempt * 5))
done
[[ $pull_succeeded == 1 ]] || {
  printf 'ERROR: immutable runtime pull failed\n' >&2
  exit 1
}
docker image inspect "$runtime_reference" >/dev/null

release_dir="$RELEASES_DIR/$desired_id"
install -d -m 0700 "$release_dir"
install -m 0600 "$desired_manifest" "$release_dir/manifest.json"
python3 "$CONTRACT" render-env \
  --manifest "$release_dir/manifest.json" \
  --bundle-manifest "$BUNDLE_MANIFEST" \
  --bind-address "$bind_address" \
  --output "$release_dir/compose.env"

rollback_needed=1
recover_previous() {
  result=$?
  trap - ERR
  jq --null-input \
    --arg release_id "$desired_id" \
    --arg failed_at "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
    --argjson exit_code "$result" \
    '{release_id:$release_id,failed_at:$failed_at,exit_code:$exit_code,state:"boot_validation_failed"}' \
    >"$temporary_dir/failed.json"
  install -m 0600 "$temporary_dir/failed.json" "$FAILED_STATE"
  if [[ $rollback_needed == 1 ]]; then
    docker compose --project-name hemovet-gpu \
      --env-file "$release_dir/compose.env" -f "$COMPOSE_FILE" \
      down --remove-orphans >/dev/null 2>&1 || true
    if [[ -n $current_release_dir \
      && -f $current_release_dir/compose.env ]]; then
      docker compose --project-name hemovet-gpu \
        --env-file "$current_release_dir/compose.env" -f "$COMPOSE_FILE" \
        up -d --no-build --pull never ollama >/dev/null 2>&1 || true
    fi
  fi
  printf 'release=failed_closed id=%s previous=%s\n' \
    "$desired_id" "${current_id:-none}" >&2
  exit "$result"
}
trap recover_previous ERR

if [[ -n $running_container ]]; then
  docker compose --project-name hemovet-gpu \
    --env-file "$current_release_dir/compose.env" -f "$COMPOSE_FILE" \
    down --remove-orphans
fi
docker compose --project-name hemovet-gpu \
  --env-file "$release_dir/compose.env" -f "$COMPOSE_FILE" \
  up -d --no-build --pull never ollama

healthy=0
for _ in $(seq 1 60); do
  health="$(docker inspect \
    --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
    hemovet-gpu-ollama-1 2>/dev/null || true)"
  if [[ $health == healthy ]]; then
    healthy=1
    break
  fi
  sleep 5
done
[[ $healthy == 1 ]] || {
  printf 'ERROR: Ollama health deadline exceeded\n' >&2
  false
}

docker compose --project-name hemovet-gpu \
  --env-file "$release_dir/compose.env" -f "$COMPOSE_FILE" \
  run --rm --no-deps ollama_setup
"$script_dir/validate-runtime.sh" \
  --manifest "$release_dir/manifest.json" \
  --env-file "$release_dir/compose.env" \
  --metrics-output "$release_dir/validation.json" \
  --run-inference

if [[ -f $APPLIED_MANIFEST ]]; then
  install -m 0600 "$APPLIED_MANIFEST" "$PREVIOUS_MANIFEST"
fi
install -m 0600 "$release_dir/manifest.json" "$APPLIED_MANIFEST"
install -m 0600 "$release_dir/validation.json" \
  "$STATE_DIR/last-validation.json"
rm -f "$PENDING_MANIFEST" "$FAILED_STATE"
rollback_needed=0
printf 'release=applied id=%s state=validated\n' "$desired_id"
