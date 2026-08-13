#!/usr/bin/env python3
"""Install and roll back a complete production environment transactionally.

The RAG collection is selected exclusively by ``RAG_COLLECTION_NAME`` inside
the environment file. Installing the complete candidate with one atomic
replace therefore changes application configuration and the RAG pointer as a
single unit. The previous file is retained verbatim in a private transaction
directory so rollback never mutates or deletes a Chroma collection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.validate_deploy_env import (  # noqa: E402
    PROMOTED_RAG_COLLECTION_PATTERN,
    validate_env_file,
)

MANIFEST_SCHEMA_VERSION = 1
MANIFEST_NAME = "transaction.json"
PREVIOUS_ENV_NAME = "previous.env"
PRIVATE_FILE_MODE = 0o600
PRIVATE_DIRECTORY_MODE = 0o700

EnvironmentValidator = Callable[[Path], object]


class DeployEnvironmentTransactionError(ValueError):
    """The environment transaction cannot be completed safely."""


@dataclass(frozen=True, slots=True)
class EnvironmentTransactionResult:
    state: str
    previous_collection: str
    target_collection: str


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _absolute(path: Path) -> str:
    return str(path.expanduser().absolute())


def _read_regular_file(path: Path, field: str) -> bytes:
    try:
        metadata = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            raise DeployEnvironmentTransactionError(field)
        return path.read_bytes()
    except DeployEnvironmentTransactionError:
        raise
    except OSError as exc:
        raise DeployEnvironmentTransactionError(field) from exc


def _collection_from_environment(content: bytes, field: str) -> str:
    try:
        text = content.decode("utf-8")
    except UnicodeError as exc:
        raise DeployEnvironmentTransactionError(field) from exc
    matches: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == "RAG_COLLECTION_NAME":
            matches.append(value.strip().strip('"').strip("'"))
    if (
        len(matches) != 1
        or PROMOTED_RAG_COLLECTION_PATTERN.fullmatch(matches[0]) is None
    ):
        raise DeployEnvironmentTransactionError(field)
    return matches[0]


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_atomic(path: Path, content: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
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
        _fsync_directory(path.parent)
    except OSError as exc:
        raise DeployEnvironmentTransactionError("atomic_write") from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _write_manifest(transaction_dir: Path, payload: dict[str, object]) -> None:
    content = (
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    _write_atomic(transaction_dir / MANIFEST_NAME, content, PRIVATE_FILE_MODE)


def _load_manifest(transaction_dir: Path) -> dict[str, object]:
    raw = _read_regular_file(
        transaction_dir / MANIFEST_NAME,
        "transaction_manifest",
    )
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise DeployEnvironmentTransactionError("transaction_manifest") from exc
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != MANIFEST_SCHEMA_VERSION
    ):
        raise DeployEnvironmentTransactionError("transaction_manifest")
    return payload


def _create_transaction_directory(transaction_dir: Path) -> None:
    if transaction_dir.exists() or transaction_dir.is_symlink():
        raise DeployEnvironmentTransactionError("transaction_already_exists")
    try:
        transaction_dir.parent.mkdir(
            mode=PRIVATE_DIRECTORY_MODE,
            parents=True,
            exist_ok=True,
        )
        transaction_dir.mkdir(mode=PRIVATE_DIRECTORY_MODE)
        os.chmod(transaction_dir, PRIVATE_DIRECTORY_MODE)
        _fsync_directory(transaction_dir.parent)
    except OSError as exc:
        raise DeployEnvironmentTransactionError("transaction_directory") from exc


def install_environment(
    candidate_env: Path,
    active_env: Path,
    transaction_dir: Path,
    *,
    expected_collection: str | None = None,
    validator: EnvironmentValidator = validate_env_file,
) -> EnvironmentTransactionResult:
    """Atomically install a validated complete env and retain exact rollback data."""

    candidate_path = candidate_env.expanduser().absolute()
    active_path = active_env.expanduser().absolute()
    transaction_path = transaction_dir.expanduser().absolute()
    if candidate_path == active_path:
        raise DeployEnvironmentTransactionError("candidate_must_be_private_copy")

    candidate_content = _read_regular_file(candidate_path, "candidate_environment")
    previous_content = _read_regular_file(active_path, "active_environment")
    try:
        validator(candidate_path)
    except Exception as exc:
        raise DeployEnvironmentTransactionError("candidate_environment") from exc
    target_collection = _collection_from_environment(
        candidate_content,
        "candidate.RAG_COLLECTION_NAME",
    )
    previous_collection = _collection_from_environment(
        previous_content,
        "active.RAG_COLLECTION_NAME",
    )
    if expected_collection is not None and target_collection != expected_collection:
        raise DeployEnvironmentTransactionError("expected_RAG_COLLECTION_NAME")

    _create_transaction_directory(transaction_path)
    previous_path = transaction_path / PREVIOUS_ENV_NAME
    _write_atomic(previous_path, previous_content, PRIVATE_FILE_MODE)
    manifest: dict[str, object] = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "state": "PREPARED",
        "active_env": _absolute(active_path),
        "previous_env": PREVIOUS_ENV_NAME,
        "previous_sha256": _sha256(previous_content),
        "target_sha256": _sha256(candidate_content),
        "previous_collection": previous_collection,
        "target_collection": target_collection,
        "prepared_at": _utc_timestamp(),
    }
    _write_manifest(transaction_path, manifest)

    try:
        _write_atomic(active_path, candidate_content, PRIVATE_FILE_MODE)
        validator(active_path)
        installed_content = _read_regular_file(active_path, "installed_environment")
        if _sha256(installed_content) != manifest["target_sha256"]:
            raise DeployEnvironmentTransactionError("installed_environment_digest")
        if (
            _collection_from_environment(
                installed_content,
                "installed.RAG_COLLECTION_NAME",
            )
            != target_collection
        ):
            raise DeployEnvironmentTransactionError("installed.RAG_COLLECTION_NAME")
        manifest["state"] = "INSTALLED"
        manifest["installed_at"] = _utc_timestamp()
        _write_manifest(transaction_path, manifest)
    except Exception as install_error:
        try:
            _write_atomic(active_path, previous_content, PRIVATE_FILE_MODE)
            restored_content = _read_regular_file(
                active_path,
                "automatic_rollback_environment",
            )
            if _sha256(restored_content) != manifest["previous_sha256"]:
                raise DeployEnvironmentTransactionError(
                    "automatic_rollback_environment_digest"
                )
            manifest["state"] = "AUTO_ROLLED_BACK"
            manifest["rolled_back_at"] = _utc_timestamp()
            manifest["failure"] = "install_validation_or_write"
            _write_manifest(transaction_path, manifest)
        except Exception as rollback_error:
            manifest["state"] = "ROLLBACK_FAILED"
            manifest["failure"] = "automatic_rollback_failed"
            try:
                _write_manifest(transaction_path, manifest)
            except Exception:
                pass
            raise DeployEnvironmentTransactionError(
                "automatic_rollback_failed"
            ) from rollback_error
        raise DeployEnvironmentTransactionError(
            "install_failed_automatic_rollback"
        ) from install_error

    return EnvironmentTransactionResult(
        state="INSTALLED",
        previous_collection=previous_collection,
        target_collection=target_collection,
    )


def rollback_environment(
    active_env: Path,
    transaction_dir: Path,
) -> EnvironmentTransactionResult:
    """Restore the exact prior env after verifying no newer release replaced it."""

    active_path = active_env.expanduser().absolute()
    transaction_path = transaction_dir.expanduser().absolute()
    manifest = _load_manifest(transaction_path)
    if manifest.get("active_env") != _absolute(active_path):
        raise DeployEnvironmentTransactionError("active_environment_mismatch")
    if manifest.get("previous_env") != PREVIOUS_ENV_NAME:
        raise DeployEnvironmentTransactionError("rollback_environment")

    previous_content = _read_regular_file(
        transaction_path / PREVIOUS_ENV_NAME,
        "rollback_environment",
    )
    previous_digest = str(manifest.get("previous_sha256") or "")
    target_digest = str(manifest.get("target_sha256") or "")
    if _sha256(previous_content) != previous_digest:
        raise DeployEnvironmentTransactionError("rollback_environment_digest")
    previous_collection = _collection_from_environment(
        previous_content,
        "rollback.RAG_COLLECTION_NAME",
    )
    if previous_collection != manifest.get("previous_collection"):
        raise DeployEnvironmentTransactionError("rollback.RAG_COLLECTION_NAME")

    active_content = _read_regular_file(active_path, "active_environment")
    active_digest = _sha256(active_content)
    if active_digest == previous_digest:
        manifest["state"] = "ROLLED_BACK"
        manifest["rolled_back_at"] = _utc_timestamp()
        _write_manifest(transaction_path, manifest)
        return EnvironmentTransactionResult(
            state="ROLLED_BACK",
            previous_collection=previous_collection,
            target_collection=str(manifest.get("target_collection") or ""),
        )
    if manifest.get("state") != "INSTALLED" or active_digest != target_digest:
        raise DeployEnvironmentTransactionError("active_environment_revision_changed")

    try:
        _write_atomic(active_path, previous_content, PRIVATE_FILE_MODE)
        restored_content = _read_regular_file(active_path, "restored_environment")
        if _sha256(restored_content) != previous_digest:
            raise DeployEnvironmentTransactionError("restored_environment_digest")
        if (
            _collection_from_environment(
                restored_content,
                "restored.RAG_COLLECTION_NAME",
            )
            != previous_collection
        ):
            raise DeployEnvironmentTransactionError("restored.RAG_COLLECTION_NAME")
        manifest["state"] = "ROLLED_BACK"
        manifest["rolled_back_at"] = _utc_timestamp()
        _write_manifest(transaction_path, manifest)
    except Exception as rollback_error:
        try:
            _write_atomic(active_path, active_content, PRIVATE_FILE_MODE)
        except Exception:
            raise DeployEnvironmentTransactionError(
                "rollback_failed_active_restore_failed"
            ) from rollback_error
        raise DeployEnvironmentTransactionError("rollback_failed") from rollback_error

    return EnvironmentTransactionResult(
        state="ROLLED_BACK",
        previous_collection=previous_collection,
        target_collection=str(manifest.get("target_collection") or ""),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Instala o revierte el entorno completo y su puntero RAG sin imprimir "
            "secretos."
        )
    )
    commands = parser.add_subparsers(dest="command", required=True)
    install = commands.add_parser("install", help="Instala el candidato completo.")
    install.add_argument("--candidate-env", type=Path, required=True)
    install.add_argument("--active-env", type=Path, required=True)
    install.add_argument("--transaction-dir", type=Path, required=True)
    install.add_argument("--expected-collection")
    rollback = commands.add_parser("rollback", help="Restaura el entorno anterior.")
    rollback.add_argument("--active-env", type=Path, required=True)
    rollback.add_argument("--transaction-dir", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "install":
            result = install_environment(
                args.candidate_env,
                args.active_env,
                args.transaction_dir,
                expected_collection=args.expected_collection,
            )
        else:
            result = rollback_environment(args.active_env, args.transaction_dir)
    except DeployEnvironmentTransactionError as exc:
        print(f"ERROR: transacción de entorno inválida: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "state": result.state,
                "previous_collection": result.previous_collection,
                "target_collection": result.target_collection,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
