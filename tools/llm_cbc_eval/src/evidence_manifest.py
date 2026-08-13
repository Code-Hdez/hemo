#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import tempfile


def build_manifest(
    root: Path,
    *,
    output: Path,
    metadata: dict[str, str] | None = None,
) -> dict[str, object]:
    root = root.resolve()
    output = output.resolve()
    files: list[dict[str, object]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path.resolve() == output:
            continue
        payload = path.read_bytes()
        files.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    return {
        "schema": "hemovet.chat-evidence/v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "root": root.name,
        "metadata": dict(sorted((metadata or {}).items())),
        "file_count": len(files),
        "total_bytes": sum(int(item["bytes"]) for item in files),
        "files": files,
    }


def write_manifest(path: Path, manifest: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as handle:
        handle.write(payload)
        temporary = Path(handle.name)
    temporary.replace(path)


def _metadata(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        key, separator, item = value.partition("=")
        if not separator or not key.strip() or not item.strip():
            raise ValueError("Cada metadata debe usar key=value con valores no vacíos.")
        result[key.strip()] = item.strip()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Genera un inventario SHA-256 de la evidencia local del chat."
    )
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--set", action="append", default=[], dest="metadata")
    args = parser.parse_args()
    manifest = build_manifest(
        args.root,
        output=args.output,
        metadata=_metadata(args.metadata),
    )
    write_manifest(args.output, manifest)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
