from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.release_manifest import ReleaseManifest


ARTIFACT_SET_CONTRACT_VERSION = "hemovet.artifacts/v1"
REQUIRED_IMAGE_PACKAGES = frozenset({"backend", "frontend", "ollama-runtime"})
_GITHUB_SHA_PATTERN = r"^[0-9a-f]{40}$"
_SHA256_PATTERN = r"^sha256:[0-9a-f]{64}$"
_REGISTRY_REPOSITORY_PATTERN = (
    r"^[a-z0-9-]+-docker\.pkg\.dev/[a-z][a-z0-9-]{4,62}/[a-z][a-z0-9._-]{0,62}$"
)
_TAGGED_REFERENCE_PATTERN = r"^[^\s@:]+(?:/[^\s@:]+)+:sha-[0-9a-f]{40}$"
_CANONICAL_REFERENCE_PATTERN = r"^[^\s@]+@sha256:[0-9a-f]{64}$"


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ArtifactSource(ContractModel):
    github_sha: str = Field(pattern=_GITHUB_SHA_PATTERN)
    repository: str = Field(
        pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$",
        min_length=3,
        max_length=200,
    )
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("artifact publication timestamp must include a timezone")
        return value


class PublishedImage(ContractModel):
    package: Literal["backend", "frontend", "ollama-runtime"]
    source_revision: str = Field(pattern=_GITHUB_SHA_PATTERN)
    tag: str = Field(pattern=r"^sha-[0-9a-f]{40}$")
    tagged_reference: str = Field(pattern=_TAGGED_REFERENCE_PATTERN)
    canonical_reference: str = Field(pattern=_CANONICAL_REFERENCE_PATTERN)
    digest: str = Field(pattern=_SHA256_PATTERN)
    upstream_reference: str | None = Field(default=None, min_length=1, max_length=500)

    @field_validator(
        "tagged_reference",
        "canonical_reference",
        "upstream_reference",
        mode="before",
    )
    @classmethod
    def reject_latest_reference(cls, value: object) -> object:
        if isinstance(value, str) and ":latest" in value.casefold():
            raise ValueError("latest is forbidden in an immutable artifact set")
        return value

    @model_validator(mode="after")
    def require_matching_digest(self) -> "PublishedImage":
        referenced_digest = self.canonical_reference.rsplit("@", maxsplit=1)[-1]
        if referenced_digest != self.digest:
            raise ValueError("canonical image reference and digest must match")
        return self


class ArtifactSet(ContractModel):
    schema_version: Literal[ARTIFACT_SET_CONTRACT_VERSION]
    release_id: str = Field(pattern=_GITHUB_SHA_PATTERN)
    source: ArtifactSource
    registry_repository: str = Field(pattern=_REGISTRY_REPOSITORY_PATTERN)
    images: tuple[PublishedImage, ...] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def require_one_immutable_revision(self) -> "ArtifactSet":
        packages = [image.package for image in self.images]
        if set(packages) != REQUIRED_IMAGE_PACKAGES or len(set(packages)) != len(
            packages
        ):
            raise ValueError(
                "artifact set must contain backend, frontend and ollama-runtime once"
            )

        expected_sha = self.source.github_sha
        if self.release_id != expected_sha:
            raise ValueError("release_id must match source.github_sha")

        for image in self.images:
            expected_tag = f"sha-{expected_sha}"
            expected_tagged_reference = (
                f"{self.registry_repository}/{image.package}:{expected_tag}"
            )
            expected_canonical_reference = (
                f"{self.registry_repository}/{image.package}@{image.digest}"
            )
            if image.source_revision != expected_sha:
                raise ValueError("every image must use source.github_sha")
            if image.tag != expected_tag:
                raise ValueError("every image tag must be sha-<source.github_sha>")
            if image.tagged_reference != expected_tagged_reference:
                raise ValueError("tagged image reference does not match its package")
            if image.canonical_reference != expected_canonical_reference:
                raise ValueError("canonical image reference does not match its package")
        return self

    def image(self, package: str) -> PublishedImage:
        for image in self.images:
            if image.package == package:
                return image
        raise KeyError(package)


def load_artifact_set(path: str | Path) -> ArtifactSet:
    return ArtifactSet.model_validate_json(Path(path).read_text(encoding="utf-8"))


def canonical_artifact_set(artifact_set: ArtifactSet) -> str:
    return json.dumps(
        artifact_set.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def bind_release_artifacts(
    manifest: ReleaseManifest,
    artifact_set: ArtifactSet,
) -> ReleaseManifest:
    """Return a validated release manifest bound to published OCI digests.

    Model, RAG, configuration and startup identities remain mandatory inputs in
    the source manifest. This function only replaces the three OCI references;
    it never manufactures the remaining release evidence.
    """

    if manifest.source.github_sha != artifact_set.source.github_sha:
        raise ValueError("release manifest and artifact set use different revisions")

    payload = manifest.model_dump(mode="json")
    backend = artifact_set.image("backend")
    frontend = artifact_set.image("frontend")
    runtime = artifact_set.image("ollama-runtime")
    payload["application"]["backend"] = {
        "reference": backend.canonical_reference,
        "digest": backend.digest,
    }
    payload["application"]["frontend"] = {
        "reference": frontend.canonical_reference,
        "digest": frontend.digest,
    }
    payload["gpu_runtime"]["runtime"] = {
        "reference": runtime.canonical_reference,
        "digest": runtime.digest,
    }
    return ReleaseManifest.model_validate(payload)
