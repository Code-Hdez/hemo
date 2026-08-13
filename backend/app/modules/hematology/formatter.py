"""
Formatea los resultados de extraccion e inferencia al formato de la API AnalysisResult.

Traduce las etiquetas del modelo a hallazgos clinicos y diagnosticos en espanol, y mapea
los valores CBC extraidos a lab_values con rangos de referencia y banderas de estado.

API publica
-----------
format_analysis(
    extraction: ExtractionResult,
    prediction: PredictionResult,
    filename: str,
    file_size: int,
) -> dict
    Retorna un dict compatible con el modelo Pydantic AnalysisResult de main.py.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from .extraction_types import ExtractionResult
from app.modules.ml.metadata import coalesce_sample_date
# created_at es la clave con la que se ordena el historial longitudinal y se
# persiste en columnas DateTime sin timezone. datetime.now() escribia la hora
# local del contenedor mientras el chat lee y escribe con utc_now(): dos husos
# sobre la misma columna. Aqui se emite UTC ingenuo como en el resto del sistema.
from app.shared.dates import utc_now

if TYPE_CHECKING:
    from .predictor import PredictionResult


# ---------------------------------------------------------------------------
# Metadatos de etiquetas: severidad y descripcion clinica en espanol
# ---------------------------------------------------------------------------

# Cada entrada: (severidad, etiqueta_corta, detalle_clinico, texto_diagnostico)
_LABEL_META: dict[str, tuple[str, str, str, str]] = {
    "QC_AGREGADOS_PLAQUETARIOS": (
        "warn",
        "Posibles agregados plaquetarios",
        "Se detectaron posibles agregados plaquetarios; el recuento puede estar subestimado.",
        "Repetir muestra fresca y revisar frotis para confirmar recuento plaquetario real.",
    ),
    "QC_INTERFERENCIA_GR": (
        "warn",
        "Interferencia de GR en leucocitos",
        "Posible interferencia de globulos rojos no lisados en el recuento leucocitario.",
        "Revisar recuento leucocitario; posible subestimacion por interferencia eritrocitaria.",
    ),
    "PATRON_INFLAMATORIO": (
        "danger",
        "Patron inflamatorio",
        "Neutrofilia con o sin leucocitosis, compatible con respuesta inflamatoria.",
        "Patron inflamatorio detectado (neutrofilia). Correlacionar con signos clinicos y PCR.",
    ),
    "PATRON_LEUCOGRAMA_ESTRES": (
        "info",
        "Leucograma de estres",
        "Neutrofilia madura, linfopenia y eosinopenia: patron tipico de respuesta al estres (HPA).",
        "Leucograma de estres (cortisol). Descartar corticoterapia o dolor cronico.",
    ),
    "PATRON_ANEMIA_NO_REGENERATIVA": (
        "warn",
        "Anemia no regenerativa",
        "Anemia sin evidencia de respuesta reticulocitaria adecuada.",
        "Anemia no regenerativa. Evaluar enfermedad cronica, deficiencia de hierro o falla medular.",
    ),
    "PATRON_HEMOLISIS_MCHC": (
        "danger",
        "Hemolisis sugerida por MCHC",
        "MCHC elevado consistente con hemolisis in vitro o in vivo.",
        "MCHC elevado: revisar muestra para hemolisis in vitro. Si se descarta, considerar hemolisis in vivo.",
    ),
    "PATRON_POLICITEMIA": (
        "warn",
        "Policitemia",
        "Hematocrito elevado sobre el rango de referencia canino.",
        "Policitemia detectada. Descartar deshidratacion, hipoxia cronica o eritrocitosis primaria.",
    ),
}

# ---------------------------------------------------------------------------
# Rangos de referencia CBC canino (para calcular el estado en lab_values)
# Umbrales de los intervalos de referencia caninos IDEXX ProCyte One (NB03)
# ---------------------------------------------------------------------------

# Formato: nombre_canonico -> (nombre_display, unidad, ref_min, ref_max)
_REFERENCE_RANGES: dict[str, tuple[str, str, float, float]] = {
    "WBC": ("WBC", "x10³/µL", 5.5, 16.9),
    "RBC": ("RBC", "x10⁶/µL", 5.5, 8.5),
    "HGB": ("HGB", "g/dL", 12.0, 18.0),
    "HCT": ("HCT", "%", 37.0, 55.0),
    "MCV": ("MCV", "fL", 62.0, 82.0),
    "MCH": ("MCH", "pg", 20.0, 28.0),
    "MCHC": ("MCHC", "g/dL", 31.0, 38.0),
    "RDW": ("RDW", "%", 12.0, 18.0),
    "Platelets": ("PLT", "x10³/µL", 175.0, 500.0),
    "MPV": ("MPV", "fL", 7.5, 12.5),
    "PDW": ("PDW", "%", 9.0, 20.0),
    "Neutrophils": ("NEU", "x10³/µL", 2.9, 11.0),
    "Lymphocytes": ("LYM", "x10³/µL", 1.0, 5.0),
    "Monocytes": ("MONO", "x10³/µL", 0.3, 2.0),
    "Eosinophils": ("EOS", "x10³/µL", 0.1, 1.4),
    "Basophils": ("BASO", "x10³/µL", 0.0, 0.15),
    "Neutrophils_pct": ("NEU%", "%", 60.0, 80.0),
    "Lymphocytes_pct": ("LYM%", "%", 12.0, 30.0),
    "Monocytes_pct": ("MONO%", "%", 2.0, 10.0),
    "Eosinophils_pct": ("EOS%", "%", 0.5, 9.0),
}


def _lab_status(value: float, ref_min: float, ref_max: float) -> str:
    """Retorna la cadena de estado de severidad para un valor de laboratorio vs su rango."""
    if value < ref_min:
        # Flag as critical if far below (>30% under lower limit)
        return "critical" if value < ref_min * 0.7 else "low"
    if value > ref_max:
        return "critical" if value > ref_max * 1.3 else "high"
    return "normal"


def _canonical_unit(unit: str | None) -> str | None:
    if not unit:
        return None
    compact = (
        str(unit)
        .strip()
        .lower()
        .replace(" ", "")
        .replace("×", "x")
        .replace("μ", "u")
        .replace("µ", "u")
        .replace("³", "^3")
        .replace("⁶", "^6")
        .replace("⁹", "^9")
        .replace("¹²", "^12")
    )
    aliases = {
        "x10^3/ul": "10^9/L",
        "10^3/ul": "10^9/L",
        "10^9/l": "10^9/L",
        "x10^9/l": "10^9/L",
        "x10^6/ul": "10^12/L",
        "10^6/ul": "10^12/L",
        "10^12/l": "10^12/L",
        "x10^12/l": "10^12/L",
        "g/dl": "g/dL",
        "%": "%",
        "fl": "fL",
        "pg": "pg",
    }
    return aliases.get(compact, str(unit).strip())


def _recorded_status(value: str | None) -> str | None:
    if not value:
        return None
    normalized = str(value).strip().lower()
    aliases = {
        "h": "high",
        "alto": "high",
        "high": "high",
        "l": "low",
        "bajo": "low",
        "low": "low",
        "n": "normal",
        "normal": "normal",
        "critical": "critical",
        "critico": "critical",
        "crítico": "critical",
    }
    return aliases.get(normalized)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def format_analysis(
    extraction: ExtractionResult,
    prediction: PredictionResult,
    filename: str,
    file_size: int,
) -> dict:
    """
    Construye el dict AnalysisResult a partir de los resultados de extraccion e inferencia.

    Parametros
    ----------
    extraction : ExtractionResult
        Valores CBC y metadatos del paciente extraidos del PDF.
    prediction : PredictionResult
        Probabilidades del modelo y predicciones binarias.
    filename : str
        Nombre original del archivo subido.
    file_size : int
        Tamano del archivo en bytes.

    Retorna
    -------
    dict
        Compatible con el modelo Pydantic AnalysisResult de main.py.
    """
    cbc = extraction.cbc

    # Etiquetas QC que se reportan como avisos de calidad, no como patrones clínicos
    _QC_LABELS = {"QC_AGREGADOS_PLAQUETARIOS", "QC_INTERFERENCIA_GR"}

    # Etiquetas del modelo que se descartan silenciosamente y no aparecen en la
    # respuesta (ni como finding ni como qc_flag). QC_REQUIERE_FROTIS es una
    # senal operativa interna del analizador; se omite por decision de producto.
    _HIDDEN_LABELS = {"QC_REQUIERE_FROTIS"}

    # Mensajes legibles para el usuario por cada flag QC visible
    _QC_MESSAGES: dict[str, str] = {
        "QC_AGREGADOS_PLAQUETARIOS": "Posible agregación plaquetaria — el recuento de plaquetas podría estar subestimado",
        "QC_INTERFERENCIA_GR": "Posible interferencia de glóbulos rojos en el recuento leucocitario",
    }

    # Hallazgos: una entrada por etiqueta activa (True)
    findings: list[dict] = []
    qc_flags: list[str] = []
    active_label_names: list[str] = []

    for label, is_active in prediction.predictions.items():
        if not is_active:
            continue
        if label in _HIDDEN_LABELS:
            continue
        if label in _QC_LABELS:
            msg = _QC_MESSAGES.get(label)
            if msg:
                qc_flags.append(msg)
            continue
        meta = _LABEL_META.get(label)
        if meta is None:
            continue
        severity, short_label, detail, _ = meta
        findings.append(
            {
                "label": short_label,
                "detail": detail,
                "severity": severity,
            }
        )
        active_label_names.append(label)

    # Diagnosticos: texto de interpretacion clinica por etiqueta activa
    diagnoses: list[str] = []
    for label in active_label_names:
        meta = _LABEL_META.get(label)
        if meta:
            diagnoses.append(meta[3])

    if not diagnoses:
        diagnoses = [
            "No se detectaron patrones hematologicos significativos. "
            "Los valores del hemograma se encuentran dentro de los rangos de referencia caninos."
        ]

    # Frase resumen
    if active_label_names:
        label_str = ", ".join(
            _LABEL_META[label][1]
            for label in active_label_names
            if label in _LABEL_META
        )
        summary = f"Hemograma analizado. Hallazgos detectados: {label_str}."
    else:
        summary = (
            "Hemograma analizado. Sin patrones hematologicos fuera del rango esperado."
        )

    # Valores de laboratorio: CBC extraido mapeado a rangos de referencia
    lab_values: list[dict] = []
    for field_name, (display, unit, ref_min, ref_max) in _REFERENCE_RANGES.items():
        if field_name not in cbc:
            continue
        val = float(cbc[field_name])
        detail = extraction.parameter_details.get(field_name)
        original_unit = detail.unit if detail and detail.unit else unit
        normalized_unit = _canonical_unit(original_unit)
        catalog_unit = _canonical_unit(unit)

        if (
            detail
            and detail.reference_min is not None
            and detail.reference_max is not None
            and detail.reference_min <= detail.reference_max
        ):
            effective_min = detail.reference_min
            effective_max = detail.reference_max
            reference_origin = "laboratory"
        elif normalized_unit == catalog_unit:
            effective_min = ref_min
            effective_max = ref_max
            reference_origin = "validated_catalog"
        else:
            effective_min = None
            effective_max = None
            reference_origin = "unknown"

        derived_status = (
            _lab_status(val, effective_min, effective_max)
            if effective_min is not None and effective_max is not None
            else None
        )
        recorded_status = _recorded_status(detail.recorded_flag if detail else None)
        status = recorded_status or derived_status or "not_evaluable"
        lab_values.append(
            {
                "name": display,
                "value": str(round(val, 2)),
                "unit": original_unit,
                "status": status,
                "ref_min": effective_min,
                "ref_max": effective_max,
                "canonical_name": field_name,
                "original_name": detail.original_name if detail else field_name,
                "original_value": detail.original_value if detail else str(val),
                "normalized_unit": normalized_unit,
                "reference_origin": reference_origin,
                "status_origin": "recorded" if recorded_status else (
                    "derived" if derived_status else "unknown"
                ),
                "derived_status": derived_status,
                "extraction_confidence": detail.confidence if detail else None,
                "notes": detail.notes if detail else None,
                "data_origin": detail.data_origin if detail else "formatter_catalog",
            }
        )

    # Puntuacion de calidad: fraccion de campos CBC clave presentes en la extraccion
    _CORE_FIELDS = [
        "WBC",
        "RBC",
        "HGB",
        "HCT",
        "MCV",
        "MCH",
        "MCHC",
        "Platelets",
        "Neutrophils",
        "Lymphocytes",
    ]
    n_found = sum(1 for f in _CORE_FIELDS if f in cbc)
    quality_score = round(n_found / len(_CORE_FIELDS), 2)

    # Especie (por defecto canino si no se especifica)
    species = extraction.metadata.get("species") or "Canino"
    if "Canine" in species or "canin" in species.lower():
        species = "Canino"

    # Fecha oficial: tomar del PDF si esta disponible; si no, usar la fecha de subida.
    sample_dt = coalesce_sample_date(extraction.metadata)
    created_at = sample_dt.isoformat() if sample_dt else utc_now().isoformat()

    return {
        "id": str(uuid.uuid4())[:8],
        "filename": filename,
        "file_size": file_size,
        "created_at": created_at,
        "_uploaded_at": utc_now().isoformat(),
        "confidence": prediction.confidence,
        "quality_score": quality_score,
        "species": species,
        "summary": summary,
        "diagnoses": diagnoses,
        "findings": findings,
        "qc_flags": qc_flags,
        "lab_values": lab_values,
        "location": extraction.metadata.get("location"),
        "latitude": None,
        "longitude": None,
    }
