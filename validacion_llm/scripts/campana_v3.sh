#!/usr/bin/env bash
# Campaña v3 — las 9 corridas del plan sellado, en una sola orden.
#
# POR QUÉ EXISTE
# --------------
# La campaña del 14-ago se lanzó con un script improvisado en /tmp que no quedó
# en el repositorio. Eso significa que la corrida más cara del proyecto no es
# reproducible: no consta con qué parámetros se lanzó ni en qué orden.
#
# Y hay un motivo más caro todavía: la ventana cuesta ~110 min de A100. Cada
# minuto que se va en teclear a mano, en recordar un flag o en descubrir a mitad
# que el pre-registro no verificaba, se paga. Esto lo deja en una orden.
#
# LO QUE ESTE SCRIPT NO HACE, Y NO ES NEGOCIABLE
# ----------------------------------------------
#   * NO enciende ninguna VM. Ni una. La prohibición es del usuario y es
#     absoluta, y además el orden de arranque —GPU primero, esperar
#     `hemovet_gpu_startup=ready` por journal SIN sondear, y SOLO entonces la
#     CPU— tiene dos causas medidas de apagado detrás.
#   * NO sondea al proveedor durante el arranque. El arnés espera sin tocar nada
#     y hace UNA comprobación al final de la espera.
#   * NO corta la campaña a mitad. Si los fallos llegan a 14 el plan ya no puede
#     aceptar, pero las 9 corridas se completan igual porque la Puerta R
#     necesita K = 9 por pregunta.
#   * NO apaga las VMs al terminar. Eso lo decide y lo verifica el operador;
#     apagarlas desde aquí escondería un fallo a mitad.
#
# USO
# ---
#   1) Enciende las máquinas TÚ, en el orden correcto, y espera por journal.
#   2) Lee el SHA desplegado EN LA VM (no en GitHub).
#   3) ./validacion_llm/scripts/campana_v3.sh <SHA_EN_LA_VM>
#   4) Al terminar, apaga las tres y verifica TERMINATED.

set -Eeuo pipefail

RELEASE="${1:-}"
BASE_URL="${BASE_URL:-https://hemovet.app}"
CORRIDAS="${CORRIDAS:-9}"
# El fixture. `correr_puerta_0.py` declara los dos como `required=True`, así que
# sin ellos la campaña aborta en argparse —con las máquinas YA ENCENDIDAS—.
# Son los del fixture `test5@test.com`, medidos el 14-ago: una mascota con dos
# hemogramas, el del 18-dic con policitemia (HCT 63,6 %). Cambiarlos rompe la
# comparabilidad con todas las campañas anteriores.
# La espera del arnés antes de CADA corrida. Su valor por defecto —40 sondeos x
# 30 s = 20 MINUTOS— existe para no tocar al proveedor durante el arranque de la
# GPU. Pero el protocolo ya exige haber verificado `hemovet_gpu_startup=ready`
# POR JOURNAL antes de llegar aquí, así que en una campaña de nueve corridas esa
# espera se paga NUEVE veces: tres horas de GPU encendida sin medir nada.
#
# Se baja a una comprobación con 10 s de margen. Lo que esa comprobación protege
# de verdad —abortar sin gastar el corpus si el proveedor no está— se conserva
# entero: sigue habiendo una comprobación única antes de cada corrida.
SONDEOS="${SONDEOS:-1}"
PAUSA_SONDA="${PAUSA_SONDA:-10}"
ANALYSIS_ID="${ANALYSIS_ID:-1e83a035}"
PET_ID="${PET_ID:-b573826b-d918-4f88-aa56-92eba7a15cc1}"
SALIDA="${SALIDA:-validacion_llm/resultados/campana_v3_$(date -u +%Y-%m-%d)}"
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$RAIZ"

rojo()  { printf '\033[31m%s\033[0m\n' "$*"; }
verde() { printf '\033[32m%s\033[0m\n' "$*"; }

# ── FASE 0 · Preflight. Todo lo que se puede romper ANTES de gastar GPU ──────
echo "══════════════════════════════════════════════════════════════════"
echo " PREFLIGHT — nada de esto gasta GPU, y todo esto invalida la campaña"
echo "══════════════════════════════════════════════════════════════════"

fallos=0

echo "── 1 · sellos del pre-registro ──"
for sello in informes_modelo/PUERTAS_v3_PREREGISTRO.sha256; do
  if sha256sum -c "$sello" >/dev/null 2>&1; then
    verde "  OK  $sello"
  else
    rojo  "  MAL $sello — el documento o el instrumento han cambiado sin resellar"
    # `|| true` a propósito: sin él, `pipefail` mata el preflight en su propia
    # línea de diagnóstico y las cuatro comprobaciones siguientes no llegan a
    # correr. Un preflight que se calla al primer fallo obliga a repetirlo cinco
    # veces, y esto existe para no perder minutos de ventana.
    sha256sum -c "$sello" 2>&1 | sed 's/^/      /' || true
    fallos=$((fallos + 1))
  fi
done

echo "── 2 · aritmética del instrumento ──"
if python3 validacion_llm/scripts/evaluar_puertas.py --autocomprobar >/dev/null 2>&1; then
  verde "  OK  42 comprobaciones"
else
  rojo  "  MAL --autocomprobar falla: documento e instrumento han divergido"
  fallos=$((fallos + 1))
fi

echo "── 3 · el árbol de trabajo está limpio ──"
if [ -z "$(git status --porcelain)" ]; then
  verde "  OK  sin cambios sin commitear"
else
  rojo  "  MAL hay cambios sin commitear: no se sabría qué árbol se midió"
  git status --short | sed 's/^/      /'
  fallos=$((fallos + 1))
fi

echo "── 4 · la release desplegada, leída EN LA VM ──"
if [ -z "$RELEASE" ]; then
  rojo  "  MAL falta el SHA. Léelo EN LA VM, no en GitHub:"
  echo  "      gcloud compute ssh hemovet-prod --zone us-central1-c --tunnel-through-iap \\"
  echo  "        --command \"sudo journalctl -u hemovet-gpu.service -b --no-pager | grep -o 'release=[0-9a-f]*' | tail -1\""
  fallos=$((fallos + 1))
else
  local_sha="$(git rev-parse HEAD)"
  # Uno debe ser prefijo del otro: la VM puede reportar el SHA corto o el largo.
  if [[ "$local_sha" == "$RELEASE"* || "$RELEASE" == "$local_sha"* ]]; then
    verde "  OK  $RELEASE coincide con HEAD local ($(git rev-parse --short HEAD))"
  elif git cat-file -e "$RELEASE^{commit}" 2>/dev/null && \
       [ -z "$(git diff --name-only "$RELEASE" HEAD -- backend/ frontend/ frontend_4/ deploy/ docker-compose.prod.yml docker-compose.yml .github/workflows/)" ]; then
    # HEAD va por delante, pero SOLO en rutas que NO se despliegan: informes,
    # herramientas de validación, notas. El árbol desplegable es idéntico, que
    # es lo que la comparabilidad exige. Comparar el SHA a secas obligaría a
    # redesplegar por cambiar un `.md` y a gastar otro arranque de GPU.
    verde "  OK  $RELEASE != HEAD ($(git rev-parse --short HEAD)), pero el ÁRBOL DESPLEGABLE es idéntico"
    echo  "      difieren solo rutas no desplegables:"
    git diff --name-only "$RELEASE" HEAD | sed 's/^/        /' | head -8
  else
    rojo  "  MAL la VM corre $RELEASE y HEAD local es $(git rev-parse --short HEAD)"
    rojo  "      medir contra otro árbol ya invalidó una campaña entera"
    fallos=$((fallos + 1))
  fi
fi

echo "── 5 · las credenciales y los identificadores del fixture ──"
if [ -z "${HEMOVET_EMAIL:-}" ] || [ -z "${HEMOVET_PASSWORD:-}" ]; then
  rojo  "  MAL faltan HEMOVET_EMAIL / HEMOVET_PASSWORD en el entorno"
  fallos=$((fallos + 1))
else
  verde "  OK  fixture ${HEMOVET_EMAIL}"
fi
if [ -z "$ANALYSIS_ID" ] || [ -z "$PET_ID" ]; then
  rojo  "  MAL faltan ANALYSIS_ID / PET_ID; el arnés los exige y abortaria en argparse"
  fallos=$((fallos + 1))
else
  verde "  OK  analysis_id=$ANALYSIS_ID  pet_id=${PET_ID:0:8}…"
fi

echo "── 6 · el arnés acepta la línea de órdenes que se le va a pasar ──"
if python3 validacion_llm/scripts/correr_puerta_0.py --help >/dev/null 2>&1; then
  verde "  OK  correr_puerta_0.py --help"
else
  rojo  "  MAL correr_puerta_0.py no arranca"
  fallos=$((fallos + 1))
fi

if [ "$fallos" -gt 0 ]; then
  echo
  rojo "PREFLIGHT FALLIDO ($fallos): NO se lanza la campaña. Cero GPU gastada."
  exit 1
fi
echo
verde "PREFLIGHT OK — se lanza la campaña de $CORRIDAS corridas"
echo

# ── FASE 1 · Las corridas, SECUENCIALES ─────────────────────────────────────
# Solaparlas rompería `NUM_PARALLEL=1` y contaminaría todas las latencias.
mkdir -p "$SALIDA"
inicio=$(date -u +%s)

for i in $(seq 1 "$CORRIDAS"); do
  echo "══ corrida $i/$CORRIDAS ══ $(date -u +%H:%M:%S) UTC"
  python3 validacion_llm/scripts/correr_puerta_0.py \
    --base-url "$BASE_URL" \
    --email "$HEMOVET_EMAIL" \
    --password "$HEMOVET_PASSWORD" \
    --analysis-id "$ANALYSIS_ID" \
    --pet-id "$PET_ID" \
    --sondeos "$SONDEOS" \
    --pausa-sonda "$PAUSA_SONDA" \
    --etiqueta "campana_v3_c$i" \
    --release "$RELEASE" \
    --salida "$SALIDA/c$i.jsonl" \
    2>&1 | sed 's/^/  /'

  # Recuento vivo de fallos de contrato, solo informativo. NO corta: el
  # curtailment del plan dice que C ya no puede aceptar a partir de 14, pero la
  # Puerta R necesita las 9 corridas de todos modos.
  acumulados=$(cat "$SALIDA"/c*.jsonl 2>/dev/null | python3 -c "
import sys, json
n = 0
for l in sys.stdin:
    if not l.strip():
        continue
    r = json.loads(l)
    if r.get('_tipo_registro'):
        continue
    if r.get('http_status') == 200:
        if r.get('validation_status') != 'passed' or (r.get('provider_calls') or 1) > 1:
            n += 1
    elif str(r.get('codigo_error') or '') in {
        'invalid_model_output', 'model_output_truncated',
        'generation_contract_failed', 'generation_repair_failed',
        'context_budget_exceeded',
    }:
        n += 1
print(n)
" 2>/dev/null || echo "?")
  echo "  fallos de contrato acumulados: $acumulados (el plan no acepta con más de 13)"
  echo
done

fin=$(date -u +%s)
echo "campaña completa en $(( (fin - inicio) / 60 )) min"
echo

# ── FASE 2 · El veredicto, con el instrumento pre-registrado ────────────────
echo "══════════════════════════════════════════════════════════════════"
python3 validacion_llm/scripts/evaluar_puertas.py "$SALIDA"/c*.jsonl \
  | tee "$SALIDA/veredicto.txt"

echo
rojo "RECUERDA: apaga las TRES VMs y verifica TERMINATED."
echo "  gcloud compute instances stop hemovet-llm-gpu-a100 --zone us-central1-a"
echo "  gcloud compute instances stop hemovet-prod --zone us-central1-c"
echo "  gcloud compute instances list --format='value(name,status)'"
