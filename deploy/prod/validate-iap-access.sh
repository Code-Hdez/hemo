#!/usr/bin/env bash
set -Eeuo pipefail

readonly PROJECT_ID="${GCP_PROJECT_ID:-project-5b36701c-f44f-4c03-a12}"
readonly ZONE="${GCP_PRODUCTION_ZONE:-us-central1-c}"
readonly INSTANCE="${GCP_PRODUCTION_INSTANCE:-hemovet-prod}"
readonly EXPECTED_PRIVATE_IP="${GCP_PRODUCTION_PRIVATE_IP:-10.128.0.2}"
readonly LOCAL_PORT="${IAP_LOCAL_PORT:-22022}"

temporary_log="$(mktemp)"
tunnel_pid=""
cleanup() {
  if [[ -n "$tunnel_pid" ]]; then
    kill "$tunnel_pid" >/dev/null 2>&1 || true
    wait "$tunnel_pid" >/dev/null 2>&1 || true
  fi
  rm -f "$temporary_log"
}
trap cleanup EXIT

read -r status private_ip < <(
  gcloud compute instances describe "$INSTANCE" \
    --project="$PROJECT_ID" \
    --zone="$ZONE" \
    --format='value(status,networkInterfaces[0].networkIP)'
)
if [[ "$status" != "RUNNING" || "$private_ip" != "$EXPECTED_PRIVATE_IP" ]]; then
  printf 'ERROR: production IAP target identity mismatch\n' >&2
  exit 1
fi

gcloud compute start-iap-tunnel "$INSTANCE" 22 \
  --project="$PROJECT_ID" \
  --zone="$ZONE" \
  --local-host-port="127.0.0.1:${LOCAL_PORT}" \
  --verbosity=warning >"$temporary_log" 2>&1 &
tunnel_pid="$!"

ready=0
for _ in $(seq 1 30); do
  if ! kill -0 "$tunnel_pid" >/dev/null 2>&1; then
    break
  fi
  if timeout 1 bash -c \
    "exec 3<>/dev/tcp/127.0.0.1/${LOCAL_PORT}; IFS= read -r -t 1 _ <&3"
  then
    ready=1
    break
  fi
  sleep 1
done

if [[ "$ready" != "1" ]]; then
  printf 'ERROR: IAP tunnel did not become ready\n' >&2
  sed -E 's/(token|authorization|credential|password)=[^[:space:]]+/\1=[REDACTED]/Ig' \
    "$temporary_log" >&2
  exit 1
fi

printf 'iap_access=success instance=%s private_ip=%s port=22\n' \
  "$INSTANCE" "$private_ip"
