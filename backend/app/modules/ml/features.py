"""
Ingenieria de caracteristicas para el modelo multilabel de HemoVet.

Replica las transformaciones aplicadas en NB03 (notebook de feature engineering)
y NB04 (notebook de etiquetado y preparacion):
  - banderas binarias de umbrales clinicos
  - 4 ratios hematologicos
  - 1 patron compuesto de leucograma de estres
  - Imputacion de medianas para valores faltantes
  - Reordenamiento al vector de caracteristicas exacto esperado por el modelo

API publica
-----------
build_features(
    cbc: dict[str, float],
    feature_columns: list[str],
    medians: dict[str, float],
) -> pd.DataFrame
    Retorna un DataFrame listo para model.predict_proba().
"""

from __future__ import annotations

import pandas as pd

# Epsilon pequeno para evitar division por cero en los calculos de ratios.
_EPS = 0.01

# Campos CBC crudos esperados por el runtime antes de derivar banderas/ratios.
RAW_CBC_FIELDS: list[str] = [
    "RBC",
    "WBC",
    "Platelets",
    "HGB",
    "HCT",
    "MCV",
    "MCH",
    "MCHC",
    "RDW",
    "Reticulocytes",
    "Reticulocytes_pct",
    "Neutrophils",
    "Neutrophils_pct",
    "Lymphocytes",
    "Lymphocytes_pct",
    "Monocytes",
    "Monocytes_pct",
    "Eosinophils",
    "Basophils",
    "MPV",
    "PDW",
    "age_years",
]

# ---------------------------------------------------------------------------
# Banderas de umbrales clinicos (de NB03, Seccion 3: Feature Engineering)
# Los umbrales se basan en los intervalos de referencia caninos del estudio.
# ---------------------------------------------------------------------------

_FLAG_RULES: list[tuple[str, str, str, float]] = [
    # (columna_salida, columna_entrada, operador, umbral)
    ("flag_thrombocytopenia", "Platelets", "<", 200.0),
    ("flag_thrombocytopenia_severe", "Platelets", "<", 100.0),
    ("flag_lymphopenia", "Lymphocytes", "<", 1.0),
    ("flag_lymphocytosis", "Lymphocytes", ">", 5.0),
    ("flag_neutrophilia", "Neutrophils", ">", 11.0),
    ("flag_neutropenia", "Neutrophils", "<", 2.9),
    ("flag_leukocytosis", "WBC", ">", 17.0),
    ("flag_leukopenia", "WBC", "<", 5.5),
    ("flag_anemia", "HGB", "<", 12.0),
    ("flag_microcytic", "MCV", "<", 62.0),
    ("flag_macrocytic", "MCV", ">", 82.0),
    ("flag_hypochromic", "MCHC", "<", 31.0),
    ("flag_macro_platelets", "MPV", ">", 12.5),
    ("flag_reticulocytosis_pct_gt2", "Reticulocytes_pct", ">", 2.0),
    ("flag_reticulocytopenia_abs_lt10", "Reticulocytes", "<", 10.0),
]


def _apply_flag(value: float, operator: str, threshold: float) -> float:
    """Retorna 1.0 si la condicion se cumple, 0.0 en caso contrario."""
    if operator == "<":
        return 1.0 if value < threshold else 0.0
    return 1.0 if value > threshold else 0.0


def build_features(
    cbc: dict[str, float],
    feature_columns: list[str],
    medians: dict[str, float],
) -> pd.DataFrame:
    """
    Construye el vector de caracteristicas a partir de valores CBC crudos.

    Parametros
    ----------
    cbc : dict
        Valores CBC extraidos, indexados por nombres canonicos de columna del modelo.
        Puede ser parcial (los campos faltantes se imputaran con las medianas).
    feature_columns : list[str]
        Lista ordenada de nombres de caracteristicas tal como los espera el modelo.
    medians : dict[str, float]
        Valor de mediana por caracteristica, calculado sobre el conjunto de entrenamiento.

    Retorna
    -------
    pd.DataFrame
        Una fila con columnas ordenadas exactamente como feature_columns.
    """
    row: dict[str, float] = {}

    # 1. Copiar valores CBC crudos presentes, imputar el resto
    for col in RAW_CBC_FIELDS:
        if col in cbc and cbc[col] is not None:
            row[col] = float(cbc[col])
        else:
            row[col] = medians.get(col, 0.0)

    # 2. Banderas de umbrales clinicos (usar valores imputados para que siempre se calculen)
    for flag_col, src_col, op, thresh in _FLAG_RULES:
        src_val = row.get(src_col, medians.get(src_col, 0.0))
        row[flag_col] = _apply_flag(src_val, op, thresh)

    # 3. Ratios hematologicos
    neut = row.get("Neutrophils", medians.get("Neutrophils", 0.0))
    lymp = row.get("Lymphocytes", medians.get("Lymphocytes", 0.0))
    mono = row.get("Monocytes", medians.get("Monocytes", 0.0))
    plt = row.get("Platelets", medians.get("Platelets", 0.0))
    mpv = row.get("MPV", medians.get("MPV", 0.0))
    hct = row.get("HCT", medians.get("HCT", 0.0))
    ret_pct = row.get("Reticulocytes_pct", medians.get("Reticulocytes_pct", 0.0))

    row["ratio_NLR"] = neut / (lymp + _EPS)
    row["ratio_PLR"] = plt / (lymp + _EPS)
    row["ratio_MLR"] = mono / (lymp + _EPS)
    row["ratio_MPV_PLT"] = mpv / (plt + _EPS)

    # 4. Patron compuesto leucograma de estres:
    #    Neutrofilia madura + linfopenia + eosinopenia (activacion eje HPA)
    eos = row.get("Eosinophils", medians.get("Eosinophils", 0.0))
    row["pattern_stress_leukogram"] = (
        1.0 if (neut > 11.0 and lymp < 1.0 and eos < 0.5) else 0.0
    )

    # 5. Proxy clinico de anemia regenerativa: HCT bajo + reticulocitosis relativa.
    row["flag_regen_anemia_proxy"] = 1.0 if (hct < 37.0 and ret_pct > 2.0) else 0.0

    # 6. Construir DataFrame en el orden exacto del modelo, imputando lo que falte
    #    (cubre campos derivados que dependen de campos crudos ausentes)
    ordered: dict[str, float] = {}
    for col in feature_columns:
        if col in row:
            ordered[col] = row[col]
        else:
            ordered[col] = medians.get(col, 0.0)

    return pd.DataFrame([ordered])
