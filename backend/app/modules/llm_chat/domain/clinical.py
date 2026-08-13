from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from decimal import Decimal
import hashlib
import json
from typing import Any, Literal


ClinicalFlag = Literal["low", "normal", "high", "critical", "unknown"]
TruthState = Literal[
    "true",
    "false",
    "unknown",
    "insufficient_data",
    "not_applicable",
]
ReferenceOrigin = Literal[
    "laboratory",
    "validated_catalog",
    "system_default_legacy",
    "unknown",
]

_PARAMETER_COLUMNS = (
    "canonical_name",
    "display_name",
    "original_name",
    "value",
    "unit",
    "reference_min",
    "reference_max",
    "flag",
    "reference_origin",
    "recorded_flag",
    "extraction_confidence",
    "notes",
    "flag_label",
    "fact_id",
)
_QUALITATIVE_PARAMETER_COLUMNS = (
    "canonical_name",
    "display_name",
    "flag",
    "flag_label",
    "fact_id",
)


@dataclass(frozen=True, slots=True)
class PatientContext:
    pet_id: str
    name: str
    species: str = "canine"
    breed: str | None = None
    sex: str | None = None
    age_years: int | None = None
    birth_year: int | None = None
    weight_kg: float | None = None
    notes: str | None = None
    # Populated only when the owner has consented to sharing an approximate
    # residence zone (see repository ``_patient``). Exact coordinates
    # (``residence_lat``/``residence_lng``) are never carried into the chat
    # domain model, consented or not.
    residence_zone_code: str | None = None
    residence_label: str | None = None

    def prompt_dict(self) -> dict[str, Any]:
        return _without_none(
            {
                "pet_id": self.pet_id,
                "name": self.name,
                "species": self.species,
                "breed": self.breed,
                "sex": self.sex,
                "age_years": self.age_years,
                "birth_year": self.birth_year,
                "weight_kg": self.weight_kg,
                "notes": self.notes,
                "residence_zone_code": self.residence_zone_code,
                "residence_label": self.residence_label,
            }
        )

    def public_dict(self) -> dict[str, Any]:
        # The original four fields stay unconditionally present (including
        # explicit ``null``) for frontend compatibility; the fields added for
        # the general-mode profile and ContextBundle are additive and only
        # appear when known, so existing consumers see no shape change.
        payload: dict[str, Any] = {
            "name": self.name,
            "species": self.species,
            "breed": self.breed,
            "sex": self.sex,
            "age_years": self.age_years,
        }
        payload.update(
            _without_none(
                {
                    "birth_year": self.birth_year,
                    "weight_kg": self.weight_kg,
                    "notes": self.notes,
                    "residence_zone_code": self.residence_zone_code,
                    "residence_label": self.residence_label,
                }
            )
        )
        return payload


@dataclass(frozen=True, slots=True)
class HemogramParameter:
    canonical_name: str
    display_name: str
    original_name: str
    value: Decimal
    value_text: str
    unit: str | None
    reference_min: Decimal | None
    reference_max: Decimal | None
    flag: ClinicalFlag
    recorded_flag: str | None = None
    reference_origin: ReferenceOrigin = "unknown"
    extraction_confidence: float | None = None
    notes: str | None = None

    def prompt_dict(self) -> dict[str, Any]:
        # Keep every clinically relevant value while avoiding repeated labels
        # and null provenance fields. A full CBC otherwise becomes larger than
        # the local model's context before the user question is even added.
        payload: dict[str, Any] = {
            "canonical_name": self.canonical_name,
            "value": self.value_text,
            "unit": self.unit,
            "reference_min": _decimal_text(self.reference_min),
            "reference_max": _decimal_text(self.reference_max),
            "flag": self.flag,
            "reference_origin": self.reference_origin,
        }
        if self.display_name != self.canonical_name:
            payload["display_name"] = self.display_name
        if self.original_name not in {self.canonical_name, self.display_name}:
            payload["original_name"] = self.original_name
        if self.recorded_flag and self.recorded_flag != self.flag:
            payload["recorded_flag"] = self.recorded_flag
        if self.extraction_confidence is not None:
            payload["extraction_confidence"] = self.extraction_confidence
        if self.notes:
            payload["notes"] = self.notes
        return _without_none(payload)

    def prompt_row(self, *, fact_id: str = "") -> list[Any]:
        """Compact, schema-addressable representation for the model prompt."""
        return [
            self.canonical_name,
            self.display_name if self.display_name != self.canonical_name else "",
            (
                self.original_name
                if self.original_name not in {self.canonical_name, self.display_name}
                else ""
            ),
            self.value_text,
            self.unit or "",
            _decimal_text(self.reference_min) or "",
            _decimal_text(self.reference_max) or "",
            self.flag,
            self.reference_origin,
            self.recorded_flag if self.recorded_flag != self.flag else "",
            self.extraction_confidence
            if self.extraction_confidence is not None
            else "",
            self.notes or "",
            clinical_flag_label(self.flag),
            fact_id,
        ]

    def qualitative_prompt_row(self, *, fact_id: str = "") -> list[str]:
        """Patient-safe view for intents that do not need measurements."""

        return [
            self.canonical_name,
            self.display_name,
            self.flag,
            clinical_flag_label(self.flag),
            fact_id,
        ]


@dataclass(frozen=True, slots=True)
class HemogramStudy:
    analysis_id: str
    study_key: str
    date: str
    label: str
    laboratory: str | None
    parameters: tuple[HemogramParameter, ...]
    pet_id: str | None = None
    analyzer: str | None = None
    date_origin: str = "unknown"
    observations: tuple[str, ...] = ()
    quality_flags: tuple[str, ...] = ()
    extraction_confidence: float | None = None
    data_origin: str = "analysis_database"
    source_revision: str = "unknown"
    classifier_outcome: dict[str, Any] | None = None

    def prompt_dict(
        self,
        *,
        relevant_parameters: set[str] | None = None,
        include_exact_measurements: bool = True,
    ) -> dict[str, Any]:
        parameters = (
            tuple(
                parameter
                for parameter in self.parameters
                if parameter.canonical_name in relevant_parameters
            )
            if relevant_parameters is not None
            else self.parameters
        )
        return _without_none(
            {
                "pet_id": self.pet_id,
                "analysis_id": self.analysis_id,
                "study_key": self.study_key,
                "date": self.date,
                "date_origin": self.date_origin,
                "label": self.label,
                "laboratory": self.laboratory,
                "analyzer": self.analyzer,
                # A column schema plus rows is equivalent to an object per value but
                # avoids repeating a dozen JSON keys for every CBC parameter.
                "parameter_columns": list(
                    _PARAMETER_COLUMNS
                    if include_exact_measurements
                    else _QUALITATIVE_PARAMETER_COLUMNS
                ),
                "parameters": [
                    (
                        parameter.prompt_row(
                            fact_id=clinical_fact_id(
                                self.analysis_id,
                                parameter.canonical_name,
                            )
                        )
                        if include_exact_measurements
                        else parameter.qualitative_prompt_row(
                            fact_id=clinical_fact_id(
                                self.analysis_id,
                                parameter.canonical_name,
                            )
                        )
                    )
                    for parameter in parameters
                ],
                "observations": list(self.observations) or None,
                "quality_flags": list(self.quality_flags) or None,
                "extraction_confidence": self.extraction_confidence,
                "data_origin": self.data_origin,
                "source_revision": self.source_revision,
                "classifier_outcome": self.classifier_outcome,
            }
        )

    def compact_history_prompt_dict(
        self,
        *,
        relevant_parameters: set[str] | None = None,
        include_exact_measurements: bool = True,
    ) -> dict[str, Any]:
        """Return one longitudinal study without repeated prompt metadata.

        Patient identity, the row schema and derived comparisons are carried by
        the surrounding history payload. The complete study remains available
        in the authorized snapshot and persisted audit metadata.
        """

        parameters = (
            tuple(
                parameter
                for parameter in self.parameters
                if parameter.canonical_name in relevant_parameters
            )
            if relevant_parameters is not None
            else self.parameters
        )
        return _without_none(
            {
                "analysis_id": self.analysis_id,
                "study_key": self.study_key,
                "date": self.date,
                "date_origin": self.date_origin,
                "laboratory": self.laboratory,
                "analyzer": self.analyzer,
                "parameters": [
                    (
                        parameter.prompt_row(
                            fact_id=clinical_fact_id(
                                self.analysis_id,
                                parameter.canonical_name,
                            )
                        )
                        if include_exact_measurements
                        else parameter.qualitative_prompt_row(
                            fact_id=clinical_fact_id(
                                self.analysis_id,
                                parameter.canonical_name,
                            )
                        )
                    )
                    for parameter in parameters
                ],
                "data_origin": self.data_origin,
                "source_revision": self.source_revision,
            }
        )


@dataclass(frozen=True, slots=True, order=True)
class ClinicalFactKey:
    """Unambiguous identity for one parameter in one authorized study."""

    analysis_id: str
    parameter_code: str

    def __post_init__(self) -> None:
        analysis_id = self.analysis_id.strip()
        parameter_code = self.parameter_code.strip().upper()
        if not analysis_id or not parameter_code:
            raise ValueError("clinical_fact_key_requires_analysis_and_parameter")
        object.__setattr__(self, "analysis_id", analysis_id)
        object.__setattr__(self, "parameter_code", parameter_code)

    @property
    def fact_id(self) -> str:
        return clinical_fact_id(self.analysis_id, self.parameter_code)


@dataclass(frozen=True, slots=True)
class VerifiedFactProvenance:
    """Auditable origin for a patient fact without relying on chat history."""

    pet_id: str | None
    analysis_id: str
    field: str
    study_date: str
    date_origin: str = "unknown"
    laboratory: str | None = None
    analyzer: str | None = None
    data_origin: str = "analysis_database"
    source_revision: str = "unknown"

    def as_dict(self) -> dict[str, Any]:
        return _without_none(
            {
                "pet_id": self.pet_id,
                "analysis_id": self.analysis_id,
                "field": self.field,
                "study_date": self.study_date,
                "date_origin": self.date_origin,
                "laboratory": self.laboratory,
                "analyzer": self.analyzer,
                "data_origin": self.data_origin,
                "source_revision": self.source_revision,
            }
        )


@dataclass(frozen=True, slots=True)
class ClinicalParameter:
    """Patient fact with its temporal identity attached.

    ``HemogramParameter`` remains the compact persistence/prompt DTO used by the
    current adapters.  This value object is the authorization and validation
    representation: a value can never exist without the study that produced it.
    """

    analysis_id: str
    study_date: str
    code: str
    canonical_name: str
    display_name: str
    value: Decimal
    value_text: str
    unit: str | None
    reference_min: Decimal | None
    reference_max: Decimal | None
    status: ClinicalFlag
    aliases: tuple[str, ...] = ()
    pet_id: str | None = None
    date_origin: str = "unknown"
    laboratory: str | None = None
    analyzer: str | None = None
    data_origin: str = "analysis_database"
    source_revision: str = "unknown"

    def __post_init__(self) -> None:
        analysis_id = self.analysis_id.strip()
        code = self.code.strip().upper()
        if not analysis_id or not self.study_date.strip() or not code:
            raise ValueError("clinical_parameter_requires_study_identity")
        aliases = tuple(
            dict.fromkeys(
                item.strip()
                for item in (
                    code,
                    self.canonical_name,
                    self.display_name,
                    *self.aliases,
                )
                if item and item.strip()
            )
        )
        object.__setattr__(self, "analysis_id", analysis_id)
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "aliases", aliases)

    @property
    def key(self) -> ClinicalFactKey:
        return ClinicalFactKey(self.analysis_id, self.code)

    @property
    def fact_id(self) -> str:
        return self.key.fact_id

    @property
    def provenance(self) -> VerifiedFactProvenance:
        return VerifiedFactProvenance(
            pet_id=self.pet_id,
            analysis_id=self.analysis_id,
            field=self.code,
            study_date=self.study_date,
            date_origin=self.date_origin,
            laboratory=self.laboratory,
            analyzer=self.analyzer,
            data_origin=self.data_origin,
            source_revision=self.source_revision,
        )

    def validation_dict(self) -> dict[str, Any]:
        return {
            "fact_type": "lab_value",
            "fact_id": self.fact_id,
            "pet_id": self.pet_id,
            "analysis_id": self.analysis_id,
            "analysis_date": self.study_date,
            "date_origin": self.date_origin,
            "code": self.code,
            "canonical_name": self.canonical_name,
            "parameter": self.canonical_name,
            "label": self.display_name,
            "display_name": self.display_name,
            "aliases": list(self.aliases),
            "value": self.value_text,
            "value_text": self.value_text,
            "unit": self.unit,
            "reference_low": _decimal_text(self.reference_min),
            "reference_high": _decimal_text(self.reference_max),
            "reference_min": _decimal_text(self.reference_min),
            "reference_max": _decimal_text(self.reference_max),
            "ref_min": _decimal_text(self.reference_min),
            "ref_max": _decimal_text(self.reference_max),
            "status": self.status,
            "flag": self.status,
            "status_label": clinical_flag_label(self.status),
            "laboratory": self.laboratory,
            "analyzer": self.analyzer,
            "data_origin": self.data_origin,
            "source_revision": self.source_revision,
            "provenance": self.provenance.as_dict(),
        }

    @classmethod
    def from_hemogram(
        cls,
        parameter: HemogramParameter,
        *,
        analysis_id: str,
        study_date: str,
        pet_id: str | None = None,
        date_origin: str = "unknown",
        laboratory: str | None = None,
        analyzer: str | None = None,
        data_origin: str = "analysis_database",
        source_revision: str = "unknown",
    ) -> ClinicalParameter:
        return cls(
            analysis_id=analysis_id,
            study_date=study_date,
            code=parameter.canonical_name,
            canonical_name=parameter.canonical_name,
            display_name=parameter.display_name,
            value=parameter.value,
            value_text=parameter.value_text,
            unit=parameter.unit,
            reference_min=parameter.reference_min,
            reference_max=parameter.reference_max,
            status=parameter.flag,
            aliases=(parameter.original_name,),
            pet_id=pet_id,
            date_origin=date_origin,
            laboratory=laboratory,
            analyzer=analyzer,
            data_origin=data_origin,
            source_revision=source_revision,
        )


@dataclass(frozen=True, slots=True)
class VerifiedFact:
    """A structured patient measurement authorized for prompt and validation."""

    fact_id: str
    code: str
    display_name: str
    value: Decimal
    value_text: str
    unit: str | None
    reference_low: Decimal | None
    reference_high: Decimal | None
    status: ClinicalFlag
    provenance: VerifiedFactProvenance

    @classmethod
    def from_parameter(cls, parameter: ClinicalParameter) -> VerifiedFact:
        return cls(
            fact_id=parameter.fact_id,
            code=parameter.code,
            display_name=parameter.display_name,
            value=parameter.value,
            value_text=parameter.value_text,
            unit=parameter.unit,
            reference_low=parameter.reference_min,
            reference_high=parameter.reference_max,
            status=parameter.status,
            provenance=parameter.provenance,
        )

    def validation_dict(self) -> dict[str, Any]:
        return {
            "fact_type": "lab_value",
            "fact_id": self.fact_id,
            "code": self.code,
            "parameter": self.code,
            "label": self.display_name,
            "value": self.value_text,
            "unit": self.unit,
            "reference_low": _decimal_text(self.reference_low),
            "reference_high": _decimal_text(self.reference_high),
            "status": self.status,
            "status_label": clinical_flag_label(self.status),
            "provenance": self.provenance.as_dict(),
            **self.provenance.as_dict(),
        }


@dataclass(frozen=True, slots=True)
class ClinicalStudy:
    analysis_id: str
    study_key: str
    study_date: str
    parameters: tuple[ClinicalParameter, ...]
    pet_id: str | None = None
    date_origin: str = "unknown"
    laboratory: str | None = None
    analyzer: str | None = None
    data_origin: str = "analysis_database"
    source_revision: str = "unknown"
    label: str = "Hemograma"
    classifier_outcome: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        analysis_id = self.analysis_id.strip()
        if not analysis_id or not self.study_key.strip() or not self.study_date.strip():
            raise ValueError("clinical_study_requires_identity_and_date")
        if any(
            parameter.analysis_id != analysis_id
            or parameter.study_date != self.study_date
            or parameter.date_origin != self.date_origin
            or (
                self.pet_id is not None
                and parameter.pet_id is not None
                and parameter.pet_id != self.pet_id
            )
            for parameter in self.parameters
        ):
            raise ValueError("clinical_study_parameter_identity_mismatch")
        codes = [parameter.code for parameter in self.parameters]
        if len(codes) != len(set(codes)):
            raise ValueError("clinical_study_duplicate_parameter")
        object.__setattr__(self, "analysis_id", analysis_id)

    @classmethod
    def from_hemogram(
        cls,
        study: HemogramStudy,
        *,
        pet_id: str | None = None,
        source_revision: str = "unknown",
    ) -> ClinicalStudy:
        revision = (
            study.source_revision
            if source_revision == "unknown" and study.source_revision
            else source_revision
        )
        return cls(
            analysis_id=study.analysis_id,
            study_key=study.study_key,
            study_date=study.date,
            pet_id=pet_id or study.pet_id,
            date_origin=study.date_origin,
            laboratory=study.laboratory,
            analyzer=study.analyzer,
            data_origin=study.data_origin,
            source_revision=revision,
            label=study.label,
            classifier_outcome=study.classifier_outcome,
            parameters=tuple(
                ClinicalParameter.from_hemogram(
                    parameter,
                    analysis_id=study.analysis_id,
                    study_date=study.date,
                    pet_id=pet_id or study.pet_id,
                    date_origin=study.date_origin,
                    laboratory=study.laboratory,
                    analyzer=study.analyzer,
                    data_origin=study.data_origin,
                    source_revision=revision,
                )
                for parameter in study.parameters
            ),
        )


@dataclass(frozen=True, slots=True)
class ClinicalTokenBudgetMetadata:
    maximum_tokens: int = 0
    materialized_tokens: int = 0
    omitted_fact_count: int = 0
    history_study_count: int = 0


@dataclass(frozen=True, slots=True)
class ClinicalContextSnapshot:
    """Immutable authorization boundary shared by prompt and validation.

    Prioritization and materialization are represented as fact keys.  They may
    narrow the prompt, but can never shrink ``authorized_studies`` or the facts
    available to the validator.
    """

    mode: Literal["general", "selected_hemogram", "hemogram_history"]
    owner_id: str
    conversation_id: str
    context_revision: int
    generated_at: datetime
    pet_id: str | None = None
    selected_analysis_id: str | None = None
    authorized_studies: tuple[ClinicalStudy, ...] = ()
    prioritized_fact_keys: tuple[ClinicalFactKey, ...] = ()
    materialized_fact_keys: tuple[ClinicalFactKey, ...] = ()
    rag_evidence: tuple[Any, ...] = ()
    conversation_memory: ConversationMemory | None = None
    token_budget_metadata: ClinicalTokenBudgetMetadata = field(
        default_factory=ClinicalTokenBudgetMetadata
    )
    context_fingerprint: str = ""

    def __post_init__(self) -> None:
        if not self.owner_id.strip() or not self.conversation_id.strip():
            raise ValueError("clinical_snapshot_requires_owner_and_conversation")
        if self.context_revision < 1:
            raise ValueError("clinical_snapshot_revision_must_be_positive")
        generated_at = self.generated_at
        if generated_at.tzinfo is None:
            generated_at = generated_at.replace(tzinfo=UTC)
            object.__setattr__(self, "generated_at", generated_at)

        study_ids = [study.analysis_id for study in self.authorized_studies]
        if len(study_ids) != len(set(study_ids)):
            raise ValueError("clinical_snapshot_duplicate_study")
        if self.mode == "general":
            if self.pet_id or self.selected_analysis_id or self.authorized_studies:
                raise ValueError("general_snapshot_cannot_authorize_clinical_data")
        elif self.mode == "selected_hemogram":
            if not self.pet_id or not self.selected_analysis_id:
                raise ValueError("selected_snapshot_requires_pet_and_analysis")
            if study_ids != [self.selected_analysis_id]:
                raise ValueError("selected_snapshot_must_authorize_only_selected_study")
        elif self.mode == "hemogram_history":
            if not self.pet_id or self.selected_analysis_id is not None:
                raise ValueError(
                    "history_snapshot_requires_pet_without_selected_analysis"
                )
        else:  # pragma: no cover - protected by the Literal type at static boundaries.
            raise ValueError("unsupported_clinical_snapshot_mode")
        if any(
            study.pet_id is not None and study.pet_id != self.pet_id
            for study in self.authorized_studies
        ):
            raise ValueError("clinical_snapshot_patient_identity_mismatch")

        authorized = self.authorized_fact_keys
        if not set(self.prioritized_fact_keys).issubset(authorized):
            raise ValueError("prioritized_facts_must_be_authorized")
        if not set(self.materialized_fact_keys).issubset(authorized):
            raise ValueError("materialized_facts_must_be_authorized")
        fingerprint = self.context_fingerprint or clinical_context_fingerprint(
            self.authorized_studies,
            mode=self.mode,
            pet_id=self.pet_id,
            selected_analysis_id=self.selected_analysis_id,
        )
        object.__setattr__(self, "context_fingerprint", fingerprint)

    @property
    def authorized_fact_keys(self) -> frozenset[ClinicalFactKey]:
        return frozenset(
            parameter.key
            for study in self.authorized_studies
            for parameter in study.parameters
        )

    @property
    def authorized_parameters(self) -> tuple[ClinicalParameter, ...]:
        return tuple(
            parameter
            for study in self.authorized_studies
            for parameter in study.parameters
        )

    def prioritized_parameters(self) -> tuple[ClinicalParameter, ...]:
        keys = set(self.prioritized_fact_keys)
        return tuple(
            parameter
            for parameter in self.authorized_parameters
            if parameter.key in keys
        )

    def materialized_parameters(self) -> tuple[ClinicalParameter, ...]:
        keys = set(self.materialized_fact_keys)
        return tuple(
            parameter
            for parameter in self.authorized_parameters
            if parameter.key in keys
        )

    def with_materialization(
        self,
        *,
        prioritized_fact_keys: tuple[ClinicalFactKey, ...],
        materialized_fact_keys: tuple[ClinicalFactKey, ...],
        token_budget_metadata: ClinicalTokenBudgetMetadata,
    ) -> ClinicalContextSnapshot:
        return replace(
            self,
            prioritized_fact_keys=prioritized_fact_keys,
            materialized_fact_keys=materialized_fact_keys,
            token_budget_metadata=token_budget_metadata,
        )

    @classmethod
    def from_context(
        cls,
        clinical: ClinicalContext,
        *,
        owner_id: str,
        conversation_id: str,
        context_revision: int,
        generated_at: datetime | None = None,
        source_revision: str = "unknown",
    ) -> ClinicalContextSnapshot:
        if clinical.mode == "selected_hemogram":
            studies = (clinical.selected,) if clinical.selected else ()
        elif clinical.mode == "hemogram_history":
            studies = clinical.history
        else:
            studies = ()
        authorized = tuple(
            ClinicalStudy.from_hemogram(
                study,
                pet_id=clinical.pet_id,
                source_revision=source_revision,
            )
            for study in studies
            if study is not None
        )
        return cls(
            mode=clinical.mode,
            owner_id=owner_id,
            conversation_id=conversation_id,
            context_revision=context_revision,
            generated_at=generated_at or datetime.now(UTC),
            pet_id=clinical.pet_id if clinical.mode != "general" else None,
            selected_analysis_id=(
                clinical.selected.analysis_id
                if clinical.mode == "selected_hemogram" and clinical.selected
                else None
            ),
            authorized_studies=authorized,
        )


def clinical_context_fingerprint(
    studies: tuple[ClinicalStudy, ...],
    *,
    mode: str = "",
    pet_id: str | None = None,
    selected_analysis_id: str | None = None,
) -> str:
    canonical = {
        "mode": mode,
        "pet_id": pet_id,
        "selected_analysis_id": selected_analysis_id,
        "studies": [
            {
                "analysis_id": study.analysis_id,
                "study_key": study.study_key,
                "study_date": study.study_date,
                "date_origin": study.date_origin,
                "pet_id": study.pet_id,
                "laboratory": study.laboratory,
                "analyzer": study.analyzer,
                "data_origin": study.data_origin,
                "source_revision": study.source_revision,
                "classifier_outcome": study.classifier_outcome,
                "parameters": [
                    {
                        "code": parameter.code,
                        "value": format(parameter.value, "f"),
                        "unit": parameter.unit or "",
                        "reference_min": _decimal_text(parameter.reference_min),
                        "reference_max": _decimal_text(parameter.reference_max),
                        "status": parameter.status,
                        "source_revision": parameter.source_revision,
                    }
                    for parameter in sorted(
                        study.parameters, key=lambda item: item.code
                    )
                ],
            }
            for study in sorted(
                studies, key=lambda item: (item.study_date, item.analysis_id)
            )
        ],
    }
    serialized = json.dumps(
        canonical,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ClinicalContext:
    mode: Literal["general", "selected_hemogram", "hemogram_history"]
    patient: PatientContext | None = None
    selected: HemogramStudy | None = None
    history: tuple[HemogramStudy, ...] = ()
    computed_facts: tuple[dict[str, Any], ...] = ()
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        studies = tuple(
            study
            for study in ((self.selected,) if self.selected else self.history)
            if study is not None
        )
        if self.selected and self.history:
            studies = tuple(
                {study.analysis_id: study for study in (self.selected, *self.history)}.values()
            )
        known_pet_ids = {study.pet_id for study in studies if study.pet_id}
        if len(known_pet_ids) > 1:
            raise ValueError("clinical_context_cannot_mix_patients")
        if (
            self.patient is not None
            and known_pet_ids
            and known_pet_ids != {self.patient.pet_id}
        ):
            raise ValueError("clinical_context_patient_identity_mismatch")

    @property
    def pet_id(self) -> str | None:
        return self.patient.pet_id if self.patient else None

    @property
    def analysis_id(self) -> str | None:
        return self.selected.analysis_id if self.selected else None

    @property
    def has_data(self) -> bool:
        return (
            self.selected is not None or bool(self.history) or bool(self.computed_facts)
        )

    def prompt_payload(
        self,
        *,
        relevant_parameters: set[str] | None = None,
        materialized_fact_keys: frozenset[ClinicalFactKey] | None = None,
        include_history: bool = True,
        include_exact_measurements: bool = True,
        compact_history: bool = False,
    ) -> dict[str, Any]:
        if self.mode == "general":
            # General mode never authorizes hemograms (``selected``/``history``
            # stay empty by construction), but an explicitly consented and
            # ownership-verified pet profile is still authorized context: the
            # user asked about their own animal without selecting a study.
            return _without_none(
                {
                    "conversation_mode": "general",
                    "patient": self.patient.prompt_dict() if self.patient else None,
                }
            )
        payload: dict[str, Any] = {
            "conversation_mode": self.mode,
            "patient": self.patient.prompt_dict() if self.patient else None,
        }
        if self.warnings:
            payload["warnings"] = list(self.warnings)
        if self.selected:
            selected_parameters = relevant_parameters
            if materialized_fact_keys is not None:
                selected_parameters = {
                    key.parameter_code
                    for key in materialized_fact_keys
                    if key.analysis_id == self.selected.analysis_id
                }
            payload["selected_hemogram"] = self.selected.prompt_dict(
                relevant_parameters=selected_parameters,
                include_exact_measurements=include_exact_measurements,
            )
        if self.history and include_history:
            # In selected mode the current study is already present above. Only
            # add the other authorized studies so follow-up comparisons remain
            # available without serializing the selected CBC twice.
            history = (
                tuple(
                    item
                    for item in self.history
                    if not self.selected
                    or item.analysis_id != self.selected.analysis_id
                )
                if self.selected
                else self.history
            )
            if history:
                # Every study is narrowed to the parameter being discussed.
                # A complete CBC is serialized only when no parameter was
                # resolved, which is reserved for an explicit whole-study
                # interpretation.
                if compact_history:
                    payload["hemogram_history_parameter_columns"] = list(
                        _PARAMETER_COLUMNS
                        if include_exact_measurements
                        else _QUALITATIVE_PARAMETER_COLUMNS
                    )
                payload["hemogram_history"] = [
                    (
                        item.compact_history_prompt_dict
                        if compact_history
                        else item.prompt_dict
                    )(
                        relevant_parameters=(
                            {
                                key.parameter_code
                                for key in materialized_fact_keys
                                if key.analysis_id == item.analysis_id
                            }
                            if materialized_fact_keys is not None
                            else (
                                {"__study_index_only__"}
                                if self.mode == "selected_hemogram"
                                and not relevant_parameters
                                else relevant_parameters
                            )
                        ),
                        include_exact_measurements=include_exact_measurements,
                    )
                    for item in history
                ]
        if (
            self.mode == "hemogram_history"
            and include_history
            and self.computed_facts
        ):
            selected_codes = relevant_parameters
            if materialized_fact_keys is not None:
                selected_codes = {
                    key.parameter_code for key in materialized_fact_keys
                }
            trends = [
                (
                    _compact_historical_trend(fact)
                    if compact_history
                    else dict(fact)
                )
                for fact in self.computed_facts
                if str(fact.get("fact_type") or "") == "history_parameter"
                and (
                    selected_codes is None
                    or str(fact.get("code") or "") in selected_codes
                )
            ]
            if trends:
                # These values were calculated by the backend. Supplying them
                # explicitly prevents the LLM from recomputing deltas or deciding
                # whether observations are comparable.
                payload["historical_trends"] = trends
        return _without_none(payload)

    def public_payload(self, *, context_revision: int = 1) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "mode": self.mode,
            "revision": context_revision,
            "context_revision": context_revision,
            "history_count": len(self.history),
        }
        if self.patient:
            payload["pet"] = self.patient.public_dict()
        if self.selected:
            payload["selected_hemogram"] = {
                "date": self.selected.date,
                "label": self.selected.label,
            }
        studies = self.history or ((self.selected,) if self.selected else ())
        payload["classification_facts"] = [
            {
                "analysis_id": study.analysis_id,
                "study_key": study.study_key,
                "sample_date": study.date,
                **(
                    study.classifier_outcome
                    or {"classification_status": "LEGACY_INCOMPLETE"}
                ),
            }
            for study in studies
            if study is not None
        ]
        return payload

    def legacy_facts(self) -> list[dict[str, Any]]:
        studies = (self.selected,) if self.selected else self.history
        facts: list[dict[str, Any]] = []
        for study in studies:
            if study is None:
                continue
            for parameter in study.parameters:
                fact = parameter.prompt_dict()
                fact.update(
                    {
                        "fact_id": clinical_fact_id(
                            study.analysis_id,
                            parameter.canonical_name,
                        ),
                        "pet_id": study.pet_id or self.pet_id,
                        "code": parameter.canonical_name,
                        "label": parameter.display_name,
                        "analysis_id": study.analysis_id,
                        "ref_min": _decimal_number(parameter.reference_min),
                        "ref_max": _decimal_number(parameter.reference_max),
                        "status": parameter.flag,
                        "fact_type": "lab_value",
                        "study_key": study.study_key,
                        "analysis_date": study.date,
                        "study_date": study.date,
                        "date_origin": study.date_origin,
                        "source_revision": study.source_revision,
                        "laboratory": study.laboratory,
                        "analyzer": study.analyzer,
                        "data_origin": study.data_origin,
                        "provenance": _without_none(
                            {
                                "pet_id": study.pet_id or self.pet_id,
                                "analysis_id": study.analysis_id,
                                "field": parameter.canonical_name,
                                "study_date": study.date,
                                "date_origin": study.date_origin,
                                "laboratory": study.laboratory,
                                "analyzer": study.analyzer,
                                "data_origin": study.data_origin,
                                "source_revision": study.source_revision,
                            }
                        ),
                        "detail": _detail(parameter),
                    }
                )
                facts.append(fact)
        facts.extend(dict(value) for value in self.computed_facts)
        return facts


@dataclass(frozen=True, slots=True)
class ConversationMemory:
    """Conversational continuity, decoupled from clinical-data authorization.

    ``context_revision`` is the *clinical* context revision: it rotates when
    the authorized PostgreSQL data (hemogram, profile) changes, and it is
    what optimistic-concurrency checks (``expected_context_revision``) key
    on. ``conversation_revision`` is the distinct, stable identity of the
    dialogue itself for this conversation id — it does not rotate when
    clinical data changes, since a new hemogram must never hide or reset the
    prior transcript, summary or active topic of the same authorized
    conversation. There is currently no conversation-reset feature, so it
    stays 1 for the lifetime of a conversation id; the field exists so the
    two concepts are represented distinctly rather than sharing one counter.
    """

    summary: str = ""
    state: dict[str, Any] = field(default_factory=dict)
    recent_messages: tuple[Any, ...] = ()
    context_revision: int = 1
    conversation_revision: int = 1


@dataclass(frozen=True, slots=True)
class ResolvedQuestion:
    original: str
    standalone: str
    is_follow_up: bool
    referenced_parameter: str | None = None
    referenced_topic: str | None = None


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    text = format(value, "f")
    # Trim only fractional zeroes. Stripping the integer representation turned
    # valid ranges such as 150–500 into 15–5 and inverted clinical statuses.
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def clinical_fact_id(analysis_id: str, parameter_code: str) -> str:
    """Return a deterministic opaque identifier for one analysis parameter."""

    key = ClinicalFactKey(analysis_id, parameter_code)
    digest = hashlib.sha256(
        f"clinical-fact-v1\x00{key.analysis_id}\x00{key.parameter_code}".encode()
    ).hexdigest()
    return f"fact_{digest[:24]}"


def clinical_flag_label(flag: str) -> str:
    return {
        "low": "bajo",
        "normal": "normal",
        "high": "alto",
        "critical": "crítico",
        "unknown": "desconocido",
    }.get(flag.strip().casefold(), "desconocido")


def normalize_clinical_unit(unit: str | None) -> str:
    """Canonicalize equivalent CBC unit spellings without converting values."""

    translation = str.maketrans(
        {
            "×": "x",
            "·": "x",
            "µ": "u",
            "μ": "u",
            "⁰": "0",
            "¹": "1",
            "²": "2",
            "³": "3",
            "⁴": "4",
            "⁵": "5",
            "⁶": "6",
            "⁷": "7",
            "⁸": "8",
            "⁹": "9",
        }
    )
    normalized = "".join(
        character
        for character in str(unit or "").casefold().translate(translation)
        if character not in " ^*()"
    )
    if normalized.startswith("x10"):
        normalized = normalized[1:]
    equivalents = {
        "k/ul": "109/l",
        "103/ul": "109/l",
        "m/ul": "1012/l",
        "106/ul": "1012/l",
    }
    return equivalents.get(normalized, normalized)


_COMPACT_HISTORICAL_TREND_FIELDS = (
    "fact_type",
    "code",
    "display_name",
    "occurrences",
    "comparison_valid",
    "comparison_reasons",
    "reason",
    "unit",
    "unit_changed",
    "reference_interval_changed",
    "laboratory_changed",
    "analyzer_changed",
    "direction_from_previous",
    "trend",
)


def _compact_historical_trend(fact: dict[str, Any]) -> dict[str, Any]:
    """Project derived comparison metadata without duplicating study values."""

    return _without_none(
        {
            key: fact[key]
            for key in _COMPACT_HISTORICAL_TREND_FIELDS
            if key in fact
        }
    )


def _without_none(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


def _decimal_number(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def _detail(parameter: HemogramParameter) -> str:
    value = " ".join(item for item in (parameter.value_text, parameter.unit) if item)
    parts = [f"{parameter.display_name}: {value}"]
    if parameter.reference_min is not None or parameter.reference_max is not None:
        low = _decimal_text(parameter.reference_min) or "sin límite inferior"
        high = _decimal_text(parameter.reference_max) or "sin límite superior"
        range_text = f"{low}–{high}"
        if parameter.unit:
            range_text = f"{range_text} {parameter.unit}"
        parts.append(f"rango de referencia {range_text}")
    parts.append(f"clasificación {parameter.flag}")
    parts.append(f"origen del rango {parameter.reference_origin}")
    return "; ".join(parts)
