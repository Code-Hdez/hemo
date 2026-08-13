"""¿Acierta el clasificador semántico de ámbito, y cuánto mejora al determinista?

Por qué existe
--------------
ESTADO_LLM_2026-08-06.md §2.4 deja una reserva explícita sobre el verificador
NLI: el umbral se calibró sobre el mismo banco con el que se puntúa, así que
el 99 % que se reportó es una estimación de ajuste, no de generalización. Su
pendiente #7 pide un conjunto retenido para convertir esa cifra en algo
defendible.

Este script lo construye. El banco no se inventa: sale de los ficheros de casos
del propio proyecto, con la etiqueta que ellos ya traen.

La distinción que mide
----------------------
**Ámbito no es seguridad.** "¿Qué dosis de ibuprofeno le doy a mi perro?" está
*dentro* del ámbito — habla de un perro y de su salud — y se rechaza por
seguridad clínica, que es una decisión determinista y separada. Confundir las
dos cosas es lo que llevó a refusar hematología legítima como si fuera fuera de
tema. Aquí solo se puntúa el ámbito.

Uso
---
    python3 validacion_llm/scripts/medir_ambito_semantico.py
    python3 validacion_llm/scripts/medir_ambito_semantico.py --todo
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

CASOS = PROJECT_ROOT / "validacion_llm" / "casos"

# Fichero, columna de la pregunta, columna de etiqueta (o None), y si el
# fichero es hematología por construcción.
FUENTES = (
    ("casos_ambito_seguridad.csv", "prompt", "clasificacion_esperada", None),
    ("casos_exactitud_contenido.csv", "prompt", None, True),
    ("casos_consistencia.csv", "prompt", None, True),
    ("casos_robustez_ortografica.csv", "prompt_typo", None, True),
    ("casos_memoria_multiturno.csv", "prompt", None, True),
)


def _cargar() -> list[tuple[str, bool]]:
    """(pregunta, está_dentro_de_ámbito) a partir de las etiquetas del proyecto."""

    banco: list[tuple[str, bool]] = []
    for nombre, columna, columna_etiqueta, dentro_por_construccion in FUENTES:
        ruta = CASOS / nombre
        if not ruta.exists():
            continue
        with ruta.open(encoding="utf-8") as fh:
            for fila in csv.DictReader(fh):
                pregunta = (fila.get(columna) or "").strip()
                if not pregunta:
                    continue
                if columna_etiqueta:
                    etiqueta = (fila.get(columna_etiqueta) or "").strip()
                    if not etiqueta:
                        continue
                    # "rechazo" son peticiones clínicas accionables: hablan de
                    # un perro, así que están DENTRO del ámbito. Solo
                    # "fuera_de_ambito_claro" está fuera.
                    dentro = etiqueta != "fuera_de_ambito_claro"
                else:
                    dentro = bool(dentro_por_construccion)
                banco.append((pregunta, dentro))
    return banco


def _particion(pregunta: str) -> str:
    """Mitad estable por hash: reproducible y no elegida a dedo."""

    digest = hashlib.sha256(pregunta.encode("utf-8")).hexdigest()
    return "calibracion" if int(digest[:8], 16) % 2 == 0 else "retenido"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--todo", action="store_true", help="puntuar el banco completo")
    parser.add_argument("--salida", type=Path, default=None)
    args = parser.parse_args()

    from app.core.config import settings
    from app.modules.llm_chat.application.services.semantic_scope import (
        SemanticScopeClassifier,
    )
    from app.modules.llm_chat.infrastructure.entailment import (
        OnnxClaimEntailmentVerifier,
    )

    banco = _cargar()
    if not banco:
        print("no hay casos", file=sys.stderr)
        return 1
    evaluar = (
        banco
        if args.todo
        else [caso for caso in banco if _particion(caso[0]) == "retenido"]
    )
    dentro = sum(1 for _, d in evaluar if d)
    print(
        f"Banco: {len(banco)} casos · evaluando {len(evaluar)} "
        f"({'completo' if args.todo else 'retenido'}) · "
        f"{dentro} dentro / {len(evaluar) - dentro} fuera"
    )

    verificador = OnnxClaimEntailmentVerifier(
        model_repo=settings.CHAT_CLAIM_ENTAILMENT_MODEL,
        threshold=settings.CHAT_CLAIM_ENTAILMENT_THRESHOLD,
        timeout_seconds=max(settings.CHAT_CLAIM_ENTAILMENT_TIMEOUT_SECONDS, 30.0),
        cache_dir=settings.CHAT_CLAIM_ENTAILMENT_CACHE_DIR,
        intra_op_threads=settings.CHAT_CLAIM_ENTAILMENT_THREADS,
    )
    print("cargando el modelo (la primera vez se descarga)...")
    verificador.warmup()
    if not verificador.wait_until_ready(300.0):
        print("el modelo no llegó a estar listo", file=sys.stderr)
        return 1

    clasificador = SemanticScopeClassifier(entailment=verificador)
    aciertos = abstenciones = 0
    fallos: list[tuple[str, bool]] = []
    latencias: list[float] = []
    filas: list[dict[str, object]] = []
    for pregunta, dentro_real in evaluar:
        inicio = time.perf_counter()
        veredicto = clasificador.is_in_scope(pregunta)
        latencias.append((time.perf_counter() - inicio) * 1000)
        if veredicto is None:
            abstenciones += 1
        elif veredicto == dentro_real:
            aciertos += 1
        else:
            fallos.append((pregunta, dentro_real))
        filas.append(
            {
                "pregunta": pregunta,
                "dentro_real": dentro_real,
                "veredicto": "" if veredicto is None else veredicto,
            }
        )

    decididos = len(evaluar) - abstenciones
    print(f"\nDecididos      : {decididos}/{len(evaluar)}")
    if decididos:
        print(f"Aciertos       : {aciertos}/{decididos} ({aciertos / decididos:.0%})")
    print(f"Abstenciones   : {abstenciones}  (dejan en pie la regla determinista)")
    if latencias:
        latencias.sort()
        print(
            f"Latencia       : mediana {latencias[len(latencias) // 2]:.0f} ms · "
            f"máxima {latencias[-1]:.0f} ms"
        )
    if fallos:
        print(f"\nErrores ({len(fallos)}):")
        for pregunta, dentro_real in fallos[:20]:
            esperado = "DENTRO" if dentro_real else "FUERA"
            print(f"  esperado {esperado:6} :: {pregunta[:66]}")

    if args.salida and filas:
        args.salida.parent.mkdir(parents=True, exist_ok=True)
        with args.salida.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(filas[0].keys()))
            writer.writeheader()
            writer.writerows(filas)
        print(f"\nDetalle: {args.salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
