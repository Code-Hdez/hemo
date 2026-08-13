#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.validate_deploy_env import (  # noqa: E402
    PROMOTED_RAG_COLLECTION_PATTERN,
    RAG_COLLECTION_BASE,
)

FINGERPRINT_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class RAGPromotionError(ValueError):
    """The staged RAG result is not safe to promote."""


def _require_mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RAGPromotionError(field)
    return value


def promoted_collection(payload: object) -> str:
    document = _require_mapping(payload, "payload")
    promotion = _require_mapping(document.get("promotion"), "promotion")
    environment = _require_mapping(
        promotion.get("set_environment"),
        "promotion.set_environment",
    )
    snapshot = _require_mapping(document.get("snapshot"), "snapshot")

    collection = document.get("collection")
    configured_collection = environment.get("RAG_COLLECTION_NAME")
    fingerprint = document.get("index_fingerprint")
    snapshot_fingerprint = snapshot.get("index_fingerprint")
    chunk_count = snapshot.get("collection_chunks")

    if document.get("validated") is not True:
        raise RAGPromotionError("validated")
    if promotion.get("ready") is not True:
        raise RAGPromotionError("promotion.ready")
    if promotion.get("requires_backend_restart") is not True:
        raise RAGPromotionError("promotion.requires_backend_restart")
    if promotion.get("staging_namespace") != RAG_COLLECTION_BASE:
        raise RAGPromotionError("promotion.staging_namespace")
    if promotion.get("rollback_requires_previous_release") is not True:
        raise RAGPromotionError("promotion.rollback_requires_previous_release")
    if (
        not isinstance(collection, str)
        or PROMOTED_RAG_COLLECTION_PATTERN.fullmatch(collection) is None
    ):
        raise RAGPromotionError("collection")
    if configured_collection != collection:
        raise RAGPromotionError("promotion.set_environment.RAG_COLLECTION_NAME")
    if (
        not isinstance(fingerprint, str)
        or FINGERPRINT_PATTERN.fullmatch(fingerprint) is None
    ):
        raise RAGPromotionError("index_fingerprint")
    if snapshot_fingerprint != fingerprint:
        raise RAGPromotionError("snapshot.index_fingerprint")
    if collection != f"{RAG_COLLECTION_BASE}__{fingerprint[:12]}":
        raise RAGPromotionError("collection_fingerprint_mismatch")
    if (
        not isinstance(chunk_count, int)
        or isinstance(chunk_count, bool)
        or chunk_count < 1
    ):
        raise RAGPromotionError("snapshot.collection_chunks")
    return collection


def _env_key(raw_line: str) -> str | None:
    line = raw_line.strip()
    if not line or line.startswith("#"):
        return None
    if line.startswith("export "):
        line = line[7:].lstrip()
    if "=" not in line:
        return None
    return line.split("=", 1)[0].strip()


def _replace_collection(source: str, collection: str) -> str:
    lines = source.splitlines(keepends=True)
    matches = [
        index
        for index, line in enumerate(lines)
        if _env_key(line) == "RAG_COLLECTION_NAME"
    ]
    if len(matches) != 1:
        raise RAGPromotionError("environment.RAG_COLLECTION_NAME")

    index = matches[0]
    newline = "\r\n" if lines[index].endswith("\r\n") else "\n"
    if not lines[index].endswith(("\n", "\r")):
        newline = ""
    lines[index] = f"RAG_COLLECTION_NAME={collection}{newline}"
    return "".join(lines)


def _write_atomic(path: Path, content: str, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_path, mode)
        os.replace(temporary_path, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def prepare_rag_promotion(
    promotion_json: Path,
    source_env: Path,
    target_env: Path,
) -> str:
    if source_env.resolve() == target_env.resolve():
        raise RAGPromotionError("environment_target_must_be_private_copy")
    try:
        payload = json.loads(promotion_json.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RAGPromotionError("promotion_json") from exc
    try:
        source = source_env.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise RAGPromotionError("source_environment") from exc

    collection = promoted_collection(payload)
    candidate = _replace_collection(source, collection)
    try:
        _write_atomic(target_env, candidate, 0o600)
    except OSError as exc:
        raise RAGPromotionError("target_environment") from exc
    return collection


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepara un entorno privado para promover una colección RAG validada."
    )
    parser.add_argument("--promotion-json", type=Path, required=True)
    parser.add_argument("--source-env", type=Path, required=True)
    parser.add_argument("--target-env", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        collection = prepare_rag_promotion(
            args.promotion_json,
            args.source_env,
            args.target_env,
        )
    except RAGPromotionError as exc:
        print(f"ERROR: promoción RAG inválida: {exc}", file=sys.stderr)
        return 1
    print(collection)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
