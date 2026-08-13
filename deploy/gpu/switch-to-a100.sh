#!/usr/bin/env bash
# Intercambio L4 → A100 (spot). EJECUTAR SOLO DESPUÉS DE LA DEMO.
#
# Preparado el 2026-08-10. Estado previo ya creado (no toca la VM actual):
#   - Cuota concedida: 1× A100 preemptible + 12 vCPU A2 en us-central1.
#   - La cuota global es de 1 GPU total: la L4 DEBE estar parada para que
#     la A100 pueda arrancar (paso 2).
#   - IP interna 10.128.0.3 reservada como estática (hemovet-llm-gpu-ip):
#     la A100 la hereda y el backend no necesita ningún cambio.
#   - Disco hemovet-llm-gpu-a100 creado desde el snapshot
#     hemovet-gpu-pre-a100-20260810 (Ollama 0.32.6 + modelo + cadena
#     fail-closed, idéntico a producción).
#
# Rollback: parar hemovet-llm-gpu-a100 y arrancar hemovet-llm-gpu — la IP
# vuelve con ella y todo queda como antes.
set -euo pipefail

PROJECT=project-5b36701c-f44f-4c03-a12
ZONE=us-central1-a
OLD=hemovet-llm-gpu
NEW=hemovet-llm-gpu-a100
IP=10.128.0.3

echo ">> 1/5 Volcando metadata de $OLD (startup-script + claves del reconcile)"
TMP=$(mktemp -d)
gcloud compute instances describe "$OLD" --zone "$ZONE" --project "$PROJECT" \
  --format="json(metadata.items)" > "$TMP/meta.json"
python3 - "$TMP" <<'PY'
import json, sys, pathlib
tmp = pathlib.Path(sys.argv[1])
items = json.loads((tmp / "meta.json").read_text())["metadata"]["items"]
for item in items:
    (tmp / f"meta-{item['key']}").write_text(item.get("value", ""))
print("claves:", ", ".join(sorted(i["key"] for i in items)))
PY

echo ">> 2/5 Parando $OLD (libera la GPU global y la IP $IP)"
gcloud compute instances stop "$OLD" --zone "$ZONE" --project "$PROJECT"

echo ">> 3/5 Creando $NEW (a2-highgpu-1g, A100 spot, misma IP, mismo disco lógico)"
gcloud compute instances create "$NEW" \
  --project "$PROJECT" --zone "$ZONE" \
  --machine-type a2-highgpu-1g \
  --provisioning-model=SPOT --instance-termination-action=STOP \
  --no-restart-on-failure --maintenance-policy TERMINATE \
  --disk "name=hemovet-llm-gpu-a100,device-name=persistent-disk-0,boot=yes,auto-delete=no" \
  --private-network-ip "$IP" \
  --service-account "hemovet-gpu-runtime@${PROJECT}.iam.gserviceaccount.com" \
  --scopes cloud-platform \
  --tags hemovet-gpu-runtime \
  --metadata-from-file "startup-script=$TMP/meta-startup-script,hemovet-gpu-desired-release=$TMP/meta-hemovet-gpu-desired-release,hemovet-gpu-previous-release=$TMP/meta-hemovet-gpu-previous-release" \
  --metadata "enable-oslogin=$(cat "$TMP/meta-enable-oslogin"),install-nvidia-driver=$(cat "$TMP/meta-install-nvidia-driver")"

echo ">> 4/5 Esperando la validación fail-closed."
echo "   LECCIÓN ESCRITA DE LA RONDA 3: no tocar Ollama durante el reconcile."
echo "   Se consulta solo el estado del servicio, nunca generación."
for i in $(seq 1 60); do
  estado=$(gcloud compute ssh "$NEW" --zone "$ZONE" --project "$PROJECT" \
    --tunnel-through-iap --command "systemctl is-active hemovet-gpu.service" \
    2>/dev/null || echo "arrancando")
  echo "   [$i/60] hemovet-gpu.service: $estado"
  if [ "$estado" = "active" ]; then
    break
  fi
  sleep 30
done

echo ">> 5/5 Verificación pasiva (versión y contexto; sin generar):"
gcloud compute ssh "$NEW" --zone "$ZONE" --project "$PROJECT" --tunnel-through-iap \
  --command "curl -s http://localhost:11434/api/version && echo && curl -s http://localhost:11434/api/ps"

cat <<'FIN'

Listo. El backend ya apunta a 10.128.0.3 — no hay nada que cambiar.
Siguiente paso recomendado: correr la batería de latencia
  validacion_llm/resultados/rondas45_2026-08-10/validar_45.py
y comparar medianas contra bateria_ronda6.jsonl (L4).

Rollback:  gcloud compute instances stop hemovet-llm-gpu-a100 --zone us-central1-a
           gcloud compute instances start hemovet-llm-gpu --zone us-central1-a
FIN
