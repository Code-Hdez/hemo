from __future__ import annotations

import argparse
from pathlib import Path

from app.core.artifact_registry_contract import load_artifact_set


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a hemovet.artifacts/v1 inventory without deploying it."
    )
    parser.add_argument("artifact_set", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    artifact_set = load_artifact_set(args.artifact_set)
    print(
        f"valid {artifact_set.schema_version}: "
        f"{artifact_set.release_id} ({len(artifact_set.images)} images)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
