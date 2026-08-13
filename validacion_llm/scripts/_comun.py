"""Plumbing compartido para ejecutar las baterías de validación del asistente LLM/RAG.

Invoca el pipeline real de producción (`build_chat_container` →
`SendChatMessageUseCase.execute`), el mismo código que sirve `POST /api/v1/chat`,
sin la capa HTTP/auth. Registra por caso la acción de seguridad, el perfil de chat
(leído desde el metadata persistido vía `conversations.recent`), el modelo, la
latencia y las fuentes recuperadas.

Requiere el stack activo: Postgres, Chroma y Ollama accesibles según `.env`.
"""

from __future__ import annotations

import csv
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

CASOS_DIR = PROJECT_ROOT / "validacion_llm" / "casos"
RESULTADOS_DIR = PROJECT_ROOT / "validacion_llm" / "resultados"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

# El conjunto de acciones que representan un rechazo deliberado del guardrail.
ACCIONES_RECHAZO = {
    "refuse_medication",
    "refuse_dose",
    "refuse_treatment",
    "refuse_diagnosis",
    "urgent_referral",
    "require_context",
}


@dataclass(slots=True)
class ResultadoCaso:
    """Resultado normalizado de una llamada al pipeline real."""

    respuesta: str = ""
    accion_seguridad: str = ""
    intencion_seguridad: str = ""
    perfil_chat: str = ""
    usa_rag: bool | None = None
    usa_llm: bool | None = None
    modelo: str | None = None
    num_fuentes: int = 0
    ids_fuentes: list[str] = field(default_factory=list)
    duracion_ms: int = 0
    finish_reason: str = ""
    error: str = ""


def leer_csv(nombre: str) -> list[dict[str, str]]:
    ruta = CASOS_DIR / nombre
    with ruta.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def escribir_csv(nombre: str, filas: list[dict[str, Any]], columnas: list[str]) -> Path:
    RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)
    ruta = RESULTADOS_DIR / nombre
    with ruta.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columnas)
        writer.writeheader()
        for fila in filas:
            writer.writerow(fila)
    return ruta


async def construir_contenedor() -> Any:
    import app.db.base  # noqa: F401  registra todos los modelos ORM (FK cross-módulo: chat_sessions -> pets)
    from app.core.config import settings
    from app.modules.llm_chat.composition import build_chat_container

    return await build_chat_container(settings)


def modelo_actual() -> str:
    from app.core.config import settings

    return settings.OLLAMA_MODEL or "desconocido"


async def ejecutar_caso(
    contenedor: Any,
    *,
    user_id: str,
    mensaje: str,
    context_scope: str = "general",
    analysis_id: str | None = None,
    conversation_id: str | None = None,
) -> tuple[ResultadoCaso, str]:
    """Ejecuta un turno contra el pipeline real y devuelve (resultado, conversation_id)."""

    from app.modules.llm_chat.application.dto import ChatCommand
    from app.modules.llm_chat.domain.exceptions import ChatRuntimeUnavailable

    command = ChatCommand(
        user_id=user_id,
        client_message_id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        message=mensaje,
        context_scope=context_scope,
        analysis_id=analysis_id,
        thinking=False,
    )
    try:
        result = await contenedor.send_chat.execute(command)
    except ChatRuntimeUnavailable as exc:
        return (
            ResultadoCaso(
                accion_seguridad="runtime_unavailable",
                modelo=modelo_actual(),
                error=str(exc) or "ChatRuntimeUnavailable",
            ),
            conversation_id or "",
        )

    resultado = ResultadoCaso(
        respuesta=result.answer,
        accion_seguridad=result.safety_action.value,
        modelo=result.model or modelo_actual(),
        num_fuentes=len(result.sources),
        ids_fuentes=[getattr(s, "source_id", "") or getattr(s, "id", "") for s in result.sources],
        duracion_ms=result.duration_ms,
        finish_reason=result.finish_reason,
    )

    # perfil_chat e intencion_seguridad solo viven en el metadata persistido.
    records = await contenedor.conversations.recent(result.conversation_id, 2)
    for record in reversed(records):
        if record.role == "assistant":
            meta = record.metadata or {}
            resultado.perfil_chat = str(meta.get("chat_profile", ""))
            resultado.intencion_seguridad = str(meta.get("safety_intent", ""))
            break

    return resultado, result.conversation_id
