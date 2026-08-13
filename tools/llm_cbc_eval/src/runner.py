#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:  # noqa: SIM105 - keeps direct script execution and package imports working.
    from .client import ChatEvalClient
    from .models import EvalConfig, EvalResult, Question
    from .report import write_csv_summary, write_markdown_report
    from .validators import classify_status, run_checks
except ImportError:  # pragma: no cover - exercised when run as a file.
    from src.client import ChatEvalClient  # type: ignore
    from src.models import EvalConfig, EvalResult, Question  # type: ignore
    from src.report import write_csv_summary, write_markdown_report  # type: ignore
    from src.validators import classify_status, run_checks  # type: ignore


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ejecuta un banco QA contra /api/v1/chat/stream y genera Markdown."
    )
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--modes", nargs="*", default=None)
    parser.add_argument("--category", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--skip-health", action="store_true")
    parser.add_argument(
        "--skip-completed-jsonl",
        type=Path,
        default=None,
        help=(
            "Reanuda una batería omitiendo pares pregunta/modo con resultado "
            "PASS, WARNING o FAIL; los ERROR se vuelven a ejecutar."
        ),
    )
    args = parser.parse_args()

    config = load_config(args.config)
    questions = load_questions(args.questions)
    if args.category:
        questions = [q for q in questions if q.categoria == args.category]
    if args.limit is not None:
        questions = questions[: args.limit]
    requested_modes = args.modes or list(config.mode_map.keys())
    validate_context(config, requested_modes)
    completed_keys = (
        load_completed_keys(args.skip_completed_jsonl)
        if args.skip_completed_jsonl
        else set()
    )

    run_id = datetime.now(UTC).strftime("eval-%Y%m%dT%H%M%SZ")
    output_root = Path(config.output_dir)
    raw_dir = output_root / "raw"
    report_dir = output_root / "reports"
    summary_dir = output_root / "summaries"
    raw_dir.mkdir(parents=True, exist_ok=True)
    git_commit = git_rev()
    jsonl_path = raw_dir / f"{run_id}.jsonl"
    json_path = raw_dir / f"{run_id}.json"
    results: list[EvalResult] = []
    conversations: dict[str, str] = {}

    with ChatEvalClient(config) as client:
        client.login_if_configured()
        if not args.skip_health:
            client.health()
        for question in questions:
            modes = _modes_for_question(question, requested_modes)
            for requested_mode in modes:
                if (question.id, requested_mode) in completed_keys:
                    continue
                backend_mode = config.mode_map[requested_mode]
                conversation_key = (
                    f"{requested_mode}:{question.conversation_group}"
                    if config.reuse_conversation and question.conversation_group
                    else None
                )
                payload = build_payload(
                    config,
                    backend_mode,
                    question.pregunta,
                    conversation_id=(
                        conversations.get(conversation_key)
                        if conversation_key
                        else None
                    ),
                )
                execution = stream_with_auth_refresh(client, payload)
                if config.retries and execution.error_type:
                    for _ in range(config.retries):
                        time.sleep(config.retry_backoff_seconds)
                        execution = stream_with_auth_refresh(
                            client,
                            build_payload(
                                config,
                                backend_mode,
                                question.pregunta,
                                conversation_id=(
                                    conversations.get(conversation_key)
                                    if conversation_key
                                    else None
                                ),
                            )
                        )
                        if not execution.error_type:
                            break
                if conversation_key and execution.conversation_id:
                    conversations[conversation_key] = execution.conversation_id
                checks = run_checks(question=question, execution=execution, config=config)
                status = classify_status(checks, execution)
                result = EvalResult(
                    run_id=run_id,
                    timestamp=datetime.now(UTC).isoformat(),
                    git_commit=git_commit,
                    question=question,
                    requested_mode=requested_mode,
                    backend_mode=backend_mode,
                    payload=payload,
                    execution=execution,
                    checks=checks,
                    status=status,
                )
                append_jsonl(jsonl_path, result.to_json())
                results.append(result)
                print(
                    f"{question.id} [{requested_mode}] {status} "
                    f"{execution.duration_ms}ms"
                )

    json_path.write_text(
        json.dumps([result.to_json() for result in results], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_markdown_report(report_dir / f"{run_id}.md", results, config)
    write_csv_summary(summary_dir / f"{run_id}.csv", results)
    print(f"Resultados JSON: {json_path}")
    print(f"Reporte Markdown: {report_dir / f'{run_id}.md'}")
    print(f"Resumen CSV: {summary_dir / f'{run_id}.csv'}")
    return 0


def load_config(path: Path) -> EvalConfig:
    return EvalConfig.from_mapping(json.loads(path.read_text(encoding="utf-8")))


def load_questions(path: Path) -> list[Question]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    values = data.get("questions") if isinstance(data, dict) else data
    if not isinstance(values, list):
        raise ValueError("El archivo de preguntas debe contener una lista o la clave 'questions'.")
    questions = [Question.from_mapping(item) for item in values if isinstance(item, dict)]
    invalid = [question for question in questions if not question.id or not question.pregunta]
    if invalid:
        raise ValueError("Hay preguntas sin id o sin texto.")
    return questions


def validate_context(config: EvalConfig, requested_modes: list[str]) -> None:
    unknown = [mode for mode in requested_modes if mode not in config.mode_map]
    if unknown:
        raise ValueError(f"Modos no configurados: {', '.join(unknown)}")
    backend_modes = {config.mode_map[mode] for mode in requested_modes}
    if backend_modes & {"selected_hemogram", "uploaded_analysis"} and not config.selected_analysis_id:
        raise ValueError("El modo seleccionado requiere context.selected_analysis_id.")
    if "hemogram_history" in backend_modes and not config.historical_pet_id:
        raise ValueError("hemogram_history requiere context.historical_pet_id.")
    if (
        "historical_analysis" in backend_modes
        and not config.historical_pet_id
        and not config.historical_analysis_id
    ):
        raise ValueError(
            "historical_analysis requiere context.historical_pet_id (o el "
            "historical_analysis_id legado)."
        )


def build_payload(
    config: EvalConfig,
    mode: str,
    message: str,
    *,
    conversation_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "client_message_id": str(uuid4()),
        "conversation_id": conversation_id,
        "message": message,
        "context_scope": mode,
        "options": {"thinking": False},
    }
    if mode in {"selected_hemogram", "uploaded_analysis"}:
        payload["analysis_id"] = config.selected_analysis_id
    elif mode in {"hemogram_history", "historical_analysis"}:
        if config.historical_pet_id:
            payload["pet_id"] = config.historical_pet_id
        elif config.historical_analysis_id:
            payload["analysis_id"] = config.historical_analysis_id
    return payload


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def load_completed_keys(path: Path) -> set[tuple[str, str]]:
    completed: set[tuple[str, str]] = set()
    with path.open(encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                result = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"JSONL de reanudación inválido en línea {line_number}."
                ) from exc
            if result.get("status") == "ERROR":
                continue
            question_id = str(result.get("question_id") or "").strip()
            mode = str(result.get("modo") or "").strip()
            if question_id and mode:
                completed.add((question_id, mode))
    return completed


def stream_with_auth_refresh(
    client: ChatEvalClient, payload: dict[str, Any]
) -> Any:
    """Retry one request after refreshing an expired login-based JWT."""
    execution = client.stream_chat(payload)
    if execution.http_status != 401:
        return execution
    if not client.refresh_login():
        return execution
    return client.stream_chat(payload)


def git_rev() -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    return completed.stdout.strip() or None


def _modes_for_question(question: Question, requested_modes: list[str]) -> list[str]:
    if not question.modos_aplicables:
        return requested_modes
    allowed = set(question.modos_aplicables)
    return [mode for mode in requested_modes if mode in allowed]


if __name__ == "__main__":
    raise SystemExit(main())
