#!/usr/bin/env python3
"""Valida el despliegue con el banco de 45 preguntas de pruebas_conversacion_3modos.

Bootstrap idempotente: registra (o reutiliza) la cuenta de prueba, asegura una
mascota con >=2 estudios (subiendo el PDF indicado), y corre las 45 preguntas
con una conversación encadenada por modo — el mismo protocolo del compañero.
"""

from __future__ import annotations

import argparse
import csv
import json
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
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="https://hemovet.app")
    p.add_argument("--email", required=True)
    p.add_argument("--password", required=True)
    p.add_argument("--pdf", type=Path, required=True)
    p.add_argument("--casos", type=Path, required=True)
    p.add_argument("--salida", type=Path, required=True)
    p.add_argument("--timeout", type=float, default=300.0)
    p.add_argument("--pet-name", default="Nube")
    args = p.parse_args()

    base = args.base_url.rstrip("/")
    browser_session = str(uuid.uuid4())

    with httpx.Client(timeout=120.0) as c:
        r = c.post(
            f"{base}/api/v1/auth/register",
            json={
                "email": args.email,
                "password": args.password,
                "full_name": "Cuenta Validacion HemoVet",
            },
        )
        if r.status_code not in (201, 409):
            raise SystemExit(f"registro fallo: {r.status_code} {r.text[:200]}")
        print(f"registro: {r.status_code}")

        r = c.post(
            f"{base}/api/v1/auth/login",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"username": args.email, "password": args.password},
        )
        r.raise_for_status()
        token = r.json()["access_token"]
        auth = {"Authorization": f"Bearer {token}"}

        pets = c.get(f"{base}/api/v1/pets", headers=auth).json()
        pet = next((x for x in pets if x["name"] == args.pet_name), None)
        if pet is None:
            r = c.post(
                f"{base}/api/v1/pets",
                headers=auth,
                json={
                    "name": args.pet_name,
                    "sex": "Hembra",
                    "residence_lat": 18.4861,
                    "residence_lng": -69.9312,
                    "residence_source": "pin",
                    "residence_consent": True,
                },
            )
            r.raise_for_status()
            pet = r.json()
        pet_id = pet["id"]
        print(f"mascota: {args.pet_name} ({pet_id})")

        historia = c.get(
            f"{base}/api/v1/history",
            headers=auth,
            params={"pet_id": pet_id, "limit": 50},
        ).json()
        while len(historia) < 2:
            print(f"subiendo estudio ({len(historia)} existentes)...")
            with args.pdf.open("rb") as fh:
                r = c.post(
                    f"{base}/api/v1/analyze",
                    headers=auth,
                    params={"pet_id": pet_id, "extraction_mode": "auto"},
                    files={"file": (args.pdf.name, fh, "application/pdf")},
                    timeout=300.0,
                )
            if r.status_code != 200:
                raise SystemExit(f"analyze fallo: {r.status_code} {r.text[:300]}")
            time.sleep(2)
            historia = c.get(
                f"{base}/api/v1/history",
                headers=auth,
                params={"pet_id": pet_id, "limit": 50},
            ).json()
        analysis_id = historia[0]["id"]
        print(f"estudios: {len(historia)} · analysis mas reciente: {analysis_id}")

        with args.casos.open(encoding="utf-8") as fh:
            casos = list(csv.DictReader(fh))
        print(f"casos: {len(casos)}")

        def renovar_token() -> str:
            r = c.post(
                f"{base}/api/v1/auth/login",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={"username": args.email, "password": args.password},
            )
            r.raise_for_status()
            return r.json()["access_token"]

        conversaciones: dict[str, str | None] = {}
        resultados = []
        for i, caso in enumerate(casos, start=1):
            scope = caso["context_scope"]
            cuerpo = {
                "client_message_id": str(uuid.uuid4()),
                "conversation_id": conversaciones.get(scope),
                "message": caso["prompt"],
                "context_scope": scope,
                "analysis_id": None if scope != "selected_hemogram" else analysis_id,
                "pet_id": pet_id if scope != "general" else None,
                "expected_context_revision": None,
                "options": {},
            }
            cab = {
                "Accept": "text/event-stream",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
                "X-HemoVet-Browser-Session-ID": browser_session,
            }
            fila = {
                "id_caso": caso["id_caso"],
                "scope": scope,
                "pregunta": caso["prompt"],
                "respuesta": "",
                "codigo_error": None,
                "etapas": [],
                "reparo": False,
                "segundos": 0.0,
                "n_fuentes": 0,
                "n_case_facts": 0,
            }
            inicio = time.perf_counter()
            try:
                with c.stream(
                    "POST",
                    f"{base}/api/v1/chat/stream",
                    headers=cab,
                    json=cuerpo,
                    timeout=args.timeout,
                ) as r:
                    if r.status_code == 401:
                        r.read()
                        token = renovar_token()
                        cab["Authorization"] = f"Bearer {token}"
                        print("  (token renovado)")
                        with c.stream(
                            "POST",
                            f"{base}/api/v1/chat/stream",
                            headers=cab,
                            json=cuerpo,
                            timeout=args.timeout,
                        ) as r2:
                            r = r2
                            if r.status_code != 200:
                                r.read()
                                fila["codigo_error"] = str(r.status_code)
                            else:
                                for evento, datos in sse_events(r):
                                    if evento == "status":
                                        etapa = str(datos.get("stage") or "")
                                        if etapa:
                                            fila["etapas"].append(etapa)
                                        if etapa == "repairing":
                                            fila["reparo"] = True
                                    elif evento == "final":
                                        fila["respuesta"] = str(
                                            datos.get("answer") or ""
                                        )
                                        conversaciones[scope] = datos.get(
                                            "conversation_id"
                                        )
                                        fila["n_fuentes"] = len(
                                            datos.get("sources") or []
                                        )
                                        fila["n_case_facts"] = len(
                                            datos.get("case_facts") or []
                                        )
                                    elif evento == "error":
                                        fila["codigo_error"] = str(
                                            datos.get("code") or "error"
                                        )
                    elif r.status_code != 200:
                        r.read()
                        fila["codigo_error"] = str(r.status_code)
                    else:
                        for evento, datos in sse_events(r):
                            if evento == "status":
                                etapa = str(datos.get("stage") or "")
                                if etapa:
                                    fila["etapas"].append(etapa)
                                if etapa == "repairing":
                                    fila["reparo"] = True
                                    razon = str(datos.get("reason") or "")
                                    if razon:
                                        fila["etapas"].append(f"reason:{razon}")
                            elif evento == "final":
                                fila["respuesta"] = str(datos.get("answer") or "")
                                conversaciones[scope] = datos.get("conversation_id")
                                fila["n_fuentes"] = len(datos.get("sources") or [])
                                fila["n_case_facts"] = len(
                                    datos.get("case_facts") or []
                                )
                            elif evento == "error":
                                fila["codigo_error"] = str(
                                    datos.get("code") or "error"
                                )
                                fila["respuesta"] = str(datos.get("message") or "")
            except httpx.HTTPError as exc:
                fila["codigo_error"] = f"transporte:{type(exc).__name__}"
            fila["segundos"] = round(time.perf_counter() - inicio, 1)
            resultados.append(fila)
            marca = fila["codigo_error"] or ("REPARO" if fila["reparo"] else "ok")
            print(
                f"[{i}/{len(casos)}] {fila['id_caso']:8s} {fila['segundos']:6.1f}s "
                f"[{marca}] {len(fila['respuesta'])} chars"
            )

    with args.salida.open("w", encoding="utf-8") as fh:
        for fila in resultados:
            fh.write(json.dumps(fila, ensure_ascii=False) + "\n")
    print(f"guardado: {args.salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
