"""Batería C: retención de contexto conversacional (memoria multi-turno).

Reproduce conversaciones guionizadas reutilizando el mismo `conversation_id`
entre turnos, exactamente como lo hace producción vía `conversations.recent`.
Registra la respuesta de cada turno de seguimiento para juzgar si incorpora el
contexto de los turnos previos.

Los casos con `analysis_ref` requieren un análisis real propiedad del usuario de
prueba. Pásalo con --analysis-id / --user-id; si no se provee, esos turnos se
marcan como omitidos en lugar de fallar.

Uso:
    python3 validacion_llm/scripts/correr_memoria_multiturno.py \
        [--user-id UID] [--analysis-id AID]
"""

from __future__ import annotations

import argparse
import asyncio
from collections import defaultdict

from _comun import construir_contenedor, ejecutar_caso, escribir_csv, leer_csv

USER_POR_DEFECTO = "validacion-llm-harness"


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", default=USER_POR_DEFECTO)
    parser.add_argument(
        "--analysis-id",
        default=None,
        help="ID de un análisis real propiedad de --user-id, para los casos con analysis_ref.",
    )
    args = parser.parse_args()

    conversaciones: dict[str, list[dict]] = defaultdict(list)
    for fila in leer_csv("casos_memoria_multiturno.csv"):
        conversaciones[fila["id_conversacion"]].append(fila)

    contenedor = await construir_contenedor()
    filas: list[dict] = []
    try:
        for conv_id, turnos in conversaciones.items():
            turnos.sort(key=lambda t: int(t["turno"]))
            conversation_id: str | None = None
            for turno in turnos:
                requiere_analisis = bool(turno["analysis_ref"])
                if requiere_analisis and not args.analysis_id:
                    filas.append(
                        {
                            "id_conversacion": conv_id,
                            "turno": turno["turno"],
                            "prompt": turno["prompt"],
                            "context_scope": turno["context_scope"],
                            "criterio_memoria": turno["criterio_memoria"],
                            "accion_seguridad": "omitido_sin_analisis",
                            "perfil_chat": "",
                            "num_fuentes": 0,
                            "duracion_ms": 0,
                            "modelo": "",
                            "respuesta": "",
                            "error": "requiere --analysis-id",
                        }
                    )
                    continue
                res, conversation_id = await ejecutar_caso(
                    contenedor,
                    user_id=args.user_id,
                    mensaje=turno["prompt"],
                    context_scope=turno["context_scope"],
                    analysis_id=args.analysis_id if requiere_analisis else None,
                    conversation_id=conversation_id,
                )
                filas.append(
                    {
                        "id_conversacion": conv_id,
                        "turno": turno["turno"],
                        "prompt": turno["prompt"],
                        "context_scope": turno["context_scope"],
                        "criterio_memoria": turno["criterio_memoria"],
                        "accion_seguridad": res.accion_seguridad,
                        "perfil_chat": res.perfil_chat,
                        "num_fuentes": res.num_fuentes,
                        "duracion_ms": res.duracion_ms,
                        "modelo": res.modelo,
                        "respuesta": res.respuesta.replace("\n", " ").strip(),
                        "error": res.error,
                    }
                )

        escribir_csv(
            "eval_memoria_multiturno.csv",
            filas,
            [
                "id_conversacion", "turno", "prompt", "context_scope",
                "criterio_memoria", "accion_seguridad", "perfil_chat",
                "num_fuentes", "duracion_ms", "modelo", "respuesta", "error",
            ],
        )
        seguimiento = [f for f in filas if int(f["turno"]) > 1 and f["respuesta"]]
        print(
            f"Batería C: {len(filas)} turnos ejecutados, "
            f"{len(seguimiento)} de seguimiento listos para juicio de memoria."
        )
        print("Revisa 'respuesta' vs 'criterio_memoria' en eval_memoria_multiturno.csv.")
    finally:
        await contenedor.close()


if __name__ == "__main__":
    asyncio.run(main())
