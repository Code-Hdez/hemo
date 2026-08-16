from __future__ import annotations

import json
from pathlib import Path
import re
import runpy
import stat
import subprocess

import pytest
from pydantic import ValidationError
import yaml

from app.core.artifact_registry_contract import canonical_artifact_set
from app.core.release_manifest import load_release_manifest
from scripts.create_artifact_set import create_artifact_set
from scripts.prepare_release import ReleasePreparationError, prepare_release
from scripts.project_gpu_release import project_gpu_release
from scripts.render_release_environment import render_release_environment
from scripts.validate_release_payload import validate_release_payload


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = PROJECT_ROOT / ".github" / "workflows" / "deploy.yml"
SHA = "a" * 40
OLLAMA_BASE_URL = "http://10.128.0.3:11434/"
REGISTRY = (
    "us-central1-docker.pkg.dev/"
    "project-5b36701c-f44f-4c03-a12/hemovet-images"
)
ACTION_PIN = re.compile(r"^[^@]+@[0-9a-f]{40}$")


def _valid_environment() -> str:
    namespace = runpy.run_path(
        str(PROJECT_ROOT / "backend" / "tests" / "test_deploy_env.py")
    )
    value = namespace["VALID_ENV"]
    assert isinstance(value, str)
    return value


def _write_artifact_set(path: Path) -> Path:
    artifact_set = create_artifact_set(
        github_sha=SHA,
        repository="xPshycho/hemogramas-proyectoICC",
        registry_repository=REGISTRY,
        created_at="2026-08-02T18:00:00Z",
        digests={
            "backend": "sha256:" + "1" * 64,
            "frontend": "sha256:" + "2" * 64,
            "ollama-runtime": "sha256:" + "3" * 64,
        },
    )
    path.write_text(canonical_artifact_set(artifact_set) + "\n", encoding="utf-8")
    return path


def _write_rag_summary(path: Path, **overrides: object) -> Path:
    payload: dict[str, object] = {
        "dry_run": True,
        "index_fingerprint": "f" * 64,
        "corpus_revision": "curated-canine-cbc-2026-08-02",
        "sources": 1250,
        "chunks": 4696,
        "quarantined_sources": 0,
        "schema_version": "markdown-v5",
        "corpus_schema_version": "hemovet-rag-v2",
    }
    payload.update(overrides)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _prepare(
    tmp_path: Path,
    *,
    base_content: str | None = None,
    ollama_base_url: str = OLLAMA_BASE_URL,
    chat_server_writes: bool = False,
) -> tuple[Path, Path, Path]:
    base_environment = tmp_path / "base.env"
    base_environment.write_text(
        base_content if base_content is not None else _valid_environment(),
        encoding="utf-8",
    )
    candidate = tmp_path / "candidate.env"
    release = tmp_path / "release-manifest.json"
    artifact_set = _write_artifact_set(tmp_path / "artifact-set.json")
    rag_summary = _write_rag_summary(tmp_path / "rag-summary.json")

    prepare_release(
        base_environment=base_environment,
        artifact_set_path=artifact_set,
        rag_summary_path=rag_summary,
        caddy_configuration=PROJECT_ROOT / "deploy" / "Caddyfile",
        bundle_manifest=PROJECT_ROOT / "deploy" / "gpu" / "bundle-manifest.sha256",
        github_sha=SHA,
        repository="xPshycho/hemogramas-proyectoICC",
        workflow_run_id=123456,
        workflow_run_attempt=1,
        created_at="2026-08-02T18:00:00Z",
        ollama_base_url=ollama_base_url,
        chat_server_writes=chat_server_writes,
        candidate_environment=candidate,
        release_manifest=release,
    )
    return base_environment, candidate, release


def test_release_pipeline_binds_one_sha_real_digests_rag_and_gpu(
    tmp_path: Path,
) -> None:
    base_environment, candidate, release_path = _prepare(tmp_path)
    release = load_release_manifest(release_path)

    assert release.release_id == SHA
    assert release.application.revision == SHA
    assert release.gpu_runtime.revision == SHA
    assert release.application.backend.digest == "sha256:" + "1" * 64
    assert release.application.frontend.digest == "sha256:" + "2" * 64
    assert release.gpu_runtime.runtime.digest == "sha256:" + "3" * 64
    assert release.rag.collection_name == (
        "hemovet_canine_hematology_v2__ffffffffffff"
    )
    assert release.rag.schema_version == "hemovet-rag-v2"
    assert release.gpu_runtime.initial_validation_state == (
        "pending_boot_validation"
    )
    assert release.gpu_runtime.update_while_running is False
    assert stat.S_IMODE(candidate.stat().st_mode) == 0o600
    assert stat.S_IMODE(release_path.stat().st_mode) == 0o600

    manifest_text = release_path.read_text(encoding="utf-8")
    for secret in (
        "database-password-strong",
        "openrouter-secret-value",
        "gemini-secret-value",
    ):
        assert secret not in manifest_text

    validate_release_payload(release_path, candidate, PROJECT_ROOT)
    rendered = tmp_path / "rendered.env"
    render_release_environment(
        base_environment,
        release_path,
        OLLAMA_BASE_URL,
        rendered,
    )
    assert rendered.read_bytes() == candidate.read_bytes()

    gpu_projection = tmp_path / "gpu-runtime.json"
    projected = project_gpu_release(
        release_path,
        PROJECT_ROOT / "deploy" / "gpu" / "bundle-manifest.sha256",
        gpu_projection,
    )
    assert projected["release_id"] == SHA
    assert projected["revision_state"] == "pending_boot_validation"
    assert set(projected) == {
        "schema_version",
        "source_contract",
        "release_id",
        "revision_state",
        "apply_on",
        "update_while_running",
        "runtime",
        "startup",
        "model",
    }


@pytest.mark.parametrize(
    "override",
    [
        {"dry_run": False},
        {"chunks": 0},
        {"quarantined_sources": 1},
        {"index_fingerprint": "not-a-digest"},
        {"corpus_schema_version": ""},
    ],
)
def test_release_preparation_fails_closed_for_invalid_rag_evidence(
    tmp_path: Path,
    override: dict[str, object],
) -> None:
    base_environment = tmp_path / "base.env"
    base_environment.write_text(_valid_environment(), encoding="utf-8")
    candidate = tmp_path / "candidate.env"
    release = tmp_path / "release.json"

    with pytest.raises(ReleasePreparationError, match="rag_summary"):
        prepare_release(
            base_environment=base_environment,
            artifact_set_path=_write_artifact_set(tmp_path / "artifacts.json"),
            rag_summary_path=_write_rag_summary(
                tmp_path / "rag-summary.json", **override
            ),
            caddy_configuration=PROJECT_ROOT / "deploy" / "Caddyfile",
            bundle_manifest=(
                PROJECT_ROOT / "deploy" / "gpu" / "bundle-manifest.sha256"
            ),
            github_sha=SHA,
            repository="xPshycho/hemogramas-proyectoICC",
            workflow_run_id=1,
            workflow_run_attempt=1,
            created_at="2026-08-02T18:00:00Z",
            ollama_base_url=OLLAMA_BASE_URL,
            candidate_environment=candidate,
            release_manifest=release,
        )

    assert not candidate.exists()
    assert not release.exists()


def test_release_rejects_rag_corpus_schema_drift(tmp_path: Path) -> None:
    base_environment = tmp_path / "base.env"
    base_environment.write_text(_valid_environment(), encoding="utf-8")

    with pytest.raises(ReleasePreparationError, match="rag_schema_version"):
        prepare_release(
            base_environment=base_environment,
            artifact_set_path=_write_artifact_set(tmp_path / "artifacts.json"),
            rag_summary_path=_write_rag_summary(
                tmp_path / "rag-summary.json",
                corpus_schema_version="hemovet-rag-v3",
            ),
            caddy_configuration=PROJECT_ROOT / "deploy" / "Caddyfile",
            bundle_manifest=(
                PROJECT_ROOT / "deploy" / "gpu" / "bundle-manifest.sha256"
            ),
            github_sha=SHA,
            repository="xPshycho/hemogramas-proyectoICC",
            workflow_run_id=1,
            workflow_run_attempt=1,
            created_at="2026-08-02T18:00:00Z",
            ollama_base_url=OLLAMA_BASE_URL,
            candidate_environment=tmp_path / "candidate.env",
            release_manifest=tmp_path / "release.json",
        )

    assert not (tmp_path / "candidate.env").exists()
    assert not (tmp_path / "release.json").exists()


def test_release_preparation_rejects_bad_digest_and_duplicate_identity(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValidationError, match="sha256"):
        create_artifact_set(
            github_sha=SHA,
            repository="xPshycho/hemogramas-proyectoICC",
            registry_repository=REGISTRY,
            created_at="2026-08-02T18:00:00Z",
            digests={
                "backend": "mutable",
                "frontend": "sha256:" + "2" * 64,
                "ollama-runtime": "sha256:" + "3" * 64,
            },
        )

    base = tmp_path / "base.env"
    base.write_text(
        _valid_environment() + "RAG_COLLECTION_NAME=duplicate\n",
        encoding="utf-8",
    )
    with pytest.raises(ReleasePreparationError, match="duplicate derived"):
        prepare_release(
            base_environment=base,
            artifact_set_path=_write_artifact_set(tmp_path / "artifacts.json"),
            rag_summary_path=_write_rag_summary(tmp_path / "rag.json"),
            caddy_configuration=PROJECT_ROOT / "deploy" / "Caddyfile",
            bundle_manifest=(
                PROJECT_ROOT / "deploy" / "gpu" / "bundle-manifest.sha256"
            ),
            github_sha=SHA,
            repository="xPshycho/hemogramas-proyectoICC",
            workflow_run_id=1,
            workflow_run_attempt=1,
            created_at="2026-08-02T18:00:00Z",
            ollama_base_url=OLLAMA_BASE_URL,
            candidate_environment=tmp_path / "candidate.env",
            release_manifest=tmp_path / "release.json",
        )


def test_release_environment_cannot_drift_after_publication(tmp_path: Path) -> None:
    base, candidate, release = _prepare(tmp_path)
    base.write_text(
        base.read_text(encoding="utf-8").replace(
            "POSTGRES_PASSWORD=database-password-strong",
            "POSTGRES_PASSWORD=a-different-private-value",
        ),
        encoding="utf-8",
    )
    output = tmp_path / "drifted.env"

    with pytest.raises(ValueError, match="release_environment_digest_mismatch"):
        render_release_environment(base, release, OLLAMA_BASE_URL, output)
    assert not output.exists()

    candidate.write_text(
        candidate.read_text(encoding="utf-8") + "# unexpected drift\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="configuration_digest"):
        validate_release_payload(release, candidate, PROJECT_ROOT)


def test_release_projects_verified_private_provider_over_legacy_local_url(
    tmp_path: Path,
) -> None:
    legacy_environment = _valid_environment().replace(
        "OLLAMA_BASE_URL=http://10.20.30.40:11434/",
        "OLLAMA_BASE_URL=http://ollama:11434/",
    )
    base, candidate, release = _prepare(
        tmp_path,
        base_content=legacy_environment,
    )

    assert f"OLLAMA_BASE_URL={OLLAMA_BASE_URL}" in candidate.read_text(
        encoding="utf-8"
    )
    reconstructed = tmp_path / "reconstructed.env"
    render_release_environment(
        base,
        release,
        OLLAMA_BASE_URL,
        reconstructed,
    )
    assert reconstructed.read_bytes() == candidate.read_bytes()

    wrong_endpoint = tmp_path / "wrong-endpoint.env"
    with pytest.raises(ValueError, match="release_environment_digest_mismatch"):
        render_release_environment(
            base,
            release,
            "http://10.128.0.99:11434/",
            wrong_endpoint,
        )
    assert not wrong_endpoint.exists()


def test_release_rejects_public_provider_url_without_leaving_candidate(
    tmp_path: Path,
) -> None:
    candidate = tmp_path / "candidate.env"

    with pytest.raises(ValueError, match="OLLAMA_BASE_URL"):
        _prepare(
            tmp_path,
            ollama_base_url="https://example.com:11434/",
        )

    assert not candidate.exists()


def test_workflow_is_manual_fail_closed_and_uses_pinned_wif_iap() -> None:
    raw = WORKFLOW_PATH.read_text(encoding="utf-8")
    workflow = yaml.safe_load(raw)
    trigger = workflow.get("on") or workflow.get(True)
    jobs = workflow["jobs"]
    dispatch = trigger["workflow_dispatch"]["inputs"]

    assert dispatch["operation"]["options"] == [
        "VALIDATE_WIF_IAP",
        "PUBLISH",
        "DEPLOY",
    ]
    assert workflow["env"]["OLLAMA_PRIVATE_BASE_URL"] == OLLAMA_BASE_URL
    assert raw.count('--ollama-base-url "$OLLAMA_PRIVATE_BASE_URL"') == 2
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["concurrency"]["cancel-in-progress"] == (
        "${{ github.event_name == 'pull_request' }}"
    )
    assert "github.event_name == 'workflow_dispatch'" in jobs["deploy_prod"]["if"]
    assert "inputs.confirm_sha == github.sha" in jobs["deploy_prod"]["if"]
    assert "github.event_name == 'workflow_dispatch'" in (
        jobs["publish_gpu_release"]["if"]
    )
    assert "inputs.operation == 'DEPLOY'" in jobs["publish_gpu_release"]["if"]
    assert "inputs.confirm_sha == github.sha" in (
        jobs["publish_gpu_release"]["if"]
    )
    assert jobs["deploy_prod"]["environment"] == "production"
    assert jobs["wif_iap_validation"]["environment"] == "production"
    assert "environment" not in jobs["wif_reject_missing_environment"]
    assert jobs["wif_reject_missing_environment"]["permissions"] == {
        "contents": "read",
        "id-token": "write",
    }
    assert jobs["wif_iap_validation"]["permissions"] == {
        "contents": "read",
        "id-token": "write",
    }

    action_references = [
        step["uses"]
        for job in jobs.values()
        for step in job.get("steps", [])
        if "uses" in step
    ]
    assert action_references
    assert all(ACTION_PIN.fullmatch(reference) for reference in action_references)
    for job in jobs.values():
        for step in job.get("steps", []):
            if str(step.get("uses", "")).startswith(
                "google-github-actions/auth@"
            ):
                assert "credentials_json" not in step["with"]

    for forbidden in (
        "secrets.GCP_HOST",
        "secrets.GCP_USER",
        "secrets.GCP_SSH_KEY",
        "appleboy/ssh-action",
        "git reset --hard",
        "git clean -fd",
        "credentials_json:",
        ":latest",
        "set -x",
    ):
        assert forbidden not in raw
    assert "--tunnel-through-iap" in raw
    assert "pending_boot_validation" in raw
    assert "--provenance=mode=max" in (
        PROJECT_ROOT / "deploy" / "ci" / "build-and-publish-images.sh"
    ).read_text(encoding="utf-8")
    assert "--sbom=true" in (
        PROJECT_ROOT / "deploy" / "ci" / "build-and-publish-images.sh"
    ).read_text(encoding="utf-8")


def test_versioned_deploy_script_validates_before_any_mutation_and_can_rollback() -> None:
    deploy = (PROJECT_ROOT / "deploy" / "prod" / "deploy-release.sh").read_text(
        encoding="utf-8"
    )
    authentication = deploy.index(
        '"$staging_root/source/deploy/prod/authenticate-artifact-registry.sh"'
    )
    validation = deploy.index('validate_payload \\\n  "$staging_root/source"')
    pull = deploy.index('compose "$release_source" "$release_candidate" pull')
    environment_install = deploy.index("manage_deploy_env.py\" install")
    stack_update = deploy.index(
        'compose "$release_source" "$ACTIVE_ENV" up -d',
        environment_install,
    )

    assert authentication < validation < pull < environment_install < stack_update
    assert 'PYTHONPATH="$release_source/backend" python \\' not in deploy
    assert 'PYTHONPATH="$release_source/backend" python3 \\' in deploy
    assert "--network none" in deploy
    assert "--read-only" in deploy
    assert "--cap-drop ALL" in deploy
    assert "--security-opt no-new-privileges=true" in deploy
    assert 'DOCKER_CONFIG="$DOCKER_CONFIG_DIRECTORY" docker run --rm' in deploy
    assert 'backend.reference | select(test(' in deploy
    assert "manage_deploy_env.py\" rollback" in deploy
    assert "--expected-collection" in deploy
    assert "--no-build" in deploy
    assert "docker-compose.gpu.yml" not in deploy
    assert "git pull" not in deploy
    assert "git reset" not in deploy
    assert "set -x" not in deploy

    authentication_script = (
        PROJECT_ROOT / "deploy" / "prod" / "authenticate-artifact-registry.sh"
    ).read_text(encoding="utf-8")
    assert "hemovet-prod-runtime@" in authentication_script
    assert "service account key" not in authentication_script.casefold()


def test_backend_container_health_tracks_core_not_optional_provider() -> None:
    compose = yaml.safe_load(
        (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    )
    health_command = compose["services"]["backend"]["healthcheck"]["test"][1]

    assert "core_ready" in health_command
    assert "status" not in health_command


def test_build_metadata_digest_expression_is_executable(tmp_path: Path) -> None:
    digest = f"sha256:{'a' * 64}"
    metadata = tmp_path / "metadata.json"
    metadata.write_text(
        json.dumps({"containerimage.digest": digest}),
        encoding="utf-8",
    )
    build_script = (
        PROJECT_ROOT / "deploy" / "ci" / "build-and-publish-images.sh"
    ).read_text(encoding="utf-8")

    assert "jq -er '.[\"containerimage.digest\"]'" in build_script
    result = subprocess.run(
        ["jq", "-er", '.["containerimage.digest"]', str(metadata)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == digest


@pytest.mark.parametrize("encendido", [False, True])
def test_la_condicion_de_medicion_viaja_por_el_manifiesto_y_el_digest_cuadra(
    tmp_path: Path, encendido: bool
) -> None:
    """El flag va al MANIFIESTO, y por eso los dos renderizados coinciden.

    El intento anterior lo inyecto solo en `prepare_release`, sin llevarlo al
    manifiesto: el renderizador de la VM no podia reconstruir el mismo texto y
    el digest dejaba de cuadrar. El control no estaba de mas — senalaba que
    faltaba la fuente de verdad.

    Se prueba en las DOS posiciones. Un flag comprobado solo en una direccion
    puede estar clavado a un literal y nadie se entera.
    """
    base, candidate, release = _prepare(tmp_path, chat_server_writes=encendido)

    esperado = "CHAT_SERVER_WRITES_ENABLED=1" if encendido else (
        "CHAT_SERVER_WRITES_ENABLED=0"
    )
    assert esperado in candidate.read_text(encoding="utf-8")

    manifiesto = load_release_manifest(release)
    assert manifiesto.application.chat_server_writes is encendido

    # Lo que decide todo: el renderizado de la VM, desde el manifiesto, produce
    # EXACTAMENTE el mismo texto — y por tanto el mismo sha256.
    salida = tmp_path / "rendered.env"
    render_release_environment(base, release, OLLAMA_BASE_URL, salida)
    assert salida.read_text(encoding="utf-8") == candidate.read_text(encoding="utf-8")
    assert esperado in salida.read_text(encoding="utf-8")


def test_la_condicion_de_medicion_esta_APAGADA_si_nadie_la_pide(
    tmp_path: Path,
) -> None:
    """Falla cerrado: un despliegue normal no enciende una condicion clinica."""
    _, candidate, release = _prepare(tmp_path)
    assert "CHAT_SERVER_WRITES_ENABLED=0" in candidate.read_text(encoding="utf-8")
    assert load_release_manifest(release).application.chat_server_writes is False


def test_un_manifiesto_ANTERIOR_al_campo_sigue_cargando(tmp_path: Path) -> None:
    """El campo es aditivo: el contrato sigue en v1 a proposito.

    Subir a v2 invalidaria el `Literal` de todos los manifiestos ya emitidos,
    incluidos los de rollback. Un campo con valor por defecto es compatible
    hacia atras, y esto lo comprueba en vez de suponerlo.
    """
    _, _, release = _prepare(tmp_path)
    crudo = json.loads(release.read_text(encoding="utf-8"))
    del crudo["application"]["chat_server_writes"]
    antiguo = tmp_path / "manifiesto-antiguo.json"
    antiguo.write_text(json.dumps(crudo), encoding="utf-8")

    cargado = load_release_manifest(antiguo)
    assert cargado.application.chat_server_writes is False
