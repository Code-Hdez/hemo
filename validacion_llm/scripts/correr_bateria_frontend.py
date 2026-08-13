"""Batería F: el mismo camino que recorre el navegador, no un atajo por consola.

Por qué existe
--------------
El resto de las baterías (`_comun.construir_contenedor`) instancia el contenedor
de chat **dentro** del contenedor Docker y llama al caso de uso en proceso. Eso
mide el motor, pero se salta todo lo que hay entre el usuario y el motor: HTTPS,
Caddy, la autenticación con JWT, el router HTTP, la validación de esquema de la
petición, la cabecera de sesión de navegador y el transporte SSE. Una defensa
puede objetar, con razón, que lo demostrado en consola no es lo que ocurre
cuando alguien escribe en la interfaz.

Esta batería no importa nada del backend. Abre sesión, manda cada pregunta a
``POST /api/v1/chat/stream`` y consume el flujo de eventos exactamente como lo
hace ``streamChatOnce`` en ``frontend_4/src/app/api.ts``:

- ``Accept: text/event-stream``, ``Cache-Control: no-cache``,
  ``Content-Type: application/json``
- ``Authorization: Bearer <token>`` obtenido de ``POST /auth/login`` con
  ``application/x-www-form-urlencoded`` (``username``/``password``)
- ``X-HemoVet-Browser-Session-ID``: un UUID por ejecución, como el que el
  frontend guarda en ``sessionStorage`` para toda la pestaña
- cuerpo con ``client_message_id``, ``conversation_id``, ``message``,
  ``context_scope``, ``analysis_id``, ``pet_id``, ``options: {}``

La conversación se encadena igual que en la interfaz: el primer turno va sin
``conversation_id`` y los siguientes reutilizan el que devolvió el servidor.

Uso
---
    python3 validacion_llm/scripts/correr_bateria_frontend.py \\
        --base-url https://hemovet.app \\
        --email UNO@EJEMPLO.COM --password '...' \\
        --casos validacion_llm/casos/casos_bateria_frontend.csv \\
        --analysis-id AID --pet-id PID \\
        --salida validacion_llm/resultados/eval_bateria_frontend.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import httpx

# El frontend manda el scope canónico y solo cae a los nombres heredados si el
# servidor responde 422 sin envoltorio tipado (api.ts, streamChat).
_FALLBACK_SCOPE = {
    "selected_hemogram": "uploaded_analysis",
    "hemogram_history": "historical_analysis",
}


@dataclass
class Resultado:
    id_caso: str
    scope: str
    pregunta: str
    respuesta: str = ""
    codigo_error: str | None = None
    http_status: int | None = None
    segundos: float = 0.0
    etapas: list[str] = field(default_factory=list)
    conversation_id: str | None = None
    claim_ids: list[str] = field(default_factory=list)
    verified_fact_ids: list[str] = field(default_factory=list)
    eventos: int = 0


def _sse_events(response: httpx.Response) -> Iterator[tuple[str, dict[str, Any]]]:
    """Parsea el flujo SSE tal y como lo hace SseParser en el frontend."""
    nombre = "message"
    datos: list[str] = []
    for linea in response.iter_lines():
        if linea == "":
            if datos:
                crudo = "\n".join(datos)
                try:
                    yield nombre, json.loads(crudo)
                except json.JSONDecodeError:
                    yield nombre, {"_crudo": crudo}
            nombre, datos = "message", []
            continue
        if linea.startswith(":"):
            continue
        if linea.startswith("event:"):
            nombre = linea[6:].strip()
        elif linea.startswith("data:"):
            datos.append(linea[5:].lstrip())


def login(cliente: httpx.Client, base: str, email: str, password: str) -> str:
    respuesta = cliente.post(
        f"{base}/api/v1/auth/login",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={"username": email, "password": password},
    )
    respuesta.raise_for_status()
    token = respuesta.json()["access_token"]
    if not token:
        raise SystemExit("el login no devolvió access_token")
    return token


def preguntar(
    cliente: httpx.Client,
    base: str,
    *,
    token: str,
    browser_session: str,
    mensaje: str,
    scope: str,
    conversation_id: str | None,
    analysis_id: str | None,
    pet_id: str | None,
    timeout: float,
) -> Resultado:
    resultado = Resultado(id_caso="", scope=scope, pregunta=mensaje)
    cuerpo: dict[str, Any] = {
        "client_message_id": str(uuid.uuid4()),
        "conversation_id": conversation_id,
        "message": mensaje,
        "context_scope": scope,
        "analysis_id": None if scope == "hemogram_history" else analysis_id,
        "pet_id": pet_id,
        "expected_context_revision": None,
        "options": {},
    }
    cabeceras = {
        "Accept": "text/event-stream",
        "Cache-Control": "no-cache",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "X-HemoVet-Browser-Session-ID": browser_session,
    }
    inicio = time.perf_counter()
    try:
        with cliente.stream(
            "POST",
            f"{base}/api/v1/chat/stream",
            headers=cabeceras,
            json=cuerpo,
            timeout=timeout,
        ) as respuesta:
            resultado.http_status = respuesta.status_code
            if respuesta.status_code != 200:
                respuesta.read()
                detalle = respuesta.json().get("detail", {})
                if isinstance(detalle, dict):
                    resultado.codigo_error = str(detalle.get("code") or respuesta.status_code)
                    resultado.respuesta = str(detalle.get("message") or "")
                else:
                    resultado.codigo_error = str(respuesta.status_code)
                resultado.segundos = time.perf_counter() - inicio
                return resultado
            for evento, datos in _sse_events(respuesta):
                resultado.eventos += 1
                if evento == "status":
                    etapa = str(datos.get("stage") or "")
                    if etapa:
                        resultado.etapas.append(etapa)
                elif evento == "final":
                    resultado.respuesta = str(datos.get("answer") or "")
                    resultado.conversation_id = datos.get("conversation_id")
                    traza = datos.get("route_trace") or {}
                    if isinstance(traza, dict):
                        resultado.claim_ids = list(traza.get("claim_ids") or [])
                        resultado.verified_fact_ids = list(
                            traza.get("verified_fact_ids") or []
                        )
                elif evento == "error":
                    resultado.codigo_error = str(datos.get("code") or "error")
                    resultado.respuesta = str(datos.get("message") or "")
                    resultado.conversation_id = datos.get("conversation_id")
                # El turno terminó: cerrar aquí, como hace el navegador
                # (`while (!finalResponse)` en frontend_4/src/app/api.ts).
                # Sin esto el cliente sigue leyendo hasta que el servidor
                # cierra o vence --timeout, y una batería de 51 casos con
                # turnos de 30 s tardaba ~7 horas en vez de ~30 minutos.
                # Solo afectaba a la medición: el frontend nunca tuvo el
                # problema.
                if evento in {"final", "error"}:
                    break
    except httpx.HTTPError as exc:
        resultado.codigo_error = f"transporte:{type(exc).__name__}"
    resultado.segundos = time.perf_counter() - inicio
    return resultado


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="https://hemovet.app")
    parser.add_argument("--email", required=True)
    # Un fichero, no un argumento: los argumentos son visibles en `ps` para
    # cualquier usuario de la máquina y quedan en el historial del shell.
    parser.add_argument("--password")
    parser.add_argument("--password-file", type=Path)
    parser.add_argument("--casos", type=Path, required=True)
    parser.add_argument("--analysis-id")
    parser.add_argument("--pet-id")
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--salida", type=Path, required=True)
    args = parser.parse_args()

    if args.password_file:
        password = args.password_file.read_text(encoding="utf-8").strip()
    elif args.password:
        password = args.password
    else:
        raise SystemExit("hace falta --password o --password-file")

    base = args.base_url.rstrip("/")
    casos = list(csv.DictReader(args.casos.open(encoding="utf-8")))
    if not casos:
        raise SystemExit(f"sin casos en {args.casos}")

    # Un identificador de sesión de navegador por ejecución, como una pestaña.
    browser_session = str(uuid.uuid4())
    resultados: list[Resultado] = []
    # Una conversación por hilo, igual que la interfaz: los casos que comparten
    # `hilo` encadenan conversation_id para poder medir memoria multi-turno.
    conversaciones: dict[str, str] = {}

    with httpx.Client(follow_redirects=True, timeout=args.timeout) as cliente:
        token = login(cliente, base, args.email, password)
        print(f"sesión iniciada como {args.email}", flush=True)
        for indice, caso in enumerate(casos, start=1):
            scope = (caso.get("context_scope") or "general").strip()
            hilo = (caso.get("hilo") or caso.get("id_caso") or str(indice)).strip()
            necesita = scope in {"selected_hemogram", "hemogram_history"}
            if necesita and not args.analysis_id:
                print(f"[{indice}/{len(casos)}] {caso.get('id_caso')}: omitido (sin --analysis-id)")
                continue
            resultado = preguntar(
                cliente,
                base,
                token=token,
                browser_session=browser_session,
                mensaje=(caso.get("prompt") or "").strip(),
                scope=scope,
                conversation_id=conversaciones.get(hilo),
                analysis_id=args.analysis_id if necesita else None,
                pet_id=args.pet_id if necesita else None,
                timeout=args.timeout,
            )
            resultado.id_caso = (caso.get("id_caso") or str(indice)).strip()
            if resultado.conversation_id:
                conversaciones[hilo] = resultado.conversation_id
            resultados.append(resultado)
            estado = resultado.codigo_error or "ok"
            print(
                f"[{indice}/{len(casos)}] {resultado.id_caso} {scope} "
                f"{estado} {resultado.segundos:.1f}s "
                f"{len(resultado.respuesta)} chars",
                flush=True,
            )

    args.salida.parent.mkdir(parents=True, exist_ok=True)
    with args.salida.open("w", encoding="utf-8", newline="") as fh:
        escritor = csv.writer(fh)
        escritor.writerow(
            [
                "id_caso",
                "context_scope",
                "pregunta",
                "respuesta",
                "codigo_error",
                "http_status",
                "segundos",
                "eventos_sse",
                "etapas",
                "claim_ids",
                "verified_fact_ids",
                "conversation_id",
            ]
        )
        for r in resultados:
            escritor.writerow(
                [
                    r.id_caso,
                    r.scope,
                    r.pregunta,
                    r.respuesta,
                    r.codigo_error or "",
                    r.http_status or "",
                    f"{r.segundos:.2f}",
                    r.eventos,
                    "|".join(r.etapas),
                    "|".join(r.claim_ids),
                    "|".join(r.verified_fact_ids),
                    r.conversation_id or "",
                ]
            )

    fallidos = [r for r in resultados if r.codigo_error]
    tiempos = [r.segundos for r in resultados]
    print("\n--- resumen ---")
    print(f"casos            : {len(resultados)}")
    print(f"con error        : {len(fallidos)}")
    if fallidos:
        codigos: dict[str, int] = {}
        for r in fallidos:
            codigos[r.codigo_error or "?"] = codigos.get(r.codigo_error or "?", 0) + 1
            print(f"  {r.id_caso}: {r.codigo_error}")
        print(f"por código       : {codigos}")
    if tiempos:
        print(f"latencia mediana : {statistics.median(tiempos):.1f} s")
        print(f"latencia máxima  : {max(tiempos):.1f} s")
    print(f"salida           : {args.salida}")
    return 1 if fallidos else 0


if __name__ == "__main__":
    sys.exit(main())
