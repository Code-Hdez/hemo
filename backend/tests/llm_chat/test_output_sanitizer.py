import pytest

from app.modules.llm_chat.application.services.output_sanitizer import OutputSanitizer


def test_sanitizer_removes_think_blocks_and_analysis_leadins() -> None:
    raw = (
        "<think>Okay, let's tackle this query. The user is asking about platelets.</think>\n"
        "Okay, let's tackle this query. The user is asking what platelets are.\n"
        "Las plaquetas ayudan a formar coágulos y controlar sangrados [S1]."
    )

    sanitized = OutputSanitizer().sanitize(raw)

    assert sanitized == "Las plaquetas ayudan a formar coágulos y controlar sangrados."


def test_sanitizer_removes_trailing_reasoning_after_final_answer() -> None:
    raw = (
        "Las plaquetas participan en la coagulación [S1].\n"
        "<think>I need to check the sources next.</think>"
    )

    sanitized = OutputSanitizer().sanitize(raw)

    assert sanitized == "Las plaquetas participan en la coagulación."


@pytest.mark.parametrize(
    "analysis_line",
    [
        "Okay, let's craft a concise answer in Spanish.",
        "According to the instructions, I should answer in Spanish.",
        "I should not provide a definitive diagnosis.",
        "We need to explain the authorized facts carefully.",
        "We need answer in Spanish using the sources.",
        "The authorized facts contain information about platelets.",
        "The user requested an educational explanation.",
        "Voy a analizar la pregunta antes de responder.",
        "El usuario pregunta qué son las plaquetas.",
        "Según las instrucciones, debo evitar un diagnóstico.",
    ],
)
def test_sanitizer_removes_supported_internal_commentary(
    analysis_line: str,
) -> None:
    raw = (
        f"{analysis_line}\n"
        "Las plaquetas participan en la hemostasia y coagulación [S1]."
    )

    sanitized = OutputSanitizer().sanitize(raw)

    assert sanitized == "Las plaquetas participan en la hemostasia y coagulación."


def test_sanitizer_removes_analysis_tags() -> None:
    raw = (
        "<analysis>We need to inspect the sources.</analysis>\n"
        "Las plaquetas participan en la hemostasia [S1]."
    )

    assert OutputSanitizer().sanitize(raw) == "Las plaquetas participan en la hemostasia."


def test_sanitizer_removes_inline_citation_variants() -> None:
    raw = "Los eritrocitos transportan oxígeno [S1, S2]. [ref]"

    assert OutputSanitizer().sanitize(raw) == "Los eritrocitos transportan oxígeno."


def test_sanitizer_extracts_attribution_without_exposing_marker() -> None:
    report = OutputSanitizer().sanitize_with_report(
        "La explicación usa dos evidencias [S2].\n[[EVIDENCE_USED:S2,S3]]"
    )

    assert report.text == "La explicación usa dos evidencias."
    assert report.used_source_ids == ("S2", "S3")
    assert report.evidence_marker_found is True


def test_sanitizer_repairs_spaced_decimal_only_before_clinical_unit() -> None:
    raw = (
        "El rango es 5.5–16. 9 ×10⁹/L. "
        "Pasos pendientes: 1. 2. Revisar con el veterinario."
    )

    sanitized = OutputSanitizer().sanitize(raw)

    assert "16.9 ×10⁹/L" in sanitized
    assert "1. 2." in sanitized
