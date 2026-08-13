from __future__ import annotations

import json
from pathlib import Path

from app.core.artifact_registry_contract import load_artifact_set
from app.core.release_manifest import load_release_manifest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RELEASES = PROJECT_ROOT / "deploy" / "releases"
EVIDENCE = (
    PROJECT_ROOT
    / "docs"
    / "implementation"
    / "prod-gpu-migration"
    / "evidence"
)
FINAL_SHA = "e7713a72369bb9365f6d5323e165fbf84488bfb4"
ROLLBACK_SHA = "af5ab60b418bc931c4c4cabc8b8ef92893325fb6"


def test_stage10_final_release_is_one_digest_pinned_revision() -> None:
    artifacts = load_artifact_set(
        RELEASES / f"artifact-set-{FINAL_SHA}.json"
    )
    release = load_release_manifest(
        RELEASES / f"release-manifest-{FINAL_SHA}.json"
    )

    assert artifacts.release_id == FINAL_SHA
    assert release.release_id == FINAL_SHA
    assert release.source.github_sha == FINAL_SHA
    assert release.application.revision == FINAL_SHA
    assert release.gpu_runtime.revision == FINAL_SHA
    expected = {
        "backend": release.application.backend.digest,
        "frontend": release.application.frontend.digest,
        "ollama-runtime": release.gpu_runtime.runtime.digest,
    }
    for package, digest in expected.items():
        image = artifacts.image(package)
        assert image.source_revision == FINAL_SHA
        assert image.digest == digest
        assert image.canonical_reference.endswith(f"@{digest}")
        assert "latest" not in image.canonical_reference


def test_stage10_rollback_plan_matches_complete_previous_release() -> None:
    previous = load_release_manifest(
        RELEASES / f"release-manifest-{ROLLBACK_SHA}.json"
    )
    plan = json.loads(
        (RELEASES / f"rollback-plan-{ROLLBACK_SHA}.json").read_text(
            encoding="utf-8"
        )
    )

    assert plan == {
        "schema_version": "hemovet.rollback-plan/v1",
        "release_id": ROLLBACK_SHA,
        "backend_digest": previous.application.backend.digest,
        "frontend_digest": previous.application.frontend.digest,
        "gpu_runtime_digest": previous.gpu_runtime.runtime.digest,
        "model_digest": previous.gpu_runtime.model.digest,
        "rag_collection": previous.rag.collection_name,
        "rag_fingerprint": previous.rag.index_fingerprint,
        "gpu_revision_state": previous.gpu_runtime.initial_validation_state,
        "gpu_apply_on": previous.gpu_runtime.apply_on,
    }


def test_stage10_rag_evidence_contains_no_ephemeral_runner_path() -> None:
    summary = json.loads(
        (RELEASES / f"rag-summary-{FINAL_SHA}.json").read_text(
            encoding="utf-8"
        )
    )

    assert summary["source_dir"] == "knowledge_base/expert_review/approved"
    assert summary["chunks"] == 4696
    assert summary["quarantined_sources"] == 0
    assert not str(summary["source_dir"]).startswith("/")


def test_stage10_acceptance_evidence_is_complete_and_sanitized() -> None:
    report = json.loads(
        (
            EVIDENCE
            / f"acceptance-report-{FINAL_SHA}.json"
        ).read_text(encoding="utf-8")
    )
    expected_cases = {
        "frontend_and_api_proxy_available",
        "registration_login_and_authentication",
        "pets_and_cross_user_authorization",
        "hemograms_history_and_user_isolation",
        "core_degraded_with_provider_off",
        "provider_timeout_does_not_block_core",
        "automatic_provider_recovery_without_backend_restart",
        "general_chat_with_readable_rag_sources",
        "selected_hemogram_uses_exact_values",
        "follow_up_memory_and_persisted_turns",
        "historical_chat_uses_patient_analyses",
        "direct_diagnosis_is_refused",
        "medication_and_dose_are_refused",
        "out_of_scope_question_is_refused",
        "browser_session_and_user_isolation",
        "streaming_sse_contract",
        "data_and_conversations_survive_backend_restart",
        "history_available_with_gpu_off",
        "provider_off_after_history_keeps_core_available",
    }
    cases = {case["name"]: case for case in report["cases"]}

    assert report["schema_version"] == "hemovet.stage10-acceptance/v1"
    assert report["release_id"] == FINAL_SHA
    assert report["summary"] == {"failed": 0, "passed": 19}
    assert set(cases) == expected_cases
    assert all(case["status"] == "PASS" for case in cases.values())
    assert cases["core_degraded_with_provider_off"]["evidence"][
        "core_ready"
    ]
    assert not cases["core_degraded_with_provider_off"]["evidence"][
        "chat_ready"
    ]
    assert cases["selected_hemogram_uses_exact_values"]["evidence"][
        "wbc_value"
    ] == 18.4
    assert cases["historical_chat_uses_patient_analyses"]["evidence"][
        "wbc_values"
    ] == [9.2, 18.4]

    forbidden = {
        "access_token",
        "answer",
        "authorization",
        "email",
        "password",
        "prompt",
        "refresh_token",
        "token",
    }

    def object_keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value).union(
                *(
                    object_keys(child)
                    for child in value.values()
                ),
                set(),
            )
        if isinstance(value, list):
            return set().union(
                *(object_keys(child) for child in value),
                set(),
            )
        return set()

    assert object_keys(report).isdisjoint(forbidden)


def test_stage10_gpu_evidence_proves_full_l4_residency() -> None:
    metrics = json.loads(
        (EVIDENCE / f"gpu-metrics-{FINAL_SHA}.json").read_text(
            encoding="utf-8"
        )
    )

    assert metrics["release_id"] == FINAL_SHA
    assert metrics["runtime_reference"].endswith(
        "@sha256:"
        "aed77e3c668587c12ac32751d484d1a287e2853b3ffb56760fe8222a5fd3cd0c"
    )
    assert metrics["model_digest"] == (
        "sha256:"
        "0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0"
    )
    assert metrics["quantization"] == "Q4_K_M"
    assert metrics["gpu_active"] is True
    assert metrics["inference_device"] == "full_gpu"
    assert metrics["model_vram_bytes"] == metrics["model_size_bytes"]
    assert metrics["peak_gpu_utilization_percent"] > 0
