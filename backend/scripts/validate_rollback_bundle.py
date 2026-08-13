#!/usr/bin/env python3
"""Validate one closed, immutable HemoVet rollback target.

The command joins the application release, OCI artifact set, private candidate
environment, source tree and GPU boot projection before any rollback mutation.
Its output is deliberately limited to non-secret identities.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from types import ModuleType

from app.core.artifact_registry_contract import load_artifact_set
from app.core.release_manifest import load_release_manifest
from scripts.validate_release_payload import validate_release_payload


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_CONTRACT_PATH = PROJECT_ROOT / "deploy" / "gpu" / "runtime_contract.py"


class RollbackBundleError(ValueError):
    """Rollback inputs do not identify one closed immutable revision."""


def _runtime_contract() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "hemovet_gpu_rollback_runtime_contract",
        RUNTIME_CONTRACT_PATH,
    )
    if spec is None or spec.loader is None:
        raise RollbackBundleError("gpu_runtime_contract")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_rollback_bundle(
    *,
    release_manifest: Path,
    artifact_set: Path,
    candidate_environment: Path,
    source_root: Path,
    gpu_release: Path,
    bundle_manifest: Path,
) -> dict[str, object]:
    """Return a sanitized rollback plan after validating every identity."""

    release = load_release_manifest(release_manifest)
    artifacts = load_artifact_set(artifact_set)
    validate_release_payload(release_manifest, candidate_environment, source_root)

    runtime_contract = _runtime_contract()
    gpu_payload = runtime_contract.load_manifest(gpu_release)
    gpu = runtime_contract.validate_manifest(
        gpu_payload,
        expected_bundle_digest=runtime_contract.bundle_digest(bundle_manifest),
    )

    if artifacts.release_id != release.release_id:
        raise RollbackBundleError("artifact_set.release_id")
    if artifacts.source.repository != release.source.repository:
        raise RollbackBundleError("artifact_set.source.repository")
    if gpu["release_id"] != release.release_id:
        raise RollbackBundleError("gpu_release.release_id")

    expected_images = {
        "backend": release.application.backend,
        "frontend": release.application.frontend,
        "ollama-runtime": release.gpu_runtime.runtime,
    }
    for package, expected in expected_images.items():
        published = artifacts.image(package)
        if (
            published.digest != expected.digest
            or published.canonical_reference != expected.reference
        ):
            raise RollbackBundleError(f"artifact_set.images.{package}")

    if gpu["runtime"] != release.gpu_runtime.runtime.model_dump():
        raise RollbackBundleError("gpu_release.runtime")
    if gpu["model"] != release.gpu_runtime.model.model_dump():
        raise RollbackBundleError("gpu_release.model")
    if gpu["startup"] != {
        "contract_version": release.gpu_runtime.startup_contract_version,
        "bundle_digest": release.gpu_runtime.startup_bundle_digest,
    }:
        raise RollbackBundleError("gpu_release.startup")

    return {
        "schema_version": "hemovet.rollback-plan/v1",
        "release_id": release.release_id,
        "backend_digest": release.application.backend.digest,
        "frontend_digest": release.application.frontend.digest,
        "gpu_runtime_digest": release.gpu_runtime.runtime.digest,
        "model_digest": release.gpu_runtime.model.digest,
        "rag_collection": release.rag.collection_name,
        "rag_fingerprint": release.rag.index_fingerprint,
        "gpu_revision_state": gpu["revision_state"],
        "gpu_apply_on": gpu["apply_on"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-manifest", required=True, type=Path)
    parser.add_argument("--artifact-set", required=True, type=Path)
    parser.add_argument("--candidate-environment", required=True, type=Path)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--gpu-release", required=True, type=Path)
    parser.add_argument("--bundle-manifest", required=True, type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        plan = validate_rollback_bundle(
            release_manifest=args.release_manifest,
            artifact_set=args.artifact_set,
            candidate_environment=args.candidate_environment,
            source_root=args.source_root,
            gpu_release=args.gpu_release,
            bundle_manifest=args.bundle_manifest,
        )
    except Exception as exc:
        print(f"ERROR: invalid rollback bundle: {type(exc).__name__}")
        return 1
    print(json.dumps(plan, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
