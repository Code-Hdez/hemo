#!/usr/bin/env python3
"""Bloque C — veredicto MEDIDO sobre la caché de prefijo. Nunca reordenar antes.

Por qué existe
--------------
Reordenar el prompt ya se intentó y está medido: la reutilización efectiva
quedó en **7,9 %** (35 de 38 turnos reevalúan el prompt entero a la tasa plena
de prefill). Seguir moviendo bloques sin un veredicto es perseguir un eje que ya
demostró no rendir.

Hay dos causas candidatas, independientes y las dos reales:

1. **Arquitectura híbrida.** Qwen3.6-27B es `3 × (Gated DeltaNet → FFN) +
   1 × (Gated Attention → FFN)` en 64 capas: 48 de atención lineal con estado
   recurrente y solo 16 de atención completa. Un estado recurrente no se puede
   truncar en un punto arbitrario, así que la reutilización sería **binaria**:
   o append puro, o nada.
2. **La plantilla de chat muta los turnos pasados.** Descarta el razonamiento de
   los turnos de asistente anteriores y emite `<think></think>` vacíos en su
   lugar, lo que introduce la divergencia **en medio del historial** — aguas
   arriba de todo lo que se reordenó.

Este script las separa. No propone un arreglo: produce el veredicto que decide
cuál de los dos arreglos tiene sentido.

El discriminador que cierra el caso
-----------------------------------
Si `/api/generate` con ``"raw": true`` —construyendo nosotros el prompt, sin
plantilla— **sí** reutiliza y `/api/chat` no, **es la plantilla, sin
ambigüedad**. Si ninguno de los dos reutiliza ni con un prompt byte-idéntico, es
el motor.

Condiciones fijas, no negociables
---------------------------------
`seed` constante (con -1 no hay dos turnos comparables), `temperature: 0`,
`num_predict: 8`, `stream: false`, `num_ctx` explícito e idéntico, y **cero
tráfico ajeno al modelo** durante la medición: con ``NUM_PARALLEL=1`` cualquier
otra petición falsea el resultado y, durante el arranque, apaga la VM.

Uso (desde la VM de CPU, por IAP, contra la GPU en 10.128.0.3:11434)
-------------------------------------------------------------------
    python3 validacion_llm/scripts/diagnostico_cache.py \
        --base-url http://10.128.0.3:11434 --modelo qwen3.6:27b-q4_K_M
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request

# Un prompt realista de >= 4 000 tokens. Se construye por repetición de prosa
# clínica en español para que la tokenización se parezca a la de producción; un
# relleno de "aaaa" tokeniza distinto y mediría otra cosa.
_PARRAFO = (
    "El hemograma canino evalúa la serie roja, la serie blanca y las plaquetas. "
    "La serie roja informa sobre la capacidad de transporte de oxígeno mediante "
    "el recuento de eritrocitos, la hemoglobina y el hematocrito, además de los "
    "índices derivados VCM, HCM y CHCM. La serie blanca describe la respuesta "
    "inmunitaria a través de neutrófilos, linfocitos, monocitos, eosinófilos y "
    "basófilos. Las plaquetas participan en la hemostasia primaria y su recuento "
    "puede verse alterado por agregación en el contador automático. "
)


def prompt_largo(tokens_objetivo: int = 4200) -> str:
    """Prosa clínica repetida hasta el tamaño pedido (~3,6 car/token)."""
    veces = max(1, int(tokens_objetivo * 3.6 / len(_PARRAFO)))
    return (_PARRAFO * veces).strip()


def pedir(base: str, ruta: str, cuerpo: dict, timeout: float = 600.0) -> dict:
    datos = json.dumps(cuerpo).encode()
    peticion = urllib.request.Request(
        base.rstrip("/") + ruta, datos, {"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(peticion, timeout=timeout) as respuesta:
            return json.loads(respuesta.read() or b"{}")
    except urllib.error.HTTPError as exc:
        return {"_error": f"http {exc.code}", "_cuerpo": exc.read()[:400].decode(errors="replace")}
    except Exception as exc:  # noqa: BLE001
        return {"_error": type(exc).__name__}


def opciones(num_ctx: int, semilla: int) -> dict:
    return {
        "temperature": 0,
        "num_predict": 8,
        "num_ctx": num_ctx,
        "seed": semilla,
        # keep_alive largo: que el runner no se descargue entre pruebas, o se
        # estaría midiendo la recarga en lugar de la caché.
        "top_p": 1.0,
        "top_k": 1,
    }


def medir_chat(base: str, modelo: str, mensajes: list[dict], num_ctx: int, semilla: int) -> dict:
    inicio = time.perf_counter()
    cuerpo = pedir(
        base,
        "/api/chat",
        {
            "model": modelo,
            "messages": mensajes,
            "stream": False,
            "keep_alive": "30m",
            "options": opciones(num_ctx, semilla),
        },
    )
    return _resumen(cuerpo, time.perf_counter() - inicio)


def medir_raw(base: str, modelo: str, texto: str, num_ctx: int, semilla: int) -> dict:
    """`raw: true` salta la plantilla: el prompt es exactamente lo que enviamos."""
    inicio = time.perf_counter()
    cuerpo = pedir(
        base,
        "/api/generate",
        {
            "model": modelo,
            "prompt": texto,
            "raw": True,
            "stream": False,
            "keep_alive": "30m",
            "options": opciones(num_ctx, semilla),
        },
    )
    return _resumen(cuerpo, time.perf_counter() - inicio)


def _resumen(cuerpo: dict, segundos: float) -> dict:
    if cuerpo.get("_error"):
        return {"error": cuerpo["_error"], "detalle": cuerpo.get("_cuerpo")}
    tokens = int(cuerpo.get("prompt_eval_count") or 0)
    prefill_ms = float(cuerpo.get("prompt_eval_duration") or 0) / 1e6
    return {
        "prompt_eval_count": tokens,
        "prompt_eval_ms": round(prefill_ms, 3),
        # La métrica honesta. El cociente turno-2+/turno-1 sube por crecimiento
        # del historial aunque la caché funcione: mide otra cosa.
        "ms_por_token": round(prefill_ms / tokens, 4) if tokens else None,
        "eval_count": cuerpo.get("eval_count"),
        "load_ms": round(float(cuerpo.get("load_duration") or 0) / 1e6, 1),
        "segundos_reloj": round(segundos, 3),
    }


def veredicto(a: dict, b: dict, c: dict, base_fria: float) -> str:
    """Traduce las tres medidas a uno de los tres diagnósticos posibles."""
    faltan = [n for n, r in (("A", a), ("B", b), ("C", c)) if r.get("error")]
    if faltan:
        return f"SIN VEREDICTO — fallaron los tests {faltan}"
    ma, mb, mc = a["ms_por_token"], b["ms_por_token"], c["ms_por_token"]
    if None in (ma, mb, mc):
        return "SIN VEREDICTO — el proveedor no devolvió prompt_eval_count"
    rapido = base_fria * 0.5  # la mitad del prefill frío ya es reutilización clara
    if ma < rapido and mb < rapido and mc >= rapido:
        return (
            "CACHE SANA — el problema es el CONTENIDO del prompt, no el motor. "
            "Toca estabilizar lo que cambia al principio."
        )
    if ma < rapido and mb >= rapido and mc >= rapido:
        return (
            "ARQUITECTURA HIBRIDA CONFIRMADA — la reutilizacion es binaria: un "
            "solo token distinto al final ya cuesta lo mismo que uno al "
            "principio. Dejar de perseguir la cache y REDUCIR TOKENS, que es "
            "determinista."
        )
    if ma >= rapido:
        return (
            "LA CACHE NI SE CONSULTA — ni siquiera un prompt byte-identico "
            "reutiliza. O hay trafico robando la ranura, o es un bug del motor."
        )
    return "PATRON NO PREVISTO — publicar las tres medidas en crudo y decidir a mano."


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-url", default="http://10.128.0.3:11434")
    p.add_argument("--modelo", required=True)
    p.add_argument("--num-ctx", type=int, default=65536)
    p.add_argument("--semilla", type=int, default=20260814)
    p.add_argument("--tokens", type=int, default=4200)
    p.add_argument("--salida", default="")
    args = p.parse_args()

    P = prompt_largo(args.tokens)
    print(f"prompt de {len(P)} caracteres (~{len(P) / 3.6:.0f} tokens estimados)")
    print(f"seed={args.semilla} temperature=0 num_predict=8 num_ctx={args.num_ctx}\n")

    resultados: dict[str, object] = {
        "modelo": args.modelo,
        "semilla": args.semilla,
        "num_ctx": args.num_ctx,
        "caracteres_prompt": len(P),
    }

    def usuario(texto: str) -> list[dict]:
        return [{"role": "user", "content": texto}]

    print("── línea base fría: el mismo prompt, primera vez ──")
    fria = medir_chat(args.base_url, args.modelo, usuario(P), args.num_ctx, args.semilla)
    print(f"   {fria}")
    resultados["base_fria"] = fria
    if fria.get("error") or not fria.get("ms_por_token"):
        print("no hay línea base; se aborta sin sacar conclusiones")
        return 2
    base = fria["ms_por_token"]

    print("\n── TEST A · P, luego P byte-idéntico ──")
    a = medir_chat(args.base_url, args.modelo, usuario(P), args.num_ctx, args.semilla)
    print(f"   {a}")

    print("\n── TEST B · P + 1 carácter AL FINAL ──")
    b = medir_chat(args.base_url, args.modelo, usuario(P + "."), args.num_ctx, args.semilla)
    print(f"   {b}")

    print("\n── TEST C · 1 carácter AL PRINCIPIO + P ──")
    c = medir_chat(args.base_url, args.modelo, usuario("." + P), args.num_ctx, args.semilla)
    print(f"   {c}")

    resultados.update({"A": a, "B": b, "C": c})

    print("\n── DISCRIMINADOR · /api/generate con raw:true (sin plantilla) ──")
    raw1 = medir_raw(args.base_url, args.modelo, P, args.num_ctx, args.semilla)
    raw2 = medir_raw(args.base_url, args.modelo, P, args.num_ctx, args.semilla)
    print(f"   1.ª: {raw1}")
    print(f"   2.ª: {raw2}")
    resultados.update({"raw_1": raw1, "raw_2": raw2})

    print("\n" + "═" * 68)
    print(f"línea base fría : {base:.4f} ms/token")
    for nombre, r in (("A", a), ("B", b), ("C", c)):
        m = r.get("ms_por_token")
        print(f"  test {nombre} : {m} ms/token" + (f"  ({base / m:.1f}× más rápido)" if m else ""))
    if not raw2.get("error") and raw2.get("ms_por_token"):
        m2 = raw2["ms_por_token"]
        print(f"  raw 2.ª : {m2} ms/token  ({base / m2:.1f}× más rápido)")
        if a.get("ms_por_token") and m2 < a["ms_por_token"] * 0.5:
            print("\n  >>> raw reutiliza y /api/chat NO: ES LA PLANTILLA, sin ambigüedad.")
    print()
    dictamen = veredicto(a, b, c, base)
    resultados["veredicto"] = dictamen
    print("VEREDICTO:", dictamen)
    print("═" * 68)

    if args.salida:
        import pathlib

        pathlib.Path(args.salida).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(args.salida).write_text(
            json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"escrito: {args.salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
