from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile

import pytest

from app.core.artifact_registry_contract import canonical_artifact_set
from scripts.create_artifact_set import create_artifact_set
from scripts.prepare_release import prepare_release
from scripts.project_gpu_release import project_gpu_release
from scripts.validate_rollback_bundle import (
    RollbackBundleError,
    validate_rollback_bundle,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEPLOY_SCRIPT = PROJECT_ROOT / "deploy" / "prod" / "deploy-release.sh"
GPU_SELECTION_SCRIPT = PROJECT_ROOT / "deploy" / "gpu" / "select-desired-release.sh"
BUNDLE_MANIFEST = PROJECT_ROOT / "deploy" / "gpu" / "bundle-manifest.sha256"
REGISTRY = "us-central1-docker.pkg.dev/project-5b36701c-f44f-4c03-a12/hemovet-images"
PREVIOUS_SHA = "1" * 40
CANDIDATE_SHA = "2" * 40
PREVIOUS_DIGESTS = {
    "backend": "sha256:c20b932993c97d6078d04033f72d2de132381f6a6a06580dc65be74d52b5191f",
    "frontend": "sha256:55b82e9e868247fc71d764f932610f0849db93fbe88b60261683f7894d305d7f",
    "ollama-runtime": "sha256:b526b1d4bc30d0cc641e0d2a186034b327c97de0171b1a47ce1c917d79604e5f",
}
CANDIDATE_DIGESTS = {
    "backend": "sha256:c710984c1c3d42959bf54ef387490903a06aa9eb92a4c00acdeb6c26ee5c72ae",
    "frontend": "sha256:8feb146ec8092fc4df480331015a71e5271eaa255daa8cb3b5454d97aedbb296",
    "ollama-runtime": "sha256:de0833bd3afd746a50281ba867b1504a836bcde54b493bf9c65c3d9c2a389179",
}
PREVIOUS_FINGERPRINT = (
    "6832f37d428731520ce903de60d0781df543df3a10c84f1fcdbf27056bef9b60"
)
CANDIDATE_FINGERPRINT = "f" * 64


def _valid_environment() -> str:
    namespace = runpy.run_path(
        str(PROJECT_ROOT / "backend" / "tests" / "test_deploy_env.py")
    )
    value = namespace["VALID_ENV"]
    assert isinstance(value, str)
    return value


def _payload(
    directory: Path,
    *,
    release_id: str,
    digests: dict[str, str],
    fingerprint: str,
) -> dict[str, Path]:
    directory.mkdir(parents=True)
    artifact_set = create_artifact_set(
        github_sha=release_id,
        repository="xPshycho/hemogramas-proyectoICC",
        registry_repository=REGISTRY,
        created_at="2026-08-03T02:00:00Z",
        digests=digests,
    )
    artifact_path = directory / "artifact-set.json"
    artifact_path.write_text(
        canonical_artifact_set(artifact_set) + "\n", encoding="utf-8"
    )
    rag_path = directory / "rag-summary.json"
    rag_path.write_text(
        json.dumps(
            {
                "dry_run": True,
                "index_fingerprint": fingerprint,
                "corpus_revision": "curated-canine-cbc-stage9",
                "sources": 1250,
                "chunks": 4696,
                "quarantined_sources": 0,
                "schema_version": "markdown-v5",
                "corpus_schema_version": "hemovet-rag-v2",
            }
        ),
        encoding="utf-8",
    )
    base = directory / "base.env"
    base.write_text(_valid_environment(), encoding="utf-8")
    candidate = directory / "candidate.env"
    manifest = directory / "release-manifest.json"
    prepare_release(
        base_environment=base,
        artifact_set_path=artifact_path,
        rag_summary_path=rag_path,
        caddy_configuration=PROJECT_ROOT / "deploy" / "Caddyfile",
        bundle_manifest=BUNDLE_MANIFEST,
        github_sha=release_id,
        repository="xPshycho/hemogramas-proyectoICC",
        workflow_run_id=30776245995,
        workflow_run_attempt=1,
        created_at="2026-08-03T02:00:00Z",
        ollama_base_url="http://10.128.0.3:11434/",
        candidate_environment=candidate,
        release_manifest=manifest,
    )
    gpu = directory / "gpu-runtime.json"
    project_gpu_release(manifest, BUNDLE_MANIFEST, gpu)
    return {
        "artifact": artifact_path,
        "candidate": candidate,
        "manifest": manifest,
        "gpu": gpu,
    }


def _source_archive(path: Path) -> Path:
    included = (
        PROJECT_ROOT / "backend" / "app",
        PROJECT_ROOT / "backend" / "scripts",
        PROJECT_ROOT / "deploy",
        PROJECT_ROOT / "docker-compose.yml",
        PROJECT_ROOT / "docker-compose.prod.yml",
        PROJECT_ROOT / "knowledge_base" / "manifests" / "sources_manifest.json",
    )
    with tarfile.open(path, "w:gz") as archive:
        for source in included:
            archive.add(
                source,
                arcname=source.relative_to(PROJECT_ROOT),
                filter=lambda info: None
                if "__pycache__" in Path(info.name).parts
                or info.name.endswith((".pyc", ".pyo"))
                else info,
            )
    return path


def _write_fake_commands(directory: Path) -> Path:
    directory.mkdir()
    docker = directory / "docker"
    docker.write_text(
        """#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys

args = sys.argv[1:]
log = Path(os.environ["HEMOVET_FAKE_DOCKER_LOG"])

def env_values():
    if "--env-file" not in args:
        return {}
    path = Path(args[args.index("--env-file") + 1])
    values = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if "=" not in raw or raw.lstrip().startswith("#"):
            continue
        key, value = raw.split("=", 1)
        values[key.strip()] = value.strip()
    return values

def record(operation):
    values = env_values()
    safe = {
        "operation": operation,
        "release": values.get("HEMOVET_BUILD_REVISION"),
        "backend": values.get("HEMOVET_BACKEND_IMAGE"),
        "frontend": values.get("HEMOVET_FRONTEND_IMAGE"),
        "rag": values.get("RAG_COLLECTION_NAME"),
    }
    with log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(safe, sort_keys=True) + "\\n")
    return safe

if args and args[0] == "inspect":
    print("healthy")
    raise SystemExit(0)
if not args or args[0] != "compose":
    raise SystemExit(2)

commands = {"config", "pull", "ps", "run", "up", "exec"}
command = next((value for value in args[1:] if value in commands), "")
safe = record(command)
if command == "ps" and "-q" in args:
    print("stage9-chroma")
elif command == "up":
    if safe["release"] == os.environ.get("HEMOVET_FAKE_FAIL_RELEASE"):
        raise SystemExit(42)
elif command == "ps":
    print(f"backend running release={safe['release']}")
raise SystemExit(0)
""",
        encoding="utf-8",
    )
    docker.chmod(0o755)
    curl = directory / "curl"
    curl.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
    curl.chmod(0o755)
    return directory


def _write_fake_gcloud(directory: Path) -> Path:
    directory.mkdir()
    gcloud = directory / "gcloud"
    gcloud.write_text(
        """#!/usr/bin/env python3
import json
import os
from pathlib import Path
import shutil
import sys

args = sys.argv[1:]
state = Path(os.environ["HEMOVET_FAKE_GPU_METADATA"])
status = os.environ.get("HEMOVET_FAKE_GPU_STATUS", "TERMINATED")
if "describe" in args and any("value(status)" in value for value in args):
    print(status)
    raise SystemExit(0)
if "describe" in args and "--format=json" in args:
    print(json.dumps({"metadata": {"items": [{
        "key": "hemovet-gpu-desired-release",
        "value": state.read_text(encoding="utf-8"),
    }]}}))
    raise SystemExit(0)
if "add-metadata" in args:
    index = args.index("--metadata-from-file") + 1
    _, source = args[index].split("=", 1)
    shutil.copyfile(source, state)
    raise SystemExit(0)
raise SystemExit(2)
""",
        encoding="utf-8",
    )
    gcloud.chmod(0o755)
    return directory


def _isolated_root() -> Path:
    root = Path(tempfile.mkdtemp(prefix="hemovet-stage9-rollback.", dir="/tmp"))
    root.chmod(0o700)
    sentinel = root / ".hemovet-isolated-deploy-test"
    sentinel.write_text("hemovet.isolated-deployment/v1\n", encoding="utf-8")
    sentinel.chmod(0o600)
    return root


def _seed_data(root: Path) -> tuple[Path, dict[str, int], str]:
    database = root / "clinical-data.sqlite3"
    connection = sqlite3.connect(database)
    try:
        expected: dict[str, int] = {}
        for table in (
            "users",
            "owners",
            "pets",
            "hemograms",
            "chat_conversations",
            "chat_turns",
        ):
            connection.execute(
                f"CREATE TABLE {table} (id INTEGER PRIMARY KEY, marker TEXT)"
            )
            connection.execute(
                f"INSERT INTO {table} (marker) VALUES (?)", (f"stage9-{table}",)
            )
            expected[table] = 1
        connection.commit()
    finally:
        connection.close()
    return database, expected, hashlib.sha256(database.read_bytes()).hexdigest()


def _assert_data_unchanged(
    database: Path, expected: dict[str, int], expected_digest: str
) -> None:
    assert hashlib.sha256(database.read_bytes()).hexdigest() == expected_digest
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        actual = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in expected
        }
    finally:
        connection.close()
    assert actual == expected


def _collection_tree(root: Path) -> tuple[Path, dict[str, str]]:
    chroma = root / "chroma-data"
    for name in (
        "hemovet_canine_hematology_v2__6832f37d4287",
        "hemovet_canine_hematology_v2__ffffffffffff",
    ):
        target = chroma / name / "index.bin"
        target.parent.mkdir(parents=True)
        target.write_bytes(f"immutable-{name}".encode())
    hashes = {
        str(path.relative_to(chroma)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(chroma.rglob("*"))
        if path.is_file()
    }
    return chroma, hashes


def _run_deploy(
    *,
    root: Path,
    archive: Path,
    payload: dict[str, Path],
    fake_bin: Path,
    fake_log: Path,
    fail_release: str = "",
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(
        {
            "HEMOVET_ALLOW_ISOLATED_DEPLOY_TEST": "1",
            "HEMOVET_FAKE_DOCKER_LOG": str(fake_log),
            "HEMOVET_FAKE_FAIL_RELEASE": fail_release,
            "PATH": f"{fake_bin}:{Path(sys.executable).parent}:{environment['PATH']}",
        }
    )
    return subprocess.run(
        [
            "bash",
            str(DEPLOY_SCRIPT),
            "--archive",
            str(archive),
            "--release-manifest",
            str(payload["manifest"]),
            "--candidate-environment",
            str(payload["candidate"]),
            "--isolated-root",
            str(root),
        ],
        cwd=PROJECT_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _prepare_isolated_state(
    root: Path, previous_environment: Path
) -> tuple[Path, Path, Path]:
    state = root / "var" / "lib" / "hemovet-prod"
    state.mkdir(parents=True)
    state.chmod(0o700)
    active = state / ".env"
    shutil.copy2(previous_environment, active)
    active.chmod(0o600)

    previous_source = root / "baseline-source"
    grandfather_source = root / "grandfather-source"
    for source in (previous_source, grandfather_source):
        source.mkdir()
        shutil.copy2(PROJECT_ROOT / "docker-compose.yml", source)
        shutil.copy2(PROJECT_ROOT / "docker-compose.prod.yml", source)
        shutil.copy2(previous_environment, source / ".env")
    deployment_root = root / "opt" / "hemovet-prod"
    deployment_root.mkdir(parents=True)
    (deployment_root / "current").symlink_to(previous_source)
    (deployment_root / "previous").symlink_to(grandfather_source)
    return active, previous_source, grandfather_source


def _safe_log(path: Path) -> list[dict[str, str | None]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def test_rollback_bundle_joins_release_artifacts_environment_and_gpu(
    tmp_path: Path,
) -> None:
    payload = _payload(
        tmp_path / "candidate",
        release_id=CANDIDATE_SHA,
        digests=CANDIDATE_DIGESTS,
        fingerprint=CANDIDATE_FINGERPRINT,
    )

    plan = validate_rollback_bundle(
        release_manifest=payload["manifest"],
        artifact_set=payload["artifact"],
        candidate_environment=payload["candidate"],
        source_root=PROJECT_ROOT,
        gpu_release=payload["gpu"],
        bundle_manifest=BUNDLE_MANIFEST,
    )

    assert plan["release_id"] == CANDIDATE_SHA
    assert plan["backend_digest"] == CANDIDATE_DIGESTS["backend"]
    assert plan["frontend_digest"] == CANDIDATE_DIGESTS["frontend"]
    assert plan["gpu_runtime_digest"] == CANDIDATE_DIGESTS["ollama-runtime"]
    assert plan["rag_collection"].endswith("ffffffffffff")
    assert "latest" not in json.dumps(plan)


def test_rollback_bundle_rejects_cross_revision_gpu_projection(tmp_path: Path) -> None:
    previous = _payload(
        tmp_path / "previous",
        release_id=PREVIOUS_SHA,
        digests=PREVIOUS_DIGESTS,
        fingerprint=PREVIOUS_FINGERPRINT,
    )
    candidate = _payload(
        tmp_path / "candidate",
        release_id=CANDIDATE_SHA,
        digests=CANDIDATE_DIGESTS,
        fingerprint=CANDIDATE_FINGERPRINT,
    )

    with pytest.raises(RollbackBundleError, match="gpu_release.release_id"):
        validate_rollback_bundle(
            release_manifest=candidate["manifest"],
            artifact_set=candidate["artifact"],
            candidate_environment=candidate["candidate"],
            source_root=PROJECT_ROOT,
            gpu_release=previous["gpu"],
            bundle_manifest=BUNDLE_MANIFEST,
        )


def test_candidate_install_and_manifest_only_rollback_restore_prior_digests(
    tmp_path: Path,
) -> None:
    previous = _payload(
        tmp_path / "previous",
        release_id=PREVIOUS_SHA,
        digests=PREVIOUS_DIGESTS,
        fingerprint=PREVIOUS_FINGERPRINT,
    )
    candidate = _payload(
        tmp_path / "candidate",
        release_id=CANDIDATE_SHA,
        digests=CANDIDATE_DIGESTS,
        fingerprint=CANDIDATE_FINGERPRINT,
    )
    archive = _source_archive(tmp_path / "source.tar.gz")
    root = _isolated_root()
    try:
        active, _, _ = _prepare_isolated_state(root, previous["candidate"])
        fake_log = root / "docker-events.jsonl"
        fake_bin = _write_fake_commands(root / "fake-bin")
        database, counts, database_digest = _seed_data(root)
        chroma, collection_hashes = _collection_tree(root)

        installed = _run_deploy(
            root=root,
            archive=archive,
            payload=candidate,
            fake_bin=fake_bin,
            fake_log=fake_log,
        )
        assert installed.returncode == 0, installed.stdout + installed.stderr
        assert active.read_bytes() == candidate["candidate"].read_bytes()
        assert Path(root / "opt/hemovet-prod/current").resolve().parent.name == (
            CANDIDATE_SHA
        )
        release_source = (
            root
            / "opt"
            / "hemovet-prod"
            / "releases"
            / CANDIDATE_SHA
            / "source"
        )
        source_manifest = (
            release_source
            / "knowledge_base"
            / "manifests"
            / "sources_manifest.json"
        )
        assert source_manifest.stat().st_mode & 0o777 == 0o644
        assert all(
            directory.stat().st_mode & 0o777 == 0o755
            for directory in (
                release_source,
                release_source / "knowledge_base",
                release_source / "knowledge_base" / "manifests",
            )
        )
        assert (
            root
            / "opt"
            / "hemovet-prod"
            / "releases"
            / CANDIDATE_SHA
            / "candidate.env"
        ).stat().st_mode & 0o777 == 0o600

        rolled_back = _run_deploy(
            root=root,
            archive=archive,
            payload=previous,
            fake_bin=fake_bin,
            fake_log=fake_log,
        )
        assert rolled_back.returncode == 0, rolled_back.stdout + rolled_back.stderr
        assert active.read_bytes() == previous["candidate"].read_bytes()
        assert Path(root / "opt/hemovet-prod/current").resolve().parent.name == (
            PREVIOUS_SHA
        )
        assert (
            f"RAG_COLLECTION_NAME=hemovet_canine_hematology_v2__{PREVIOUS_FINGERPRINT[:12]}"
            in active.read_text()
        )

        events = _safe_log(fake_log)
        final_up = [event for event in events if event["operation"] == "up"][-1]
        assert final_up["backend"].endswith(f"@{PREVIOUS_DIGESTS['backend']}")
        assert final_up["frontend"].endswith(f"@{PREVIOUS_DIGESTS['frontend']}")
        assert final_up["rag"].endswith(PREVIOUS_FINGERPRINT[:12])
        assert all("latest" not in json.dumps(event) for event in events)

        _assert_data_unchanged(database, counts, database_digest)
        assert {
            str(path.relative_to(chroma)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(chroma.rglob("*"))
            if path.is_file()
        } == collection_hashes
    finally:
        shutil.rmtree(root)


def test_post_install_failure_restores_exact_state_and_is_repeatable(
    tmp_path: Path,
) -> None:
    previous = _payload(
        tmp_path / "previous",
        release_id=PREVIOUS_SHA,
        digests=PREVIOUS_DIGESTS,
        fingerprint=PREVIOUS_FINGERPRINT,
    )
    candidate = _payload(
        tmp_path / "candidate",
        release_id=CANDIDATE_SHA,
        digests=CANDIDATE_DIGESTS,
        fingerprint=CANDIDATE_FINGERPRINT,
    )
    archive = _source_archive(tmp_path / "source.tar.gz")
    root = _isolated_root()
    try:
        active, previous_source, grandfather_source = _prepare_isolated_state(
            root, previous["candidate"]
        )
        previous_bytes = active.read_bytes()
        previous_digest = hashlib.sha256(previous_bytes).hexdigest()
        fake_log = root / "docker-events.jsonl"
        fake_bin = _write_fake_commands(root / "fake-bin")
        database, counts, database_digest = _seed_data(root)
        chroma, collection_hashes = _collection_tree(root)

        for _ in range(2):
            failed = _run_deploy(
                root=root,
                archive=archive,
                payload=candidate,
                fake_bin=fake_bin,
                fake_log=fake_log,
                fail_release=CANDIDATE_SHA,
            )
            assert failed.returncode == 42
            assert "rollback=completed" in failed.stderr
            assert active.read_bytes() == previous_bytes
            assert hashlib.sha256(active.read_bytes()).hexdigest() == previous_digest
            assert (root / "opt/hemovet-prod/current").resolve() == previous_source
            assert (root / "opt/hemovet-prod/previous").resolve() == grandfather_source
            _assert_data_unchanged(database, counts, database_digest)

        transaction_root = root / "var/lib/hemovet-prod/transactions" / CANDIDATE_SHA
        attempts = sorted(transaction_root.glob("*/transaction.json"))
        assert len(attempts) == 2
        assert [json.loads(path.read_text())["state"] for path in attempts] == [
            "ROLLED_BACK",
            "ROLLED_BACK",
        ]
        assert {
            str(path.relative_to(chroma)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(chroma.rglob("*"))
            if path.is_file()
        } == collection_hashes

        events = _safe_log(fake_log)
        up_events = [event for event in events if event["operation"] == "up"]
        assert [event["release"] for event in up_events] == [
            CANDIDATE_SHA,
            PREVIOUS_SHA,
            CANDIDATE_SHA,
            PREVIOUS_SHA,
        ]
        assert up_events[-1]["backend"].endswith(f"@{PREVIOUS_DIGESTS['backend']}")
        assert up_events[-1]["frontend"].endswith(f"@{PREVIOUS_DIGESTS['frontend']}")
        combined_output = "\n".join(
            json.dumps(event, sort_keys=True) for event in events
        )
        for secret in (
            "database-password-strong",
            "openrouter-secret-value",
            "gemini-secret-value",
        ):
            assert secret not in combined_output
    finally:
        shutil.rmtree(root)


def test_isolated_deployment_requires_explicit_enablement(tmp_path: Path) -> None:
    root = _isolated_root()
    try:
        placeholder = tmp_path / "placeholder"
        placeholder.write_text("test", encoding="utf-8")
        result = subprocess.run(
            [
                "bash",
                str(DEPLOY_SCRIPT),
                "--archive",
                str(placeholder),
                "--release-manifest",
                str(placeholder),
                "--candidate-environment",
                str(placeholder),
                "--isolated-root",
                str(root),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "was not explicitly enabled" in result.stderr
    finally:
        shutil.rmtree(root)


def test_gpu_desired_revision_can_be_selected_and_restored_while_stopped(
    tmp_path: Path,
) -> None:
    previous = _payload(
        tmp_path / "previous",
        release_id=PREVIOUS_SHA,
        digests=PREVIOUS_DIGESTS,
        fingerprint=PREVIOUS_FINGERPRINT,
    )
    candidate = _payload(
        tmp_path / "candidate",
        release_id=CANDIDATE_SHA,
        digests=CANDIDATE_DIGESTS,
        fingerprint=CANDIDATE_FINGERPRINT,
    )
    fake_bin = _write_fake_gcloud(tmp_path / "fake-gcloud")
    state = tmp_path / "metadata.json"
    shutil.copy2(previous["gpu"], state)
    original = state.read_bytes()
    backup = tmp_path / "previous-output.json"
    environment = os.environ.copy()
    environment.update(
        {
            "HEMOVET_FAKE_GPU_METADATA": str(state),
            "HEMOVET_FAKE_GPU_STATUS": "TERMINATED",
            "PATH": f"{fake_bin}:{Path(sys.executable).parent}:{environment['PATH']}",
        }
    )

    selected = subprocess.run(
        [
            "bash",
            str(GPU_SELECTION_SCRIPT),
            "--manifest",
            str(candidate["gpu"]),
            "--previous-output",
            str(backup),
        ],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert selected.returncode == 0, selected.stdout + selected.stderr
    assert state.read_bytes() == candidate["gpu"].read_bytes()
    assert backup.read_bytes() == original
    assert "vm_status=TERMINATED" in selected.stdout

    restored = subprocess.run(
        [
            "bash",
            str(GPU_SELECTION_SCRIPT),
            "--manifest",
            str(previous["gpu"]),
        ],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert restored.returncode == 0, restored.stdout + restored.stderr
    assert state.read_bytes() == original

    environment["HEMOVET_FAKE_GPU_STATUS"] = "RUNNING"
    refused = subprocess.run(
        [
            "bash",
            str(GPU_SELECTION_SCRIPT),
            "--manifest",
            str(candidate["gpu"]),
        ],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert refused.returncode == 1
    assert "require a stopped VM" in refused.stderr
    assert state.read_bytes() == original
