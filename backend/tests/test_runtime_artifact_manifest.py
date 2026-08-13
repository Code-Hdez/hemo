from __future__ import annotations

import hashlib
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PROJECT_ROOT / "data" / "processed" / "artifact_manifest_v2.json"


def test_runtime_artifact_manifest_matches_the_files_shipped_with_the_project() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    for artifact in manifest["runtime_artifacts"]:
        artifact_path = PROJECT_ROOT / artifact["path"]
        assert (
            artifact_path.is_file()
        ), f"Runtime artifact is missing: {artifact['path']}"
        actual_sha256 = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        assert actual_sha256 == artifact["sha256"], artifact["path"]
