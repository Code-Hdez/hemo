"""Prueba adversaria: ¿honra Ollama la gramática que HemoVet le envía?

La prueba de la fase anterior (prompt_eval_count 40 vs 40) no discrimina: es
compatible con que el esquema se compile a gramática y con que se ignore en
silencio. Ésta sí: el esquema prohíbe todo lo que el modelo produciría de forma
natural, así que sólo hay una salida legal y no guarda ninguna relación con la
pregunta.

Se ejecuta a través del cliente real de HemoVet —no con curl— porque la pregunta
no es si Ollama sabe aplicar gramáticas, sino si la petición de HemoVet le llega
en una forma que honre.
"""

from __future__ import annotations

import asyncio
import json
import sys

sys.path.insert(0, "/home/matel/Documents/project/vscode/hemogramas-proyectoICC/backend")

import httpx

from app.modules.llm_chat.domain.entities import ModelRequest
from app.modules.llm_chat.infrastructure.llm.openai_compatible_client import (
    OllamaNativeLLMClient,
)

BASE_URL = "http://127.0.0.1:11434"

# Prohibe todo lo que el modelo diria por su cuenta. La unica cadena legal es
# {"zzz":"QQQ"}, y QQQ no tiene ninguna relacion con la capital de Francia.
ESQUEMA_ADVERSARIO = {
    "type": "object",
    "properties": {"zzz": {"type": "string", "enum": ["QQQ"]}},
    "required": ["zzz"],
    "additionalProperties": False,
}

# Exactamente los de produccion (llm_chat.generation_config, perfil main).
PRODUCCION = dict(
    thinking=False,
    model="qwen3.6:27b-q4_K_M",
    profile_name="faq_simple",
    profile_kind="main",
    num_predict=1280,
    num_ctx=65536,
    max_input_tokens=12000,
    context_reserve_tokens=512,
    temperature=0.3,
    top_p=0.8,
    top_k=20,
    repeat_penalty=1.0,
    timeout_seconds=120.0,
    keep_alive=-1,
)


def _peticion(*, con_esquema: bool) -> ModelRequest:
    return ModelRequest(
        system_prompt="Eres un asistente conciso.",
        user_prompt="¿Cuál es la capital de Francia?",
        response_schema=ESQUEMA_ADVERSARIO if con_esquema else None,
        **PRODUCCION,
    )


async def main() -> None:
    async with httpx.AsyncClient(timeout=180.0) as http:
        cliente = OllamaNativeLLMClient(
            http_client=http,
            base_url=BASE_URL,
            model_name=PRODUCCION["model"],
            timeout_seconds=180.0,
            warmup_profile=None,
        )

        for etiqueta, con_esquema in (("SIN format", False), ("CON format", True)):
            peticion = _peticion(con_esquema=con_esquema)

            # El payload lo construye el propio codigo de HemoVet, asi que lo
            # que sale por el cable es byte a byte lo que sale en produccion.
            payload = cliente._payload(peticion, stream=False)
            print(f"\n=== {etiqueta} · payload de HemoVet ===")
            print(json.dumps({k: v for k, v in payload.items() if k != "messages"},
                             ensure_ascii=False, sort_keys=True)[:400])
            print("clave de esquema presente:", "format" in payload)

            # Peticion cruda con ese mismo payload, para poder mirar el cuerpo
            # entero: `message.thinking` no lo expone el cliente.
            crudo = await http.post(f"{BASE_URL}/api/chat", json=payload)
            cuerpo = crudo.json()
            mensaje = cuerpo.get("message", {})
            print("--- cuerpo crudo ---")
            print("content        :", repr(mensaje.get("content")))
            print("campo thinking :", repr(mensaje.get("thinking")))
            print("claves mensaje :", sorted(mensaje.keys()))
            print("done_reason    :", cuerpo.get("done_reason"))
            print("prompt_eval    :", cuerpo.get("prompt_eval_count"),
                  "· eval:", cuerpo.get("eval_count"))

            # Y la ruta real del cliente, de punta a punta.
            try:
                respuesta = await cliente.generate(peticion)
                print("--- via cliente.generate() ---")
                print("text           :", repr(respuesta.text))
                print("finish_reason  :", respuesta.finish_reason)
            except Exception as exc:  # noqa: BLE001 - queremos ver el fallo
                print("--- via cliente.generate() ---")
                print("EXCEPCION:", type(exc).__name__, exc)


asyncio.run(main())
