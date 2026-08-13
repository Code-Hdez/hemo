#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
contract="$script_dir/runtime_contract.py"
bundle_manifest="$script_dir/bundle-manifest.sha256"
manifest=""
env_file=""
metrics_output=""
run_inference=0

while (($#)); do
  case "$1" in
    --manifest) manifest="$2"; shift 2 ;;
    --env-file) env_file="$2"; shift 2 ;;
    --metrics-output) metrics_output="$2"; shift 2 ;;
    --run-inference) run_inference=1; shift ;;
    *) printf 'ERROR: unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
done
[[ -f $manifest && -f $env_file ]] || {
  printf 'ERROR: --manifest and --env-file are required\n' >&2
  exit 2
}
if [[ ${EUID} -ne 0 ]]; then
  printf 'ERROR: runtime validation must run as root\n' >&2
  exit 1
fi

python3 "$contract" validate \
  --manifest "$manifest" --bundle-manifest "$bundle_manifest" >/dev/null
release_id="$(python3 "$contract" field --manifest "$manifest" --bundle-manifest "$bundle_manifest" --name release_id)"
runtime_reference="$(python3 "$contract" field --manifest "$manifest" --bundle-manifest "$bundle_manifest" --name runtime.reference)"
expected_model="$(python3 "$contract" field --manifest "$manifest" --bundle-manifest "$bundle_manifest" --name model.name)"
expected_digest="$(python3 "$contract" field --manifest "$manifest" --bundle-manifest "$bundle_manifest" --name model.digest)"
expected_quantization="$(python3 "$contract" field --manifest "$manifest" --bundle-manifest "$bundle_manifest" --name model.quantization)"

bind_address="$(awk -F= '$1 == "OLLAMA_BIND_ADDRESS" {print $2}' "$env_file")"
context_length="$(awk -F= '$1 == "OLLAMA_CONTEXT_LENGTH" {print $2}' "$env_file")"
[[ $context_length =~ ^[0-9]+$ && $context_length -ge 65536 ]] || {
  printf 'ERROR: OLLAMA_CONTEXT_LENGTH must be at least 65536\n' >&2
  exit 1
}
api_base="http://${bind_address}:11434"
container_id="$(docker ps --quiet \
  --filter name='^/hemovet-gpu-ollama-1$' --filter status=running)"
[[ -n $container_id ]] || {
  printf 'ERROR: isolated Ollama container is not running\n' >&2
  exit 1
}
container_image="$(docker inspect --format '{{.Config.Image}}' "$container_id")"
[[ $container_image == "$runtime_reference" ]] || {
  printf 'ERROR: running runtime reference differs from desired digest\n' >&2
  exit 1
}
docker inspect --format '{{json .HostConfig.DeviceRequests}}' "$container_id" \
  | jq --exit-status \
    'any(.[]; (.Capabilities | flatten | index("gpu")) != null)' >/dev/null
docker exec "$container_id" nvidia-smi --query-gpu=name --format=csv,noheader \
  | grep -Ex 'NVIDIA L4|NVIDIA A100-SXM4-40GB' >/dev/null

temporary_dir="$(mktemp -d /run/hemovet-gpu-validation.XXXXXX)"
sampler_pid=""
cleanup() {
  if [[ -n $sampler_pid ]]; then
    kill "$sampler_pid" 2>/dev/null || true
    wait "$sampler_pid" 2>/dev/null || true
  fi
  find "$temporary_dir" -type f -delete
  rmdir "$temporary_dir"
}
trap cleanup EXIT
curl --fail --silent --show-error --connect-timeout 2 --max-time 15 \
  "$api_base/api/tags" >"$temporary_dir/tags.json"
installed_digest="$(jq --exit-status --raw-output --arg model "$expected_model" \
  '.models[] | select((.name == $model) or (.model == $model)) | .digest' \
  "$temporary_dir/tags.json" | head -n1)"
[[ ${installed_digest#sha256:} == "${expected_digest#sha256:}" ]] || {
  printf 'ERROR: installed model digest mismatch\n' >&2
  exit 1
}

jq --null-input --arg model "$expected_model" '{model:$model}' \
  >"$temporary_dir/show-request.json"
curl --fail --silent --show-error --connect-timeout 2 --max-time 30 \
  --header 'Content-Type: application/json' \
  --data-binary "@$temporary_dir/show-request.json" \
  "$api_base/api/show" >"$temporary_dir/show.json"
actual_quantization="$(jq --exit-status --raw-output \
  '.details.quantization_level' "$temporary_dir/show.json")"
[[ $actual_quantization == "$expected_quantization" ]] || {
  printf 'ERROR: model quantization mismatch\n' >&2
  exit 1
}

latency_ms=0
peak_vram_mib=0
peak_gpu_utilization=0
if ((run_inference)); then
  jq --null-input --arg model "$expected_model" --argjson num_ctx "$context_length" \
    '{model:$model,prompt:"Responde unicamente: OK",stream:false,keep_alive:-1,options:{temperature:0,num_ctx:$num_ctx,num_predict:8}}' \
    >"$temporary_dir/inference-request.json"
  (
    while true; do
      nvidia-smi --query-gpu=memory.used,utilization.gpu \
        --format=csv,noheader,nounits || true
      sleep 0.2
    done
  ) >"$temporary_dir/gpu-samples.csv" 2>/dev/null &
  sampler_pid=$!
  started_ms="$(date +%s%3N)"
  curl --fail-with-body --silent --show-error --connect-timeout 3 --max-time 420 \
    --header 'Content-Type: application/json' \
    --data-binary "@$temporary_dir/inference-request.json" \
    "$api_base/api/generate" >"$temporary_dir/inference-response.json"
  finished_ms="$(date +%s%3N)"
  kill "$sampler_pid" 2>/dev/null || true
  wait "$sampler_pid" 2>/dev/null || true
  sampler_pid=""
  latency_ms=$((finished_ms - started_ms))
  jq --exit-status --arg model "$expected_model" \
    '.done == true and .model == $model and (.response | type == "string")' \
    "$temporary_dir/inference-response.json" >/dev/null
  # Canary for https://github.com/ollama/ollama/issues/14645: /api/generate
  # above proves the model answers, but the production chat path calls
  # /api/chat with think:false and a JSON Schema format, which that bug
  # silently ignores on affected Ollama builds while /api/generate stays
  # unaffected — this would otherwise pass boot validation on a runtime
  # that cannot actually serve structured chat output.
  jq --null-input --arg model "$expected_model" \
    '{model:$model,messages:[{role:"user",content:"Responde con un objeto JSON."}],think:false,stream:false,keep_alive:-1,format:{type:"object",properties:{ok:{type:"boolean"}},required:["ok"],additionalProperties:false},options:{temperature:0,num_predict:16}}' \
    >"$temporary_dir/chat-format-request.json"
  curl --fail-with-body --silent --show-error --connect-timeout 3 --max-time 60 \
    --header 'Content-Type: application/json' \
    --data-binary "@$temporary_dir/chat-format-request.json" \
    "$api_base/api/chat" >"$temporary_dir/chat-format-response.json"
  jq --exit-status '.message.content | fromjson | .ok | type == "boolean"' \
    "$temporary_dir/chat-format-response.json" >/dev/null || {
    printf 'ERROR: /api/chat ignored format with think=false (ollama/ollama#14645)\n' >&2
    exit 1
  }
  peak_vram_mib="$(awk -F, '
    {gsub(/ /, "", $1); if ($1 + 0 > peak) peak = $1 + 0}
    END {print peak + 0}
  ' "$temporary_dir/gpu-samples.csv")"
  peak_gpu_utilization="$(awk -F, '
    {gsub(/ /, "", $2); if ($2 + 0 > peak) peak = $2 + 0}
    END {print peak + 0}
  ' "$temporary_dir/gpu-samples.csv")"
fi

curl --fail --silent --show-error --connect-timeout 2 --max-time 15 \
  "$api_base/api/ps" >"$temporary_dir/ps.json"
model_size="$(jq --exit-status --raw-output --arg model "$expected_model" \
  '.models[] | select((.name == $model) or (.model == $model)) | .size' \
  "$temporary_dir/ps.json")"
model_vram="$(jq --exit-status --raw-output --arg model "$expected_model" \
  '.models[] | select((.name == $model) or (.model == $model)) | .size_vram' \
  "$temporary_dir/ps.json")"
((model_vram > 0 && model_vram * 100 >= model_size * 95)) || {
  printf 'ERROR: model is not resident primarily on GPU\n' >&2
  exit 1
}
docker exec "$container_id" ollama ps \
  | grep -F "$expected_model" | grep -F '100% GPU' >/dev/null

vram_used_mib="$(nvidia-smi --query-gpu=memory.used \
  --format=csv,noheader,nounits | tr -d '[:space:]')"
gpu_utilization="$(nvidia-smi --query-gpu=utilization.gpu \
  --format=csv,noheader,nounits | tr -d '[:space:]')"
root_used_bytes="$(df -B1 --output=used / | tail -1 | tr -d '[:space:]')"
memory_available_kib="$(awk '/MemAvailable/{print $2}' /proc/meminfo)"
container_memory_usage="$(docker stats --no-stream \
  --format '{{.MemUsage}}' "$container_id" | awk -F/ '{gsub(/^ +| +$/, "", $1); print $1}')"
model_volume_mount="$(docker volume inspect \
  --format '{{.Mountpoint}}' hemovet_gpu_ollama_models)"
model_volume_bytes="$(du -sb "$model_volume_mount" | awk '{print $1}')"

if [[ -n $metrics_output ]]; then
  install -d -m 0700 "$(dirname "$metrics_output")"
  temporary_metrics="$(mktemp "$(dirname "$metrics_output")/.metrics.XXXXXX")"
  jq --null-input \
    --arg release_id "$release_id" \
    --arg model "$expected_model" \
    --arg digest "$expected_digest" \
    --arg quantization "$actual_quantization" \
    --arg runtime_reference "$runtime_reference" \
    --arg validated_at "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
    --argjson latency_ms "$latency_ms" \
    --argjson model_size_bytes "$model_size" \
    --argjson model_vram_bytes "$model_vram" \
    --argjson vram_used_mib "$vram_used_mib" \
    --argjson gpu_utilization_percent "$gpu_utilization" \
    --argjson peak_vram_mib "$peak_vram_mib" \
    --argjson peak_gpu_utilization_percent "$peak_gpu_utilization" \
    --argjson root_used_bytes "$root_used_bytes" \
    --argjson memory_available_kib "$memory_available_kib" \
    --arg container_memory_usage "$container_memory_usage" \
    --argjson model_volume_bytes "$model_volume_bytes" \
    '{release_id:$release_id,validated_at:$validated_at,runtime_reference:$runtime_reference,model:$model,model_digest:$digest,quantization:$quantization,gpu_active:true,inference_device:"full_gpu",latency_ms:$latency_ms,model_size_bytes:$model_size_bytes,model_vram_bytes:$model_vram_bytes,vram_used_mib:$vram_used_mib,gpu_utilization_percent:$gpu_utilization_percent,peak_vram_mib:$peak_vram_mib,peak_gpu_utilization_percent:$peak_gpu_utilization_percent,container_memory_usage:$container_memory_usage,model_volume_bytes:$model_volume_bytes,root_used_bytes:$root_used_bytes,memory_available_kib:$memory_available_kib}' \
    >"$temporary_metrics"
  chmod 0600 "$temporary_metrics"
  mv -f "$temporary_metrics" "$metrics_output"
fi
printf 'runtime=valid release=%s model=%s digest=%s quantization=%s inference_device=full_gpu latency_ms=%s\n' \
  "$release_id" "$expected_model" "${expected_digest#sha256:}" \
  "$actual_quantization" "$latency_ms"
