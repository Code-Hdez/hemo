#!/usr/bin/env python3
"""Batería reducida contra producción (https://hemovet.app).

Mide, por ámbito (general / selected_hemogram / hemogram_history):
latencia total, TTFB, etapas vistas (¿reparó?), código de error, fuentes
y respuesta. Incluye una conversación de fluidez de 12 turnos.

Uso:
  python3 bateria_prod.py --email X --password-file pass.txt --salida out.jsonl
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path

import httpx


@dataclass
class Resultado:
    id_caso: str
    scope: str
    pregunta: str
    segundos: float = 0.0
    ttfb: float = 0.0
    http_status: int | None = None
    codigo_error: str | None = None
    etapas: list[str] = field(default_factory=list)
    eventos: int = 0
    reparo: bool = False
    n_fuentes: int = 0
    n_case_facts: int = 0
    respuesta: str = ""
    conversation_id: str | None = None
    turno: int = 0


def _sse_events(response):
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
    r = cliente.post(
        f"{base}/api/v1/auth/login",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={"username": email, "password": password},
    )
    r.raise_for_status()
    return r.json()["access_token"]


def preguntar(
    cliente, base, *, token, browser_session, id_caso, mensaje, scope,
    conversation_id=None, analysis_id=None, pet_id=None, timeout=300.0, turno=0,
) -> Resultado:
    res = Resultado(id_caso=id_caso, scope=scope, pregunta=mensaje, turno=turno)
    cuerpo = {
        "client_message_id": str(uuid.uuid4()),
        "conversation_id": conversation_id,
        "message": mensaje,
        "context_scope": scope,
        "analysis_id": None if scope == "hemogram_history" else analysis_id,
        "pet_id": pet_id if scope != "general" else None,
        "expected_context_revision": None,
        "options": {},
    }
    cabeceras = {
        "Accept": "text/event-stream",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "X-HemoVet-Browser-Session-ID": browser_session,
    }
    inicio = time.perf_counter()
    try:
        with cliente.stream(
            "POST", f"{base}/api/v1/chat/stream",
            headers=cabeceras, json=cuerpo, timeout=timeout,
        ) as r:
            res.http_status = r.status_code
            if r.status_code != 200:
                r.read()
                try:
                    det = r.json().get("detail", {})
                    res.codigo_error = str(det.get("code") or r.status_code) if isinstance(det, dict) else str(r.status_code)
                except Exception:
                    res.codigo_error = str(r.status_code)
                res.segundos = time.perf_counter() - inicio
                return res
            for evento, datos in _sse_events(r):
                if res.eventos == 0:
                    res.ttfb = time.perf_counter() - inicio
                res.eventos += 1
                if evento == "status":
                    etapa = str(datos.get("stage") or "")
                    if etapa:
                        res.etapas.append(etapa)
                    if etapa == "repairing":
                        res.reparo = True
                        razon = str(datos.get("reason") or "")
                        if razon:
                            res.etapas.append(f"reason:{razon}")
                elif evento in {"context_ready", "retrieval_completed", "generation_started"}:
                    res.etapas.append(evento)
                elif evento == "final":
                    res.respuesta = str(datos.get("answer") or "")
                    res.conversation_id = datos.get("conversation_id")
                    res.n_fuentes = len(datos.get("sources") or [])
                    res.n_case_facts = len(datos.get("case_facts") or [])
                elif evento == "error":
                    res.codigo_error = str(datos.get("code") or "error")
                    res.respuesta = str(datos.get("message") or "")
                    res.conversation_id = datos.get("conversation_id") or res.conversation_id
    except httpx.HTTPError as exc:
        res.codigo_error = f"transporte:{type(exc).__name__}"
    res.segundos = time.perf_counter() - inicio
    return res


CASOS_GENERAL = [
    ("GEN-01", "Hola, ¿para qué sirves?"),
    ("GEN-02", "¿En qué puedes ayudarme con un hemograma canino?"),
    ("GEN-05", "Gracias, eso era todo."),
    ("GEN-EDU1", "¿Qué mide el hematocrito en un perro?"),
    ("GEN-EDU2", "¿Qué puede causar leucocitos altos en un perro?"),
    ("GEN-SAFE", "¿Qué dosis de ibuprofeno le doy a mi perro?"),
]

CASOS_SELECTED = [
    ("SEL-PLT-1", "¿Cómo están las plaquetas?"),
    ("SEL-PLT-2", "¿Cómo están las plaquetas?"),
    ("SEL-RANGO", "¿Qué valores están fuera de rango en este hemograma?"),
    ("SEL-RBC", "¿Cómo están sus eritrocitos, hemoglobina y hematocrito?"),
    ("SEL-HALLAZGOS", "No quiero un diagnóstico: dime qué hallazgos debería discutir con el veterinario."),
]

CASOS_HISTORY = [
    ("HIS-INV", "¿Cuántos hemogramas tienes disponibles?"),
    ("HIS-PLT", "¿Cómo cambiaron las plaquetas entre los estudios?"),
    ("HIS-HCT", "¿El hematocrito subió o bajó respecto al estudio anterior?"),
    ("HIS-RESUMEN", "Resume la evolución de este paciente."),
]

FLUIDEZ = [
    "Hola",
    "¿Cómo están las plaquetas?",
    "¿Están cerca de algún límite?",
    "¿Eso significa que tiene una enfermedad?",
    "¿Y los leucocitos?",
    "¿Qué es el hematocrito?",
    "¿El valor de este estudio es normal?",
    "Explícame qué es el RDW.",
    "¿Qué debería preguntarle al veterinario?",
    "¿Puedes resumir todo lo que vimos?",
    "¿Algo más que deba vigilar?",
    "Gracias, eso era todo.",
]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="https://hemovet.app")
    p.add_argument("--email", required=True)
    p.add_argument("--password-file", type=Path, required=True)
    p.add_argument("--salida", type=Path, required=True)
    p.add_argument("--etiqueta", default="")
    p.add_argument("--sin-fluidez", action="store_true")
    p.add_argument("--timeout", type=float, default=300.0)
    args = p.parse_args()

    password = args.password_file.read_text(encoding="utf-8").strip()
    base = args.base_url.rstrip("/")
    browser_session = str(uuid.uuid4())
    resultados: list[Resultado] = []

    with httpx.Client(timeout=60.0) as cliente:
        token = login(cliente, base, args.email, password)
        auth = {"Authorization": f"Bearer {token}"}
        pets = cliente.get(f"{base}/api/v1/pets", headers=auth).json()
        if not pets:
            raise SystemExit("la cuenta no tiene mascotas")
        elegido, estudios = None, []
        for pet in pets:
            h = cliente.get(
                f"{base}/api/v1/history",
                headers=auth, params={"pet_id": pet["id"], "limit": 50},
            ).json()
            if len(h) > len(estudios):
                elegido, estudios = pet, h
        if not elegido or not estudios:
            raise SystemExit("ninguna mascota tiene estudios")
        pet_id = elegido["id"]
        analysis_id = estudios[0]["id"]
        print(f"mascota={elegido.get('name')} estudios={len(estudios)} analysis={analysis_id}")

        def correr(id_caso, msg, scope, conv=None, an=None, turno=0):
            r = preguntar(
                cliente, base, token=token, browser_session=browser_session,
                id_caso=id_caso, mensaje=msg, scope=scope, conversation_id=conv,
                analysis_id=an, pet_id=pet_id, timeout=args.timeout, turno=turno,
            )
            resultados.append(r)
            marca = r.codigo_error or ("REPARO" if r.reparo else "ok")
            print(f"  {id_caso:14s} {r.segundos:6.1f}s ttfb={r.ttfb:4.2f}s [{marca}] fuentes={r.n_fuentes} facts={r.n_case_facts}")
            return r

        print("== GENERAL ==")
        for id_caso, msg in CASOS_GENERAL:
            correr(id_caso, msg, "general")
        print("== SELECTED ==")
        for id_caso, msg in CASOS_SELECTED:
            correr(id_caso, msg, "selected_hemogram", an=analysis_id)
        print("== HISTORY ==")
        for id_caso, msg in CASOS_HISTORY:
            correr(id_caso, msg, "hemogram_history")

        if not args.sin_fluidez:
            print("== FLUIDEZ (12 turnos, una conversación, selected) ==")
            conv = None
            for i, msg in enumerate(FLUIDEZ, start=1):
                r = correr(f"FLU-{i:02d}", msg, "selected_hemogram", conv=conv, an=analysis_id, turno=i)
                conv = r.conversation_id or conv

    with args.salida.open("w", encoding="utf-8") as fh:
        for r in resultados:
            fila = asdict(r)
            fila["etiqueta"] = args.etiqueta
            fh.write(json.dumps(fila, ensure_ascii=False) + "\n")

    print("\n===== RESUMEN =====")
    for scope in ("general", "selected_hemogram", "hemogram_history"):
        del_scope = [r for r in resultados if r.scope == scope and not r.id_caso.startswith("FLU")]
        if not del_scope:
            continue
        tiempos = [r.segundos for r in del_scope]
        errores = [r for r in del_scope if r.codigo_error]
        reparos = [r for r in del_scope if r.reparo]
        print(
            f"{scope:18s} n={len(del_scope):2d} mediana={statistics.median(tiempos):6.1f}s "
            f"max={max(tiempos):6.1f}s errores={len(errores)} reparaciones={len(reparos)}"
        )
    flu = [r for r in resultados if r.id_caso.startswith("FLU")]
    if flu:
        ok = [r for r in flu if not r.codigo_error]
        print(
            f"fluidez            n={len(flu):2d} ok={len(ok)} mediana={statistics.median([r.segundos for r in flu]):6.1f}s "
            f"errores={[r.codigo_error for r in flu if r.codigo_error]}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
