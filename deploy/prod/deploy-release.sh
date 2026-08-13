#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_NAME="hemogramas-proyectoicc"
RELEASES_ROOT="/opt/hemovet-prod/releases"
CURRENT_LINK="/opt/hemovet-prod/current"
PREVIOUS_LINK="/opt/hemovet-prod/previous"
STATE_ROOT="/var/lib/hemovet-prod"
ACTIVE_ENV="$STATE_ROOT/.env"
LOCK_FILE="/run/lock/hemovet-prod-deploy.lock"
DOCKER_CONFIG_DIRECTORY="/run/hemovet-prod/docker-config"
readonly ISOLATED_SENTINEL_CONTENT="hemovet.isolated-deployment/v1"

archive=""
manifest=""
candidate=""
isolated_root=""
while (($#)); do
  case "$1" in
    --archive) archive="$2"; shift 2 ;;
    --release-manifest) manifest="$2"; shift 2 ;;
    --candidate-environment) candidate="$2"; shift 2 ;;
    --isolated-root) isolated_root="$2"; shift 2 ;;
    *) printf 'ERROR: unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
done

if [[ -n "$isolated_root" ]]; then
  if [[ ${HEMOVET_ALLOW_ISOLATED_DEPLOY_TEST:-0} != "1" ]]; then
    printf 'ERROR: isolated deployment validation was not explicitly enabled\n' >&2
    exit 1
  fi
  isolated_root="$(realpath --canonicalize-existing -- "$isolated_root")"
  if [[ ! "$isolated_root" =~ ^/tmp/hemovet-stage9-rollback\.[A-Za-z0-9_-]+$ \
    || -L "$isolated_root" \
    || "$(stat -c '%u' "$isolated_root")" != "$EUID" \
    || "$(stat -c '%a' "$isolated_root")" != "700" \
    || ! -f "$isolated_root/.hemovet-isolated-deploy-test" \
    || -L "$isolated_root/.hemovet-isolated-deploy-test" \
    || "$(<"$isolated_root/.hemovet-isolated-deploy-test")" \
      != "$ISOLATED_SENTINEL_CONTENT" ]]; then
    printf 'ERROR: unsafe isolated deployment root\n' >&2
    exit 1
  fi
  PROJECT_NAME="hemovet-stage9-${BASHPID}"
  RELEASES_ROOT="$isolated_root/opt/hemovet-prod/releases"
  CURRENT_LINK="$isolated_root/opt/hemovet-prod/current"
  PREVIOUS_LINK="$isolated_root/opt/hemovet-prod/previous"
  STATE_ROOT="$isolated_root/var/lib/hemovet-prod"
  ACTIVE_ENV="$STATE_ROOT/.env"
  LOCK_FILE="$isolated_root/run/lock/hemovet-prod-deploy.lock"
  DOCKER_CONFIG_DIRECTORY="$isolated_root/run/hemovet-prod/docker-config"
  export HEMOVET_ISOLATED_DEPLOY_ROOT="$isolated_root"
elif [[ ${EUID} -ne 0 ]]; then
  printf 'ERROR: production deployment must run as root\n' >&2
  exit 1
fi
readonly PROJECT_NAME RELEASES_ROOT CURRENT_LINK PREVIOUS_LINK STATE_ROOT
readonly ACTIVE_ENV LOCK_FILE DOCKER_CONFIG_DIRECTORY
for required in "$archive" "$manifest" "$candidate"; do
  if [[ -z "$required" || ! -f "$required" || -L "$required" ]]; then
    printf 'ERROR: deployment input is missing or unsafe\n' >&2
    exit 1
  fi
done

install -d -m 0700 "$(dirname "$LOCK_FILE")"
exec 9>"$LOCK_FILE"
if ! flock --nonblock 9; then
  printf 'ERROR: another production deployment is active\n' >&2
  exit 1
fi

umask 077
release_id="$(jq -er '.release_id' "$manifest")"
if ! [[ "$release_id" =~ ^[0-9a-f]{40}$ ]]; then
  printf 'ERROR: invalid release id\n' >&2
  exit 1
fi
release_root="$RELEASES_ROOT/$release_id"
release_source="$release_root/source"
release_manifest="$release_root/release-manifest.json"
release_candidate="$release_root/candidate.env"
transaction_root="$STATE_ROOT/transactions/$release_id"
attempt_id="$(date -u '+%Y%m%dT%H%M%S.%NZ')-${BASHPID}"
transaction_dir="$transaction_root/$attempt_id"
install -d -m 0755 "$RELEASES_ROOT"
install -d -m 0700 "$STATE_ROOT" "$STATE_ROOT/transactions"
staging_root="$(mktemp -d "$RELEASES_ROOT/.${release_id}.XXXXXX")"
previous_source=""
environment_installed=0
current_switched=0
links_started=0
previous_link_existed=0
previous_link_value=""

cleanup() {
  if [[ -d "$staging_root" ]]; then
    rm -r -- "$staging_root"
  fi
  if [[ -d "$DOCKER_CONFIG_DIRECTORY" ]]; then
    rm -r -- "$DOCKER_CONFIG_DIRECTORY"
  fi
}

compose() {
  local source="$1"
  local environment="$2"
  shift 2
  DOCKER_CONFIG="$DOCKER_CONFIG_DIRECTORY" docker compose \
    --project-name "$PROJECT_NAME" \
    --project-directory "$source" \
    --env-file "$environment" \
    -f "$source/docker-compose.yml" \
    -f "$source/docker-compose.prod.yml" "$@"
}

validate_payload() {
  local source="$1"
  local manifest_path="$2"
  local environment="$3"
  if [[ -n "$isolated_root" ]]; then
    PYTHONPATH="$source/backend" python3 \
      "$source/backend/scripts/validate_release_payload.py" \
      --release-manifest "$manifest_path" \
      --environment "$environment" \
      --source-root "$source"
    return
  fi

  local backend_reference
  backend_reference="$(jq -er \
    '.application.backend.reference | select(test("^[^[:space:]@]+@sha256:[0-9a-f]{64}$"))' \
    "$manifest_path")"
  if ! DOCKER_CONFIG="$DOCKER_CONFIG_DIRECTORY" \
    docker image inspect "$backend_reference" >/dev/null 2>&1
  then
    DOCKER_CONFIG="$DOCKER_CONFIG_DIRECTORY" docker pull "$backend_reference"
  fi
  DOCKER_CONFIG="$DOCKER_CONFIG_DIRECTORY" docker run --rm \
    --network none \
    --read-only \
    --cap-drop ALL \
    --security-opt no-new-privileges=true \
    --user 0:0 \
    --tmpfs /tmp:rw,noexec,nosuid,size=16m \
    --env PYTHONPATH=/release/source/backend \
    --env PYTHONDONTWRITEBYTECODE=1 \
    --mount "type=bind,source=$source,target=/release/source,readonly" \
    --mount "type=bind,source=$manifest_path,target=/release/release-manifest.json,readonly" \
    --mount "type=bind,source=$environment,target=/release/candidate.env,readonly" \
    --entrypoint python \
    "$backend_reference" \
    /release/source/backend/scripts/validate_release_payload.py \
    --release-manifest /release/release-manifest.json \
    --environment /release/candidate.env \
    --source-root /release/source
}

rollback_on_failure() {
  local status=$?
  local rollback_failed=0
  trap - ERR EXIT
  if [[ "$status" -eq 0 ]]; then
    cleanup
    return 0
  fi
  printf 'ERROR: immutable deployment failed; starting bounded rollback\n' >&2
  if [[ "$environment_installed" == "1" ]]; then
    if ! PYTHONPATH="$release_source/backend" python3 \
      "$release_source/backend/scripts/manage_deploy_env.py" rollback \
      --active-env "$ACTIVE_ENV" \
      --transaction-dir "$transaction_dir" >/dev/null
    then
      printf 'CRITICAL: complete environment rollback failed\n' >&2
      rollback_failed=1
    fi
  fi
  if [[ "$current_switched" == "1" && -n "$previous_source" ]]; then
    temporary_link="${CURRENT_LINK}.rollback"
    rm -f -- "$temporary_link"
    ln -s "$previous_source" "$temporary_link"
    mv -Tf "$temporary_link" "$CURRENT_LINK"
  fi
  if [[ "$links_started" == "1" ]]; then
    temporary_previous="${PREVIOUS_LINK}.rollback"
    rm -f -- "$temporary_previous"
    if [[ "$previous_link_existed" == "1" ]]; then
      ln -s "$previous_link_value" "$temporary_previous"
      mv -Tf "$temporary_previous" "$PREVIOUS_LINK"
    else
      rm -f -- "$PREVIOUS_LINK"
    fi
  fi
  if [[ "$current_switched" == "1" && -n "$previous_source" ]]; then
    if [[ "$rollback_failed" == "0" \
      && -f "$previous_source/docker-compose.yml" \
      && -f "$ACTIVE_ENV" ]]; then
      if ! compose "$previous_source" "$ACTIVE_ENV" up -d --no-build; then
        printf 'CRITICAL: previous Compose revision did not restart\n' >&2
        rollback_failed=1
      fi
    fi
  fi
  cleanup
  if [[ "$rollback_failed" == "1" ]]; then
    printf 'rollback=failed original_status=%s\n' "$status" >&2
    exit 70
  fi
  printf 'rollback=completed original_status=%s transaction=%s\n' \
    "$status" "$attempt_id" >&2
  exit "$status"
}
trap rollback_on_failure ERR EXIT

mkdir -p "$staging_root/source"
tar --extract --gzip --file "$archive" --directory "$staging_root/source" \
  --no-same-owner --no-same-permissions
# The deployment umask deliberately protects the candidate environment and
# manifest, but the tracked source tree is mounted read-only into containers
# that run without root privileges. Normalize only that source tree to
# non-executable files and traversable directories; private deployment inputs
# remain mode 0600 below.
find "$staging_root/source" -type d -exec chmod 0755 {} +
find "$staging_root/source" -type f -exec chmod 0644 {} +
install -m 0600 "$manifest" "$staging_root/release-manifest.json"
install -m 0600 "$candidate" "$staging_root/candidate.env"

export HEMOVET_PROD_DOCKER_CONFIG="$DOCKER_CONFIG_DIRECTORY"
install -d -m 0700 "$DOCKER_CONFIG_DIRECTORY"
if [[ -n "$isolated_root" ]]; then
  printf 'artifact_registry_auth=isolated_validation credentials=none\n'
else
  bash "$staging_root/source/deploy/prod/authenticate-artifact-registry.sh"
fi
validate_payload \
  "$staging_root/source" \
  "$staging_root/release-manifest.json" \
  "$staging_root/candidate.env"

if [[ -e "$release_root" ]]; then
  if ! cmp -s "$release_root/release-manifest.json" \
    "$staging_root/release-manifest.json"
  then
    printf 'ERROR: immutable release directory already differs\n' >&2
    exit 1
  fi
  rm -r -- "$staging_root"
else
  chmod 0755 "$staging_root" "$staging_root/source"
  mv "$staging_root" "$release_root"
fi

if [[ -L "$CURRENT_LINK" ]]; then
  previous_source="$(readlink -f "$CURRENT_LINK")"
else
  previous_source="$(docker ps --filter label=com.docker.compose.service=backend \
    --format '{{.ID}}' | head -n 1 | xargs -r docker inspect \
    --format '{{ index .Config.Labels "com.docker.compose.project.working_dir" }}')"
fi
if [[ -z "$previous_source" || ! -d "$previous_source" ]]; then
  printf 'ERROR: previous production source cannot be resolved\n' >&2
  exit 1
fi

if [[ ! -f "$ACTIVE_ENV" ]]; then
  if [[ ! -f "$previous_source/.env" ]]; then
    printf 'ERROR: previous production environment cannot be resolved\n' >&2
    exit 1
  fi
  install -m 0600 "$previous_source/.env" "$ACTIVE_ENV"
fi

compose "$release_source" "$release_candidate" config --quiet
compose "$release_source" "$release_candidate" pull
chroma_id="$(compose "$release_source" "$release_candidate" ps -q chroma)"
if [[ -z "$chroma_id" ]]; then
  printf 'ERROR: existing production Chroma service is not running\n' >&2
  exit 1
fi
if [[ "$(docker inspect --format '{{.State.Health.Status}}' "$chroma_id")" != "healthy" ]]; then
  printf 'ERROR: existing production Chroma service is not healthy\n' >&2
  exit 1
fi

target_collection="$(jq -er '.rag.collection_name' "$release_manifest")"
if ! compose "$release_source" "$release_candidate" run --rm --no-deps \
  rag_ingest python scripts/ingest_rag.py index --validate-only
then
  promotion_json="$release_root/rag-promotion.json"
  compose "$release_source" "$release_candidate" run --rm --no-deps \
    rag_ingest python scripts/ingest_rag.py index \
    --collection hemovet_canine_hematology_v2 --stage --prune \
    >"$promotion_json"
  promoted_candidate="$release_root/candidate.promoted.env"
  PYTHONPATH="$release_source/backend" python3 \
    "$release_source/backend/scripts/prepare_rag_promotion.py" \
    --promotion-json "$promotion_json" \
    --source-env "$release_candidate" \
    --target-env "$promoted_candidate" >/dev/null
  install -m 0600 "$promoted_candidate" "$release_candidate"
  compose "$release_source" "$release_candidate" run --rm --no-deps \
    rag_ingest python scripts/ingest_rag.py index --validate-only
fi

validate_payload "$release_source" "$release_manifest" "$release_candidate"

PYTHONPATH="$release_source/backend" python3 \
  "$release_source/backend/scripts/manage_deploy_env.py" install \
  --candidate-env "$release_candidate" \
  --active-env "$ACTIVE_ENV" \
  --transaction-dir "$transaction_dir" \
  --expected-collection "$target_collection" >/dev/null
environment_installed=1

temporary_previous="${PREVIOUS_LINK}.next"
temporary_current="${CURRENT_LINK}.next"
if [[ -L "$PREVIOUS_LINK" ]]; then
  previous_link_existed=1
  previous_link_value="$(readlink "$PREVIOUS_LINK")"
fi
links_started=1
rm -f -- "$temporary_previous" "$temporary_current"
ln -s "$previous_source" "$temporary_previous"
mv -Tf "$temporary_previous" "$PREVIOUS_LINK"
ln -s "$release_source" "$temporary_current"
mv -Tf "$temporary_current" "$CURRENT_LINK"
current_switched=1

compose "$release_source" "$ACTIVE_ENV" run --rm volume_permissions
# Deliberately omit --remove-orphans: Ollama local remains recoverable until
# the controlled cutover stage explicitly authorizes its retirement.
compose "$release_source" "$ACTIVE_ENV" up -d --no-build

deadline=$((SECONDS + 900))
until compose "$release_source" "$ACTIVE_ENV" exec -T backend \
  python -c "import json,sys,urllib.request; d=json.load(urllib.request.urlopen('http://127.0.0.1:8000/health/operational',timeout=10)); sys.exit(0 if d.get('core_ready') is True and d.get('database_ready') is True and d.get('rag_ready') is True else 1)"
do
  if ((SECONDS >= deadline)); then
    printf 'ERROR: core/RAG readiness deadline exceeded\n' >&2
    exit 1
  fi
  sleep 5
done

curl --fail --silent --show-error --max-time 15 \
  --resolve hemovet.app:443:127.0.0.1 https://hemovet.app/ \
  --output /dev/null
compose "$release_source" "$ACTIVE_ENV" ps
printf 'deployment=success release=%s rag_collection=%s\n' \
  "$release_id" "$target_collection"
printf 'deployment_transaction=%s\n' "$attempt_id"

# Limpieza acotada tras un despliegue verificado: las imagenes de releases
# viejas se acumulan (29 imagenes / 31,8 GB recuperables el 2026-08-09) y
# llenaron el disco al 99%, rompiendo el despliegue e1cffc7 con "no space
# left on device". El filtro de 72h conserva las imagenes del release
# anterior (rollback inmediato sin registro de por medio); todo lo demas
# se re-descarga del registro si un rollback antiguo lo necesitara. Nunca
# falla el despliegue que acaba de verificarse.
docker image prune --all --force --filter "until=72h" >/dev/null 2>&1 || true

# Presion de disco: con despliegues frecuentes las imagenes de MENOS de 72h
# tambien llenan el disco (98% el 2026-08-10, segundo incidente en dos dias;
# 26,73 GB recuperados a mano). Si tras la poda por edad el uso sigue alto,
# se poda todo lo no referenciado por contenedores activos — el registro
# conserva cada release para rollback.
disk_use_pct="$(df --output=pcent / 2>/dev/null | tail -1 | tr -dc '0-9' || true)"
if [ "${disk_use_pct:-0}" -ge 70 ]; then
  docker image prune --all --force >/dev/null 2>&1 || true
fi

trap - ERR EXIT
cleanup
