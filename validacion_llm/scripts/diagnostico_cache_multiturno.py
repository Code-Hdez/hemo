#!/usr/bin/env python3
"""Bloque F.2 — ¿reutiliza la caché en RÉGIMEN multi-turno, o solo en un turno?

Por qué existe, y qué pregunta queda de verdad
----------------------------------------------
El protocolo A/B/C del Bloque C midió **un solo mensaje de usuario, sin historial
creciente** —el caso más favorable posible— y dio 14,5× de reutilización. El
issue `ggml-org/llama.cpp#24587` describe justo el caso contrario: con la
**sección intermedia** del prompt variando entre peticiones (chunks de RAG,
hechos seleccionados), el servidor entra en un bucle de invalidación continua.
Las dos cosas pueden ser ciertas a la vez.

**La mitad en vivo de este experimento ya está respondida, y sin GPU.** Sobre los
198 turnos de `campana_r_2026-08-14` con métricas de prefill:

    ms/token de prefill, p50            0,8241     (frío medido: 0,8716)
    aciertos claros de caché            15/198 = 7,6 %
    reutilización efectiva              10,6 %
    general (case_facts SIEMPRE 0)      19,4 % de aciertos
    ámbitos con paciente                 1,5 %

Es decir: **en régimen no se reutiliza casi nada**, y la hipótesis heredada —«la
culpa es de `case_facts` en el tercer bloque»— **no basta**, porque `general`
tiene ese bloque constante en los 15 turnos y tampoco reutiliza.

Lo que la lectura del código añade, y nadie había nombrado
----------------------------------------------------------
Tres rompe-prefijos ya estaban corregidos y la reutilización sigue en el 10 %:

1. el rol *system* es estable (`_compose_system_prompt` ignora la política);
2. la memoria va **detrás** del historial (commit `75a29a03`);
3. `_select_history` ya **no** reordena por solapamiento léxico con la pregunta.

Queda un cuarto, y es determinista:

    max_groups = max(1, limit // 2)              # limit = CHAT_HISTORY_LIMIT = 12
    selected = [x for g in groups[-max_groups:] for x in g]

Es una **ventana deslizante**. A partir del turno 7, cada turno **tira el turno
más antiguo por delante** del bloque `history_json`, que es el 4.º de 11. El
prefijo muere ahí y con él todo lo que viene detrás: memoria, resumen, fuentes,
catálogo, política, instrucción y pregunta. En producción, **126 de 377**
construcciones de prompt están en el tope de 12 mensajes, o sea con la ventana ya
deslizando.

La pregunta que queda, y que sí necesita GPU
--------------------------------------------
**¿Es capaz este motor de reutilizar en una secuencia creciente, una vez
quitados nuestros propios rompe-prefijos?** O dicho de otro modo: ¿el Test B
—añadir al final— sigue rindiendo cuando se encadena quince veces sobre un
prompt que crece, o la atención lineal de Qwen3.6 lo mata en régimen?

    Brazo APPEND    P1 ⊂ P2 ⊂ … ⊂ P15, cada uno es el anterior MÁS texto al final.
                    Es el mejor caso alcanzable si arregláramos la ventana.
    Brazo VENTANA   simula lo que hace hoy el backend: el mismo crecimiento, pero
                    tirando el bloque más antiguo por delante a partir del 7.º.
    Brazo MEDIO     el prefijo se mantiene y cambia un bloque INTERMEDIO cada vez.
                    Es el caso del `#24587` y el de `sources_json`.

Los tres comparten longitud por paso, así que ms/token es comparable entre ellos.

Regla de decisión, escrita antes de medir
-----------------------------------------
    APPEND reutiliza (p50 < 50 % del frío) y VENTANA no
        -> la culpa es NUESTRA y es arreglable. G.3 rinde: arreglar la ventana y
           mandar lo volátil a la cola. Se implementa con su propia puerta.

    APPEND tampoco reutiliza
        -> la arquitectura híbrida muerde en régimen. Reordenar la plantilla NO
           rinde en este motor: no se invierte ahí. Se documenta y se pasa.

    APPEND y VENTANA reutilizan los dos
        -> el rompe-prefijos no es la ventana. Volver a los datos antes de tocar
           nada; el candidato siguiente es `sources_json`, y lo mide el brazo MEDIO.

Condiciones fijas
-----------------
`seed` constante, `temperature: 0`, `num_predict: 8`, `stream: false`, `num_ctx`
explícito e idéntico, `keep_alive` largo, y **cero tráfico ajeno**: con
`NUM_PARALLEL=1` cualquier otra petición falsea la medida y, durante el arranque,
apaga la VM.

Uso (desde `hemovet-prod`, la única VM que alcanza 10.128.0.3:11434)
--------------------------------------------------------------------
    python3 validacion_llm/scripts/diagnostico_cache_multiturno.py \
        --base-url http://10.128.0.3:11434 --modelo qwen3.6:27b-q4_K_M \
        --salida veredicto_f2.json

    # y, sin GPU, la mitad ya respondida:
    python3 validacion_llm/scripts/diagnostico_cache_multiturno.py --analizar \
        validacion_llm/resultados/campana_r_2026-08-14/c*.jsonl
"""

from __future__ import annotations

import argparse
import glob
import json
import pathlib
import time
import urllib.error
import urllib.request

# Prefill en frío medido en el Bloque C (protocolo A/B/C, 14-ago-2026). Es la
# referencia contra la que se decide si un turno reutilizó o reprocesó.
MS_POR_TOKEN_FRIO = 0.8716
UMBRAL_ACIERTO = MS_POR_TOKEN_FRIO * 0.5

_PARRAFO = (
    "El hemograma canino evalúa la serie roja, la serie blanca y las plaquetas. "
    "La serie roja informa sobre la capacidad de transporte de oxígeno mediante "
    "el recuento de eritrocitos, la hemoglobina y el hematocrito, además de los "
    "índices derivados VCM, HCM y CHCM. La serie blanca describe la respuesta "
    "inmunitaria a través de neutrófilos, linfocitos, monocitos, eosinófilos y "
    "basófilos. Las plaquetas participan en la hemostasia primaria. "
)


def bloque(indice: int, tokens: int = 300) -> str:
    """Un «turno» sintético, distinguible del resto y de tamaño estable."""
    veces = max(1, int(tokens * 3.6 / len(_PARRAFO)))
    return f"\n[TURNO {indice:02d}]\n" + (_PARRAFO * veces)


# ── Transporte ──────────────────────────────────────────────────────────────


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


def medir(base: str, modelo: str, texto: str, num_ctx: int, semilla: int) -> dict:
    """`raw:true` para que el prompt sea EXACTAMENTE lo que enviamos.

    Con `/api/chat` la plantilla del modelo se interpone y no se puede afirmar
    qué bytes vieron el prefijo. El Bloque C ya demostró que `raw:true` y
    `/api/chat` se comportan igual (14,6× frente a 14,5×), así que usar el
    camino sin plantilla no cambia el fenómeno y sí elimina una variable.
    """
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
            "options": {
                "temperature": 0,
                "top_p": 1.0,
                "top_k": 1,
                "seed": semilla,
                "num_ctx": num_ctx,
                "num_predict": 8,
            },
        },
    )
    segundos = time.perf_counter() - inicio
    if cuerpo.get("_error"):
        return {"error": cuerpo["_error"], "detalle": cuerpo.get("_cuerpo")}
    tokens = int(cuerpo.get("prompt_eval_count") or 0)
    prefill_ms = float(cuerpo.get("prompt_eval_duration") or 0) / 1e6
    return {
        "prompt_eval_count": tokens,
        "prompt_eval_ms": round(prefill_ms, 3),
        "ms_por_token": round(prefill_ms / tokens, 4) if tokens else None,
        "acierto": bool(tokens and prefill_ms / tokens < UMBRAL_ACIERTO),
        "segundos_reloj": round(segundos, 3),
    }


# ── Los tres brazos ─────────────────────────────────────────────────────────


def secuencia_append(n: int) -> list[str]:
    """P1 ⊂ P2 ⊂ … ⊂ Pn. Append puro: el mejor caso alcanzable."""
    salida, acumulado = [], ""
    for i in range(1, n + 1):
        acumulado += bloque(i)
        salida.append(acumulado)
    return salida


def secuencia_ventana(n: int, ventana: int = 6) -> list[str]:
    """Lo que hace HOY el backend: ventana deslizante de `ventana` turnos.

    A partir del turno `ventana+1` el más antiguo se cae **por delante**, que es
    exactamente lo que rompe el prefijo en `history_json`.
    """
    salida = []
    for i in range(1, n + 1):
        vivos = range(max(1, i - ventana + 1), i + 1)
        salida.append("".join(bloque(j) for j in vivos))
    return salida


def secuencia_medio(n: int, ventana: int = 6) -> list[str]:
    """Prefijo estable, un bloque INTERMEDIO que cambia. El caso del #24587.

    Reproduce `sources_json`: la cabecera no se mueve, pero en mitad del prompt
    hay un bloque cuyo contenido cambia en cada turno.
    """
    cabeza = "".join(bloque(j) for j in range(1, ventana + 1))
    cola = bloque(99)
    return [cabeza + bloque(1000 + i) + cola for i in range(1, n + 1)]


BRAZOS = {
    "APPEND": (secuencia_append, "append puro — el mejor caso alcanzable"),
    "VENTANA": (secuencia_ventana, "ventana deslizante — lo que hace hoy el backend"),
    "MEDIO": (secuencia_medio, "bloque intermedio variable — el caso del #24587"),
}


def correr_brazo(base: str, modelo: str, nombre: str, n: int, num_ctx: int, semilla: int) -> dict:
    constructor, descripcion = BRAZOS[nombre]
    prompts = constructor(n)
    print(f"\n── BRAZO {nombre} · {descripcion} ──")
    pasos = []
    for i, p in enumerate(prompts, 1):
        r = medir(base, modelo, p, num_ctx, semilla)
        r["paso"] = i
        pasos.append(r)
        if r.get("error"):
            print(f"   {i:2d}  ERROR {r['error']}")
        else:
            print(f"   {i:2d}  {r['prompt_eval_count']:6d} tok  "
                  f"{r['ms_por_token']:.4f} ms/tok  {'ACIERTO' if r['acierto'] else 'reprocesa'}")
    validos = [p for p in pasos if not p.get("error") and p.get("ms_por_token")]
    # El paso 1 es frío por definición: se excluye del resumen, o se estaría
    # castigando a todos los brazos por igual con un dato que no discrimina.
    posteriores = [p for p in validos if p["paso"] > 1]
    m = sorted(p["ms_por_token"] for p in posteriores)
    return {
        "descripcion": descripcion,
        "pasos": pasos,
        "n_validos": len(validos),
        "p50_ms_por_token": m[len(m) // 2] if m else None,
        "aciertos": sum(1 for p in posteriores if p["acierto"]),
        "de": len(posteriores),
    }


def veredicto(res: dict[str, dict]) -> str:
    def reutiliza(nombre: str) -> bool | None:
        p50 = res.get(nombre, {}).get("p50_ms_por_token")
        return None if p50 is None else p50 < UMBRAL_ACIERTO

    a, v, m = reutiliza("APPEND"), reutiliza("VENTANA"), reutiliza("MEDIO")
    if a is None:
        return "SIN VEREDICTO — el brazo APPEND no produjo medidas válidas."
    if a and not v:
        return (
            "LA CULPA ES NUESTRA Y ES ARREGLABLE — el append puro sí reutiliza en "
            "régimen y la ventana deslizante lo mata. El Bloque G.3 RINDE: hay que "
            "arreglar `_select_history` (que tira el turno más antiguo por delante "
            "de `history_json`) y mandar lo volátil a la cola. Va con su propia "
            "puerta y su propia regla de decisión."
        )
    if not a:
        return (
            "LA ARQUITECTURA MUERDE EN RÉGIMEN — ni siquiera el append puro "
            "reutiliza al encadenarlo. El 14,5× del Bloque C era el mejor caso "
            "posible y no se sostiene multi-turno. Reordenar la plantilla NO rinde "
            "en este motor: NO se invierte ahí. Se documenta y se pasa al Bloque G, "
            "que ataca la validez y no la latencia."
        )
    if a and v:
        extra = " Y el bloque intermedio tampoco lo rompe." if m else " Pero el bloque intermedio SÍ lo rompe: el sospechoso es `sources_json`."
        return (
            "LA VENTANA NO ERA EL ROMPE-PREFIJOS — los dos brazos reutilizan." + extra
            + " Volver a los datos antes de tocar nada."
        )
    return "PATRÓN NO PREVISTO — publicar los tres brazos en crudo y decidir a mano."


# ── La mitad que NO necesita GPU ────────────────────────────────────────────


def analizar_en_vivo(rutas: list[str]) -> int:
    """Reutilización real, calculada sobre corridas que ya existen."""
    turnos = []
    for ruta in rutas:
        for linea in pathlib.Path(ruta).read_text(encoding="utf-8").splitlines():
            if not linea.strip():
                continue
            r = json.loads(linea)
            if r.get("_tipo_registro"):
                continue
            if r.get("prompt_eval_count") and r.get("prompt_eval_duration_ms"):
                r["mspt"] = r["prompt_eval_duration_ms"] / r["prompt_eval_count"]
                turnos.append(r)
    if not turnos:
        print("sin turnos con métricas de prefill")
        return 2
    m = sorted(t["mspt"] for t in turnos)
    aciertos = sum(1 for t in turnos if t["mspt"] < UMBRAL_ACIERTO)
    gastado = sum(t["prompt_eval_duration_ms"] for t in turnos)
    si_frio = sum(t["prompt_eval_count"] * MS_POR_TOKEN_FRIO for t in turnos)
    print(f"turnos con métricas de prefill : {len(turnos)}")
    print(f"ms/token p50                   : {m[len(m) // 2]:.4f}   (frío medido: {MS_POR_TOKEN_FRIO})")
    print(f"aciertos claros (< {UMBRAL_ACIERTO:.4f})     : {aciertos}/{len(turnos)} = {aciertos / len(turnos) * 100:.1f} %")
    print(f"reutilización efectiva         : {(1 - gastado / si_frio) * 100:.1f} %")
    print("\npor ámbito:")
    for a in sorted({str(t.get("scope") or "?") for t in turnos}):
        sub = [t for t in turnos if str(t.get("scope") or "?") == a]
        ms = sorted(t["mspt"] for t in sub)
        ac = sum(1 for t in sub if t["mspt"] < UMBRAL_ACIERTO)
        print(f"  {a:<20s} n={len(sub):3d}  p50 {ms[len(ms) // 2]:.4f}  aciertos {ac}/{len(sub)} = {ac / len(sub) * 100:4.1f} %")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--analizar", nargs="*", help="ficheros .jsonl de corridas ya hechas (sin GPU)")
    p.add_argument("--base-url", default="http://10.128.0.3:11434")
    p.add_argument("--modelo", default="")
    p.add_argument("--num-ctx", type=int, default=65536)
    p.add_argument("--semilla", type=int, default=20260815)
    p.add_argument("--pasos", type=int, default=15)
    p.add_argument("--salida", default="")
    args = p.parse_args()

    if args.analizar is not None:
        rutas = [r for patron in (args.analizar or []) for r in sorted(glob.glob(patron))] or args.analizar
        return analizar_en_vivo(rutas)

    if not args.modelo:
        p.error("--modelo es obligatorio para el experimento en vivo")

    print(f"modelo={args.modelo} num_ctx={args.num_ctx} pasos={args.pasos} "
          f"seed={args.semilla} temperature=0 num_predict=8")
    print(f"referencia: prefill frío {MS_POR_TOKEN_FRIO} ms/token · "
          f"umbral de acierto {UMBRAL_ACIERTO:.4f}")

    resultados: dict[str, dict] = {}
    for nombre in ("APPEND", "VENTANA", "MEDIO"):
        resultados[nombre] = correr_brazo(
            args.base_url, args.modelo, nombre, args.pasos, args.num_ctx, args.semilla
        )

    print("\n" + "═" * 72)
    for nombre, r in resultados.items():
        print(f"  {nombre:8s} p50 {r['p50_ms_por_token']} ms/tok   "
              f"aciertos {r['aciertos']}/{r['de']}   ({r['descripcion']})")
    dictamen = veredicto(resultados)
    print()
    print("VEREDICTO F.2:", dictamen)
    print("═" * 72)

    if args.salida:
        pathlib.Path(args.salida).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(args.salida).write_text(
            json.dumps(
                {
                    "modelo": args.modelo, "num_ctx": args.num_ctx, "pasos": args.pasos,
                    "semilla": args.semilla, "ms_por_token_frio": MS_POR_TOKEN_FRIO,
                    "brazos": resultados, "veredicto": dictamen,
                },
                ensure_ascii=False, indent=2,
            ),
            encoding="utf-8",
        )
        print(f"escrito: {args.salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
