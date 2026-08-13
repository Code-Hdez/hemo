from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum
import re
import unicodedata

from app.modules.llm_chat.application.services.clinical_code_registry import (
    mentioned_parameter_codes,
)


class ClinicalClauseKind(StrEnum):
    """Semantic role of one clause that mentions a CBC parameter."""

    CONCEPTUAL = "conceptual"
    SUGGESTION = "suggestion"
    QUESTION = "question"
    PATIENT = "patient"
    TEMPORAL = "temporal"


@dataclass(frozen=True, slots=True)
class ClinicalDateReference:
    start: int
    end: int
    year: int
    month: int | None = None
    day: int | None = None


@dataclass(frozen=True, slots=True)
class ClinicalUnitReference:
    start: int
    end: int
    text: str


@dataclass(frozen=True, slots=True)
class ClinicalNumberReference:
    start: int
    end: int
    text: str
    value: Decimal


@dataclass(frozen=True, slots=True)
class ClinicalRangeReference:
    low: ClinicalNumberReference
    high: ClinicalNumberReference


@dataclass(frozen=True, slots=True)
class ParsedClinicalClause:
    raw: str
    normalized: str
    kind: ClinicalClauseKind
    parameter_codes: frozenset[str]
    dates: tuple[ClinicalDateReference, ...]
    units: tuple[ClinicalUnitReference, ...]
    numbers: tuple[ClinicalNumberReference, ...]
    ranges: tuple[ClinicalRangeReference, ...]

    @property
    def is_question_or_suggestion(self) -> bool:
        return self.kind in {
            ClinicalClauseKind.QUESTION,
            ClinicalClauseKind.SUGGESTION,
        }

    @property
    def is_conceptual(self) -> bool:
        return self.kind is ClinicalClauseKind.CONCEPTUAL

    @property
    def is_patient_specific(self) -> bool:
        return self.kind in {
            ClinicalClauseKind.PATIENT,
            ClinicalClauseKind.TEMPORAL,
        }


_MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}
_ISO_DATE = re.compile(r"\b(?P<year>20\d{2})-(?P<month>\d{2})-(?P<day>\d{2})\b")
_DMY_DATE = re.compile(
    r"\b(?P<day>0?[1-9]|[12]\d|3[01])/(?P<month>0?[1-9]|1[0-2])/"
    r"(?P<year>20\d{2})\b"
)
_SPANISH_DATE = re.compile(
    r"\b(?:(?P<day>\d{1,2})\s+de\s+)?"
    r"(?P<month>enero|febrero|marzo|abril|mayo|junio|julio|agosto|"
    r"septiembre|octubre|noviembre|diciembre)\s+(?:de(?:l)?\s+)?"
    r"(?P<year>20\d{2})\b"
)
_YEAR_REFERENCE = re.compile(
    r"\b(?:durante|en|desde|hasta|del|de|ano)\s+(?P<year>20\d{2})\b"
)
_NUMBER = re.compile(r"(?<![\w])(?P<number>[+-]?\d+(?:[.,]\d+)?)")
_UNIT = re.compile(
    r"(?:"
    r"(?:[x×·]\s*)?10\s*(?:\^\s*)?[0-9⁰¹²³⁴⁵⁶⁷⁸⁹]+\s*/\s*(?:[uµμ]?l|litro)|"
    r"[a-záéíóúñµμ]+(?:\s+[a-záéíóúñµμ]+){0,2}\s*/\s*[a-záéíóúñµμ]+|"
    r"[a-záéíóúñµμ]+\s+por\s+(?:microlitro|litro)|"
    r"%|\b(?:fl|pg)\b"
    r")",
    re.IGNORECASE,
)
_RANGE = re.compile(
    r"\b(?:rango|referencia|intervalo|limites?)\b[^.!?;\n]{0,45}?"
    r"(?:entre\s+)?(?P<low>[+-]?\d+(?:[.,]\d+)?)\s*"
    r"(?:-|–|a|hasta|y)\s*(?P<high>[+-]?\d+(?:[.,]\d+)?)",
    re.IGNORECASE,
)
_TEMPORAL = re.compile(
    r"\b(?:estudio\s+anterior|anterior|previo|antes|mas\s+reciente|reciente|"
    r"ultimo|actual|ahora|a\s+traves\s+del\s+tiempo|a\s+lo\s+largo|"
    r"cambi\w*|evolucion\w*|tendencia\w*)\b"
)
_PATIENT_ANCHOR = re.compile(
    r"\b(?:paciente|mascota|perro|este\s+(?:hemograma|analisis|estudio|resultado)|"
    r"ese\s+(?:hemograma|analisis|estudio|resultado)|"
    r"(?:del|en\s+el)\s+(?:hemograma|analisis|estudio|resultado)|"
    r"patron\s+(?:incluye|muestra|presenta)|"
    r"hallazgos?\s+(?:incluye(?:n)?|muestra(?:n)?|presenta(?:n)?)|"
    r"presenta(?:n)?|se\s+encuentra(?:n)?|se\s+observa(?:n)?|"
    r"aparece(?:n)?|registro|registraron|midieron|obtuvo|arrojo)\b"
)
_STATUS_ASSERTION = re.compile(
    r"(?:\b(?:esta(?:n)?|son|es|fue(?:ron)?|eran|aparece(?:n)?|presenta(?:n)?|"
    r"se\s+encuentra(?:n)?)\b[^.!?;\n]{0,35}\b"
    r"(?:alto|alta|altos|altas|elevad\w*|aumentad\w*|bajo|baja|bajos|bajas|"
    r"disminuid\w*|reducid\w*|normal(?:es)?)\b|"
    r"\bdentro\s+(?:(?:de\s+)?(?:su|el|los)\s+|del\s+|de\s+)?rangos?\b)"
)
_CONCEPTUAL = re.compile(
    r"\b(?:en\s+general|normalmente|habitualmente|"
    r"puede(?:n)?|podria(?:n)?|suele(?:n)?|"
    r"se\s+define(?:n)?|se\s+describe(?:n)?|significa(?:n)?|"
    r"consiste(?:n)?|participa(?:n)?|sirve(?:n)?|"
    r"ocurre(?:n)?\s+cuando|"
    r"(?:esta(?:n)?|es|son)\s+(?:alto|alta|altos|altas|elevad\w*|"
    r"aumentad\w*|bajo|baja|bajos|bajas|disminuid\w*|reducid\w*|"
    r"normal(?:es)?)\s+cuando)\b"
)
_SUGGESTION = re.compile(
    r"\b(?:seria\s+(?:bueno|util|conveniente)|puede\s+ser\s+util|"
    r"te\s+sugiero|se\s+sugiere|conviene|podrias?|recomiendo)\b"
    r"[^.!?;\n]{0,80}\b(?:preguntar|preguntarle|consultar|comentar|revisar)\b|"
    r"\b(?:pregunta|pregunte|consultar)\b[^.!?;\n]{0,70}"
    r"\b(?:si|sobre|por\s+que|que)\b"
)


def parse_clinical_clauses(
    text: str,
    *,
    available_codes: set[str] | frozenset[str] | None = None,
) -> tuple[ParsedClinicalClause, ...]:
    parsed: list[ParsedClinicalClause] = []
    for raw in re.split(r"(?<=[.!?;])\s+|\n+", str(text or "")):
        clause = raw.strip()
        if not clause:
            continue
        normalized = normalize_clinical_text(clause)
        codes = frozenset(
            mentioned_parameter_codes(
                normalized,
                available_codes=available_codes,
            )
        )
        dates = extract_date_references(normalized)
        units = extract_unit_references(clause)
        numbers = extract_number_references(clause, dates=dates, units=units)
        ranges = extract_range_references(clause)
        kind = classify_clinical_clause(
            clause,
            normalized=normalized,
            dates=dates,
            numbers=numbers,
            ranges=ranges,
        )
        parsed.append(
            ParsedClinicalClause(
                raw=clause,
                normalized=normalized,
                kind=kind,
                parameter_codes=codes,
                dates=dates,
                units=units,
                numbers=numbers,
                ranges=ranges,
            )
        )
    return tuple(parsed)


def classify_clinical_clause(
    raw: str,
    *,
    normalized: str | None = None,
    dates: tuple[ClinicalDateReference, ...] = (),
    numbers: tuple[ClinicalNumberReference, ...] = (),
    ranges: tuple[ClinicalRangeReference, ...] = (),
) -> ClinicalClauseKind:
    normalized = normalized or normalize_clinical_text(raw)
    if raw.rstrip().endswith("?") or raw.lstrip().startswith("¿"):
        return ClinicalClauseKind.QUESTION
    if _SUGGESTION.search(normalized):
        return ClinicalClauseKind.SUGGESTION
    if _CONCEPTUAL.search(normalized) and not _PATIENT_ANCHOR.search(normalized):
        return ClinicalClauseKind.CONCEPTUAL
    if dates or _TEMPORAL.search(normalized):
        return ClinicalClauseKind.TEMPORAL
    if numbers or ranges or _PATIENT_ANCHOR.search(normalized) or _STATUS_ASSERTION.search(
        normalized
    ):
        return ClinicalClauseKind.PATIENT
    return ClinicalClauseKind.CONCEPTUAL


def extract_date_references(text: str) -> tuple[ClinicalDateReference, ...]:
    normalized = normalize_clinical_text(text)
    references: list[ClinicalDateReference] = []
    occupied: list[tuple[int, int]] = []
    for pattern in (_ISO_DATE, _DMY_DATE, _SPANISH_DATE):
        for match in pattern.finditer(normalized):
            if _overlaps(match.span(), occupied):
                continue
            month_value = match.group("month")
            month = (
                _MONTHS[month_value]
                if month_value in _MONTHS
                else int(month_value)
            )
            reference = ClinicalDateReference(
                start=match.start(),
                end=match.end(),
                year=int(match.group("year")),
                month=month,
                day=int(match.group("day")) if match.group("day") else None,
            )
            references.append(reference)
            occupied.append(match.span())
    for match in _YEAR_REFERENCE.finditer(normalized):
        if _overlaps(match.span("year"), occupied):
            continue
        references.append(
            ClinicalDateReference(
                start=match.start("year"),
                end=match.end("year"),
                year=int(match.group("year")),
            )
        )
    return tuple(sorted(references, key=lambda item: item.start))


def extract_unit_references(text: str) -> tuple[ClinicalUnitReference, ...]:
    return tuple(
        ClinicalUnitReference(match.start(), match.end(), match.group(0).strip())
        for match in _UNIT.finditer(str(text or ""))
    )


def extract_number_references(
    text: str,
    *,
    dates: tuple[ClinicalDateReference, ...] | None = None,
    units: tuple[ClinicalUnitReference, ...] | None = None,
) -> tuple[ClinicalNumberReference, ...]:
    dates = dates if dates is not None else extract_date_references(text)
    units = units if units is not None else extract_unit_references(text)
    excluded = [*(date_span(item) for item in dates), *((item.start, item.end) for item in units)]
    references: list[ClinicalNumberReference] = []
    for match in _NUMBER.finditer(str(text or "")):
        span = match.span("number")
        if _overlaps(span, excluded) or _is_list_marker(text, span):
            continue
        token = match.group("number").replace(",", ".")
        try:
            value = Decimal(token)
        except InvalidOperation:  # pragma: no cover - regex constrains the token.
            continue
        references.append(
            ClinicalNumberReference(span[0], span[1], match.group("number"), value)
        )
    return tuple(references)


def extract_range_references(text: str) -> tuple[ClinicalRangeReference, ...]:
    references: list[ClinicalRangeReference] = []
    normalized = normalize_clinical_text(text)
    for match in _RANGE.finditer(normalized):
        low_token = match.group("low").replace(",", ".")
        high_token = match.group("high").replace(",", ".")
        references.append(
            ClinicalRangeReference(
                low=ClinicalNumberReference(
                    match.start("low"),
                    match.end("low"),
                    match.group("low"),
                    Decimal(low_token),
                ),
                high=ClinicalNumberReference(
                    match.start("high"),
                    match.end("high"),
                    match.group("high"),
                    Decimal(high_token),
                ),
            )
        )
    return tuple(references)


def date_span(reference: ClinicalDateReference) -> tuple[int, int]:
    return reference.start, reference.end


def normalize_clinical_text(value: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", str(value or "").casefold())
        if not unicodedata.combining(character)
    )


def _overlaps(span: tuple[int, int], others: list[tuple[int, int]]) -> bool:
    return any(span[0] < end and start < span[1] for start, end in others)


def _is_list_marker(text: str, span: tuple[int, int]) -> bool:
    if str(text or "")[: span[0]].strip():
        return False
    suffix = str(text or "")[span[1] : span[1] + 2]
    return bool(re.match(r"\s*[.)-]", suffix))
