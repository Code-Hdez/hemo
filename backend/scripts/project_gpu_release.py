#!/usr/bin/env python3
"""Project a complete release manifest to the closed GPU boot contract."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from types import ModuleType

from app.core.release_manifest import load_release_manifest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_CONTRACT_PATH = PROJECT_ROOT / "deploy" / "gpu" / "runtime_contract.py"


def _runtime_contract() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "hemovet_gpu_runtime_contract", RUNTIME_CONTRACT_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("gpu_runtime_contract")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def project_gpu_release(
    release_manifest: Path,
    bundle_manifest: Path,
    output: Path,
) -> dict[str, object]:
    release = load_release_manifest(release_manifest)
    payload: dict[str, object] = {
        "schema_version": "hemovet.gpu-runtime-release/v1",
        "source_contract": release.schema_version,
        "release_id": release.release_id,
        "revision_state": release.gpu_runtime.initial_validation_state,
        "apply_on": release.gpu_runtime.apply_on,
        "update_while_running": release.gpu_runtime.update_while_running,
        "runtime": release.gpu_runtime.runtime.model_dump(),
        "startup": {
            "contract_version": release.gpu_runtime.startup_contract_version,
            "bundle_digest": release.gpu_runtime.startup_bundle_digest,
        },
        "model": release.gpu_runtime.model.model_dump(),
    }
    contract = _runtime_contract()
    expected_bundle = contract.bundle_digest(bundle_manifest)
    validated = contract.validate_manifest(
        payload, expected_bundle_digest=expected_bundle
    )
    contract.atomic_write(output, json.dumps(validated, indent=2) + "\n")
    print(f"projected hemovet.gpu-runtime-release/v1: {release.release_id}")
    return validated


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-manifest", required=True, type=Path)
    parser.add_argument("--bundle-manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    project_gpu_release(
        args.release_manifest,
        args.bundle_manifest,
        args.output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
