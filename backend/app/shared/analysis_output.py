"""Compatibility sanitizers for historical analysis payloads."""

import re
import unicodedata
from typing import Any

HIDDEN_LABELS = {"QC_REQUIERE_FROTIS", "Frotis recomendado"}
_HIDDEN_QC_FLAG_SUBSTRINGS = ("frotis",)


def _normalize(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(value).lower())
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _is_hidden_diagnosis(value: Any) -> bool:
    return (
        "confirmacion con frotis sanguineo recomendada para evaluacion morfologica"
        in _normalize(value)
    )


def _scrub_summary(value: Any) -> str:
    text = str(value or "")
    for hidden in HIDDEN_LABELS:
        text = re.sub(re.escape(hidden), "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*,\s*,", ",", text)
    text = re.sub(r":\s*,\s*", ": ", text)
    text = re.sub(r",\s*\.", ".", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    return "Hemograma analizado." if text.endswith(":") else text


def scrub_hidden_labels(record: dict) -> dict:
    findings = record.get("findings") or []
    qc_flags = record.get("qc_flags") or []
    diagnoses = record.get("diagnoses") or []
    scrubbed_findings = [f for f in findings if f.get("label") not in HIDDEN_LABELS]
    scrubbed_qc = [
        flag
        for flag in qc_flags
        if not any(sub in _normalize(flag) for sub in _HIDDEN_QC_FLAG_SUBSTRINGS)
    ]
    scrubbed_diagnoses = [d for d in diagnoses if not _is_hidden_diagnosis(d)]
    summary = record.get("summary", "")
    scrubbed_summary = _scrub_summary(summary)
    if (
        len(scrubbed_findings) == len(findings)
        and len(scrubbed_qc) == len(qc_flags)
        and len(scrubbed_diagnoses) == len(diagnoses)
        and scrubbed_summary == summary
    ):
        return record
    result = dict(record)
    result.update(
        findings=scrubbed_findings,
        qc_flags=scrubbed_qc,
        diagnoses=scrubbed_diagnoses,
        summary=scrubbed_summary,
    )
    return result
