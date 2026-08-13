from __future__ import annotations

from dataclasses import dataclass
import re

from app.modules.hematology.cbc_fields import (
    canonical_cbc_clinical_code,
    cbc_clinical_aliases,
    normalize_cbc_alias,
)


PARAMETER_ALIASES: dict[str, tuple[str, ...]] = cbc_clinical_aliases()

_PERCENT_CODES = frozenset(
    code for code in PARAMETER_ALIASES if code.endswith("_PCT")
)
_PERCENT_BY_BASE = {
    code.removesuffix("_PCT"): code for code in _PERCENT_CODES
}
_BASE_BY_PERCENT = {percent: base for base, percent in _PERCENT_BY_BASE.items()}


@dataclass(frozen=True, slots=True)
class ParameterMention:
    code: str
    start: int
    end: int
    generic_family: bool = False
    explicit_percentage: bool = False


def canonical_parameter_code(value: str) -> str:
    return canonical_cbc_clinical_code(value)


def parameter_family(code: str) -> str:
    normalized = canonical_parameter_code(code)
    return _BASE_BY_PERCENT.get(normalized, normalized)


def percentage_variant(code: str) -> str | None:
    return _PERCENT_BY_BASE.get(parameter_family(code))


def is_percentage_code(code: str) -> bool:
    return canonical_parameter_code(code) in _PERCENT_CODES


def parameter_alias_pattern(
    code: str,
    *,
    include_generic_for_percentage: bool = True,
) -> str:
    """Return a normalized-text regex for one stable clinical code."""

    normalized_code = canonical_parameter_code(code)
    aliases = list(PARAMETER_ALIASES.get(normalized_code, (normalized_code.casefold(),)))
    if normalized_code in _PERCENT_CODES and include_generic_for_percentage:
        aliases.extend(PARAMETER_ALIASES.get(_BASE_BY_PERCENT[normalized_code], ()))
    return _aliases_pattern(aliases)


def parameter_mentions(
    text: str,
    *,
    available_codes: set[str] | frozenset[str] | None = None,
) -> tuple[ParameterMention, ...]:
    """Resolve parameter mentions without collapsing absolute and percentage facts.

    Explicit percentage markers win over an overlapping generic alias. A bare
    family name resolves to the absolute code when present, or to the percentage
    code when that is the only available variant.
    """

    normalized = normalize_cbc_alias(text)
    available = (
        {canonical_parameter_code(code) for code in available_codes}
        if available_codes is not None
        else None
    )
    candidates: list[tuple[int, int, int, str, bool, bool]] = []

    for code, aliases in PARAMETER_ALIASES.items():
        if code in _PERCENT_CODES:
            explicit_aliases = [alias for alias in aliases if _is_explicit_percent(alias)]
            for match in _find_aliases(normalized, explicit_aliases):
                candidates.append(
                    (match.start(), match.end(), 0, code, False, True)
                )
            continue

        percent = _PERCENT_BY_BASE.get(code)
        for match in _find_aliases(normalized, aliases):
            resolved = code
            generic_family = percent is not None
            if (
                generic_family
                and available is not None
                and code not in available
                and percent in available
            ):
                resolved = percent
            candidates.append(
                (match.start(), match.end(), 1, resolved, generic_family, False)
            )

    # Prefer the longest alias at a position, and explicit percentage mentions
    # over a generic family alias covering the same text.
    candidates.sort(key=lambda item: (item[0], item[2], -(item[1] - item[0])))
    selected: list[ParameterMention] = []
    occupied: list[tuple[int, int]] = []
    for start, end, _, code, generic_family, explicit_percentage in candidates:
        if any(start < used_end and used_start < end for used_start, used_end in occupied):
            continue
        selected.append(
            ParameterMention(
                code=code,
                start=start,
                end=end,
                generic_family=generic_family,
                explicit_percentage=explicit_percentage,
            )
        )
        occupied.append((start, end))
    return tuple(sorted(selected, key=lambda item: item.start))


def mentioned_parameter_codes(
    text: str,
    *,
    available_codes: set[str] | frozenset[str] | None = None,
) -> set[str]:
    return {
        mention.code
        for mention in parameter_mentions(text, available_codes=available_codes)
    }


def extract_parameter_code(text: str) -> str | None:
    mentions = parameter_mentions(text)
    return mentions[0].code if mentions else None


def generic_family_mentions(
    text: str,
    *,
    available_codes: set[str] | frozenset[str] | None = None,
) -> set[str]:
    return {
        parameter_family(mention.code)
        for mention in parameter_mentions(text, available_codes=available_codes)
        if mention.generic_family and not mention.explicit_percentage
    }


def _aliases_pattern(aliases: list[str] | tuple[str, ...]) -> str:
    escaped = sorted(
        {
            re.escape(alias).replace(r"\ ", r"\s+")
            for alias in aliases
            if alias
        },
        key=len,
        reverse=True,
    )
    return "(?:" + "|".join(escaped or [r"(?!)"]) + ")"


def _find_aliases(text: str, aliases: list[str] | tuple[str, ...]):
    pattern = _aliases_pattern(aliases)
    return re.finditer(rf"(?<![a-z0-9]){pattern}(?![a-z0-9])", text)


def _is_explicit_percent(alias: str) -> bool:
    tokens = set(alias.split())
    return "%" in alias or "pct" in tokens or "porcentaje" in tokens
