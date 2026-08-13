from __future__ import annotations

from enum import StrEnum
import json
import logging
import re
from typing import Iterable, Literal, Mapping
import unicodedata

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.modules.llm_chat.domain.ports.entailment import ClaimEntailmentPort

logger = logging.getLogger("uvicorn.error.hemovet.llm_chat")


class ClaimType(StrEnum):
    """Canonical claim taxonomy (etapa 4).

    Reconciled with the plan's minimum vocabulary rather than duplicated:
    ``PATIENT_FACT``/``PATIENT_FACT_EXPLANATION`` are this codebase's
    existing names for what the plans call ``LAB_FACT``; ``SAFETY_GUIDANCE``
    is the existing name for ``SAFETY_BOUNDARY``; ``DOCUMENTED_GENERAL_
    KNOWLEDGE`` is the existing name for ``DOCUMENTARY_EVIDENCE``. Renaming
    these deeply-embedded, already-working names would be cosmetic churn
    with real regression risk in a validator this load-bearing, so the
    single canonical name is the existing one; this docstring is the
    reconciliation record. The genuinely new types below (no prior
    equivalent existed) close real gaps: profile, study, ML, quality and
    history facts had no claimable, ID-backed representation before this
    etapa, and parametric veterinary knowledge had no claim type distinct
    from bare conversational prose.
    """

    PATIENT_FACT = "PATIENT_FACT"
    PATIENT_FACT_EXPLANATION = "PATIENT_FACT_EXPLANATION"
    # New (etapa 4): authorized facts beyond lab values, each backed by a
    # stable ContextBundle-derived fact_id (see send_chat_message.py's
    # authorized fact registry). Validated the same way as PATIENT_FACT —
    # by materialized-token projection, not literal text matching.
    PATIENT_PROFILE_FACT = "PATIENT_PROFILE_FACT"
    STUDY_METADATA = "STUDY_METADATA"
    ML_CLASSIFICATION = "ML_CLASSIFICATION"
    ML_FINDING = "ML_FINDING"
    QUALITY_FLAG = "QUALITY_FLAG"
    HISTORY_COMPARISON = "HISTORY_COMPARISON"
    # New (etapa 4): safe parametric (pretrained) veterinary knowledge,
    # distinct from bare CONVERSATIONAL prose so a plan can permit it
    # specifically (ResponsePlan.allow_parametric_knowledge) without opening
    # the door to unscoped chit-chat claims.
    PARAMETRIC_VETERINARY_KNOWLEDGE = "PARAMETRIC_VETERINARY_KNOWLEDGE"
    DOCUMENTED_GENERAL_KNOWLEDGE = "DOCUMENTED_GENERAL_KNOWLEDGE"
    LIMITATION = "LIMITATION"
    SAFETY_GUIDANCE = "SAFETY_GUIDANCE"
    URGENT_REFERRAL = "URGENT_REFERRAL"
    CONVERSATIONAL = "CONVERSATIONAL"
    # Connective tissue: announces or closes a topic without asserting
    # anything about it ("y ahora los valores de la serie blanca"). The
    # answer is a concatenation of claim texts, so without a claim type for
    # transitions there was nowhere to put one, and a claim that merely
    # named a parameter was rejected as an unbacked patient fact. It may
    # name parameters and must carry no digits: naming a topic is not
    # asserting a measurement, but a number would be one.
    TRANSITION = "TRANSITION"


# Every claim type whose text asserts something about one or more specific,
# ID-addressable authorized facts (from the registry send_chat_message.py
# builds out of ContextBundle). All are validated the same way: fact_ids
# must be authorized, and the text must be a materialized projection of
# those facts (see _patient_fact_is_materialized_projection) — never a
# literal string chosen from a backend-provided enum. Public (no leading
# underscore): send_chat_message.py imports this directly rather than
# redeclaring an equivalent set, so the two stay in sync by construction.
FACT_BASED_CLAIM_TYPES = frozenset(
    {
        ClaimType.PATIENT_FACT,
        ClaimType.PATIENT_FACT_EXPLANATION,
        ClaimType.PATIENT_PROFILE_FACT,
        ClaimType.STUDY_METADATA,
        ClaimType.ML_CLASSIFICATION,
        ClaimType.ML_FINDING,
        ClaimType.QUALITY_FLAG,
        ClaimType.HISTORY_COMPARISON,
    }
)


# The mirror image of FACT_BASED_CLAIM_TYPES: types whose validator forbids
# fact_ids outright. Kept explicit so the generation grammar can check, before
# it forces a citation onto every claim, whether that would make one of the
# authorized types impossible to emit — the state that produced
# ``structured_schema_invalid`` with no reachable repair, since the grammar
# demanded exactly what the validator rejected.
FACT_FORBIDDING_CLAIM_TYPES = frozenset(
    {
        ClaimType.PARAMETRIC_VETERINARY_KNOWLEDGE,
        ClaimType.TRANSITION,
    }
)


class EvidenceSpan(BaseModel):
    """Short, internal support copied from one retained source.

    The span is never exposed as the public citation.  Requiring it to occur in
    the retained chunk prevents a model from attaching an arbitrary source id
    to a claim that was generated from parametric knowledge.
    """

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1, max_length=160)
    text: str = Field(min_length=1, max_length=600)


class GeneratedClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: str = Field(pattern=r"^claim_[A-Za-z0-9_-]{1,80}$")
    text: str = Field(min_length=1, max_length=1800)
    claim_type: ClaimType
    fact_ids: list[str] = Field(default_factory=list, max_length=32)
    source_ids: list[str] = Field(default_factory=list, max_length=16)
    policy_rule_ids: list[str] = Field(default_factory=list, max_length=16)
    evidence_spans: list[EvidenceSpan] = Field(default_factory=list, max_length=16)

    @model_validator(mode="after")
    def validate_support_shape(self) -> "GeneratedClaim":
        if self.claim_type in FACT_BASED_CLAIM_TYPES and not self.fact_ids:
            raise ValueError("fact-based claims require at least one fact_id")
        if self.claim_type is ClaimType.DOCUMENTED_GENERAL_KNOWLEDGE:
            if not self.source_ids:
                raise ValueError("documented general knowledge requires source_ids")
            if not self.evidence_spans:
                raise ValueError("documented general knowledge requires evidence_spans")
        if self.claim_type in {
            ClaimType.SAFETY_GUIDANCE,
            ClaimType.URGENT_REFERRAL,
        } and not self.policy_rule_ids:
            raise ValueError("safety guidance requires a policy_rule_id")
        # A conversational claim may now cite authorized patient facts. It
        # could not before, and that single rule is why the assistant reads
        # like a report instead of a conversation: naming a value obliged the
        # model to open a separate fact claim, so "el hematocrito está algo
        # bajo, en 32 %, y encaja con el cansancio que cuentas" had to be
        # split into two blocks that the backend then joined with a blank
        # line. Citing does not loosen anything — send_chat_message.py
        # verifies any claim carrying fact_ids exactly like a patient fact
        # (the text must anchor them and OutputClaimValidator must match every
        # value, unit, range and date against them). What it drops is the
        # materialized-projection rule, which is a phrasing constraint, not a
        # safety one. Documentary sources, policy rules and evidence spans
        # stay closed: interpretation still needs a claim type that can carry
        # the evidence for it.
        if self.claim_type in {
            ClaimType.CONVERSATIONAL,
            ClaimType.PARAMETRIC_VETERINARY_KNOWLEDGE,
        } and (self.source_ids or self.policy_rule_ids or self.evidence_spans):
            raise ValueError("conversational claims cannot cite documentary support")
        if (
            self.claim_type is ClaimType.PARAMETRIC_VETERINARY_KNOWLEDGE
            and self.fact_ids
        ):
            raise ValueError("parametric knowledge claims cannot cite patient facts")
        # A transition carries the answer from one topic to the next and
        # asserts nothing, so it cites nothing.
        if self.claim_type is ClaimType.TRANSITION and (
            self.fact_ids
            or self.source_ids
            or self.policy_rule_ids
            or self.evidence_spans
        ):
            raise ValueError("transition claims cannot cite support")
        span_sources = {span.source_id for span in self.evidence_spans}
        if not span_sources.issubset(set(self.source_ids)):
            raise ValueError("every evidence span must reference a declared source_id")
        return self


# Cada descripción existe porque el alias corto de M-4 perdió la semántica del
# nombre largo: en la batería rigurosa del 9-ago el modelo marcó los flags por
# lo que la PREGUNTA pedía (una dosis) y no por lo que su RESPUESTA contenía
# (un rechazo sin dosis), y el turno murió con structured_safety_flags_invalid
# en las dos preguntas de seguridad de medicación (GEN-13/GEN-14).
_SAFETY_FLAG_NOTE = (
    "true SOLO si TU RESPUESTA lo contiene; lo que pregunta el usuario no cuenta."
)


class GeneratedSafety(BaseModel):
    """Seven mandatory booleans the model must emit on every envelope.

    The short aliases are what the generation grammar demands (M-4): the
    envelope floor is paid on every single call, and the seven long names
    alone cost ~74 output tokens (~5,7 s at the measured 13 tok/s).
    ``populate_by_name=True`` keeps every existing payload, log replay and
    test fixture that still uses the long names valid.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    contains_diagnosis_confirmation: bool = Field(
        alias="dx",
        description="¿Tu respuesta confirma un diagnóstico? " + _SAFETY_FLAG_NOTE,
    )
    contains_medication_recommendation: bool = Field(
        alias="med",
        description="¿Tu respuesta recomienda un medicamento? " + _SAFETY_FLAG_NOTE,
    )
    contains_dose: bool = Field(
        alias="dose",
        description="¿Tu respuesta indica una dosis? " + _SAFETY_FLAG_NOTE,
    )
    contains_frequency: bool = Field(
        alias="freq",
        description="¿Tu respuesta indica una frecuencia de administración? "
        + _SAFETY_FLAG_NOTE,
    )
    contains_treatment_duration: bool = Field(
        alias="dur",
        description="¿Tu respuesta indica una duración de tratamiento? "
        + _SAFETY_FLAG_NOTE,
    )
    contains_personalized_treatment: bool = Field(
        alias="pers",
        description="¿Tu respuesta personaliza un tratamiento para este paciente? "
        + _SAFETY_FLAG_NOTE,
    )
    requires_urgent_referral: bool = Field(
        alias="urgent",
        description=(
            "true si tu respuesta recomienda atención veterinaria urgente o "
            "el turno la exige."
        ),
    )


class GeneratedResponseEnvelope(BaseModel):
    """Internal model output; every visible paragraph is a validated claim."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["hemovet-response-v2"] = "hemovet-response-v2"
    response_type: str = Field(min_length=1, max_length=80)
    intent: str = Field(min_length=1, max_length=80)
    # Raised from 24: the canonical CBC catalog alone has 24 parameters, and
    # a full-hemogram summary can legitimately need one claim per parameter
    # plus profile/ML/quality/closing claims. A hemogram must never be
    # arbitrarily truncated to fit a claim-count ceiling (etapa 4, Block C).
    claims: list[GeneratedClaim] = Field(min_length=1, max_length=48)
    safety: GeneratedSafety

    @model_validator(mode="after")
    def unique_claim_ids(self) -> "GeneratedResponseEnvelope":
        claim_ids = [claim.claim_id for claim in self.claims]
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("claim_id values must be unique")
        return self

    @property
    def answer(self) -> str:
        return "\n\n".join(claim.text.strip() for claim in self.claims).strip()

    @property
    def used_fact_ids(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(fid for claim in self.claims for fid in claim.fact_ids))

    @property
    def used_source_ids(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(sid for claim in self.claims for sid in claim.source_ids)
        )


class StructuredResponseError(ValueError):
    def __init__(
        self,
        code: str,
        *,
        claim_id: str | None = None,
        detail_code: str | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.claim_id = claim_id
        self.detail_code = detail_code


class StructuredResponseService:
    """Parse and verify the model's claim-level response envelope.

    This validator intentionally checks only relationships that can be proven
    without another LLM. Existing clinical output validators remain responsible
    for numeric, unit, status and diagnostic-language validation of ``answer``.

    ``claim_entailment`` is optional and defaults to ``None``, which is the
    behaviour that shipped before it: documentary support is decided by
    lexical overlap alone. When one is injected it replaces that overlap
    decision — it is not stacked behind it, because a check that runs only
    after the lexicon already accepted inherits every unsafe acceptance the
    lexicon makes (11 of them on the bilingual bench). What it never replaces
    are the numeric and polarity vetoes below: those keep refusing regardless
    of what the entailment model says.
    """

    _WHITESPACE = re.compile(r"\s+")
    # Etapa 5, Block H: Unicode-aware (see retrieval_service._terms for the
    # identical reasoning) — a source in a script this file's ASCII-only
    # pattern used to discard entirely (Cyrillic, Greek, non-Latin scripts)
    # must still be tokenizable for cross-lingual grounding.
    _TOKEN = re.compile(r"[^\W_]+")
    _STOPWORDS = frozenset(
        {
            "algo",
            "como",
            "con",
            "del",
            "desde",
            "el",
            "ella",
            "en",
            "es",
            "esta",
            "este",
            "esto",
            "la",
            "las",
            "lo",
            "los",
            "para",
            "pero",
            "por",
            "que",
            "se",
            "sin",
            "son",
            "su",
            "sus",
            "una",
            "uno",
            "unos",
            # English function words are ignored as well because the curated
            # veterinary corpus is English while HemoVet's public contract is
            # Spanish.  They carry no clinical meaning for cross-language
            # evidence matching.
            "and",
            "are",
            "as",
            "at",
            "be",
            "by",
            "for",
            "from",
            "in",
            "is",
            "of",
            "on",
            "or",
            "that",
            "the",
            "their",
            "these",
            "this",
            "those",
            "to",
            "was",
            "were",
            "with",
            # Spanish hedge/modal/connector words carry no independent
            # clinical content: they are how a paraphrase is phrased, not
            # what it asserts.  Counting them as content tokens inflates the
            # required-overlap denominator and makes ordinary, faithful
            # paraphrases of the English corpus fail grounding even though
            # every factual noun in the claim is genuinely supported.
            "puede",
            "pueden",
            "podria",
            "podrian",
            "debe",
            "deben",
            "deberia",
            "deberian",
            "estar",
            "estan",
            "estara",
            "ser",
            "sea",
            "sean",
            "suele",
            "suelen",
            "indica",
            "indican",
            "indicar",
            "sugiere",
            "sugieren",
            "sugerir",
            "presenta",
            "presentan",
            "presentarse",
            "relacionado",
            "relacionada",
            "relacionados",
            "relacionadas",
            "asociado",
            "asociada",
            "asociados",
            "asociadas",
            "generalmente",
            "usualmente",
        }
    )
    _CLINICAL_ASSERTION = re.compile(
        r"\b(?:causa|causan|causar|provoca|provocan|produce|producen|"
        r"siempre|nunca|cambio(?:s)?\s+permanente(?:s)?|"
        r"indica\s+que|significa\s+que|se\s+debe\s+a)\b"
    )
    # A limitation is, by construction, a *negated* clinical statement: "un
    # valor alto no significa que haya enfermedad" is a textbook limitation
    # yet trips _CLINICAL_ASSERTION on "significa que". This marker is what
    # separates the two readings, and it is deliberately restricted to
    # negation particles — a hedge such as "requiere" or "solo" can coexist
    # with a genuine unsupported assertion, a negation inside the same
    # proposition cannot.
    #
    # It is matched only *before* the assertion verb (see
    # _asserts_without_negation): a negation anywhere in the proposition also
    # accepts decorative ones that do not negate the claim at all — "sin duda
    # la anemia causa debilidad", "la anemia no tratada causa debilidad" —
    # which an adversarial review demonstrated slipping through.
    # Anchored to the end of the text preceding the verb, so the negation has
    # to actually govern it. Only clitics, copulas and a few adverbs may sit
    # in between ("no se puede confirmar", "no necesariamente significa").
    # Anything else means the negation belongs to something other than the
    # assertion: "sin duda la anemia causa debilidad" and "la anemia no
    # tratada causa debilidad" both read as affirmations.
    _NEGATION = re.compile(
        r"\b(?:no|ni|nunca|tampoco|sin)\b"
        r"(?:\s+(?:se|lo|la|le|les|me|te|nos|necesariamente|realmente|"
        r"forzosamente|siempre|puede|pueden|podria|podrian|es|son|esta|"
        r"estan|resulta|resultan|implica|implican))*\s*$"
    )
    # What makes a claim a limitation rather than a bare assertion. Broad on
    # purpose — the closed phrase whitelist this replaced rejected nine of
    # twelve correct phrasings — but still a *positive* requirement: without
    # it LIMITATION becomes the one claim type that needs no fact, no source
    # and no evidence span, so "Lucas tiene anemia." would be deliverable.
    # `_CLINICAL_ASSERTION` cannot catch that on its own: it lists causal
    # verbs, not "tiene"/"padece"/"presenta".
    _LIMITATION_MARKER = re.compile(
        r"\b(?:no|ni|nunca|tampoco|sin|solo|unicamente|"
        r"limitacion\w*|limitad\w*|limite\w*|"
        r"insuficient\w*|incertidumbre|incierto|"
        r"orientativ\w*|preliminar\w*|provisional\w*|"
        r"requiere|requieren|corresponde|depende|"
        r"fuera\s+de\s+(?:mi|este|ese|su)\s+\w+)\b|"
        r"\bpor\s+si\s+sol[oa]\b"
    )
    _PROPOSITION_BOUNDARY = re.compile(
        r"\s+(?:y|pero|aunque|ademas|sin\s+embargo|mientras\s+que|por\s+tanto)\s+|"
        r",\s+"
    )
    # Conservative bilingual vocabulary used only to prove lexical support
    # between a Spanish public claim and a literal English evidence span.  It
    # does not translate prose or add knowledge: every mapped token still has
    # to occur in the retained source sentence, and numeric/polarity checks are
    # applied independently below.
    _TOKEN_EQUIVALENTS = {
        "agregacion": "aggregation",
        "agregados": "aggregate",
        "alto": "increase",
        "alta": "increase",
        "altos": "increase",
        "altas": "increase",
        "aumenta": "increase",
        "aumento": "increase",
        "aumentos": "increase",
        "aumentado": "increase",
        "aumentada": "increase",
        "aumentados": "increase",
        "aumentadas": "increase",
        "increased": "increase",
        "increase": "increase",
        "increases": "increase",
        "elevado": "increase",
        "elevada": "increase",
        "elevados": "increase",
        "elevadas": "increase",
        "bajo": "decrease",
        "baja": "decrease",
        "bajos": "decrease",
        "bajas": "decrease",
        "disminuye": "decrease",
        "disminucion": "decrease",
        "disminuciones": "decrease",
        "disminuido": "decrease",
        "disminuida": "decrease",
        "disminuidos": "decrease",
        "disminuidas": "decrease",
        "decreased": "decrease",
        "decrease": "decrease",
        "decreases": "decrease",
        "sangre": "blood",
        "sanguineo": "blood",
        "sanguinea": "blood",
        "sanguineos": "blood",
        "sanguineas": "blood",
        "blood": "blood",
        "celula": "cell",
        "celulas": "cell",
        "globulo": "cell",
        "globulos": "cell",
        "cell": "cell",
        "cells": "cell",
        "deshidratacion": "dehydration",
        "deshidratado": "dehydration",
        "deshidratada": "dehydration",
        "deshidratados": "dehydration",
        "deshidratadas": "dehydration",
        "dehydration": "dehydration",
        "dehydrated": "dehydration",
        "eritrocito": "erythrocyte",
        "eritrocitos": "erythrocyte",
        "erythrocyte": "erythrocyte",
        "erythrocytes": "erythrocyte",
        "rbc": "erythrocyte",
        "rojo": "red",
        "roja": "red",
        "rojos": "red",
        "rojas": "red",
        "red": "red",
        "leucocito": "leukocyte",
        "leucocitos": "leukocyte",
        "leukocyte": "leukocyte",
        "leukocytes": "leukocyte",
        "wbc": "leukocyte",
        "blanco": "white",
        "blanca": "white",
        "blancos": "white",
        "blancas": "white",
        "white": "white",
        "plaqueta": "platelet",
        "plaquetas": "platelet",
        "trombocito": "platelet",
        "trombocitos": "platelet",
        "platelet": "platelet",
        "platelets": "platelet",
        "plt": "platelet",
        "hemoglobina": "hemoglobin",
        "hemoglobin": "hemoglobin",
        "hgb": "hemoglobin",
        "hematocrito": "hematocrit",
        "hematocrit": "hematocrit",
        "hct": "hematocrit",
        "pcv": "hematocrit",
        "neutrofilo": "neutrophil",
        "neutrofilos": "neutrophil",
        "neutrophil": "neutrophil",
        "neutrophils": "neutrophil",
        "linfocito": "lymphocyte",
        "linfocitos": "lymphocyte",
        "lymphocyte": "lymphocyte",
        "lymphocytes": "lymphocyte",
        "monocito": "monocyte",
        "monocitos": "monocyte",
        "monocyte": "monocyte",
        "monocytes": "monocyte",
        "eosinofilo": "eosinophil",
        "eosinofilos": "eosinophil",
        "eosinophil": "eosinophil",
        "eosinophils": "eosinophil",
        "basofilo": "basophil",
        "basofilos": "basophil",
        "basophil": "basophil",
        "basophils": "basophil",
        "recuento": "count",
        "cantidad": "count",
        "count": "count",
        "counts": "count",
        "masa": "mass",
        "mass": "mass",
        "circulante": "circulating",
        "circulantes": "circulating",
        "circulating": "circulating",
        "indicador": "indicator",
        "indicadores": "indicator",
        "indicator": "indicator",
        "indicators": "indicator",
        "transporta": "transport",
        "transportan": "transport",
        "transporte": "transport",
        "transport": "transport",
        "transports": "transport",
        "oxigeno": "oxygen",
        "oxygen": "oxygen",
        "tejido": "tissue",
        "tejidos": "tissue",
        "tissue": "tissue",
        "tissues": "tissue",
        "coagulacion": "coagulation",
        "coagulation": "coagulation",
        "hemostasia": "hemostasis",
        "hemostasis": "hemostasis",
        "sangrado": "bleeding",
        "hemorragia": "bleeding",
        "bleeding": "bleeding",
        "infeccion": "infection",
        "infecciones": "infection",
        "infection": "infection",
        "infections": "infection",
        "inflamacion": "inflammation",
        "inflamatorio": "inflammation",
        "inflamatoria": "inflammation",
        "inflammation": "inflammation",
        "inmune": "immune",
        "inmunitaria": "immune",
        "inmunitario": "immune",
        "immune": "immune",
        "defensa": "defense",
        "defensas": "defense",
        "defense": "defense",
        "produccion": "production",
        "produce": "production",
        "production": "production",
        "medula": "marrow",
        "marrow": "marrow",
        "osea": "bone",
        "oseo": "bone",
        "bone": "bone",
        "rango": "range",
        "rangos": "range",
        "range": "range",
        "ranges": "range",
        "referencia": "reference",
        "reference": "reference",
        "resultado": "result",
        "resultados": "result",
        "result": "result",
        "results": "result",
        "laboratorio": "laboratory",
        "laboratory": "laboratory",
        "prueba": "test",
        "pruebas": "test",
        "test": "test",
        "tests": "test",
        "anemia": "anemia",
        "leucocitosis": "leukocytosis",
        "leukocytosis": "leukocytosis",
        "leucopenia": "leukopenia",
        "leukopenia": "leukopenia",
        "trombocitopenia": "thrombocytopenia",
        "thrombocytopenia": "thrombocytopenia",
        "trombocitosis": "thrombocytosis",
        "thrombocytosis": "thrombocytosis",
        "tamano": "size",
        "size": "size",
        "volumen": "volume",
        "volume": "volume",
        "promedio": "mean",
        "media": "mean",
        "mean": "mean",
        "concentracion": "concentration",
        "concentration": "concentration",
        "distribucion": "distribution",
        "distribution": "distribution",
        "variacion": "variation",
        "variation": "variation",
        "forma": "shape",
        "shape": "shape",
        "funcion": "function",
        "funciones": "function",
        "function": "function",
        "functions": "function",
        "explicacion": "content",
        "contenido": "content",
        "content": "content",
    }
    # Keyed by the exact message raised in validate_support_shape /
    # unique_claim_ids. Three keys drifted from the messages they were meant to
    # map (the fact_id and conversational rules were reworded, and the
    # parametric and transition rules were added without an entry), so the very
    # failures that needed naming fell through to the opaque
    # ``schema_validation_error:value_error`` — which is why the
    # ``structured_schema_invalid`` logs could not be read.
    _SCHEMA_ERROR_DETAILS = {
        "fact-based claims require at least one fact_id": "patient_fact_ids_missing",
        "documented general knowledge requires source_ids": "documented_source_ids_missing",
        (
            "documented general knowledge requires evidence_spans"
        ): "documented_evidence_spans_missing",
        "safety guidance requires a policy_rule_id": "policy_rule_id_missing",
        (
            "conversational claims cannot cite documentary support"
        ): "conversational_support_forbidden",
        (
            "parametric knowledge claims cannot cite patient facts"
        ): "parametric_fact_ids_forbidden",
        "transition claims cannot cite support": "transition_support_forbidden",
        (
            "every evidence span must reference a declared source_id"
        ): "evidence_source_undeclared",
        "claim_id values must be unique": "duplicate_claim_ids",
    }

    def __init__(
        self,
        *,
        claim_entailment: ClaimEntailmentPort | None = None,
    ) -> None:
        self._claim_entailment = claim_entailment

    @staticmethod
    def json_schema(
        *,
        allowed_fact_ids: Iterable[str] = (),
        allowed_source_ids: Iterable[str] = (),
        allowed_policy_rule_ids: Iterable[str] = (),
        allowed_claim_types: Iterable[ClaimType] | None = None,
        require_documentary_support: bool = False,
        allow_parametric_supplement: bool = False,
        documentary_text_options: Iterable[str] = (),
        require_patient_support: bool = False,
        patient_text_options: Iterable[str] = (),
        required_patient_claim_count: int = 0,
        require_policy_support: bool = False,
    ) -> dict[str, object]:
        """Build the provider schema from the support available to this request.

        Pydantic remains the final, fail-closed validator.  Constraining the
        generation grammar as well prevents the provider from selecting a
        patient, documentary, or policy claim type when the corresponding
        identifiers do not exist in the authorized request context.
        """
        # ``by_alias=True`` makes the grammar demand the short safety keys
        # (dx/med/dose/freq/dur/pers/urgent) instead of the seven long names,
        # shrinking both the schema sent with every request and the envelope
        # the model must emit (M-4).
        schema = GeneratedResponseEnvelope.model_json_schema(by_alias=True)
        definitions = schema.get("$defs")
        if not isinstance(definitions, dict):
            return schema

        claim_types = definitions.get("ClaimType")
        # Resolved once here because the support constraints below have to know
        # which types this turn can actually emit before they decide whether a
        # citation may be demanded of all of them.
        claim_type_values = tuple(
            dict.fromkeys(
                str(claim_type.value if isinstance(claim_type, ClaimType) else claim_type)
                for claim_type in (
                    allowed_claim_types
                    if allowed_claim_types is not None
                    else tuple(ClaimType)
                )
            )
        )
        fact_based_values = {claim_type.value for claim_type in FACT_BASED_CLAIM_TYPES}
        if isinstance(claim_types, dict) and allowed_claim_types is not None:
            claim_types["enum"] = list(claim_type_values)

        claim = definitions.get("GeneratedClaim")
        evidence = definitions.get("EvidenceSpan")
        if not isinstance(claim, dict):
            return schema
        properties = claim.get("properties")
        if not isinstance(properties, dict):
            return schema

        def constrain_identifier_array(field: str, values: Iterable[str]) -> None:
            allowed = list(dict.fromkeys(str(value) for value in values if value))
            field_schema = properties.get(field)
            if not isinstance(field_schema, dict):
                return
            items = field_schema.get("items")
            if isinstance(items, dict) and allowed:
                items["enum"] = allowed
            if not allowed:
                field_schema["maxItems"] = 0

        fact_ids = tuple(allowed_fact_ids)
        source_ids = tuple(allowed_source_ids)
        policy_rule_ids = tuple(allowed_policy_rule_ids)
        constrain_identifier_array("fact_ids", fact_ids)
        constrain_identifier_array("source_ids", source_ids)
        constrain_identifier_array("policy_rule_ids", policy_rule_ids)
        if require_policy_support:
            # En un turno de rechazo el único patrón válido de los seis flags
            # de contenido es todos-false: el validador mata cualquier true
            # (structured_safety_flags_invalid) y las puertas de texto ya
            # prohíben la dosis real. Un campo con un solo valor válido no
            # lleva información — se fija en la gramática. Medido el
            # 2026-08-09: el modelo marcaba los flags por el TEMA de la
            # pregunta (una dosis) y las dos preguntas de seguridad de
            # medicación morían tras la reparación, incluso con las
            # descripciones explícitas. En turnos clínicos los flags quedan
            # libres: ahí el auto-reporte sí es un cable trampa con valor.
            safety_def = definitions.get("GeneratedSafety")
            if isinstance(safety_def, dict):
                safety_properties = safety_def.get("properties")
                if isinstance(safety_properties, dict):
                    for flag in ("dx", "med", "dose", "freq", "dur", "pers"):
                        flag_schema = safety_properties.get(flag)
                        if isinstance(flag_schema, dict):
                            flag_schema["const"] = False
            policy_schema = properties.get("policy_rule_ids")
            if isinstance(policy_schema, dict):
                policy_schema["minItems"] = 1
                policy_schema["description"] = (
                    "One exact policy rule id authorized by this request."
                )
            required = claim.get("required")
            if isinstance(required, list) and "policy_rule_ids" not in required:
                required.append("policy_rule_ids")
            root_properties = schema.get("properties")
            if isinstance(root_properties, dict):
                claims_schema = root_properties.get("claims")
                if isinstance(claims_schema, dict):
                    claims_schema["minItems"] = 1
                    claims_schema["maxItems"] = 1
        if require_patient_support:
            fact_schema = properties.get("fact_ids")
            text_schema = properties.get("text")
            # ``fact_ids`` is a per-claim-type obligation, not a per-envelope
            # one, and JSON Schema cannot express that coupling in the subset
            # of keywords this provider's grammar is known to support. So the
            # requirement is only written into the grammar when it holds for
            # *every* authorized type; otherwise it is stated in prose and left
            # to GeneratedClaim.validate_support_shape, which enforces it per
            # type and remains the fail-closed authority either way.
            #
            # Forcing it unconditionally made any turn that also authorized
            # PARAMETRIC_VETERINARY_KNOWLEDGE or TRANSITION unanswerable: the
            # grammar demanded a citation those types are rejected for
            # carrying, so neither the first generation nor the repair — which
            # reuses this same schema — had a valid output to produce. It also
            # forced LIMITATION and CONVERSATIONAL claims to cite a fact, which
            # makes every sentence a literal fact projection: the reason a
            # clinical answer read like a table instead of an answer.
            unconditional = bool(claim_type_values) and all(
                value in fact_based_values for value in claim_type_values
            )
            if isinstance(fact_schema, dict):
                if unconditional:
                    fact_schema["minItems"] = 1
                fact_schema["description"] = (
                    "One or more exact patient fact ids authorized by this request."
                    if unconditional
                    else "One or more exact patient fact ids authorized by this "
                    "request. Required for every claim that states a measured "
                    "value, and forbidden on PARAMETRIC_VETERINARY_KNOWLEDGE "
                    "and TRANSITION claims, which assert no patient data."
                )
            required = claim.get("required")
            if (
                unconditional
                and isinstance(required, list)
                and "fact_ids" not in required
            ):
                required.append("fact_ids")
            if isinstance(text_schema, dict):
                # Deliberately no ``enum`` here: the model writes its own
                # Spanish sentence for the cited fact_ids. Forcing a literal,
                # backend-written sentence (the previous behavior) is exactly
                # what etapa 4 removes — validation instead checks that every
                # word is drawn from the materialized fact's own vocabulary
                # (_patient_fact_is_materialized_projection), which accepts
                # any faithful paraphrase and rejects any invented content.
                text_schema["description"] = (
                    "A Spanish sentence stating the authorized value(s) for the "
                    "cited fact_ids, in your own words. Use only the value, unit, "
                    "date and status carried by those facts; no interpretation, "
                    "cause, or diagnosis. With claim_type CONVERSATIONAL you may "
                    "write it as you would say it out loud, addressing the reader "
                    "and linking it to what they asked, as long as every value, "
                    "unit, range and date still comes from the cited facts."
                )
            root_properties = schema.get("properties")
            if isinstance(root_properties, dict):
                claims_schema = root_properties.get("claims")
                if isinstance(claims_schema, dict):
                    # No arbitrary cap here (previously capped at 4): a full
                    # hemogram must be able to produce one claim per
                    # authorized fact actually requested, up to the
                    # envelope's own claims ceiling.
                    # A ceiling, not a quota. Forcing minItems == maxItems ==
                    # (every lab value in the study) left no room in the
                    # envelope for a claim that answers the actual question,
                    # so a targeted question could only ever fail: the model
                    # had to emit one literal projection per lab value and
                    # nothing else. Fact coverage is enforced separately and
                    # per turn by the output validator's own
                    # ``required_coverage`` — which is 0 for these turns — so
                    # the quota was never backed by a real requirement.
                    count = min(max(1, int(required_patient_claim_count or 1)), 48)
                    claims_schema["minItems"] = 1
                    claims_schema["maxItems"] = min(count + 4, 48)
        if require_documentary_support:
            text_options = list(
                dict.fromkeys(
                    str(value).strip()
                    for value in documentary_text_options
                    if 12 <= len(str(value).strip()) <= 600
                )
            )
            source_schema = properties.get("source_ids")
            evidence_schema = properties.get("evidence_spans")
            text_schema = properties.get("text")
            if isinstance(source_schema, dict):
                if not allow_parametric_supplement:
                    source_schema["minItems"] = 1
                source_schema["description"] = (
                    "One or more exact source ids authorized by this request."
                    if not allow_parametric_supplement
                    else "One or more exact source ids authorized by this request. "
                    "Leave empty when the claim is not drawn from a retained "
                    "source; retrieval supports an answer, it never gates one."
                )
            if isinstance(evidence_schema, dict):
                if not allow_parametric_supplement:
                    evidence_schema["minItems"] = 1
                evidence_schema["description"] = (
                    "Literal spans copied verbatim from the retained source, in the "
                    "source's own original language — never translated or paraphrased. "
                    "Many retained sources are in English; an English source keeps its "
                    "evidence_spans in English even though claim.text is in Spanish."
                )
            if isinstance(text_schema, dict):
                text_schema["description"] = (
                    "One Spanish proposition supported by the selected literal "
                    "evidence span, even when that span is in another language; do not "
                    "combine unsupported ideas."
                )
            required = claim.get("required")
            # With a parametric supplement permitted, citation fields stay
            # optional in the generation grammar: a claim the retrieved
            # sources genuinely support still carries them (and is still
            # validated literally downstream), while a claim they do not
            # support is answered without inventing one. Forcing them here
            # would make PARAMETRIC_VETERINARY_KNOWLEDGE structurally
            # impossible to emit, since that type forbids citations.
            if isinstance(required, list) and not allow_parametric_supplement:
                for field in ("source_ids", "evidence_spans"):
                    if field not in required:
                        required.append(field)
            root_properties = schema.get("properties")
            if isinstance(root_properties, dict):
                claims_schema = root_properties.get("claims")
                if isinstance(claims_schema, dict):
                    # Etapa 4, Block C raised this from 1 to 8 so a documental
                    # explanation could combine several evidence-grounded
                    # points. In production, 8 independent claims each
                    # requiring their own non-empty, literal-language-matched
                    # source_ids/evidence_spans compounds into a generation
                    # that frequently fails structured_schema_invalid on a
                    # long educational answer — and the repair pass reuses
                    # this same schema unchanged, so it fails the same way
                    # and simply wastes another generation. 4 still allows a
                    # multi-point answer while meaningfully shrinking that
                    # failure surface.
                    claims_schema["maxItems"] = 4

        if isinstance(evidence, dict):
            evidence_properties = evidence.get("properties")
            if isinstance(evidence_properties, dict):
                source_schema = evidence_properties.get("source_id")
                if isinstance(source_schema, dict):
                    if source_ids:
                        source_schema["enum"] = list(dict.fromkeys(source_ids))
                    # GeneratedClaim.validate_support_shape requires every
                    # span's source_id to also appear in that claim's own
                    # source_ids array. JSON Schema cannot express a
                    # cross-field subset constraint, so unless the model is
                    # told here it silently emits a span citing a source the
                    # claim never declared and fails validation as
                    # `evidence_source_undeclared` — on the repair too, since
                    # nothing in the correction explained the coupling.
                    source_schema["description"] = (
                        "Exact id of the retained source this span was copied "
                        "from. It MUST also be listed in this claim's "
                        "source_ids array; a span citing a source the claim "
                        "does not declare is rejected."
                    )
                evidence_text = evidence_properties.get("text")
                if (
                    require_documentary_support
                    and isinstance(evidence_text, dict)
                    and text_options
                ):
                    evidence_text["enum"] = text_options
        if not source_ids:
            evidence_schema = properties.get("evidence_spans")
            if isinstance(evidence_schema, dict):
                evidence_schema["maxItems"] = 0
        return schema

    @classmethod
    def _schema_error_detail(cls, exc: ValidationError) -> str:
        """Return a fixed, non-clinical diagnostic code for schema failures.

        Pydantic validation errors may contain the rejected model value.  This
        projection deliberately reads only the fixed error type/message and
        never emits ``input``, a claim's text, or any patient context.
        """
        errors = exc.errors(include_url=False, include_input=False)
        if not errors:
            return "schema_validation_error"
        first = errors[0]
        message = str(first.get("msg", ""))
        if message.startswith("Value error, "):
            message = message.removeprefix("Value error, ")
        mapped = cls._SCHEMA_ERROR_DETAILS.get(message)
        if mapped:
            return mapped
        error_type = re.sub(r"[^a-z0-9_]+", "_", str(first.get("type", "")))
        if not error_type:
            return "schema_validation_error"
        return f"schema_validation_error:{error_type[:80]}"

    @staticmethod
    def parse(
        raw: str,
        *,
        sole_policy_rule_id: str | None = None,
        sole_fact_id: str | None = None,
    ) -> GeneratedResponseEnvelope:
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, TypeError) as exc:
            raise StructuredResponseError("structured_json_invalid") from exc
        payload = StructuredResponseService._materialize_deterministic_support(
            payload,
            sole_policy_rule_id=sole_policy_rule_id,
            sole_fact_id=sole_fact_id,
        )
        try:
            return GeneratedResponseEnvelope.model_validate(payload)
        except ValidationError as exc:
            raise StructuredResponseError(
                "structured_schema_invalid",
                detail_code=StructuredResponseService._schema_error_detail(exc),
            ) from exc

    @staticmethod
    def _materialize_deterministic_support(
        payload: object,
        *,
        sole_policy_rule_id: str | None,
        sole_fact_id: str | None,
    ) -> object:
        """Fill a support id the backend already knows with certainty (M-1/M-2).

        A turn authorizes at most one policy rule, and sometimes exactly one
        patient fact.  When the model states the right content but omits the
        only id that could ever be valid, rejecting the envelope buys no
        safety: there is exactly one value the field may hold, and the backend
        chose it.  Filling it here relaxes nothing downstream — the subset
        check in ``validate_support``, the text-anchoring gates and the
        materialized-projection rule still apply unchanged, so a claim whose
        text does not actually support the filled id dies exactly where it
        always did.
        """
        if not isinstance(payload, dict):
            return payload
        claims = payload.get("claims")
        if not isinstance(claims, list):
            return payload
        policy_types = {
            ClaimType.SAFETY_GUIDANCE.value,
            ClaimType.URGENT_REFERRAL.value,
        }
        fact_types = {claim_type.value for claim_type in FACT_BASED_CLAIM_TYPES}
        for claim in claims:
            if not isinstance(claim, dict):
                continue
            claim_type = claim.get("claim_type")
            if (
                sole_policy_rule_id
                and claim_type in policy_types
                and not claim.get("policy_rule_ids")
            ):
                claim["policy_rule_ids"] = [sole_policy_rule_id]
            if (
                sole_fact_id
                and claim_type in fact_types
                and not claim.get("fact_ids")
            ):
                claim["fact_ids"] = [sole_fact_id]
        return payload

    def validate_support(
        self,
        envelope: GeneratedResponseEnvelope,
        *,
        expected_intent: str,
        allowed_fact_ids: Iterable[str],
        retained_sources: Mapping[str, str],
        allowed_policy_rule_ids: Iterable[str],
    ) -> None:
        if envelope.intent != expected_intent:
            raise StructuredResponseError("structured_intent_mismatch")

        facts = set(allowed_fact_ids)
        sources = dict(retained_sources)
        policy_rules = set(allowed_policy_rule_ids)
        for claim in envelope.claims:
            if not set(claim.fact_ids).issubset(facts):
                raise StructuredResponseError(
                    "unknown_fact_id", claim_id=claim.claim_id
                )
            if not set(claim.source_ids).issubset(sources):
                raise StructuredResponseError(
                    "unknown_source_id", claim_id=claim.claim_id
                )
            if not set(claim.policy_rule_ids).issubset(policy_rules):
                raise StructuredResponseError(
                    "unknown_policy_rule_id", claim_id=claim.claim_id
                )
            for span in claim.evidence_spans:
                retained = sources.get(span.source_id, "")
                if self._normalize(span.text) not in self._normalize(retained):
                    raise StructuredResponseError(
                        "evidence_span_not_found", claim_id=claim.claim_id
                    )
            if claim.evidence_spans and not self._claim_has_evidence_overlap(
                claim,
                retained_sources=sources,
            ):
                raise StructuredResponseError(
                    "evidence_claim_mismatch",
                    claim_id=claim.claim_id,
                    detail_code=self._evidence_mismatch_detail(
                        claim,
                        retained_sources=sources,
                    ),
                )
            if claim.claim_type is ClaimType.LIMITATION and not (
                self._limitation_text_is_safe(claim.text)
            ):
                raise StructuredResponseError(
                    "limitation_claim_invalid",
                    claim_id=claim.claim_id,
                )

    def citation_is_verifiable(
        self,
        claim: GeneratedClaim,
        *,
        retained_sources: Mapping[str, str],
    ) -> bool:
        """Whether this claim's declared evidence actually proves it.

        Same two conditions ``validate_support`` enforces — every span must
        occur literally in its retained source, and every proposition must be
        supported by one of those spans' sentences — exposed separately so a
        caller can decide to *drop the citation* rather than fail the turn.
        """

        for span in claim.evidence_spans:
            retained = retained_sources.get(span.source_id, "")
            if self._normalize(span.text) not in self._normalize(retained):
                return False
        if not claim.evidence_spans:
            return True
        return self._claim_has_evidence_overlap(
            claim,
            retained_sources=dict(retained_sources),
        )

    @classmethod
    def _limitation_text_is_safe(cls, text: str) -> bool:
        """Decide whether a LIMITATION claim stays inside its contract.

        A limitation states what cannot be concluded or done. The only two
        ways it can harm the user are by smuggling in a measurement, or by
        asserting a positive clinical mechanism under a claim type that
        skips fact and evidence citation. Both are still refused here.

        What is deliberately *not* required anymore is that the wording match
        a closed whitelist of Spanish limitation phrasings. That whitelist
        rejected ordinary, correct sentences a model actually writes ("no
        puedo emitir diagnósticos", "no realizo diagnósticos", "no tengo
        acceso a esos datos") while accepting only a handful of memorized
        forms. Because the failure is fatal and the repair prompt never told
        the model which phrasings were acceptable, the second attempt landed
        outside the whitelist too and the whole turn was returned to the user
        as `generation_repair_failed` (HTTP 502) — a valid, safe answer
        discarded on a wording technicality. Reproduced end to end for
        "¿qué puedes hacer?" before this change.

        The assertion check is applied per proposition and only where nothing
        negates it, because an unnegated "la anemia causa debilidad" is the
        real risk while "un valor alto no significa que haya enfermedad" is
        the intended content of a limitation.
        """

        normalized = cls._normalize(text)
        if re.search(r"\d", normalized):
            return False
        propositions = cls._propositions(text)
        if any(cls._asserts_without_negation(proposition) for proposition in propositions):
            return False
        # A limitation marker is a *signal*, not a requirement. Demanding one
        # brought back the failure this whole line of work removes: measured
        # against production, "¿qué hallazgo detectó el sistema?" died with
        # `limitation_claim_invalid` because the model wrote a perfectly
        # correct caveat that carried none of the listed words. Requiring a
        # closed vocabulary is the exact antipattern that produced the 502s.
        #
        # What the adversarial review found through this gap — "Lucas tiene
        # anemia." reaching the user — is a *diagnosis* leaking, and that is
        # not this function's job. It is now caught where it belongs, by the
        # clinical safety net in OutputValidator, which was blind to the
        # patient's own name as the subject (`_definitive_named_subject`).
        # Guarding it here as well only meant a caveat had to be phrased from
        # a list; guarding it there means no phrasing gets a diagnosis
        # through, whatever claim type carries it.
        return True

    @classmethod
    def _asserts_without_negation(cls, proposition: str) -> bool:
        """Whether a proposition states a clinical mechanism as fact.

        The negation has to appear *before* the asserting verb. Accepting one
        anywhere in the proposition lets a decorative negation license the
        assertion it does not touch ("sin duda la anemia causa debilidad").
        """

        assertion = cls._CLINICAL_ASSERTION.search(proposition)
        if assertion is None:
            return False
        return cls._NEGATION.search(proposition[: assertion.start()]) is None

    @classmethod
    def _normalize(cls, value: str) -> str:
        decomposed = unicodedata.normalize("NFKD", value.casefold())
        ascii_like = "".join(
            character
            for character in decomposed
            if not unicodedata.combining(character)
        )
        return cls._WHITESPACE.sub(" ", ascii_like).strip()

    @classmethod
    def _content_tokens(cls, value: str) -> set[str]:
        tokens: set[str] = set()
        for token in cls._TOKEN.findall(cls._normalize(value)):
            if token in cls._STOPWORDS:
                continue
            mapped = cls._TOKEN_EQUIVALENTS.get(token, token)
            # The length gate exists to drop short filler tokens, not
            # clinical abbreviations (rbc, wbc, plt, hct, pcv, hgb) that the
            # equivalence table maps to their full canonical term.  Checking
            # the mapped form keeps those abbreviations eligible.
            if len(token) < 4 and len(mapped) < 4:
                continue
            tokens.add(mapped)
        return tokens

    def _claim_has_evidence_overlap(
        self,
        claim: GeneratedClaim,
        *,
        retained_sources: Mapping[str, str] | None = None,
    ) -> bool:
        """Require documentary support for every independently asserted clause.

        A whole-claim bag-of-words score is unsafe: a supported first sentence
        can lend its tokens to an unsupported second sentence.  Evidence spans
        are therefore expanded only to the sentence that contains the literal
        span, then every proposition must be supported by one such context on
        its own (including numbers and polarity).
        """

        sources = dict(retained_sources or {})
        contexts = self._evidence_contexts(claim, retained_sources=sources)
        propositions = self._propositions(claim.text)
        if not (contexts and propositions):
            return False
        # Numbers and polarity veto first and always. They are the two
        # language-independent anti-fabrication signals — an invented figure
        # and a flipped sign are exactly what a paraphrase must not smuggle in
        # — so no entailment verdict is allowed to talk them out of a refusal.
        # For the lexical path this is a no-op: `_proposition_supported`
        # requires the same two conditions on the same context it accepts.
        if not all(
            self._numbers_and_polarity_agree(proposition, contexts)
            for proposition in propositions
        ):
            return False
        entailed = self._claim_is_entailed(claim, retained_sources=sources)
        if entailed is not None:
            return entailed
        return all(
            self._proposition_supported(proposition, contexts)
            for proposition in propositions
        )

    def _claim_is_entailed(
        self,
        claim: GeneratedClaim,
        *,
        retained_sources: Mapping[str, str],
    ) -> bool | None:
        """Whether a cited sentence implies the claim, or ``None`` if unknown.

        The hypothesis is the whole claim text rather than one proposition at
        a time: entailment of a conjunction already requires every conjunct to
        hold, so a single premise still cannot lend support to a clause it
        does not cover — the leak the proposition split exists to stop.

        Premises are the *raw* source sentences, not the normalized contexts
        the lexical rule works on. Measured on the bilingual bench, feeding
        the model casefolded, accent-stripped text costs two cases and, worse,
        collapses the margin the threshold sits in: the weakest faithful claim
        drops from 0.916 to 0.275.

        ``None`` means no verdict was produced at all (no verifier injected,
        or every premise came back undecided because the model is unavailable
        or over its deadline), and the caller falls back to the lexical rule.
        """

        if self._claim_entailment is None:
            return None
        hypothesis = " ".join(claim.text.split())
        decided = False
        for premise in self._raw_evidence_sentences(
            claim,
            retained_sources=retained_sources,
        ):
            try:
                verdict = self._claim_entailment.entails(
                    premise=premise,
                    hypothesis=hypothesis,
                )
            except Exception as exc:
                # The port promises a `None` instead of raising, so reaching
                # here is a defect in the verifier — which is still no reason
                # to lose a turn the lexical rule can decide on its own.
                logger.warning(
                    "llm_chat.claim_entailment_raised code=%s",
                    type(exc).__name__,
                )
                verdict = None
            if verdict:
                return True
            decided = decided or verdict is False
        return False if decided else None

    def _evidence_mismatch_detail(
        self,
        claim: GeneratedClaim,
        *,
        retained_sources: Mapping[str, str],
    ) -> str:
        """Describe support failure using counts only, never clinical text."""
        contexts = self._evidence_contexts(
            claim,
            retained_sources=retained_sources,
        )
        propositions = self._propositions(claim.text)
        # An entailment refusal has no overlap arithmetic to report — the
        # lexical counts below would describe a rule that did not decide this
        # claim — so it names itself instead.
        vetoes_passed = all(
            self._numbers_and_polarity_agree(proposition, contexts)
            for proposition in propositions
        )
        entailed = self._claim_is_entailed(claim, retained_sources=retained_sources)
        # `None` is not a refusal: it is the absence of a verdict, and the
        # lexical arithmetic below is then exactly what decided the claim.
        if vetoes_passed and entailed is False:
            return "claim_entailment_rejected"
        for index, proposition in enumerate(propositions, start=1):
            if self._proposition_supported(proposition, contexts):
                continue
            tokens = self._content_tokens(proposition)
            best_overlap = max(
                (
                    len(tokens & self._content_tokens(context))
                    for context in contexts
                ),
                default=0,
            )
            token_count = len(tokens)
            required = (
                token_count
                if token_count <= 2
                else 2
                if token_count == 3
                else max(2, (token_count * 3 + 4) // 5)
            )
            return (
                f"proposition_{min(index, 24)}:overlap_{min(best_overlap, 99)}:"
                f"required_{min(required, 99)}:tokens_{min(token_count, 99)}:"
                f"contexts_{min(len(contexts), 16)}"
            )
        return "evidence_support_mismatch"

    @classmethod
    def _evidence_contexts(
        cls,
        claim: GeneratedClaim,
        *,
        retained_sources: Mapping[str, str],
    ) -> tuple[str, ...]:
        contexts: list[str] = []
        for span in claim.evidence_spans:
            normalized_span = cls._normalize(span.text)
            normalized_source = cls._normalize(
                retained_sources.get(span.source_id, "")
            )
            start = normalized_source.find(normalized_span)
            if start < 0:
                contexts.append(normalized_span)
                continue
            end = start + len(normalized_span)
            left = max(
                normalized_source.rfind(mark, 0, start)
                for mark in (".", ";", "!", "?")
            )
            right_candidates = [
                position
                for mark in (".", ";", "!", "?")
                if (position := normalized_source.find(mark, end)) >= 0
            ]
            right = min(right_candidates) + 1 if right_candidates else len(normalized_source)
            sentence = normalized_source[left + 1 : right].strip()
            contexts.append(sentence or normalized_span)
        return tuple(dict.fromkeys(context for context in contexts if context))

    @classmethod
    def _raw_evidence_sentences(
        cls,
        claim: GeneratedClaim,
        *,
        retained_sources: Mapping[str, str],
    ) -> tuple[str, ...]:
        """The sentences of ``_evidence_contexts`` as the corpus wrote them.

        Same expansion, on the source text with its accents and capitalization
        intact, because those are what the entailment model reads and what the
        lexical rule deliberately throws away. Only whitespace is collapsed,
        and on both sides: the corpus keeps the line wrapping of the original
        PDF export while a model quoting from it writes one line.

        A span whose accents differ from the source will still not be found;
        its own text is then the premise, which is corpus content all the same
        — ``citation_is_verifiable`` has already required it to occur in the
        retained source once normalized.
        """

        sentences: list[str] = []
        for span in claim.evidence_spans:
            source = " ".join(retained_sources.get(span.source_id, "").split())
            span_text = " ".join(span.text.split())
            start = source.find(span_text)
            if start < 0:
                sentences.append(span_text)
                continue
            end = start + len(span_text)
            left = max(source.rfind(mark, 0, start) for mark in (".", ";", "!", "?"))
            right_candidates = [
                position
                for mark in (".", ";", "!", "?")
                if (position := source.find(mark, end)) >= 0
            ]
            right = min(right_candidates) + 1 if right_candidates else len(source)
            sentence = source[left + 1 : right].strip()
            sentences.append(sentence or span_text)
        return tuple(dict.fromkeys(sentence for sentence in sentences if sentence))

    @classmethod
    def _propositions(cls, text: str) -> tuple[str, ...]:
        hard_parts = [
            part.strip()
            for part in re.split(r"[.;!?]+|\n+", cls._normalize(text))
            if part.strip()
        ]
        propositions: list[str] = []
        for part in hard_parts:
            soft_parts = [
                candidate.strip()
                for candidate in cls._PROPOSITION_BOUNDARY.split(part)
                if candidate.strip()
            ]
            # Do not split ordinary noun lists ("leucocitos y plaquetas").
            # A conjunction becomes a proposition boundary only when every
            # side carries at least two content-bearing words.
            if len(soft_parts) > 1 and all(
                len(cls._content_tokens(candidate)) >= 2
                for candidate in soft_parts
            ):
                propositions.extend(soft_parts)
            else:
                propositions.append(part)
        return tuple(propositions)

    @staticmethod
    def _shares_cognate_prefix(a: str, b: str) -> bool:
        """Language-agnostic cognate signal: a shared leading substring.

        Etapa 5, Block H: many veterinary/medical terms share a Greco-Latin
        root across Spanish, English, French, German and Portuguese
        (trombocitopenia/thrombocytopenia/thrombocytopénie/
        Thrombozytopenie/trombocitopenia) even though the full word differs.
        Requiring only a real prefix match (never for very short tokens,
        where a shared prefix is not a meaningful signal) recovers this
        without a per-language dictionary and without claiming to be a
        semantic/embedding model.
        """
        if a == b:
            return True
        threshold = min(len(a), len(b), 6)
        if threshold < 5:
            return False
        return a[:threshold] == b[:threshold]

    @classmethod
    def _proposition_supported(
        cls,
        proposition: str,
        contexts: tuple[str, ...],
    ) -> bool:
        claim_tokens = cls._content_tokens(proposition)
        if not claim_tokens:
            return False
        for context in contexts:
            if not cls._numbers_and_polarity_agree(proposition, (context,)):
                continue
            evidence_tokens = cls._content_tokens(context)
            overlap = claim_tokens & evidence_tokens
            # Etapa 5, Block H: this used to require ~60% exact/dictionary-
            # mapped token overlap — the "rigid lexical coincidence" the
            # audit explicitly names, which fails a faithful Spanish
            # paraphrase of a source in any language not in
            # _TOKEN_EQUIVALENTS. Cognate matches count toward coverage too,
            # and the required fraction drops substantially: numbers/
            # polarity below remain the real anti-fabrication signal
            # (language-independent by construction), so lexical overlap
            # only needs to show the proposition is not entirely
            # disconnected from the cited evidence, not that it restates it.
            cognate_matches = {
                claim_token
                for claim_token in claim_tokens - evidence_tokens
                if any(
                    cls._shares_cognate_prefix(claim_token, evidence_token)
                    for evidence_token in evidence_tokens
                )
            }
            covered = len(overlap) + len(cognate_matches)
            token_count = len(claim_tokens)
            required = 1 if token_count <= 3 else max(1, (token_count + 3) // 4)
            if covered < required:
                continue
            return True
        return False

    @classmethod
    def _numbers_and_polarity_agree(
        cls,
        proposition: str,
        contexts: tuple[str, ...],
    ) -> bool:
        """The two vetoes that hold whatever else decides support.

        Every figure the proposition states must appear in the same context
        that grounds it, and the two must carry the same sign. Both are
        language-independent by construction, which is why they survive a
        cross-lingual claim, and both refuse the two things a paraphrase can
        never do: invent a number, or invert what the source says.
        """

        claim_numbers = set(re.findall(r"\d+(?:[.,]\d+)?", proposition))
        claim_negative = bool(
            re.search(
                r"\b(?:no|nunca|sin|not|never|without)\b",
                cls._normalize(proposition),
            )
        )
        for context in contexts:
            evidence_numbers = set(re.findall(r"\d+(?:[.,]\d+)?", context))
            if not claim_numbers.issubset(evidence_numbers):
                continue
            evidence_negative = bool(
                re.search(
                    r"\b(?:no|nunca|sin|not|never|without)\b",
                    cls._normalize(context),
                )
            )
            if claim_negative != evidence_negative:
                continue
            return True
        return False
