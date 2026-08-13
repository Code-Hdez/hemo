#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
  printf 'ERROR: bootstrap installation must run as root\n' >&2
  exit 1
fi
source_root="${1:-}"
[[ -n $source_root \
  && -f $source_root/deploy/gpu/bundle-manifest.sha256 ]] || {
  printf 'Usage: %s REPOSITORY_BUNDLE_ROOT\n' "$0" >&2
  exit 2
}
source_root="$(cd "$source_root" && pwd)"
manifest="$source_root/deploy/gpu/bundle-manifest.sha256"
(cd "$source_root" && sha256sum --check deploy/gpu/bundle-manifest.sha256)
bundle_digest="$(sha256sum "$manifest" | awk '{print $1}')"
bundle_dir="/opt/hemovet-gpu/bundles/$bundle_digest"

install -d -m 0755 /opt/hemovet-gpu/bundles
install -d -m 0755 /etc/cdi
install -d -m 0700 /var/lib/hemovet-gpu /var/lib/hemovet-gpu/releases
if [[ ! -d $bundle_dir ]]; then
  staging_dir="$(mktemp -d \
    "/opt/hemovet-gpu/bundles/.${bundle_digest}.XXXXXX")"
  while read -r _ file_path; do
    [[ -n $file_path ]] || continue
    mode=0644
    if [[ $file_path == *.sh || $file_path == *.py ]]; then
      mode=0755
    fi
    install -D -m "$mode" "$source_root/$file_path" \
      "$staging_dir/$file_path"
  done <"$manifest"
  install -D -m 0644 "$manifest" \
    "$staging_dir/deploy/gpu/bundle-manifest.sha256"
  mv "$staging_dir" "$bundle_dir"
fi
(cd "$bundle_dir" && sha256sum --check deploy/gpu/bundle-manifest.sha256)

next_link="/opt/hemovet-gpu/.current.$bundle_digest"
ln -s "$bundle_dir" "$next_link"
mv -Tf "$next_link" /opt/hemovet-gpu/current
install -m 0644 "$bundle_dir/deploy/gpu/hemovet-gpu.service" \
  /etc/systemd/system/hemovet-gpu.service
install -m 0644 \
  "$bundle_dir/deploy/gpu/hemovet-gpu-failure-shutdown.service" \
  /etc/systemd/system/hemovet-gpu-failure-shutdown.service
systemctl daemon-reload
systemctl enable hemovet-gpu.service >/dev/null
"$bundle_dir/deploy/gpu/validate-host.sh"
printf 'bootstrap=installed bundle=sha256:%s service=enabled action=not_started\n' \
  "$bundle_digest"
