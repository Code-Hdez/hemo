from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.hematology import extraction_service  # noqa: E402
from app.modules.hematology.extraction_types import ExtractionResult  # noqa: E402


def _rich_payload() -> dict[str, Any]:
    return {
        "Leucocitos(WBC)": {
            "value": "11,2",
            "unit": "10^3/uL",
            "raw_label": "Leucocitos(WBC)",
            "confidence": 0.95,
        },
        "Hemoglobina(HGB)": {"value": "14.1", "unit": "g/dL"},
        "Hematocrito (HCT)": {"value": 43.0, "unit": "%"},
        "Hematíes(RBC)": {"value": 7.4, "unit": "10^6/uL"},
        "Recuento total de plaquetas (EPLT)": {"value": 250, "unit": "10^3/uL"},
        "Reticulocitos %(RET%)": {"value": "1,8", "unit": "%"},
        "Distribución eritrocitaria (RDW-CV)": {"value": 13.5, "unit": "%"},
        "Distribución eritrocitaria (RDW-SD)": {"value": 42.0, "unit": "fL"},
        "Plaquetocrito (PCT)": {"value": 0.22, "unit": "%"},
        "Eosinófilos % (EOS%)": {"value": 3.0, "unit": "%"},
    }


def test_normalizer_maps_aliases_to_ml_fields_and_ignores_unused_visible_fields() -> (
    None
):
    from app.modules.gemini_extraction.normalizer import normalize_extracted_payload

    normalized = normalize_extracted_payload(_rich_payload())

    assert normalized.normalized_data["WBC"] == 11.2
    assert normalized.normalized_data["HGB"] == 14.1
    assert normalized.normalized_data["HCT"] == 43.0
    assert normalized.normalized_data["RBC"] == 7.4
    assert normalized.normalized_data["Platelets"] == 250.0
    assert normalized.normalized_data["Reticulocytes_pct"] == 1.8
    assert normalized.normalized_data["RDW"] == 13.5
    assert "PCT" not in normalized.normalized_data
    assert "Eosinophils_pct" not in normalized.normalized_data


def test_local_txt_extraction_parses_spanish_and_analyzer_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HEMOVET_ENABLE_LOCAL_EXTRACTION", "1")
    text = """
    Leucocitos(WBC) 11,2 10^3/uL 5.5-17.0
    Hematíes(RBC) 7.40 10^6/uL 5.5-8.5
    Hemoglobina(HGB) 14.1 g/dL 12.0-18.0
    Hematocrito (HCT) 43.0 % 37-55
    MCV(MCV) 66 fL
    MCH(MCH) 21 pg
    MCHC(MCHC) 33 g/dL
    Distribución eritrocitaria (RDW-CV) 13.5 %
    Recuento total de plaquetas (EPLT) 250 10^3/uL
    Neutrófilos %(NEU%) 70 %
    Neutrófilos(NEU#) 7.8 10^3/uL
    Linfocitos %(LYM%) 20 %
    Linfocitos(LYM#) 2.2 10^3/uL
    Plaquetocrito (PCT) 0.20 %
    WBC CURVE ignored 999
    """

    extraction = extraction_service.extract_uploaded_file(
        contents=text.encode("utf-8"),
        content_type="text/plain",
        filename="hemograma.txt",
        mode="local",
    )

    assert extraction.provider == "local"
    assert extraction.extraction.cbc["WBC"] == 11.2
    assert extraction.extraction.cbc["RBC"] == 7.4
    assert extraction.extraction.cbc["HGB"] == 14.1
    assert extraction.extraction.cbc["HCT"] == 43.0
    assert extraction.extraction.cbc["RDW"] == 13.5
    assert extraction.extraction.cbc["Platelets"] == 250.0
    assert extraction.extraction.cbc["Neutrophils_pct"] == 70.0
    assert "PCT" not in extraction.extraction.cbc


def test_local_txt_parser_ignores_numbered_subitems_and_converts_gl_units(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HEMOVET_ENABLE_LOCAL_EXTRACTION", "1")
    text = """
    1.Leucocitos(WBC) 5.97 10^9/L 4.3-16.5
    1-1.Neutrófilos(NEU#) 3.80 10^9/L 2.7-12.8
    1-20.Recuento absoluto de leucocitos atípicos(AWBC#) 0.00 10^9/L 0-0
    2.Hematíes(RBC) 9.23 10^12/L 4.5-8.5
    2-1.Hemoglobina(HGB) 203.67 g/L 110-190
    2-2.Hematocrito(HCT) 67.77 % 30-56
    2-5.MCHC(MCHC) 300.54 g/L 300-380
    2-6.Distribución eritrocitaria(RDW-SD) 33.00 fL 18-37
    2-7.Distribución eritrocitaria(RDW-CV) 13.49 % 10-17
    2-13.NRBC/WBC%(NRBC/WBC) 0.00 % 0-0
    3.Recuento total de plaquetas(EPLT) 449.31 10^9/L 117-500
    3-1.Recuento absoluto de plaquetas(PLT#) 197.69 10^9/L 117-500
    Monocitos CANT.:16/378fotos Co.:0.38 x 10^9/L PCT:6.37
    """

    extraction = extraction_service.extract_uploaded_file(
        contents=text.encode("utf-8"),
        content_type="text/plain",
        filename="bengi.txt",
        mode="local",
    )

    assert extraction.extraction.cbc["WBC"] == 5.97
    assert extraction.extraction.cbc["RBC"] == 9.23
    assert extraction.extraction.cbc["HGB"] == pytest.approx(20.367)
    assert extraction.extraction.cbc["HCT"] == 67.77
    assert extraction.extraction.cbc["MCHC"] == pytest.approx(30.054)
    assert extraction.extraction.cbc["RDW"] == 13.49
    assert extraction.extraction.cbc["Platelets"] == 449.31
    assert "Monocytes" not in extraction.extraction.cbc


def test_openrouter_image_payload_uses_multimodal_content() -> None:
    from app.modules.gemini_extraction.extractors.openrouter_extractor import (
        _message_content_for_file,
    )

    content = _message_content_for_file(
        prompt="extrae JSON",
        contents=b"fake-image",
        content_type="image/jpeg",
        filename="cbc.jpeg",
    )

    assert isinstance(content, list)
    assert content[0] == {"type": "text", "text": "extrae JSON"}
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_default_attempts_skip_openrouter_unless_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.modules.gemini_extraction import service

    base_settings = {
        "openrouter_api_key": "fake",
        "openrouter_base_url": "https://openrouter.ai/api/v1",
        "openrouter_gemma_model": "gemma",
        "openrouter_nemotron_model": "nemotron",
        "openrouter_http_referer": None,
        "openrouter_x_title": "hemovet",
        "openrouter_gemma_timeout_seconds": 20,
        "openrouter_nemotron_timeout_seconds": 20,
        "gemini_extraction_timeout_seconds": 30,
        "local_extraction_timeout_seconds": 20,
        "total_timeout_seconds": 60,
        "min_valid_fields": 8,
    }

    monkeypatch.setattr(
        service,
        "get_extraction_settings",
        lambda: SimpleNamespace(openrouter_extraction_enabled=False, **base_settings),
    )
    assert [attempt.name for attempt in service.build_default_attempts()] == ["gemini", "local"]

    monkeypatch.setattr(
        service,
        "get_extraction_settings",
        lambda: SimpleNamespace(openrouter_extraction_enabled=True, **base_settings),
    )
    assert [attempt.name for attempt in service.build_default_attempts()] == [
        "gemini",
        "openrouter_gemma",
        "openrouter_nemotron",
        "local",
    ]


@dataclass
class _FakeAttempt:
    name: str
    model: str | None
    outcome: ExtractionResult | Exception

    def extract(
        self,
        *,
        contents: bytes,
        content_type: str,
        filename: str | None,
    ) -> ExtractionResult:
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def test_pipeline_tries_gemini_before_openrouter_and_local() -> None:
    from app.modules.gemini_extraction.schemas import ExtractionAttemptError
    from app.modules.gemini_extraction.service import run_extraction_pipeline

    attempted: list[str] = []

    class RecordingAttempt(_FakeAttempt):
        def extract(
            self,
            *,
            contents: bytes,
            content_type: str,
            filename: str | None,
        ) -> ExtractionResult:
            attempted.append(self.name)
            return super().extract(
                contents=contents,
                content_type=content_type,
                filename=filename,
            )

    gemini_result = ExtractionResult(
        cbc={
            "WBC": 11.2,
            "RBC": 7.4,
            "HGB": 14.1,
            "HCT": 43.0,
            "Platelets": 250.0,
            "MCV": 66.0,
            "MCH": 21.0,
            "MCHC": 33.0,
        },
        metadata={"species": "Canino"},
    )
    result = run_extraction_pipeline(
        contents=b"hemograma",
        content_type="text/plain",
        filename="hemograma.txt",
        attempts=[
            RecordingAttempt(
                "gemini",
                "gemini-3.1-flash-lite",
                gemini_result,
            ),
            RecordingAttempt(
                "openrouter_gemma",
                "google/gemma-4-31b-it:free",
                ExtractionAttemptError("OPENROUTER_TIMEOUT", "timeout"),
            ),
            RecordingAttempt("local", None, gemini_result),
        ],
        min_valid_fields=8,
    )

    assert attempted == ["gemini"]
    assert result.extraction.cbc["Platelets"] == 250.0
    assert result.extractor_used == "gemini"
    assert result.model_used == "gemini-3.1-flash-lite"
    assert result.fallback_used is False


def test_pipeline_applies_wall_timeout_per_attempt() -> None:
    from app.modules.gemini_extraction.service import run_extraction_pipeline

    attempted: list[str] = []
    fallback_result = ExtractionResult(
        cbc={
            "WBC": 11.2,
            "RBC": 7.4,
            "HGB": 14.1,
            "HCT": 43.0,
            "Platelets": 250.0,
            "MCV": 66.0,
            "MCH": 21.0,
            "MCHC": 33.0,
        },
        metadata={"species": "Canino"},
    )

    class SlowAttempt(_FakeAttempt):
        timeout_seconds = 0.01

        def extract(
            self,
            *,
            contents: bytes,
            content_type: str,
            filename: str | None,
        ) -> ExtractionResult:
            attempted.append(self.name)
            time.sleep(0.2)
            return fallback_result

    class RecordingAttempt(_FakeAttempt):
        def extract(
            self,
            *,
            contents: bytes,
            content_type: str,
            filename: str | None,
        ) -> ExtractionResult:
            attempted.append(self.name)
            return super().extract(
                contents=contents,
                content_type=content_type,
                filename=filename,
            )

    started = time.perf_counter()
    result = run_extraction_pipeline(
        contents=b"hemograma",
        content_type="text/plain",
        filename="hemograma.txt",
        attempts=[
            SlowAttempt("openrouter_nemotron", "slow-model", fallback_result),
            RecordingAttempt("gemini", "gemini-3.1-flash-lite", fallback_result),
        ],
        min_valid_fields=8,
    )

    assert time.perf_counter() - started < 0.15
    assert attempted == ["openrouter_nemotron", "gemini"]
    assert result.extractor_used == "gemini"
    assert result.fallback_used is True


def test_extraction_service_uses_remote_pipeline_for_non_tabular_uploads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.modules.gemini_extraction.schemas import PipelineExtractionResult

    extraction = ExtractionResult(
        cbc={
            "WBC": 11.2,
            "RBC": 7.4,
            "HGB": 14.1,
            "HCT": 43.0,
            "Platelets": 250.0,
            "MCV": 66.0,
            "MCH": 21.0,
            "MCHC": 33.0,
        },
        metadata={"species": "Canino"},
        comments=None,
    )

    def fake_pipeline(**kwargs: Any) -> PipelineExtractionResult:  # noqa: ARG001
        return PipelineExtractionResult(
            extraction=extraction,
            extractor_used="openrouter_gemma",
            model_used="google/gemma-4-31b-it:free",
            fallback_used=False,
            warnings=["Extraccion remota completada con OpenRouter Gemma."],
            valid_fields_count=8,
            duration_ms=10,
        )

    monkeypatch.setattr(
        extraction_service, "extract_hemogram_with_fallbacks", fake_pipeline
    )

    output = extraction_service.extract_uploaded_file(
        contents=b"cbc",
        content_type="application/pdf",
        filename="cbc.pdf",
        mode="auto",
    )

    assert output.provider == "gemini"
    assert output.fallback_used is False
    assert output.warnings == []
    assert output.extraction.cbc["WBC"] == 11.2


def test_extraction_service_hides_model_fallback_details_from_public_warnings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.modules.gemini_extraction.schemas import PipelineExtractionResult

    extraction = ExtractionResult(
        cbc={
            "WBC": 11.2,
            "RBC": 7.4,
            "HGB": 14.1,
            "HCT": 43.0,
            "Platelets": 250.0,
            "MCV": 66.0,
            "MCH": 21.0,
            "MCHC": 33.0,
        },
        metadata={"species": "Canino"},
        comments=None,
    )

    def fake_pipeline(**kwargs: Any) -> PipelineExtractionResult:  # noqa: ARG001
        return PipelineExtractionResult(
            extraction=extraction,
            extractor_used="openrouter_nemotron",
            model_used="nvidia/nemotron-nano-12b-v2-vl:free",
            fallback_used=True,
            warnings=[
                "openrouter_gemma produjo pocos campos validos.",
                "Gemini excedio el timeout de extraccion.",
            ],
            errors=["OPENROUTER_TIMEOUT", "GEMINI_TIMEOUT"],
            valid_fields_count=8,
            duration_ms=1000,
        )

    monkeypatch.setattr(
        extraction_service, "extract_hemogram_with_fallbacks", fake_pipeline
    )

    output = extraction_service.extract_uploaded_file(
        contents=b"cbc",
        content_type="text/plain",
        filename="cbc.txt",
        mode="auto",
    )

    public_text = " ".join(output.warnings).lower()
    assert output.fallback_used is True
    assert "gemini" not in public_text
    assert "openrouter" not in public_text
    assert "nemotron" not in public_text
    assert "gemma" not in public_text
    assert "modelo" not in public_text


def test_extraction_service_returns_generic_message_when_pipeline_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.modules.gemini_extraction.schemas import ExtractionAttemptError

    def fake_pipeline(**kwargs: Any) -> object:  # noqa: ARG001
        raise ExtractionAttemptError(
            "GEMINI_TIMEOUT",
            "Gemini excedio el timeout de extraccion.",
        )

    monkeypatch.setattr(
        extraction_service, "extract_hemogram_with_fallbacks", fake_pipeline
    )

    with pytest.raises(extraction_service.ExtractionError) as exc_info:
        extraction_service.extract_uploaded_file(
            contents=b"cbc",
            content_type="text/plain",
            filename="cbc.txt",
            mode="auto",
        )

    public_message = str(exc_info.value).lower()
    assert "gemini" not in public_message
    assert "openrouter" not in public_message
    assert "modelo" not in public_message
