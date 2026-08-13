#!/usr/bin/env python3
"""Create and validate one immutable OCI artifact set for a GitHub revision."""

from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import tempfile

from app.core.artifact_registry_contract import (
    ARTIFACT_SET_CONTRACT_VERSION,
    ArtifactSet,
    canonical_artifact_set,
)


OLLAMA_UPSTREAM = (
    "docker.io/ollama/ollama:0.32.5@sha256:"
    "4dea9fb511947e24a84237bb636b0203abcb2ff0d3fbc7b4ff865deb91362131"
)


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def create_artifact_set(
    *,
    github_sha: str,
    repository: str,
    registry_repository: str,
    created_at: str,
    digests: dict[str, str],
) -> ArtifactSet:
    images: list[dict[str, str]] = []
    tag = f"sha-{github_sha}"
    for package in ("backend", "frontend", "ollama-runtime"):
        digest = digests[package]
        image: dict[str, str] = {
            "package": package,
            "source_revision": github_sha,
            "tag": tag,
            "tagged_reference": f"{registry_repository}/{package}:{tag}",
            "canonical_reference": f"{registry_repository}/{package}@{digest}",
            "digest": digest,
        }
        if package == "ollama-runtime":
            image["upstream_reference"] = OLLAMA_UPSTREAM
        images.append(image)
    return ArtifactSet.model_validate(
        {
            "schema_version": ARTIFACT_SET_CONTRACT_VERSION,
            "release_id": github_sha,
            "source": {
                "github_sha": github_sha,
                "repository": repository,
                "created_at": datetime.fromisoformat(
                    created_at.replace("Z", "+00:00")
                ),
            },
            "registry_repository": registry_repository,
            "images": images,
        }
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--github-sha", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--registry-repository", required=True)
    parser.add_argument("--created-at", required=True)
    parser.add_argument("--backend-digest", required=True)
    parser.add_argument("--frontend-digest", required=True)
    parser.add_argument("--gpu-digest", required=True)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    artifact_set = create_artifact_set(
        github_sha=args.github_sha,
        repository=args.repository,
        registry_repository=args.registry_repository,
        created_at=args.created_at,
        digests={
            "backend": args.backend_digest,
            "frontend": args.frontend_digest,
            "ollama-runtime": args.gpu_digest,
        },
    )
    _atomic_write(args.output, canonical_artifact_set(artifact_set))
    print(
        f"created {artifact_set.schema_version}: "
        f"{artifact_set.release_id} ({len(artifact_set.images)} images)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
