from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.availability import AVAILABILITY_CONTRACT_VERSION
from app.modules.llm_chat.domain.provider_contract import (
    LLM_PROVIDER_CONTRACT_VERSION,
)


RELEASE_MANIFEST_CONTRACT_VERSION = "hemovet.release/v1"
_SHA256_PATTERN = r"^sha256:[0-9a-f]{64}$"
_RAW_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_GITHUB_SHA_PATTERN = r"^[0-9a-f]{40}$"
_IMAGE_REFERENCE_PATTERN = r"^[^\s@]+@sha256:[0-9a-f]{64}$"


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ImmutableImage(ContractModel):
    reference: str = Field(pattern=_IMAGE_REFERENCE_PATTERN)
    digest: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_reference_digest(self) -> "ImmutableImage":
        referenced_digest = self.reference.rsplit("@", maxsplit=1)[-1]
        if referenced_digest != self.digest:
            raise ValueError("image reference and digest must identify the same blob")
        return self


class ReleaseSource(ContractModel):
    github_sha: str = Field(pattern=_GITHUB_SHA_PATTERN)
    repository: str = Field(
        pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$",
        min_length=3,
        max_length=200,
    )
    workflow_run_id: int = Field(ge=1)
    workflow_run_attempt: int = Field(ge=1)
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("release creation timestamp must include a timezone")
        return value


class ApplicationRelease(ContractModel):
    revision: str = Field(pattern=_GITHUB_SHA_PATTERN)
    backend: ImmutableImage
    frontend: ImmutableImage
    configuration_digest: str = Field(pattern=_SHA256_PATTERN)
    caddy_configuration_digest: str = Field(pattern=_SHA256_PATTERN)
    # Condicion de MEDICION del chat, no ajuste de producto.
    #
    # Vive aqui y no en el secreto `PRODUCTION_ENV_B64` por un motivo de
    # categoria, no de comodidad: un booleano que decide si el servidor escribe
    # las cifras de la historia clinica **no es un secreto**. No es una
    # credencial, no se rota, su divulgacion no compromete nada, y su valor
    # **debe ser legible para un auditor**. Guardarlo en un almacen de secretos
    # le da las propiedades equivocadas —rotacion silenciosa, opacidad, sin
    # historial legible— y le quita las necesarias: revision, atribucion y
    # reproducibilidad.
    #
    # Al vivir en el manifiesto queda cubierto por el MISMO `sha256` que ya
    # protege el resto de la configuracion, asi que la cadena de confianza no se
    # rodea: se le anade una entrada. Y el commit que lo cambia es el registro
    # de cuando entro en vigor.
    #
    # Por defecto APAGADO. Un ajuste que cambia lo que el sistema escribe en la
    # historia clinica no se activa por omision en ninguna rama.
    #
    # Campo ADITIVO y opcional: el contrato sigue en `hemovet.release/v1` a
    # proposito. Subir a v2 invalidaria el `Literal` de todos los manifiestos ya
    # emitidos —incluidos los de rollback—, que es un coste real a cambio de
    # nada: un campo con valor por defecto es compatible hacia atras.
    chat_server_writes: bool = False


class ModelRelease(ContractModel):
    name: str = Field(min_length=3, max_length=200)
    digest: str = Field(pattern=_SHA256_PATTERN)
    quantization: str = Field(pattern=r"^[A-Za-z0-9_]{2,32}$")

    @field_validator("name")
    @classmethod
    def reject_mutable_model_tag(cls, value: str) -> str:
        normalized = value.strip()
        if normalized.casefold().endswith(":latest") or ":" not in normalized:
            raise ValueError("model name must use an explicit non-latest tag")
        return normalized


class GpuRuntimeRelease(ContractModel):
    revision: str = Field(pattern=_GITHUB_SHA_PATTERN)
    runtime: ImmutableImage
    startup_bundle_digest: str = Field(pattern=_SHA256_PATTERN)
    startup_contract_version: str = Field(min_length=3, max_length=100)
    model: ModelRelease
    apply_on: Literal["next_boot"]
    initial_validation_state: Literal["pending_boot_validation"]
    update_while_running: Literal[False]


class RagRelease(ContractModel):
    required: bool
    collection_name: str = Field(
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$"
    )
    corpus_revision: str = Field(min_length=1, max_length=200)
    index_fingerprint: str = Field(pattern=_RAW_SHA256_PATTERN)
    schema_version: str = Field(min_length=1, max_length=100)
    embedding_model: str = Field(min_length=1, max_length=300)
    embedding_revision: str = Field(min_length=1, max_length=200)


class ReleaseContractVersions(ContractModel):
    release_manifest: Literal[RELEASE_MANIFEST_CONTRACT_VERSION]
    availability: Literal[AVAILABILITY_CONTRACT_VERSION]
    llm_provider: Literal[LLM_PROVIDER_CONTRACT_VERSION]


class ReleaseManifest(ContractModel):
    schema_version: Literal[RELEASE_MANIFEST_CONTRACT_VERSION]
    release_id: str = Field(pattern=_GITHUB_SHA_PATTERN)
    source: ReleaseSource
    application: ApplicationRelease
    gpu_runtime: GpuRuntimeRelease
    rag: RagRelease
    contracts: ReleaseContractVersions

    @model_validator(mode="after")
    def require_one_source_revision(self) -> "ReleaseManifest":
        expected = self.source.github_sha
        revisions = {
            self.release_id,
            self.application.revision,
            self.gpu_runtime.revision,
        }
        if revisions != {expected}:
            raise ValueError("all release components must reference source.github_sha")
        return self


def load_release_manifest(path: str | Path) -> ReleaseManifest:
    manifest_path = Path(path)
    raw = manifest_path.read_text(encoding="utf-8")
    return ReleaseManifest.model_validate_json(raw)


def release_manifest_json_schema() -> dict[str, object]:
    return ReleaseManifest.model_json_schema(
        ref_template="#/$defs/{model}",
        mode="validation",
    )


def canonical_release_manifest(manifest: ReleaseManifest) -> str:
    """Stable representation used when publishing or signing the manifest."""

    return json.dumps(
        manifest.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
