"""
Carga del modelo e inferencia para el clasificador multilabel XGBoost de HemoVet.

El modelo guardado es un dict que mapea cada nombre de etiqueta oficial
a una instancia de XGBClassifier entrenada. La inferencia produce probabilidades por etiqueta
que luego se umbralan a predicciones binarias.

Las etiquetas basadas en reglas (QC_AGREGADOS_PLAQUETARIOS, QC_INTERFERENCIA_GR) se manejan
mediante regex sobre el texto de comentarios IDEXX, no a traves del modelo.

Postprocesamiento del artefacto MCHC: si MCHC > 50 g/dL (fisiologicamente imposible),
se fuerza la probabilidad de PATRON_HEMOLISIS_MCHC a 0.0 -- replica NB05b.

API publica
-----------
load_resources(project_root: Path) -> ModelResources
predict(cbc, comments, resources) -> PredictionResult
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import pickle
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from .features import RAW_CBC_FIELDS, build_features
from .input_contract import validate_cbc_contract

# ---------------------------------------------------------------------------
# Estructuras de datos
# ---------------------------------------------------------------------------


@dataclass
class ModelResources:
    """Todos los artefactos necesarios para una llamada de inferencia."""

    model: dict  # etiqueta -> XGBClassifier
    feature_columns: list[str]  # lista ordenada de nombres de caracteristicas
    thresholds: dict[str, float]  # etiqueta -> umbral de decision
    medians: dict[str, float]  # caracteristica -> mediana de entrenamiento (imputacion)
    label_policy: dict  # JSON completo de politica de etiquetas (metadatos)
    model_metadata: dict  # JSON de metadatos del modelo runtime
    artifact_manifest: dict | None = (
        None  # metadatos del manifiesto de artefactos verificados
    )
    calibrators: dict | None = (
        None  # etiqueta -> SigmoidCalibrator (Platt scaling); None si no disponibles
    )
    ready: bool = False


@dataclass
class PredictionResult:
    """Resultado de una llamada de inferencia."""

    probabilities: dict[str, float]  # etiqueta modelo -> probabilidad [0, 1]
    predictions: dict[str, bool]  # todas las etiquetas (modelo + regla) -> bool
    confidence: float  # puntuacion de confianza resumen del analisis
    feature_row: pd.DataFrame  # DataFrame (1, n_features) enviado al modelo
    status: str  # success | partial_imputation | no_prediction
    imputed_fields: list[str]  # campos CBC crudos imputados para inferencia
    error_code: str | None = None  # codigo semantico de error si no_prediction
    error_message: str | None = None  # mensaje de error de alto nivel para auditoria
    warnings: list[str] = field(default_factory=list)  # alertas no fatales del pipeline


# Version del contrato de salida de inferencia (envelope runtime).
SCHEMA_VERSION = os.getenv("HEMOVET_SCHEMA_VERSION", "3.0.0")


# ---------------------------------------------------------------------------
# Patrones regex para etiquetas basadas en reglas (de final_label_policy.json)
# ---------------------------------------------------------------------------

_RULE_PATTERNS: dict[str, str] = {
    "QC_AGREGADOS_PLAQUETARIOS": (
        r"agregad|platelet.?clump|recuento.+plaquetas.+mayor"
    ),
    "QC_INTERFERENCIA_GR": (
        r"GR.?no.?lisad|unlysed.?red|gl[oó]bulos?.?roj[oa]s?.?no.?lisad"
    ),
}


# ---------------------------------------------------------------------------
# Carga de artefactos
# ---------------------------------------------------------------------------


def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Calcula el hash SHA-256 de un archivo de forma incremental."""
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_artifact_path(project_root: Path, env_var: str, default_rel: str) -> Path:
    """Resuelve ruta de artefacto via variable de entorno o ruta relativa por defecto."""
    env_value = os.getenv(env_var)
    if env_value:
        candidate = Path(env_value)
        if not candidate.is_absolute():
            candidate = project_root / candidate
        return candidate
    return project_root / default_rel


def _resolve_model_version(resources: ModelResources) -> str:
    """Retorna la version de modelo declarada en metadata."""
    if isinstance(resources.model_metadata, dict):
        return str(resources.model_metadata.get("version", "unknown"))
    return "unknown"


def _resolve_policy_version(resources: ModelResources) -> str:
    """Retorna la version de politica declarada en label_policy."""
    if isinstance(resources.label_policy, dict):
        return str(resources.label_policy.get("version", "unknown"))
    return "unknown"


def _calibrate_probability(calibrator: Any, probability: float) -> float:
    """Aplica un calibrador runtime compatible con objetos o parámetros JSON-like."""
    if hasattr(calibrator, "calibrate"):
        return float(calibrator.calibrate(probability))
    if isinstance(calibrator, dict) and calibrator.get("type") == "sigmoid_logit":
        if "coefficient" not in calibrator or "intercept" not in calibrator:
            raise TypeError("Calibrador sigmoid_logit sin 'coefficient' o 'intercept'")
        clipped = min(max(float(probability), 1e-6), 1.0 - 1e-6)
        logit = math.log(clipped / (1.0 - clipped))
        score = float(calibrator["coefficient"]) * logit + float(calibrator["intercept"])
        score = min(max(score, -40.0), 40.0)
        return 1.0 / (1.0 + math.exp(-score))
    raise TypeError("Formato de calibrador no soportado")


def build_prediction_envelope(
    prediction_id: str,
    resources: ModelResources,
    prediction: PredictionResult,
) -> dict[str, Any]:
    """
    Construye el envelope estandar de inferencia para runtime/API.

    Incluye trazabilidad completa de versionado y estado triestado.
    """
    return {
        "prediction_id": prediction_id,
        "model_version": _resolve_model_version(resources),
        "policy_version": _resolve_policy_version(resources),
        "schema_version": SCHEMA_VERSION,
        "status": str(getattr(prediction, "status", "success")),
        "imputed_fields": list(getattr(prediction, "imputed_fields", [])),
    }


def _validate_artifact_manifest(project_root: Path) -> dict:
    """
    Valida que los artefactos runtime coincidan con el manifiesto versionado.

    El manifiesto es obligatorio para evitar que archivos criticos (modelo,
    umbrales, politicas y columnas) se modifiquen sin trazabilidad.
    """
    manifest_path = _resolve_artifact_path(
        project_root,
        "HEMOVET_ARTIFACT_MANIFEST_PATH",
        "data/processed/artifact_manifest_v2.json",
    )
    if not manifest_path.exists():
        raise FileNotFoundError(
            "No se encontro data/processed/artifact_manifest_v2.json. "
            "Ejecuta scripts/generate_artifact_manifest_v2.py antes de iniciar el backend."
        )

    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)

    runtime_artifacts = manifest.get("runtime_artifacts")
    if not isinstance(runtime_artifacts, list) or len(runtime_artifacts) == 0:
        raise ValueError(
            "artifact_manifest_v2.json no contiene runtime_artifacts validos."
        )

    for entry in runtime_artifacts:
        rel_path = entry.get("path")
        expected_sha256 = entry.get("sha256")

        if not rel_path or not expected_sha256:
            raise ValueError(
                "artifact_manifest_v2.json contiene una entrada sin path o sha256."
            )

        abs_path = project_root / rel_path
        if not abs_path.exists():
            raise FileNotFoundError(
                f"Falta el artefacto declarado en manifiesto: {rel_path}"
            )

        actual_sha256 = _sha256_file(abs_path)
        if actual_sha256 != expected_sha256:
            raise ValueError(
                "Checksum inválido para artefacto runtime. "
                f"Archivo: {rel_path}. "
                f"Esperado: {expected_sha256}. Actual: {actual_sha256}."
            )

    return manifest


def load_resources(project_root: Path) -> ModelResources:
    """
    Carga el modelo entrenado y todos los artefactos de soporte desde el disco.

    Parametros
    ----------
    project_root : Path
        Raiz del repositorio (el directorio que contiene models/ y data/).

    Retorna
    -------
    ModelResources
        Poblado y marcado como ready=True.

    Lanza
    -----
    FileNotFoundError
        Si falta algun archivo de artefacto requerido.
    Exception
        Para cualquier otro error de carga (pickle corrupto, JSON inválido, etc.).
    """
    # Validacion de inmutabilidad: falla si algun artefacto no coincide con el hash esperado.
    manifest = _validate_artifact_manifest(project_root)

    # Pickle del modelo: dict[str, XGBClassifier]
    model_path = _resolve_artifact_path(
        project_root, "HEMOVET_MODEL_PATH", "models/best_model_v2.pkl"
    )
    with open(model_path, "rb") as f:
        model = pickle.load(f)

    model_metadata_path = _resolve_artifact_path(
        project_root,
        "HEMOVET_MODEL_METADATA_PATH",
        "models/model_metadata_v2.json",
    )
    with open(model_metadata_path, "r", encoding="utf-8") as f:
        model_metadata = json.load(f)

    # Orden de las columnas de caracteristicas
    feature_columns_path = _resolve_artifact_path(
        project_root,
        "HEMOVET_FEATURE_COLUMNS_PATH",
        "data/processed/feature_columns.json",
    )
    with open(feature_columns_path) as f:
        feature_columns_doc = json.load(f)
    feature_columns: list[str] = feature_columns_doc["feature_columns"]

    # Umbrales de decision por etiqueta (optimizados sobre el conjunto de validacion)
    thresholds_path = _resolve_artifact_path(
        project_root,
        "HEMOVET_THRESHOLDS_PATH",
        "data/processed/decision_thresholds_v2.json",
    )
    with open(thresholds_path) as f:
        thresholds_doc = json.load(f)
    thresholds: dict[str, float] = thresholds_doc["thresholds"]

    # Medianas del conjunto de entrenamiento para imputacion
    medians_path = _resolve_artifact_path(
        project_root,
        "HEMOVET_IMPUTER_MEDIANS_PATH",
        "data/processed/imputer_medians.csv",
    )
    medians_df = pd.read_csv(medians_path)
    medians: dict[str, float] = dict(
        zip(medians_df["feature"], medians_df["mediana_train"])
    )

    # Politica completa de etiquetas (para metadatos y descripciones)
    policy_path = _resolve_artifact_path(
        project_root,
        "HEMOVET_LABEL_POLICY_PATH",
        "data/processed/final_label_policy.json",
    )
    with open(policy_path) as f:
        label_policy = json.load(f)

    # Calibradores de probabilidad Platt scaling por etiqueta (artefacto runtime opcional)
    calibrators_path = _resolve_artifact_path(
        project_root,
        "HEMOVET_CALIBRATORS_PATH",
        "models/calibrators_v2.pkl",
    )
    calibrators: dict | None = None
    if calibrators_path.exists():
        with open(calibrators_path, "rb") as f:
            calibrators = pickle.load(f)
    else:
        import warnings as _warnings

        _warnings.warn(
            f"Calibradores no encontrados en {calibrators_path}. "
            "Se usaran probabilidades crudas del modelo.",
            RuntimeWarning,
            stacklevel=2,
        )

    return ModelResources(
        model=model,
        feature_columns=feature_columns,
        thresholds=thresholds,
        medians=medians,
        label_policy=label_policy,
        model_metadata=model_metadata,
        artifact_manifest=manifest,
        calibrators=calibrators,
        ready=True,
    )


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------


def predict(
    cbc: dict[str, float],
    comments: Optional[str],
    resources: ModelResources,
) -> PredictionResult:
    """
    Ejecuta el pipeline completo de inferencia sobre un hemograma.

    Pasos:
    1. Construir DataFrame de caracteristicas (banderas, ratios, imputacion).
    2. Obtener predict_proba de cada XGBClassifier por etiqueta.
    3. Aplicar postprocesamiento del artefacto MCHC > 50.
    4. Umbralizar probabilidades a predicciones binarias.
    5. Evaluar etiquetas basadas en reglas desde idexx_comments.
    6. Calcular la puntuacion de confianza resumen.

    Parametros
    ----------
    cbc : dict
        Valores CBC canonicos del extractor.
    comments : str or None
        Texto de comentarios IDEXX (solo para etiquetas basadas en reglas).
    resources : ModelResources
        Artefactos del modelo cargados.

    Retorna
    -------
    PredictionResult
    """
    # Paso 1: validacion de contrato CBC e ingenieria de caracteristicas
    cbc_validado = validate_cbc_contract(cbc)
    feature_row = build_features(
        cbc_validado, resources.feature_columns, resources.medians
    )
    imputed_fields = sorted(
        field for field in RAW_CBC_FIELDS if field not in cbc_validado
    )

    # Paso 2: probabilidades del modelo por cada etiqueta oficial
    probabilities: dict[str, float] = {}
    warnings: list[str] = []
    successful_scores = 0
    for label, clf in resources.model.items():
        try:
            prob_cruda = float(clf.predict_proba(feature_row)[:, 1][0])
            # Aplicar calibrador Platt scaling si esta disponible para esta etiqueta
            _calibrators = resources.calibrators or {}
            if label in _calibrators:
                prob = _calibrate_probability(_calibrators[label], prob_cruda)
            else:
                prob = prob_cruda
            successful_scores += 1
        except Exception as exc:
            prob = 0.0
            warnings.append(
                f"No se pudo calcular probabilidad para {label}: {type(exc).__name__}"
            )
        probabilities[label] = prob

    # Paso 3: postprocesamiento del artefacto MCHC
    mchc_val = float(cbc_validado.get("MCHC", feature_row["MCHC"].iloc[0]))
    if mchc_val > 50.0 and "PATRON_HEMOLISIS_MCHC" in probabilities:
        probabilities["PATRON_HEMOLISIS_MCHC"] = 0.0

    # Paso 4: aplicar umbrales por etiqueta
    predictions: dict[str, bool] = {}
    for label, prob in probabilities.items():
        threshold = resources.thresholds.get(label, 0.5)
        predictions[label] = prob >= threshold

    # Paso 5: etiquetas basadas en reglas desde los comentarios
    for rule_label, pattern in _RULE_PATTERNS.items():
        if comments:
            predictions[rule_label] = bool(re.search(pattern, comments, re.IGNORECASE))
        else:
            predictions[rule_label] = False

    # Paso 6: puntuacion de confianza resumen
    # Promedio de probabilidades de todas las etiquetas activas del modelo.
    # Si ninguna etiqueta esta activa, se usa la probabilidad maxima.
    active_probs = [
        p for lbl, p in probabilities.items() if predictions.get(lbl, False)
    ]
    if active_probs:
        confidence = round(sum(active_probs) / len(active_probs), 4)
    elif probabilities:
        confidence = round(max(probabilities.values()), 4)
    else:
        confidence = 0.0

    if successful_scores == 0:
        status = "no_prediction"
        error_code = "MODEL_SCORE_ERROR"
        error_message = "No se pudo calcular ninguna probabilidad del modelo."
    elif imputed_fields:
        status = "partial_imputation"
        error_code = None
        error_message = None
    else:
        status = "success"
        error_code = None
        error_message = None

    return PredictionResult(
        probabilities=probabilities,
        predictions=predictions,
        confidence=confidence,
        feature_row=feature_row,
        status=status,
        imputed_fields=imputed_fields,
        error_code=error_code,
        error_message=error_message,
        warnings=warnings,
    )


def _build_no_prediction_result(
    *,
    resources: ModelResources,
    comments: Optional[str],
    error_code: str,
    error_message: str,
) -> PredictionResult:
    """Construye un resultado no_prediction explicito para flujos batch."""
    probabilities = {label: 0.0 for label in resources.model.keys()}
    predictions = {label: False for label in resources.model.keys()}

    for rule_label, pattern in _RULE_PATTERNS.items():
        if comments:
            predictions[rule_label] = bool(re.search(pattern, comments, re.IGNORECASE))
        else:
            predictions[rule_label] = False

    fallback_row = {
        col: float(resources.medians.get(col, 0.0)) for col in resources.feature_columns
    }

    return PredictionResult(
        probabilities=probabilities,
        predictions=predictions,
        confidence=0.0,
        feature_row=pd.DataFrame([fallback_row]),
        status="no_prediction",
        imputed_fields=sorted(RAW_CBC_FIELDS),
        error_code=error_code,
        error_message=error_message,
        warnings=[error_message],
    )


def predict_batch(
    cbc_items: list[dict[str, Any]],
    comments_items: list[Optional[str]] | None,
    resources: ModelResources,
) -> list[PredictionResult]:
    """
    Ejecuta inferencia batch robusta con manejo explicito de no_prediction por item.

    En batch se evita abortar todo el lote por un item invalido: cada caso
    retorna success/partial_imputation/no_prediction con su causa.
    """
    if comments_items is None:
        comments_items = [None] * len(cbc_items)

    if len(comments_items) != len(cbc_items):
        raise ValueError("comments_items debe tener la misma longitud que cbc_items")

    results: list[PredictionResult] = []
    for cbc, comments in zip(cbc_items, comments_items):
        try:
            results.append(predict(cbc=cbc, comments=comments, resources=resources))
        except Exception as exc:
            error_code = getattr(exc, "error_code", "BATCH_ITEM_ERROR")
            message = str(getattr(exc, "message", "")) or str(exc)
            if not message:
                message = "Fallo inesperado en inferencia batch."
            results.append(
                _build_no_prediction_result(
                    resources=resources,
                    comments=comments,
                    error_code=str(error_code),
                    error_message=message,
                )
            )

    return results
