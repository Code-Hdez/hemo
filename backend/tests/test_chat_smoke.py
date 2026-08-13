from __future__ import annotations

import json

import pytest

from scripts.verify_chat_smoke import ChatSmokeError, verify_sse


def event(name: str, payload: object) -> str:
    return f"event: {name}\ndata: {json.dumps(payload)}\n\n"


def test_smoke_accepts_completed_stream_with_sources() -> None:
    body = event("status", {"stage": "retrieving"}) + event(
        "sources", {"sources": [{"id": "chunk-1"}]}
    ) + event(
        "done",
        {
            "answer": "Las plaquetas participan en la hemostasia [S1].",
            "sources": [{"id": "chunk-1"}],
        },
    )

    result = verify_sse(body)

    assert result.source_count == 1
    assert result.completed is True


def test_smoke_rejects_evidence_fallback() -> None:
    body = event("sources", {"sources": []}) + event(
        "done",
        {
            "answer": "Con la información disponible no puedo confirmarlo.",
            "sources": [],
        },
    )

    with pytest.raises(ChatSmokeError, match="fuentes"):
        verify_sse(body)
