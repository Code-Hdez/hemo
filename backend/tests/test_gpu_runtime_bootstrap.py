from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
from types import ModuleType

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
GPU_DIR = PROJECT_ROOT / "deploy" / "gpu"
COMPOSE_PATH = PROJECT_ROOT / "docker-compose.gpu.yml"
RUNTIME_CONTRACT_PATH = GPU_DIR / "runtime_contract.py"
SHA = "515d343ac805779f94be9277376bdadf5516154d"
RUNTIME_DIGEST = (
    "sha256:b526b1d4bc30d0cc641e0d2a186034b327c97de0171b1a47ce1c917d79604e5f"
)


def _load_contract() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "gpu_runtime_contract", RUNTIME_CONTRACT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _manifest(bundle_digest: str = "sha256:" + "a" * 64) -> dict[str, object]:
    return {
        "schema_version": "hemovet.gpu-runtime-release/v1",
        "source_contract": "hemovet.release/v1",
        "release_id": SHA,
        "revision_state": "pending_boot_validation",
        "apply_on": "next_boot",
        "update_while_running": False,
        "runtime": {
            "reference": (
                "us-central1-docker.pkg.dev/"
                "project-5b36701c-f44f-4c03-a12/hemovet-images/"
                f"ollama-runtime@{RUNTIME_DIGEST}"
            ),
            "digest": RUNTIME_DIGEST,
        },
        "startup": {
            "contract_version": "hemovet.gpu-startup/v1",
            "bundle_digest": bundle_digest,
        },
        "model": {
            "name": "qwen3.6:27b-q4_K_M",
            "digest": (
                "sha256:a50eda8ed977ab48a12431878896b27f"
                "fd5cef552c17af3317d9623b939a7f1e"
            ),
            "quantization": "Q4_K_M",
        },
    }


def test_gpu_runtime_projection_is_closed_and_renders_private_compose_env(
    tmp_path: Path,
) -> None:
    contract = _load_contract()
    manifest = _manifest()

    validated = contract.validate_manifest(manifest)
    rendered = contract.render_compose_environment(validated, bind_address="10.128.0.3")

    assert "HEMOVET_GPU_RELEASE_ID=" + SHA in rendered
    assert "ollama-runtime@sha256:" in rendered
    assert "OLLAMA_BIND_ADDRESS=10.128.0.3" in rendered
    assert "latest" not in rendered
    output = tmp_path / "compose.env"
    contract.atomic_write(output, rendered)
    assert stat.S_IMODE(output.stat().st_mode) == 0o600


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("state", "pending_boot_validation"),
        ("hot_update", "while running"),
        ("mutable_image", "authorized package"),
        ("digest", "digest mismatch"),
        ("model", "not approved"),
        ("quantization", "not approved"),
        ("extra", "fields differ"),
    ],
)
def test_gpu_runtime_projection_fails_closed(mutation: str, message: str) -> None:
    contract = _load_contract()
    payload = deepcopy(_manifest())
    if mutation == "state":
        payload["revision_state"] = "validated"
    elif mutation == "hot_update":
        payload["update_while_running"] = True
    elif mutation == "mutable_image":
        payload["runtime"]["reference"] = "ollama:latest"  # type: ignore[index]
    elif mutation == "digest":
        payload["runtime"]["digest"] = "sha256:" + "9" * 64  # type: ignore[index]
    elif mutation == "model":
        payload["model"]["name"] = "qwen3:latest"  # type: ignore[index]
    elif mutation == "quantization":
        payload["model"]["quantization"] = "Q8_0"  # type: ignore[index]
    else:
        payload["unexpected"] = True

    with pytest.raises(contract.RuntimeContractError, match=message):
        contract.validate_manifest(payload)


def test_historical_release_projects_to_current_bundle_without_mutation() -> None:
    contract = _load_contract()
    historical_digest = "sha256:" + "1" * 64
    current_digest = "sha256:" + "2" * 64
    historical = _manifest(historical_digest)

    projected = contract.project_manifest_to_bundle(
        historical, current_bundle_digest=current_digest
    )

    assert historical["startup"]["bundle_digest"] == historical_digest  # type: ignore[index]
    assert projected["startup"]["bundle_digest"] == current_digest
    assert projected["release_id"] == historical["release_id"]
    assert projected["runtime"] == historical["runtime"]
    assert projected["model"] == historical["model"]


def test_historical_manifest_accepts_a_pre_upgrade_model_as_evidence() -> None:
    contract = _load_contract()
    historical = _manifest()
    historical["model"] = {
        "name": "qwen3:4b-q4_K_M",
        "digest": "sha256:" + "7" * 64,
        "quantization": "Q4_K_M",
    }

    validated = contract.validate_historical_manifest(historical)

    assert contract._field(validated, "release_id") == SHA
    with pytest.raises(contract.RuntimeContractError, match="model name is not approved"):
        contract.validate_manifest(historical)


def test_boot_validation_warms_the_full_context_without_expiring() -> None:
    validation = (GPU_DIR / "validate-runtime.sh").read_text(encoding="utf-8")

    assert 'keep_alive:-1' in validation
    assert 'num_ctx:$num_ctx' in validation
    assert '--max-time 420' in validation
    assert 'keep_alive:"30m"' not in validation


def test_host_validation_rejects_uncorrectable_gpu_ecc() -> None:
    validation = (GPU_DIR / "validate-host.sh").read_text(encoding="utf-8")

    assert "ecc.errors.uncorrected.volatile.total" in validation
    assert "ecc.errors.uncorrected.aggregate.total" in validation
    assert "uncorrectable ECC errors" in validation


def test_bundle_manifest_covers_operational_files_and_matches_bytes() -> None:
    bundle_manifest = GPU_DIR / "bundle-manifest.sha256"
    covered: set[str] = set()
    for line in bundle_manifest.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        path = PROJECT_ROOT / relative
        assert path.is_file(), relative
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, relative
        covered.add(relative)

    assert "docker-compose.gpu.yml" in covered
    assert "deploy/gpu/reconcile-release.sh" in covered
    assert "deploy/gpu/rollback-release.sh" in covered
    assert "deploy/gpu/hemovet-gpu.service" in covered
    assert "deploy/gpu/hemovet-gpu-failure-shutdown.service" in covered
    assert "deploy/gpu/shutdown-on-failure.sh" in covered
    assert "deploy/gpu/README.md" in covered


def test_reconciler_uses_lock_ephemeral_identity_and_no_hot_update() -> None:
    reconcile = (GPU_DIR / "reconcile-release.sh").read_text(encoding="utf-8")
    authentication = (GPU_DIR / "authenticate-artifact-registry.sh").read_text(
        encoding="utf-8"
    )
    startup = (GPU_DIR / "startup.sh").read_text(encoding="utf-8")
    contract = (GPU_DIR / "runtime_contract.py").read_text(encoding="utf-8")

    assert "flock --nonblock" in reconcile
    assert "pending_boot_validation" in contract
    assert "release=deferred" in reconcile
    assert "runtime_running" in reconcile
    assert "--boot" in startup
    assert "reconciler-boot-id" in startup
    assert "historical-field" in reconcile
    assert 'validation_action="boot_inference"' in reconcile
    assert "validation_arguments+=(--run-inference)" in reconcile
    assert "existing Ollama health deadline exceeded" in reconcile
    assert "Metadata-Flavor: Google" in authentication
    assert "service-accounts/default/token" in authentication
    assert "/run/hemovet-gpu/docker-config" in authentication
    combined = reconcile + authentication + startup
    assert "git pull" not in combined
    assert ":latest" not in combined
    assert "set -x" not in combined
    assert "service-account.json" not in combined


def test_rollback_rebinds_historical_release_to_installed_bundle() -> None:
    rollback = (GPU_DIR / "rollback-release.sh").read_text(encoding="utf-8")

    assert "project-bundle" in rollback
    assert "--bundle-manifest" in rollback
    assert "target_release=" in rollback


def test_installer_creates_systemd_write_paths_before_enabling_service() -> None:
    installer = (GPU_DIR / "install-bootstrap.sh").read_text(encoding="utf-8")
    unit = (GPU_DIR / "hemovet-gpu.service").read_text(encoding="utf-8")

    create_cdi = installer.index("install -d -m 0755 /etc/cdi")
    enable_service = installer.index("systemctl enable hemovet-gpu.service")
    assert create_cdi < enable_service
    assert "ReadWritePaths=" in unit
    assert "/etc/cdi" in unit


def test_failed_bootstrap_records_evidence_and_powers_off() -> None:
    installer = (GPU_DIR / "install-bootstrap.sh").read_text(encoding="utf-8")
    unit = (GPU_DIR / "hemovet-gpu.service").read_text(encoding="utf-8")
    failure_unit = (GPU_DIR / "hemovet-gpu-failure-shutdown.service").read_text(
        encoding="utf-8"
    )
    shutdown = (GPU_DIR / "shutdown-on-failure.sh").read_text(encoding="utf-8")

    assert "OnFailure=hemovet-gpu-failure-shutdown.service" in unit
    assert "hemovet-gpu-failure-shutdown.service" in installer
    assert "shutdown-on-failure.sh hemovet-gpu.service" in failure_unit
    assert "bootstrap-failure.json" in shutdown
    assert "hemovet.gpu-bootstrap-failure/v1" in shutdown
    assert "shutdown_requested" in shutdown
    assert "systemctl --no-block poweroff" in shutdown
    assert "gcloud" not in shutdown
    assert "set -x" not in shutdown


def test_nvidia_cdi_generation_is_hidden_until_atomic_install() -> None:
    configuration = (GPU_DIR / "configure-nvidia-runtime.sh").read_text(
        encoding="utf-8"
    )

    assert "mktemp /run/hemovet-gpu/nvidia-cdi.XXXXXX" in configuration
    assert "mktemp /etc/cdi/.hemovet-nvidia.XXXXXX.tmp" in configuration
    assert 'nvidia-ctk cdi generate >"$temporary_cdi"' in configuration
    assert '--output="$temporary_cdi"' not in configuration
    assert 'mv -f "$staged_cdi" /etc/cdi/nvidia.yaml' in configuration
    assert "/etc/cdi/.nvidia.yaml.*.yaml" in configuration


def test_gpu_compose_requires_nvidia_and_never_pulls_implicitly() -> None:
    compose = COMPOSE_PATH.read_text(encoding="utf-8")
    assert "runtime: nvidia" in compose
    assert compose.count("pull_policy: never") == 2
    assert "com.hemovet.release" in compose
    rendered_example = (GPU_DIR / "compose.env.example").read_text(encoding="utf-8")
    assert "HEMOVET_GPU_RELEASE_ID=" + SHA in rendered_example
    assert "HEMOVET_GPU_RUNTIME_DIGEST=" + RUNTIME_DIGEST in rendered_example


def test_runtime_schema_matches_approved_model_and_pending_state() -> None:
    schema = json.loads(
        (GPU_DIR / "gpu-runtime-release-v1.schema.json").read_text(encoding="utf-8")
    )
    assert schema["additionalProperties"] is False
    properties = schema["properties"]
    assert properties["revision_state"]["const"] == "pending_boot_validation"
    assert properties["update_while_running"]["const"] is False
    assert properties["model"]["properties"]["quantization"]["const"] == "Q4_K_M"


def test_versioned_gpu_releases_match_installed_bundle_and_immutable_images() -> None:
    contract = _load_contract()
    bundle_manifest = GPU_DIR / "bundle-manifest.sha256"
    expected_bundle = contract.bundle_digest(bundle_manifest)
    release_paths = sorted(
        (PROJECT_ROOT / "deploy" / "releases").glob("gpu-runtime-*.json")
    )

    assert len(release_paths) >= 2
    releases = [
        contract.validate_manifest(
            contract.load_manifest(path),
            expected_bundle_digest=expected_bundle,
        )
        for path in release_paths
    ]
    release_ids = {release["release_id"] for release in releases}
    assert len(release_ids) == len(release_paths)
    assert {
        "6e2969d6fa735473097d4f1c19af46263436bd66",
        SHA,
        "af5ab60b418bc931c4c4cabc8b8ef92893325fb6",
    } <= release_ids
    assert all("@sha256:" in release["runtime"]["reference"] for release in releases)
