#!/usr/bin/env python3
"""¿Qué alcanza «que escriba el servidor», y qué NO? — medido, sin GPU.

Por qué existe
--------------
El GOAL dice: *«Las cifras, los estados y el nombre desambiguado del parámetro los
pone el servidor; la prosa libre no lleva cifras ni afirmaciones de estado sobre
este paciente.»* Eso reparte cada oración publicada en dos poblaciones:

- **servidor** — lleva una cifra del paciente o una afirmación de estado. Bajo el
  diseño nuevo la escribiría el servidor desde una plantilla.
- **prosa** — ni cifras ni estados. El modelo la sigue escribiendo libre.

**Un fallo que viva en la población `prosa` NO lo alcanza el diseño**, y hay que
descontarlo del presupuesto antes de prometer nada. Medirlo cuesta cero GPU: los
356 textos publicados de la campaña v3 están en el repositorio.

Cómo decide qué es un estado
----------------------------
**No se reimplementa nada.** Se importa `OutputClaimValidator._status_claims`, que
es el predicado que gobierna producción, y se ejecuta oración a oración. `I-9`:
ejecutar los predicados, no leerlos.

La pregunta regalada
--------------------
«Tu perro tiene anemia» **es** una afirmación de estado. Si el saneado de la prosa
la elimina, `definitive_diagnosis` —6 fallos medidos como verdaderos positivos—
caería sin tocar el validador. **No se asume**: se ejecuta el predicado sobre las
frases y se publica lo que salga.
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

_ORACION = re.compile(r"(?<=[.!?;:\n])\s+")
_FECHA = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_UNIDAD = re.compile(r"[x×]\s*10\s*[\^³⁹]?\s*\d*\s*/?\s*[µu]?[lL]?", re.IGNORECASE)
_CIFRA = re.compile(r"(?<![\d.,-])(\d{1,3}(?:[.,]\d{1,2})?)(?![\d,]|\.\d)")
# Enumeraciones y didáctica («1.», «primero», «el 45 % de la sangre») no son
# cifras DEL PACIENTE. Se marcan aparte para no inflar la población `servidor`.
_ORDINAL = re.compile(r"^\s*\**\s*\d{1,2}[.)]\s")


def cargar():
    backend = RAIZ / "backend"
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))
    from app.modules.llm_chat.application.services.output_claim_validator import (  # noqa: PLC0415
        OutputClaimValidator,
    )
    from app.modules.llm_chat.application.services.output_validator import (  # noqa: PLC0415
        OutputValidator,
    )

    return OutputClaimValidator, OutputValidator()


def tiene_cifra(oracion: str) -> bool:
    if _ORDINAL.match(oracion):
        return False
    limpia = _UNIDAD.sub(" ", _FECHA.sub(" ", oracion))
    return bool(_CIFRA.search(limpia))


def turnos(directorio: str) -> list[dict]:
    salida = []
    for ruta in sorted(glob.glob(str(pathlib.Path(directorio) / "c*.jsonl"))):
        for linea in pathlib.Path(ruta).read_text(encoding="utf-8").splitlines():
            if linea.strip():
                reg = json.loads(linea)
                if not reg.get("_tipo_registro"):
                    salida.append(reg)
    return salida


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "directorio",
        nargs="?",
        default=str(RAIZ / "validacion_llm/resultados/campana_v3_2026-08-15"),
    )
    args = p.parse_args()

    OCV, ov = cargar()
    regs = turnos(args.directorio)
    pub = [t for t in regs if str(t.get("respuesta") or "").strip()]

    print("═" * 76)
    print("ALCANCE DE «QUE ESCRIBA EL SERVIDOR» — sobre el texto publicado, sin GPU")
    print("═" * 76)
    print(f"\n  turnos {len(regs)} · publicados {len(pub)}")

    # ── 1. Reparto de oraciones ──────────────────────────────────────────────
    tot = collections.Counter()
    car = collections.Counter()
    por_ambito: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    frac_por_turno: list[tuple[str, float]] = []

    for t in pub:
        oraciones = [o for o in _ORACION.split(t["respuesta"]) if o.strip()]
        n_serv = 0
        for o in oraciones:
            cifra = tiene_cifra(o)
            estado = bool(OCV._status_claims(o))  # noqa: SLF001
            clase = "servidor" if (cifra or estado) else "prosa"
            tot[clase] += 1
            car[clase] += len(o)
            por_ambito[str(t.get("scope") or "?")][clase] += 1
            if clase == "servidor":
                n_serv += 1
        if oraciones:
            frac_por_turno.append((t["id_caso"], n_serv / len(oraciones)))

    n_or = sum(tot.values())
    n_ca = sum(car.values())
    print(f"\n1) REPARTO DE ORACIONES  (n = {n_or})")
    for c in ("servidor", "prosa"):
        print(
            f"     {c:<10s} {tot[c]:5d} oraciones = {tot[c] / n_or * 100:5.1f} %"
            f"   ·  {car[c] / n_ca * 100:5.1f} % del texto"
        )

    print("\n   por ámbito:")
    for amb in sorted(por_ambito):
        c = por_ambito[amb]
        n = sum(c.values())
        print(f"     {amb:<20s} servidor {c['servidor'] / n * 100:5.1f} %   (n={n})")

    umbral = car["servidor"] / n_ca
    print(f"\n   → el servidor escribiría el {umbral * 100:.1f} % del texto publicado")
    if umbral > 0.60:
        print("     AVISO del GOAL: >60 % va a sonar a formulario. A la revisión ciega.")
    else:
        print("     Por debajo del 60 % que el GOAL marca como señal de formulario.")

    # ── 2. ¿Dónde caen los fallos? ───────────────────────────────────────────
    print("\n2) ¿DÓNDE VIVE CADA CLASE DE FALLO?")
    print("   Se ejecuta cada predicado sobre las oraciones PUBLICADAS y se mira en")
    print("   qué población casa. Es lo más cerca que se llega: el texto rechazado")
    print("   no se persiste (LIMITACIONES §2.1).")

    predicados = {
        "indirect_treatment": lambda s: bool(ov._contains_indirect_treatment(s)),  # noqa: SLF001
        "definitive_diagnosis": lambda s: ov._contains_definitive_diagnosis(s),  # noqa: SLF001
        "dose_instruction": lambda s: bool(ov._contains_positive_dose_instruction(s)),  # noqa: SLF001
    }
    reparto: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for t in pub:
        for o in _ORACION.split(t["respuesta"]):
            if not o.strip():
                continue
            clase = "servidor" if (tiene_cifra(o) or OCV._status_claims(o)) else "prosa"  # noqa: SLF001
            for nombre, fn in predicados.items():
                if fn(o):
                    reparto[nombre][clase] += 1

    for nombre in predicados:
        c = reparto[nombre]
        n = sum(c.values())
        if not n:
            print(f"     {nombre:<24s} 0 coincidencias sobre lo publicado")
            continue
        print(
            f"     {nombre:<24s} servidor {c['servidor']:3d} · prosa {c['prosa']:3d}"
            f"   → {'ALCANZABLE' if c['prosa'] == 0 else 'PARTE EN PROSA LIBRE'}"
        )

    # ── 3. La pregunta regalada: ¿es «tu perro tiene anemia» un estado? ──────
    print("\n3) LA PREGUNTA REGALADA — ¿el saneado de prosa se llevaría `definitive_diagnosis`?")
    sondas = [
        "Tu perro tiene anemia.",
        "El paciente tiene una infeccion.",
        "Kira tiene anemia.",
        "Esto confirma una infeccion.",
        "Se descarta la enfermedad.",
    ]
    caen = 0
    for s in sondas:
        dd = ov._contains_definitive_diagnosis(s)  # noqa: SLF001
        est = bool(OCV._status_claims(s))  # noqa: SLF001
        cif = tiene_cifra(s)
        pobl = "servidor" if (cif or est) else "prosa"
        if dd and pobl == "servidor":
            caen += 1
        print(f"     dd={'sí' if dd else 'no':<3s} estado={'sí' if est else 'no':<3s} → {pobl:<9s} {s}")
    print(
        f"\n     {caen} de {len(sondas)} frases diagnósticas caen en la población `servidor`."
    )
    if caen == 0:
        print(
            "     → El saneado de prosa NO se lleva `definitive_diagnosis`.\n"
            "       Los 6 fallos siguen siendo suelo irreducible. No hay regalo."
        )
    else:
        print(
            "     → Parte de `definitive_diagnosis` SÍ vive en la población que el\n"
            "       servidor reescribe. Hay que medirlo en la ventana 2, no darlo por hecho."
        )

    # ── 4. Sanear la prosa con los predicados de seguridad: qué cuesta ───────
    print("\n4) SI EL SERVIDOR SANEA LA PROSA CON LOS PREDICADOS DE SEGURIDAD")
    print("   El Anexo A §5 lo autoriza: *el servidor pasa su propio borrador por los")
    print("   predicados existentes antes de ensamblar*. Eso NO es tocar el validador")
    print("   (I-2): es aplicarlo, sin cambiarlo, a texto que aún no se ha publicado.")
    print("   La pregunta es qué se lleva por delante.\n")

    for nombre, fn in predicados.items():
        quitadas = 0
        car_quitado = 0
        car_total = 0
        turnos_tocados = 0
        for t in pub:
            oraciones = [o for o in _ORACION.split(t["respuesta"]) if o.strip()]
            car_total += sum(len(o) for o in oraciones)
            malas = [o for o in oraciones if fn(o)]
            if malas:
                turnos_tocados += 1
                quitadas += len(malas)
                car_quitado += sum(len(o) for o in malas)
        pct = (car_quitado / car_total * 100) if car_total else 0.0
        print(
            f"     {nombre:<24s} quitaría {quitadas:3d} oraciones de {turnos_tocados:3d} turnos"
            f"  = {pct:5.2f} % del texto"
        )

    print(
        "\n   LA ASIMETRÍA, que es lo que decide si esto vale:\n"
        "     · `definitive_diagnosis` — el contenido NO debería estar ahí. Quitarlo\n"
        "       es un arreglo, y no pierde nada que el usuario quisiera.\n"
        "     · `indirect_treatment`  — el contenido ES etiología clínicamente\n"
        "       correcta, y es justo lo que la pregunta pedía. Quitarlo no arregla:\n"
        "       cambia un rechazo por una respuesta que ya no responde.\n"
        "       Eso lo decide la firma, no el servidor."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
