#!/usr/bin/env python3
"""Motor de figuras — HemoVet · RECARACTERIZACION-A100.

Única puerta de entrada de datos (`cargar`) y única puerta de salida de figuras
(`figura`). Ninguna celda dibuja fuera de aquí y ninguna vuelve a leer disco.

I-B · CERO CIFRAS A MANO: las constantes permitidas son SOLO físicas y de estilo,
declaradas juntas y con fuente. Todo lo demás se carga.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import random
from datetime import datetime, timezone

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

W = pathlib.Path(__file__).resolve().parent.parent
FIG = W / "06_analisis/figuras"
TAB = W / "06_analisis/tablas"
FIG.mkdir(parents=True, exist_ok=True)
TAB.mkdir(parents=True, exist_ok=True)

SEMILLA = 20260811

# ── CONSTANTES FÍSICAS Y DE ESTILO (las únicas permitidas, §4 I-B) ────────────
# Fuente: NVIDIA A100 SXM4 datasheet — ancho de banda HBM2e nominal.
BW_NOMINAL_GBS = 2039.0
# Fuente: literatura de MBU — el ancho de banda alcanzable es 77-86 % del nominal.
BW_ALCANZABLE = (0.77, 0.86)
# Fuente: rango documentado de MBU en decodificación autoregresiva.
MBU_REF = (0.30, 0.80)
# Fuente: literatura GBNF citada en el pre-registro (TPOT 15,4 → 29,98 ms).
GRAMATICA_LITERATURA_MS = 14.6
# Fuente: 03_hipotesis/preregistro.md — umbral de H-2.
H2_UMBRAL_MS = 10.0

GENERAL, HEMOGRAMA, HISTORICO = "#2a78d6", "#eb6834", "#1baf7a"
L4_VIEJA, A100_NUEVA = "#2a78d6", "#e34948"
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#256abf", "#184f95", "#0d366b"]
DIV_NEG, DIV_MID, DIV_POS = "#2a78d6", "#f0efec", "#e34948"
BUENO, AVISO, SERIO, CRITICO = "#0ca30c", "#fab219", "#ec835a", "#d03b3b"
TINTA, TINTA_2, APAGADO = "#0b0b0b", "#52514e", "#898781"
REJILLA, LINEA_BASE, SUPERFICIE = "#e1e0d9", "#c3c2b7", "#fcfcfb"

MARCADOR = {"GENERAL": "o", "HEMOGRAMA": "s", "HISTORICO": "^"}
COLOR_MODO = {"GENERAL": GENERAL, "HEMOGRAMA": HEMOGRAMA, "HISTORICO": HISTORICO}

PROCEDENCIA: dict[str, dict] = {}
MANIFIESTO: list[dict] = []
PIES: list[str] = []


def aplicar_estilo() -> None:
    plt.rcParams.update({
        "figure.facecolor": SUPERFICIE, "axes.facecolor": SUPERFICIE,
        "savefig.facecolor": SUPERFICIE, "savefig.bbox": "tight",
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans"],
        "axes.titlesize": 11, "axes.labelsize": 9,
        "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8,
        "axes.edgecolor": APAGADO, "axes.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False,
        "grid.color": REJILLA, "grid.linewidth": 0.6, "grid.linestyle": "-",
        "xtick.direction": "out", "ytick.direction": "out",
        "xtick.color": APAGADO, "ytick.color": APAGADO,
        "text.color": TINTA, "axes.labelcolor": TINTA_2,
        "pdf.fonttype": 42, "svg.fonttype": "none",
        "figure.dpi": 110, "savefig.dpi": 300,
    })


def fmt_es(x: float, dec: int = 2) -> str:
    """1234.5 -> '1 234,5' — espacio fino de millares y coma decimal."""
    s = f"{x:,.{dec}f}"
    return s.replace(",", " ").replace(".", ",")


def formateador_es(dec: int = 0) -> FuncFormatter:
    return FuncFormatter(lambda v, _p: fmt_es(v, dec))


def cargar(clave: str, ruta: str, lector):
    """Única puerta de entrada de datos. Hashea y registra procedencia."""
    p = W / ruta
    b = p.read_bytes()
    obj = lector(p)
    try:
        n = len(obj)
    except TypeError:
        n = 1
    cols = sorted(obj[0].keys()) if isinstance(obj, list) and obj and isinstance(obj[0], dict) else []
    PROCEDENCIA[clave] = {
        "ruta": ruta, "sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b),
        "n_registros": n, "columnas": cols,
        "cargado_en": datetime.now(timezone.utc).isoformat(),
    }
    return obj


def leer_ndjson(p: pathlib.Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def leer_json(p: pathlib.Path):
    return json.loads(p.read_text(encoding="utf-8"))


# ── ESTADÍSTICA ───────────────────────────────────────────────────────────────
def wilson(exitos: int, n: int, conf: float = 0.95) -> tuple[float, float]:
    """IC de Wilson para una proporción. Nunca Wald (§8 H-12)."""
    if n == 0:
        return (0.0, 1.0)
    from scipy.stats import norm
    z = norm.ppf(1 - (1 - conf) / 2)
    p = exitos / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (max(0.0, c - h), min(1.0, c + h))


def bootstrap(muestra, estadistico, B: int = 10_000, semilla: int = SEMILLA):
    rng = random.Random(semilla)
    xs = list(muestra)
    s = sorted(estadistico(rng.choices(xs, k=len(xs))) for _ in range(B))
    return s[int(0.025 * B)], s[int(0.975 * B)]


def kappa_cohen(a: list[bool], b: list[bool]) -> float:
    n = len(a)
    x = sum(1 for i in range(n) if a[i] and b[i])
    y = sum(1 for i in range(n) if a[i] and not b[i])
    z = sum(1 for i in range(n) if not a[i] and b[i])
    w = sum(1 for i in range(n) if not a[i] and not b[i])
    po = (x + w) / n
    pe = ((x + y) * (x + z) + (z + w) * (y + w)) / n ** 2
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def n_por_grupo(p1: float, p2: float, alfa: float = 0.05, potencia: float = 0.80) -> float:
    from scipy.stats import norm
    za = norm.ppf(1 - alfa / 2)
    zb = norm.ppf(potencia)
    pb = (p1 + p2) / 2
    num = (za * (2 * pb * (1 - pb)) ** 0.5 + zb * (p1 * (1 - p1) + p2 * (1 - p2)) ** 0.5) ** 2
    return num / (p1 - p2) ** 2


# ── FIGURA ────────────────────────────────────────────────────────────────────
def figura(id_, titulo, slug, tabla, dibujar, pie, marca, procedencia,
           nota_lectura=None, tam=(7.0, 4.2)):
    """Única puerta de salida. Dibuja DESDE la tabla, exporta 3 formatos + CSV."""
    fig, ax = plt.subplots(figsize=tam)
    dibujar(ax, tabla)
    ax.set_title(titulo, color=TINTA, loc="left", pad=10)
    base = f"fig_{id_}_{slug}"
    rutas = {}
    for ext in ("pdf", "svg", "png"):
        r = FIG / f"{base}.{ext}"
        fig.savefig(r, format=ext)
        rutas[ext] = str(r.relative_to(W))
    plt.close(fig)

    tp = TAB / f"tab_{id_}_{slug}.csv"
    import csv
    with tp.open("w", encoding="utf-8", newline="") as fh:
        wcsv = csv.writer(fh, delimiter=";")   # ; como separador, coma decimal
        wcsv.writerow(tabla["columnas"])
        for fila in tabla["filas"]:
            wcsv.writerow(fila)

    n = tabla.get("n")
    pie_txt = f"**Figura {id_}.** {titulo}. {pie} n = {n}. [{marca}]. Fuente: {', '.join(procedencia)}."
    if nota_lectura:
        pie_txt += f"\n\n> *Nota de lectura.* {nota_lectura}"
    PIES.append(pie_txt)
    MANIFIESTO.append({
        "id": id_, "titulo": titulo, "rutas": rutas,
        "sha256": {e: hashlib.sha256((W / r).read_bytes()).hexdigest() for e, r in rutas.items()},
        "tabla": str(tp.relative_to(W)), "procedencia": procedencia,
        "n": n, "marca": marca, "nota_lectura": nota_lectura,
    })
    return rutas


def panel_ausencia(id_, titulo, que_habria, motivo, que_haria_falta, tam=(7.0, 4.2)):
    fig, ax = plt.subplots(figsize=tam)
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes,
                               facecolor=SUPERFICIE, edgecolor=LINEA_BASE, lw=1.2, ls=(0, (6, 4))))
    y = 0.88
    ax.text(0.05, y, f"FIGURA {id_} — NO PRODUCIBLE", transform=ax.transAxes,
            fontsize=11, weight="bold", color=CRITICO, va="top")
    y -= 0.13
    ax.text(0.05, y, titulo, transform=ax.transAxes, fontsize=10, color=TINTA, va="top", wrap=True)
    for etiqueta, texto in (("Qué habría mostrado", que_habria),
                            ("Por qué no se puede producir", motivo),
                            ("Qué haría falta", que_haria_falta)):
        y -= 0.16
        ax.text(0.05, y, etiqueta, transform=ax.transAxes, fontsize=8,
                color=APAGADO, va="top", weight="bold")
        y -= 0.055
        ax.text(0.05, y, _envolver(texto, 88), transform=ax.transAxes,
                fontsize=8, color=TINTA_2, va="top", linespacing=1.5)
    base = f"ausencia_{id_}"
    rutas = {}
    for ext in ("pdf", "svg", "png"):
        r = FIG / f"{base}.{ext}"
        fig.savefig(r, format=ext)
        rutas[ext] = str(r.relative_to(W))
    plt.close(fig)
    PIES.append(f"**Figura {id_}.** {titulo}. NO PRODUCIBLE — {motivo}")
    MANIFIESTO.append({"id": id_, "titulo": titulo, "rutas": rutas,
                       "sha256": {e: hashlib.sha256((W / r).read_bytes()).hexdigest()
                                  for e, r in rutas.items()},
                       "tabla": None, "procedencia": [], "n": None,
                       "marca": "AUSENCIA", "motivo": motivo})
    return rutas


def _envolver(t: str, ancho: int) -> str:
    import textwrap
    return "\n".join(textwrap.wrap(t, ancho))


def marca_corte_eje(ax, x=0.0):
    """§8 H-5: todo eje truncado lleva marca de corte visible."""
    ax.plot([x, x], [0.02, 0.05], transform=ax.get_xaxis_transform(),
            color=APAGADO, lw=1.2, clip_on=False, zorder=10)
    ax.text(x, 0.065, "⁄⁄", transform=ax.get_xaxis_transform(),
            ha="center", fontsize=9, color=APAGADO, clip_on=False)
