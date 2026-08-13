from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from scripts.run_stage10_acceptance import (
    Stage10Runner,
    _atomic_json,
    _numeric_values,
)


RELEASE_ID = "e5991a0462afaabdc34eb1284740e1d06a653415"


def test_numeric_values_preserve_selected_and_historical_cbc_values() -> None:
    facts = [
        {"parameter": "WBC", "value": "9.2 x10^9/L"},
        {"code": "WBC", "value": "18,4 x10^9/L"},
        {"parameter": "RBC", "value": "6.1 x10^12/L"},
    ]

    assert _numeric_values(facts, "wbc") == [9.2, 18.4]


def test_atomic_json_replaces_bytes_and_keeps_mode_0600(tmp_path: Path) -> None:
    target = tmp_path / "evidence.json"

    _atomic_json(target, {"revision": "previous"})
    _atomic_json(target, {"revision": RELEASE_ID})

    assert json.loads(target.read_text(encoding="utf-8")) == {
        "revision": RELEASE_ID
    }
    assert target.stat().st_mode & 0o777 == 0o600
    assert not list(tmp_path.glob(".evidence.json.*.tmp"))


def test_public_report_excludes_sensitive_acceptance_state(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    report_path = tmp_path / "report.json"
    secret = "stage10-secret-that-must-not-be-reported"
    _atomic_json(
        state_path,
        {
            "release_id": RELEASE_ID,
            "identities": {
                "a": {
                    "email": "synthetic@example.com",
                    "password": secret,
                    "token": secret,
                }
            },
            "results": [
                {
                    "name": "sanitized_contract",
                    "status": "PASS",
                    "duration_ms": 1,
                    "evidence": {"tokens_redacted": True},
                }
            ],
        },
    )
    runner = Stage10Runner(
        Namespace(
            release_id=RELEASE_ID,
            phase="domain-off",
            state=state_path,
            report=report_path,
            api_base="http://frontend/api/v1",
            core_base="http://backend:8000",
            frontend_base="http://frontend",
        )
    )

    runner._save()

    report = report_path.read_text(encoding="utf-8")
    assert secret not in report
    assert "synthetic@example.com" not in report
    assert json.loads(report)["summary"] == {"failed": 0, "passed": 1}
    assert report_path.stat().st_mode & 0o777 == 0o600
