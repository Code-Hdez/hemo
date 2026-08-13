#!/usr/bin/env python3
"""Sonda puntual contra producción: preguntas sueltas por el camino del navegador."""

import json
import sys
import time
import uuid
from pathlib import Path

import httpx


def sse_events(response):
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


def main() -> int:
    base = "https://hemovet.app"
    email, password, scope, salida = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    preguntas = sys.argv[5:]
    with httpx.Client(timeout=120.0) as c:
        r = c.post(
            f"{base}/api/v1/auth/login",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"username": email, "password": password},
        )
        r.raise_for_status()
        token = r.json()["access_token"]
        auth = {"Authorization": f"Bearer {token}"}
        pets = c.get(f"{base}/api/v1/pets", headers=auth).json()
        pet = pets[0]
        historia = c.get(
            f"{base}/api/v1/history",
            headers=auth,
            params={"pet_id": pet["id"], "limit": 50},
        ).json()
        analysis_id = historia[0]["id"]
        resultados = []
        conv = None
        for pregunta in preguntas:
            cuerpo = {
                "client_message_id": str(uuid.uuid4()),
                "conversation_id": conv,
                "message": pregunta,
                "context_scope": scope,
                "analysis_id": analysis_id if scope == "selected_hemogram" else None,
                "pet_id": pet["id"] if scope != "general" else None,
                "expected_context_revision": None,
                "options": {},
            }
            cab = {
                "Accept": "text/event-stream",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
                "X-HemoVet-Browser-Session-ID": str(uuid.uuid4()),
            }
            fila = {"pregunta": pregunta, "respuesta": "", "codigo_error": None,
                    "reparo": False, "razones": [], "segundos": 0.0}
            inicio = time.perf_counter()
            with c.stream("POST", f"{base}/api/v1/chat/stream", headers=cab,
                          json=cuerpo, timeout=300.0) as r:
                if r.status_code != 200:
                    r.read()
                    fila["codigo_error"] = str(r.status_code)
                else:
                    for evento, datos in sse_events(r):
                        if evento == "status":
                            if datos.get("stage") == "repairing":
                                fila["reparo"] = True
                                if datos.get("reason"):
                                    fila["razones"].append(str(datos["reason"]))
                        elif evento == "final":
                            fila["respuesta"] = str(datos.get("answer") or "")
                            conv = datos.get("conversation_id")
                        elif evento == "error":
                            fila["codigo_error"] = str(datos.get("code") or "error")
                            fila["respuesta"] = str(datos.get("message") or "")
            fila["segundos"] = round(time.perf_counter() - inicio, 1)
            resultados.append(fila)
            print(f"[{fila['segundos']:6.1f}s] {'REPARO ' if fila['reparo'] else ''}"
                  f"{fila['codigo_error'] or 'ok'} | {pregunta}")
            print(fila["respuesta"])
            print("=" * 80)
    with Path(salida).open("a", encoding="utf-8") as fh:
        for fila in resultados:
            fh.write(json.dumps(fila, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
