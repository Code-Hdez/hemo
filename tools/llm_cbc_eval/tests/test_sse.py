from __future__ import annotations

import pytest

from tools.llm_cbc_eval.src.sse import IncrementalSseParser, SseParseError


def test_incremental_sse_parser_reads_split_events() -> None:
    parser = IncrementalSseParser()
    assert parser.feed('event: delta\ndata: {"text": "hola"}\n') == []
    events = parser.feed('\nevent: done\ndata: {"answer": "hola"}\n\n')
    assert [(event.event, event.data) for event in events] == [
        ("delta", {"text": "hola"}),
        ("done", {"answer": "hola"}),
    ]


def test_incremental_sse_parser_rejects_invalid_json() -> None:
    parser = IncrementalSseParser()
    with pytest.raises(SseParseError):
        parser.feed("event: done\ndata: {bad}\n\n")

