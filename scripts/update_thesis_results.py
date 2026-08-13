from __future__ import annotations

import argparse
import csv
import json
import shutil
import xml.etree.ElementTree as ET
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
ET.register_namespace("w", W_NS)

OFFICIAL_ORDER = [
    "QC_REQUIERE_FROTIS",
    "PATRON_INFLAMATORIO",
    "PATRON_LEUCOGRAMA_ESTRES",
    "PATRON_ANEMIA_NO_REGENERATIVA",
    "PATRON_HEMOLISIS_MCHC",
    "PATRON_POLICITEMIA",
]

NON_OFFICIAL_METRIC_ORDER = [
    "QC_AGREGADOS_PLAQUETARIOS",
    "PATRON_ANEMIA_REGENERATIVA",
]


def _w(tag: str) -> str:
    return f"{{{W_NS}}}{tag}"


def _fmt4(value: object) -> str:
    return f"{float(value):.4f}"


def _fmt_threshold(value: object) -> str:
    return f"{float(value):.10f}"


def _fmt_pct(value: object) -> str:
    return f"{float(value) * 100:.2f}"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_document(docx_path: Path) -> tuple[ET.Element, dict[str, str]]:
    with ZipFile(docx_path, "r") as archive:
        document_xml = archive.read("word/document.xml")
    namespaces: dict[str, str] = {}
    for _, namespace in ET.iterparse(BytesIO(document_xml), events=("start-ns",)):
        prefix, uri = namespace
        if prefix and prefix != "xml":
            namespaces.setdefault(prefix, uri)
            if not (prefix.startswith("ns") and prefix[2:].isdigit()):
                ET.register_namespace(prefix, uri)
    return ET.fromstring(document_xml), namespaces


def _document_xml_bytes(root: ET.Element, namespaces: dict[str, str]) -> bytes:
    xml_text = ET.tostring(root, encoding="unicode", xml_declaration=True)
    declaration_end = xml_text.find("?>")
    root_start = xml_text.find("<", declaration_end + 2)
    root_end = xml_text.find(">", root_start)
    root_tag = xml_text[root_start:root_end]
    missing_declarations = "".join(
        f' xmlns:{prefix}="{uri}"'
        for prefix, uri in namespaces.items()
        if f"xmlns:{prefix}=" not in root_tag
    )
    if missing_declarations:
        xml_text = xml_text[:root_end] + missing_declarations + xml_text[root_end:]
    return xml_text.encode("utf-8")


def _csv_row_count(path: Path) -> int:
    with path.open(encoding="utf-8", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def _paragraph_text(paragraph: ET.Element) -> str:
    return "".join(node.text or "" for node in paragraph.findall(f".//{_w('t')}"))


def _set_paragraph_text(paragraph: ET.Element, text: str) -> None:
    text_nodes = paragraph.findall(f".//{_w('t')}")
    if text_nodes:
        text_nodes[0].text = text
        for node in text_nodes[1:]:
            node.text = ""
        return
    run = ET.SubElement(paragraph, _w("r"))
    text_node = ET.SubElement(run, _w("t"))
    text_node.text = text


def _simple_paragraph(text: str) -> ET.Element:
    paragraph = ET.Element(_w("p"))
    run = ET.SubElement(paragraph, _w("r"))
    text_node = ET.SubElement(run, _w("t"))
    if text[:1].isspace() or text[-1:].isspace():
        text_node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    text_node.text = text
    return paragraph


def _rewrite_docx_xml(docx_path: Path, document_xml: bytes) -> None:
    tmp_path = docx_path.with_suffix(docx_path.suffix + ".tmp")
    with ZipFile(docx_path, "r") as zin, ZipFile(tmp_path, "w", ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            payload = document_xml if item.filename == "word/document.xml" else zin.read(item.filename)
            zout.writestr(item, payload)
    tmp_path.replace(docx_path)


def build_metrics_summary(project_root: Path) -> dict[str, object]:
    metrics_v2 = _read_json(project_root / "data" / "processed" / "metrics_test_v2.json")
    metrics_final = _read_json(project_root / "data" / "processed" / "metrics_test_final.json")
    label_policy = _read_json(project_root / "data" / "processed" / "final_label_policy.json")
    final_state = _read_json(project_root / "outputs" / "final_system_state.json")
    dap_summary = _read_json(project_root / "outputs" / "nb06_validation_summary.json")
    label_details = label_policy.get("label_details", {})

    official_labels: dict[str, dict[str, str]] = {}
    for label in OFFICIAL_ORDER:
        row = metrics_v2["metrics"][label]
        official_labels[label] = {
            "pr_auc": _fmt4(row["pr_auc"]),
            "roc_auc": _fmt4(row["roc_auc"]),
            "f1": _fmt4(row["f1_optimal_thresh"]),
            "threshold": _fmt_threshold(row["threshold_used"]),
            "test_positive": str(int(row["n_positive_test"])),
        }

    non_official_metrics: dict[str, dict[str, str]] = {}
    for label in NON_OFFICIAL_METRIC_ORDER:
        row = metrics_final["metrics"][label]
        policy_row = label_details.get(label, {})
        non_official_metrics[label] = {
            "pr_auc": _fmt4(row["pr_auc"]),
            "roc_auc": _fmt4(row["roc_auc"]),
            "f1": _fmt4(row["f1_optimal_thresh"]),
            "test_positive": str(int(row["n_positive_test"])),
            "ic95": str(row.get("bootstrap_ic_95") or ""),
            "output_method": str(policy_row.get("output_method", "unknown")),
            "policy_status": str(policy_row.get("status", "unknown")),
        }

    rates: dict[str, dict[str, str]] = {}
    rates_path = project_root / "outputs" / "activation_rates_comparison.csv"
    with rates_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            label = row.get("") or row.get("label")
            if not label:
                continue
            rates[label] = {
                "idexx_pct": _fmt_pct(row["idexx_rate"]),
                "dap_pct": _fmt_pct(row["dap_rate"]),
                "diagnosis": row.get("diagnosis", ""),
            }

    return {
        "official": {
            "macro_pr_auc": _fmt4(metrics_v2["prauc_macro"]),
            "test_n": str(_csv_row_count(project_root / "data" / "processed" / "test.csv")),
            "model": str(metrics_v2["model"]),
            "n_labels": str(label_policy.get("n_model_labels", metrics_v2["n_labels"])),
            "status": str(final_state.get("status", "")),
        },
        "official_labels": official_labels,
        "non_official_metrics": non_official_metrics,
        "policy": {
            "rule_labels": list(label_policy.get("rule_labels", [])),
            "excluded_labels": list(label_policy.get("excluded_labels", [])),
        },
        "dap": {
            "n": str(int(dap_summary["dap_n_records"])),
            "rates": rates,
            "limitations": list(dap_summary.get("limitations", [])),
            "domain_shift_severe": list(dap_summary.get("domain_shift_severe", [])),
            "domain_shift_moderate": list(dap_summary.get("domain_shift_moderate", [])),
        },
    }


def replace_paragraph_texts(docx_path: Path, replacements: dict[str, str]) -> int:
    root, namespaces = _read_document(docx_path)

    count = 0
    for paragraph in root.findall(f".//{_w('p')}"):
        current = _paragraph_text(paragraph)
        replacement = replacements.get(current)
        if replacement is None:
            continue
        _set_paragraph_text(paragraph, replacement)
        count += 1

    if count:
        _rewrite_docx_xml(docx_path, _document_xml_bytes(root, namespaces))
    return count


def insert_paragraphs_before_prefix(docx_path: Path, prefix: str, paragraphs: list[str]) -> int:
    root, namespaces = _read_document(docx_path)

    body = root.find(f".//{_w('body')}")
    if body is None:
        raise ValueError("word/document.xml does not contain a w:body element")

    insert_at = None
    body_children = list(body)
    existing_start = None
    for index, child in enumerate(body_children):
        if child.tag != _w("p"):
            continue
        text = _paragraph_text(child)
        if paragraphs and text == paragraphs[0]:
            existing_start = index
            break

    if existing_start is not None:
        remove_until = len(body_children)
        for index, child in enumerate(body_children[existing_start + 1 :], start=existing_start + 1):
            if child.tag == _w("p") and _paragraph_text(child).startswith(prefix):
                remove_until = index
                break
        for child in body_children[existing_start:remove_until]:
            body.remove(child)
        insert_at = existing_start
    else:
        for index, child in enumerate(body_children):
            if child.tag != _w("p"):
                continue
            if _paragraph_text(child).startswith(prefix):
                insert_at = index
                break
    if insert_at is None:
        insert_at = max(0, len(list(body)) - 1)

    for offset, text in enumerate(paragraphs):
        body.insert(insert_at + offset, _simple_paragraph(text))

    _rewrite_docx_xml(docx_path, _document_xml_bytes(root, namespaces))
    return len(paragraphs)


def extract_paragraphs(docx_path: Path) -> list[str]:
    root, _ = _read_document(docx_path)
    return [_paragraph_text(p).strip() for p in root.findall(f".//{_w('p')}") if _paragraph_text(p).strip()]


def _find_paragraph(paragraphs: list[str], needle: str) -> str | None:
    for paragraph in paragraphs:
        if needle in paragraph:
            return paragraph
    return None


def _replacement_paragraphs(summary: dict[str, object]) -> dict[str, str]:
    official = summary["official"]  # type: ignore[index]
    dap = summary["dap"]  # type: ignore[index]
    rates = dap["rates"]  # type: ignore[index]
    inflamatorio = rates["PATRON_INFLAMATORIO"]  # type: ignore[index]
    anemia = rates["PATRON_ANEMIA_NO_REGENERATIVA"]  # type: ignore[index]
    stress = rates["PATRON_LEUCOGRAMA_ESTRES"]  # type: ignore[index]

    return {
        "abstract_result": (
            "El motor de clasificación alcanzó un PR-AUC macro de "
            f"{str(official['macro_pr_auc']).replace('.', ',')} sobre seis patrones hematológicos oficiales, "
            "evaluado en un conjunto de test de 369 registros correspondientes al período octubre 2025 - febrero 2026. "
            f"La validación externa sobre {dap['n']} registros del Dog Aging Project (EE. UU.) se interpreta como "
            "validación de coherencia biológica y distribución, no como performance supervisada externa, porque DAP no "
            "incluye labels equivalentes para calcular F1 ni PR-AUC. En esa cohorte predominantemente sana, "
            f"PATRON_INFLAMATORIO se activó en {inflamatorio['dap_pct']}% frente a {inflamatorio['idexx_pct']}% "
            f"en IDEXX local; PATRON_ANEMIA_NO_REGENERATIVA en {anemia['dap_pct']}% frente a {anemia['idexx_pct']}%; "
            f"y PATRON_LEUCOGRAMA_ESTRES en {stress['dap_pct']}% frente a {stress['idexx_pct']}%."
        ),
        "english_result": (
            "The classification engine achieved a macro PR-AUC of "
            f"{official['macro_pr_auc']} across six official hematological patterns, evaluated on a {official['test_n']}-record "
            f"test set spanning October 2025 to February 2026. External validation on {dap['n']} Dog Aging Project records "
            "supports biological and distributional coherence, but it is not supervised external performance because "
            "DAP does not provide equivalent labels for F1 or PR-AUC calculation."
        ),
        "domain_shift": (
            "En quinto lugar, la validación externa sobre el Dog Aging Project mostró que el domain shift entre una "
            "población clínica tropical y una cohorte sana norteamericana es cuantificable y biológicamente coherente. "
            "Este hallazgo no debe interpretarse como prueba definitiva de generalización supervisada, porque DAP no "
            "aporta etiquetas equivalentes para medir F1 o PR-AUC; su valor es confirmar tasas de activación plausibles "
            "en una cohorte externa y señalar la necesidad de validaciones clínicas regionales adicionales."
        ),
        "conclusion": (
            "En conclusión, la plataforma HemoVet demostró que un sistema de interpretación hematológica canina, "
            "basado en aprendizaje automático y con un macro PR-AUC de 0,9495 en seis patrones hematológicos oficiales, "
            "era técnicamente viable. La validación actual respalda el rendimiento interno sobre test y la coherencia "
            "distribucional externa en DAP, mientras que la puesta en producción requiere completar la trazabilidad de "
            "artefactos, validar el runtime dockerizado con Ollama disponible como dependencia externa y ejecutar pruebas "
            "clínicas formales de aceptación por veterinarios."
        ),
        "single_command": (
            "La plataforma está dockerizada con tres servicios (backend FastAPI, portal React y PostgreSQL). El despliegue "
            "del stack de aplicación se realiza con Docker Compose; el módulo conversacional requiere además un servicio "
            "Ollama externo accesible desde el contenedor backend mediante OLLAMA_BASE_URL."
        ),
    }


def _audit_lines(summary: dict[str, object]) -> list[str]:
    official = summary["official"]  # type: ignore[index]
    official_labels = summary["official_labels"]  # type: ignore[index]
    non_official_metrics = summary["non_official_metrics"]  # type: ignore[index]
    policy = summary["policy"]  # type: ignore[index]
    dap = summary["dap"]  # type: ignore[index]
    rates = dap["rates"]  # type: ignore[index]

    lines = [
        "Anexo técnico: métricas reales verificadas",
        "Fuente primaria de métricas: data/processed/metrics_test_v2.json, data/processed/metrics_test_final.json, outputs/final_system_state.json y outputs/activation_rates_comparison.csv.",
        f"Resumen oficial: modelo {official['model']}, seis etiquetas oficiales, test n={official['test_n']}, PR-AUC macro={official['macro_pr_auc']}.",
        "Tabla de métricas oficiales (Etiqueta | PR-AUC | ROC-AUC | F1-opt | Umbral | Test+):",
    ]
    for label in OFFICIAL_ORDER:
        row = official_labels[label]
        lines.append(
            f"{label} | {row['pr_auc']} | {row['roc_auc']} | {row['f1']} | {row['threshold']} | {row['test_positive']}"
        )
    lines.extend(
        [
            "Etiquetas fuera del modelo oficial con metrica historica (Etiqueta | Metodo/politica | PR-AUC | ROC-AUC | F1-opt | Test+ | IC95):",
        ]
    )
    for label in NON_OFFICIAL_METRIC_ORDER:
        row = non_official_metrics[label]
        lines.append(
            f"{label} | {row['output_method']}/{row['policy_status']} | {row['pr_auc']} | {row['roc_auc']} | {row['f1']} | {row['test_positive']} | {row['ic95']}"
        )
    measured_non_official = set(NON_OFFICIAL_METRIC_ORDER)
    policy_without_metric = [
        label
        for label in list(policy["rule_labels"]) + list(policy["excluded_labels"])
        if label not in measured_non_official
    ]
    if policy_without_metric:
        lines.append(
            "Etiquetas de politica sin metrica supervisada en metrics_test_final.json: "
            + ", ".join(policy_without_metric)
            + "."
        )
    lines.extend(
        [
            f"Validación externa DAP: n={dap['n']}. No se reporta F1 ni PR-AUC externo porque DAP no tiene labels equivalentes.",
            "Tasas de activación IDEXX test vs DAP (Etiqueta | IDEXX % | DAP % | diagnóstico de coherencia):",
        ]
    )
    for label in OFFICIAL_ORDER:
        row = rates[label]
        lines.append(f"{label} | {row['idexx_pct']} | {row['dap_pct']} | {row['diagnosis']}")
    lines.extend(
        [
            "Correcciones aplicadas: macro PR-AUC 0,9497 corregido a 0,9495; validación DAP redactada como coherencia biológica/distribucional; Ollama descrito como dependencia externa; se evitó afirmar performance supervisada externa.",
            "Limitaciones operativas detectadas y tratadas: outputs/ debía montarse en backend para exponer métricas/gates; artifact_manifest_v2.json, policy_freeze_v3.json y policy_preregistered_v3.json fueron restaurados desde los artefactos actuales; los tests RAG pueden fallar por permisos de temporales en Windows si no se ajusta TMP/TEMP.",
        ]
    )
    return lines


def write_audit_markdown(project_root: Path, summary: dict[str, object], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(_audit_lines(summary)) + "\n", encoding="utf-8")


def update_docx(project_root: Path, docx_path: Path) -> dict[str, int | str]:
    if not docx_path.exists():
        raise FileNotFoundError(docx_path)

    backup_path = docx_path.with_name(docx_path.stem + ".backup-original" + docx_path.suffix)
    if not backup_path.exists():
        shutil.copy2(docx_path, backup_path)

    summary = build_metrics_summary(project_root)
    replacements_by_role = _replacement_paragraphs(summary)
    current_paragraphs = extract_paragraphs(docx_path)

    replacement_map: dict[str, str] = {}
    target_specs = {
        "abstract_result": "El motor de clasificación alcanzó un PR-AUC macro",
        "english_result": "The classification engine achieved a macro PR-AUC",
        "domain_shift": "En quinto lugar, la validación externa sobre el Dog Aging Project",
        "conclusion": "En conclusión, la plataforma HemoVet demostró",
        "single_command": "La plataforma está dockerizada con tres servicios",
    }
    for role, needle in target_specs.items():
        existing = _find_paragraph(current_paragraphs, needle)
        if existing is not None:
            replacement_map[existing] = replacements_by_role[role]

    replaced = replace_paragraph_texts(docx_path, replacement_map)
    inserted = insert_paragraphs_before_prefix(docx_path, "[1]", _audit_lines(summary))
    audit_path = project_root / "outputs" / "thesis_metrics_audit.md"
    write_audit_markdown(project_root, summary, audit_path)

    return {
        "backup": str(backup_path),
        "audit": str(audit_path),
        "paragraphs_replaced": replaced,
        "paragraphs_inserted": inserted,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Update thesis DOCX result claims with verified metrics.")
    parser.add_argument("--project-root", default=".", type=Path)
    parser.add_argument("--docx", required=True, type=Path)
    args = parser.parse_args()

    result = update_docx(args.project_root.resolve(), args.docx)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
