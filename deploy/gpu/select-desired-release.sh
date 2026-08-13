#!/usr/bin/env bash
set -Eeuo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ID="project-5b36701c-f44f-4c03-a12"
readonly ZONE="us-central1-a"
readonly INSTANCE="hemovet-llm-gpu-a100"
readonly METADATA_KEY="hemovet-gpu-desired-release"
readonly BUNDLE_MANIFEST="$script_dir/bundle-manifest.sha256"

manifest=""
previous_output=""
while (($#)); do
  case "$1" in
    --manifest) manifest="$2"; shift 2 ;;
    --previous-output) previous_output="$2"; shift 2 ;;
    *) printf 'ERROR: unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
done

if [[ -z "$manifest" || ! -f "$manifest" || -L "$manifest" ]]; then
  printf 'ERROR: desired GPU release is missing or unsafe\n' >&2
  exit 1
fi
if [[ -n "$previous_output" \
  && ( -e "$previous_output" || -L "$previous_output" ) ]]; then
  printf 'ERROR: previous-output already exists\n' >&2
  exit 1
fi
python3 "$script_dir/runtime_contract.py" validate \
  --manifest "$manifest" \
  --bundle-manifest "$BUNDLE_MANIFEST" >/dev/null

temporary_dir="$(mktemp -d /tmp/hemovet-gpu-release-selection.XXXXXX)"
chmod 700 "$temporary_dir"
previous_manifest="$temporary_dir/previous.json"
after_manifest="$temporary_dir/after.json"
metadata_changed=0
cleanup() {
  find "$temporary_dir" -type f -delete 2>/dev/null || true
  rmdir "$temporary_dir" 2>/dev/null || true
}
restore_on_failure() {
  local status=$?
  trap - ERR EXIT
  if [[ "$status" -ne 0 && "$metadata_changed" == "1" ]]; then
    printf 'ERROR: GPU release selection failed; restoring prior metadata\n' >&2
    gcloud compute instances add-metadata "$INSTANCE" \
      --project "$PROJECT_ID" \
      --zone "$ZONE" \
      --metadata-from-file "$METADATA_KEY=$previous_manifest" \
      --quiet >/dev/null || {
        printf 'CRITICAL: prior GPU release metadata was not restored\n' >&2
        cleanup
        exit 70
      }
  fi
  cleanup
  exit "$status"
}
trap restore_on_failure ERR EXIT

status="$(gcloud compute instances describe "$INSTANCE" \
  --project "$PROJECT_ID" --zone "$ZONE" --format='value(status)')"
if [[ "$status" != "TERMINATED" ]]; then
  printf 'ERROR: GPU release metadata changes require a stopped VM\n' >&2
  exit 1
fi

gcloud compute instances describe "$INSTANCE" \
  --project "$PROJECT_ID" --zone "$ZONE" --format=json \
  | jq -erj --arg key "$METADATA_KEY" \
    '.metadata.items[] | select(.key == $key) | .value' \
    >"$previous_manifest"
chmod 600 "$previous_manifest"
python3 "$script_dir/runtime_contract.py" validate \
  --manifest "$previous_manifest" \
  --bundle-manifest "$BUNDLE_MANIFEST" >/dev/null
previous_release="$(python3 "$script_dir/runtime_contract.py" field \
  --manifest "$previous_manifest" \
  --bundle-manifest "$BUNDLE_MANIFEST" \
  --name release_id)"

if [[ -n "$previous_output" ]]; then
  install -m 0600 "$previous_manifest" "$previous_output"
fi

gcloud compute instances add-metadata "$INSTANCE" \
  --project "$PROJECT_ID" \
  --zone "$ZONE" \
  --metadata-from-file "$METADATA_KEY=$manifest" \
  --quiet >/dev/null
metadata_changed=1

gcloud compute instances describe "$INSTANCE" \
  --project "$PROJECT_ID" --zone "$ZONE" --format=json \
  | jq -erj --arg key "$METADATA_KEY" \
    '.metadata.items[] | select(.key == $key) | .value' \
    >"$after_manifest"
cmp -s "$manifest" "$after_manifest" || {
  printf 'ERROR: selected GPU release bytes differ from the authorized manifest\n' >&2
  exit 1
}
selected_release="$(python3 "$script_dir/runtime_contract.py" field \
  --manifest "$after_manifest" \
  --bundle-manifest "$BUNDLE_MANIFEST" \
  --name release_id)"
final_status="$(gcloud compute instances describe "$INSTANCE" \
  --project "$PROJECT_ID" --zone "$ZONE" --format='value(status)')"
if [[ "$final_status" != "TERMINATED" ]]; then
  printf 'ERROR: GPU VM changed state during release selection\n' >&2
  exit 1
fi

printf 'gpu_release_selection=success previous=%s selected=%s vm_status=%s\n' \
  "$previous_release" "$selected_release" "$final_status"
trap - ERR EXIT
cleanup
