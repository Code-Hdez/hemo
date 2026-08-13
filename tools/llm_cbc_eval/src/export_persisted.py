#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any

from .client import ChatEvalClient
from .runner import load_config


def conversation_ids(path: Path) -> list[str]:
    identifiers: list[str] = []
    with path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            if not raw_line.strip():
                continue
            result = json.loads(raw_line)
            identifier = str(result.get("conversation_id") or "").strip()
            if not identifier:
                error = result.get("stream_error_event")
                if isinstance(error, dict):
                    identifier = str(error.get("conversation_id") or "").strip()
            if identifier:
                identifiers.append(identifier)
    return list(dict.fromkeys(identifiers))


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as handle:
        handle.write(serialized)
        temporary = Path(handle.name)
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Exporta localmente los mensajes persistidos por PostgreSQL para "
            "las conversaciones registradas en una batería JSONL."
        )
    )
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-jsonl", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    run_bytes = args.run_jsonl.read_bytes()
    identifiers = conversation_ids(args.run_jsonl)
    exports: list[dict[str, Any]] = []
    with ChatEvalClient(load_config(args.config)) as client:
        client.login_if_configured()
        for index, identifier in enumerate(identifiers, start=1):
            exports.append(
                {
                    "conversation_id": identifier,
                    "messages": client.conversation_messages(identifier),
                }
            )
            if index % 50 == 0:
                print(f"exportadas={index}/{len(identifiers)}")

    payload = {
        "schema": "hemovet.persisted-chat-export/v1",
        "exported_at": datetime.now(UTC).isoformat(),
        "source_jsonl": args.run_jsonl.name,
        "source_sha256": hashlib.sha256(run_bytes).hexdigest(),
        "conversation_count": len(exports),
        "conversations": exports,
    }
    _write_json_atomic(args.output, payload)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
