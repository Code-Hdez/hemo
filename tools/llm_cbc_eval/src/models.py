from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import UUID

BackendMode = Literal[
    "general",
    "selected_hemogram",
    "hemogram_history",
    "uploaded_analysis",
    "historical_analysis",
]
EvalStatus = Literal["PASS", "WARNING", "FAIL", "ERROR"]
Severity = Literal["info", "warning", "fail", "error"]


@dataclass(frozen=True, slots=True)
class Question:
    id: str
    categoria: str
    pregunta: str
    tipo_de_riesgo: str = ""
    esperado: str = ""
    modos_aplicables: list[str] = field(default_factory=list)
    notas: str = ""
    conversation_group: str | None = None

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> Question:
        return cls(
            id=str(value.get("id") or "").strip(),
            categoria=str(value.get("categoria") or "sin_categoria").strip(),
            pregunta=str(value.get("pregunta") or "").strip(),
            tipo_de_riesgo=str(value.get("tipo_de_riesgo") or "").strip(),
            esperado=str(value.get("esperado") or "").strip(),
            modos_aplicables=[
                str(item).strip()
                for item in value.get("modos_aplicables", [])
                if str(item).strip()
            ],
            notas=str(value.get("notas") or "").strip(),
            conversation_group=_optional_str(value.get("conversation_group")),
        )


@dataclass(frozen=True, slots=True)
class AuthConfig:
    bearer_token: str | None = None
    login_email: str | None = None
    login_password: str | None = None


@dataclass(frozen=True, slots=True)
class EvalConfig:
    base_url: str
    chat_stream_path: str
    auth: AuthConfig
    mode_map: dict[str, BackendMode]
    selected_analysis_id: str | None
    historical_pet_id: str | None
    historical_analysis_id: str | None
    browser_session_id: str | None
    timeout_seconds: float
    retries: int
    retry_backoff_seconds: float
    output_dir: str
    latency_warning_ms: int
    validations: dict[str, bool]
    reuse_conversation: bool = False

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> EvalConfig:
        auth_value = value.get("auth") or {}
        context_value = value.get("context") or {}
        mode_map = value.get("mode_map") or value.get("modes") or {}
        if not mode_map:
            mode_map = {
                "informacion_general": "general",
                "hemograma_seleccionado": "selected_hemogram",
                "hemograma_historico": "hemogram_history",
            }
        return cls(
            base_url=str(value.get("base_url") or "http://localhost:3000/api/v1").rstrip("/"),
            chat_stream_path=str(value.get("chat_stream_path") or "/chat/stream"),
            auth=AuthConfig(
                bearer_token=_configured_value(auth_value, "bearer_token"),
                login_email=_configured_value(auth_value, "login_email"),
                login_password=_configured_value(auth_value, "login_password"),
            ),
            mode_map={str(key): _backend_mode(raw) for key, raw in mode_map.items()},
            selected_analysis_id=_optional_str(
                _configured_value(context_value, "selected_analysis_id")
                or value.get("selected_analysis_id")
            ),
            historical_pet_id=_optional_str(
                _configured_value(context_value, "historical_pet_id")
                or value.get("historical_pet_id")
            ),
            historical_analysis_id=_optional_str(
                _configured_value(context_value, "historical_analysis_id")
                or value.get("historical_analysis_id")
            ),
            browser_session_id=_browser_session_id(
                _configured_value(context_value, "browser_session_id")
                or value.get("browser_session_id")
            ),
            timeout_seconds=float(value.get("timeout_seconds") or 180),
            retries=int(value.get("retries") or 0),
            retry_backoff_seconds=float(value.get("retry_backoff_seconds") or 2),
            output_dir=str(value.get("output_dir") or "tools/llm_cbc_eval/results"),
            latency_warning_ms=int(value.get("latency_warning_ms") or 120000),
            validations=dict(value.get("validations") or {}),
            reuse_conversation=bool(value.get("reuse_conversation", False)),
        )


@dataclass(frozen=True, slots=True)
class SseEvent:
    event: str
    data: Any


@dataclass(frozen=True, slots=True)
class ChatExecution:
    http_status: int | None
    answer: str
    sources: list[dict[str, Any]]
    case_facts: list[dict[str, Any]]
    warnings: list[str]
    safety_action: str | None
    model: str | None
    usage: dict[str, Any]
    route_trace: dict[str, Any]
    finish_reason: str | None
    conversation_id: str | None
    message_id: str | None
    raw_events: list[dict[str, Any]]
    stream_started: bool
    stream_done_received: bool
    stream_error_event: dict[str, Any] | None
    duration_ms: int
    first_token_ms: int | None
    error_type: str | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class CheckResult:
    name: str
    passed: bool
    severity: Severity
    message: str
    evidence: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class EvalResult:
    run_id: str
    timestamp: str
    git_commit: str | None
    question: Question
    requested_mode: str
    backend_mode: BackendMode
    payload: dict[str, Any]
    execution: ChatExecution
    checks: list[CheckResult]
    status: EvalStatus

    def to_json(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "git_commit": self.git_commit,
            "question_id": self.question.id,
            "categoria": self.question.categoria,
            "tipo_de_riesgo": self.question.tipo_de_riesgo,
            "modo": self.requested_mode,
            "backend_mode": self.backend_mode,
            "pregunta": self.question.pregunta,
            "esperado": self.question.esperado,
            "conversation_group": self.question.conversation_group,
            "payload": self.payload,
            "http_status": self.execution.http_status,
            "answer": self.execution.answer,
            "sources": self.execution.sources,
            "case_facts": self.execution.case_facts,
            "warnings": self.execution.warnings,
            "safety_action": self.execution.safety_action,
            "model": self.execution.model,
            "usage": self.execution.usage,
            "route_trace": self.execution.route_trace,
            "finish_reason": self.execution.finish_reason,
            "conversation_id": self.execution.conversation_id,
            "message_id": self.execution.message_id,
            "stream_started": self.execution.stream_started,
            "stream_done_received": self.execution.stream_done_received,
            "stream_error_event": self.execution.stream_error_event,
            # Preserve the complete SSE transcript for reproducibility. General
            # battery accounts contain no production clinical records; keeping
            # every event makes interrupted streams and partial answers auditable.
            "raw_events": self.execution.raw_events,
            "duration_ms": self.execution.duration_ms,
            "first_token_ms": self.execution.first_token_ms,
            "error_type": self.execution.error_type,
            "error_message": self.execution.error_message,
            "checks": [
                {
                    "name": check.name,
                    "passed": check.passed,
                    "severity": check.severity,
                    "message": check.message,
                    "evidence": check.evidence,
                }
                for check in self.checks
            ],
            "status": self.status,
        }


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _browser_session_id(value: object) -> str | None:
    text = _optional_str(value)
    if text is None:
        return None
    try:
        parsed = UUID(text)
    except ValueError as exc:
        raise ValueError("browser_session_id debe ser un UUIDv4.") from exc
    if parsed.version != 4:
        raise ValueError("browser_session_id debe ser un UUIDv4.")
    return str(parsed)


def _configured_value(mapping: dict[str, Any], key: str) -> str | None:
    """Read a non-secret literal or resolve `<key>_env` without persisting it."""
    direct = _optional_str(mapping.get(key))
    if direct:
        return direct
    env_name = _optional_str(mapping.get(f"{key}_env"))
    return _optional_str(os.getenv(env_name)) if env_name else None


def _backend_mode(value: object) -> BackendMode:
    text = str(value).strip()
    if text not in {
        "general",
        "selected_hemogram",
        "hemogram_history",
        "uploaded_analysis",
        "historical_analysis",
    }:
        raise ValueError(f"Modo de chat no soportado: {text}")
    return text  # type: ignore[return-value]
