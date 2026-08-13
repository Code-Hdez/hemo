from __future__ import annotations

import json
from typing import Any

from .models import SseEvent


class SseParseError(RuntimeError):
    """Raised when the backend emits malformed SSE data."""


class IncrementalSseParser:
    def __init__(self) -> None:
        self._buffer = ""

    def feed(self, text: str) -> list[SseEvent]:
        self._buffer += text.replace("\r\n", "\n").replace("\r", "\n")
        events: list[SseEvent] = []
        while "\n\n" in self._buffer:
            block, self._buffer = self._buffer.split("\n\n", 1)
            event = parse_sse_block(block)
            if event is not None:
                events.append(event)
        return events

    def flush(self) -> list[SseEvent]:
        if not self._buffer.strip():
            self._buffer = ""
            return []
        block = self._buffer
        self._buffer = ""
        event = parse_sse_block(block)
        return [event] if event is not None else []


def parse_sse_block(block: str) -> SseEvent | None:
    name = "message"
    data_lines: list[str] = []
    for raw_line in block.splitlines():
        line = raw_line.strip("\n")
        if not line or line.startswith(":"):
            continue
        if line.startswith("event:"):
            name = line[6:].strip() or "message"
        elif line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
    if not data_lines:
        return None
    payload_text = "\n".join(data_lines)
    try:
        payload: Any = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise SseParseError(f"SSE JSON invalido en evento {name}: {payload_text[:160]}") from exc
    return SseEvent(event=name, data=payload)

