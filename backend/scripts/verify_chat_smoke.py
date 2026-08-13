#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


class ChatSmokeError(RuntimeError):
    """The authenticated production stream did not satisfy its contract."""


@dataclass(frozen=True, slots=True)
class ChatSmokeResult:
    completed: bool
    source_count: int


def _events(text: str) -> list[tuple[str, object]]:
    parsed: list[tuple[str, object]] = []
    normalized = text.replace("\r\n", "\n")
    for block in normalized.split("\n\n"):
        name = "message"
        data_lines: list[str] = []
        for line in block.splitlines():
            if line.startswith("event:"):
                name = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].lstrip())
        if not data_lines:
            continue
        try:
            payload = json.loads("\n".join(data_lines))
        except json.JSONDecodeError as exc:
            raise ChatSmokeError("El stream contiene datos SSE inválidos.") from exc
        parsed.append((name, payload))
    return parsed


def verify_sse(text: str) -> ChatSmokeResult:
    events = _events(text)
    if any(name == "error" for name, _ in events):
        raise ChatSmokeError("El stream emitió un evento de error.")
    done_payload = next(
        (payload for name, payload in reversed(events) if name == "done"), None
    )
    if not isinstance(done_payload, dict):
        raise ChatSmokeError("El stream no emitió el evento done.")
    source_payloads = [
        payload for name, payload in events if name == "sources" and isinstance(payload, dict)
    ]
    sources = done_payload.get("sources")
    if not isinstance(sources, list) or not sources:
        sources = next(
            (
                payload.get("sources")
                for payload in reversed(source_payloads)
                if isinstance(payload.get("sources"), list)
            ),
            [],
        )
    if not sources:
        raise ChatSmokeError("El stream terminó sin fuentes RAG.")
    answer = str(done_payload.get("answer") or "").lower()
    if "con la información disponible no puedo confirmarlo" in answer:
        raise ChatSmokeError("El stream devolvió el fallback de evidencia insuficiente.")
    return ChatSmokeResult(completed=True, source_count=len(sources))


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida un stream SSE de chat.")
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    try:
        result = verify_sse(args.path.read_text(encoding="utf-8"))
    except (OSError, ChatSmokeError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    print(f"Smoke SSE válido ({result.source_count} fuentes).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
