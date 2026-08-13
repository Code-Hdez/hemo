"""Batería E: exactitud de contenido (prioridad de la asesora).

Ejecuta las preguntas de hematología contra el pipeline real y genera la rúbrica
que los dos veterinarios ("Médico 1"/"Médico 2") completan. La rúbrica se entrega
pre-rellenada con pregunta, respuesta del asistente y fuentes citadas; las
columnas de juicio quedan vacías.

Salidas:
  - validacion_llm/resultados/exactitud_contenido_crudo.csv        (crudo del harness)
  - validacion_llm/rubrica_veterinarios/rubrica_contenido_llm.csv  (plantilla en blanco)

Los casos con `analysis_ref` requieren --analysis-id / --user-id; si no se provee,
se omiten.

Uso:
    python3 validacion_llm/scripts/correr_exactitud_contenido.py [--user-id UID] [--analysis-id AID]
"""

from __future__ import annotations

import argparse
import asyncio
import csv
from pathlib import Path

from _comun import PROJECT_ROOT, construir_contenedor, ejecutar_caso, escribir_csv, leer_csv

USER_POR_DEFECTO = "validacion-llm-harness"
RUBRICA_DIR = PROJECT_ROOT / "validacion_llm" / "rubrica_veterinarios"

RUBRICA_COLUMNAS = [
    "id_caso",
    "pregunta",
    "respuesta_llm",
    "fuentes_citadas",
    "correctitud",       # correcto | parcialmente_correcto | incorrecto | alucinado
    "cita_apropiada",    # si | no
    "seguridad_clinica",  # si | no
    "comentario",
]


def _escribir_rubrica(filas: list[dict]) -> Path:
    RUBRICA_DIR.mkdir(parents=True, exist_ok=True)
    ruta = RUBRICA_DIR / "rubrica_contenido_llm.csv"
    with ruta.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RUBRICA_COLUMNAS)
        writer.writeheader()
        for fila in filas:
            writer.writerow(
                {
                    "id_caso": fila["id_caso"],
                    "pregunta": fila["prompt"],
                    "respuesta_llm": fila["respuesta"],
                    "fuentes_citadas": fila["fuentes_citadas"],
                    "correctitud": "",
                    "cita_apropiada": "",
                    "seguridad_clinica": "",
                    "comentario": "",
                }
            )
    return ruta


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", default=USER_POR_DEFECTO)
    parser.add_argument("--analysis-id", default=None)
    args = parser.parse_args()

    contenedor = await construir_contenedor()
    filas_crudo: list[dict] = []
    try:
        for caso in leer_csv("casos_exactitud_contenido.csv"):
            requiere_analisis = bool(caso["analysis_ref"])
            if requiere_analisis and not args.analysis_id:
                filas_crudo.append(
                    {
                        "id_caso": caso["id_caso"],
                        "etiqueta_relacionada": caso["etiqueta_relacionada"],
                        "tipo_pregunta": caso["tipo_pregunta"],
                        "prompt": caso["prompt"],
                        "accion_seguridad": "omitido_sin_analisis",
                        "perfil_chat": "",
                        "fuentes_citadas": "",
                        "num_fuentes": 0,
                        "duracion_ms": 0,
                        "modelo": "",
                        "respuesta": "",
                        "error": "requiere --analysis-id",
                    }
                )
                continue
            res, _ = await ejecutar_caso(
                contenedor,
                user_id=args.user_id,
                mensaje=caso["prompt"],
                context_scope=caso["context_scope"],
                analysis_id=args.analysis_id if requiere_analisis else None,
            )
            filas_crudo.append(
                {
                    "id_caso": caso["id_caso"],
                    "etiqueta_relacionada": caso["etiqueta_relacionada"],
                    "tipo_pregunta": caso["tipo_pregunta"],
                    "prompt": caso["prompt"],
                    "accion_seguridad": res.accion_seguridad,
                    "perfil_chat": res.perfil_chat,
                    "fuentes_citadas": "|".join(s for s in res.ids_fuentes if s),
                    "num_fuentes": res.num_fuentes,
                    "duracion_ms": res.duracion_ms,
                    "modelo": res.modelo,
                    "respuesta": res.respuesta.replace("\n", " ").strip(),
                    "error": res.error,
                }
            )

        escribir_csv(
            "exactitud_contenido_crudo.csv",
            filas_crudo,
            [
                "id_caso", "etiqueta_relacionada", "tipo_pregunta", "prompt",
                "accion_seguridad", "perfil_chat", "fuentes_citadas", "num_fuentes",
                "duracion_ms", "modelo", "respuesta", "error",
            ],
        )
        ruta_rubrica = _escribir_rubrica(filas_crudo)
        print(f"Batería E: {len(filas_crudo)} casos ejecutados.")
        print(f"Rúbrica en blanco para veterinarios: {ruta_rubrica}")
        print("Duplícala como rubrica_contenido_llm_medico1.csv y _medico2.csv para cada evaluador.")
    finally:
        await contenedor.close()


if __name__ == "__main__":
    asyncio.run(main())
