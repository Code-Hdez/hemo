from __future__ import annotations

import asyncio
from dataclasses import asdict
import json
from pathlib import Path

import pytest

from scripts.benchmark_chat_sse import (
    BenchmarkCase,
    SseDecoder,
    StreamSample,
    benchmark_stream,
    distribution,
    load_cases,
    percentile,
    summarize_samples,
)
from scripts.inspect_llm_runtime import (
    RuntimeInspectionError,
    _docker_stats,
    classify_gpu_residency,
    collect_runtime,
    summarize_ollama,
)


@pytest.mark.parametrize(
    ("size", "size_vram", "expected"),
    [
        (1_000, 1_000, "full_gpu"),
        (1_000, 980, "full_gpu"),
        (1_000, 500, "mixed_cpu_gpu"),
        (1_000, 0, "cpu"),
        (0, 0, "unknown"),
    ],
)
def test_gpu_residency_requires_nearly_all_model_bytes_in_vram(
    size: int,
    size_vram: int,
    expected: str,
) -> None:
    result = classify_gpu_residency(size, size_vram)

    assert result["inference_device"] == expected


def test_ollama_summary_keeps_runtime_metadata_but_not_prompts() -> None:
    result = summarize_ollama(
        version={"version": "0.30.10"},
        tags={
            "models": [
                {
                    "name": "qwen3:test",
                    "digest": "digest-123",
                    "size": 2_000,
                    "details": {
                        "format": "gguf",
                        "parameter_size": "4B",
                        "quantization_level": "Q4_K_M",
                    },
                }
            ]
        },
        processes={
            "models": [
                {
                    "name": "qwen3:test",
                    "digest": "digest-123",
                    "size": 2_000,
                    "size_vram": 2_000,
                    "context_length": 4_096,
                }
            ]
        },
        show={
            "system": "prompt clínico que no debe salir",
            "template": "plantilla que no debe salir",
            "details": {"quantization_level": "Q4_K_M"},
            "model_info": {
                "general.architecture": "qwen3",
                "qwen3.context_length": 32_768,
                "tokenizer.ggml.tokens": ["contenido", "no", "permitido"],
            },
        },
        requested_model="qwen3:test",
    )

    serialized = json.dumps(result)
    assert result["ollama_version"] == "0.30.10"
    assert result["loaded_models"][0]["inference_device"] == "full_gpu"
    assert result["selected_model"]["digest"] == "digest-123"
    assert "Q4_K_M" in serialized
    assert "prompt clínico" not in serialized
    assert "plantilla" not in serialized
    assert "tokenizer.ggml.tokens" not in serialized


def test_invalid_container_name_never_reaches_docker() -> None:
    errors: list[RuntimeInspectionError] = []

    result = _docker_stats("ollama;rm", 1, errors)

    assert result == {}
    assert errors == [RuntimeInspectionError("docker_stats", "invalid_container_name")]


def test_runtime_inspection_can_split_internal_ollama_and_host_gpu() -> None:
    result = collect_runtime(
        ollama_url="http://ollama:11434",
        model=None,
        ollama_container=None,
        timeout_seconds=1,
        inspect_ollama=False,
        inspect_gpu=False,
    )

    assert result["ollama"] == {"skipped": True}
    assert result["gpu"] == []
    assert result["errors"] == []


def test_jsonl_cases_are_validated_without_copying_messages_to_results(
    tmp_path: Path,
) -> None:
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "name": "greeting",
                        "message": "Hola, contenido que no debe quedar en métricas",
                        "context_scope": "general",
                    }
                ),
                json.dumps(
                    {
                        "name": "selected_wbc",
                        "message": "¿Cómo está WBC?",
                        "context_scope": "selected_hemogram",
                        "analysis_id": "analysis-1",
                        "pet_id": "pet-1",
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    cases = load_cases(dataset)
    sample = StreamSample(
        case_name=cases[0].name,
        concurrency=1,
        status="completed",
        first_event_ms=1,
        first_approved_content_ms=2,
        total_ms=3,
        terminal_event="done",
    )

    assert len(cases) == 2
    assert cases[1].analysis_id == "analysis-1"
    assert "contenido que no debe" not in json.dumps(asdict(sample))
    assert "analysis-1" not in json.dumps(asdict(sample))


def test_sse_decoder_accepts_multiline_json_and_requires_object_payload() -> None:
    decoder = SseDecoder()

    assert decoder.feed("event: delta") is None
    assert decoder.feed('data: {"text":') is None
    assert decoder.feed('data: "aprobado"}') is None
    event = decoder.feed("")

    assert event == ("delta", {"text": "aprobado"})


def test_percentiles_and_summary_report_tail_latency_and_failures() -> None:
    samples = [
        StreamSample("one", 2, "completed", 1, 10, 20, "done"),
        StreamSample("two", 2, "completed", 2, 20, 40, "done"),
        StreamSample("three", 2, "error", 3, None, 60, "error", "timeout"),
        StreamSample("four", 2, "cancelled", None, None, 5, "client_cancelled"),
    ]

    summary = summarize_samples(samples)

    assert percentile([10, 20, 30, 40], 75) == 32.5
    assert distribution([10, 20, 30, 40])["p99"] == 39.7
    assert summary["completed"] == 2
    assert summary["errors"] == 1
    assert summary["cancelled"] == 1
    assert summary["error_rate"] == 0.25
    assert summary["first_approved_content_ms"]["p95"] == 19.5
    assert summary["total_ms"]["p99"] == 59.4
    assert summary["error_codes"] == {"timeout": 1}


class _FakeResponse:
    status_code = 200

    def __init__(self, lines: list[str]) -> None:
        self.lines = lines

    async def aiter_lines(self):
        for line in self.lines:
            yield line


class _FakeStreamContext:
    def __init__(self, response: _FakeResponse) -> None:
        self.response = response

    async def __aenter__(self) -> _FakeResponse:
        return self.response

    async def __aexit__(self, *args: object) -> None:
        return None


class _FakeClient:
    def __init__(self, lines: list[str]) -> None:
        self.response = _FakeResponse(lines)
        self.headers: dict[str, str] | None = None
        self.payload: dict[str, object] | None = None

    def stream(
        self,
        method: str,
        endpoint: str,
        *,
        json: dict[str, object],
        headers: dict[str, str],
    ) -> _FakeStreamContext:
        assert method == "POST"
        assert endpoint.endswith("/chat/stream")
        self.headers = headers
        self.payload = json
        return _FakeStreamContext(self.response)


def test_stream_benchmark_measures_only_the_validated_delta() -> None:
    # The SSE contract no longer streams raw "delta" text: content is
    # buffered and validated server-side, then delivered atomically in one
    # "final" event carrying the complete "answer" (etapa 8's honest SSE
    # contract / stream_mode="buffered_validated"; see the removal of the
    # old delta/validating gate in commit 87776a9a).
    client = _FakeClient(
        [
            "event: status",
            'data: {"stage":"generating"}',
            "",
            "event: status",
            'data: {"stage":"validating"}',
            "",
            "event: final",
            'data: {"answer":"contenido ya aprobado"}',
            "",
            "event: done",
            'data: {"state":"completed"}',
            "",
        ]
    )

    sample = asyncio.run(
        benchmark_stream(
            client,  # type: ignore[arg-type]
            endpoint="http://localhost/api/v1/chat/stream",
            case=BenchmarkCase("greeting", "Hola", "general"),
            concurrency=1,
            browser_session_id="browser-session",
            token="secret-token",
        )
    )

    assert sample.status == "completed"
    assert sample.first_event_ms is not None
    assert sample.first_approved_content_ms is not None
    assert sample.first_approved_content_ms >= sample.first_event_ms
    assert sample.terminal_event == "done"
    assert sample.event_count == 4
    assert client.headers is not None
    assert client.headers["Authorization"] == "Bearer secret-token"
    assert "contenido ya aprobado" not in json.dumps(asdict(sample))


def test_stream_benchmark_fails_an_unvalidated_delta() -> None:
    client = _FakeClient(
        [
            "event: status",
            'data: {"stage":"generating"}',
            "",
            "event: delta",
            'data: {"text":"contenido prematuro"}',
            "",
            "event: done",
            'data: {"state":"completed"}',
            "",
        ]
    )

    sample = asyncio.run(
        benchmark_stream(
            client,  # type: ignore[arg-type]
            endpoint="http://localhost/api/v1/chat/stream",
            case=BenchmarkCase("unsafe", "Hola", "general"),
            concurrency=1,
            browser_session_id="browser-session",
            token=None,
        )
    )

    # No "final" event ever arrives, so benchmark_stream can never observe a
    # validated answer even though the stream reaches "done" — the current
    # contract flags that as "missing_approved_content" (the old client-side
    # "unvalidated_delta" detection was removed along with the "delta" event
    # itself; see commit 87776a9a).
    assert sample.status == "error"
    assert sample.error_code == "missing_approved_content"
    assert sample.first_approved_content_ms is None
