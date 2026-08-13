#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly STATE_DIR="/var/lib/hemovet-gpu"
readonly PREVIOUS_MANIFEST="$STATE_DIR/previous-release.json"
readonly RELEASES_DIR="$STATE_DIR/releases"
readonly BUNDLE_MANIFEST="$script_dir/bundle-manifest.sha256"
target_manifest=""

if [[ ${EUID} -ne 0 ]]; then
  printf 'ERROR: runtime rollback must run as root\n' >&2
  exit 1
fi
case "${1:-}" in
  --previous)
    target_manifest="$PREVIOUS_MANIFEST"
    ;;
  --release-id)
    [[ ${2:-} =~ ^[0-9a-f]{40}$ ]] || {
      printf 'ERROR: invalid release id\n' >&2
      exit 2
    }
    target_manifest="$RELEASES_DIR/$2/manifest.json"
    ;;
  *)
    printf 'Usage: %s --previous | --release-id FULL_SHA\n' "$0" >&2
    exit 2
    ;;
esac
[[ -f $target_manifest ]] || {
  printf 'ERROR: rollback target is unavailable\n' >&2
  exit 1
}
temporary_dir="$(mktemp -d "$STATE_DIR/.rollback.XXXXXX")"
cleanup() {
  find "$temporary_dir" -type f -delete 2>/dev/null || true
  rmdir "$temporary_dir" 2>/dev/null || true
}
trap cleanup EXIT
projected_manifest="$temporary_dir/manifest.json"
python3 "$script_dir/runtime_contract.py" project-bundle \
  --manifest "$target_manifest" \
  --bundle-manifest "$BUNDLE_MANIFEST" \
  --output "$projected_manifest"
target_id="$(python3 "$script_dir/runtime_contract.py" field \
  --manifest "$projected_manifest" \
  --bundle-manifest "$BUNDLE_MANIFEST" \
  --name release_id)"
printf 'rollback=authorized target_release=%s\n' "$target_id"
"$script_dir/reconcile-release.sh" --boot --manifest-file "$projected_manifest"
