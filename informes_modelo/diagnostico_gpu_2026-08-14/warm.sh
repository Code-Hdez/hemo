#!/bin/bash
# Warmup manual: carga qwen3.6:27b-q4_K_M en VRAM con los MISMOS parametros que
# usa produccion (num_ctx=16384, keep_alive=-1) para que no haya recarga despues.
date -u +"start=%H:%M:%S" > /tmp/warm.out
curl -sS --max-time 900 http://10.128.0.3:11434/api/generate \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen3.6:27b-q4_K_M","prompt":"ok","stream":false,"keep_alive":-1,"options":{"num_ctx":16384,"num_predict":1}}' \
  >> /tmp/warm.out 2>/tmp/warm.err
echo "" >> /tmp/warm.out
echo "curl_exit=$?" >> /tmp/warm.out
date -u +"end=%H:%M:%S" >> /tmp/warm.out
