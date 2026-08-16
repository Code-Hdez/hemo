#!/usr/bin/env python3
"""Bloque F.1 — ¿propaga Ollama `enum` y `pattern` al GBNF de llama.cpp?

Por qué existe, y por qué va ANTES que nada
-------------------------------------------
Los Bloques H (el servidor pone las cifras) e I (cerrar los actos de habla)
descansan enteros en una premisa que **nadie ha verificado**: que un `enum` en el
`format` de Ollama se convierte de verdad en una alternación GBNF que el
muestreador no puede violar.

Lo que se sabe:

- Ollama **no expone GBNF crudo** (`ollama/ollama#11911`, cerrado como duplicado;
  `#6237` lista nueve PRs de gramática sin resolver). El único camino es `format`
  con JSON Schema, que Ollama convierte internamente.
- El conversor **de llama.cpp** sí soporta `enum`, `const` y `pattern`.
- Pero **Ollama tiene su propia ruta Go de conversión**, y su documentación no
  menciona `enum` ni `pattern`.

Si Ollama no las propaga, H e I no son viables en este motor y hay que decidir
arquitectura con su propio informe. Es un experimento de diez minutos que puede
ahorrar semanas.

El diseño, y por qué no es «repetir 30 veces»
---------------------------------------------
Repetir 30 veces y no ver una violación **no demuestra** que la restricción se
aplique: con 0 de 30, Clopper-Pearson solo acota la tasa de violación en
≤ 9,50 %. Haría falta n = 299 para acotarla en ≤ 1 %.

Lo que sí decide con n pequeño es un **A/B pareado**: la misma pregunta, la misma
semilla, **sin** `format` y **con** `format`. Se eligen preguntas cuyo prior es
abrumador y cuya respuesta correcta **NO está en el enum**:

    «¿Cuánto es 2+2?»   con enum ["siete", "nueve", "once"]

- Si SIN restricción el modelo dice «cuatro» y CON restricción dice «siete», la
  gramática está haciendo el trabajo. **Una sola pareja así ya es concluyente**,
  porque el modelo no tenía ninguna razón para elegir ese token.
- Si CON restricción sigue diciendo «cuatro», o devuelve JSON con un valor fuera
  del enum, Ollama **no** propaga la restricción. **Una sola violación refuta.**

Es asimétrico a propósito: refutar es barato, confirmar es caro. Por eso se
reportan las dos cosas — el veredicto del pareado y la cota superior del
recuento — y nunca se declara «propaga» sin decir con qué n.

Condiciones fijas
-----------------
`temperature: 0`, `stream: false`, `num_ctx` explícito, `seed` fija por sonda
(distinta entre repeticiones, igual entre el brazo libre y el restringido), y
**cero tráfico ajeno**: con `NUM_PARALLEL=1` cualquier otra petición contamina la
medida y, durante el arranque, apaga la VM.

Uso (desde `hemovet-prod`, la única VM que alcanza 10.128.0.3:11434)
--------------------------------------------------------------------
    python3 validacion_llm/scripts/experimento_gramatica.py \
        --base-url http://10.128.0.3:11434 --modelo qwen3.6:27b-q4_K_M \
        --repeticiones 30 --salida veredicto_f1.json
"""

from __future__ import annotations

import argparse
import json
import pathlib
import time
import urllib.error
import urllib.request
from math import comb

# ── Sondas ──────────────────────────────────────────────────────────────────
#
# Cada sonda tiene un `prior` abrumador y un `enum` que lo excluye. Esa es toda
# la potencia del diseño: si la salida restringida cae dentro del enum, no puede
# ser por casualidad ni por complacencia — el modelo no tenía ese token entre sus
# candidatos plausibles.

SONDAS: list[dict] = [
    {
        "id": "aritmetica",
        "pregunta": "¿Cuánto es 2+2? Responde solo el número, en palabras.",
        "enum": ["siete", "nueve", "once"],
        "prior": "cuatro",
        "por_que": "el prior aritmético es máximo; ninguna de las tres opciones es plausible",
    },
    {
        "id": "capital",
        "pregunta": "¿Cuál es la capital de Francia?",
        "enum": ["Lisboa", "Oslo", "Varsovia"],
        "prior": "París",
        "por_que": "conocimiento factual duro, y las tres opciones son capitales reales pero falsas",
    },
    {
        "id": "leucocitos",
        "pregunta": (
            "El recuento de leucocitos de este paciente es 8.40 ×10³/µL. "
            "¿Cuál es el recuento de leucocitos? Responde el valor."
        ),
        "enum": ["4.52", "6.10", "15.20"],
        "prior": "8.40",
        "por_que": "el valor correcto está EN EL PROMPT y aun así se excluye del enum: es el caso de HemoVet",
    },
]

# Un enum grande, para medir el coste de compilación de la gramática. El paper de
# trie-automata (arXiv:2608.12574) mide 0,65 µs por paso de enmascarado y
# compilación sub-100 ms hasta K=10 000; aquí se comprueba en este motor.
ENUM_GRANDE = [f"{v / 100:.2f}" for v in range(100, 400)]  # 300 valores

# `pattern` anclado. Si Ollama lo propaga, la salida debe casar siempre.
SONDA_PATRON = {
    "id": "patron",
    "pregunta": "Escribe el hematocrito del paciente en el formato indicado.",
    "patron": r"^HCT=[0-9]{2}\.[0-9]$",
    "por_que": "sin la gramática el modelo escribe prosa; con ella no puede",
}

# Esquemas mal formados. Hay issues abiertos de agosto-2026 sobre crashes del
# grammar stack de llama.cpp (#26530, #26535, #26658, #26600, #26787), y una
# gramática generada por turno es exactamente ese vector. Interesa saber si un
# esquema torcido tumba el servidor o solo devuelve un error.
ESQUEMAS_TORCIDOS: list[tuple[str, dict]] = [
    ("enum_vacio", {"type": "object", "properties": {"v": {"enum": []}}, "required": ["v"]}),
    ("patron_invalido", {"type": "object", "properties": {"v": {"type": "string", "pattern": "["}}, "required": ["v"]}),
    ("recursivo", {"type": "object", "properties": {"v": {"$ref": "#"}}, "required": ["v"]}),
    ("profundo", {"type": "object", "properties": {"v": {"enum": ["a" * 4000]}}, "required": ["v"]}),
]


# ── Transporte ──────────────────────────────────────────────────────────────


def pedir(base: str, ruta: str, cuerpo: dict, timeout: float = 300.0) -> dict:
    datos = json.dumps(cuerpo).encode()
    peticion = urllib.request.Request(
        base.rstrip("/") + ruta, datos, {"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(peticion, timeout=timeout) as respuesta:
            return json.loads(respuesta.read() or b"{}")
    except urllib.error.HTTPError as exc:
        return {
            "_error": f"http {exc.code}",
            "_cuerpo": exc.read()[:600].decode(errors="replace"),
        }
    except Exception as exc:  # noqa: BLE001
        return {"_error": type(exc).__name__, "_cuerpo": str(exc)[:300]}


def generar(
    base: str,
    modelo: str,
    pregunta: str,
    *,
    formato: dict | None,
    semilla: int,
    num_ctx: int,
    num_predict: int = 160,
    think: bool | None = False,
) -> dict:
    """Una generación. `formato=None` es el brazo LIBRE del pareado.

    `think=False` por defecto, y NO es un detalle
    ---------------------------------------------
    Qwen3.6 es un modelo de *thinking*. Sin `think: false` explícito, Ollama
    v0.32.6 deja pensar al modelo y el razonamiento **consume el presupuesto de
    `num_predict`**: la primera versión de este experimento pedía 24 tokens y las
    33 salidas volvieron **vacías** —`content` = ""—, no con valores erróneos.
    El veredicto automático las contó como violaciones del enum y concluyó «NO
    PROPAGA», que era falso: lo que fallaba era la sonda, no el motor.

    Lo cazó la sub-prueba de dos pasadas, que sí enviaba `think:false` y obtuvo
    `15.20` —dentro del enum— con el mismo modelo y el mismo esquema.

    `num_predict` sube a 160 por el mismo motivo: un margen que no dependa de
    cuánto decida razonar el modelo.
    """
    cuerpo: dict = {
        "model": modelo,
        "messages": [{"role": "user", "content": pregunta}],
        "stream": False,
        "keep_alive": "30m",
        "options": {
            "temperature": 0,
            "top_p": 1.0,
            "top_k": 1,
            "seed": semilla,
            "num_ctx": num_ctx,
            "num_predict": num_predict,
        },
    }
    if formato is not None:
        cuerpo["format"] = formato
    if think is not None:
        cuerpo["think"] = think
    inicio = time.perf_counter()
    respuesta = pedir(base, "/api/chat", cuerpo)
    ms = (time.perf_counter() - inicio) * 1000
    if respuesta.get("_error"):
        return {"error": respuesta["_error"], "detalle": respuesta.get("_cuerpo"), "ms": round(ms, 1)}
    return {
        # CRUDO, íntegro. El GOAL exige registrar cada salida sin recortar: un
        # recorte es exactamente lo que dejó ciega a la Puerta 3.
        "texto": str((respuesta.get("message") or {}).get("content") or ""),
        # Si viene `thinking`, una salida vacía NO es una violación del enum:
        # es que el razonamiento se comió el presupuesto de tokens.
        "trae_thinking": bool((respuesta.get("message") or {}).get("thinking")),
        "done_reason": respuesta.get("done_reason"),
        "eval_count": respuesta.get("eval_count"),
        "ms": round(ms, 1),
    }


def medir_pasadas(
    base: str,
    modelo: str,
    *,
    formato: dict | None,
    think: bool | None,
    semilla: int,
    num_ctx: int,
) -> dict:
    """¿Hace Ollama UNA llamada a llama-server, o DOS?

    Por qué esto puede tumbar el Bloque H entero
    --------------------------------------------
    En `server/routes.go` de Ollama v0.32.6, cuando el modelo tiene capacidad de
    *thinking* —Qwen3.6 la tiene— y se envía `format` **sin** `think: false`
    explícito, Ollama **anula la gramática en la primera pasada**, deja pensar al
    modelo, y luego **reconstruye el prompt y vuelve a llamar** con la gramática:

        if req.Format != nil && ... && !forceImmediate &&
           slices.Contains(m.Capabilities(), model.CapabilityThinking) {
            currentFormat = nil          // la primera pasada va SIN gramática
        }

    Eso rompe a la vez el invariante de una llamada por turno y el presupuesto de
    10-15 s, y lo hace **por debajo del ledger**: el contador cuenta peticiones
    del backend a Ollama, no peticiones de Ollama a llama-server.

    Cómo se detecta desde el cliente, sin leer el log del servidor
    -------------------------------------------------------------
    Ollama informa `total_duration`, `load_duration`, `prompt_eval_duration` y
    `eval_duration` **de la llamada que devuelve**. Si hubo una pasada previa, su
    coste está en el reloj de pared y **no** en esas cifras. El discriminante es
    el residuo:

        residuo = segundos_de_reloj − total_duration_de_ollama

    Un residuo pequeño (décimas) es red y serialización. Un residuo del orden de
    la propia generación significa que hubo trabajo que Ollama no reportó — es
    decir, una pasada extra.

    Se mide en tres condiciones para que el contraste sea interpretable, no una
    cifra suelta.
    """
    cuerpo: dict = {
        "model": modelo,
        "messages": [{"role": "user", "content": SONDAS[-1]["pregunta"]}],
        "stream": False,
        "keep_alive": "30m",
        "options": {
            "temperature": 0,
            "top_p": 1.0,
            "top_k": 1,
            "seed": semilla,
            "num_ctx": num_ctx,
            "num_predict": 64,
        },
    }
    if formato is not None:
        cuerpo["format"] = formato
    if think is not None:
        cuerpo["think"] = think

    inicio = time.perf_counter()
    r = pedir(base, "/api/chat", cuerpo)
    reloj_ms = (time.perf_counter() - inicio) * 1000
    if r.get("_error"):
        return {"error": r["_error"], "detalle": r.get("_cuerpo"), "reloj_ms": round(reloj_ms, 1)}

    ns = lambda k: float(r.get(k) or 0) / 1e6  # noqa: E731 - ns → ms
    total = ns("total_duration")
    mensaje = r.get("message") or {}
    return {
        "reloj_ms": round(reloj_ms, 1),
        "total_duration_ms": round(total, 1),
        "load_duration_ms": round(ns("load_duration"), 1),
        "prompt_eval_duration_ms": round(ns("prompt_eval_duration"), 1),
        "eval_duration_ms": round(ns("eval_duration"), 1),
        "prompt_eval_count": r.get("prompt_eval_count"),
        "eval_count": r.get("eval_count"),
        # LA CIFRA QUE DECIDE: trabajo que el reloj ve y Ollama no reporta.
        "residuo_ms": round(reloj_ms - total, 1),
        "residuo_frac": round((reloj_ms - total) / reloj_ms, 3) if reloj_ms else None,
        # Si viene `thinking`, el modelo pensó — y con `format` activo eso es
        # justo la primera pasada sin gramática.
        "trae_thinking": bool(mensaje.get("thinking")),
        "texto": str(mensaje.get("content") or ""),
    }


def experimento_dos_pasadas(base: str, modelo: str, num_ctx: int, semilla: int) -> dict:
    """Las tres condiciones de §3.2, para que el contraste sea interpretable."""
    sonda = SONDAS[-1]
    esquema = esquema_enum(sonda["enum"])
    condiciones = {
        # Control: sin gramática. El residuo aquí es la línea base de red.
        "sin_format": {"formato": None, "think": None},
        # El caso peligroso: gramática y `think` NULO.
        "format_think_nulo": {"formato": esquema, "think": None},
        # El caso que §3.2 dice que evita la doble pasada.
        "format_think_false": {"formato": esquema, "think": False},
    }
    filas: dict[str, dict] = {}
    for nombre, kw in condiciones.items():
        r = medir_pasadas(base, modelo, semilla=semilla, num_ctx=num_ctx, **kw)
        filas[nombre] = r
        if r.get("error"):
            print(f"  {nombre:22s} ERROR {r['error']}")
            continue
        v = valor_de(r["texto"])
        print(
            f"  {nombre:22s} reloj {r['reloj_ms']:8.1f} ms · ollama {r['total_duration_ms']:8.1f} ms"
            f" · residuo {r['residuo_ms']:8.1f} ms ({r['residuo_frac']:.1%})"
            f" · thinking={r['trae_thinking']} · valor={v!r}"
        )

    base_res = filas.get("sin_format", {}).get("residuo_ms")
    nulo = filas.get("format_think_nulo", {})
    falso = filas.get("format_think_false", {})
    veredicto = "SIN VEREDICTO — alguna condición falló"
    if base_res is not None and nulo.get("residuo_ms") is not None:
        # Doble pasada = el residuo con `think` nulo se dispara frente al control.
        doble = nulo["residuo_ms"] > max(3 * abs(base_res), 1000)
        respeta = valor_de(falso.get("texto", "")) in sonda["enum"] if not falso.get("error") else None
        if doble and not (falso.get("residuo_ms", 0) > max(3 * abs(base_res), 1000)):
            veredicto = (
                "DOBLE PASADA CONFIRMADA con `think` nulo, y `think:false` la evita. "
                "ENVIAR `think: false` EXPLÍCITO ES OBLIGATORIO en toda petición con "
                "`format`, o el Bloque H rompe el invariante de una llamada por turno "
                "por debajo del ledger."
            )
        elif doble:
            veredicto = (
                "DOBLE PASADA CONFIRMADA y `think:false` NO la evita. El Bloque H no "
                "puede cumplir `provider_calls == 1` en este motor: decisión de "
                "arquitectura, con su propio informe."
            )
        else:
            veredicto = (
                "SIN DOBLE PASADA — el residuo con `format` no se distingue del "
                "control. La lógica de dos pasadas de routes.go no se activa aquí."
            )
        if respeta is False:
            veredicto += (
                " AVISO ADICIONAL: con `think:false` la salida NO respetó el enum "
                "(el modo de fallo de ollama#14645/#15260, que se daba por cerrado)."
            )
    print(f"\n  → {veredicto}")
    return {"condiciones": filas, "veredicto": veredicto}


def esquema_enum(valores: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {"valor": {"enum": valores}},
        "required": ["valor"],
    }


def valor_de(texto: str) -> str | None:
    """Extrae `valor` del JSON devuelto. `None` si no es JSON o no lo trae."""
    try:
        datos = json.loads(texto)
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(datos, dict):
        return None
    v = datos.get("valor")
    return None if v is None else str(v)


def cota_superior_violacion(c: int, n: int, alpha: float = 0.05) -> float:
    """Clopper-Pearson: qué tasa de violación NO queda descartada con c en n.

    Con 0 de 30 la cota es 9,50 %: no ver una violación en 30 tiros deja sin
    descartar que una de cada diez peticiones la viole. Se publica siempre, para
    que «30/30 limpio» no se lea como «garantizado».
    """
    if n == 0:
        return 1.0
    if c == 0:
        return 1 - alpha ** (1 / n)
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        s = sum(comb(n, i) * mid**i * (1 - mid) ** (n - i) for i in range(c + 1))
        if s > alpha:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# ── Los cuatro experimentos ─────────────────────────────────────────────────


def experimento_pareado(base: str, modelo: str, num_ctx: int, semilla: int) -> list[dict]:
    """A/B pareado: la misma pregunta y semilla, sin y con `enum`."""
    filas = []
    for sonda in SONDAS:
        libre = generar(base, modelo, sonda["pregunta"], formato=None, semilla=semilla, num_ctx=num_ctx)
        atado = generar(
            base, modelo, sonda["pregunta"],
            formato=esquema_enum(sonda["enum"]), semilla=semilla, num_ctx=num_ctx,
        )
        v = valor_de(atado.get("texto", "")) if not atado.get("error") else None
        dentro = v in sonda["enum"] if v is not None else False
        filas.append({
            "sonda": sonda["id"],
            "prior": sonda["prior"],
            "enum": sonda["enum"],
            "libre": libre,
            "restringido": atado,
            "valor_extraido": v,
            "dentro_del_enum": dentro,
            # Concluyente = el brazo libre NO cae en el enum (así que el modelo no
            # iba a decirlo por su cuenta) y el restringido SÍ.
            "concluyente": bool(
                dentro and not any(e.lower() in libre.get("texto", "").lower() for e in sonda["enum"])
            ),
        })
        print(f"  {sonda['id']:12s} libre={libre.get('texto', libre.get('error'))!r:44.44} "
              f"atado={atado.get('texto', atado.get('error'))!r:34.34} dentro={dentro}")
    return filas


def experimento_recuento(base: str, modelo: str, num_ctx: int, repeticiones: int) -> dict:
    """La sonda clínica, repetida con semillas distintas. Cuenta violaciones."""
    sonda = SONDAS[-1]
    violaciones, vacias, salidas = 0, 0, []
    for i in range(repeticiones):
        r = generar(
            base, modelo, sonda["pregunta"],
            formato=esquema_enum(sonda["enum"]), semilla=20260815 + i, num_ctx=num_ctx,
        )
        v = valor_de(r.get("texto", "")) if not r.get("error") else None
        # Una salida VACÍA no es una violación del enum: es una sonda que no
        # llegó a producir contenido. Distinguirlas es lo que evitó publicar
        # «NO PROPAGA» cuando lo que fallaba era el presupuesto de tokens.
        vacia = not str(r.get("texto") or "").strip()
        fuera = (not vacia) and v not in sonda["enum"]
        violaciones += int(fuera)
        vacias += int(vacia)
        salidas.append({
            "i": i, "texto": r.get("texto"), "valor": v, "fuera": fuera,
            "vacia": vacia, "trae_thinking": r.get("trae_thinking"),
            "error": r.get("error"),
        })
        if fuera:
            print(f"    VIOLACIÓN en i={i}: {r.get('texto')!r}")
    evaluables = repeticiones - vacias
    cota = cota_superior_violacion(violaciones, evaluables) if evaluables else 1.0
    print(f"  {evaluables - violaciones}/{evaluables} dentro del enum "
          f"({vacias} salidas vacías, NO contadas como violación) · "
          f"cota superior 95 % de la tasa de violación: {cota * 100:.2f} %")
    if vacias:
        print(f"    AVISO: {vacias}/{repeticiones} vacías. Si `trae_thinking`, el "
              "razonamiento se comió `num_predict` y la sonda no es concluyente.")
    return {
        "n": repeticiones, "evaluables": evaluables, "vacias": vacias,
        "violaciones": violaciones, "cota_superior": cota, "salidas": salidas,
    }


def experimento_coste(base: str, modelo: str, num_ctx: int) -> dict:
    """¿Cuánto cuesta compilar un enum grande? Se compara con el enum de 3."""
    sonda = SONDAS[-1]
    corto = generar(base, modelo, sonda["pregunta"], formato=esquema_enum(sonda["enum"]),
                    semilla=777, num_ctx=num_ctx)
    largo = generar(base, modelo, sonda["pregunta"], formato=esquema_enum(ENUM_GRANDE),
                    semilla=777, num_ctx=num_ctx)
    patron = generar(base, modelo, SONDA_PATRON["pregunta"],
                     formato={"type": "object",
                              "properties": {"valor": {"type": "string", "pattern": SONDA_PATRON["patron"]}},
                              "required": ["valor"]},
                     semilla=777, num_ctx=num_ctx)
    v_patron = valor_de(patron.get("texto", "")) if not patron.get("error") else None
    import re as _re
    casa = bool(v_patron and _re.fullmatch(SONDA_PATRON["patron"].strip("^$"), v_patron))
    print(f"  enum de 3   : {corto.get('ms')} ms")
    print(f"  enum de {len(ENUM_GRANDE)} : {largo.get('ms')} ms")
    print(f"  pattern     : {patron.get('texto', patron.get('error'))!r} casa={casa}")
    return {
        "enum_corto_ms": corto.get("ms"), "enum_largo_ms": largo.get("ms"),
        "enum_largo_tam": len(ENUM_GRANDE), "enum_largo_valor": valor_de(largo.get("texto", "")),
        "patron": {"salida": patron, "valor": v_patron, "casa": casa},
    }


def experimento_fuzz(base: str, modelo: str, num_ctx: int) -> list[dict]:
    """Esquemas torcidos. Lo que importa es que el servidor SIGA VIVO después."""
    filas = []
    for nombre, esquema in ESQUEMAS_TORCIDOS:
        r = generar(base, modelo, "Responde algo.", formato=esquema, semilla=1, num_ctx=num_ctx, num_predict=8)
        vivo = not (r.get("error") or "").startswith(("URLError", "RemoteDisconnected", "ConnectionReset"))
        filas.append({"esquema": nombre, "resultado": r, "servidor_vivo": vivo})
        print(f"  {nombre:16s} -> {r.get('error') or (r.get('texto') or '')[:60]!r}  vivo={vivo}")
    return filas


# ── Veredicto ───────────────────────────────────────────────────────────────


def veredicto(pareado: list[dict], recuento: dict) -> str:
    """Traduce lo medido a la decisión que gobierna los Bloques H e I."""
    if recuento.get("evaluables", recuento["n"]) == 0:
        return (
            "SIN VEREDICTO — todas las salidas vinieron vacías. Con un modelo de "
            "thinking, el razonamiento consume `num_predict` y `content` vuelve "
            "vacío: es un defecto de la SONDA, no del motor. Enviar `think: false` "
            "y subir `num_predict`."
        )
    if recuento["violaciones"] > 0:
        return (
            "NO PROPAGA — hay al menos una salida fuera del enum. Los Bloques H e I "
            "NO son viables en Ollama tal cual. Evaluar llama-server directo "
            "(-DLLAMA_LLGUIDANCE=ON) o vLLM/SGLang, con su propio informe de coste "
            "y riesgo. UNA violación refuta; no hace falta más muestra."
        )
    concluyentes = [f for f in pareado if f["concluyente"]]
    if not concluyentes:
        return (
            "SIN VEREDICTO — ninguna pareja fue concluyente: el brazo libre ya "
            "producía valores del enum, así que no se puede atribuir el acierto a "
            "la gramática. Rehacer con sondas de prior más fuerte."
        )
    return (
        f"PROPAGA — {len(concluyentes)}/{len(pareado)} parejas concluyentes y "
        f"{recuento['n'] - recuento['violaciones']}/{recuento['n']} dentro del enum. "
        f"La cota superior 95 % de la tasa de violación es "
        f"{recuento['cota_superior'] * 100:.2f} %, que es lo máximo afirmable con "
        f"n={recuento['n']}: NO es «garantizado», es «no refutado a este n». "
        "Los Bloques H e I son viables en el motor actual."
    )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-url", default="http://10.128.0.3:11434")
    p.add_argument("--modelo", required=True)
    p.add_argument("--num-ctx", type=int, default=16384)
    p.add_argument("--semilla", type=int, default=20260815)
    p.add_argument("--repeticiones", type=int, default=30)
    p.add_argument("--salida", default="")
    args = p.parse_args()

    print(f"modelo={args.modelo} num_ctx={args.num_ctx} temperature=0 top_k=1\n")

    print("── 1 · A/B PAREADO · misma pregunta y semilla, sin y con enum ──")
    pareado = experimento_pareado(args.base_url, args.modelo, args.num_ctx, args.semilla)

    print(f"\n── 2 · RECUENTO · la sonda clínica × {args.repeticiones} semillas ──")
    recuento = experimento_recuento(args.base_url, args.modelo, args.num_ctx, args.repeticiones)

    print("\n── 3 · COSTE · enum de 3 vs enum de 300, y `pattern` anclado ──")
    coste = experimento_coste(args.base_url, args.modelo, args.num_ctx)

    print("\n── 4 · FUZZ · esquemas torcidos; ¿sobrevive el servidor? ──")
    fuzz = experimento_fuzz(args.base_url, args.modelo, args.num_ctx)

    print("\n── 5 · ¿UNA llamada a llama-server, o DOS? (§3.2 del prompt maestro) ──")
    pasadas = experimento_dos_pasadas(
        args.base_url, args.modelo, args.num_ctx, args.semilla
    )

    dictamen = veredicto(pareado, recuento)
    print("\n" + "═" * 72)
    print("VEREDICTO F.1 · gramática :", dictamen)
    print("VEREDICTO F.1 · pasadas   :", pasadas["veredicto"])
    print("═" * 72)

    resultados = {
        "modelo": args.modelo, "num_ctx": args.num_ctx, "semilla_base": args.semilla,
        "pareado": pareado, "recuento": recuento, "coste": coste, "fuzz": fuzz,
        "dos_pasadas": pasadas,
        "veredicto": dictamen,
    }
    if args.salida:
        pathlib.Path(args.salida).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(args.salida).write_text(
            json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"escrito: {args.salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
