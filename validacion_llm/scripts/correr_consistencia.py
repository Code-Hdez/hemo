"""Batería D: consistencia entre ejecuciones repetidas del mismo prompt.

Con temperatura 0.1 (no determinista por diseño), la exactitud literal no es el
criterio. Se miden proxies automáticos: solapamiento del conjunto de fuentes
citadas y variación de longitud de la respuesta entre repeticiones. La
equivalencia semántica la juzgan los veterinarios sobre las respuestas exportadas.

Cada repetición usa una conversación nueva para evitar arrastre de contexto.

Salidas:
  - validacion_llm/resultados/eval_consistencia.csv        (una fila por repetición)
  - validacion_llm/resultados/resumen_consistencia.csv      (una fila por prompt)

Uso:
    python3 validacion_llm/scripts/correr_consistencia.py
"""

from __future__ import annotations

import asyncio
import statistics

from _comun import construir_contenedor, ejecutar_caso, escribir_csv, leer_csv

USER_ID = "validacion-llm-harness"


def _jaccard(conjuntos: list[set[str]]) -> float:
    """Solapamiento promedio par a par (Jaccard) de los conjuntos de fuentes."""
    pares = [
        (conjuntos[i], conjuntos[j])
        for i in range(len(conjuntos))
        for j in range(i + 1, len(conjuntos))
    ]
    if not pares:
        return 1.0
    puntajes = []
    for a, b in pares:
        union = a | b
        puntajes.append(len(a & b) / len(union) if union else 1.0)
    return round(statistics.mean(puntajes), 4)


async def main(user_id: str = USER_ID) -> None:
    contenedor = await construir_contenedor()
    filas_detalle: list[dict] = []
    filas_resumen: list[dict] = []
    try:
        for caso in leer_csv("casos_consistencia.csv"):
            reps = int(caso["repeticiones"])
            conjuntos_fuentes: list[set[str]] = []
            longitudes: list[int] = []
            acciones: list[str] = []
            for rep in range(1, reps + 1):
                res, _ = await ejecutar_caso(
                    contenedor, user_id=user_id, mensaje=caso["prompt"]
                )
                conjuntos_fuentes.append({s for s in res.ids_fuentes if s})
                longitudes.append(len(res.respuesta))
                acciones.append(res.accion_seguridad)
                filas_detalle.append(
                    {
                        "id_caso": caso["id_caso"],
                        "repeticion": rep,
                        "prompt": caso["prompt"],
                        "accion_seguridad": res.accion_seguridad,
                        "perfil_chat": res.perfil_chat,
                        "num_fuentes": res.num_fuentes,
                        "ids_fuentes": "|".join(sorted(s for s in res.ids_fuentes if s)),
                        "longitud_respuesta": len(res.respuesta),
                        "duracion_ms": res.duracion_ms,
                        "modelo": res.modelo,
                        "respuesta": res.respuesta.replace("\n", " ").strip(),
                        "error": res.error,
                    }
                )
            filas_resumen.append(
                {
                    "id_caso": caso["id_caso"],
                    "prompt": caso["prompt"],
                    "repeticiones": reps,
                    "citas_jaccard_promedio": _jaccard(conjuntos_fuentes),
                    "longitud_media": round(statistics.mean(longitudes)) if longitudes else 0,
                    "longitud_desv_std": round(statistics.pstdev(longitudes), 1) if len(longitudes) > 1 else 0.0,
                    "acciones_consistentes": int(len(set(acciones)) == 1),
                    "acciones_observadas": "|".join(sorted(set(acciones))),
                }
            )

        escribir_csv(
            "eval_consistencia.csv",
            filas_detalle,
            [
                "id_caso", "repeticion", "prompt", "accion_seguridad", "perfil_chat",
                "num_fuentes", "ids_fuentes", "longitud_respuesta", "duracion_ms",
                "modelo", "respuesta", "error",
            ],
        )
        escribir_csv(
            "resumen_consistencia.csv",
            filas_resumen,
            [
                "id_caso", "prompt", "repeticiones", "citas_jaccard_promedio",
                "longitud_media", "longitud_desv_std", "acciones_consistentes",
                "acciones_observadas",
            ],
        )
        print(f"Batería D: {len(filas_detalle)} ejecuciones, {len(filas_resumen)} prompts.")
        for fila in filas_resumen:
            print(
                f"  {fila['id_caso']}: Jaccard citas={fila['citas_jaccard_promedio']}, "
                f"acciones_consistentes={fila['acciones_consistentes']}"
            )
    finally:
        await contenedor.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Batería D: consistencia")
    parser.add_argument("--user-id", default=USER_ID)
    args = parser.parse_args()
    asyncio.run(main(args.user_id))
