#!/usr/bin/env python3
"""Puerta 0 — las 45 preguntas con la telemetría de la Fase 0.

Qué mide y por qué
------------------
La línea base ``bateria_a100.jsonl`` guarda diez campos y **ninguna métrica de
servidor**: no hay ``done_reason``, ni ``prompt_eval_duration``, ni forma de
saber cuántas veces se llamó al modelo en un turno. Por eso no puede responder
las preguntas de la Puerta 0, y por eso existe la Fase 0.

Este arnés repite **el mismo corpus, literal**, por el mismo camino que recorre
el navegador, y recoge lo que la instrumentación nueva expone en
``route_trace``:

- ``provider_calls`` y ``provider_call_routes`` — el invariante del rediseño.
- ``provider_metrics.done_reason`` — decide si el bucle de reparación funcionó
  alguna vez. Si en las reparaciones domina ``length``, reparar reproduce el
  truncamiento que debía arreglar.
- ``provider_metrics.prompt_eval_duration_ms`` — el indicador **correcto** del
  acierto de caché de prefijo. No ``prompt_eval_count``, que cuenta tokens
  procesados y no dice si venían de caché.
- ``provider_metrics.residual_duration_ms`` — el tiempo que el proveedor gasta
  fuera de carga, prefill y decode.
- ``size_vram_bytes`` y el ``num_ctx`` efectivo del runner.

Comparabilidad
--------------
Las preguntas se leen del propio fichero de la línea base, con su ``id_caso`` y
su texto exacto, así que la comparación antes/después es sobre el mismo corpus.
Lo que **no** es idéntico: la línea base no dejó constancia de cómo encadenó las
conversaciones. Aquí se abre una conversación por ámbito y se encadena por
``conversation_id``, que es lo que hace producción hoy. Queda declarado.

Uso
---
    python3 validacion_llm/scripts/correr_puerta_0.py \
        --email test5@test.com --password '...' \
        --analysis-id AID --pet-id PID \
        --salida validacion_llm/resultados/puerta_0.jsonl
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import statistics as st
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

RAIZ = pathlib.Path(__file__).resolve().parents[2]
LINEA_BASE = RAIZ / "validacion_llm/resultados/rondas45_2026-08-10/bateria_a100.jsonl"


def pedir(
    base: str,
    ruta: str,
    datos: dict | None = None,
    *,
    token: str | None = None,
    form: bool = False,
    timeout: float = 300.0,
    navegador: str | None = None,
) -> tuple[int, dict]:
    cabeceras: dict[str, str] = {}
    if token:
        cabeceras["Authorization"] = "Bearer " + token
    # CHAT_REQUIRE_BROWSER_SESSION_ID: sin esta cabecera el endpoint responde
    # 422, que es un error DISTINTO del 503 de proveedor caído aunque ambos
    # sean códigos de fallo. Clasificar por el código HTTP y no por el cuerpo es
    # tratar una condición necesaria como suficiente.
    if navegador:
        cabeceras["X-HemoVet-Browser-Session-ID"] = navegador
    if form:
        cuerpo = urllib.parse.urlencode(datos or {}).encode()
        cabeceras["Content-Type"] = "application/x-www-form-urlencoded"
    elif datos is not None:
        cuerpo = json.dumps(datos).encode()
        cabeceras["Content-Type"] = "application/json"
    else:
        cuerpo = None
    peticion = urllib.request.Request(base + ruta, cuerpo, cabeceras)
    try:
        with urllib.request.urlopen(peticion, timeout=timeout) as respuesta:
            return respuesta.status, json.loads(respuesta.read() or b"{}")
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"{}")
    except Exception as exc:  # noqa: BLE001
        return 0, {"detail": {"code": "CLIENT_" + type(exc).__name__}}


def corpus() -> list[dict]:
    """El corpus literal de la línea base, en su orden original."""
    return [
        json.loads(linea)
        for linea in LINEA_BASE.read_text(encoding="utf-8").splitlines()
        if linea.strip()
    ]


def esperar_proveedor(base: str, token: str, *, sondeos: int, pausa: float) -> bool:
    """Espera acotada a que el modelo esté cargado, SIN sondear al proveedor.

    Por qué ya no sondea `/api/v1/chat/health`
    ------------------------------------------
    Esa sonda llegaba a Ollama, que corre con ``NUM_PARALLEL=1``. Durante el
    arranque de la GPU compite con el canario `POST /api/chat` de
    ``deploy/gpu/validate-runtime.sh``, que tiene ``--max-time 60``: el canario
    se queda sin ranura, recibe 0 bytes, `curl` sale con 28,
    ``hemovet-gpu.service`` falla y su ``OnFailure`` ejecuta ``poweroff``.

    Los «desalojos spot» de la sesión anterior eran esto. Las operaciones de GCP
    dicen ``guestTerminate``, no ``preempted``, y el arranque sin sondas termina
    en ``release=applied state=validated``.

    Lo que se hace en su lugar: **esperar sin tocar nada**. Un arranque en frío
    sano tarda ~3,5 min (`/api/generate` de validación ≈204 s, canario ≈1,4 s).
    Quien lanza la campaña debe haber comprobado por journal, en solo lectura,
    que el arranque validó — `hemovet_gpu_startup=ready`— antes de invocar esto.
    """
    espera_total = sondeos * pausa
    print(
        f"  esperando {espera_total:.0f} s SIN sondear al proveedor "
        "(sondear durante el arranque apaga la VM)",
        flush=True,
    )
    time.sleep(espera_total)
    # Una única comprobación, ya fuera de la ventana de arranque. Si el
    # proveedor no está, se aborta sin gastar el corpus.
    #
    # Se devuelve el CUERPO además del veredicto porque el pre-registro v3 §7
    # exige publicar la identidad del runtime —`model`, `digest`,
    # `quantization`— junto a los resultados, y esta respuesta ya la trae. Pedirla
    # otra vez sería una petición más contra la única ranura de `NUM_PARALLEL=1`
    # por un dato que ya está en la mano.
    codigo, cuerpo = pedir(base, "/api/v1/chat/health", token=token, timeout=30)
    listo = bool(cuerpo.get("provider_ready"))
    print(f"  comprobacion unica: http {codigo} provider_ready={listo}", flush=True)
    return (codigo == 200 and listo), cuerpo


def _identidad_runtime(salud: dict) -> dict:
    """Extrae la identidad del proveedor del cuerpo de `/health`.

    Se busca en varias profundidades a propósito: el contrato de ese endpoint ha
    cambiado de forma entre versiones, y una campaña que se quede sin identidad
    de runtime por un cambio de anidamiento es una campaña que no se puede
    auditar. Lo que no aparezca se anota como `None`, nunca se inventa.
    """
    candidatos: list[dict] = [salud]
    for clave in ("provider", "provider_identity", "identity", "runtime", "llm"):
        valor = salud.get(clave)
        if isinstance(valor, dict):
            candidatos.append(valor)
    campos = ("provider", "model", "digest", "quantization", "installed")
    identidad: dict[str, object] = {campo: None for campo in campos}
    for fuente in candidatos:
        for campo in campos:
            valor = fuente.get(campo)
            # Solo escalares. En la forma anidada, `salud["provider"]` es el
            # diccionario entero de identidad, y guardarlo como si fuera el
            # nombre del proveedor metería un objeto donde se espera "ollama" —
            # y de paso cambiaría la huella de la corrida.
            if identidad[campo] is None and isinstance(valor, (str, bool, int, float)):
                identidad[campo] = valor
    return identidad


def _huella_corrida(cabecera: dict) -> str:
    """`run_fingerprint`: un solo campo que resume de qué corrida hablamos.

    El pre-registro v3 §7 lo exige junto a las semillas. Sirve para poder decir
    «estas dos corridas son comparables» sin cotejar ocho campos a mano: si la
    huella coincide, coinciden el modelo, el digest, la cuantización, la release
    leída en la VM y el corpus.

    Deliberadamente NO incluye la semilla ni la marca de tiempo: dos corridas de
    la misma campaña deben compartir huella, que es justo lo que se quiere poder
    afirmar de ellas.
    """
    identidad = cabecera.get("identidad_runtime") or {}
    material = json.dumps(
        {
            "provider": identidad.get("provider"),
            "model": identidad.get("model"),
            "digest": identidad.get("digest"),
            "quantization": identidad.get("quantization"),
            "release_en_vm": cabecera.get("release_en_vm"),
            "corpus": cabecera.get("corpus"),
            "n_turnos": cabecera.get("n_turnos"),
            "base_url": cabecera.get("base_url"),
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


# Solo los campos que hacen falta para comprobar en frío si una cifra publicada
# corresponde al parámetro que la frase nombra. Se dejan fuera `fact_id`,
# `analysis_id` y `study_key`: son identificadores internos, no aportan nada a
# esa comprobación y engordan el fichero por turno.
_CAMPOS_CITABLES = ("code", "parameter", "value", "unit", "status", "study_date")


def _hechos_citables(case_facts: object) -> list[dict]:
    """El conjunto autorizado del turno, tal como lo vio el validador.

    `[MEDIDO]` La campaña v3 solo guardó `n_case_facts` —el recuento—, y con eso
    no se puede distinguir «el modelo inventó una cifra» de «el modelo puso la
    cifra correcta bajo el parámetro equivocado». Esa distinción es el único
    resultado primario que discriminaría el Bloque H, porque
    `unsupported_numeric_claim` cae a 0 **por construcción** bajo una gramática.
    """
    if not isinstance(case_facts, list):
        return []
    salida = []
    for hecho in case_facts:
        if not isinstance(hecho, dict):
            continue
        fila = {c: hecho.get(c) for c in _CAMPOS_CITABLES if hecho.get(c) is not None}
        if fila:
            salida.append(fila)
    return salida


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-url", default="https://hemovet.app")
    p.add_argument("--email", required=True)
    p.add_argument("--password", required=True)
    p.add_argument("--analysis-id", required=True)
    p.add_argument("--pet-id", required=True)
    p.add_argument("--salida", required=True)
    p.add_argument("--sondeos", type=int, default=40)
    p.add_argument("--pausa-sonda", type=float, default=30.0)
    p.add_argument("--pausa-turno", type=float, default=1.0)
    p.add_argument(
        "--etiqueta",
        default="",
        help="Nombre de la corrida dentro de la campaña. Vacío = el del directorio.",
    )
    p.add_argument(
        "--semilla",
        default="-1",
        help=(
            "Semilla declarada de esta corrida, para el registro. El backend usa "
            "hoy seed=-1; el valor se anota tal cual, sin fingir que se aplicó."
        ),
    )
    p.add_argument(
        "--release",
        default="",
        help=(
            "SHA de la release desplegada, LEÍDO EN LA VM y no en GitHub. El "
            "pre-registro v3 §7 lo exige y la trampa del commit vacío es "
            "exactamente creerse el de GitHub. Si se omite, la corrida queda "
            "marcada como release no verificada."
        ),
    )
    p.add_argument(
        "--ambitos",
        default="",
        help=(
            "Ámbitos a ejecutar, separados por comas. Vacío = los tres. "
            "Diagnosticar tres turnos de `general` no exige gastar los 45: "
            "cada batería completa cuesta ~12 min de GPU y arrastra los "
            "502 del desalojo spot a casos que no se están investigando."
        ),
    )
    args = p.parse_args()

    base = args.base_url.rstrip("/")
    casos = corpus()
    if args.ambitos:
        querido = {a.strip() for a in args.ambitos.split(",") if a.strip()}
        # Se filtra por ámbito, NUNCA por id_caso: dentro de un ámbito el orden
        # es la conversación. GEN-13 pregunta «el primer tema que tocamos»; sin
        # los doce turnos previos la pregunta no significa lo mismo y el
        # diagnóstico mediría otra cosa.
        casos = [c for c in casos if c.get("scope") in querido]
    print(f"corpus: {len(casos)} turnos leídos de {LINEA_BASE.name}", flush=True)

    codigo, cuerpo = pedir(
        base,
        "/api/v1/auth/login",
        {"username": args.email, "password": args.password},
        form=True,
    )
    token = (cuerpo or {}).get("access_token")
    if not token:
        print(f"login falló: http {codigo} {cuerpo}", file=sys.stderr)
        return 2
    print("sesión abierta", flush=True)

    print("esperando al proveedor…", flush=True)
    listo, salud = esperar_proveedor(
        base, token, sondeos=args.sondeos, pausa=args.pausa_sonda
    )
    if not listo:
        print(
            "el proveedor no llegó a estar listo; se aborta SIN gastar el corpus",
            file=sys.stderr,
        )
        return 3
    identidad = _identidad_runtime(salud)
    print(
        f"  runtime: model={identidad.get('model')} "
        f"digest={str(identidad.get('digest') or '')[:16]}… "
        f"quant={identidad.get('quantization')}",
        flush=True,
    )
    if not args.release:
        # No se aborta: se avisa. El pre-registro exige el SHA leído EN LA VM, y
        # el arnés no puede leerlo por sí mismo —no tiene SSH—. Que falte es un
        # defecto del procedimiento del operador, y queda escrito en el dato.
        print(
            "  AVISO: --release vacío. El pre-registro v3 §7 exige el SHA leído "
            "EN LA VM, no en GitHub. La corrida se marca sin release verificada.",
            file=sys.stderr,
            flush=True,
        )

    salida = pathlib.Path(args.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    sesion = str(uuid.uuid4())

    # Cabecera de la corrida. El pre-registro exige publicar las semillas y la
    # identidad del runtime junto a los resultados: una campaña de 5 corridas
    # cuyos parámetros no consten no es reproducible ni auditable, y la validez
    # de primera pasada es estocástica (`seed = -1`), así que la semilla forma
    # parte del dato, no del entorno.
    cabecera = {
        "_tipo_registro": "cabecera_corrida",
        "etiqueta": args.etiqueta or salida.parent.name,
        "ts_inicio": dt.datetime.now(dt.UTC).isoformat(),
        "semilla_declarada": args.semilla,
        "base_url": base,
        "corpus": LINEA_BASE.name,
        "n_turnos": len(casos),
        "sesion_navegador": sesion,
        "preregistro": "informes_modelo/PUERTAS_v3_PREREGISTRO.md",
        # §7 del pre-registro v3, que el arnés no cumplía: «Identidad del
        # runtime: model, digest, quantization, size_vram_bytes y release». Los
        # cuatro primeros salen de la comprobación de salud que ya se hacía;
        # `size_vram_bytes` viaja por turno; `release` la lee el operador EN LA
        # VM y la pasa por `--release`, porque leerla en GitHub es justamente la
        # trampa que este proyecto tiene documentada.
        "identidad_runtime": identidad,
        "release_en_vm": args.release or None,
        "release_verificada_en_vm": bool(args.release),
    }
    cabecera["run_fingerprint"] = _huella_corrida(cabecera)
    print(f"  run_fingerprint: {cabecera['run_fingerprint']}", flush=True)
    conversaciones: dict[str, str | None] = {}
    registros: list[dict] = []

    with salida.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps(cabecera, ensure_ascii=False) + "\n")
        fh.flush()
        for indice, caso in enumerate(casos, 1):
            ambito = caso["scope"]
            extra: dict[str, str] = {}
            if ambito == "selected_hemogram":
                extra = {"analysis_id": args.analysis_id, "pet_id": args.pet_id}
            elif ambito == "hemogram_history":
                extra = {"pet_id": args.pet_id}

            peticion = {
                "client_message_id": str(uuid.uuid4()),
                "message": caso["pregunta"],
                "context_scope": ambito,
                **extra,
            }
            if conversaciones.get(ambito):
                peticion["conversation_id"] = conversaciones[ambito]

            # UNA llamada por turno. Sin reintentos, de ningún tipo.
            #
            # Antes había hasta tres intentos «solo si el proveedor está
            # caído». Eso es un reintento, que el GOAL prohíbe, y además borra
            # de los datos justo la no-respuesta que la Puerta D existe para
            # contar: un turno que falló dos veces y respondió a la tercera se
            # registraba como si hubiera respondido a la primera.
            t0 = time.perf_counter()
            codigo, cuerpo = pedir(
                base, "/api/v1/chat", peticion, token=token, navegador=sesion
            )
            ms = (time.perf_counter() - t0) * 1000

            if cuerpo.get("conversation_id"):
                conversaciones[ambito] = cuerpo["conversation_id"]

            traza = cuerpo.get("route_trace") or {}
            metricas = traza.get("provider_metrics") or {}
            # En un error terminal no hay `route_trace`: el motivo viaja en el
            # sobre de error. Sin este rescate, los turnos que mueren de forma
            # terminal —los más difíciles del corpus— se registran sin motivo,
            # que es exactamente lo que dejó ciega a la Puerta 3.
            sobre_error = cuerpo.get("detail") if isinstance(cuerpo.get("detail"), dict) else {}
            motivo = traza.get("first_validation_reason") or sobre_error.get(
                "first_validation_reason"
            )
            registro = {
                "id_caso": caso["id_caso"],
                "scope": ambito,
                "pregunta": caso["pregunta"],
                "orden": indice,
                "ts": dt.datetime.now(dt.UTC).isoformat(),
                "http_status": codigo,
                "segundos_cliente": round(ms / 1000, 3),
                # ── lo que la Fase 0 hizo visible ──
                "provider_calls": traza.get("provider_calls"),
                "provider_call_routes": traza.get("provider_call_routes"),
                "first_validation_reason": motivo,
                # Métrica del Bloque G.2: el parámetro que la pregunta nombraba
                # y que el paciente no tiene. Su regla revierte G.2 por encima
                # del 2 % de los turnos, y sin grabarlo aquí no se puede contar.
                "requested_parameter_absent": traza.get("requested_parameter_absent"),
                "done_reason": metricas.get("done_reason"),
                "prompt_eval_count": metricas.get("prompt_eval_count"),
                "prompt_eval_duration_ms": metricas.get("prompt_eval_duration_ms"),
                "eval_count": metricas.get("eval_count"),
                "eval_duration_ms": metricas.get("eval_duration_ms"),
                "load_duration_ms": metricas.get("load_duration_ms"),
                "total_duration_ms": metricas.get("total_duration_ms"),
                "residual_duration_ms": metricas.get("residual_duration_ms"),
                "queue_wait_ms": metricas.get("queue_wait_ms"),
                "size_vram_bytes": traza.get("size_vram_bytes"),
                # ── lo que ya existía ──
                "generation_attempts": cuerpo.get("generation_attempts"),
                "finish_reason": cuerpo.get("finish_reason"),
                "validation_status": cuerpo.get("validation_status"),
                "duration_ms": cuerpo.get("duration_ms"),
                "conversation_id": cuerpo.get("conversation_id"),
                "n_case_facts": len(cuerpo.get("case_facts") or []),
                # El CONTENIDO, no solo el recuento. Sin esto no se puede
                # comprobar en frío si una cifra publicada corresponde al
                # parámetro que la frase nombra, y ese es el único resultado
                # primario que discriminaría el Bloque H: `unsupported_numeric_claim`
                # cae a 0 por construcción bajo una gramática, así que medirlo
                # contra el validador no probaría nada.
                # (`BLOQUE_H_LO_QUE_MIDE_DE_VERDAD.md` §5.)
                #
                # Privacidad: son los hechos del paciente FIXTURE, y sus mismas
                # cifras ya viajan dentro de `respuesta` en este fichero. No añade
                # exposición; si algún día se corre contra un paciente real, este
                # campo es lo primero que hay que revisar.
                "case_facts": _hechos_citables(cuerpo.get("case_facts")),
                "n_fuentes": len(cuerpo.get("sources") or []),
                "respuesta": cuerpo.get("answer") or "",
                "codigo_error": (cuerpo.get("detail") or {}).get("code")
                if isinstance(cuerpo.get("detail"), dict)
                else None,
                # Comparación contra la línea base, turno a turno.
                "base_segundos": caso.get("segundos"),
                "base_reparo": caso.get("reparo"),
                "base_etapas": caso.get("etapas"),
            }
            registros.append(registro)
            fh.write(json.dumps(registro, ensure_ascii=False) + "\n")
            fh.flush()
            print(
                f"[{indice:02d}/{len(casos)}] {caso['id_caso']:7s} {ambito:18s} "
                f"http {codigo} {ms / 1000:6.1f}s "
                f"calls={registro['provider_calls']} "
                f"done={registro['done_reason']} "
                f"pe={registro['prompt_eval_duration_ms']}",
                flush=True,
            )
            time.sleep(args.pausa_turno)

    resumen(registros)
    print(f"\nescrito: {salida}")
    return 0


def resumen(registros: list[dict]) -> None:
    ok = [r for r in registros if r["http_status"] == 200]
    print("\n═══ PUERTA 0 ═══")
    print(f"turnos            : {len(registros)}   con respuesta: {len(ok)}")

    llamadas = [r["provider_calls"] for r in ok if r["provider_calls"] is not None]
    if llamadas:
        reparto: dict[int, int] = {}
        for n in llamadas:
            reparto[n] = reparto.get(n, 0) + 1
        print(f"provider_calls    : {dict(sorted(reparto.items()))}")
        print(f"  turnos con >1   : {sum(1 for n in llamadas if n > 1)}/{len(llamadas)}")
    else:
        print("provider_calls    : NO EXPUESTO — ¿está desplegada la Fase 0?")

    rutas: dict[str, int] = {}
    for r in ok:
        for ruta in r.get("provider_call_routes") or []:
            rutas[ruta] = rutas.get(ruta, 0) + 1
    if rutas:
        print(f"rutas             : {rutas}")

    # La hipótesis que más importa: ¿por qué terminan las llamadas?
    razones: dict[str, int] = {}
    for r in ok:
        clave = str(r.get("done_reason"))
        razones[clave] = razones.get(clave, 0) + 1
    print(f"done_reason       : {razones}")

    multiples = [r for r in ok if (r["provider_calls"] or 0) > 1]
    if multiples:
        rz: dict[str, int] = {}
        for r in multiples:
            rz[str(r.get("done_reason"))] = rz.get(str(r.get("done_reason")), 0) + 1
        print(f"  en turnos >1 llamada: {rz}")

    pe = [
        r["prompt_eval_duration_ms"]
        for r in ok
        if isinstance(r.get("prompt_eval_duration_ms"), (int, float))
    ]
    if pe:
        print(
            f"prompt_eval_ms    : p50 {st.median(pe):.1f}  min {min(pe):.1f}  max {max(pe):.1f}"
        )
        # Turno 1 frente a los siguientes DENTRO de cada conversación: es la
        # medida de reutilización de prefijo que pide la Puerta 2.
        for ambito in sorted({r["scope"] for r in ok}):
            serie = [
                r["prompt_eval_duration_ms"]
                for r in ok
                if r["scope"] == ambito
                and isinstance(r.get("prompt_eval_duration_ms"), (int, float))
            ]
            if len(serie) > 1:
                resto = st.median(serie[1:])
                print(
                    f"  {ambito:18s} turno1 {serie[0]:8.1f} ms · "
                    f"p50 turnos 2+ {resto:8.1f} ms · "
                    f"ratio {resto / serie[0] * 100 if serie[0] else float('nan'):5.1f} %"
                )

    lat = [r["segundos_cliente"] for r in ok]
    base = [r["base_segundos"] for r in registros if r.get("base_segundos")]
    if lat:
        print(f"latencia cliente  : p50 {st.median(lat):.2f} s   máx {max(lat):.2f} s")
    if base:
        print(f"línea base 10-ago : p50 {st.median(base):.2f} s")


if __name__ == "__main__":
    raise SystemExit(main())
