#!/usr/bin/env python3
"""Validate the fail-closed GPU projection of ``hemovet.release/v1``.

The VM deliberately has no application configuration. It consumes only the
fields needed to select an immutable runtime, startup bundle and approved
model. The full application and RAG release remains on production.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any


CONTRACT_VERSION = "hemovet.gpu-runtime-release/v1"
SOURCE_CONTRACT_VERSION = "hemovet.release/v1"
STARTUP_CONTRACT_VERSION = "hemovet.gpu-startup/v1"
REGISTRY_IMAGE_PREFIX = (
    "us-central1-docker.pkg.dev/"
    "project-5b36701c-f44f-4c03-a12/hemovet-images/ollama-runtime"
)
APPROVED_MODEL = "qwen3.6:27b-q4_K_M"
APPROVED_MODEL_DIGEST = (
    "sha256:a50eda8ed977ab48a12431878896b27ffd5cef552c17af3317d9623b939a7f1e"
)
APPROVED_QUANTIZATION = "Q4_K_M"

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_REFERENCE_RE = re.compile(
    rf"^{re.escape(REGISTRY_IMAGE_PREFIX)}@sha256:[0-9a-f]{{64}}$"
)


class RuntimeContractError(ValueError):
    """A desired GPU release violates the closed runtime contract."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeContractError(message)


def _require_object(value: object, name: str) -> dict[str, Any]:
    _require(isinstance(value, dict), f"{name} must be an object")
    return value  # type: ignore[return-value]


def _require_keys(value: dict[str, Any], expected: set[str], name: str) -> None:
    actual = set(value)
    _require(
        actual == expected,
        f"{name} fields differ; expected={sorted(expected)} actual={sorted(actual)}",
    )


def bundle_digest(path: str | Path) -> str:
    content = Path(path).read_bytes()
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def load_manifest(path: str | Path) -> dict[str, Any]:
    manifest_path = Path(path)
    _require(manifest_path.is_file(), "desired release manifest is missing")
    _require(manifest_path.stat().st_size <= 64 * 1024, "manifest exceeds 64 KiB")
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeContractError(
            "desired release manifest is not valid JSON"
        ) from exc
    return _require_object(payload, "manifest")


def validate_historical_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate immutable release evidence without applying today's allowlist.

    An applied manifest can legitimately describe the model approved by an
    older bundle.  The reconciler only reads its release id to locate the
    previous release directory; requiring the *current* approved model here
    prevents model upgrades from ever reconciling on the next boot.

    Historical evidence remains closed to the same schema, registry, digest,
    and state invariants.  Only the current model identity allowlist and the
    installed startup-bundle binding are intentionally deferred to the path
    that validates the new desired release.
    """
    _require_keys(
        payload,
        {
            "schema_version",
            "source_contract",
            "release_id",
            "revision_state",
            "apply_on",
            "update_while_running",
            "runtime",
            "startup",
            "model",
        },
        "manifest",
    )
    _require(payload["schema_version"] == CONTRACT_VERSION, "unsupported schema")
    _require(
        payload["source_contract"] == SOURCE_CONTRACT_VERSION,
        "unsupported source release contract",
    )
    release_id = payload["release_id"]
    _require(
        isinstance(release_id, str) and _SHA_RE.fullmatch(release_id) is not None,
        "release_id must be a full Git SHA",
    )
    _require(
        payload["revision_state"] == "pending_boot_validation",
        "only pending_boot_validation may be applied",
    )
    _require(payload["apply_on"] == "next_boot", "GPU releases apply on next_boot")
    _require(
        payload["update_while_running"] is False,
        "runtime updates while running are forbidden",
    )

    runtime = _require_object(payload["runtime"], "runtime")
    _require_keys(runtime, {"reference", "digest"}, "runtime")
    reference = runtime["reference"]
    digest = runtime["digest"]
    _require(
        isinstance(reference, str) and _REFERENCE_RE.fullmatch(reference) is not None,
        "runtime reference must use the authorized package and @sha256",
    )
    _require(
        isinstance(digest, str) and _DIGEST_RE.fullmatch(digest) is not None,
        "runtime digest must be sha256",
    )
    _require(reference.rsplit("@", 1)[-1] == digest, "runtime digest mismatch")

    startup = _require_object(payload["startup"], "startup")
    _require_keys(startup, {"contract_version", "bundle_digest"}, "startup")
    _require(
        startup["contract_version"] == STARTUP_CONTRACT_VERSION,
        "unsupported startup contract",
    )
    startup_digest = startup["bundle_digest"]
    _require(
        isinstance(startup_digest, str)
        and _DIGEST_RE.fullmatch(startup_digest) is not None,
        "startup bundle digest must be sha256",
    )

    model = _require_object(payload["model"], "model")
    _require_keys(model, {"name", "digest", "quantization"}, "model")
    _require(
        isinstance(model["name"], str) and bool(model["name"].strip()),
        "historical model name must be non-empty",
    )
    _require(
        isinstance(model["digest"], str)
        and _DIGEST_RE.fullmatch(model["digest"]) is not None,
        "historical model digest must be sha256",
    )
    _require(
        isinstance(model["quantization"], str)
        and bool(model["quantization"].strip()),
        "historical model quantization must be non-empty",
    )
    return payload


def validate_manifest(
    payload: dict[str, Any],
    *,
    expected_bundle_digest: str | None = None,
) -> dict[str, Any]:
    validated = validate_historical_manifest(payload)
    startup_digest = validated["startup"]["bundle_digest"]
    if expected_bundle_digest is not None:
        _require(
            startup_digest == expected_bundle_digest,
            "desired startup bundle differs from the installed bundle",
        )

    model = validated["model"]
    _require(model["name"] == APPROVED_MODEL, "model name is not approved")
    _require(model["digest"] == APPROVED_MODEL_DIGEST, "model digest is not approved")
    _require(
        model["quantization"] == APPROVED_QUANTIZATION,
        "model quantization is not approved",
    )
    return payload


def project_manifest_to_bundle(
    payload: dict[str, Any], *, current_bundle_digest: str
) -> dict[str, Any]:
    """Create a current-bundle projection of a validated historical release.

    Applied and previous manifests remain immutable evidence of the bundle that
    originally executed them. A rollback may reuse their runtime and model only
    after producing a new projection bound to the currently installed startup
    bundle and validating that projection through the normal closed contract.
    """

    validated = validate_manifest(payload)
    _require(
        _DIGEST_RE.fullmatch(current_bundle_digest) is not None,
        "current startup bundle digest must be sha256",
    )
    projected = deepcopy(validated)
    projected["startup"]["bundle_digest"] = current_bundle_digest
    return validate_manifest(
        projected, expected_bundle_digest=current_bundle_digest
    )


def _private_bind_address(raw: str) -> str:
    try:
        address = ipaddress.ip_address(raw)
    except ValueError as exc:
        raise RuntimeContractError("bind address must be an IP literal") from exc
    _require(address.version == 4, "GPU bind address must be IPv4")
    _require(address.is_private, "GPU bind address must be private")
    _require(not address.is_loopback, "GPU bind address may not be loopback")
    _require(not address.is_link_local, "GPU bind address may not be link-local")
    _require(not address.is_unspecified, "GPU bind address may not be wildcard")
    return str(address)


def render_compose_environment(
    payload: dict[str, Any],
    *,
    bind_address: str,
) -> str:
    validated = validate_manifest(payload)
    runtime = validated["runtime"]
    model = validated["model"]
    values = {
        "HEMOVET_OLLAMA_RUNTIME_IMAGE": runtime["reference"],
        "HEMOVET_GPU_RELEASE_ID": validated["release_id"],
        "HEMOVET_GPU_RUNTIME_DIGEST": runtime["digest"],
        "OLLAMA_BIND_ADDRESS": _private_bind_address(bind_address),
        "OLLAMA_MODEL": model["name"],
        "OLLAMA_EXPECTED_MODEL_DIGEST": model["digest"].removeprefix("sha256:"),
        "OLLAMA_EXPECTED_QUANTIZATION": model["quantization"],
        "OLLAMA_AUTO_PULL": "1",
        "OLLAMA_KEEP_ALIVE": "-1",
        "OLLAMA_CONTEXT_LENGTH": "65536",
        "OLLAMA_NUM_PARALLEL": "1",
        "OLLAMA_MAX_LOADED_MODELS": "1",
        "OLLAMA_MAX_QUEUE": "32",
        "OLLAMA_FLASH_ATTENTION": "1",
        "OLLAMA_KV_CACHE_TYPE": "q8_0",
        "NVIDIA_VISIBLE_DEVICES": "all",
        "NVIDIA_DRIVER_CAPABILITIES": "compute,utility",
    }
    return "".join(f"{key}={value}\n" for key, value in values.items())


def atomic_write(path: str | Path, content: str, *, mode: int = 0o600) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        directory_descriptor = os.open(destination.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        if temporary.exists():
            temporary.unlink()


def _field(payload: dict[str, Any], name: str) -> str:
    fields = {
        "release_id": payload["release_id"],
        "runtime.reference": payload["runtime"]["reference"],
        "runtime.digest": payload["runtime"]["digest"],
        "startup.bundle_digest": payload["startup"]["bundle_digest"],
        "model.name": payload["model"]["name"],
        "model.digest": payload["model"]["digest"],
        "model.quantization": payload["model"]["quantization"],
    }
    return str(fields[name])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "field"):
        child = subparsers.add_parser(command)
        child.add_argument("--manifest", required=True, type=Path)
        child.add_argument("--bundle-manifest", required=True, type=Path)
        if command == "field":
            child.add_argument(
                "--name",
                required=True,
                choices=(
                    "release_id",
                    "runtime.reference",
                    "runtime.digest",
                    "startup.bundle_digest",
                    "model.name",
                    "model.digest",
                    "model.quantization",
                ),
            )
    historical = subparsers.add_parser("historical-field")
    historical.add_argument("--manifest", required=True, type=Path)
    historical.add_argument(
        "--name",
        required=True,
        choices=(
            "release_id",
            "runtime.reference",
            "runtime.digest",
            "startup.bundle_digest",
            "model.name",
            "model.digest",
            "model.quantization",
        ),
    )
    project = subparsers.add_parser("project-bundle")
    project.add_argument("--manifest", required=True, type=Path)
    project.add_argument("--bundle-manifest", required=True, type=Path)
    project.add_argument("--output", required=True, type=Path)
    render = subparsers.add_parser("render-env")
    render.add_argument("--manifest", required=True, type=Path)
    render.add_argument("--bundle-manifest", required=True, type=Path)
    render.add_argument("--bind-address", required=True)
    render.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "historical-field":
        payload = validate_historical_manifest(load_manifest(args.manifest))
        print(_field(payload, args.name))
        return 0

    expected = bundle_digest(args.bundle_manifest)
    if args.command == "project-bundle":
        payload = project_manifest_to_bundle(
            load_manifest(args.manifest), current_bundle_digest=expected
        )
        atomic_write(args.output, json.dumps(payload, indent=2) + "\n")
        print(f"projected {payload['release_id']} to {expected}")
        return 0


    payload = validate_manifest(
        load_manifest(args.manifest), expected_bundle_digest=expected
    )
    if args.command == "validate":
        print(f"valid {CONTRACT_VERSION}: {payload['release_id']}")
    elif args.command == "field":
        print(_field(payload, args.name))
    else:
        rendered = render_compose_environment(payload, bind_address=args.bind_address)
        atomic_write(args.output, rendered)
        print(f"rendered compose environment for {payload['release_id']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeContractError as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
