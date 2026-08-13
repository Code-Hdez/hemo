from __future__ import annotations

import time
from typing import Any, Self
from uuid import uuid4

import httpx

from .models import ChatExecution, EvalConfig
from .sse import IncrementalSseParser, SseParseError

_NON_TECHNICAL_STREAM_CODES = {
    "refuse_treatment",
    "refuse_medication",
    "refuse_dose",
    "refuse_diagnosis",
    "refuse_out_of_scope",
    "urgent_referral",
    "require_context",
    "insufficient_evidence",
}


class ChatEvalClient:
    def __init__(self, config: EvalConfig) -> None:
        self.config = config
        self.browser_session_id = config.browser_session_id or str(uuid4())
        self._client = httpx.Client(
            base_url=config.base_url,
            timeout=httpx.Timeout(config.timeout_seconds),
            headers={
                "Content-Type": "application/json",
                "X-HemoVet-Browser-Session-ID": self.browser_session_id,
            },
        )
        if config.auth.bearer_token:
            self._client.headers["Authorization"] = f"Bearer {config.auth.bearer_token}"

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def login_if_configured(self) -> bool:
        if self.config.auth.bearer_token:
            return False
        if not self.config.auth.login_email or not self.config.auth.login_password:
            return False
        return self.refresh_login()

    def refresh_login(self) -> bool:
        """Replace an expired JWT when reusable login credentials are configured."""
        if not self.config.auth.login_email or not self.config.auth.login_password:
            return False
        response = self._client.post(
            "/auth/login",
            data={
                "username": self.config.auth.login_email,
                "password": self.config.auth.login_password,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        token = response.json().get("access_token")
        if token:
            self._client.headers["Authorization"] = f"Bearer {token}"
            return True
        return False

    def health(self) -> dict[str, Any]:
        response = self._client.get("/chat/health")
        response.raise_for_status()
        return dict(response.json())

    def conversation_messages(
        self,
        conversation_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Read the server-persisted copy for the active synthetic session."""
        response = self._client.get(
            f"/chat/conversations/{conversation_id}/messages",
            params={"limit": limit, "offset": offset},
        )
        if response.status_code == 401 and self.refresh_login():
            response = self._client.get(
                f"/chat/conversations/{conversation_id}/messages",
                params={"limit": limit, "offset": offset},
            )
        response.raise_for_status()
        return dict(response.json())

    def stream_chat(self, payload: dict[str, Any]) -> ChatExecution:
        started = time.perf_counter()
        first_token_ms: int | None = None
        raw_events: list[dict[str, Any]] = []
        answer_parts: list[str] = []
        sources: list[dict[str, Any]] = []
        case_facts: list[dict[str, Any]] = []
        warnings: list[str] = []
        safety_action: str | None = None
        model: str | None = None
        usage: dict[str, Any] = {}
        route_trace: dict[str, Any] = {}
        finish_reason: str | None = None
        conversation_id: str | None = None
        message_id: str | None = None
        stream_error_event: dict[str, Any] | None = None
        done_received = False
        http_status: int | None = None
        parser = IncrementalSseParser()

        def handle_event(event_name: str, data: Any) -> None:
            nonlocal first_token_ms
            nonlocal answer_parts
            nonlocal sources
            nonlocal case_facts
            nonlocal warnings
            nonlocal safety_action
            nonlocal model
            nonlocal usage
            nonlocal route_trace
            nonlocal finish_reason
            nonlocal conversation_id
            nonlocal message_id
            nonlocal stream_error_event
            nonlocal done_received

            if event_name == "delta" and isinstance(data, dict):
                text = str(data.get("text") or "")
                if text and first_token_ms is None:
                    first_token_ms = round((time.perf_counter() - started) * 1000)
                answer_parts.append(text)
            elif event_name == "sources" and isinstance(data, dict):
                raw_sources = data.get("sources")
                if isinstance(raw_sources, list):
                    sources = [item for item in raw_sources if isinstance(item, dict)]
            elif event_name == "done" and isinstance(data, dict):
                done_received = True
                answer = data.get("answer")
                if isinstance(answer, str):
                    answer_parts = [answer]
                raw_sources = data.get("sources")
                if isinstance(raw_sources, list):
                    sources = [item for item in raw_sources if isinstance(item, dict)]
                raw_facts = data.get("case_facts")
                if isinstance(raw_facts, list):
                    case_facts = [item for item in raw_facts if isinstance(item, dict)]
                warnings = _string_list(data.get("warnings"))
                safety_action = _optional_str(data.get("safety_action"))
                model = _optional_str(data.get("model"))
                usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
                raw_trace = data.get("route_trace")
                route_trace = raw_trace if isinstance(raw_trace, dict) else {}
                finish_reason = _optional_str(data.get("finish_reason"))
                conversation_id = _optional_str(data.get("conversation_id"))
                message_id = _optional_str(data.get("message_id"))
            elif event_name == "error":
                stream_error_event = data if isinstance(data, dict) else {"data": data}
                if isinstance(data, dict):
                    code = str(data.get("code") or "")
                    message = str(data.get("message") or "").strip()
                    if code in _NON_TECHNICAL_STREAM_CODES and message and not answer_parts:
                        answer_parts = [message]

        try:
            with self._client.stream(
                "POST", self.config.chat_stream_path, json=payload
            ) as response:
                http_status = response.status_code
                if response.status_code >= 400:
                    error_body = response.read().decode("utf-8", errors="replace")
                    return _error_execution(
                        started=started,
                        http_status=http_status,
                        error_type="http_error",
                        error_message=error_body[:1000],
                        raw_events=raw_events,
                    )
                for chunk in response.iter_text():
                    for event in parser.feed(chunk):
                        raw_events.append({"event": event.event, "data": event.data})
                        handle_event(event.event, event.data)
                for event in parser.flush():
                    raw_events.append({"event": event.event, "data": event.data})
                    handle_event(event.event, event.data)
        except SseParseError as exc:
            return _error_execution(
                started=started,
                http_status=http_status,
                error_type="stream_parse_error",
                error_message=str(exc),
                raw_events=raw_events,
                first_token_ms=first_token_ms,
                answer="".join(answer_parts),
                sources=sources,
            )
        except httpx.TimeoutException as exc:
            return _error_execution(
                started=started,
                http_status=http_status,
                error_type="timeout",
                error_message=str(exc),
                raw_events=raw_events,
                first_token_ms=first_token_ms,
                answer="".join(answer_parts),
                sources=sources,
            )
        except httpx.HTTPError as exc:
            return _error_execution(
                started=started,
                http_status=http_status,
                error_type="http_client_error",
                error_message=str(exc),
                raw_events=raw_events,
                first_token_ms=first_token_ms,
                answer="".join(answer_parts),
                sources=sources,
            )

        error_type = None
        error_message = None
        if stream_error_event is not None:
            error_type = str(stream_error_event.get("code") or "stream_error")
            error_message = str(stream_error_event.get("message") or stream_error_event)
        elif not done_received:
            error_type = "stream_incomplete"
            error_message = "El stream termino sin evento done."

        return ChatExecution(
            http_status=http_status,
            answer="".join(answer_parts).strip(),
            sources=sources,
            case_facts=case_facts,
            warnings=warnings,
            safety_action=safety_action,
            model=model,
            usage=usage,
            route_trace=route_trace,
            finish_reason=finish_reason,
            conversation_id=conversation_id,
            message_id=message_id,
            raw_events=raw_events,
            stream_started=http_status is not None,
            stream_done_received=done_received,
            stream_error_event=stream_error_event,
            duration_ms=round((time.perf_counter() - started) * 1000),
            first_token_ms=first_token_ms,
            error_type=error_type,
            error_message=error_message,
        )


def _error_execution(
    *,
    started: float,
    http_status: int | None,
    error_type: str,
    error_message: str,
    raw_events: list[dict[str, Any]],
    first_token_ms: int | None = None,
    answer: str = "",
    sources: list[dict[str, Any]] | None = None,
) -> ChatExecution:
    return ChatExecution(
        http_status=http_status,
        answer=answer.strip(),
        sources=sources or [],
        case_facts=[],
        warnings=[],
        safety_action=None,
        model=None,
        usage={},
        route_trace={},
        finish_reason=None,
        conversation_id=None,
        message_id=None,
        raw_events=raw_events,
        stream_started=http_status is not None,
        stream_done_received=False,
        stream_error_event=None,
        duration_ms=round((time.perf_counter() - started) * 1000),
        first_token_ms=first_token_ms,
        error_type=error_type,
        error_message=error_message,
    )


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]
