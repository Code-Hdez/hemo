from __future__ import annotations

import json
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.prepare_rag_promotion import RAGPromotionError, prepare_rag_promotion
from scripts.manage_deploy_env import (
    DeployEnvironmentTransactionError,
    install_environment,
    rollback_environment,
)
from scripts.validate_deploy_env import DeployEnvironmentError, validate_env_file

VALID_ENV = """\
APP_ENV=production
API_V1_PREFIX=/api/v1
SECRET_KEY=0123456789abcdef0123456789abcdef0123456789abcdef
POSTGRES_PASSWORD=database-password-strong
DATABASE_URL=postgresql://hemovet:database-password-strong@db:5432/hemovet
HEMOVET_DOG_ID_SALT=0123456789abcdef0123456789abcdef
ADMIN_EMAILS=admin@hemovet.app
OTEL_ENABLED=1
OTEL_SERVICE_NAME=hemovet-backend
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=
OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=
OTEL_EXPORTER_OTLP_HEADERS=
OTEL_IDENTIFIER_HMAC_SECRET=abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789
OTEL_TRACES_SAMPLER=parentbased_traceidratio
OTEL_TRACES_SAMPLER_ARG=1.0
OTEL_FASTAPI_INSTRUMENTATION_ENABLED=1
CORS_ORIGINS=https://hemovet.app,https://www.hemovet.app
PUBLIC_BASE_URL=https://hemovet.app
CADDY_SITE_ADDRESS=hemovet.app
CADDY_WWW_ADDRESS=www.hemovet.app
HEMOVET_BACKEND_IMAGE=us-central1-docker.pkg.dev/project-5b36701c-f44f-4c03-a12/hemovet-images/backend@sha256:c20b932993c97d6078d04033f72d2de132381f6a6a06580dc65be74d52b5191f
HEMOVET_FRONTEND_IMAGE=us-central1-docker.pkg.dev/project-5b36701c-f44f-4c03-a12/hemovet-images/frontend@sha256:55b82e9e868247fc71d764f932610f0849db93fbe88b60261683f7894d305d7f
INSTALL_LOCAL_ML=1
HEMOVET_ENABLE_LOCAL_ML=1
INSTALL_LOCAL_EXTRACTION=1
HEMOVET_ENABLE_LOCAL_EXTRACTION=1
OPENROUTER_API_KEY=openrouter-secret-value
GEMINI_API_KEY=gemini-secret-value
OLLAMA_BASE_URL=http://10.20.30.40:11434/
OLLAMA_MODEL=qwen3.6:27b-q4_K_M
OLLAMA_EXPECTED_MODEL_DIGEST=a50eda8ed977ab48a12431878896b27ffd5cef552c17af3317d9623b939a7f1e
OLLAMA_EXPECTED_QUANTIZATION=Q4_K_M
OLLAMA_CONNECT_TIMEOUT_SECONDS=5
OLLAMA_TIMEOUT_SECONDS=90
OLLAMA_WRITE_TIMEOUT_SECONDS=15
OLLAMA_POOL_TIMEOUT_SECONDS=5
OLLAMA_HTTP_MAX_CONNECTIONS=8
OLLAMA_HTTP_MAX_KEEPALIVE_CONNECTIONS=4
OLLAMA_HTTP_KEEPALIVE_EXPIRY_SECONDS=30
OLLAMA_THINK=0
OLLAMA_NUM_PREDICT=384
OLLAMA_TEMPERATURE=0.1
OLLAMA_TOP_P=0.9
OLLAMA_TOP_K=20
OLLAMA_REPEAT_PENALTY=1.0
OLLAMA_MAX_RETRIES=1
OLLAMA_KEEP_ALIVE=30m
OLLAMA_CONTEXT_LENGTH=4096
OLLAMA_WARMUP_ENABLED=1
OLLAMA_WARMUP_TIMEOUT_SECONDS=120
OPENAI_COMPATIBLE_BASE_URL=
OPENAI_COMPATIBLE_MODEL=qwen3:8b
OPENAI_COMPATIBLE_API_KEY=
CHROMA_HOST=chroma
CHROMA_PORT=8000
CHROMA_PERSIST_DIRECTORY=/data
RAG_ENABLED=1
RAG_SOURCE_DIR=knowledge_base/expert_review/approved
RAG_COLLECTION_NAME=hemovet_canine_hematology_v2__0123456789ab
RAG_SCHEMA_VERSION=hemovet-rag-v2
RAG_SOURCE_MANIFEST=knowledge_base/manifests/sources_manifest.json
RAG_EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
RAG_EMBEDDING_MODEL_REVISION=fastembed-registry-0.8.0
RAG_EMBEDDING_POOLING_STRATEGY=mean
RAG_EMBEDDING_NORMALIZATION=true
RAG_EMBEDDING_DOCUMENT_PREFIX=
RAG_EMBEDDING_QUERY_PREFIX=
RAG_EMBEDDING_DIMENSION=384
RAG_EMBEDDING_CACHE_DIR=/app/.cache/fastembed
RAG_CHUNK_SIZE_WORDS=90
RAG_CHUNK_OVERLAP_WORDS=15
RAG_INGEST_BATCH_SIZE=64
RAG_FETCH_K=10
RAG_TOP_K=3
RAG_MIN_RELEVANCE_SCORE=0.38
RAG_BLOCKING_MAX_CONCURRENCY=2
RAG_MAX_CONTEXT_CHARS=3000
RAG_MAX_PER_SOURCE=2
RAG_RRF_K=60
RAG_ALLOW_TEST_DOCUMENTS=0
RAG_ALLOW_AI_PROVISIONAL=0
CHAT_LLM_PROVIDER=ollama
CHAT_MESSAGE_MAX_CHARS=2000
CHAT_STRUCTURED_OUTPUT_ENABLED=1
CHAT_REQUIRE_BROWSER_SESSION_ID=1
CHAT_HISTORY_LIMIT=12
CHAT_SUMMARY_MAX_CHARS=3200
CHAT_SUMMARY_MAX_TOKENS=800
CHAT_MAX_INPUT_TOKENS=3200
CHAT_CONTEXT_RESERVE_TOKENS=256
CHAT_PROFILE_GENERAL_CONTEXT_LENGTH=
CHAT_PROFILE_SELECTED_CONTEXT_LENGTH=
CHAT_PROFILE_HISTORY_CONTEXT_LENGTH=
CHAT_REPAIR_CONTEXT_LENGTH=
CHAT_REPAIR_MAX_INPUT_TOKENS=
CHAT_REPAIR_NUM_PREDICT=512
CHAT_REPAIR_TEMPERATURE=0.1
CHAT_REPAIR_TOP_P=0.9
CHAT_REPAIR_TOP_K=40
CHAT_REPAIR_REPEAT_PENALTY=1.1
CHAT_REPAIR_THINK=0
CHAT_MAX_GENERATION_ATTEMPTS=2
CHAT_REPAIR_MIN_REMAINING_SECONDS=30
CHAT_CLINICAL_FACT_MIN_COUNT=12
CHAT_CLINICAL_FACT_MAX_COUNT=64
CHAT_CLINICAL_FACT_TOKENS_PER_ITEM=96
CHAT_MEMORY_TOPIC_LIMIT=12
CHAT_MEMORY_RECENT_QUESTION_LIMIT=40
CHAT_MEMORY_CLINICAL_FACT_LIMIT=24
CHAT_MEMORY_SUMMARIZED_MESSAGE_ID_LIMIT=200
CHAT_MEMORY_ANSWER_EXCERPT_CHARS=420
CHAT_MEMORY_QUESTION_EXCERPT_CHARS=240
CHAT_MEMORY_SUMMARY_ENTRY_CHARS=260
CHAT_SESSION_TTL_SECONDS=3600
CHAT_TURN_LEASE_GRACE_SECONDS=5
CHAT_QUEUE_TIMEOUT_SECONDS=20
CHAT_TOTAL_TIMEOUT_SECONDS=150
CHAT_MAX_CONCURRENT_GENERATIONS=1
CHAT_DB_BLOCKING_MAX_CONCURRENCY=4
CHAT_STREAM_HEARTBEAT_SECONDS=15
CHAT_TOKENIZER_JSON=
CHAT_TOKENIZER_SHA256=
CHAT_TOKENIZER_REQUIRED=0
VETERINARY_PLACES_OVERPASS_URL=https://overpass-api.de/api/interpreter
VETERINARY_PLACES_TIMEOUT_SECONDS=8
"""


def write_env(path: Path, content: str = VALID_ENV) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def write_promotion(path: Path) -> Path:
    fingerprint = "6832f37d428731520ce903de60d0781df543df3a10c84f1fcdbf27056bef9b60"
    collection = f"hemovet_canine_hematology_v2__{fingerprint[:12]}"
    path.write_text(
        json.dumps(
            {
                "validated": True,
                "collection": collection,
                "index_fingerprint": fingerprint,
                "snapshot": {
                    "collection_chunks": 4696,
                    "index_fingerprint": fingerprint,
                },
                "promotion": {
                    "ready": True,
                    "requires_backend_restart": True,
                    "set_environment": {"RAG_COLLECTION_NAME": collection},
                    "staging_namespace": "hemovet_canine_hematology_v2",
                    "rollback_requires_previous_release": True,
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def with_collection(content: str, collection: str) -> str:
    return content.replace(
        "RAG_COLLECTION_NAME=hemovet_canine_hematology_v2__0123456789ab",
        f"RAG_COLLECTION_NAME={collection}",
    )


def test_rag_promotion_prepares_private_environment_atomically(tmp_path: Path) -> None:
    source = write_env(tmp_path / ".env")
    source.chmod(0o644)
    target = tmp_path / ".env.next"

    collection = prepare_rag_promotion(
        write_promotion(tmp_path / "promotion.json"),
        source,
        target,
    )

    assert collection == "hemovet_canine_hematology_v2__6832f37d4287"
    assert "RAG_COLLECTION_NAME=hemovet_canine_hematology_v2__6832f37d4287" in (
        target.read_text(encoding="utf-8")
    )
    assert "RAG_COLLECTION_NAME=hemovet_canine_hematology_v2__0123456789ab" in (
        source.read_text(encoding="utf-8")
    )
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    validate_env_file(target)


def test_rag_promotion_rejects_mismatched_collection_without_writing(
    tmp_path: Path,
) -> None:
    promotion = write_promotion(tmp_path / "promotion.json")
    payload = json.loads(promotion.read_text(encoding="utf-8"))
    payload["promotion"]["set_environment"]["RAG_COLLECTION_NAME"] = (
        "hemovet_canine_hematology_v2__000000000000"
    )
    promotion.write_text(json.dumps(payload), encoding="utf-8")
    source = write_env(tmp_path / ".env")
    previous = source.read_bytes()
    target = tmp_path / ".env.next"

    with pytest.raises(
        RAGPromotionError,
        match=r"promotion\.set_environment\.RAG_COLLECTION_NAME",
    ):
        prepare_rag_promotion(promotion, source, target)

    assert not target.exists()
    assert source.read_bytes() == previous


def test_complete_environment_install_is_atomic_and_keeps_private_rollback(
    tmp_path: Path,
) -> None:
    target_collection = "hemovet_canine_hematology_v2__aaaaaaaaaaaa"
    active = write_env(tmp_path / ".env")
    previous = active.read_bytes()
    candidate = write_env(
        tmp_path / ".env.next",
        with_collection(VALID_ENV, target_collection)
        + "HEMOVET_BUILD_REVISION=release-two\n",
    )
    transaction = tmp_path / "transactions" / "release-two"

    result = install_environment(
        candidate,
        active,
        transaction,
        expected_collection=target_collection,
    )

    assert result.state == "INSTALLED"
    assert active.read_bytes() == candidate.read_bytes()
    assert (transaction / "previous.env").read_bytes() == previous
    assert stat.S_IMODE(active.stat().st_mode) == 0o600
    assert stat.S_IMODE((transaction / "previous.env").stat().st_mode) == 0o600
    assert stat.S_IMODE(transaction.stat().st_mode) == 0o700
    manifest = json.loads((transaction / "transaction.json").read_text())
    assert manifest["state"] == "INSTALLED"
    assert manifest["previous_collection"].endswith("0123456789ab")
    assert manifest["target_collection"] == target_collection
    assert "openrouter-secret-value" not in json.dumps(manifest)
    assert "gemini-secret-value" not in json.dumps(manifest)


def test_failed_post_install_validation_restores_complete_previous_environment(
    tmp_path: Path,
) -> None:
    target_collection = "hemovet_canine_hematology_v2__bbbbbbbbbbbb"
    active = write_env(tmp_path / ".env")
    previous = active.read_bytes()
    candidate = write_env(
        tmp_path / ".env.next",
        with_collection(VALID_ENV, target_collection),
    )
    transaction = tmp_path / "transactions" / "release-failed"

    def fail_only_after_install(path: Path) -> object:
        result = validate_env_file(path)
        if path == active and target_collection in path.read_text(encoding="utf-8"):
            raise DeployEnvironmentError("Variables inválidas: RAG_COLLECTION_NAME")
        return result

    with pytest.raises(
        DeployEnvironmentTransactionError,
        match="install_failed_automatic_rollback",
    ):
        install_environment(
            candidate,
            active,
            transaction,
            expected_collection=target_collection,
            validator=fail_only_after_install,
        )

    assert active.read_bytes() == previous
    assert "RAG_COLLECTION_NAME=hemovet_canine_hematology_v2__0123456789ab" in (
        active.read_text(encoding="utf-8")
    )
    manifest = json.loads((transaction / "transaction.json").read_text())
    assert manifest["state"] == "AUTO_ROLLED_BACK"


def test_rollback_restores_previous_env_and_rag_collection_idempotently(
    tmp_path: Path,
) -> None:
    target_collection = "hemovet_canine_hematology_v2__cccccccccccc"
    active = write_env(tmp_path / ".env")
    previous = active.read_bytes()
    candidate = write_env(
        tmp_path / ".env.next",
        with_collection(VALID_ENV, target_collection),
    )
    transaction = tmp_path / "transactions" / "release-three"
    install_environment(candidate, active, transaction)

    first = rollback_environment(active, transaction)
    second = rollback_environment(active, transaction)

    assert first.state == second.state == "ROLLED_BACK"
    assert active.read_bytes() == previous
    assert first.previous_collection.endswith("0123456789ab")
    assert first.target_collection == target_collection
    manifest = json.loads((transaction / "transaction.json").read_text())
    assert manifest["state"] == "ROLLED_BACK"


def test_rollback_refuses_to_overwrite_a_newer_environment(tmp_path: Path) -> None:
    target_collection = "hemovet_canine_hematology_v2__dddddddddddd"
    newer_collection = "hemovet_canine_hematology_v2__eeeeeeeeeeee"
    active = write_env(tmp_path / ".env")
    candidate = write_env(
        tmp_path / ".env.next",
        with_collection(VALID_ENV, target_collection),
    )
    transaction = tmp_path / "transactions" / "release-four"
    install_environment(candidate, active, transaction)
    newer = with_collection(VALID_ENV, newer_collection).encode()
    active.write_bytes(newer)

    with pytest.raises(
        DeployEnvironmentTransactionError,
        match="active_environment_revision_changed",
    ):
        rollback_environment(active, transaction)

    assert active.read_bytes() == newer


def test_environment_transaction_cli_installs_and_rolls_back(tmp_path: Path) -> None:
    target_collection = "hemovet_canine_hematology_v2__ffffffffffff"
    active = write_env(tmp_path / ".env")
    previous = active.read_bytes()
    candidate = write_env(
        tmp_path / ".env.next",
        with_collection(VALID_ENV, target_collection),
    )
    transaction = tmp_path / "transactions" / "release-cli"
    script = Path(__file__).resolve().parents[1] / "scripts" / "manage_deploy_env.py"

    installed = subprocess.run(
        [
            sys.executable,
            str(script),
            "install",
            "--candidate-env",
            str(candidate),
            "--active-env",
            str(active),
            "--transaction-dir",
            str(transaction),
            "--expected-collection",
            target_collection,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    rolled_back = subprocess.run(
        [
            sys.executable,
            str(script),
            "rollback",
            "--active-env",
            str(active),
            "--transaction-dir",
            str(transaction),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert installed.returncode == rolled_back.returncode == 0
    assert json.loads(installed.stdout)["state"] == "INSTALLED"
    assert json.loads(rolled_back.stdout)["state"] == "ROLLED_BACK"
    assert "openrouter-secret-value" not in installed.stdout + installed.stderr
    assert active.read_bytes() == previous


def test_rag_promotion_rejects_duplicate_environment_pointer(tmp_path: Path) -> None:
    source = write_env(
        tmp_path / ".env",
        VALID_ENV + "RAG_COLLECTION_NAME=hemovet_canine_hematology_v2__ffffffffffff\n",
    )
    target = tmp_path / ".env.next"

    with pytest.raises(RAGPromotionError, match="environment.RAG_COLLECTION_NAME"):
        prepare_rag_promotion(
            write_promotion(tmp_path / "promotion.json"),
            source,
            target,
        )

    assert not target.exists()


def test_valid_production_environment_passes_without_returning_values(
    tmp_path: Path,
) -> None:
    result = validate_env_file(write_env(tmp_path / ".env"))

    assert result.variable_count >= 25
    assert result.app_env == "production"


def test_invalid_environment_reports_only_variable_names(tmp_path: Path) -> None:
    secret = "secret-do-not-show"
    invalid = VALID_ENV.replace(
        "0123456789abcdef0123456789abcdef0123456789abcdef", secret
    ).replace("CHAT_REQUIRE_BROWSER_SESSION_ID=1", "CHAT_REQUIRE_BROWSER_SESSION_ID=0")

    with pytest.raises(DeployEnvironmentError) as captured:
        validate_env_file(write_env(tmp_path / ".env", invalid))

    message = str(captured.value)
    assert "SECRET_KEY" in message
    assert "CHAT_REQUIRE_BROWSER_SESSION_ID" in message
    assert secret not in message


def test_placeholders_are_rejected_before_deploy(tmp_path: Path) -> None:
    invalid = VALID_ENV.replace(
        "OPENROUTER_API_KEY=openrouter-secret-value", "OPENROUTER_API_KEY=<set-me>"
    )

    with pytest.raises(DeployEnvironmentError, match="OPENROUTER_API_KEY"):
        validate_env_file(write_env(tmp_path / ".env", invalid))


def test_private_gpu_ollama_endpoint_is_accepted(tmp_path: Path) -> None:
    result = validate_env_file(write_env(tmp_path / ".env"))

    assert result.app_env == "production"


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://public.example.com:11434/",
        "ftp://10.20.30.40:11434/",
        "http://user:secret@10.20.30.40:11434/",
        "http://ollama:11434/",
    ],
)
def test_public_or_credentialed_ollama_endpoint_is_rejected(
    tmp_path: Path,
    endpoint: str,
) -> None:
    invalid = VALID_ENV.replace(
        "OLLAMA_BASE_URL=http://10.20.30.40:11434/",
        f"OLLAMA_BASE_URL={endpoint}",
    )

    with pytest.raises(DeployEnvironmentError, match="OLLAMA_BASE_URL"):
        validate_env_file(write_env(tmp_path / ".env", invalid))


@pytest.mark.parametrize(
    ("variable", "invalid_reference"),
    [
        (
            "HEMOVET_BACKEND_IMAGE",
            "us-central1-docker.pkg.dev/project-5b36701c-f44f-4c03-a12/hemovet-images/backend:latest",
        ),
        (
            "HEMOVET_FRONTEND_IMAGE",
            "us-central1-docker.pkg.dev/project-5b36701c-f44f-4c03-a12/hemovet-images/backend@sha256:"
            + "a" * 64,
        ),
    ],
)
def test_production_images_require_the_expected_package_and_digest(
    tmp_path: Path,
    variable: str,
    invalid_reference: str,
) -> None:
    lines = VALID_ENV.splitlines()
    invalid = "\n".join(
        f"{variable}={invalid_reference}" if line.startswith(f"{variable}=") else line
        for line in lines
    )

    with pytest.raises(DeployEnvironmentError, match=variable):
        validate_env_file(write_env(tmp_path / ".env", invalid))


def test_veterinary_places_endpoint_and_timeout_are_validated(tmp_path: Path) -> None:
    invalid = VALID_ENV.replace(
        "VETERINARY_PLACES_OVERPASS_URL=https://overpass-api.de/api/interpreter",
        "VETERINARY_PLACES_OVERPASS_URL=file:///tmp/places.json",
    ).replace(
        "VETERINARY_PLACES_TIMEOUT_SECONDS=8",
        "VETERINARY_PLACES_TIMEOUT_SECONDS=90",
    )

    with pytest.raises(DeployEnvironmentError) as captured:
        validate_env_file(write_env(tmp_path / ".env", invalid))

    assert "VETERINARY_PLACES_OVERPASS_URL" in str(captured.value)
    assert "VETERINARY_PLACES_TIMEOUT_SECONDS" in str(captured.value)


def test_provisional_rag_corpus_is_rejected_in_production(tmp_path: Path) -> None:
    invalid = (
        VALID_ENV.replace(
            "RAG_SOURCE_DIR=knowledge_base/expert_review/approved",
            "RAG_SOURCE_DIR=knowledge_base/ai_review/approved_provisional",
        )
        .replace(
            "RAG_COLLECTION_NAME=hemovet_canine_hematology_v2__0123456789ab",
            "RAG_COLLECTION_NAME=hemovet_canine_hematology_v1",
        )
        .replace("RAG_ALLOW_AI_PROVISIONAL=0", "RAG_ALLOW_AI_PROVISIONAL=1")
    )

    with pytest.raises(DeployEnvironmentError) as captured:
        validate_env_file(write_env(tmp_path / ".env", invalid))

    message = str(captured.value)
    assert "RAG_SOURCE_DIR" in message
    assert "RAG_COLLECTION_NAME" in message
    assert "RAG_ALLOW_AI_PROVISIONAL" in message


def test_incoherent_chat_token_and_timeout_limits_are_rejected(tmp_path: Path) -> None:
    # Lowering the total timeout below a valid queue timeout is what
    # exercises the cross-field ordering check on its own: raising the queue
    # timeout instead would report both its own range violation and the
    # ordering one, which does not tell the two checks apart.
    invalid = VALID_ENV.replace(
        "CHAT_MAX_INPUT_TOKENS=3200",
        "CHAT_MAX_INPUT_TOKENS=3900",
    ).replace(
        "CHAT_TOTAL_TIMEOUT_SECONDS=150",
        "CHAT_TOTAL_TIMEOUT_SECONDS=15",
    )

    with pytest.raises(DeployEnvironmentError) as captured:
        validate_env_file(write_env(tmp_path / ".env", invalid))

    message = str(captured.value)
    assert "CHAT_MAX_INPUT_TOKENS" in message
    assert "OLLAMA_CONTEXT_LENGTH" in message
    assert "CHAT_QUEUE_TIMEOUT_SECONDS" in message
    assert "CHAT_TOTAL_TIMEOUT_SECONDS" in message


@pytest.mark.parametrize(
    ("variable", "configured", "unexpected"),
    [
        # OLLAMA_MODEL/OLLAMA_EXPECTED_MODEL_DIGEST/OLLAMA_EXPECTED_QUANTIZATION
        # are intentionally NOT in CANONICAL_VALUES: validate_deploy_env.py
        # only checks their *format* (a syntactically valid digest/
        # quantization string), not a pinned value — that identity pin is
        # deploy/gpu/runtime_contract.py's job (APPROVED_MODEL/_DIGEST/
        # _QUANTIZATION, exercised by test_gpu_runtime_bootstrap.py), a
        # separate, fail-closed layer at GPU release time.
        ("RAG_SCHEMA_VERSION", "hemovet-rag-v2", "hemovet-rag-v1"),
        (
            "RAG_EMBEDDING_MODEL",
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            "sentence-transformers/all-MiniLM-L6-v2",
        ),
        ("RAG_EMBEDDING_DIMENSION", "384", "768"),
        ("CHAT_SESSION_TTL_SECONDS", "3600", "2592000"),
    ],
)
def test_noncanonical_production_runtime_is_rejected(
    tmp_path: Path,
    variable: str,
    configured: str,
    unexpected: str,
) -> None:
    # OLLAMA_CONTEXT_LENGTH, OLLAMA_NUM_PREDICT, RAG_TOP_K and
    # CHAT_MAX_CONCURRENT_GENERATIONS are validated by range + cross-field
    # arithmetic fit (see validate_deploy_env.py), not pinned to one
    # canonical value — a within-range change to any of them is legitimate
    # operational tuning, not a "noncanonical runtime" rejection case.
    invalid = VALID_ENV.replace(
        f"{variable}={configured}",
        f"{variable}={unexpected}",
    )

    with pytest.raises(DeployEnvironmentError) as captured:
        validate_env_file(write_env(tmp_path / ".env", invalid))

    assert variable in str(captured.value)


@pytest.mark.parametrize(
    "variable",
    [
        "RAG_EMBEDDING_MODEL",
        "RAG_EMBEDDING_DIMENSION",
        "RAG_TOP_K",
    ],
)
def test_rag_runtime_identity_is_required(tmp_path: Path, variable: str) -> None:
    lines = [
        line for line in VALID_ENV.splitlines() if not line.startswith(f"{variable}=")
    ]

    with pytest.raises(DeployEnvironmentError) as captured:
        validate_env_file(write_env(tmp_path / ".env", "\n".join(lines)))

    assert variable in str(captured.value)


@pytest.mark.parametrize(
    "collection",
    [
        "hemovet_canine_hematology_v2",
        "hemovet_canine_hematology_v2__0123456789ag",
        "hemovet_canine_hematology_v2__0123456789abcdef",
        "other__0123456789ab",
    ],
)
def test_production_requires_a_promoted_fingerprinted_collection(
    tmp_path: Path,
    collection: str,
) -> None:
    invalid = VALID_ENV.replace(
        "RAG_COLLECTION_NAME=hemovet_canine_hematology_v2__0123456789ab",
        f"RAG_COLLECTION_NAME={collection}",
    )

    with pytest.raises(DeployEnvironmentError, match="RAG_COLLECTION_NAME"):
        validate_env_file(write_env(tmp_path / ".env", invalid))


def test_preflight_and_settings_reject_more_than_one_connect_retry(
    tmp_path: Path,
) -> None:
    invalid = VALID_ENV.replace("OLLAMA_MAX_RETRIES=1", "OLLAMA_MAX_RETRIES=2")

    with pytest.raises(DeployEnvironmentError, match="OLLAMA_MAX_RETRIES"):
        validate_env_file(write_env(tmp_path / ".env", invalid))


def test_a_warmup_timeout_shorter_than_a_cold_load_is_rejected(tmp_path: Path) -> None:
    """The value that shipped to production, refused before it can ship again.

    Measured on 2026-08-06: the model takes 79 s to load cold, and with
    OLLAMA_WARMUP_TIMEOUT_SECONDS=20 the backend gave the warmup up as failed
    while the load was proceeding normally, published LLM_PROVIDER_UNAVAILABLE
    and the frontend disabled the chat. It happens on any restart of the GPU
    VM, with nobody having touched anything — so the deploy has to refuse the
    value rather than record the preference somewhere.
    """

    invalid = VALID_ENV.replace(
        "OLLAMA_WARMUP_TIMEOUT_SECONDS=120", "OLLAMA_WARMUP_TIMEOUT_SECONDS=20"
    )

    with pytest.raises(
        DeployEnvironmentError, match="OLLAMA_WARMUP_TIMEOUT_SECONDS"
    ):
        validate_env_file(write_env(tmp_path / ".env", invalid))
