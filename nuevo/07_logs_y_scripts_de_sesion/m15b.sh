set -u
A=http://10.128.0.3:11434
v() { curl -s $A/api/ps | python3 -c "import sys,json;m=json.load(sys.stdin)['models'];print(m[0]['size_vram'] if m else 0)"; }
M=$(date -Is)
echo "T0 $(date -Is) vram=$(v)"
curl -s -X POST $A/api/generate -H 'Content-Type: application/json' \
 -d '{"model":"qwen3.6:27b-q4_K_M","prompt":"ok","stream":false,"keep_alive":-1,"options":{"num_ctx":65536,"num_predict":1,"temperature":0}}' -o /dev/null
V1=$(v); echo "T1 $(date -Is) deriva forzada vram=$V1"
I=$(date +%s)
for i in $(seq 1 26); do
  sleep 5; V=$(v); T=$(( $(date +%s)-I ))
  if [ "$V" != "$V1" ] && [ "$V" != "0" ]; then echo "REARMADO a los ${T}s  vram=$V"; break; fi
  [ $((T % 20)) -lt 5 ] && echo "   +${T}s $V"
done
echo "=== log desde $M ==="
sudo docker logs --since "$M" hemogramas-proyectoicc-backend-1 2>&1 | grep -E "runner_realign|provider_warmup" | tail -8
echo "=== estado final ==="; v
