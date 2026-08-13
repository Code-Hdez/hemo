from __future__ import annotations

import argparse
import os
from pathlib import Path
import tempfile

from app.core.artifact_registry_contract import (
    bind_release_artifacts,
    load_artifact_set,
)
from app.core.release_manifest import (
    canonical_release_manifest,
    load_release_manifest,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Bind real OCI digests to a complete hemovet.release/v1 manifest. "
            "No deployment or publication is performed."
        )
    )
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--artifact-set", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        dir=path.parent,
        text=True,
    )
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    args = parse_args()
    manifest = load_release_manifest(args.manifest)
    artifact_set = load_artifact_set(args.artifact_set)
    bound = bind_release_artifacts(manifest, artifact_set)
    canonical = canonical_release_manifest(bound)
    if args.output:
        atomic_write(args.output, canonical)
        print(f"wrote validated {bound.schema_version}: {args.output}")
    else:
        print(canonical)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
