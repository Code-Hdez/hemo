#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:  # noqa: SIM105 - keeps direct script execution and package imports working.
    from .metrics import evaluate
    from .records import latest_run_id, load_turns
    from .report import render_markdown, write_markdown
    from .semantic import (
        DEFAULT_CACHE_DIR,
        DEFAULT_EMBEDDING_MODEL,
        EmbeddingUnavailableError,
        calibrate_grounding,
        measure_relevance,
    )
except ImportError:  # pragma: no cover - exercised when run as a file.
    from src.metrics import evaluate  # type: ignore
    from src.records import latest_run_id, load_turns  # type: ignore
    from src.report import render_markdown, write_markdown  # type: ignore
    from src.semantic import (  # type: ignore
        DEFAULT_CACHE_DIR,
        DEFAULT_EMBEDDING_MODEL,
        EmbeddingUnavailableError,
        calibrate_grounding,
        measure_relevance,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Calcula métricas offline sobre respuestas ya capturadas y emite "
            "una tabla Markdown lista para el documento de tesis."
        )
    )
    parser.add_argument("--answers", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--run",
        default=None,
        help=(
            "Identificador de corrida a evaluar, o `last` para la más reciente. "
            "Por defecto se agregan todas las corridas de los ficheros."
        ),
    )
    parser.add_argument(
        "--semantic",
        action="store_true",
        help="Añade la relevancia pregunta/respuesta usando el embebedor local.",
    )
    parser.add_argument(
        "--knowledge-dir",
        type=Path,
        default=None,
        help=(
            "Directorio de documentos aprobados. Con --semantic activa además la "
            "calibración del anclaje respuesta/documento."
        ),
    )
    parser.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    parser.add_argument("--embedding-cache", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--sample-size", type=int, default=150)
    args = parser.parse_args()

    missing = [path for path in args.answers if not path.is_file()]
    if missing:
        parser.error("No existe: " + ", ".join(str(path) for path in missing))

    run_id = latest_run_id(args.answers) if args.run == "last" else args.run
    turns = load_turns(args.answers, run_id=run_id)
    if not turns:
        parser.error("Los ficheros no contienen turnos con un modo de contexto reconocible.")

    report = evaluate(turns)
    relevance = None
    grounding = None
    if args.semantic:
        try:
            relevance = measure_relevance(
                turns,
                model_name=args.embedding_model,
                cache_dir=args.embedding_cache,
                sample_size=args.sample_size,
            )
            if args.knowledge_dir:
                grounding = calibrate_grounding(
                    turns,
                    args.knowledge_dir,
                    model_name=args.embedding_model,
                    cache_dir=args.embedding_cache,
                )
        except EmbeddingUnavailableError as exc:
            print(f"Métricas semánticas omitidas: {exc}", file=sys.stderr)

    content = render_markdown(
        turns,
        report,
        sources=list(args.answers),
        run_id=run_id,
        relevance=relevance,
        grounding=grounding,
    )
    write_markdown(args.output, content)
    print(f"Informe escrito en {args.output} con {len(turns)} turnos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
