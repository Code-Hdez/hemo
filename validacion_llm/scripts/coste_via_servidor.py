#!/usr/bin/env python3
"""El coste que el validador NO ve: sobre-rechazo, latencia y compilación. Sin GPU.

Por qué existe
--------------
Un sistema que no sirve tampoco pasa. El validador mide validez; **no mide si el
sistema ha dejado de responder, ni cuánto tarda, ni si la prosa quedó mutilada**.
Esas tres cosas deciden si «que escriba el servidor» vale la pena, y ninguna sale
de la puerta.

Se lee todo del **mismo ledger** de la campaña: gratis si el dato está, imposible
si no. Por eso `_decode_slot_generation` registra `prosa_oraciones_quitadas` y
`prosa_motivos_recorte` en `provider_metrics` — sin ese campo el sobre-rechazo
sería invisible.

Los tres criterios, ya fijados
------------------------------
- **Latencia:** `p50 <= 15 s` y `p95 <= 25 s`. `[MEDIDO]` La línea base v3 está en
  **p95 = 24,31 s**: quedan **0,69 s** de margen, así que esto no es un adorno.
- **Sobre-rechazo:** respuestas que no responden. Está medido un 25,4 % en modelos
  de esta familia cerca de la frontera.
- **Compilación del `enum`:** `[MEDIDO]` 1400 ms con 3 valores y 2574 ms con 300.
  Aquí serán decenas, pero entra directo en el p95 y se registra por turno.

Sobre una campaña **anterior** al modo servidor, los campos de saneado no existen
y se reporta **SIN DATOS** en vez de cero. Un cero inventado se lee como «no hubo
recorte», que es lo contrario de «no se midió».
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import math
import pathlib
import statistics


def turnos(directorio: str) -> list[dict]:
    salida = []
    for ruta in sorted(glob.glob(str(pathlib.Path(directorio) / "c*.jsonl"))):
        for linea in pathlib.Path(ruta).read_text(encoding="utf-8").splitlines():
            if linea.strip():
                reg = json.loads(linea)
                if not reg.get("_tipo_registro"):
                    salida.append(reg)
    return salida


def _percentil(valores: list[float], q: float) -> float:
    """Percentil INTERPOLADO."""
    if not valores:
        return float("nan")
    ordenados = sorted(valores)
    k = (len(ordenados) - 1) * q
    bajo, alto = int(k), min(int(k) + 1, len(ordenados) - 1)
    return ordenados[bajo] + (ordenados[alto] - ordenados[bajo]) * (k - bajo)


def _percentil_rango(valores: list[float], q: float) -> float:
    """Percentil por *nearest rank*, el otro convenio habitual.

    `[MEDIDO]` Sobre la campaña v3 los dos convenios dan **24,23 s** y
    **24,31 s** para el p95. La diferencia es de 0,08 s y **normalmente daría
    igual** — pero el criterio es 25 s y el margen medido es de **0,69 s**, así
    que el convenio puede decidir el veredicto. Por eso se publican los dos en
    vez de elegir uno en silencio.
    """
    if not valores:
        return float("nan")
    ordenados = sorted(valores)
    indice = math.ceil(q * len(ordenados)) - 1
    return ordenados[min(max(indice, 0), len(ordenados) - 1)]


def _metricas(turno: dict) -> dict:
    m = turno.get("provider_metrics")
    return m if isinstance(m, dict) else {}


def analizar(etiqueta: str, directorio: str) -> None:
    regs = turnos(directorio)
    pub = [t for t in regs if str(t.get("respuesta") or "").strip()]
    print(f"\n── {etiqueta}: {len(regs)} turnos · {len(pub)} publicados")
    if not regs:
        print("     directorio vacío")
        return

    # ── 1. Latencia ─────────────────────────────────────────────────────────
    seg = [float(t["segundos_cliente"]) for t in regs if t.get("segundos_cliente")]
    if seg:
        p50 = _percentil(seg, 0.50)
        p95i, p95r = _percentil(seg, 0.95), _percentil_rango(seg, 0.95)
        peor = max(p95i, p95r)
        print(f"\n   LATENCIA   p50            {p50:6.2f} s  {'✔' if p50 <= 15 else '✘ >15 s'}")
        print(f"              p95 interpolado {p95i:6.2f} s")
        print(f"              p95 nearest-rank{p95r:6.2f} s")
        print(f"              → se juzga por el PEOR de los dos: {peor:6.2f} s"
              f"  {'✔' if peor <= 25 else '✘ >25 s'}")
        print(f"              margen contra el criterio: {25 - peor:5.2f} s")
        print(f"              máx            {max(seg):6.2f} s   n={len(seg)}")

    # ── 2. Sobre-rechazo ────────────────────────────────────────────────────
    print("\n   SOBRE-RECHAZO")
    con_campo = [t for t in regs if "prosa_oraciones_quitadas" in _metricas(t)]
    if not con_campo:
        print(
            "     SIN DATOS. Este `.jsonl` es anterior al modo servidor: no trae\n"
            "     `prosa_oraciones_quitadas`. No se devuelve 0, que se leería como\n"
            "     «no hubo recorte» en vez de «no se midió»."
        )
    else:
        quitadas = [int(_metricas(t).get("prosa_oraciones_quitadas") or 0) for t in con_campo]
        tocados = [q for q in quitadas if q]
        print(f"     turnos con recorte : {len(tocados)}/{len(con_campo)}"
              f" = {len(tocados) / len(con_campo) * 100:5.2f} %")
        print(f"     oraciones quitadas : {sum(quitadas)}  (media {statistics.mean(quitadas):.2f})")
        motivos: collections.Counter = collections.Counter()
        for t in con_campo:
            for m in str(_metricas(t).get("prosa_motivos_recorte") or "").split(","):
                if m:
                    motivos[m] += 1
        print(f"     motivos            : {dict(motivos.most_common())}")

    # Respuestas que NO responden: turnos publicados con cuerpo muy corto.
    cortas = [t for t in pub if len(str(t.get("respuesta") or "")) < 120]
    print(f"     publicadas < 120 car: {len(cortas)}/{len(pub)}"
          f" = {len(cortas) / len(pub) * 100:5.2f} %" if pub else "")

    # ── 3. Coste de compilar el enum ────────────────────────────────────────
    print("\n   COMPILACIÓN DEL ESQUEMA")
    carga = [
        float(t["load_duration_ms"])
        for t in regs
        if t.get("load_duration_ms") not in (None, "")
    ]
    if carga:
        print(f"     load_duration_ms   p50 {_percentil(carga, 0.50):8.1f}"
              f"  p95 {_percentil(carga, 0.95):8.1f}  máx {max(carga):8.1f}")
        print("     (con el esquema del turno activo, el delta contra la línea base")
        print("      es el coste de compilar el `enum`; sin él, es solo la carga)")

    # ── 4. Llamadas al proveedor ────────────────────────────────────────────
    c = collections.Counter(t.get("provider_calls") for t in regs)
    uno = c.get(1, 0)
    print(f"\n   PROVIDER_CALLS     {dict(sorted(c.items(), key=lambda x: (x[0] is None, x[0])))}")
    print(f"     == 1 en {uno}/{len(regs)} = {uno / len(regs) * 100:5.2f} %")
    print("     AVISO: cuenta llamadas del BACKEND. Con `format` y un modelo de")
    print("     thinking, Ollama puede hacer dos pasadas al motor por cada una, y")
    print("     esas son invisibles al ledger.")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("condiciones", nargs="+", help="etiqueta=directorio")
    args = p.parse_args()

    print("═" * 76)
    print("COSTE DE QUE ESCRIBA EL SERVIDOR — lo que el validador no ve")
    print("═" * 76)
    print("\n  criterios: p50 <= 15 s · p95 <= 25 s · sobre-rechazo · compilación")

    for spec in args.condiciones:
        if "=" not in spec:
            p.error(f"«{spec}» no tiene la forma etiqueta=directorio")
        etiqueta, directorio = spec.split("=", 1)
        analizar(etiqueta, directorio)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
