#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = "hemovet.llm-general-battery-selection/v1"
ALGORITHM = "proportional-largest-remainder+sha256-ranking/v1"


def select_stratified(
    questions: list[dict[str, Any]],
    *,
    mode: str,
    sample_size: int,
    seed: str,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, int]]]:
    if sample_size <= 0:
        raise ValueError("sample_size debe ser mayor que cero.")
    identifiers = [str(item.get("id") or "").strip() for item in questions]
    if any(not identifier for identifier in identifiers):
        raise ValueError("Hay preguntas sin id.")
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Los ids de preguntas deben ser únicos.")

    indexed = [
        (index, item)
        for index, item in enumerate(questions)
        if mode in [str(value) for value in item.get("modos_aplicables", [])]
    ]
    if sample_size > len(indexed):
        raise ValueError(
            f"La muestra solicitada ({sample_size}) excede las preguntas aplicables "
            f"al modo {mode} ({len(indexed)})."
        )

    by_category: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    for index, item in indexed:
        by_category[str(item.get("categoria") or "sin_categoria")].append(
            (index, item)
        )

    total = len(indexed)
    allocations: dict[str, int] = {}
    remainders: list[tuple[float, str]] = []
    for category, values in by_category.items():
        exact = sample_size * len(values) / total
        allocations[category] = int(exact)
        remainders.append((exact - int(exact), category))

    remaining = sample_size - sum(allocations.values())
    for _, category in sorted(remainders, key=lambda item: (-item[0], item[1])):
        if remaining == 0:
            break
        if allocations[category] < len(by_category[category]):
            allocations[category] += 1
            remaining -= 1
    if remaining:
        raise RuntimeError("No fue posible completar la asignación estratificada.")

    selected: list[tuple[int, dict[str, Any]]] = []
    category_counts: dict[str, dict[str, int]] = {}
    for category, values in sorted(by_category.items()):
        ranked = sorted(
            values,
            key=lambda pair: hashlib.sha256(
                (
                    f"{seed}\0{pair[1].get('id')}\0"
                    f"{pair[1].get('pregunta', '')}"
                ).encode()
            ).hexdigest(),
        )
        take = allocations[category]
        selected.extend(ranked[:take])
        category_counts[category] = {
            "eligible": len(values),
            "selected": take,
        }

    selected.sort(key=lambda pair: pair[0])
    return [item for _, item in selected], category_counts


def build_manifest(
    *,
    source_path: Path,
    output_path: Path,
    source_count: int,
    eligible_count: int,
    selected: list[dict[str, Any]],
    mode: str,
    seed: str,
    category_counts: dict[str, dict[str, int]],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "algorithm": ALGORITHM,
        "seed": seed,
        "mode": mode,
        "backend_mode": "general" if mode == "informacion_general" else None,
        "source": {
            "path": source_path.as_posix(),
            "sha256": _sha256(source_path),
            "question_count": source_count,
        },
        "selection": {
            "path": output_path.as_posix(),
            "sha256": _sha256(output_path),
            "eligible_count": eligible_count,
            "selected_count": len(selected),
            "question_ids": [str(item["id"]) for item in selected],
            "categories": category_counts,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Selecciona una muestra estratificada reproducible de preguntas LLM."
    )
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--mode", default="informacion_general")
    parser.add_argument("--sample-size", type=int, required=True)
    parser.add_argument("--seed", required=True)
    args = parser.parse_args()

    source_payload = yaml.safe_load(args.source.read_text(encoding="utf-8")) or {}
    questions = (
        source_payload.get("questions")
        if isinstance(source_payload, dict)
        else source_payload
    )
    if not isinstance(questions, list) or not all(
        isinstance(item, dict) for item in questions
    ):
        raise ValueError("La fuente debe contener una lista de preguntas.")

    selected, category_counts = select_stratified(
        questions,
        mode=args.mode,
        sample_size=args.sample_size,
        seed=args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        yaml.safe_dump(
            {"questions": selected},
            allow_unicode=True,
            sort_keys=False,
            width=120,
        ),
        encoding="utf-8",
    )
    eligible_count = sum(
        args.mode in [str(value) for value in item.get("modos_aplicables", [])]
        for item in questions
    )
    manifest = build_manifest(
        source_path=args.source,
        output_path=args.output,
        source_count=len(questions),
        eligible_count=eligible_count,
        selected=selected,
        mode=args.mode,
        seed=args.seed,
        category_counts=category_counts,
    )
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False))
    return 0


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
