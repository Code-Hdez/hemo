#!/usr/bin/env bash
set -euo pipefail

readonly STATE_DIR="/var/lib/hemovet-gpu"
readonly INVENTORY="$STATE_DIR/legacy-runtime-before.tsv"
readonly -a LEGACY_PROJECTS=("hemogramas-proyectoicc" "hemovet-deploy")

if [[ ${EUID} -ne 0 ]]; then
  printf 'ERROR: legacy quarantine must run as root\n' >&2
  exit 1
fi
install -d -m 0700 "$STATE_DIR"

if [[ ! -f $INVENTORY ]]; then
  temporary_inventory="$(mktemp "$STATE_DIR/.legacy-runtime-before.XXXXXX")"
  chmod 0600 "$temporary_inventory"
  printf 'kind\tname\timage_or_enabled\tstatus\trestart_policy\n' \
    >"$temporary_inventory"
  for project in "${LEGACY_PROJECTS[@]}"; do
    while IFS= read -r container_id; do
      [[ -n $container_id ]] || continue
      docker inspect --format 'container\t{{.Name}}\t{{.Config.Image}}\t{{.State.Status}}\t{{.HostConfig.RestartPolicy.Name}}' \
        "$container_id" >>"$temporary_inventory"
    done < <(
      docker ps --all --quiet \
        --filter "label=com.docker.compose.project=$project"
    )
  done
  printf 'service\tollama.service\t%s\t%s\t-\n' \
    "$(systemctl is-enabled ollama.service 2>/dev/null || true)" \
    "$(systemctl is-active ollama.service 2>/dev/null || true)" \
    >>"$temporary_inventory"
  mv -f "$temporary_inventory" "$INVENTORY"
fi

if systemctl list-unit-files ollama.service --no-legend 2>/dev/null \
  | grep -q '^ollama.service'; then
  systemctl disable --now ollama.service >/dev/null
  printf 'legacy_host_ollama=disabled\n'
fi

for project in "${LEGACY_PROJECTS[@]}"; do
  while IFS= read -r container_id; do
    [[ -n $container_id ]] || continue
    container_name="$(docker inspect --format '{{.Name}}' "$container_id")"
    docker update --restart=no "$container_id" >/dev/null
    if [[ $(docker inspect --format '{{.State.Running}}' "$container_id") == true ]]; then
      docker stop --time 60 "$container_id" >/dev/null
    fi
    printf 'legacy_container=quarantined name=%s\n' "$container_name"
  done < <(
    docker ps --all --quiet \
      --filter "label=com.docker.compose.project=$project"
  )
done
