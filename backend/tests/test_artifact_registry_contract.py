from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.artifact_registry_contract import (
    ARTIFACT_SET_CONTRACT_VERSION,
    ArtifactSet,
    bind_release_artifacts,
)
from app.core.release_manifest import ReleaseManifest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESOURCE_CONTRACT_PATH = (
    PROJECT_ROOT / "deploy" / "gcp" / "stage3-resource-contract.json"
)
CLEANUP_POLICY_PATH = (
    PROJECT_ROOT / "deploy" / "gcp" / "artifact-registry-cleanup-policy.json"
)
RELEASE_EXAMPLE_PATH = (
    PROJECT_ROOT / "deploy" / "releases" / "release-manifest.example.json"
)
SHA = "0123456789abcdef0123456789abcdef01234567"
REGISTRY = (
    "us-central1-docker.pkg.dev/"
    "project-5b36701c-f44f-4c03-a12/hemovet-images"
)


def artifact_payload() -> dict[str, object]:
    images = []
    for index, package in enumerate(("backend", "frontend", "ollama-runtime"), 1):
        digest = f"sha256:{str(index) * 64}"
        images.append(
            {
                "package": package,
                "source_revision": SHA,
                "tag": f"sha-{SHA}",
                "tagged_reference": f"{REGISTRY}/{package}:sha-{SHA}",
                "canonical_reference": f"{REGISTRY}/{package}@{digest}",
                "digest": digest,
                "upstream_reference": (
                    "docker.io/ollama/ollama:0.30.10@sha256:" + "a" * 64
                    if package == "ollama-runtime"
                    else None
                ),
            }
        )
    return {
        "schema_version": ARTIFACT_SET_CONTRACT_VERSION,
        "release_id": SHA,
        "source": {
            "github_sha": SHA,
            "repository": "xPshycho/hemogramas-proyectoICC",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        "registry_repository": REGISTRY,
        "images": images,
    }


def test_artifact_set_accepts_one_digest_pinned_image_per_runtime() -> None:
    artifact_set = ArtifactSet.model_validate(artifact_payload())

    assert artifact_set.release_id == SHA
    assert {image.package for image in artifact_set.images} == {
        "backend",
        "frontend",
        "ollama-runtime",
    }
    assert all(image.tag == f"sha-{SHA}" for image in artifact_set.images)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("latest", "latest"),
        ("digest_mismatch", "digest"),
        ("revision_mismatch", "source.github_sha"),
        ("duplicate_package", "once"),
    ],
)
def test_artifact_set_fails_closed_on_mutable_or_divergent_input(
    mutation: str,
    message: str,
) -> None:
    payload = artifact_payload()
    images = payload["images"]
    assert isinstance(images, list)
    if mutation == "latest":
        images[0]["tagged_reference"] = f"{REGISTRY}/backend:latest"
    elif mutation == "digest_mismatch":
        images[0]["digest"] = "sha256:" + "9" * 64
    elif mutation == "revision_mismatch":
        images[0]["source_revision"] = "f" * 40
    else:
        images[2]["package"] = "frontend"

    with pytest.raises(ValidationError, match=message):
        ArtifactSet.model_validate(payload)


def test_real_artifact_digests_can_be_bound_to_release_v1() -> None:
    artifact_set = ArtifactSet.model_validate(artifact_payload())
    release_payload = json.loads(RELEASE_EXAMPLE_PATH.read_text(encoding="utf-8"))
    release = ReleaseManifest.model_validate(release_payload)

    bound = bind_release_artifacts(release, artifact_set)

    assert bound.application.backend.reference == artifact_set.image(
        "backend"
    ).canonical_reference
    assert bound.application.frontend.digest == artifact_set.image(
        "frontend"
    ).digest
    assert bound.gpu_runtime.runtime.reference == artifact_set.image(
        "ollama-runtime"
    ).canonical_reference


def test_release_binding_rejects_a_different_source_revision() -> None:
    payload = artifact_payload()
    payload["release_id"] = "f" * 40
    payload["source"]["github_sha"] = "f" * 40
    for image in payload["images"]:
        image["source_revision"] = "f" * 40
        image["tag"] = "sha-" + "f" * 40
        image["tagged_reference"] = image["tagged_reference"].replace(
            f"sha-{SHA}", "sha-" + "f" * 40
        )
    artifact_set = ArtifactSet.model_validate(payload)
    release = ReleaseManifest.model_validate_json(
        RELEASE_EXAMPLE_PATH.read_text(encoding="utf-8")
    )

    with pytest.raises(ValueError, match="different revisions"):
        bind_release_artifacts(release, artifact_set)


def test_stage3_resource_contract_enforces_least_privilege_and_fail_closed_wif() -> None:
    contract = json.loads(RESOURCE_CONTRACT_PATH.read_text(encoding="utf-8"))

    assert contract["schema_version"] == "hemovet.gcp-artifacts/v1"
    assert contract["repository"]["immutable_tags"] is True
    assert contract["repository"]["deployment_reference"] == "digest"
    assert contract["repository"]["cleanup_dry_run"] is True
    assert set(contract["repository"]["packages"]) == {
        "backend",
        "frontend",
        "ollama-runtime",
    }

    accounts = set(contract["service_accounts"].values())
    assert len(accounts) == 3
    assert all("-compute@developer.gserviceaccount.com" not in item for item in accounts)

    bindings = contract["repository_iam"]
    assert {item["role"] for item in bindings} == {
        "roles/artifactregistry.reader",
        "roles/artifactregistry.writer",
    }
    assert sum(item["role"] == "roles/artifactregistry.writer" for item in bindings) == 1
    forbidden_roles = {"roles/owner", "roles/editor", "roles/artifactregistry.admin"}
    assert not ({item["role"] for item in bindings} & forbidden_roles)

    wif = contract["workload_identity"]
    condition = wif["attribute_condition"]
    for boundary in (
        'assertion.repository == "xPshycho/hemogramas-proyectoICC"',
        'assertion.repository_id == "1148021152"',
        'assertion.repository_owner == "xPshycho"',
        'assertion.repository_owner_id == "115911218"',
        'assertion.ref == "refs/heads/main"',
        'assertion.workflow_ref == "xPshycho/hemogramas-proyectoICC/.github/workflows/deploy.yml@refs/heads/main"',
        'assertion.environment == "production"',
    ):
        assert boundary in condition
    assert wif["impersonation_role"] == "roles/iam.workloadIdentityUser"
    assert wif["principal_set"].endswith(
        "/attribute.repository/xPshycho/hemogramas-proyectoICC"
    )


def test_cleanup_policy_cannot_delete_tagged_or_recent_artifacts() -> None:
    policies = json.loads(CLEANUP_POLICY_PATH.read_text(encoding="utf-8"))
    delete_policies = [item for item in policies if item["action"]["type"] == "Delete"]
    keep_policies = [item for item in policies if item["action"]["type"] == "Keep"]

    assert delete_policies == [
        {
            "name": "delete-untagged-after-30-days",
            "action": {"type": "Delete"},
            "condition": {"tagState": "untagged", "olderThan": "30d"},
        }
    ]
    assert keep_policies[0]["mostRecentVersions"]["keepCount"] >= 20
