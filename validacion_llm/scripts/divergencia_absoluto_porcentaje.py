#!/usr/bin/env python3
"""¿Con qué frecuencia el absoluto y el porcentaje dicen cosas distintas? — sin GPU.

Por qué existe
--------------
`ambiguous_parameter_claim` es el frente **más grande** de la campaña v3: 31 de 97
fallos de contrato, y `[MEDIDO]` **los 31 son neutrófilos**. La comprobación salta
cuando una frase menciona la familia del parámetro de forma genérica y **el valor
absoluto y el porcentual tienen estados distintos** — es decir, detecta una
ambigüedad **real**, no un falso positivo.

La petición de firma veterinaria (`FIRMA_VETERINARIA_G1.md`) preguntaba si el
porcentaje debe ser citable por sí solo. Le faltaba el dato que convierte la
pregunta en una decisión informada: **cuántas veces pasa esto de verdad**.

Este script lo mide sobre el conjunto de datos real del proyecto, con los mismos
rangos de referencia que usa producción (`hematology/formatter.py`). Cero GPU,
cero backend: es aritmética sobre un CSV que ya está en el repositorio.

Limitación declarada
--------------------
Mide la **prevalencia de la ambigüedad en los datos**, no la tasa de fallo del
chat. Que el 43,5 % de los hemogramas la contengan no implica que el 43,5 % de las
respuestas fallen: depende de si la pregunta invita a una afirmación de estado
sobre esa familia. Las dos cifras van juntas y no se confunden.
"""

from __future__ import annotations

import argparse
import collections
import csv
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[2]

# Los mismos rangos que `backend/app/modules/hematology/formatter.py`. Si allí
# cambian, aquí hay que cambiarlos: se duplican a propósito para que este script
# no importe el backend y se pueda correr en frío.
RANGOS: dict[str, tuple[tuple[float, float], tuple[float, float]]] = {
    # familia: (rango absoluto, rango porcentual)
    "Neutrophils": ((2.9, 11.0), (60.0, 80.0)),
    "Lymphocytes": ((1.0, 5.0), (12.0, 30.0)),
    "Monocytes": ((0.3, 2.0), (2.0, 10.0)),
}
ESTADOS = ("bajo", "normal", "alto")


def estado(valor: float, lo: float, hi: float) -> str:
    if valor < lo:
        return "bajo"
    if valor > hi:
        return "alto"
    return "normal"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "csv",
        nargs="?",
        default=str(RAIZ / "data/processed/labeled_idexx.csv"),
        help="CSV con columnas <Familia> y <Familia>_pct",
    )
    args = p.parse_args()

    ruta = pathlib.Path(args.csv)
    if not ruta.exists():
        print(f"no existe {ruta}", file=sys.stderr)
        return 2

    with ruta.open(encoding="utf-8", errors="replace") as fh:
        filas = list(csv.DictReader(fh))

    print("═" * 74)
    print("DIVERGENCIA absoluto ↔ porcentaje — sobre datos reales, sin GPU")
    print("═" * 74)
    print(f"\n  fichero: {ruta.name}   filas: {len(filas)}")

    for familia, ((abs_lo, abs_hi), (pct_lo, pct_hi)) in RANGOS.items():
        col_abs, col_pct = familia, f"{familia}_pct"
        if col_abs not in (filas[0] if filas else {}):
            continue
        pares: list[tuple[str, str]] = []
        for fila in filas:
            try:
                a = float(fila[col_abs])
                q = float(fila[col_pct])
            except (TypeError, ValueError, KeyError):
                continue
            pares.append((estado(a, abs_lo, abs_hi), estado(q, pct_lo, pct_hi)))

        if not pares:
            continue
        n = len(pares)
        div = [x for x in pares if x[0] != x[1]]
        print(f"\n── {familia}   absoluto {abs_lo}–{abs_hi}   porcentaje {pct_lo}–{pct_hi} %")
        print(f"   con ambos valores: {n}")
        print(f"   ESTADOS DISTINTOS: {len(div):5d} = {len(div) / n * 100:5.1f} %")

        m = collections.Counter(pares)
        print(f"\n     {'abs↓ pct→':>10s}" + "".join(f"{e:>9s}" for e in ESTADOS))
        for a in ESTADOS:
            print(f"     {a:>10s}" + "".join(f"{m[(a, e)]:9d}" for e in ESTADOS))

        print("\n     divergencias más frecuentes:")
        for (a, q), c in collections.Counter(div).most_common(3):
            print(f"       absoluto {a:<7s} + porcentaje {q:<7s} {c:5d}  ({c / n * 100:4.1f} %)")

    print(
        "\n  NOTA: esto mide la prevalencia de la ambigüedad EN LOS DATOS, no la\n"
        "  tasa de fallo del chat. Son dos cosas distintas y no se confunden."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
