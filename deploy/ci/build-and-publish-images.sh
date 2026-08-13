#!/usr/bin/env bash
set -Eeuo pipefail

readonly PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
readonly OUTPUT_DIRECTORY="${1:?usage: build-and-publish-images.sh OUTPUT_DIRECTORY}"
readonly REGISTRY_REPOSITORY="${REGISTRY_REPOSITORY:?set REGISTRY_REPOSITORY}"
readonly RELEASE_SHA="${GITHUB_SHA:?set GITHUB_SHA}"
readonly SOURCE_REPOSITORY="${GITHUB_REPOSITORY:?set GITHUB_REPOSITORY}"
readonly BUILD_CREATED="${BUILD_CREATED:?set BUILD_CREATED}"

if ! [[ "$RELEASE_SHA" =~ ^[0-9a-f]{40}$ ]]; then
  printf 'ERROR: GITHUB_SHA must be a full commit SHA\n' >&2
  exit 1
fi
if [[ "$REGISTRY_REPOSITORY" == *:latest* ]]; then
  printf 'ERROR: mutable registry reference rejected\n' >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIRECTORY/metadata"

build_image() {
  local package="$1"
  local dockerfile="$2"
  local tagged_reference="${REGISTRY_REPOSITORY}/${package}:sha-${RELEASE_SHA}"
  local metadata_file="${OUTPUT_DIRECTORY}/metadata/${package}.json"
  local digest_file="${OUTPUT_DIRECTORY}/metadata/${package}.digest"
  local manifest_file="${OUTPUT_DIRECTORY}/metadata/${package}.manifest"

  if docker buildx imagetools inspect "$tagged_reference" \
    --raw >"$manifest_file" 2>/dev/null
  then
    printf 'artifact=%s state=reused\n' "$package"
  else
    docker buildx build \
      --file "$PROJECT_ROOT/$dockerfile" \
      --platform linux/amd64 \
      --build-arg "HEMOVET_BUILD_REVISION=${RELEASE_SHA}" \
      --build-arg "HEMOVET_BUILD_CREATED=${BUILD_CREATED}" \
      --build-arg "HEMOVET_SOURCE_URL=https://github.com/${SOURCE_REPOSITORY}" \
      --tag "$tagged_reference" \
      --metadata-file "$metadata_file" \
      --provenance=mode=max \
      --sbom=true \
      --push \
      "$PROJECT_ROOT"
    docker buildx imagetools inspect "$tagged_reference" \
      --raw >"$manifest_file"
    printf 'artifact=%s state=published\n' "$package"
  fi

  local digest
  digest="sha256:$(sha256sum "$manifest_file" | cut -d ' ' -f 1)"
  if ! [[ "$digest" =~ ^sha256:[0-9a-f]{64}$ ]]; then
    printf 'ERROR: %s did not produce a canonical digest\n' "$package" >&2
    exit 1
  fi
  printf '%s\n' "$digest" >"$digest_file"
  if [[ -f "$metadata_file" ]]; then
    local declared_digest
    declared_digest="$(jq -er '.["containerimage.digest"]' "$metadata_file")"
    if [[ "$declared_digest" != "$digest" ]]; then
      printf 'ERROR: %s registry and build digests differ\n' "$package" >&2
      exit 1
    fi
  fi
  docker buildx imagetools inspect \
    "${REGISTRY_REPOSITORY}/${package}@${digest}" >/dev/null
}

build_image backend backend/Dockerfile
build_image frontend frontend_4/Dockerfile
build_image ollama-runtime deploy/gpu/ollama-runtime.Dockerfile

PYTHONPATH="$PROJECT_ROOT/backend" python \
  "$PROJECT_ROOT/backend/scripts/create_artifact_set.py" \
  --github-sha "$RELEASE_SHA" \
  --repository "$SOURCE_REPOSITORY" \
  --registry-repository "$REGISTRY_REPOSITORY" \
  --created-at "$BUILD_CREATED" \
  --backend-digest "$(<"$OUTPUT_DIRECTORY/metadata/backend.digest")" \
  --frontend-digest "$(<"$OUTPUT_DIRECTORY/metadata/frontend.digest")" \
  --gpu-digest "$(<"$OUTPUT_DIRECTORY/metadata/ollama-runtime.digest")" \
  --output "$OUTPUT_DIRECTORY/artifact-set.json"

PYTHONPATH="$PROJECT_ROOT/backend" python \
  "$PROJECT_ROOT/backend/scripts/validate_artifact_set.py" \
  "$OUTPUT_DIRECTORY/artifact-set.json"
