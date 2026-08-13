from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.hematology import extractor  # noqa: E402
from app.modules.hematology.extraction_service import (  # noqa: E402
    ExtractionServiceResult,
    extract_uploaded_file,
)  # noqa: E402
from app.modules.gemini_extraction.client import (  # noqa: E402
    GeminiCbcValues,
    GeminiExtractionConfig,
    GeminiExtractionError,
    GeminiExtractor,
    get_gemini_config_from_env,
    inspect_gemini_runtime,
    _prepare_file_for_gemini,
)


class _FakeFile:
    name = "files/fake-cbc"
    state = SimpleNamespace(name="ACTIVE")


class _FakeFiles:
    def __init__(self) -> None:
        self.deleted: list[str] = []
        self.upload_config: dict | None = None

    def upload(self, *, file, config):  # noqa: ANN001
        self.upload_config = config
        return _FakeFile()

    def get(self, *, name: str):  # noqa: ARG002
        return _FakeFile()

    def delete(self, *, name: str) -> None:
        self.deleted.append(name)


class _FakeModels:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.config: dict | None = None
        self.contents: list | None = None

    def generate_content(
        self, *, model: str, contents: list, config: dict
    ):  # noqa: ARG002
        self.config = config
        self.contents = contents
        return SimpleNamespace(text=self.response_text)


class _FakeClient:
    def __init__(self, response_text: str) -> None:
        self.files = _FakeFiles()
        self.models = _FakeModels(response_text)


class GeminiExtractionTests(unittest.TestCase):
    def test_gemini_cbc_schema_is_developer_api_compatible(self) -> None:
        self.assertNotIn(
            "additionalProperties",
            json.dumps(GeminiCbcValues.model_json_schema()),
        )

    def test_pdf_with_extractable_text_is_sent_to_gemini_as_text(self) -> None:
        with patch(
            "app.modules.gemini_extraction.client._pdf_to_text",
            return_value="WBC 11.2\n" * 20,
        ):
            file_bytes, mime_type, upload_name = _prepare_file_for_gemini(
                contents=b"%PDF fake",
                content_type="application/pdf",
                filename="cbc.pdf",
            )

        self.assertEqual(mime_type, "text/plain")
        self.assertEqual(upload_name, "cbc.pdf.txt")
        self.assertIn("Texto extraído localmente", file_bytes.decode("utf-8"))

    def test_coerce_lab_number_removes_analyzer_flags(self) -> None:
        self.assertEqual(extractor._coerce_lab_number("0.02*"), 0.02)
        self.assertEqual(extractor._coerce_lab_number("*0.02"), 0.02)
        self.assertEqual(extractor._coerce_lab_number("<5"), 5.0)
        self.assertEqual(extractor._coerce_lab_number("1,25"), 1.25)

    def test_csv_extraction_accepts_flagged_numeric_values(self) -> None:
        contents = b"WBC,RBC,HGB,HCT,Platelets\n12.3*,7.1,14.2,42,*250\n"
        extraction = extractor.extract_from_file(contents, "text/csv")

        self.assertEqual(extraction.cbc["WBC"], 12.3)
        self.assertEqual(extraction.cbc["Platelets"], 250.0)

    def test_gemini_extractor_parses_structured_payload_and_deletes_file(self) -> None:
        payload = {
            "cbc": {
                "WBC": 11.2,
                "RBC": 7.4,
                "HGB": 14.1,
                "HCT": 43.0,
                "Platelets": "250*",
                "Basophils": "0.02*",
            },
            "metadata": {"species": "Canine", "patient_name": "Luna"},
            "comments": "Platelet aggregates suspected.",
            "warnings": ["valor marcado por el analizador"],
        }
        fake_client = _FakeClient(json.dumps(payload))
        gemini = GeminiExtractor(
            config=GeminiExtractionConfig(api_key="fake-key", model="fake-model"),
            client_factory=lambda config: fake_client,  # noqa: ARG005
        )

        output = gemini.extract(
            contents=b"%PDF fake",
            content_type="application/pdf",
            filename="cbc.pdf",
        )

        self.assertEqual(output.extraction.cbc["Platelets"], 250.0)
        self.assertEqual(output.extraction.cbc["Basophils"], 0.02)
        self.assertEqual(output.extraction.metadata["species"], "Canine")
        self.assertEqual(output.warnings, ["valor marcado por el analizador"])
        self.assertEqual(fake_client.files.deleted, ["files/fake-cbc"])
        self.assertEqual(
            fake_client.files.upload_config["mime_type"], "application/pdf"
        )
        self.assertEqual(
            (fake_client.models.config or {}).get("response_mime_type"),
            "application/json",
        )
        self.assertIn("response_schema", fake_client.models.config or {})

    def test_gemini_extractor_sends_small_text_inline_without_files_api(self) -> None:
        payload = {
            "cbc": {
                "WBC": 11.2,
                "RBC": 7.4,
                "HGB": 14.1,
                "HCT": 43.0,
                "Platelets": 250,
            },
            "metadata": {"species": "Canine"},
            "comments": None,
            "warnings": [],
        }
        fake_client = _FakeClient(json.dumps(payload))
        gemini = GeminiExtractor(
            config=GeminiExtractionConfig(api_key="fake-key", model="fake-model"),
            client_factory=lambda config: fake_client,  # noqa: ARG005
        )

        output = gemini.extract(
            contents=b"WBC,RBC,HGB,HCT,Platelets\n11.2,7.4,14.1,43,250\n",
            content_type="text/plain",
            filename="cbc.txt",
        )

        self.assertEqual(output.extraction.cbc["WBC"], 11.2)
        self.assertIsNone(fake_client.files.upload_config)
        self.assertEqual(fake_client.files.deleted, [])
        self.assertTrue(
            any("HEMOGRAM_CONTENT" in str(item) for item in fake_client.models.contents or [])
        )

    def test_gemini_extractor_accepts_partial_payload_for_human_review(self) -> None:
        payload = {
            "cbc": {
                "WBC": 11.2,
            },
            "metadata": {"species": "Canine", "patient_name": "Luna"},
            "comments": None,
            "warnings": [],
        }
        fake_client = _FakeClient(json.dumps(payload))
        gemini = GeminiExtractor(
            config=GeminiExtractionConfig(api_key="fake-key", model="fake-model"),
            client_factory=lambda config: fake_client,  # noqa: ARG005
        )

        output = gemini.extract(
            contents=b"%PDF fake",
            content_type="application/pdf",
            filename="cbc.pdf",
        )

        self.assertEqual(output.extraction.cbc, {"WBC": 11.2})
        self.assertEqual(output.extraction.metadata["species"], "Canine")

    def test_gemini_extractor_rejects_invalid_json(self) -> None:
        fake_client = _FakeClient("no-json")
        gemini = GeminiExtractor(
            config=GeminiExtractionConfig(api_key="fake-key", model="fake-model"),
            client_factory=lambda config: fake_client,  # noqa: ARG005
        )

        with self.assertRaises(GeminiExtractionError) as ctx:
            gemini.extract(
                contents=b"%PDF fake",
                content_type="application/pdf",
                filename="cbc.pdf",
            )

        self.assertEqual(ctx.exception.error_code, "GEMINI_INVALID_JSON")
        self.assertEqual(fake_client.files.deleted, ["files/fake-cbc"])

    def test_auto_mode_uses_local_extractor_first_for_csv(self) -> None:
        contents = b"WBC,RBC,HGB,HCT,Platelets\n12.3,7.1,14.2,42,250\n"

        with patch(
            "app.modules.hematology.extraction_service.extract_hemogram_with_fallbacks",
        ) as pipeline:
            output = extract_uploaded_file(
                contents=contents,
                content_type="text/csv",
                filename="cbc.csv",
                mode="auto",
            )

        pipeline.assert_not_called()
        self.assertEqual(output.provider, "local")
        self.assertFalse(output.fallback_used)
        self.assertEqual(output.extraction.cbc["WBC"], 12.3)

    def test_gemini_mode_uses_local_extractor_first_for_csv(self) -> None:
        contents = b"WBC,RBC,HGB,HCT,Platelets\n12.3,7.1,14.2,42,250\n"

        with patch(
            "app.modules.hematology.extraction_service.extract_hemogram_with_fallbacks",
        ) as pipeline:
            output = extract_uploaded_file(
                contents=contents,
                content_type="text/csv",
                filename="cbc.csv",
                mode="gemini",
            )

        pipeline.assert_not_called()
        self.assertEqual(output.provider, "local")
        self.assertEqual(output.mode, "auto")
        self.assertFalse(output.fallback_used)

    def test_gemini_health_does_not_expose_api_key(self) -> None:
        old_env = os.environ.copy()
        try:
            os.environ["GEMINI_API_KEY"] = "secret-key"
            os.environ["GEMINI_MODEL"] = "fake-model"
            status = inspect_gemini_runtime()
        finally:
            os.environ.clear()
            os.environ.update(old_env)

        self.assertTrue(status["configured"])
        self.assertEqual(status["model"], "fake-model")
        self.assertNotIn("secret-key", json.dumps(status))

    def test_gemini_config_uses_central_settings_when_environment_is_not_exported(
        self,
    ) -> None:
        settings = SimpleNamespace(
            GEMINI_API_KEY="settings-key",
            GEMINI_MODEL="settings-model",
            GEMINI_TIMEOUT_SECONDS=12,
            GEMINI_FILE_POLL_SECONDS=3,
            GEMINI_FILE_POLL_MAX_ATTEMPTS=4,
            GEMINI_INLINE_TEXT_MAX_BYTES=1234,
        )
        with (
            patch("app.modules.gemini_extraction.client.settings", settings),
            patch.dict(os.environ, {}, clear=True),
        ):
            config = get_gemini_config_from_env()

        self.assertEqual(config.api_key, "settings-key")
        self.assertEqual(config.model, "settings-model")
        self.assertEqual(config.timeout_seconds, 12)
        self.assertEqual(config.inline_text_max_bytes, 1234)


class GeminiExtractionApiTests(unittest.TestCase):
    def test_extract_endpoint_returns_provider_metadata(self) -> None:
        from app.modules.hematology.schemas import (  # noqa: PLC0415
            ExtractionDebugResponse,
        )

        service_result = ExtractionServiceResult(
            extraction=extractor.ExtractionResult(
                cbc={
                    "WBC": 12.3,
                    "RBC": 7.1,
                    "HGB": 14.2,
                    "HCT": 42.0,
                    "Platelets": 250.0,
                },
                metadata={"species": "Canino", "patient_name": "Luna"},
                comments="Comentario del analizador.",
            ),
            provider="gemini",
            mode="auto",
            warnings=["valor marcado por el analizador"],
        )

        response = ExtractionDebugResponse(
            cbc=service_result.extraction.cbc,
            metadata=service_result.extraction.metadata,
            comments=service_result.extraction.comments,
            extraction_provider=service_result.provider,
            extraction_mode=service_result.mode,
            warnings=service_result.warnings,
        )

        payload = response.model_dump()
        self.assertEqual(payload["extraction_provider"], "gemini")
        self.assertEqual(payload["extraction_mode"], "auto")
        self.assertEqual(payload["cbc"]["Platelets"], 250.0)
        self.assertEqual(payload["warnings"], ["valor marcado por el analizador"])


if __name__ == "__main__":
    unittest.main()
