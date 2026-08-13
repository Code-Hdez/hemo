from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SanitizedOutput:
    text: str
    raw_length: int
    sanitized_length: int
    removed_reasoning: bool
    used_source_ids: tuple[str, ...] = ()
    evidence_marker_found: bool = False


class OutputSanitizer:
    _evidence_marker = re.compile(
        r"\[\[\s*EVIDENCE_USED\s*:\s*([^\]]*)\]\]",
        re.IGNORECASE,
    )
    _source_id = re.compile(r"\bS([1-9]\d*)\b", re.IGNORECASE)
    _inline_citation = re.compile(
        r"\[\s*(?:S\s*\d+(?:\s*,\s*S\s*\d+)*|refs?|references?|source\s*\d*|fuente\s*\d*)\s*\]",
        re.IGNORECASE,
    )
    _citation_only_line = re.compile(
        r"(?m)^\s*(?:"
        r"\[\s*(?:S\s*\d+(?:\s*,\s*S\s*\d+)*|refs?|references?|source\s*\d*|fuente\s*\d*)\s*\]"
        r"[\s,;:.]*)+\s*$",
        re.IGNORECASE,
    )
    _trailing_citation_fragment = re.compile(
        r"\[\s*(?:S\s*\d{0,3}|refs?|references?|source\s*\d*|fuente\s*\d*)?$",
        re.IGNORECASE,
    )
    _closed_reasoning_tag = re.compile(
        r"<\s*(think|thinking|reasoning|analysis)\b[^>]*>.*?<\s*/\s*\1\s*>",
        re.IGNORECASE | re.DOTALL,
    )
    _leading_orphan_close = re.compile(
        r"^.*?<\s*/\s*(think|thinking|reasoning|analysis)\s*>",
        re.IGNORECASE | re.DOTALL,
    )
    _unclosed_reasoning_tag = re.compile(
        r"<\s*(think|thinking|reasoning|analysis)\b[^>]*>.*$",
        re.IGNORECASE | re.DOTALL,
    )
    _analysis_leadin = re.compile(
        r"^\s*(?:"
        r"okay[, ]+let(?:'|’)?s\s+[a-z]+\b|"
        r"let\s+me\s+(?:analy[sz]e|check|think|review)\b|"
        r"i\s+need\s+to\s+(?:check|analy[sz]e|ensure|answer|review)\b|"
        r"i\s+should(?:\s+not)?\b|"
        r"the\s+user\s+(?:is\s+asking|asks|wants|requested)\b|"
        r"according\s+to\s+(?:the\s+)?"
        r"(?:instructions|authorized\s+facts|sources?|context)\b|"
        r"the\s+authorized\s+facts\b|"
        r"first[, ]+i\s+(?:need|will)\b|"
        r"we\s+need(?:\s+to)?\s+[a-z]+\b|"
        r"voy\s+a\s+(?:analizar|revisar|comprobar)\b|"
        r"el\s+usuario\s+(?:pregunta|pide|solicita)\b|"
        r"seg[uú]n\s+las\s+instrucciones\b"
        r")[^\n.!?]*(?:[.!?]\s*|\n+)",
        re.IGNORECASE,
    )
    _answer_label = re.compile(
        r"^\s*(?:respuesta\s+final|final\s+answer|answer)\s*:\s*",
        re.IGNORECASE,
    )
    _spaced_clinical_decimal = re.compile(
        r"(?<!\d)(\d+)([.,])\s+(\d+)"
        r"(?=\s*(?:[x×]\s*10\s*(?:\^?\s*[369]|³|⁶|⁹)\s*/|"
        r"[km]\s*/\s*[uµμ]?\s*l|g\s*/\s*dl|%|fl|pg))",
        re.IGNORECASE,
    )

    def sanitize(self, text: str) -> str:
        return self.sanitize_with_report(text).text

    def clean_visible_answer(self, text: str, *, final: bool = True) -> str:
        """Remove source markers from user-visible answer text."""
        cleaned = self._strip_inline_citations(str(text or ""))
        if not final:
            cleaned = self._trailing_citation_fragment.sub("", cleaned)
        return cleaned

    def sanitize_with_report(self, text: str) -> SanitizedOutput:
        raw = str(text or "")
        raw_length = len(raw)
        marker_matches = list(self._evidence_marker.finditer(raw))
        used_source_ids: list[str] = []
        for match in marker_matches:
            for source_match in self._source_id.finditer(match.group(1)):
                source_id = f"S{int(source_match.group(1))}"
                if source_id not in used_source_ids:
                    used_source_ids.append(source_id)
        # Inline markers are never shown, but can safely recover attribution if
        # a runtime ignores the requested hidden envelope.
        for match in self._inline_citation.finditer(raw):
            for source_match in self._source_id.finditer(match.group(0)):
                source_id = f"S{int(source_match.group(1))}"
                if source_id not in used_source_ids:
                    used_source_ids.append(source_id)
        cleaned = str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
        cleaned = self._evidence_marker.sub("", cleaned)
        if not cleaned:
            return SanitizedOutput(
                text="",
                raw_length=raw_length,
                sanitized_length=0,
                removed_reasoning=False,
                used_source_ids=tuple(used_source_ids),
                evidence_marker_found=bool(marker_matches),
            )

        had_reasoning = any(
            pattern.search(cleaned)
            for pattern in (
                self._closed_reasoning_tag,
                self._leading_orphan_close,
                self._unclosed_reasoning_tag,
                self._analysis_leadin,
            )
        )
        cleaned = self._closed_reasoning_tag.sub("", cleaned)
        cleaned = self._leading_orphan_close.sub("", cleaned)
        cleaned = self._unclosed_reasoning_tag.sub("", cleaned)
        cleaned = self._strip_analysis_leadins(cleaned)
        cleaned = self._answer_label.sub("", cleaned)
        cleaned = self.clean_visible_answer(cleaned)
        # Small local models occasionally split a decimal before a clinical
        # unit (``16. 9 ×10⁹/L``). This is a formatting glitch, not a new
        # clinical value. Normalize only when a recognized unit follows so
        # ordinary numbered prose is never joined accidentally.
        cleaned = self._spaced_clinical_decimal.sub(r"\1\2\3", cleaned)
        normalized = self._normalize_whitespace(cleaned)
        return SanitizedOutput(
            text=normalized,
            raw_length=raw_length,
            sanitized_length=len(normalized),
            removed_reasoning=had_reasoning,
            used_source_ids=tuple(used_source_ids),
            evidence_marker_found=bool(marker_matches),
        )

    def _strip_analysis_leadins(self, text: str) -> str:
        cleaned = text.lstrip()
        for _ in range(12):
            match = self._analysis_leadin.match(cleaned)
            if match is None:
                return cleaned
            cleaned = cleaned[match.end():].lstrip(" \n\t-:;.")
        return cleaned

    def _strip_inline_citations(self, text: str) -> str:
        cleaned = self._citation_only_line.sub("", str(text or ""))
        cleaned = self._inline_citation.sub("", cleaned)
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        cleaned = re.sub(r"\s+([.,;:])", r"\1", cleaned)
        cleaned = re.sub(r"\(\s*\)", "", cleaned)
        return cleaned.lstrip()

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        lines = [line.strip() for line in text.strip().splitlines()]
        paragraphs: list[str] = []
        previous_blank = False
        for line in lines:
            if not line:
                if not previous_blank and paragraphs:
                    paragraphs.append("")
                previous_blank = True
                continue
            paragraphs.append(re.sub(r"[ \t]+", " ", line))
            previous_blank = False
        return "\n".join(paragraphs).strip()
