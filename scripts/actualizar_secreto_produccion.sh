#!/usr/bin/env bash
# Regenera PRODUCTION_ENV_B64 a partir del .env real de producción.
#
# Por qué existe
# --------------
# Los valores de la sesión del 2026-08-06 se aplicaron a mano en
# /var/lib/hemovet-prod/.env y viven solo en la máquina: el despliegue
# reconstruye el entorno desde el secreto PRODUCTION_ENV_B64, así que el
# siguiente despliegue los revierte. Este script toma el fichero real, aplica
# los valores acordados, lo pasa por el mismo validador que corre
# prepare_release.py y solo entonces emite el base64.
#
# El orden importa: validar *antes* de subir el secreto es lo que evita
# descubrir un entorno inválido a mitad de un despliegue a producción.
#
# Uso
# ---
#   # en la VM de producción, o con una copia del fichero:
#   scripts/actualizar_secreto_produccion.sh /var/lib/hemovet-prod/.env
#
# Imprime el base64 y, si `gh` está autenticado, ofrece el comando exacto.
# Nunca sube nada por su cuenta: el secreto es una credencial de despliegue.

set -Eeuo pipefail

origen="${1:-/var/lib/hemovet-prod/.env}"
if [[ ! -r "$origen" ]]; then
  echo "error: no se puede leer $origen" >&2
  echo "       pásale la ruta del .env de producción como primer argumento" >&2
  exit 1
fi

raiz="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
destino="$(mktemp)"
trap 'rm -f -- "$destino"' EXIT
umask 077
cp -- "$origen" "$destino"

# Los valores de ESTADO_LLM_2026-08-06.md §6. Cada uno con el motivo medido,
# porque dentro de un año la cifra sin el motivo no se puede revisar.
declare -A valores=(
  # La carga en frío del modelo tardó 79 s; con 20 el backend daba el warmup
  # por fallido y el chat aparecía caído tras cualquier reinicio de la VM.
  [OLLAMA_WARMUP_TIMEOUT_SECONDS]=120
  # Los prompts reales pesan ~1.700 tokens; 65536 era ×20 y la VRAM ociosa es
  # lo que impedía una segunda ranura de generación.
  [OLLAMA_CONTEXT_LENGTH]=16384
  [CHAT_MAX_INPUT_TOKENS]=12000
  # Lo que la L4 alcanza a generar en 120 s.
  [OLLAMA_NUM_PREDICT]=1280
  # Una pregunta murió a los 90,4 s con el límite en 90.
  [OLLAMA_TIMEOUT_SECONDS]=120
  # Un turno son hasta dos generaciones.
  [CHAT_TOTAL_TIMEOUT_SECONDS]=240
  [CHAT_QUEUE_TIMEOUT_SECONDS]=60
)

for clave in "${!valores[@]}"; do
  valor="${valores[$clave]}"
  if grep -qE "^${clave}=" "$destino"; then
    actual="$(grep -E "^${clave}=" "$destino" | head -1 | cut -d= -f2-)"
    if [[ "$actual" != "$valor" ]]; then
      printf '  %-32s %s -> %s\n' "$clave" "$actual" "$valor"
    fi
    sed -i -E "s|^${clave}=.*|${clave}=${valor}|" "$destino"
  else
    printf '  %-32s (ausente) -> %s\n' "$clave" "$valor"
    printf '%s=%s\n' "$clave" "$valor" >>"$destino"
  fi
done

echo
echo "Validando con el mismo validador que usa el despliegue..."
if ! PYTHONPATH="$raiz/backend" python3 "$raiz/backend/scripts/validate_deploy_env.py" \
    "$destino"; then
  echo "error: el entorno resultante NO es válido; no se emite el secreto" >&2
  exit 1
fi

echo
echo "Entorno válido. Base64 para el secreto PRODUCTION_ENV_B64:"
echo
base64 -w0 <"$destino"
echo
echo
echo "Para subirlo (requiere permisos sobre el repositorio):"
echo "  scripts/actualizar_secreto_produccion.sh '$origen' \\"
echo "    | tail -n +N | gh secret set PRODUCTION_ENV_B64 --repo <owner>/<repo>"
echo
echo "O, más simple y sin dejar el valor en el historial del shell:"
echo "  gh secret set PRODUCTION_ENV_B64 --repo <owner>/<repo> < <(base64 -w0 '$destino')"
echo
echo "Recuerda: guarda antes una copia del .env actual"
echo "  cp '$origen' '$origen.antes-\$(date +%F)'"
