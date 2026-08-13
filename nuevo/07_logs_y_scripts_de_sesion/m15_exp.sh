set -u
API=http://10.128.0.3:11434
vram() { curl -s $API/api/ps | python3 -c "import sys,json;m=json.load(sys.stdin)['models'];print(m[0]['size_vram'] if m else 0)"; }
ms() { date +%s%3N; }
echo "T0 $(date -Is)  size_vram=$(vram)"
MARCA=$(date -Is)
echo "--- provocando la discordancia: /api/generate con num_ctx=65536, keep_alive=-1 ---"
A=$(ms)
curl -s -X POST $API/api/generate -H 'Content-Type: application/json' \
  -d '{"model":"qwen3.6:27b-q4_K_M","prompt":"ok","stream":false,"keep_alive":-1,"options":{"num_ctx":65536,"num_predict":1,"temperature":0}}' \
  -o /dev/null -w '' 
B=$(ms)
V1=$(vram)
echo "T1 $(date -Is)  recarga a 65536 tardo $(( (B-A)/1000 )) s   size_vram=$V1"
echo "--- observando el rearmado del poller (max 300 s) ---"
INI=$(ms); REARMADO=""
for i in $(seq 1 60); do
  sleep 5
  V=$(vram)
  T=$(( ($(ms)-INI)/1000 ))
  echo "   +${T}s  size_vram=$V"
  if [ "$V" != "$V1" ] && [ "$V" != "0" ]; then REARMADO=$T; V2=$V; break; fi
done
echo "T2 $(date -Is)  rearmado a los ${REARMADO:-NO} s   size_vram=${V2:-$V1}"
echo "--- eventos en el log del backend desde $MARCA ---"
sudo docker logs --since "$MARCA" hemogramas-proyectoicc-backend-1 2>&1 | grep -i "realign\|runner_" | tail -12
