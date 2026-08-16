#!/usr/bin/env bash
# Verifica TODOS los sellos, línea a línea. Sin GPU.
#
# Por qué existe
# --------------
# Cada `.sha256` sella VARIOS ficheros: el informe y, según el caso, el script
# que lo instrumenta o la petición de firma que lo acompaña. Una comprobación
# que solo mire la primera línea da un ✔ FALSO — pasó el 15-ago-2026: dos
# sellos llevaban horas rotos y la comprobación casera decía que estaban bien.
#
# `sha256sum -c` comprueba todas las líneas. Es la única forma correcta.
#
# Salida: 0 si todo cuadra o si lo único que falla está en la lista de fallos
# ESPERADOS y documentados; 1 si hay cualquier otro fallo.

set -uo pipefail
cd "$(dirname "$0")/../.." || exit 2

# Fallos conocidos, documentados y con su razón. Cualquier otro es un fallo real.
#   PUERTAS_v2 sella `evaluar_puertas.py` en su versión de v2. El script se
#   extendió para el plan v3 (§0.4 del pre-registro v3 lo dice y lo exige), así
#   que esa línea TIENE que fallar. Que dejara de fallar sería la señal mala.
ESPERADOS="PUERTAS_v2_PREREGISTRO.sha256:validacion_llm/scripts/evaluar_puertas.py"

fallos_reales=0
esperados_vistos=0

for sello in informes_modelo/*.sha256; do
    nombre=$(basename "$sello")
    while IFS= read -r linea; do
        case "$linea" in
            *": OK") printf '  \033[32m✔\033[0m %-52s %s\n' "${linea%: OK}" "$nombre" ;;
            *": FAILED")
                fichero="${linea%: FAILED}"
                if [ "$ESPERADOS" = "$nombre:$fichero" ]; then
                    printf '  \033[33m~\033[0m %-52s %s  (fallo ESPERADO)\n' "$fichero" "$nombre"
                    esperados_vistos=$((esperados_vistos + 1))
                else
                    printf '  \033[31m✘\033[0m %-52s %s  SELLO ROTO\n' "$fichero" "$nombre"
                    fallos_reales=$((fallos_reales + 1))
                fi
                ;;
        esac
    done < <(sha256sum -c "$sello" 2>/dev/null)
done

echo
if [ "$fallos_reales" -eq 0 ]; then
    echo "  Sellos correctos. Fallos esperados y documentados: $esperados_vistos."
    exit 0
fi
echo "  $fallos_reales SELLO(S) ROTO(S) sin justificar."
echo "  Un sello roto no se regenera en silencio: se anota en SELLOS_REGISTRO.md"
echo "  con qué cambió y por qué, y SOLO entonces se vuelve a sellar."
exit 1
