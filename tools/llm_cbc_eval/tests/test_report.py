from __future__ import annotations

from tools.llm_cbc_eval.src.models import ChatExecution, CheckResult, EvalConfig, EvalResult, Question
from tools.llm_cbc_eval.src.report import render_markdown


def test_render_markdown_includes_readable_source_and_latency_percentiles() -> None:
    result = EvalResult(
        run_id="run",
        timestamp="now",
        git_commit="abc",
        question=Question(id="31", categoria="valores", pregunta="¿Qué son los leucocitos?"),
        requested_mode="informacion_general",
        backend_mode="general",
        payload={},
        execution=ChatExecution(
            http_status=200,
            answer="Respuesta limpia.",
            sources=[
                {
                    "citation_id": "S1",
                    "display_title": "Schalm's Veterinary Hematology",
                    "edition": "6th edition",
                    "section": "Leukocytosis",
                    "page_start": 123,
                    "page_end": 125,
                }
            ],
            case_facts=[],
            warnings=[],
            safety_action="allow",
            model="test",
            usage={},
            route_trace={},
            finish_reason="stop",
            conversation_id="c",
            message_id="m",
            raw_events=[{"event": "done", "data": {"answer": "Respuesta limpia."}}],
            stream_started=True,
            stream_done_received=True,
            stream_error_event=None,
            duration_ms=20,
            first_token_ms=5,
        ),
        checks=[
            CheckResult(
                name="inline_citations",
                passed=True,
                severity="fail",
                message="No hay citas inline visibles.",
            )
        ],
        status="PASS",
    )
    markdown = render_markdown([result], EvalConfig.from_mapping({}))
    assert "Schalm's Veterinary Hematology — 6th edition — Leukocytosis — pp. 123–125" in markdown
    assert "Latencia total p95" in markdown
    assert "Respuesta limpia." in markdown
    assert result.to_json()["raw_events"] == [
        {"event": "done", "data": {"answer": "Respuesta limpia."}}
    ]
