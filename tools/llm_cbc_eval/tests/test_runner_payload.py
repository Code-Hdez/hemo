from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest

from tools.llm_cbc_eval.src.models import EvalConfig, Question
from tools.llm_cbc_eval.src.runner import (
    build_payload,
    load_completed_keys,
    load_questions,
    stream_with_auth_refresh,
    validate_context,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_build_payload_omits_analysis_id_for_general() -> None:
    config = EvalConfig.from_mapping({})
    payload = build_payload(config, "general", "¿Qué son los leucocitos?")
    assert payload["context_scope"] == "general"
    assert "analysis_id" not in payload


def test_eval_config_reads_valid_browser_session_id(monkeypatch: pytest.MonkeyPatch) -> None:
    browser_session_id = "01234567-89ab-4def-8123-456789abcdef"
    monkeypatch.setenv("HEMOVET_EVAL_BROWSER_SESSION_ID", browser_session_id)
    config = EvalConfig.from_mapping(
        {"context": {"browser_session_id_env": "HEMOVET_EVAL_BROWSER_SESSION_ID"}}
    )
    assert config.browser_session_id == browser_session_id
    assert UUID(config.browser_session_id).version == 4


def test_eval_config_rejects_non_v4_browser_session_id() -> None:
    with pytest.raises(ValueError, match="UUIDv4"):
        EvalConfig.from_mapping({"context": {"browser_session_id": "not-a-uuid"}})


def test_build_payload_adds_selected_analysis_id() -> None:
    config = EvalConfig.from_mapping({"context": {"selected_analysis_id": "a1"}})
    payload = build_payload(config, "selected_hemogram", "resumen")
    assert payload["analysis_id"] == "a1"


def test_validate_context_requires_historical_pet_id() -> None:
    config = EvalConfig.from_mapping({"context": {"selected_analysis_id": "a1"}})
    with pytest.raises(ValueError):
        validate_context(config, ["hemograma_historico"])


def test_build_payload_adds_history_pet_and_reuses_conversation() -> None:
    config = EvalConfig.from_mapping({"context": {"historical_pet_id": "p1"}})
    payload = build_payload(
        config,
        "hemogram_history",
        "¿Cómo cambiaron?",
        conversation_id="c1",
    )
    assert payload["pet_id"] == "p1"
    assert payload["conversation_id"] == "c1"
    assert "analysis_id" not in payload


def test_question_from_mapping_defaults() -> None:
    question = Question.from_mapping({"id": 31, "pregunta": "texto"})
    assert question.id == "31"
    assert question.categoria == "sin_categoria"
    assert question.conversation_group is None


def test_question_reads_conversation_group() -> None:
    question = Question.from_mapping(
        {"id": "m1", "pregunta": "¿Y eso?", "conversation_group": "memory-wbc"}
    )
    assert question.conversation_group == "memory-wbc"


def test_resume_skips_completed_results_but_retries_errors(tmp_path: Path) -> None:
    jsonl = tmp_path / "partial.jsonl"
    jsonl.write_text(
        "\n".join(
            [
                '{"question_id":"1","modo":"informacion_general","status":"PASS"}',
                '{"question_id":"2","modo":"informacion_general","status":"FAIL"}',
                '{"question_id":"3","modo":"informacion_general","status":"ERROR"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    assert load_completed_keys(jsonl) == {
        ("1", "informacion_general"),
        ("2", "informacion_general"),
    }


def test_stream_refreshes_expired_login_once() -> None:
    class _Execution:
        def __init__(self, status: int) -> None:
            self.http_status = status

    class _Client:
        def __init__(self) -> None:
            self.stream_calls = 0
            self.refresh_calls = 0

        def stream_chat(self, payload: dict[str, object]) -> _Execution:
            del payload
            self.stream_calls += 1
            return _Execution(401 if self.stream_calls == 1 else 200)

        def refresh_login(self) -> bool:
            self.refresh_calls += 1
            return True

    client = _Client()
    execution = stream_with_auth_refresh(client, {"message": "hola"})  # type: ignore[arg-type]

    assert execution.http_status == 200
    assert client.stream_calls == 2
    assert client.refresh_calls == 1


def test_versioned_acceptance_cases_are_unique_and_executable() -> None:
    questions = load_questions(
        PROJECT_ROOT / "tools" / "llm_cbc_eval" / "data" / "acceptance_cases.yaml"
    )
    question_ids = [question.id for question in questions]
    supported_modes = {
        "informacion_general",
        "hemograma_seleccionado",
        "hemograma_historico",
    }

    assert len(question_ids) == len(set(question_ids))
    assert all(question.modos_aplicables for question in questions)
    assert {
        mode for question in questions for mode in question.modos_aplicables
    } <= supported_modes
    assert {
        "owner-free-text-prepare-consultation",
        "owner-free-text-what-changed-percentage",
        "owner-free-text-no-classifier-pattern",
        "owner-free-text-urgent-without-vet",
        "owner-free-text-missing-context",
    } <= set(question_ids)
