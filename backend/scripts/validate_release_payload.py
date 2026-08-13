#!/usr/bin/env python3
"""Validate source/configuration identities before a production mutation."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from app.core.release_manifest import load_release_manifest
from scripts.prepare_release import _environment_values
from scripts.validate_deploy_env import validate_env_file


def _digest(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def validate_release_payload(
    release_manifest: Path,
    environment: Path,
    source_root: Path,
) -> None:
    release = load_release_manifest(release_manifest)
    validate_env_file(environment)
    if _digest(environment) != release.application.configuration_digest:
        raise ValueError("configuration_digest")
    if _digest(source_root / "deploy" / "Caddyfile") != (
        release.application.caddy_configuration_digest
    ):
        raise ValueError("caddy_configuration_digest")
    values, duplicates = _environment_values(environment.read_text(encoding="utf-8"))
    if duplicates:
        raise ValueError("duplicate_environment_keys")
    expected = {
        "HEMOVET_BUILD_REVISION": release.release_id,
        "HEMOVET_BACKEND_IMAGE": release.application.backend.reference,
        "HEMOVET_FRONTEND_IMAGE": release.application.frontend.reference,
        "RAG_COLLECTION_NAME": release.rag.collection_name,
    }
    if any(values.get(key) != value for key, value in expected.items()):
        raise ValueError("release_environment_identity")
    print(f"valid deployment payload: {release.release_id}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-manifest", required=True, type=Path)
    parser.add_argument("--environment", required=True, type=Path)
    parser.add_argument("--source-root", required=True, type=Path)
    args = parser.parse_args()
    validate_release_payload(
        args.release_manifest,
        args.environment,
        args.source_root,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
