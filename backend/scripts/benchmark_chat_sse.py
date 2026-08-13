#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
import math
import os
from pathlib import Path
import random
import re
import sys
import time
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

import httpx

_SCOPES = frozenset({"general", "selected_hemogram", "hemogram_history"})
_CODE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    name: str
    message: str
    context_scope: str
    analysis_id: str | None = None
    pet_id: str | None = None

    def request_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "client_message_id": str(uuid4()),
            "message": self.message,
            "context_scope": self.context_scope,
        }
        if self.analysis_id:
            payload["analysis_id"] = self.analysis_id
        if self.pet_id:
            payload["pet_id"] = self.pet_id
        return payload


@dataclass(frozen=True, slots=True)
class StreamSample:
    case_name: str
    concurrency: int
    status: str
    first_event_ms: float | None
    first_approved_content_ms: float | None
    total_ms: float
    terminal_event: str | None
    error_code: str | None = None
    event_count: int = 0


class SseDecoder:
    def __init__(self) -> None:
        self.event = "message"
        self.data: list[str] = []

    def feed(self, raw_line: str) -> tuple[str, dict[str, Any]] | None:
        line = raw_line.rstrip("\r")
        if line == "":
            return self._dispatch()
        if line.startswith(":"):
            return None
        if line.startswith("event:"):
            self.event = line[6:].strip() or "message"
        elif line.startswith("data:"):
            self.data.append(line[5:].lstrip())
        return None

    def finish(self) -> tuple[str, dict[str, Any]] | None:
        return self._dispatch()

    def _dispatch(self) -> tuple[str, dict[str, Any]] | None:
        if not self.data:
            self.event = "message"
            return None
        payload = json.loads("\n".join(self.data))
        event = self.event
        self.event = "message"
        self.data = []
        if not isinstance(payload, dict):
            raise ValueError("sse_payload_not_an_object")
        return event, payload


def load_cases(path: Path) -> list[BenchmarkCase]:
    cases: list[BenchmarkCase] = []
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid_jsonl_line:{line_number}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"case_not_an_object:{line_number}")
        name = _safe_code(value.get("name")) or f"case_{line_number}"
        message = str(value.get("message") or "").strip()
        scope = str(value.get("context_scope") or "general").strip()
        analysis_id = _optional_text(value.get("analysis_id"))
        pet_id = _optional_text(value.get("pet_id"))
        if not message or len(message) > 8_000:
            raise ValueError(f"invalid_message:{line_number}")
        if scope not in _SCOPES:
            raise ValueError(f"invalid_context_scope:{line_number}")
        if scope == "general" and (analysis_id or pet_id):
            raise ValueError(f"general_case_has_clinical_id:{line_number}")
        if scope == "selected_hemogram" and not analysis_id:
            raise ValueError(f"selected_case_missing_analysis_id:{line_number}")
        if scope == "hemogram_history" and not pet_id:
            raise ValueError(f"history_case_missing_pet_id:{line_number}")
        cases.append(
            BenchmarkCase(
                name=name,
                message=message,
                context_scope=scope,
                analysis_id=analysis_id,
                pet_id=pet_id,
            )
        )
    if not cases:
        raise ValueError("benchmark_dataset_empty")
    return cases


def percentile(values: list[float], percentile_value: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * (percentile_value / 100)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return round(ordered[lower], 3)
    weight = position - lower
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * weight, 3)


def distribution(values: list[float]) -> dict[str, float | int | None]:
    return {
        "count": len(values),
        "p50": percentile(values, 50),
        "p75": percentile(values, 75),
        "p90": percentile(values, 90),
        "p95": percentile(values, 95),
        "p99": percentile(values, 99),
        "max": round(max(values), 3) if values else None,
    }


def summarize_samples(samples: list[StreamSample]) -> dict[str, object]:
    completed = [sample for sample in samples if sample.status == "completed"]
    errors = [sample for sample in samples if sample.status == "error"]
    cancelled = [sample for sample in samples if sample.status == "cancelled"]
    first_events = [
        sample.first_event_ms for sample in samples if sample.first_event_ms is not None
    ]
    approved = [
        sample.first_approved_content_ms
        for sample in samples
        if sample.first_approved_content_ms is not None
    ]
    error_codes = Counter(sample.error_code or "unknown" for sample in errors)
    total = len(samples)
    return {
        "requests": total,
        "completed": len(completed),
        "errors": len(errors),
        "cancelled": len(cancelled),
        "error_rate": round(len(errors) / total, 6) if total else 0.0,
        "cancellation_rate": round(len(cancelled) / total, 6) if total else 0.0,
        "missing_approved_content": sum(
            sample.status == "completed" and sample.first_approved_content_ms is None
            for sample in samples
        ),
        "error_codes": dict(sorted(error_codes.items())),
        "first_event_ms": distribution(first_events),
        "first_approved_content_ms": distribution(approved),
        "total_ms": distribution([sample.total_ms for sample in samples]),
    }


async def benchmark_stream(
    client: httpx.AsyncClient,
    *,
    endpoint: str,
    case: BenchmarkCase,
    concurrency: int,
    browser_session_id: str,
    token: str | None,
) -> StreamSample:
    started = time.perf_counter()
    first_event_ms: float | None = None
    first_approved_ms: float | None = None
    terminal_event: str | None = None
    terminal_count = 0
    event_count = 0
    error_code: str | None = None
    decoder = SseDecoder()
    headers = {
        "Accept": "text/event-stream",
        "Cache-Control": "no-cache",
        "X-HemoVet-Browser-Session-ID": browser_session_id,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        async with client.stream(
            "POST",
            endpoint,
            json=case.request_payload(),
            headers=headers,
        ) as response:
            if response.status_code != 200:
                elapsed = _elapsed_ms(started)
                return StreamSample(
                    case_name=case.name,
                    concurrency=concurrency,
                    status="error",
                    first_event_ms=None,
                    first_approved_content_ms=None,
                    total_ms=elapsed,
                    terminal_event=None,
                    error_code=f"http_{response.status_code}",
                )
            async for line in response.aiter_lines():
                dispatched = decoder.feed(line)
                if dispatched is None:
                    continue
                event_count += 1
                now_ms = _elapsed_ms(started)
                if first_event_ms is None:
                    first_event_ms = now_ms
                event, payload = dispatched
                if (
                    event == "final"
                    and first_approved_ms is None
                    and str(payload.get("answer") or "").strip()
                ):
                    first_approved_ms = now_ms
                if event in {"done", "error", "cancelled"}:
                    terminal_count += 1
                    terminal_event = terminal_event or event
                    if terminal_count > 1:
                        error_code = "duplicate_terminal_event"
                    if event == "error":
                        error_code = _safe_code(payload.get("code")) or "sse_error"
            trailing = decoder.finish()
            if terminal_event is None and trailing is not None:
                event_count += 1
                event, payload = trailing
                if first_event_ms is None:
                    first_event_ms = _elapsed_ms(started)
                if event in {"done", "error", "cancelled"}:
                    terminal_count += 1
                    terminal_event = terminal_event or event
                    if terminal_count > 1:
                        error_code = "duplicate_terminal_event"
                    if event == "error":
                        error_code = _safe_code(payload.get("code")) or "sse_error"
    except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
        return StreamSample(
            case_name=case.name,
            concurrency=concurrency,
            status="error",
            first_event_ms=first_event_ms,
            first_approved_content_ms=first_approved_ms,
            total_ms=_elapsed_ms(started),
            terminal_event=terminal_event,
            error_code=type(exc).__name__,
            event_count=event_count,
        )

    status = (
        "completed"
        if terminal_event == "done" and error_code is None
        else "cancelled" if terminal_event == "cancelled" else "error"
    )
    if status == "completed" and first_approved_ms is None:
        status = "error"
        error_code = "missing_approved_content"
    elif status == "error" and error_code is None:
        error_code = "missing_terminal_event"
    return StreamSample(
        case_name=case.name,
        concurrency=concurrency,
        status=status,
        first_event_ms=first_event_ms,
        first_approved_content_ms=first_approved_ms,
        total_ms=_elapsed_ms(started),
        terminal_event=terminal_event,
        error_code=error_code,
        event_count=event_count,
    )


async def _run_with_optional_cancellation(
    client: httpx.AsyncClient,
    *,
    endpoint: str,
    case: BenchmarkCase,
    concurrency: int,
    browser_session_id: str,
    token: str | None,
    cancel_after_ms: float | None,
) -> StreamSample:
    started = time.perf_counter()
    task = asyncio.create_task(
        benchmark_stream(
            client,
            endpoint=endpoint,
            case=case,
            concurrency=concurrency,
            browser_session_id=browser_session_id,
            token=token,
        )
    )
    if cancel_after_ms is None:
        return await task
    try:
        return await asyncio.wait_for(
            asyncio.shield(task),
            timeout=cancel_after_ms / 1000,
        )
    except TimeoutError:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return StreamSample(
            case_name=case.name,
            concurrency=concurrency,
            status="cancelled",
            first_event_ms=None,
            first_approved_content_ms=None,
            total_ms=_elapsed_ms(started),
            terminal_event="client_cancelled",
            error_code=None,
        )


async def run_benchmark(
    *,
    base_url: str,
    cases: list[BenchmarkCase],
    concurrency_levels: list[int],
    repetitions: int,
    timeout_seconds: float,
    token: str | None,
    warmup: int,
    cancel_fraction: float,
    cancel_after_ms: float,
    seed: int,
    metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    endpoint = _chat_endpoint(base_url)
    maximum_connections = max(concurrency_levels)
    timeout = httpx.Timeout(timeout_seconds)
    limits = httpx.Limits(
        max_connections=maximum_connections,
        max_keepalive_connections=maximum_connections,
    )
    randomizer = random.Random(seed)
    scenarios: list[dict[str, object]] = []
    warmup_samples: list[StreamSample] = []
    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        for _ in range(warmup):
            warmup_samples.append(
                await benchmark_stream(
                    client,
                    endpoint=endpoint,
                    case=cases[0],
                    concurrency=1,
                    browser_session_id=str(uuid4()),
                    token=token,
                )
            )
        for concurrency in concurrency_levels:
            scenario_started = time.perf_counter()
            jobs = [case for _ in range(repetitions) for case in cases]
            semaphore = asyncio.Semaphore(concurrency)

            async def run_one(case: BenchmarkCase) -> StreamSample:
                async with semaphore:
                    cancel = randomizer.random() < cancel_fraction
                    return await _run_with_optional_cancellation(
                        client,
                        endpoint=endpoint,
                        case=case,
                        concurrency=concurrency,
                        browser_session_id=str(uuid4()),
                        token=token,
                        cancel_after_ms=cancel_after_ms if cancel else None,
                    )

            samples = await asyncio.gather(*(run_one(case) for case in jobs))
            wall_time_ms = _elapsed_ms(scenario_started)
            summary = summarize_samples(samples)
            summary["wall_time_ms"] = wall_time_ms
            summary["throughput_requests_per_second"] = round(
                len(samples) / (max(wall_time_ms, 0.001) / 1000),
                4,
            )
            scenarios.append(
                {
                    "concurrency": concurrency,
                    "summary": summary,
                    "samples": [asdict(sample) for sample in samples],
                }
            )
    return {
        "schema_version": "hemovet-chat-sse-benchmark-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "configuration": {
            "case_count": len(cases),
            "concurrency_levels": concurrency_levels,
            "repetitions": repetitions,
            "timeout_seconds": timeout_seconds,
            "warmup_requests": warmup,
            "cancel_fraction": cancel_fraction,
            "cancel_after_ms": cancel_after_ms,
            "seed": seed,
        },
        "runtime_metadata": _safe_runtime_metadata(metadata or {}),
        "warmup": summarize_samples(warmup_samples),
        "scenarios": scenarios,
    }


def _chat_endpoint(base_url: str) -> str:
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("invalid_base_url")
    return base_url.rstrip("/") + "/chat/stream"


def _parse_concurrency(value: str) -> list[int]:
    try:
        levels = [int(item.strip()) for item in value.split(",") if item.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("concurrency inválida") from exc
    if not levels or any(level < 1 or level > 64 for level in levels):
        raise argparse.ArgumentTypeError("concurrency debe estar entre 1 y 64")
    return list(dict.fromkeys(levels))


def _safe_code(value: object) -> str | None:
    normalized = str(value or "").strip()
    return normalized if _CODE_PATTERN.fullmatch(normalized) else None


def _optional_text(value: object) -> str | None:
    normalized = str(value or "").strip()
    return normalized[:128] if normalized else None


def _safe_runtime_metadata(values: dict[str, object]) -> dict[str, object]:
    allowed = {
        "context_length",
        "embedding_version",
        "model_digest",
        "model_name",
        "prompt_version",
        "quantization",
        "reranker_model",
        "retriever_version",
    }
    return {
        key: normalized
        for key, value in values.items()
        if key in allowed
        for normalized in [_safe_code(value)]
        if normalized is not None
    }


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 3)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark reproducible del SSE validado de HemoVet.",
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api/v1")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--concurrency", type=_parse_concurrency, default=[1, 2, 4, 8])
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--timeout-seconds", type=float, default=90.0)
    parser.add_argument("--cancel-fraction", type=float, default=0.0)
    parser.add_argument("--cancel-after-ms", type=float, default=500.0)
    parser.add_argument("--seed", type=int, default=20260719)
    parser.add_argument("--model-name")
    parser.add_argument("--model-digest")
    parser.add_argument("--quantization")
    parser.add_argument("--context-length", type=int)
    parser.add_argument("--prompt-version")
    parser.add_argument("--retriever-version")
    parser.add_argument("--embedding-version")
    parser.add_argument("--reranker-model")
    parser.add_argument("--token-env", default="HEMOVET_BENCHMARK_TOKEN")
    parser.add_argument("--allow-unauthenticated", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fail-on-error", action="store_true")
    args = parser.parse_args()
    if args.repetitions < 1 or args.repetitions > 1_000:
        parser.error("--repetitions debe estar entre 1 y 1000")
    if args.warmup < 0 or args.warmup > 100:
        parser.error("--warmup debe estar entre 0 y 100")
    if args.timeout_seconds <= 0 or args.timeout_seconds > 600:
        parser.error("--timeout-seconds debe estar entre 0 y 600")
    if not 0 <= args.cancel_fraction <= 1:
        parser.error("--cancel-fraction debe estar entre 0 y 1")
    if args.cancel_after_ms <= 0:
        parser.error("--cancel-after-ms debe ser positivo")
    if args.context_length is not None and args.context_length <= 0:
        parser.error("--context-length debe ser positivo")
    token = os.environ.get(args.token_env)
    if not token and not args.allow_unauthenticated:
        parser.error(
            f"falta el token en la variable {args.token_env}; "
            "usa --allow-unauthenticated solo en un entorno local controlado"
        )
    try:
        cases = load_cases(args.dataset)
        result = asyncio.run(
            run_benchmark(
                base_url=args.base_url,
                cases=cases,
                concurrency_levels=args.concurrency,
                repetitions=args.repetitions,
                timeout_seconds=args.timeout_seconds,
                token=token,
                warmup=args.warmup,
                cancel_fraction=args.cancel_fraction,
                cancel_after_ms=args.cancel_after_ms,
                seed=args.seed,
                metadata={
                    "model_name": args.model_name,
                    "model_digest": args.model_digest,
                    "quantization": args.quantization,
                    "context_length": args.context_length,
                    "prompt_version": args.prompt_version,
                    "retriever_version": args.retriever_version,
                    "embedding_version": args.embedding_version,
                    "reranker_model": args.reranker_model,
                },
            )
        )
    except (OSError, ValueError, httpx.HTTPError) as exc:
        parser.exit(2, f"ERROR: {type(exc).__name__}\n")
    serialized = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(serialized + "\n", encoding="utf-8")
    else:
        sys.stdout.write(serialized + "\n")
    errors = sum(
        int(scenario["summary"]["errors"])
        for scenario in result["scenarios"]
        if isinstance(scenario, dict) and isinstance(scenario.get("summary"), dict)
    )
    return 1 if args.fail_on_error and errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
