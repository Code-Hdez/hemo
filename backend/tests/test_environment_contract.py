from __future__ import annotations

import os
import re
from pathlib import Path

import yaml

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-at-least-32-characters")
os.environ.setdefault("CORS_ORIGINS", '["http://testserver"]')

from app.core.config import Settings
from scripts.validate_deploy_env import CANONICAL_VALUES, REQUIRED_VARIABLES

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _env_keys(path: Path) -> set[str]:
    return {
        line.split("=", 1)[0]
        for line in path.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#") and "=" in line
    }


def _env_values(path: Path) -> dict[str, str]:
    return {
        line.split("=", 1)[0]: line.split("=", 1)[1]
        for line in path.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#") and "=" in line
    }


def test_env_example_documents_all_runtime_and_compose_variables() -> None:
    documented = _env_keys(PROJECT_ROOT / ".env.example")
    required = set(Settings.model_fields) | {
        "INSTALL_LOCAL_ML",
        "INSTALL_LOCAL_EXTRACTION",
        "COMPOSE_FILE",
        "OLLAMA_AUTO_PULL",
        "OLLAMA_CONTEXT_LENGTH",
        "OLLAMA_KEEP_ALIVE",
        "OLLAMA_MAX_LOADED_MODELS",
        "OLLAMA_MAX_QUEUE",
        "OLLAMA_MODELS_DIR",
        "OLLAMA_NUM_PARALLEL",
        "OLLAMA_REPEAT_PENALTY",
        "OLLAMA_TOP_K",
        "OLLAMA_TOP_P",
        "OLLAMA_WARMUP_ENABLED",
        "OLLAMA_WARMUP_TIMEOUT_SECONDS",
        "VITE_API_BASE_URL",
        "VITE_API_PROXY_TARGET",
        "VITE_MAP_TILE_URL",
        "PUBLIC_BASE_URL",
        "CADDY_SITE_ADDRESS",
        "CADDY_WWW_ADDRESS",
        "CHROMA_PERSIST_DIRECTORY",
    }
    assert required <= documented


def test_production_env_example_documents_every_deploy_variable() -> None:
    documented = _env_keys(PROJECT_ROOT / ".env.production.example")
    required = set(Settings.model_fields) | {
        "INSTALL_LOCAL_ML",
        "INSTALL_LOCAL_EXTRACTION",
        "COMPOSE_FILE",
        "OLLAMA_CONTEXT_LENGTH",
        "OLLAMA_KEEP_ALIVE",
        "OLLAMA_REPEAT_PENALTY",
        "OLLAMA_TOP_K",
        "OLLAMA_TOP_P",
        "OLLAMA_WARMUP_ENABLED",
        "OLLAMA_WARMUP_TIMEOUT_SECONDS",
        "VITE_API_BASE_URL",
        "VITE_API_PROXY_TARGET",
        "VITE_MAP_TILE_URL",
        "PUBLIC_BASE_URL",
        "CADDY_SITE_ADDRESS",
        "CADDY_WWW_ADDRESS",
        "CHROMA_PERSIST_DIRECTORY",
        "HEMOVET_BACKEND_IMAGE",
        "HEMOVET_FRONTEND_IMAGE",
    }

    assert REQUIRED_VARIABLES <= documented
    assert required <= documented


def test_environment_examples_separate_local_runtime_from_production_images() -> None:
    local = _env_keys(PROJECT_ROOT / ".env.example")
    production = _env_keys(PROJECT_ROOT / ".env.production.example")

    assert local - production == {
        "OLLAMA_AUTO_PULL",
        "OLLAMA_FLASH_ATTENTION",
        "OLLAMA_KV_CACHE_TYPE",
        "OLLAMA_MAX_LOADED_MODELS",
        "OLLAMA_MAX_QUEUE",
        "OLLAMA_MODELS_DIR",
        "OLLAMA_NUM_PARALLEL",
    }
    assert production - local == {
        "HEMOVET_BACKEND_IMAGE",
        "HEMOVET_FRONTEND_IMAGE",
    }


def test_chat_runtime_limits_match_settings_examples_and_effective_compose() -> None:
    # Model-scale knobs are legitimately different between the small local
    # dev model (.env.example) and the qualified production profile
    # (.env.production.example, Qwen3.6 27B / 64K) — everything else here is
    # operational tuning that both environments share.
    shared = {
        "OLLAMA_MAX_RETRIES": "1",
        "CHAT_MESSAGE_MAX_CHARS": "2000",
        "CHAT_STRUCTURED_OUTPUT_ENABLED": "1",
        "CHAT_HISTORY_LIMIT": "12",
        "CHAT_SESSION_TTL_SECONDS": "3600",
        # Una sola generación con 20 s de espera en cola rechazaba a la
        # segunda persona que escribía: comprobado en producción, de tres
        # peticiones simultáneas dos murieron con HTTP 429 a los 21 s frente
        # a generaciones que duran entre 20 y 123 s. La espera ahora cubre
        # una generación completa y hay dos ranuras.
        "CHAT_QUEUE_TIMEOUT_SECONDS": "60",
        # Un turno son hasta dos generaciones (la inicial y su reparación),
        # así que el techo total debe caber ambas más la espera en cola.
        "CHAT_TOTAL_TIMEOUT_SECONDS": "240",
        "CHAT_MAX_CONCURRENT_GENERATIONS": "1",
        "CHAT_DB_BLOCKING_MAX_CONCURRENCY": "4",
        "CHAT_STREAM_HEARTBEAT_SECONDS": "15",
    }
    local_only = {
        **shared,
        "OLLAMA_NUM_PREDICT": "384",
        "OLLAMA_TEMPERATURE": "0.1",
        "OLLAMA_TOP_P": "0.9",
        "OLLAMA_CONTEXT_LENGTH": "4096",
        "CHAT_SUMMARY_MAX_TOKENS": "800",
        "CHAT_MAX_INPUT_TOKENS": "3200",
    }
    production_only = {
        **shared,
        # Las respuestas reales usan 263 tokens de media y 427 como máximo,
        # y un resumen que agotaba los 2048 chocaba con el timeout del
        # proveedor: SEL-03 de la batería murió a los 90,5 s.
        "OLLAMA_NUM_PREDICT": "1280",
        # La salida de producción es un contrato estructurado que se valida
        # frase a frase, no conversación abierta: con 0.6 la redacción
        # cambiaba en cada llamada y esa variación era la que hacía fallar a
        # los validadores y disparaba reparaciones.
        "OLLAMA_TEMPERATURE": "0.3",
        "OLLAMA_TOP_P": "0.8",
        # Los prompts medidos pesan 1.682 tokens de media y 2.884 el mayor:
        # 64K reservaba veinte veces lo necesario, y como la VRAM escala con
        # NUM_PARALLEL × CONTEXT_LENGTH, era lo que impedía la segunda
        # ranura en una L4 con 18 GB ya ocupados por el modelo.
        "OLLAMA_CONTEXT_LENGTH": "16384",
        "CHAT_SUMMARY_MAX_TOKENS": "800",
        "CHAT_MAX_INPUT_TOKENS": "12000",
    }
    for path, expected in (
        (PROJECT_ROOT / ".env.example", local_only),
        (PROJECT_ROOT / ".env.production.example", production_only),
    ):
        values = _env_values(path)
        assert {key: values[key] for key in expected} == expected

    # docker-compose.yml is the local/base compose file: its fallback
    # defaults must match the local (non-production) profile.
    compose = yaml.safe_load(
        (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    )
    environment = compose["services"]["backend"]["environment"]
    assert {
        key: environment[key] for key in local_only
    } == {
        key: f"${{{key}:-{value}}}" for key, value in local_only.items()
    }

    production = (PROJECT_ROOT / "docker-compose.prod.yml").read_text(
        encoding="utf-8"
    )
    assert 'CHAT_MAX_INPUT_TOKENS: "${CHAT_MAX_INPUT_TOKENS:-3200}"' in production
    assert 'CHAT_REQUIRE_BROWSER_SESSION_ID: "${CHAT_REQUIRE_BROWSER_SESSION_ID:-1}"' in production


def test_compose_fallback_defaults_are_accepted_by_settings() -> None:
    """Cada default del compose tiene que arrancar, no solo estar escrito.

    `docker-compose.yml` traía `CHAT_REPAIR_TEMPERATURE:-0.0` mientras
    `config.py` declara ese campo con `gt=0` (una reparación a temperatura 0
    reproduce el borrador rechazado). Levantar el stack sin exportar esa
    variable — el caso normal en local — hacía que `Settings()` fallara y el
    backend no arrancara. Ningún test lo veía: los contratos existentes
    comparan cadenas del compose contra cadenas esperadas, así que un default
    inválido pasaba mientras coincidiera consigo mismo.
    """

    compose = yaml.safe_load(
        (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    )
    environment = compose["services"]["backend"]["environment"]

    defaults: dict[str, str] = {}
    for raw in environment.values():
        match = re.fullmatch(r"\$\{([A-Z0-9_]+):-(.*)\}", str(raw))
        if match is None:
            continue
        name, value = match.group(1), match.group(2)
        # Un default vacío deja actuar al default del propio campo; los nombres
        # ajenos a Settings (INSTALL_LOCAL_ML, VITE_*) no son de este contrato.
        if not value or name not in Settings.model_fields:
            continue
        defaults[name] = value

    # Sin esto el propio test no probaría nada si el compose cambia de formato.
    assert len(defaults) > 50
    assert defaults["CHAT_REPAIR_TEMPERATURE"] == "0.1"

    defaults.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    defaults.setdefault("SECRET_KEY", "test-secret-key-with-at-least-32-characters")

    Settings(**defaults)


def test_production_requires_ephemeral_browser_session_but_local_is_compatible() -> None:
    local = _env_values(PROJECT_ROOT / ".env.example")
    production = _env_values(PROJECT_ROOT / ".env.production.example")

    assert local["CHAT_REQUIRE_BROWSER_SESSION_ID"] == "0"
    assert production["CHAT_REQUIRE_BROWSER_SESSION_ID"] == "1"


def test_qualified_production_runtime_matches_examples_and_settings() -> None:
    # CANONICAL_VALUES (validate_deploy_env.py) only pins values that must be
    # byte-identical everywhere regardless of environment/model swaps: the
    # RAG embedding identity (changing it silently would desync the index
    # from query-time embeddings) and the OTel service identity. Runtime
    # knobs like the Ollama model/digest/context or chat concurrency are
    # validated by format/range instead (see validate_deploy_env.py), so a
    # qualified model swap (e.g. to Qwen3.6 27B) does not require touching
    # this pinned set.
    canonical = {
        "RAG_SCHEMA_VERSION": "hemovet-rag-v2",
        "RAG_EMBEDDING_MODEL": (
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        ),
        "RAG_EMBEDDING_DIMENSION": "384",
        "OTEL_SERVICE_NAME": "hemovet-backend",
        "OTEL_TRACES_SAMPLER": "parentbased_traceidratio",
    }
    assert CANONICAL_VALUES == canonical

    # Development retains the smaller fallback default; production pins its
    # own qualified runtime explicitly through its validated environment
    # (.env.production.example), asserted separately below.
    assert Settings.model_fields["OLLAMA_MODEL"].default == (
        "qwen3:4b-instruct-2507-q4_K_M"
    )
    assert str(Settings.model_fields["OLLAMA_NUM_PREDICT"].default) == "384"
    assert str(Settings.model_fields["OLLAMA_CONTEXT_LENGTH"].default) == "4096"
    assert Settings.model_fields["RAG_COLLECTION_NAME"].default == (
        "hemovet_canine_hematology_v2"
    )
    assert Settings.model_fields["RAG_SCHEMA_VERSION"].default == canonical[
        "RAG_SCHEMA_VERSION"
    ]
    assert Settings.model_fields["RAG_EMBEDDING_MODEL"].default == canonical[
        "RAG_EMBEDDING_MODEL"
    ]
    assert str(Settings.model_fields["RAG_EMBEDDING_DIMENSION"].default) == canonical[
        "RAG_EMBEDDING_DIMENSION"
    ]
    assert str(Settings.model_fields["RAG_TOP_K"].default) == "3"

    # The qualified production runtime profile (Qwen3.6 27B / 16K, verified
    # on the L4 GPU host — see deploy/gpu/runtime_contract.py's
    # APPROVED_MODEL/_DIGEST, which is the actual fail-closed identity gate
    # at GPU release time). The context dropped from 64K after measuring the
    # real prompts at 1682 tokens on average and 2884 at most: the unused
    # reservation was what kept a second generation slot from fitting in the
    # L4's remaining VRAM, since Ollama's budget scales with
    # NUM_PARALLEL × CONTEXT_LENGTH.
    production_expected = {
        "OLLAMA_MODEL": "qwen3.6:27b-q4_K_M",
        "OLLAMA_EXPECTED_MODEL_DIGEST": (
            "a50eda8ed977ab48a12431878896b27ffd5cef552c17af3317d9623b939a7f1e"
        ),
        "OLLAMA_EXPECTED_QUANTIZATION": "Q4_K_M",
        "OLLAMA_NUM_PREDICT": "1280",
        "OLLAMA_CONTEXT_LENGTH": "16384",
        "OLLAMA_KEEP_ALIVE": "-1",
        "RAG_SCHEMA_VERSION": canonical["RAG_SCHEMA_VERSION"],
        "RAG_EMBEDDING_MODEL": canonical["RAG_EMBEDDING_MODEL"],
        "RAG_EMBEDDING_DIMENSION": canonical["RAG_EMBEDDING_DIMENSION"],
        "RAG_TOP_K": "3",
        "CHAT_SESSION_TTL_SECONDS": "3600",
        "CHAT_MAX_CONCURRENT_GENERATIONS": "1",
        "CHAT_DB_BLOCKING_MAX_CONCURRENCY": "4",
        "OTEL_SERVICE_NAME": canonical["OTEL_SERVICE_NAME"],
        "OTEL_TRACES_SAMPLER": canonical["OTEL_TRACES_SAMPLER"],
    }
    production_values = _env_values(PROJECT_ROOT / ".env.production.example")
    assert {
        key: production_values[key] for key in production_expected
    } == production_expected

    local = _env_values(PROJECT_ROOT / ".env.example")
    production = _env_values(PROJECT_ROOT / ".env.production.example")
    assert local["RAG_COLLECTION_NAME"] == "hemovet_canine_hematology_v2"
    assert production["RAG_COLLECTION_NAME"] == (
        "hemovet_canine_hematology_v2__<fingerprint-12-hex>"
    )


def test_repository_declares_pinned_python_node_nginx_and_ollama_bases() -> None:
    assert (PROJECT_ROOT / ".python-version").read_text(encoding="utf-8").strip() == (
        "3.11"
    )
    assert (PROJECT_ROOT / ".nvmrc").read_text(encoding="utf-8").strip() == "22"
    assert (PROJECT_ROOT / "backend" / "Dockerfile").read_text(
        encoding="utf-8"
    ).startswith(
        "FROM python:3.11-slim@sha256:"
        "c20888b6acdd1e63e1c433a185bf3ad162c0288fe484616ce062e0d28add2900\n"
    )
    frontend_dockerfile = (PROJECT_ROOT / "frontend_4" / "Dockerfile").read_text(
        encoding="utf-8"
    )
    assert frontend_dockerfile.startswith(
        "FROM node:22-alpine@sha256:"
        "c610fcdfb1d5b4740dd70c284ed3cb16bb857e0f7166196e36a5501df7a3aa32 "
        "AS build\n"
    )
    assert (
        "FROM nginx:alpine@sha256:"
        "4a73073bd557c65b759505da037898b61f1be6cbcc3c2c3aeac22d2a470c1752\n"
        in frontend_dockerfile
    )

    ollama_dockerfile = (
        PROJECT_ROOT / "deploy" / "gpu" / "ollama-runtime.Dockerfile"
    ).read_text(encoding="utf-8")
    assert ollama_dockerfile.startswith(
        "FROM ollama/ollama:0.32.6@sha256:"
        "b88c73ace3e115f8ec53dc8761ae1c0aabfa675406e3681786b98757ce050f42\n"
    )
    assert 'org.opencontainers.image.version="0.32.6"' in ollama_dockerfile
    assert 'io.hemovet.ollama.version="0.32.6"' in ollama_dockerfile

    for dockerfile in (
        (PROJECT_ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8"),
        frontend_dockerfile,
        ollama_dockerfile,
    ):
        assert 'org.opencontainers.image.revision="${HEMOVET_BUILD_REVISION}"' in (
            dockerfile
        )
        assert ":latest" not in dockerfile


def test_environment_examples_use_versioned_expert_rag_corpus() -> None:
    local = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
    production = (PROJECT_ROOT / ".env.production.example").read_text(
        encoding="utf-8"
    )

    expected_source = "RAG_SOURCE_DIR=knowledge_base/expert_review/approved"
    expected_provisional = "RAG_ALLOW_AI_PROVISIONAL=0"

    for env_file in (local, production):
        assert expected_source in env_file
        assert expected_provisional in env_file
    assert "RAG_COLLECTION_NAME=hemovet_canine_hematology_v2\n" in local
    assert (
        "RAG_COLLECTION_NAME=hemovet_canine_hematology_v2__<fingerprint-12-hex>"
        in production
    )


def test_settings_accepts_comma_separated_cors_from_dotenv(
    tmp_path: Path, monkeypatch
) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "DATABASE_URL=sqlite+pysqlite:///:memory:\n"
        "SECRET_KEY=test-secret-key-with-at-least-32-characters\n"
        "CORS_ORIGINS=http://localhost:3000,http://localhost:5175\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("CORS_ORIGINS")

    settings = Settings(_env_file=dotenv)

    assert settings.CORS_ORIGINS == ["http://localhost:3000", "http://localhost:5175"]


def test_compose_builds_frontend_against_versioned_api_by_default() -> None:
    compose = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert 'VITE_API_BASE_URL: "${VITE_API_BASE_URL:-/api/v1}"' in compose


def test_compose_rag_source_and_ai_provisional_mode_are_env_configurable() -> None:
    compose = yaml.safe_load(
        (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    )
    services = compose["services"]

    for service_name in ("rag_ingest", "backend"):
        environment = services[service_name]["environment"]
        assert environment["RAG_SOURCE_DIR"] == (
            "${RAG_SOURCE_DIR:-knowledge_base/expert_review/approved}"
        )
        assert environment["RAG_ALLOW_AI_PROVISIONAL"] == (
            "${RAG_ALLOW_AI_PROVISIONAL:-0}"
        )
        assert environment["RAG_COLLECTION_NAME"] == (
            "${RAG_COLLECTION_NAME:-hemovet_canine_hematology_v2}"
        )


def test_nearby_veterinary_provider_is_documented_and_reaches_backend() -> None:
    local = _env_values(PROJECT_ROOT / ".env.example")
    production = _env_values(PROJECT_ROOT / ".env.production.example")
    compose = yaml.safe_load(
        (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    )
    backend_environment = compose["services"]["backend"]["environment"]

    expected = {
        "VETERINARY_PLACES_OVERPASS_URL": ("https://overpass-api.de/api/interpreter"),
        "VETERINARY_PLACES_TIMEOUT_SECONDS": "8",
    }
    assert {key: local[key] for key in expected} == expected
    assert {key: production[key] for key in expected} == expected
    assert backend_environment["VETERINARY_PLACES_OVERPASS_URL"] == (
        "${VETERINARY_PLACES_OVERPASS_URL:-https://overpass-api.de/api/interpreter}"
    )
    assert backend_environment["VETERINARY_PLACES_TIMEOUT_SECONDS"] == (
        "${VETERINARY_PLACES_TIMEOUT_SECONDS:-8}"
    )


def test_chroma_healthcheck_uses_tools_available_in_the_chroma_image() -> None:
    compose = yaml.safe_load(
        (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    )
    command = compose["services"]["chroma"]["healthcheck"]["test"][1]

    assert "python" not in command
    assert "bash -ec" in command
    assert "/api/v2/heartbeat" in command
    assert "$$status" in command


def test_local_compose_waits_for_ollama_model_and_rag_before_backend() -> None:
    compose = yaml.safe_load((PROJECT_ROOT / "docker-compose.yml").read_text())
    local = yaml.safe_load((PROJECT_ROOT / "docker-compose.local.yml").read_text())
    production_compose = (PROJECT_ROOT / "docker-compose.prod.yml").read_text(
        encoding="utf-8"
    )
    services = compose["services"]
    local_services = local["services"]
    env_example = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
    expected_model = (
        "${OLLAMA_MODEL:-qwen3:4b-instruct-2507-q4_K_M}"
    )

    assert "ollama" not in services
    assert "ollama_setup" not in services
    assert local_services["ollama"]["image"].startswith(
        "ollama/ollama:0.32.6@sha256:"
    )
    assert local_services["ollama_setup"]["environment"]["OLLAMA_MODEL"] == (
        expected_model
    )
    assert services["backend"]["environment"]["OLLAMA_MODEL"] == expected_model
    assert local_services["ollama_setup"]["depends_on"]["ollama"]["condition"] == (
        "service_healthy"
    )
    assert local_services["ollama_setup"]["environment"]["OLLAMA_AUTO_PULL"] == (
        "${OLLAMA_AUTO_PULL:-0}"
    )
    setup_command = "\n".join(local_services["ollama_setup"]["command"])
    assert "OLLAMA_AUTO_PULL" in setup_command
    assert "Skipping Ollama model bootstrap" in setup_command
    assert "ollama pull" in setup_command
    assert "ollama show" in setup_command
    assert local_services["backend"]["depends_on"]["ollama_setup"]["condition"] == (
        "service_completed_successfully"
    )
    assert services["backend"]["depends_on"]["rag_ingest"]["condition"] == (
        "service_completed_successfully"
    )
    assert "ollama_setup" not in services["backend"]["depends_on"]
    assert "OLLAMA_MODEL=qwen3:4b-instruct-2507-q4_K_M" in env_example
    assert "OLLAMA_AUTO_PULL=1" in env_example
    assert "ollama_setup:" not in production_compose
    assert "ollama:" not in production_compose
    assert "      - --validate-only" in production_compose


def test_production_migrates_only_exact_nonroot_volume_mounts() -> None:
    production = (PROJECT_ROOT / "docker-compose.prod.yml").read_text(
        encoding="utf-8"
    )

    assert "  volume_permissions:\n" in production
    assert "    image: alpine:3.22.1@sha256:" in production
    assert '    user: "0:0"\n' in production
    assert '    restart: "no"\n' in production
    assert "    read_only: true\n" in production
    assert "      - pet-media:/app/media\n" in production
    assert "      - embedding-cache:/app/.cache/fastembed\n" in production
    assert "      - ALL\n" in production
    assert "      - CHOWN\n" in production
    assert "chown -R 10001:10001 /app/media /app/.cache/fastembed" in production
    assert "      volume_permissions:\n        condition: service_completed_successfully" in production


def test_production_requires_promoted_rag_collection_at_compose_boundary() -> None:
    production = (PROJECT_ROOT / "docker-compose.prod.yml").read_text(
        encoding="utf-8"
    )

    assert production.count(
        "${RAG_COLLECTION_NAME:?set-promoted-fingerprinted-RAG_COLLECTION_NAME}"
    ) == 2
    assert (
        '${RAG_COLLECTION_NAME:-hemovet_canine_hematology_v2}' not in production
    )


def test_compose_base_excludes_runtime_and_local_overlay_is_cpu_only() -> None:
    compose = yaml.safe_load(
        (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    )
    local = yaml.safe_load(
        (PROJECT_ROOT / "docker-compose.local.yml").read_text(encoding="utf-8")
    )
    assert "ollama" not in compose["services"]
    assert "ollama_setup" not in compose["services"]

    ollama = local["services"]["ollama"]
    environment = ollama["environment"]

    assert "NVIDIA_VISIBLE_DEVICES" not in environment
    assert "NVIDIA_DRIVER_CAPABILITIES" not in environment
    assert "deploy" not in ollama
    assert environment["OLLAMA_KEEP_ALIVE"] == "${OLLAMA_KEEP_ALIVE:-30m}"
    assert environment["OLLAMA_CONTEXT_LENGTH"] == "${OLLAMA_CONTEXT_LENGTH:-4096}"
    assert environment["OLLAMA_NUM_PARALLEL"] == "${OLLAMA_NUM_PARALLEL:-1}"
    assert environment["OLLAMA_MAX_LOADED_MODELS"] == (
        "${OLLAMA_MAX_LOADED_MODELS:-1}"
    )
    assert environment["OLLAMA_MAX_QUEUE"] == "${OLLAMA_MAX_QUEUE:-16}"
    assert "ollama-data:/root/.ollama" in ollama["volumes"]


def test_production_manual_commands_keep_the_web_host_cpu_only() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    production = (PROJECT_ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")
    expected = (
        "docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-build"
    )

    assert expected in readme
    assert expected in production
    assert "docker-compose.gpu.yml" in production
    assert "No combinar este archivo" in production
    assert "ollama_setup:" not in production
    assert "  ollama:" not in production


def test_chroma_persistence_is_explicit() -> None:
    compose = yaml.safe_load(
        (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    )
    chroma = compose["services"]["chroma"]

    assert "IS_PERSISTENT" not in chroma.get("environment", {})
    assert "PERSIST_DIRECTORY" not in chroma.get("environment", {})
    assert "chroma-data:/data" in chroma["volumes"]


def test_runtime_requirements_include_the_container_migration_command() -> None:
    requirements = (PROJECT_ROOT / "backend" / "requirements.txt").read_text(
        encoding="utf-8"
    )
    dockerfile = (PROJECT_ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")

    assert "alembic -c alembic.ini upgrade head" in dockerfile
    assert any(
        line.strip().lower().startswith("alembic") for line in requirements.splitlines()
    )


def test_backend_images_embed_build_revision_without_busting_dependency_cache() -> None:
    compose = yaml.safe_load(
        (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    )
    expected_revision = "${HEMOVET_BUILD_REVISION:-dev}"

    for service_name in ("rag_ingest", "backend"):
        build_args = compose["services"][service_name]["build"]["args"]
        assert build_args["HEMOVET_BUILD_REVISION"] == expected_revision

    dockerfile = (PROJECT_ROOT / "backend" / "Dockerfile").read_text(
        encoding="utf-8"
    )
    dependency_install = dockerfile.index("RUN pip install")
    revision_arg = dockerfile.index("ARG HEMOVET_BUILD_REVISION=dev")
    backend_copy = dockerfile.index(
        "COPY --chown=hemovet:hemovet backend/ ./backend/"
    )

    assert dependency_install < revision_arg < backend_copy


def test_production_caddy_routes_api_and_streams_directly_to_backend() -> None:
    caddyfile = (PROJECT_ROOT / "deploy" / "Caddyfile").read_text(encoding="utf-8")
    production_compose = (PROJECT_ROOT / "docker-compose.prod.yml").read_text(
        encoding="utf-8"
    )

    assert "{$CADDY_SITE_ADDRESS:hemovet.app}" in caddyfile
    assert "{$CADDY_WWW_ADDRESS:www.hemovet.app}" in caddyfile
    assert "handle /api/v1/*" in caddyfile
    assert "reverse_proxy backend:8000" in caddyfile
    assert "flush_interval -1" in caddyfile
    assert "reverse_proxy frontend:80" in caddyfile
    assert "caddy:2.11.4-alpine@sha256:" in production_compose
    assert "./deploy/Caddyfile:/etc/caddy/Caddyfile:ro" in production_compose
    assert "name: caddy_data" in production_compose
    assert "name: caddy_config" in production_compose


def test_local_caddy_overlay_is_http_only_and_never_requests_public_tls() -> None:
    caddyfile = (PROJECT_ROOT / "deploy" / "Caddyfile.local").read_text(
        encoding="utf-8"
    )
    local_compose = (PROJECT_ROOT / "docker-compose.local-caddy.yml").read_text(
        encoding="utf-8"
    )
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")

    assert ":80 {" in caddyfile
    assert "hemovet.app" not in caddyfile
    assert "www.hemovet.app" not in caddyfile
    assert "tls" not in caddyfile.lower()
    assert "acme" not in caddyfile.lower()
    assert "reverse_proxy backend:8000" in caddyfile
    assert "reverse_proxy frontend:80" in caddyfile

    assert "./deploy/Caddyfile.local:/etc/caddy/Caddyfile:ro" in local_compose
    assert "caddy:2.11.4-alpine@sha256:" in local_compose
    assert '"8080:80"' in local_compose
    assert '"443:443"' not in local_compose
    assert "CADDY_SITE_ADDRESS" not in local_compose
    assert "CADDY_WWW_ADDRESS" not in local_compose
    assert "!deploy/Caddyfile.local" in gitignore


def test_frontend_nginx_preserves_auth_and_disables_stream_buffering() -> None:
    nginx = (PROJECT_ROOT / "frontend_4" / "nginx.conf").read_text(encoding="utf-8")

    assert "proxy_http_version 1.1;" in nginx
    assert "proxy_set_header Authorization $http_authorization;" in nginx
    assert "proxy_set_header Cookie $http_cookie;" in nginx
    assert "proxy_set_header X-Forwarded-Host $host;" in nginx
    assert "proxy_buffering off;" in nginx
    assert "proxy_request_buffering off;" in nginx
    assert "proxy_cache off;" in nginx


def test_main_deploy_uses_immutable_production_topology_and_public_health() -> None:
    workflow_path = PROJECT_ROOT / ".github" / "workflows" / "deploy.yml"
    workflow = workflow_path.read_text(encoding="utf-8")
    parsed_workflow = yaml.safe_load(workflow)

    assert "PRODUCTION_ENV_B64" in workflow
    assert "backend/scripts/validate_release_payload.py" in workflow
    assert "deploy/prod/deploy-release.sh" in workflow
    assert "https://hemovet.app/api/v1/chat/health" in workflow
    assert "PRODUCTION_SMOKE_EMAIL" not in workflow
    assert "PRODUCTION_SMOKE_PASSWORD" not in workflow
    trigger = parsed_workflow.get("on") or parsed_workflow.get(True)
    assert set(trigger) == {"push", "pull_request", "workflow_dispatch"}
    assert set(parsed_workflow["concurrency"]) == {"group", "cancel-in-progress"}
    assert {
        "test",
        "frontend",
        "configuration",
        "build_and_push",
        "publish_gpu_release",
        "deploy_prod",
        "production_smoke_tests",
    } <= set(
        parsed_workflow["jobs"]
    )
    production_env = _env_values(PROJECT_ROOT / ".env.production.example")
    assert production_env["COMPOSE_FILE"] == (
        "docker-compose.yml:docker-compose.prod.yml"
    )
    assert "python -m ruff check" in workflow
    assert "python -m pytest tests/test_migrations.py -q" in workflow
    assert "python -m pytest tests/llm_chat -q" in workflow
    assert "python -m pytest tools/llm_cbc_eval/tests -q" in workflow
    assert "npm test -- --run" in workflow
    assert "npm run check" in workflow
    assert "npm run build" in workflow
    assert "backend/scripts/validate_compose_topology.py" in workflow
    assert "caddy validate --config /etc/caddy/Caddyfile" in workflow
