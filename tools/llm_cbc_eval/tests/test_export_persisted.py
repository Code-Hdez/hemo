from __future__ import annotations

from tools.llm_cbc_eval.src.export_persisted import conversation_ids


def test_conversation_ids_include_completed_and_failed_turns(tmp_path) -> None:
    path = tmp_path / "run.jsonl"
    path.write_text(
        "\n".join(
            [
                '{"conversation_id":"conversation-ok"}',
                '{"conversation_id":"conversation-ok"}',
                '{"conversation_id":null,"stream_error_event":'
                '{"conversation_id":"conversation-error"}}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    assert conversation_ids(path) == ["conversation-ok", "conversation-error"]
