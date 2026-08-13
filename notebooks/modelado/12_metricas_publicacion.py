"""
12_metricas_publicacion.py — HemoVet v4
========================================
Genera las métricas faltantes para publicación / tesis:
  1. ROC-AUC por etiqueta
  2. Specificity, PPV (precision), NPV por etiqueta
  3. Bootstrap CI 95% en PR-AUC, F1, Recall, ROC-AUC (n=1000)
  4. SHAP values — top-3 features por etiqueta + gráfico resumen

Outputs:
  outputs/metricas_publicacion/tabla_metricas_completas.csv
  outputs/metricas_publicacion/tabla_bootstrap_ci.csv
  outputs/metricas_publicacion/shap_top3_por_etiqueta.csv
  outputs/metricas_publicacion/shap_summary_<label>.png
  outputs/metricas_publicacion/roc_curves.png
  outputs/metricas_publicacion/pr_curves.png

Uso:
  cd /home/edwinb/tesis/hemogramas-proyectoICC
  python notebooks/modelado/12_metricas_publicacion.py
"""

from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "outputs" / "metricas_publicacion"
OUT.mkdir(parents=True, exist_ok=True)

# ── 0. Cargar artefactos ──────────────────────────────────────────────────────

print("Cargando modelo y datos...")

with open(ROOT / "models" / "best_model_v2.pkl", "rb") as f:
    model: dict = pickle.load(f)

with open(ROOT / "data" / "processed" / "feature_columns.json") as f:
    fc_meta = json.load(f)
FEATURE_COLS: list[str] = fc_meta["feature_columns"]

with open(ROOT / "data" / "processed" / "decision_thresholds_v2.json") as f:
    thr_meta = json.load(f)
THRESHOLDS: dict[str, float] = thr_meta["thresholds"]

LABELS = list(model.keys())
print(f"  Etiquetas: {LABELS}")
print(f"  Features:  {len(FEATURE_COLS)}")

test_df = pd.read_csv(ROOT / "data" / "processed" / "test.csv")
print(f"  Test set:  {len(test_df)} filas")

# ── 1. Construir X_test e y_test ─────────────────────────────────────────────

X_test = test_df[FEATURE_COLS].copy()
y_true = test_df[LABELS].copy().astype(int)

# Imputar medianas (misma lógica que el predictor)
medians = pd.read_csv(ROOT / "data" / "processed" / "imputer_medians.csv", index_col=0).squeeze()
for col in FEATURE_COLS:
    if col in medians.index:
        X_test[col] = X_test[col].fillna(float(medians[col]))
    else:
        X_test[col] = X_test[col].fillna(0.0)

# Probabilidades brutas del modelo (sin calibrador, sin postprocesamiento MCHC)
print("\nCalculando probabilidades...")
proba: dict[str, np.ndarray] = {}
for label, clf in model.items():
    proba[label] = clf.predict_proba(X_test)[:, 1]

proba_df = pd.DataFrame(proba, index=test_df.index)

# Predicciones binarias con umbrales operativos
pred_df = pd.DataFrame({
    label: (proba_df[label] >= THRESHOLDS.get(label, 0.5)).astype(int)
    for label in LABELS
})

# ── 2. Métricas completas por etiqueta ───────────────────────────────────────

from sklearn.metrics import (
    average_precision_score,
    f1_score,
    roc_auc_score,
)

print("\nCalculando métricas por etiqueta...")

rows = []
for label in LABELS:
    yt = y_true[label].values
    yp = pred_df[label].values
    ysc = proba_df[label].values

    tp = int(((yt == 1) & (yp == 1)).sum())
    fp = int(((yt == 0) & (yp == 1)).sum())
    fn = int(((yt == 1) & (yp == 0)).sum())
    tn = int(((yt == 0) & (yp == 0)).sum())

    n_pos = int(yt.sum())
    thr = THRESHOLDS.get(label, 0.5)

    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    spec      = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    npv       = tn / (tn + fn) if (tn + fn) > 0 else 0.0
    f1        = f1_score(yt, yp, zero_division=0)
    roc_auc   = roc_auc_score(yt, ysc) if len(np.unique(yt)) > 1 else float("nan")
    pr_auc    = average_precision_score(yt, ysc) if n_pos > 0 else float("nan")

    rows.append({
        "label":     label,
        "n_pos":     n_pos,
        "threshold": round(thr, 4),
        "TP": tp, "FP": fp, "FN": fn, "TN": tn,
        "recall":    round(recall, 4),
        "precision": round(precision, 4),
        "specificity": round(spec, 4),
        "NPV":       round(npv, 4),
        "F1":        round(f1, 4),
        "ROC_AUC":   round(roc_auc, 4) if not np.isnan(roc_auc) else "NA",
        "PR_AUC":    round(pr_auc, 4) if not np.isnan(pr_auc) else "NA",
    })

metrics_df = pd.DataFrame(rows)
metrics_df.to_csv(OUT / "tabla_metricas_completas.csv", index=False)

print("\n── Métricas completas (test set, n=369) ──")
pd.set_option("display.max_columns", 20)
pd.set_option("display.width", 140)
print(metrics_df[["label","n_pos","recall","precision","specificity","NPV","F1","ROC_AUC","PR_AUC"]].to_string(index=False))

# Macro promedios
numeric_cols = ["recall","precision","specificity","NPV","F1"]
macro = metrics_df[numeric_cols].mean()
roc_vals = pd.to_numeric(metrics_df["ROC_AUC"], errors="coerce")
pr_vals  = pd.to_numeric(metrics_df["PR_AUC"], errors="coerce")
print(f"\nMacro avg  recall={macro['recall']:.4f}  precision={macro['precision']:.4f}  "
      f"specificity={macro['specificity']:.4f}  NPV={macro['NPV']:.4f}  "
      f"F1={macro['F1']:.4f}  ROC_AUC={roc_vals.mean():.4f}  PR_AUC={pr_vals.mean():.4f}")

# ── 3. Bootstrap CI 95% ──────────────────────────────────────────────────────

print("\nBootstrap CI 95% (n=1000 iteraciones)...")
N_BOOT = 1000
rng = np.random.default_rng(42)
n = len(test_df)

boot_rows = []
for label in LABELS:
    yt = y_true[label].values
    ysc = proba_df[label].values
    yp = pred_df[label].values

    boot_recall, boot_f1, boot_roc, boot_pr = [], [], [], []
    for _ in range(N_BOOT):
        idx = rng.integers(0, n, size=n)
        yt_b, yp_b, ysc_b = yt[idx], yp[idx], ysc[idx]
        if yt_b.sum() == 0 or yt_b.sum() == len(yt_b):
            continue
        tp_b = ((yt_b == 1) & (yp_b == 1)).sum()
        fn_b = ((yt_b == 1) & (yp_b == 0)).sum()
        boot_recall.append(tp_b / (tp_b + fn_b) if (tp_b + fn_b) > 0 else 0.0)
        boot_f1.append(f1_score(yt_b, yp_b, zero_division=0))
        try:
            boot_roc.append(roc_auc_score(yt_b, ysc_b))
            boot_pr.append(average_precision_score(yt_b, ysc_b))
        except Exception:
            pass

    def ci(vals):
        if not vals:
            return float("nan"), float("nan")
        a = np.array(vals)
        return round(float(np.percentile(a, 2.5)), 4), round(float(np.percentile(a, 97.5)), 4)

    r_lo, r_hi = ci(boot_recall)
    f_lo, f_hi = ci(boot_f1)
    roc_lo, roc_hi = ci(boot_roc)
    pr_lo, pr_hi  = ci(boot_pr)

    boot_rows.append({
        "label": label,
        "recall_mean":  round(float(np.mean(boot_recall)), 4),
        "recall_CI95":  f"[{r_lo}, {r_hi}]",
        "F1_mean":      round(float(np.mean(boot_f1)), 4),
        "F1_CI95":      f"[{f_lo}, {f_hi}]",
        "ROC_AUC_mean": round(float(np.mean(boot_roc)), 4) if boot_roc else float("nan"),
        "ROC_AUC_CI95": f"[{roc_lo}, {roc_hi}]",
        "PR_AUC_mean":  round(float(np.mean(boot_pr)), 4) if boot_pr else float("nan"),
        "PR_AUC_CI95":  f"[{pr_lo}, {pr_hi}]",
    })

boot_df = pd.DataFrame(boot_rows)
boot_df.to_csv(OUT / "tabla_bootstrap_ci.csv", index=False)

print("\n── Bootstrap CI 95% ──")
for _, r in boot_df.iterrows():
    print(f"  {r['label'][:35]:<35}  "
          f"Recall={r['recall_mean']} {r['recall_CI95']}  "
          f"F1={r['F1_mean']} {r['F1_CI95']}  "
          f"ROC={r['ROC_AUC_mean']} {r['ROC_AUC_CI95']}  "
          f"PR={r['PR_AUC_mean']} {r['PR_AUC_CI95']}")

# ── 4. Curvas ROC y PR ───────────────────────────────────────────────────────

print("\nGenerando curvas ROC y PR-AUC...")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import precision_recall_curve, roc_curve

COLORS = ["#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd","#8c564b","#e377c2"]

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

for i, label in enumerate(LABELS):
    yt = y_true[label].values
    ysc = proba_df[label].values
    if len(np.unique(yt)) < 2:
        continue
    color = COLORS[i % len(COLORS)]
    short = label.replace("PATRON_", "").replace("QC_", "QC ")

    fpr, tpr, _ = roc_curve(yt, ysc)
    auc_val = roc_auc_score(yt, ysc)
    axes[0].plot(fpr, tpr, color=color, lw=1.8, label=f"{short} ({auc_val:.3f})")

    prec, rec, _ = precision_recall_curve(yt, ysc)
    ap = average_precision_score(yt, ysc)
    axes[1].plot(rec, prec, color=color, lw=1.8, label=f"{short} ({ap:.3f})")

axes[0].plot([0, 1], [0, 1], "k--", lw=0.8, alpha=0.5)
axes[0].set_xlabel("False Positive Rate", fontsize=11)
axes[0].set_ylabel("True Positive Rate", fontsize=11)
axes[0].set_title("ROC curves — HemoVet v4 (test set, n=369)", fontsize=12)
axes[0].legend(fontsize=8, loc="lower right")
axes[0].set_xlim(0, 1); axes[0].set_ylim(0, 1.02)

axes[1].set_xlabel("Recall", fontsize=11)
axes[1].set_ylabel("Precision", fontsize=11)
axes[1].set_title("PR curves — HemoVet v4 (test set, n=369)", fontsize=12)
axes[1].legend(fontsize=8, loc="lower left")
axes[1].set_xlim(0, 1); axes[1].set_ylim(0, 1.02)

for ax in axes:
    ax.grid(alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)

plt.tight_layout()
fig.savefig(OUT / "roc_pr_curves.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"  Guardado: {OUT / 'roc_pr_curves.png'}")

# ── 5. SHAP values ───────────────────────────────────────────────────────────

print("\nCalculando SHAP values (TreeExplainer)...")
import shap

shap_top3_rows = []

fig_shap, axes_shap = plt.subplots(4, 2, figsize=(16, 24))
axes_shap = axes_shap.flatten()

RAW_CBC = ["RBC","WBC","Platelets","HGB","HCT","MCV","MCH","MCHC","RDW",
           "Neutrophils","Lymphocytes","Monocytes","Eosinophils","Basophils","MPV","PDW"]

for i, label in enumerate(LABELS):
    clf = model[label]
    explainer = shap.TreeExplainer(clf)
    shap_vals = explainer.shap_values(X_test)

    mean_abs = np.abs(shap_vals).mean(axis=0)
    feat_imp = pd.Series(mean_abs, index=FEATURE_COLS).sort_values(ascending=False)

    top3 = feat_imp.head(3)
    for rank, (feat, imp) in enumerate(top3.items(), 1):
        shap_top3_rows.append({
            "label": label,
            "rank": rank,
            "feature": feat,
            "mean_abs_shap": round(float(imp), 5),
            "is_raw_cbc": feat in RAW_CBC,
        })

    # Gráfico de barras top-10 para esta etiqueta
    ax = axes_shap[i]
    top10 = feat_imp.head(10)
    colors = ["#1f77b4" if f in RAW_CBC else "#aec7e8" for f in top10.index]
    top10[::-1].plot(kind="barh", ax=ax, color=colors[::-1], edgecolor="none")
    ax.set_title(label.replace("PATRON_", "").replace("QC_REQUIERE_", "QC "), fontsize=10, fontweight="bold")
    ax.set_xlabel("Mean |SHAP|", fontsize=8)
    ax.tick_params(labelsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", alpha=0.3)

axes_shap[-1].set_visible(False)

plt.suptitle("SHAP feature importance — HemoVet v4\n(azul oscuro = parámetro CBC crudo)",
             fontsize=13, y=1.01)
plt.tight_layout()
fig_shap.savefig(OUT / "shap_importancia_por_etiqueta.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"  Guardado: {OUT / 'shap_importancia_por_etiqueta.png'}")

shap_df = pd.DataFrame(shap_top3_rows)
shap_df.to_csv(OUT / "shap_top3_por_etiqueta.csv", index=False)

print("\n── Top-3 features por etiqueta (SHAP) ──")
for label in LABELS:
    sub = shap_df[shap_df["label"] == label]
    feats = "  |  ".join(f"{r['rank']}. {r['feature']} ({r['mean_abs_shap']:.4f})"
                          for _, r in sub.iterrows())
    print(f"  {label[:30]:<30}  {feats}")

# ── 6. Resumen final ─────────────────────────────────────────────────────────

print("\n" + "="*70)
print("RESUMEN EJECUTIVO — HemoVet v4 (test set n=369)")
print("="*70)

roc_mean = metrics_df["ROC_AUC"].apply(pd.to_numeric, errors="coerce").mean()
pr_mean  = metrics_df["PR_AUC"].apply(pd.to_numeric, errors="coerce").mean()

print(f"  ROC-AUC  macro:       {roc_mean:.4f}")
print(f"  PR-AUC   macro:       {pr_mean:.4f}")
print(f"  F1       macro:       {metrics_df['F1'].mean():.4f}")
print(f"  Recall   macro:       {metrics_df['recall'].mean():.4f}")
print(f"  Precision macro:      {metrics_df['precision'].mean():.4f}")
print(f"  Specificity macro:    {metrics_df['specificity'].mean():.4f}")
print(f"  NPV      macro:       {metrics_df['NPV'].mean():.4f}")
print()
print(f"Outputs guardados en: {OUT}/")
print("  tabla_metricas_completas.csv")
print("  tabla_bootstrap_ci.csv")
print("  shap_top3_por_etiqueta.csv")
print("  roc_pr_curves.png")
print("  shap_importancia_por_etiqueta.png")
