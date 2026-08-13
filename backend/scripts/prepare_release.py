#!/usr/bin/env python3
"""Render a private production environment and its immutable release manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from app.core.artifact_registry_contract import load_artifact_set
from app.core.availability import AVAILABILITY_CONTRACT_VERSION
from app.core.release_manifest import (
    RELEASE_MANIFEST_CONTRACT_VERSION,
    ReleaseManifest,
    canonical_release_manifest,
)
from app.modules.llm_chat.domain.provider_contract import (
    LLM_PROVIDER_CONTRACT_VERSION,
)
from scripts.validate_deploy_env import validate_env_file


DERIVED_ENVIRONMENT_KEYS = (
    "HEMOVET_BUILD_REVISION",
    "HEMOVET_BACKEND_IMAGE",
    "HEMOVET_FRONTEND_IMAGE",
    "OLLAMA_BASE_URL",
    "RAG_COLLECTION_NAME",
)
RAG_BASE_COLLECTION = "hemovet_canine_hematology_v2"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ReleasePreparationError(ValueError):
    """The release inputs do not form one closed, deployable revision."""


def _sha256(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def _atomic_write(path: Path, content: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _environment_values(content: str) -> tuple[dict[str, str], set[str]]:
    values: dict[str, str] = {}
    duplicates: set[str] = set()
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in values:
            duplicates.add(key)
        values[key] = value.strip().strip('"').strip("'")
    return values, duplicates


def _render_environment(content: str, replacements: dict[str, str]) -> bytes:
    _, duplicates = _environment_values(content)
    ambiguous = duplicates.intersection(replacements)
    if ambiguous:
        raise ReleasePreparationError(
            "duplicate derived environment keys: " + ",".join(sorted(ambiguous))
        )

    seen: set[str] = set()
    rendered: list[str] = []
    for raw_line in content.splitlines():
        candidate = raw_line.strip()
        exported = candidate.startswith("export ")
        assignment = candidate[7:].lstrip() if exported else candidate
        key = assignment.split("=", 1)[0].strip() if "=" in assignment else ""
        if key in replacements:
            rendered.append(f"{key}={replacements[key]}")
            seen.add(key)
        else:
            rendered.append(raw_line)
    for key in DERIVED_ENVIRONMENT_KEYS:
        if key not in seen:
            rendered.append(f"{key}={replacements[key]}")
    return ("\n".join(rendered).rstrip("\n") + "\n").encode("utf-8")


def prepare_release(
    *,
    base_environment: Path,
    artifact_set_path: Path,
    rag_summary_path: Path,
    caddy_configuration: Path,
    bundle_manifest: Path,
    github_sha: str,
    repository: str,
    workflow_run_id: int,
    workflow_run_attempt: int,
    created_at: str,
    ollama_base_url: str,
    candidate_environment: Path,
    release_manifest: Path,
) -> ReleaseManifest:
    artifact_set = load_artifact_set(artifact_set_path)
    if artifact_set.release_id != github_sha:
        raise ReleasePreparationError("artifact_set.release_id")
    if artifact_set.source.repository != repository:
        raise ReleasePreparationError("artifact_set.source.repository")

    rag_summary = json.loads(rag_summary_path.read_text(encoding="utf-8"))
    fingerprint = str(rag_summary.get("index_fingerprint") or "")
    corpus_revision = str(rag_summary.get("corpus_revision") or "")
    chunk_schema_version = str(rag_summary.get("schema_version") or "")
    corpus_schema_version = str(
        rag_summary.get("corpus_schema_version") or ""
    )
    if (
        rag_summary.get("dry_run") is not True
        or SHA256_RE.fullmatch(fingerprint) is None
        or not corpus_revision
        or not chunk_schema_version
        or not corpus_schema_version
        or int(rag_summary.get("sources") or 0) <= 0
        or int(rag_summary.get("chunks") or 0) <= 0
        or int(rag_summary.get("quarantined_sources") or 0) != 0
    ):
        raise ReleasePreparationError("rag_summary")
    collection_name = f"{RAG_BASE_COLLECTION}__{fingerprint[:12]}"

    base_content = base_environment.read_text(encoding="utf-8")
    backend_image = artifact_set.image("backend").canonical_reference
    frontend_image = artifact_set.image("frontend").canonical_reference
    candidate_content = _render_environment(
        base_content,
        {
            "HEMOVET_BUILD_REVISION": github_sha,
            "HEMOVET_BACKEND_IMAGE": backend_image,
            "HEMOVET_FRONTEND_IMAGE": frontend_image,
            "OLLAMA_BASE_URL": ollama_base_url,
            "RAG_COLLECTION_NAME": collection_name,
        },
    )
    environment, duplicates = _environment_values(
        candidate_content.decode("utf-8")
    )
    if duplicates:
        raise ReleasePreparationError("duplicate_environment_keys")
    if environment.get("RAG_SCHEMA_VERSION") != corpus_schema_version:
        raise ReleasePreparationError("rag_schema_version")
    _atomic_write(candidate_environment, candidate_content, 0o600)
    try:
        validate_env_file(candidate_environment)
    except Exception:
        candidate_environment.unlink(missing_ok=True)
        raise

    model_digest = str(environment["OLLAMA_EXPECTED_MODEL_DIGEST"])
    if not model_digest.startswith("sha256:"):
        model_digest = f"sha256:{model_digest}"
    manifest = ReleaseManifest.model_validate(
        {
            "schema_version": RELEASE_MANIFEST_CONTRACT_VERSION,
            "release_id": github_sha,
            "source": {
                "github_sha": github_sha,
                "repository": repository,
                "workflow_run_id": workflow_run_id,
                "workflow_run_attempt": workflow_run_attempt,
                "created_at": created_at,
            },
            "application": {
                "revision": github_sha,
                "backend": {
                    "reference": artifact_set.image("backend").canonical_reference,
                    "digest": artifact_set.image("backend").digest,
                },
                "frontend": {
                    "reference": artifact_set.image("frontend").canonical_reference,
                    "digest": artifact_set.image("frontend").digest,
                },
                "configuration_digest": _sha256(candidate_content),
                "caddy_configuration_digest": _sha256(
                    caddy_configuration.read_bytes()
                ),
            },
            "gpu_runtime": {
                "revision": github_sha,
                "runtime": {
                    "reference": artifact_set.image(
                        "ollama-runtime"
                    ).canonical_reference,
                    "digest": artifact_set.image("ollama-runtime").digest,
                },
                "startup_bundle_digest": _sha256(bundle_manifest.read_bytes()),
                "startup_contract_version": "hemovet.gpu-startup/v1",
                "model": {
                    "name": environment["OLLAMA_MODEL"],
                    "digest": model_digest,
                    "quantization": environment[
                        "OLLAMA_EXPECTED_QUANTIZATION"
                    ],
                },
                "apply_on": "next_boot",
                "initial_validation_state": "pending_boot_validation",
                "update_while_running": False,
            },
            "rag": {
                "required": environment["RAG_ENABLED"].casefold()
                in {"1", "true", "yes", "on"},
                "collection_name": collection_name,
                "corpus_revision": corpus_revision,
                "index_fingerprint": fingerprint,
                "schema_version": environment["RAG_SCHEMA_VERSION"],
                "embedding_model": environment["RAG_EMBEDDING_MODEL"],
                "embedding_revision": environment[
                    "RAG_EMBEDDING_MODEL_REVISION"
                ],
            },
            "contracts": {
                "release_manifest": RELEASE_MANIFEST_CONTRACT_VERSION,
                "availability": AVAILABILITY_CONTRACT_VERSION,
                "llm_provider": LLM_PROVIDER_CONTRACT_VERSION,
            },
        }
    )
    _atomic_write(
        release_manifest,
        (canonical_release_manifest(manifest) + "\n").encode("utf-8"),
        0o600,
    )
    print(f"prepared {manifest.schema_version}: {manifest.release_id}")
    return manifest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-environment", required=True, type=Path)
    parser.add_argument("--artifact-set", required=True, type=Path)
    parser.add_argument("--rag-summary", required=True, type=Path)
    parser.add_argument("--caddy-configuration", required=True, type=Path)
    parser.add_argument("--bundle-manifest", required=True, type=Path)
    parser.add_argument("--github-sha", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--workflow-run-id", required=True, type=int)
    parser.add_argument("--workflow-run-attempt", required=True, type=int)
    parser.add_argument("--created-at", required=True)
    parser.add_argument("--ollama-base-url", required=True)
    parser.add_argument("--candidate-environment", required=True, type=Path)
    parser.add_argument("--release-manifest", required=True, type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    prepare_release(
        base_environment=args.base_environment,
        artifact_set_path=args.artifact_set,
        rag_summary_path=args.rag_summary,
        caddy_configuration=args.caddy_configuration,
        bundle_manifest=args.bundle_manifest,
        github_sha=args.github_sha,
        repository=args.repository,
        workflow_run_id=args.workflow_run_id,
        workflow_run_attempt=args.workflow_run_attempt,
        created_at=args.created_at,
        ollama_base_url=args.ollama_base_url,
        candidate_environment=args.candidate_environment,
        release_manifest=args.release_manifest,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
