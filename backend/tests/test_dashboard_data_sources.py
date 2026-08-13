from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime
from pathlib import Path

from pydantic import TypeAdapter

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.auth import compat as auth  # noqa: E402
from app.modules.auth import service as auth_service  # noqa: E402
from app.modules.auth.dependencies import require_admin  # noqa: E402
from app.modules.dashboard import service as dashboard_service  # noqa: E402
from app.modules.hematology.schemas import AnalysisResult  # noqa: E402
from app.modules.pet_history import service as history_service  # noqa: E402
from app.shared.analysis_output import scrub_hidden_labels  # noqa: E402
from app.db import queries as db  # noqa: E402


def _reset_memory_db() -> None:
    os.environ.pop("DATABASE_URL", None)
    os.environ.pop("ADMIN_EMAILS", None)
    db.DATABASE_URL = None
    db._use_db = False
    db._engine = None
    db._memory_analyses.clear()
    db._memory_users.clear()
    db._memory_pets.clear()
    db._memory_breeds.clear()
    db._memory_dashboard_metrics.clear()
    db._memory_epidemiology_events.clear()
    db.init_db()


def _auth_headers(user_id: str) -> dict[str, str]:
    token = auth.create_access_token({"sub": user_id})
    return {"Authorization": f"Bearer {token}"}


def _analysis_payload(
    analysis_id: str,
    *,
    created_at: str | None = None,
    findings: list[dict] | None = None,
    qc_flags: list[str] | None = None,
) -> dict:
    return {
        "id": analysis_id,
        "filename": f"{analysis_id}.pdf",
        "file_size": 2048,
        "created_at": created_at or datetime.now().isoformat(),
        "confidence": 0.91,
        "quality_score": 0.88,
        "species": "Canino",
        "summary": "Analisis de prueba",
        "diagnoses": [],
        "findings": (
            findings
            if findings is not None
            else [
                {"label": "PLT bajo", "detail": "Plaquetas bajas", "severity": "danger"}
            ]
        ),
        "qc_flags": qc_flags or [],
        "lab_values": [],
    }


class DashboardDataSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_memory_db()

    def test_temporal_analytics_returns_only_real_records_for_small_cohort(
        self,
    ) -> None:
        db.save_analysis(_analysis_payload("real-1"))

        response = dashboard_service.temporal(granularity="week", period_days=90)

        self.assertEqual(len(response.timeline), 1)
        self.assertEqual(response.timeline[0].n_analyses, 1)
        self.assertEqual(response.timeline[0].top_finding, "PLT bajo")

    def test_breed_distribution_is_empty_when_database_has_no_registered_pets(
        self,
    ) -> None:
        response = dashboard_service.breed_distribution(period_days=30)

        self.assertEqual(response.total, 0)
        self.assertEqual(response.breeds, [])

    def test_user_role_comes_from_database(self) -> None:
        db.create_user("admin-1", "admin@example.com", "hashed", "Admin", role="admin")
        db.create_user("user-1", "owner@example.com", "hashed", "Owner")

        admin = auth_service.to_response(db.get_user_by_id("admin-1"))
        user = auth_service.to_response(db.get_user_by_id("user-1"))

        self.assertEqual(admin.role, "admin")
        self.assertEqual(user.role, "user")

    def test_technical_dashboard_endpoints_require_admin(self) -> None:
        from fastapi import HTTPException

        db.create_user("admin-1", "admin@example.com", "hashed", "Admin", role="admin")
        db.create_user("user-1", "owner@example.com", "hashed", "Owner")
        with self.assertRaises(HTTPException) as raised:
            require_admin("user-1")
        self.assertEqual(raised.exception.status_code, 403)
        require_admin("admin-1")
        self.assertEqual(dashboard_service.model_quality().version is not None, True)

    def test_scrub_hidden_frotis_artifacts_removes_historical_findings_qc_and_diagnoses(
        self,
    ) -> None:
        record = _analysis_payload(
            "frotis-1",
            findings=[
                {
                    "label": "Frotis recomendado",
                    "detail": "El analizador recomienda revision.",
                    "severity": "warn",
                },
                {
                    "label": "PLT bajo",
                    "detail": "Plaquetas bajas",
                    "severity": "danger",
                },
            ],
            qc_flags=["Se recomienda revisión de frotis sanguíneo"],
        )
        record["diagnoses"] = [
            "Confirmación con frotis sanguíneo recomendada para evaluación morfológica.",
            "Trombocitopenia leve.",
        ]
        record["summary"] = "Hallazgos detectados: Frotis recomendado, PLT bajo."

        scrubbed = scrub_hidden_labels(record)

        self.assertEqual([f["label"] for f in scrubbed["findings"]], ["PLT bajo"])
        self.assertEqual(scrubbed["qc_flags"], [])
        self.assertEqual(scrubbed["diagnoses"], ["Trombocitopenia leve."])
        self.assertNotIn("Frotis recomendado", scrubbed["summary"])

    def test_model_quality_reads_metrics_and_gates_from_dashboard_metric_store(
        self,
    ) -> None:
        old_cache = dashboard_service._analytics_cache
        old_get_dashboard_metric = getattr(db, "get_dashboard_metric", None)

        def fake_get_dashboard_metric(key: str):
            if key == "model_analytics_cache":
                return {
                    "cv_results": [
                        {
                            "label": "DB_LABEL",
                            "pr_auc_mean": "0.50",
                            "roc_auc_mean": "0.60",
                            "f1_mean": "0.70",
                        }
                    ],
                    "calibration": {"DB_LABEL": {"ece_test": "0.02"}},
                    "domain_shift": [],
                    "model_metadata": {"version": "db-version"},
                }
            if key == "operational_gates":
                return {"feature_parity": "fail"}
            return None

        try:
            dashboard_service._analytics_cache = {
                "cv_results": [
                    {
                        "label": "CACHE_LABEL",
                        "pr_auc_mean": "0.90",
                        "roc_auc_mean": "0.90",
                        "f1_mean": "0.90",
                    }
                ],
                "calibration": {"CACHE_LABEL": {"ece_test": "0.01"}},
                "domain_shift": [],
                "model_metadata": {"version": "cache-version"},
            }
            setattr(db, "get_dashboard_metric", fake_get_dashboard_metric)

            response = dashboard_service.model_quality()

            self.assertEqual(response.version, "db-version")
            self.assertEqual([label.name for label in response.labels], ["DB_LABEL"])
            self.assertEqual(response.gates, {"feature_parity": "fail"})
        finally:
            dashboard_service._analytics_cache = old_cache
            if old_get_dashboard_metric is None:
                delattr(db, "get_dashboard_metric")
            else:
                setattr(db, "get_dashboard_metric", old_get_dashboard_metric)

    def test_history_response_model_accepts_legacy_records_without_model_metadata(
        self,
    ) -> None:
        db.save_analysis(_analysis_payload("legacy-1"), user_id="user-1")

        records = history_service.list_history("user-1", pet_id=None, limit=1, offset=0)
        validated = TypeAdapter(list[AnalysisResult]).validate_python(records)

        payload = validated[0].model_dump()
        self.assertIsNone(payload["prediction_id"])
        self.assertIsNone(payload["model_version"])
        self.assertIsNone(payload["policy_version"])
        self.assertIsNone(payload["schema_version"])


if __name__ == "__main__":
    unittest.main()
