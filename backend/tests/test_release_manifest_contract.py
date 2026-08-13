from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.release_manifest import (
    RELEASE_MANIFEST_CONTRACT_VERSION,
    ReleaseManifest,
    canonical_release_manifest,
    load_release_manifest,
    release_manifest_json_schema,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_PATH = PROJECT_ROOT / "deploy" / "releases" / "release-manifest.example.json"
SCHEMA_PATH = (
    PROJECT_ROOT / "deploy" / "releases" / "release-manifest-v1.schema.json"
)


def example_payload() -> dict[str, object]:
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


def test_versioned_release_example_is_valid_and_canonicalizable() -> None:
    manifest = load_release_manifest(EXAMPLE_PATH)

    assert manifest.schema_version == RELEASE_MANIFEST_CONTRACT_VERSION
    assert manifest.release_id == manifest.source.github_sha
    assert manifest.gpu_runtime.initial_validation_state == "pending_boot_validation"
    assert manifest.gpu_runtime.update_while_running is False
    assert json.loads(canonical_release_manifest(manifest)) == manifest.model_dump(
        mode="json"
    )


def test_every_component_must_use_the_same_github_sha() -> None:
    payload = example_payload()
    payload["gpu_runtime"]["revision"] = "f" * 40  # type: ignore[index]

    with pytest.raises(ValidationError, match="source.github_sha"):
        ReleaseManifest.model_validate(payload)


def test_image_reference_and_declared_digest_cannot_diverge() -> None:
    payload = example_payload()
    payload["application"]["backend"]["digest"] = (  # type: ignore[index]
        "sha256:" + "9" * 64
    )

    with pytest.raises(ValidationError, match="same blob"):
        ReleaseManifest.model_validate(payload)


def test_release_rejects_latest_model_and_unqualified_model_name() -> None:
    for model_name in ("qwen3:latest", "qwen3"):
        payload = deepcopy(example_payload())
        payload["gpu_runtime"]["model"]["name"] = model_name  # type: ignore[index]
        with pytest.raises(ValidationError, match="non-latest"):
            ReleaseManifest.model_validate(payload)


def test_release_timestamp_requires_explicit_timezone() -> None:
    payload = example_payload()
    payload["source"]["created_at"] = "2026-08-02T12:00:00"  # type: ignore[index]

    with pytest.raises(ValidationError, match="timezone"):
        ReleaseManifest.model_validate(payload)


def test_generated_json_schema_is_closed_and_versioned() -> None:
    schema = release_manifest_json_schema()

    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RELEASE_MANIFEST_CONTRACT_VERSION
    )
    assert set(schema["required"]) == {
        "schema_version",
        "release_id",
        "source",
        "application",
        "gpu_runtime",
        "rag",
        "contracts",
    }
    assert json.loads(SCHEMA_PATH.read_text(encoding="utf-8")) == schema
