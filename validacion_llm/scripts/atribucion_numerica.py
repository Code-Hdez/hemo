#!/usr/bin/env python3
"""¿La cifra publicada corresponde al parámetro que la frase nombra? — sin GPU.

Por qué existe
--------------
`[MEDIDO]` `unsupported_numeric_claim` **sub-detecta**. La ruta numérica de
`claim_validation` compara **fragmentos** de número y le basta una intersección no
vacía con el hecho que aportó el solape de términos:

- el tokenizador parte ``4.52`` en ``4`` y ``52``;
- la fecha aporta ``2026``/``01``/``10``, así que una frase que cite la fecha del
  estudio pasa el control **con cualquier valor**.

Consecuencia para el Bloque H: una gramática que restrinja los slots numéricos
hace la cifra derivada **inescribible**, así que la clase caería a **0 por
construcción**, y su regla sellada leería eso como éxito sin haber demostrado
nada. Ver `BLOQUE_H_LO_QUE_MIDE_DE_VERDAD.md`.

Qué mide esto en su lugar
-------------------------
El resultado primario que **sí** discrimina, y en frío:

===========================  ====================================================
``correcta``                 la cifra es el valor de ESE parámetro en el turno
``mal_atribuida``            la cifra existe en el turno, pero es de OTRO parámetro
``inventada``                la cifra no está en ningún hecho autorizado
===========================  ====================================================

`mal_atribuida` es justo lo que una gramática **no** arregla —lo dice la propia
regla del bloque: *«garantiza que escriba 4,52 en vez de 4,25; no garantiza que
4,52 sea el eritrocito»*—, así que separar las dos es lo que convierte la medición
de H en una prueba en vez de un artefacto.

Requisito
---------
El `.jsonl` debe traer el campo **`case_facts`** con su contenido. `[MEDIDO]` La
campaña v3 solo guardó `n_case_facts`; el campo se añadió a
`correr_puerta_0.py` después, así que esta herramienta **no tiene datos hasta la
siguiente campaña** y lo dice en vez de devolver ceros.
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import pathlib
import re
import unicodedata

RAIZ = pathlib.Path(__file__).resolve().parents[2]

# Una cifra publicable: entero o decimal con coma o punto.
#
# El lookahead lleva `\.\d` y no `.` a secas: con `[\d.,-]` una cifra al FINAL de
# la oración —«…está en 12.4.»— no casaba, porque el punto de cierre entraba en
# la clase. Lo encontró la batería sintética, no la lectura.
_CIFRA = re.compile(r"(?<![\d.,-])(\d{1,3}(?:[.,]\d{1,2})?)(?![\d,]|\.\d)")
_FECHA = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_ORACION = re.compile(r"(?<=[.!?;:\n])\s+")
# `x10³/µL`, `10^9/L`, `x 10 3`: la unidad LLEVA dígitos y se colaban como
# cifras inventadas. Se quitan antes de extraer nada.
_UNIDAD_CIENTIFICA = re.compile(r"[x×]\s*10\s*[\^³⁹]?\s*\d*\s*/?\s*[µu]?[lL]?", re.IGNORECASE)


def _norm(texto: str) -> str:
    sin = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in sin if not unicodedata.combining(c))


def _numero(valor: object) -> str | None:
    crudo = str(valor or "").strip().replace(",", ".")
    m = re.match(r"^-?\d+(?:\.\d+)?$", crudo)
    return crudo if m else None


def turnos(directorio: str) -> list[dict]:
    salida = []
    for ruta in sorted(glob.glob(str(pathlib.Path(directorio) / "c*.jsonl"))):
        for linea in pathlib.Path(ruta).read_text(encoding="utf-8").splitlines():
            if linea.strip():
                reg = json.loads(linea)
                if not reg.get("_tipo_registro"):
                    salida.append(reg)
    return salida


def clasificar(turno: dict) -> list[tuple[str, str, str]]:
    """(veredicto, parámetro nombrado, cifra) por cada cifra atribuida."""
    hechos = turno.get("case_facts") or []
    texto = str(turno.get("respuesta") or "")
    if not hechos or not texto.strip():
        return []

    # valor -> parámetros a los que pertenece
    autorizados: dict[str, set[str]] = collections.defaultdict(set)
    for h in hechos:
        v = _numero(h.get("value"))
        if v:
            autorizados[v].add(str(h.get("code") or h.get("parameter") or "?"))

    # Las unidades del propio turno, para quitarlas literalmente. Es exacto y no
    # depende de una tabla externa que se desincronice.
    unidades = sorted(
        {str(h.get("unit") or "").strip() for h in hechos if str(h.get("unit") or "").strip()},
        key=len,
        reverse=True,
    )

    salida = []
    for oracion in _ORACION.split(texto):
        limpia = _FECHA.sub(" ", oracion)  # la fecha no es una cifra clínica
        for u in unidades:  # `x10³/µL` aporta un `10` que no es del paciente
            limpia = limpia.replace(u, " ")
        limpia = _UNIDAD_CIENTIFICA.sub(" ", limpia)
        cifras = {c.replace(",", ".") for c in _CIFRA.findall(limpia)}
        if not cifras:
            continue
        # ¿qué parámetros nombra esta oración?
        nombrados = set()
        for h in hechos:
            for etiqueta in (h.get("code"), h.get("parameter")):
                if etiqueta and _norm(str(etiqueta)) in _norm(limpia):
                    nombrados.add(str(h.get("code") or h.get("parameter")))
        if not nombrados:
            continue
        for cifra in cifras:
            duenos = autorizados.get(cifra, set())
            if not duenos:
                veredicto = "inventada"
            elif duenos & nombrados:
                veredicto = "correcta"
            else:
                veredicto = "mal_atribuida"
            salida.append((veredicto, "|".join(sorted(nombrados)), cifra))
    return salida


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("condiciones", nargs="+", help="etiqueta=directorio")
    args = p.parse_args()

    print("═" * 74)
    print("ATRIBUCIÓN NUMÉRICA — la cifra, ¿es del parámetro que se nombra?")
    print("═" * 74)

    hubo_datos = False
    for spec in args.condiciones:
        if "=" not in spec:
            p.error(f"«{spec}» no tiene la forma etiqueta=directorio")
        etiqueta, directorio = spec.split("=", 1)
        regs = turnos(directorio)
        con_hechos = [t for t in regs if t.get("case_facts")]
        print(f"\n── {etiqueta}: {len(regs)} turnos, {len(con_hechos)} con `case_facts`")
        if not con_hechos:
            print(
                "     SIN DATOS. Este `.jsonl` no guarda el contenido de `case_facts`.\n"
                "     La campaña v3 solo guardó el recuento; el campo se añadió a\n"
                "     `correr_puerta_0.py` después. No se devuelven ceros como si\n"
                "     fueran un resultado."
            )
            continue
        hubo_datos = True
        cuenta: collections.Counter = collections.Counter()
        ejemplos: dict[str, list] = collections.defaultdict(list)
        for t in con_hechos:
            for veredicto, parametros, cifra in clasificar(t):
                cuenta[veredicto] += 1
                if len(ejemplos[veredicto]) < 5:
                    ejemplos[veredicto].append((t.get("id_caso"), parametros, cifra))
        total = sum(cuenta.values())
        if not total:
            print("     ningún turno atribuye una cifra a un parámetro nombrado")
            continue
        for v in ("correcta", "mal_atribuida", "inventada"):
            n = cuenta[v]
            print(f"     {v:<16s} {n:5d} = {n / total * 100:5.1f} %")
            for caso, par, cif in ejemplos[v][:3]:
                print(f"         [{caso}] {par} → {cif}")
        print(f"     {'total':<16s} {total:5d}")
        print(
            "\n     `mal_atribuida` es lo que una gramática NO arregla. Si sale\n"
            "     alto, el Bloque H no puede reclamar el mérito de bajar\n"
            "     `unsupported_numeric_claim` a cero."
        )

    if not hubo_datos:
        print("\n  Ninguna condición traía `case_facts`. Nada que concluir.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
