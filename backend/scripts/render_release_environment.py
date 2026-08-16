#!/usr/bin/env python3
"""Render and verify a private environment from a validated release manifest."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from app.core.release_manifest import load_release_manifest
from scripts.prepare_release import _atomic_write, _render_environment
from scripts.validate_deploy_env import validate_env_file


def render_release_environment(
    base_environment: Path,
    release_manifest: Path,
    ollama_base_url: str,
    output: Path,
) -> None:
    release = load_release_manifest(release_manifest)
    rendered = _render_environment(
        base_environment.read_text(encoding="utf-8"),
        {
            "HEMOVET_BUILD_REVISION": release.release_id,
            "HEMOVET_BACKEND_IMAGE": release.application.backend.reference,
            "HEMOVET_FRONTEND_IMAGE": release.application.frontend.reference,
            "OLLAMA_BASE_URL": ollama_base_url,
            "RAG_COLLECTION_NAME": release.rag.collection_name,
            # Del MANIFIESTO, no de un argumento: es lo que hace que este
            # renderizado y el del runner produzcan el mismo texto y el mismo
            # sha256. La cadena de confianza no se rodea; se le anade una entrada.
            "CHAT_SERVER_WRITES_ENABLED": (
                "1" if release.application.chat_server_writes else "0"
            ),
        },
    )
    actual_digest = f"sha256:{hashlib.sha256(rendered).hexdigest()}"
    if actual_digest != release.application.configuration_digest:
        raise ValueError("release_environment_digest_mismatch")
    _atomic_write(output, rendered, 0o600)
    try:
        validate_env_file(output)
    except Exception:
        output.unlink(missing_ok=True)
        raise
    print(f"rendered validated environment for {release.release_id}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-environment", required=True, type=Path)
    parser.add_argument("--release-manifest", required=True, type=Path)
    parser.add_argument("--ollama-base-url", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    render_release_environment(
        args.base_environment,
        args.release_manifest,
        args.ollama_base_url,
        args.output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
