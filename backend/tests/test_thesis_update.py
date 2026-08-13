from __future__ import annotations

import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import csv

import xml.etree.ElementTree as ET
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.update_thesis_results import (  # noqa: E402
    build_metrics_summary,
    insert_paragraphs_before_prefix,
    replace_paragraph_texts,
)


class ThesisUpdateTests(unittest.TestCase):
    def _sample_docx(self, filename: str, xml: str) -> Path:
        tmp_dir = PROJECT_ROOT / "outputs" / "tmp_thesis_test"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        docx_path = tmp_dir / filename
        if docx_path.exists():
            docx_path.unlink()
        with ZipFile(docx_path, "w", ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", "<Types />")
            zf.writestr("word/document.xml", xml)
        return docx_path

    def test_build_metrics_summary_uses_verified_metric_sources(self) -> None:
        summary = build_metrics_summary(PROJECT_ROOT)
        with (PROJECT_ROOT / "data" / "processed" / "test.csv").open(
            encoding="utf-8", newline=""
        ) as handle:
            expected_test_n = str(sum(1 for _ in csv.DictReader(handle)))

        self.assertEqual(summary["official"]["macro_pr_auc"], "0.9529")
        self.assertEqual(summary["official"]["test_n"], expected_test_n)
        self.assertEqual(
            summary["official_labels"]["QC_REQUIERE_FROTIS"]["f1"], "0.7111"
        )
        self.assertEqual(
            summary["official_labels"]["PATRON_POLICITEMIA"]["pr_auc"], "1.0000"
        )
        self.assertEqual(
            summary["non_official_metrics"]["PATRON_ANEMIA_REGENERATIVA"][
                "test_positive"
            ],
            "6",
        )
        self.assertEqual(
            summary["non_official_metrics"]["QC_AGREGADOS_PLAQUETARIOS"][
                "output_method"
            ],
            "deterministic_rule",
        )
        self.assertIn("QC_UNIDAD_NO_CONVERTIDA", summary["policy"]["excluded_labels"])
        self.assertEqual(summary["dap"]["n"], "1301")
        self.assertEqual(
            summary["dap"]["rates"]["PATRON_INFLAMATORIO"]["dap_pct"], "1.77"
        )

    def test_replace_paragraph_texts_updates_docx_xml_without_losing_document_package(
        self,
    ) -> None:
        ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:document xmlns:w="{ns}"><w:body>'
            "<w:p><w:r><w:t>macro PR-AUC de 0,9497</w:t></w:r></w:p>"
            "<w:p><w:r><w:t>texto sin cambios</w:t></w:r></w:p>"
            "</w:body></w:document>"
        )

        docx_path = self._sample_docx("replace.docx", xml)
        count = replace_paragraph_texts(
            docx_path,
            {"macro PR-AUC de 0,9497": "macro PR-AUC de 0,9495"},
        )

        self.assertEqual(count, 1)
        with ZipFile(docx_path) as zf:
            self.assertIn("[Content_Types].xml", zf.namelist())
            updated = zf.read("word/document.xml")

        root = ET.fromstring(updated)
        texts = [
            node.text
            for node in root.findall(
                ".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"
            )
        ]
        self.assertIn("macro PR-AUC de 0,9495", texts)
        self.assertIn("texto sin cambios", texts)

    def test_replace_paragraph_texts_preserves_declared_word_namespaces(self) -> None:
        ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        mc = "http://schemas.openxmlformats.org/markup-compatibility/2006"
        w14 = "http://schemas.microsoft.com/office/word/2010/wordml"
        xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:document xmlns:w="{ns}" xmlns:mc="{mc}" xmlns:w14="{w14}" mc:Ignorable="w14">'
            "<w:body>"
            "<w:p><w:r><w:t>macro PR-AUC de 0,9497</w:t></w:r></w:p>"
            "</w:body></w:document>"
        )

        docx_path = self._sample_docx("namespaces.docx", xml)
        replace_paragraph_texts(
            docx_path, {"macro PR-AUC de 0,9497": "macro PR-AUC de 0,9495"}
        )

        with ZipFile(docx_path) as zf:
            updated = zf.read("word/document.xml").decode("utf-8")

        self.assertIn("xmlns:mc=", updated)
        self.assertIn("xmlns:w14=", updated)
        self.assertIn('mc:Ignorable="w14"', updated)

    def test_insert_paragraphs_before_prefix_adds_audit_section_before_references(
        self,
    ) -> None:
        ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:document xmlns:w="{ns}"><w:body>'
            "<w:p><w:r><w:t>Conclusion original</w:t></w:r></w:p>"
            "<w:p><w:r><w:t>[1] Referencia bibliografica</w:t></w:r></w:p>"
            "<w:sectPr />"
            "</w:body></w:document>"
        )

        docx_path = self._sample_docx("insert.docx", xml)
        count = insert_paragraphs_before_prefix(
            docx_path,
            "[1]",
            ["Metricas verificadas", "PR-AUC macro oficial: 0.9495"],
        )

        self.assertEqual(count, 2)
        with ZipFile(docx_path) as zf:
            updated = zf.read("word/document.xml")

        root = ET.fromstring(updated)
        texts = [
            node.text
            for node in root.findall(
                ".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"
            )
        ]
        self.assertEqual(
            texts,
            [
                "Conclusion original",
                "Metricas verificadas",
                "PR-AUC macro oficial: 0.9495",
                "[1] Referencia bibliografica",
            ],
        )

    def test_insert_paragraphs_before_prefix_replaces_existing_audit_section(
        self,
    ) -> None:
        ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:document xmlns:w="{ns}"><w:body>'
            "<w:p><w:r><w:t>Conclusion original</w:t></w:r></w:p>"
            "<w:p><w:r><w:t>Metricas verificadas</w:t></w:r></w:p>"
            "<w:p><w:r><w:t>Linea antigua</w:t></w:r></w:p>"
            "<w:p><w:r><w:t>[1] Referencia bibliografica</w:t></w:r></w:p>"
            "<w:sectPr />"
            "</w:body></w:document>"
        )

        docx_path = self._sample_docx("upsert.docx", xml)
        count = insert_paragraphs_before_prefix(
            docx_path,
            "[1]",
            ["Metricas verificadas", "Linea nueva"],
        )

        self.assertEqual(count, 2)
        with ZipFile(docx_path) as zf:
            updated = zf.read("word/document.xml")

        root = ET.fromstring(updated)
        texts = [
            node.text
            for node in root.findall(
                ".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"
            )
        ]
        self.assertEqual(
            texts,
            [
                "Conclusion original",
                "Metricas verificadas",
                "Linea nueva",
                "[1] Referencia bibliografica",
            ],
        )


if __name__ == "__main__":
    unittest.main()
