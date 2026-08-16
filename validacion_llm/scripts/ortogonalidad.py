#!/usr/bin/env python3
"""Matriz validador × condición — la prueba de ortogonalidad, sin GPU.

Por qué existe
--------------
El plan asigna cada clase de rechazo a un bloque —G.1 al porcentaje, H a las
cifras, I a los actos de habla— y da por hecho que atacan poblaciones disjuntas.
`[MEDIDO]` La campaña v3 ya mostró que **eso no es exacto**: 3 de 96 fallos
cruzan la frontera de ámbito.

Asumir la independencia y luego atribuir el efecto a cada bloque sería el error
que `§3.8` describe: *«las ablaciones por pares tienen un efecto más fuerte que la
suma de las ablaciones individuales»*.

**Pero demostrarla es gratis.** Los `.jsonl` de cada condición guardan el texto
publicado. Reejecutar los cuatro validadores sobre las cuatro condiciones es
aritmética sobre datos que ya existen, y produce una matriz que dice si la
independencia es real o es una esperanza.

El punto débil que hay que vigilar, y es concreto
-------------------------------------------------
La gramática del Bloque H **cambia el texto**, y ese texto alimenta el léxico de
recomendación del Bloque I. Es la interacción más probable de las tres, y es
justo la que la diagonal detectaría.

Limitación declarada
--------------------
Solo se puede reejecutar sobre el texto **publicado**. Los turnos terminales no
publican nada, así que la matriz cubre los turnos que respondieron —que son
también los que el validador dejó pasar—. Es un límite del diseño de privacidad,
no de este script, y se reporta con su denominador.

Uso
---
    python3 validacion_llm/scripts/ortogonalidad.py \\
        base=validacion_llm/resultados/campana_v3_2026-08-15 \\
        G1=validacion_llm/resultados/campana_g1_... \\
        H=... I=...
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[2]


def cargar_validador():
    """Los mismos predicados que gobiernan producción. No se reimplementan."""
    backend = RAIZ / "backend"
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))
    from app.modules.llm_chat.application.services.output_validator import (  # noqa: PLC0415
        OutputValidator,
    )

    return OutputValidator()


# Los cuatro validadores que el plan asigna a un bloque cada uno. Se evalúan
# TODOS sobre TODAS las condiciones: esa es la gracia de la matriz.
def _indirect(v, texto: str) -> bool:
    motivo = v._contains_indirect_treatment(texto)  # noqa: SLF001
    return bool(motivo) and not v._is_safe_refusal(texto)  # noqa: SLF001


VALIDADORES = {
    "indirect_treatment": _indirect,
    "definitive_diagnosis": lambda v, t: bool(v._contains_definitive_diagnosis(t)),  # noqa: SLF001
    "dose_instruction": lambda v, t: bool(v._contains_positive_dose_instruction(t)),  # noqa: SLF001
    "internal_material": lambda v, t: bool(v._internal_material.search(t)),  # noqa: SLF001
}


def turnos_de(directorio: str) -> list[dict]:
    salida = []
    for ruta in sorted(glob.glob(str(pathlib.Path(directorio) / "c*.jsonl"))):
        for linea in pathlib.Path(ruta).read_text(encoding="utf-8").splitlines():
            if not linea.strip():
                continue
            registro = json.loads(linea)
            if not registro.get("_tipo_registro"):
                salida.append(registro)
    return salida


def clase_declarada(turno: dict) -> str | None:
    crudo = str(turno.get("first_validation_reason") or "")
    m = re.match(r"^r=([a-z_]+)\|", crudo)
    if m:
        return None if m.group(1) == "ok" else m.group(1)
    if not crudo or crudo == "-":
        return None
    return crudo.split(":")[0]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("condiciones", nargs="+", help="etiqueta=directorio, una por condición")
    args = p.parse_args()

    v = cargar_validador()
    if v is None:
        print("el backend no es importable; no se inventa una matriz", file=sys.stderr)
        return 2

    condiciones: dict[str, list[dict]] = {}
    for spec in args.condiciones:
        if "=" not in spec:
            p.error(f"«{spec}» no tiene la forma etiqueta=directorio")
        etiqueta, directorio = spec.split("=", 1)
        condiciones[etiqueta] = turnos_de(directorio)

    print("═" * 78)
    print("MATRIZ VALIDADOR × CONDICIÓN — sobre el texto PUBLICADO, sin GPU")
    print("═" * 78)

    etiquetas = list(condiciones)
    print(f"\n  {'condición':<14s} {'turnos':>7s} {'publicados':>11s}")
    for e in etiquetas:
        pub = sum(1 for t in condiciones[e] if str(t.get("respuesta") or "").strip())
        print(f"  {e:<14s} {len(condiciones[e]):7d} {pub:11d}")

    print(f"\n  {'validador':<22s} " + "".join(f"{e[:12]:>14s}" for e in etiquetas))
    matriz: dict[str, dict[str, int]] = {}
    for nombre, fn in VALIDADORES.items():
        fila = {}
        for e in etiquetas:
            pubs = [str(t.get("respuesta") or "") for t in condiciones[e]]
            pubs = [x for x in pubs if x.strip()]
            fila[e] = sum(1 for x in pubs if fn(v, x))
        matriz[nombre] = fila
        print(f"  {nombre:<22s} " + "".join(f"{fila[e]:14d}" for e in etiquetas))

    print("\n  ── lo que el validador DECLARÓ en su momento (para contrastar) ──")
    for e in etiquetas:
        c = collections.Counter(
            clase_declarada(t) for t in condiciones[e] if clase_declarada(t)
        )
        print(f"  {e:<14s} {dict(c.most_common(6))}")

    if len(etiquetas) < 2:
        print(
            "\n  UNA SOLA CONDICIÓN: la matriz no puede ser diagonal ni dejar de serlo.\n"
            "  Esto es la columna de referencia; la prueba de ortogonalidad necesita\n"
            "  las condiciones del plan, y esas no existen hasta que se implementen."
        )
        return 0

    print("\n  ── ¿es diagonal? ──")
    base = etiquetas[0]
    fuera = 0
    for nombre, fila in matriz.items():
        for e in etiquetas[1:]:
            if e != nombre and fila[e] != fila[base]:
                fuera += 1
                print(f"    {nombre} cambia con la condición {e}: {fila[base]} → {fila[e]}")
    if not fuera:
        print("    DIAGONAL — cada condición mueve solo su validador. La independencia")
        print("    queda DEMOSTRADA, no asumida, y la Fase B puede omitirse con razón.")
    else:
        print(f"    NO DIAGONAL — {fuera} celdas fuera. La Fase B del pre-registro de")
        print("    ablación es OBLIGATORIA: los efectos no son separables.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
