from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import re
import unicodedata

from app.modules.llm_chat.application.services.clinical_facts import (
    ClinicalFactIndex,
    LabFact,
    normalize_clinical_unit,
    temporal_fact_index,
)
from app.modules.llm_chat.application.services.clinical_code_registry import (
    generic_family_mentions,
    mentioned_parameter_codes as resolve_mentioned_parameter_codes,
    parameter_alias_pattern,
    percentage_variant,
)
from app.modules.llm_chat.application.services.clinical_claim_parser import (
    ClinicalDateReference,
    ClinicalNumberReference,
    ParsedClinicalClause,
    extract_date_references,
    parse_clinical_clauses,
)

_NAMED_STATUS: dict[str, tuple[str, str]] = {
    "leucocitosis": ("WBC", "high"),
    "leucopenia": ("WBC", "low"),
    "neutrofilia": ("NEU", "high"),
    "neutropenia": ("NEU", "low"),
    "linfocitosis": ("LYM", "high"),
    "linfopenia": ("LYM", "low"),
    "monocitosis": ("MONO", "high"),
    "monocitopenia": ("MONO", "low"),
    "eosinofilia": ("EOS", "high"),
    "eosinopenia": ("EOS", "low"),
    "basofilia": ("BASO", "high"),
    "basopenia": ("BASO", "low"),
    "trombocitosis": ("PLT", "high"),
    "trombocitopenia": ("PLT", "low"),
}

_HIGH = re.compile(
    r"\b(?:alto|alta|altos|altas|elevado|elevada|elevados|elevadas|"
    r"aumentado|aumentada|aumentados|aumentadas|por encima)\b"
)
_LOW = re.compile(
    r"\b(?:bajo|baja|bajos|bajas|disminuido|disminuida|disminuidos|disminuidas|"
    r"reducido|reducida|reducidos|reducidas|"
    r"por debajo)\b"
)
_NORMAL = re.compile(
    r"\b(?:esta|estan|aparece|aparecen|permanece|permanecen|es|son)\b"
    r".{0,16}\bnormal(?:es)?\b|"
    r"\bdentro\s+(?:(?:de\s+)?(?:su|el|los)\s+|del\s+|de\s+)?rangos?\b"
)
_NON_STATUS_CONTEXT = re.compile(
    r"\bbajo\s+(?:(?:la|una|esta|esa)\s+)?supervision(?:\s+veterinaria)?\b|"
    r"\bbajo\s+(?:(?:este|ese|el)\s+)?contexto(?:\s+clinico)?\b|"
    r"\balta\s+prioridad(?:\s+clinica)?\b"
)
_TEMPORAL_MARKER = re.compile(
    r"\b(?:en\s+)?(?:el\s+)?(?P<previous>estudio\s+anterior|anterior|previo|antes)\b|"
    r"\b(?:en\s+)?(?:el\s+)?(?P<latest>mas\s+reciente|reciente|ultimo|actual|ahora)\b"
)
_NUMBER = r"[+-]?\d+(?:[.,]\d+)?"
_UNIT = re.compile(
    r"(?:(?:[x×·]\s*)?10\s*(?:\^\s*)?[0-9⁰¹²³⁴⁵⁶⁷⁸⁹]+\s*/\s*(?:[uµμ]?l|l)|"
    r"[a-záéíóúñµμ]+(?:\s+[a-záéíóúñµμ]+){0,2}\s*/\s*[a-záéíóúñµμ]+|"
    r"[a-záéíóúñµμ]+\s+por\s+(?:microlitro|litro)|%|fl|pg)",
    re.IGNORECASE,
)
_UNCERTAINTY = re.compile(
    r"\b(?:no\s+(?:permite(?:n)?|significa(?:n)?|implica(?:n)?|"
    r"demuestra(?:n)?|confirma(?:n)?)|"
    r"no\s+se\s+puede\s+(?:afirmar|confirmar)|por\s+si\s+solo\s+no)\b"
)
_CONCEPTUAL_MODAL = re.compile(
    r"\b(?:puede(?:n)?|podria(?:n)?|suele(?:n)?|en\s+general|normalmente|"
    r"habitualmente|se\s+define(?:n)?|describe(?:n)?|significa(?:n)?|"
    r"consiste(?:n)?|participa(?:n)?|sirve(?:n)?)\b"
)
_DIAGNOSTIC_CERTAINTY = re.compile(
    r"\b(?:esto|el resultado|el hemograma)\s+(?:confirma|demuestra|diagnostica)\b|"
    r"\b(?:tu perro|el perro|el paciente|la mascota)\s+"
    r"(?:tiene|padece|sufre)\s+(?:una\s+)?(?:enfermedad|infeccion|anemia|cancer)\b|"
    r"\b(?:no\s+hay|no\s+presenta|se\s+descarta)\s+(?:una\s+)?"
    r"(?:enfermedad|infeccion|anemia|cancer)\b"
)
_DOSAGE_INSTRUCTION = re.compile(
    r"\b(?:administra(?:le)?|dale|suministra(?:le)?|aplica|inicia)\b"
    r"[^.!?\n]{0,80}\b\d+(?:[.,]\d+)?\s*(?:mg|ml|cc|gotas?|tabletas?)\b"
)
_UNSUPPORTED_SEVERITY = re.compile(
    r"\b(?:leve|moderad[oa]s?|sever[oa]s?|grave|marcad[oa]s?|extrem[oa]s?)\b"
)


@dataclass(frozen=True, slots=True)
class ClinicalClaimIssue:
    code: str
    detail: str
    parameter_code: str | None = None
    analysis_id: str | None = None
    claim_text: str = ""


@dataclass(frozen=True, slots=True)
class ClinicalClaimValidation:
    is_valid: bool
    issues: tuple[ClinicalClaimIssue, ...] = ()

    @property
    def first_issue(self) -> ClinicalClaimIssue | None:
        return self.issues[0] if self.issues else None


class OutputClaimValidator:
    """Validate patient-specific claims, not bare hematology vocabulary.

    The extractor is intentionally conservative: it validates explicit values,
    units, ranges, dates and status predicates.  Definitions, questions and
    suggestions remain ordinary language and are not reclassified as patient
    facts merely because they name a parameter.
    """

    def validate(
        self,
        text: str,
        *,
        case_facts: list[dict[str, object]],
    ) -> ClinicalClaimValidation:
        normalized = _normalize(text)
        if _DOSAGE_INSTRUCTION.search(normalized):
            return self._invalid(
                "dosage_instruction", "positive_dosage_instruction", text
            )
        if _DIAGNOSTIC_CERTAINTY.search(normalized) and not _UNCERTAINTY.search(
            normalized
        ):
            return self._invalid(
                "diagnostic_certainty", "definitive_patient_diagnosis", text
            )

        index = temporal_fact_index(case_facts)
        issues: list[ClinicalClaimIssue] = []
        clauses = parse_clinical_clauses(
            text,
            available_codes=index.available_codes,
        )
        for parsed in clauses:
            clause = parsed.raw
            normalized_clause = parsed.normalized
            codes = set(parsed.parameter_codes)
            named = self._named_status_codes(normalized_clause)
            codes.update(code for code, _ in named)
            if not codes:
                continue

            if parsed.is_patient_specific:
                ambiguous = self._ambiguous_parameter_claim(
                    clause,
                    normalized_clause,
                    index,
                )
                if ambiguous is not None:
                    issues.append(ambiguous)
                    continue

            date_issue = self._validate_dates(parsed, codes, index)
            if date_issue:
                issues.append(date_issue)
                continue

            for code in sorted(codes):
                numeric_issue = self._validate_numbers_and_units(
                    parsed,
                    code,
                    index,
                )
                if numeric_issue:
                    issues.append(numeric_issue)
                    continue

            if parsed.is_question_or_suggestion or parsed.is_conceptual:
                # Asking whether a parameter should be reviewed is not a status
                # claim. General education is likewise not compared with this
                # patient's status. Concrete measurements and dates embedded in
                # either kind were still checked above and cannot smuggle data.
                continue
            if named and _UNSUPPORTED_SEVERITY.search(normalized_clause):
                code = named[0][0]
                issues.append(
                    ClinicalClaimIssue(
                        code="unsupported_status_claim",
                        detail=f"{code}:unsupported_severity",
                        parameter_code=code,
                        claim_text=clause[:240],
                    )
                )
                continue
            issues.extend(
                self._validate_statuses(clause, normalized_clause, codes, index)
            )
        return ClinicalClaimValidation(is_valid=not issues, issues=tuple(issues))

    @staticmethod
    def _invalid(code: str, detail: str, text: str) -> ClinicalClaimValidation:
        return ClinicalClaimValidation(
            is_valid=False,
            issues=(
                ClinicalClaimIssue(code=code, detail=detail, claim_text=text[:240]),
            ),
        )

    @staticmethod
    def _named_status_codes(normalized: str) -> list[tuple[str, str]]:
        return [
            (code, status)
            for term, (code, status) in _NAMED_STATUS.items()
            if re.search(rf"\b{re.escape(term)}\b", normalized)
        ]

    def _validate_dates(
        self,
        clause: ParsedClinicalClause,
        codes: set[str],
        index: ClinicalFactIndex,
    ) -> ClinicalClaimIssue | None:
        for reference in clause.dates:
            if not any(
                _fact_matches_calendar(
                    fact,
                    year=reference.year,
                    month=reference.month,
                    day=reference.day,
                )
                for code in codes
                for fact in index.series(code)
            ):
                display = _display_date_reference(reference)
                return ClinicalClaimIssue(
                    code="unsupported_date_claim",
                    detail=f"date_not_authorized:{display}",
                    claim_text=clause.raw[:240],
                )
        return None

    def _validate_numbers_and_units(
        self,
        clause: ParsedClinicalClause,
        code: str,
        index: ClinicalFactIndex,
    ) -> ClinicalClaimIssue | None:
        facts = self._facts_for_clause(clause.normalized, code, index)
        ranges = tuple(
            reference
            for reference in clause.ranges
            if self._reference_belongs_to_code(
                clause,
                code,
                reference.low.start,
                reference.high.end,
            )
        )
        range_spans = {
            (number.start, number.end)
            for reference in ranges
            for number in (reference.low, reference.high)
        }
        numbers = tuple(
            reference
            for reference in clause.numbers
            if (reference.start, reference.end) not in range_spans
            and self._reference_belongs_to_code(
                clause,
                code,
                reference.start,
                reference.end,
            )
        )

        for reference in ranges:
            match_facts = self._facts_for_numeric_position(
                clause.normalized,
                code,
                (reference.low.start, reference.high.end),
                index,
                fallback=facts,
            )
            if not match_facts:
                return ClinicalClaimIssue(
                    code="unsupported_range_claim",
                    detail=f"parameter_not_available:{code}",
                    parameter_code=code,
                    claim_text=clause.raw[:240],
                )
            actual = (reference.low.value, reference.high.value)
            allowed_ranges = {
                (Decimal(str(fact.reference_low)), Decimal(str(fact.reference_high)))
                for fact in match_facts
                if fact.reference_low is not None and fact.reference_high is not None
            }
            if actual not in allowed_ranges:
                return ClinicalClaimIssue(
                    code="unsupported_range_claim",
                    detail=f"{code}:unsupported_range:{actual[0]}:{actual[1]}",
                    parameter_code=code,
                    claim_text=clause.raw[:240],
                )
            unit_issue = self._validate_unit_after_reference(
                clause,
                reference.high,
                code,
                match_facts,
            )
            if unit_issue is not None:
                return unit_issue

        for reference in numbers:
            match_facts = self._facts_for_numeric_position(
                clause.normalized,
                code,
                (reference.start, reference.end),
                index,
                fallback=facts,
            )
            if not match_facts:
                return ClinicalClaimIssue(
                    code="unsupported_numeric_claim",
                    detail=f"parameter_not_available:{code}",
                    parameter_code=code,
                    claim_text=clause.raw[:240],
                )
            allowed_values = {
                Decimal(str(fact.value))
                for fact in match_facts
                if fact.value is not None
            }
            if reference.value not in allowed_values:
                return ClinicalClaimIssue(
                    code="unsupported_numeric_claim",
                    detail=f"{code}:unsupported_number:{reference.text}",
                    parameter_code=code,
                    claim_text=clause.raw[:240],
                )
            unit_issue = self._validate_unit_after_reference(
                clause,
                reference,
                code,
                match_facts,
            )
            if unit_issue is not None:
                return unit_issue
        return None

    @staticmethod
    def _reference_belongs_to_code(
        clause: ParsedClinicalClause,
        code: str,
        start: int,
        end: int,
    ) -> bool:
        if not clause.parameter_codes or clause.parameter_codes == {code}:
            return True
        mentions: list[tuple[int, int, str]] = []
        for candidate_code in clause.parameter_codes:
            alias = parameter_alias_pattern(candidate_code)
            for match in re.finditer(rf"\b{alias}\b", clause.normalized):
                mentions.append((match.start(), match.end(), candidate_code))
        mentions.sort()
        if not mentions:
            return False
        preceding = [mention for mention in mentions if mention[0] <= start]
        if preceding:
            return preceding[-1][2] == code
        following = [mention for mention in mentions if mention[0] >= end]
        if following:
            return following[0][2] == code
        center = (start + end) / 2
        return min(
            mentions,
            key=lambda mention: abs(center - ((mention[0] + mention[1]) / 2)),
        )[2] == code

    @staticmethod
    def _validate_unit_after_reference(
        clause: ParsedClinicalClause,
        reference: ClinicalNumberReference,
        code: str,
        facts: tuple[LabFact, ...],
    ) -> ClinicalClaimIssue | None:
        unit = next(
            (
                candidate
                for candidate in clause.units
                if candidate.start >= reference.end
                and re.fullmatch(
                    r"\s*(?:[,;:]\s*)?",
                    clause.raw[reference.end : candidate.start],
                )
            ),
            None,
        )
        if unit is None:
            return None
        actual_unit = normalize_clinical_unit(unit.text)
        allowed_units = {
            normalize_clinical_unit(fact.unit)
            for fact in facts
            if fact.unit
        }
        if actual_unit in allowed_units:
            return None
        return ClinicalClaimIssue(
            code="unsupported_unit_claim",
            detail=f"{code}:unsupported_unit:{actual_unit}",
            parameter_code=code,
            claim_text=clause.raw[:240],
        )

    def _facts_for_numeric_position(
        self,
        normalized: str,
        code: str,
        number_span: tuple[int, int],
        index: ClinicalFactIndex,
        *,
        fallback: tuple[LabFact, ...],
    ) -> tuple[LabFact, ...]:
        prefix = normalized[max(0, number_span[0] - 50) : number_span[0]]
        if re.search(
            r"\b(?:cambio|paso|aumento|subio|descendio|disminuyo)?\s*de\s*$",
            prefix,
        ):
            related = self._facts_for_relation(
                code,
                "previous",
                prefix,
                index,
            )
            if related:
                return related
        preceding_text = normalized[: number_span[0]]
        if re.search(r"\b(?:a|al)\s*$", prefix) and re.search(
            r"\b(?:cambi\w*|pas\w*|aument\w*|subi\w*|descend\w*|disminu\w*)\s+de\b",
            preceding_text,
        ):
            # ``prefix`` may still contain the previous study's date. The
            # explicit transition connector "a/al" has already established
            # that this endpoint is the latest value, so do not let that old
            # date override the relation.
            related = self._facts_for_relation(code, "latest", "", index)
            if related:
                return related

        references = _date_references(normalized)
        if references:
            center = (number_span[0] + number_span[1]) / 2
            selected = None
            for reference in references:
                if reference[0] < number_span[1]:
                    continue
                bridge = normalized[number_span[1] : reference[0]]
                if re.fullmatch(
                    rf"\s*{_UNIT.pattern}\s+(?:en|de|del)\s+",
                    bridge,
                    re.IGNORECASE,
                ):
                    selected = reference
                    break
            if selected is None:
                selected = min(
                    references,
                    key=lambda item: abs(center - ((item[0] + item[1]) / 2)),
                )
            _, _, year, month, day = selected
            matched = tuple(
                fact
                for fact in index.series(code)
                if _fact_matches_calendar(fact, year=year, month=month, day=day)
            )
            return matched

        markers = list(_TEMPORAL_MARKER.finditer(normalized))
        preceding = [marker for marker in markers if marker.start() <= number_span[0]]
        if preceding:
            marker = preceding[-1]
            relation = "previous" if marker.group("previous") else "latest"
            return self._facts_for_relation(
                code,
                relation,
                normalized[marker.start() :],
                index,
            )
        return fallback

    def _validate_statuses(
        self,
        clause: str,
        normalized: str,
        codes: set[str],
        index: ClinicalFactIndex,
    ) -> list[ClinicalClaimIssue]:
        transition = re.search(
            r"\bde\s+(?:(?:un|el)\s+)?(?:valor\s+)?"
            r"(?P<from>alto|alta|altos|altas|elevado|elevada|bajo|baja|bajos|bajas|"
            r"disminuido|disminuida|normal|normales)\s+"
            r"(?:a|hacia)\s+(?:(?:un|uno|una|el)\s+)?(?:valor\s+)?"
            r"(?P<to>alto|alta|altos|altas|elevado|elevada|bajo|baja|bajos|bajas|"
            r"disminuido|disminuida|normal|normales)\b",
            normalized,
        )
        if transition and len(codes) == 1:
            code = next(iter(codes))
            previous = index.previous(code)
            latest = index.latest(code)
            from_status = self._canonical_status(transition.group("from"))
            to_status = self._canonical_status(transition.group("to"))
            issues: list[ClinicalClaimIssue] = []
            if previous is None or previous.status != from_status:
                issues.append(
                    ClinicalClaimIssue(
                        code="unsupported_temporal_claim",
                        detail=(
                            f"{code}:previous:expected_"
                            f"{previous.status if previous else 'missing'}:claimed_{from_status}"
                        ),
                        parameter_code=code,
                        analysis_id=previous.analysis_id if previous else None,
                        claim_text=clause[:240],
                    )
                )
            if latest is None or latest.status != to_status:
                issues.append(
                    ClinicalClaimIssue(
                        code="unsupported_temporal_claim",
                        detail=(
                            f"{code}:latest:expected_"
                            f"{latest.status if latest else 'missing'}:claimed_{to_status}"
                        ),
                        parameter_code=code,
                        analysis_id=latest.analysis_id if latest else None,
                        claim_text=clause[:240],
                    )
                )
            return issues

        issues: list[ClinicalClaimIssue] = []
        windows = self._temporal_windows(normalized)
        for relation, window in windows:
            window_codes = mentioned_parameter_codes(
                window,
                available_codes=index.available_codes,
            ) or set(codes)
            for code, parameter_window in self._parameter_windows(window, window_codes):
                claims = self._status_claims(parameter_window)
                claims.extend(
                    (status, False)
                    for term, (named_code, status) in _NAMED_STATUS.items()
                    if named_code == code
                    and re.search(rf"\b{re.escape(term)}\b", parameter_window)
                )
                if not claims:
                    continue
                facts = self._facts_for_relation(code, relation, window, index)
                if not facts and (
                    _CONCEPTUAL_MODAL.search(parameter_window)
                    or _UNCERTAINTY.search(parameter_window)
                ):
                    # "Los leucocitos pueden estar altos en distintos procesos"
                    # is general education, not a claim about this patient.
                    continue
                for claimed_status, negated in claims:
                    if not facts:
                        issues.append(
                            ClinicalClaimIssue(
                                code="unsupported_status_claim",
                                detail=f"parameter_not_available:{code}:{claimed_status}",
                                parameter_code=code,
                                claim_text=clause[:240],
                            )
                        )
                        continue
                    if any(
                        (fact.status == claimed_status) != negated for fact in facts
                    ):
                        continue
                    fact = facts[-1]
                    issue_code = (
                        "unsupported_temporal_claim"
                        if relation
                        else "unsupported_status_claim"
                    )
                    issues.append(
                        ClinicalClaimIssue(
                            code=issue_code,
                            detail=(
                                f"{code}:{relation or 'current'}:expected_{fact.status}:"
                                f"claimed_{'not_' if negated else ''}{claimed_status}"
                            ),
                            parameter_code=code,
                            analysis_id=fact.analysis_id,
                            claim_text=clause[:240],
                        )
                    )
        return issues

    @staticmethod
    def _ambiguous_parameter_claim(
        clause: str,
        normalized: str,
        index: ClinicalFactIndex,
    ) -> ClinicalClaimIssue | None:
        if _CONCEPTUAL_MODAL.search(normalized) or _UNCERTAINTY.search(normalized):
            return None
        if not (
            OutputClaimValidator._status_claims(normalized)
            or re.search(rf"{_NUMBER}\s*{_UNIT.pattern}", normalized, re.IGNORECASE)
        ):
            return None
        for base in sorted(
            generic_family_mentions(
                normalized,
                available_codes=index.available_codes,
            )
        ):
            percent = percentage_variant(base)
            absolute_fact = index.latest(base)
            percent_fact = index.latest(percent or "")
            if absolute_fact is None or percent_fact is None:
                continue
            if absolute_fact.status == percent_fact.status:
                continue
            return ClinicalClaimIssue(
                code="ambiguous_parameter_claim",
                detail=(
                    f"{base}:absolute_{absolute_fact.status}:"
                    f"percentage_{percent_fact.status}"
                ),
                parameter_code=base,
                claim_text=clause[:240],
            )
        return None

    @staticmethod
    def _canonical_status(value: str) -> str:
        normalized = _normalize(value)
        if _HIGH.search(normalized):
            return "high"
        if _LOW.search(normalized):
            return "low"
        return "normal"

    @staticmethod
    def _parameter_windows(
        window: str,
        codes: set[str],
    ) -> list[tuple[str, str]]:
        matches: list[tuple[int, int, str]] = []
        for code in codes:
            alias = parameter_alias_pattern(code)
            matches.extend(
                (match.start(), match.end(), code)
                for match in re.finditer(rf"\b{alias}\b", window)
            )
        matches.sort()
        if not matches:
            # A second temporal clause may omit the repeated noun: "WBC estaba
            # bajo y ahora está alto".  The surrounding sentence supplies one
            # carried parameter code in the usual case.
            return [(code, window) for code in sorted(codes)]
        bounded: list[tuple[str, str]] = []
        for position, (start, _, code) in enumerate(matches):
            right = (
                matches[position + 1][0] if position + 1 < len(matches) else len(window)
            )
            bounded.append((code, window[start:right]))
        return bounded

    @staticmethod
    def _status_claims(window: str) -> list[tuple[str, bool]]:
        claims: list[tuple[str, bool]] = []
        non_status_spans = tuple(
            match.span() for match in _NON_STATUS_CONTEXT.finditer(window)
        )
        for status, pattern in (("high", _HIGH), ("low", _LOW), ("normal", _NORMAL)):
            for match in pattern.finditer(window):
                if any(
                    start <= match.start() and match.end() <= end
                    for start, end in non_status_spans
                ):
                    continue
                prefix = window[max(0, match.start() - 30) : match.start()]
                uncertainty = bool(_UNCERTAINTY.search(prefix))
                if uncertainty:
                    continue
                negated = bool(re.search(r"\bno\b[^,;.!?]{0,20}$", prefix))
                claims.append((status, negated))
        return claims

    @staticmethod
    def _temporal_windows(normalized: str) -> list[tuple[str | None, str]]:
        matches = list(_TEMPORAL_MARKER.finditer(normalized))
        if not matches:
            return [(None, normalized)]
        windows: list[tuple[str | None, str]] = []
        for position, match in enumerate(matches):
            right = (
                matches[position + 1].start()
                if position + 1 < len(matches)
                else len(normalized)
            )
            relation = "previous" if match.group("previous") else "latest"
            windows.append((relation, normalized[match.start() : right]))
        return windows

    def _facts_for_clause(
        self,
        normalized: str,
        code: str,
        index: ClinicalFactIndex,
    ) -> tuple[LabFact, ...]:
        values = index.series(code)
        dates = _date_references(normalized)
        if dates:
            return tuple(
                fact
                for fact in values
                if any(
                    _fact_matches_calendar(
                        fact,
                        year=year,
                        month=month,
                        day=day,
                    )
                    for _, _, year, month, day in dates
                )
            )
        for fact in values:
            if fact.study_key and re.search(
                rf"\b{re.escape(_normalize(fact.study_key))}\b", normalized
            ):
                return (fact,)
        for relation, window in self._temporal_windows(normalized):
            if re.search(
                rf"\b{parameter_alias_pattern(code)}\b",
                window,
            ):
                return self._facts_for_relation(code, relation, window, index)
        return values

    @staticmethod
    def _facts_for_relation(
        code: str,
        relation: str | None,
        window: str,
        index: ClinicalFactIndex,
    ) -> tuple[LabFact, ...]:
        values = index.series(code)
        if not values:
            return ()
        dates = _date_references(window)
        if dates:
            return tuple(
                fact
                for fact in values
                if any(
                    _fact_matches_calendar(
                        fact,
                        year=year,
                        month=month,
                        day=day,
                    )
                    for _, _, year, month, day in dates
                )
            )
        for fact in values:
            if fact.study_key and re.search(
                rf"\b{re.escape(_normalize(fact.study_key))}\b", window
            ):
                return (fact,)
        if relation == "previous":
            return (values[-2],) if len(values) >= 2 else ()
        if relation == "latest" or relation is None:
            return (values[-1],)
        return ()


def mentioned_parameter_codes(
    normalized_text: str,
    *,
    available_codes: set[str] | frozenset[str] | None = None,
) -> set[str]:
    return resolve_mentioned_parameter_codes(
        _normalize(normalized_text),
        available_codes=available_codes,
    )


def _date_references(text: str) -> list[tuple[int, int, int, int | None, int | None]]:
    """Compatibility tuple view over the typed date parser."""

    return [
        (item.start, item.end, item.year, item.month, item.day)
        for item in extract_date_references(text)
    ]


def _display_date_reference(reference: ClinicalDateReference) -> str:
    if reference.month is None:
        return f"{reference.year:04d}"
    if reference.day is None:
        return f"{reference.year:04d}-{reference.month:02d}"
    return f"{reference.year:04d}-{reference.month:02d}-{reference.day:02d}"


def _fact_matches_calendar(
    fact: LabFact,
    *,
    year: int,
    month: int | None,
    day: int | None,
) -> bool:
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})", fact.study_date)
    if not match:
        return False
    fact_year, fact_month, fact_day = (int(part) for part in match.groups())
    return (
        fact_year == year
        and (month is None or fact_month == month)
        and (day is None or fact_day == day)
    )


def _normalize(value: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", str(value or "").casefold())
        if not unicodedata.combining(character)
    )
