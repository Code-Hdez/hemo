#!/usr/bin/env python3
"""§12.8 — prueba de supervivencia en escala de grises.

Convierte cada PNG del catálogo a luminancia y los monta en rejillas para
inspección visual. Además mide, para cada figura, el contraste entre los tonos
de gris presentes: si dos series sólo se distinguían por color, sus grises
colapsan y la figura queda ilegible sin él.
"""
from __future__ import annotations
import json
import pathlib

from PIL import Image, ImageDraw

W = pathlib.Path(__file__).resolve().parent.parent
FIG = W / "06_analisis/figuras"
SAL = W / "06_analisis/grises"
SAL.mkdir(parents=True, exist_ok=True)

ORDEN = json.loads((FIG / "MANIFIESTO.json").read_text(encoding="utf-8"))
ids = [m["id"] for m in ORDEN]

COLS, ANCHO_CELDA = 4, 620
FILAS_POR_HOJA = 3


def a_grises(p: pathlib.Path) -> Image.Image:
    return Image.open(p).convert("L").convert("RGB")


hojas, celdas = [], []
for m in ORDEN:
    p = W / m["rutas"]["png"]
    g = a_grises(p)
    g.thumbnail((ANCHO_CELDA, ANCHO_CELDA), Image.LANCZOS)
    celdas.append((m["id"], g))
    (SAL / f"{p.stem}_gris.png").write_bytes(b"")
    a_grises(p).save(SAL / f"{p.stem}_gris.png")

por_hoja = COLS * FILAS_POR_HOJA
for h in range(0, len(celdas), por_hoja):
    lote = celdas[h:h + por_hoja]
    filas = (len(lote) + COLS - 1) // COLS
    alto_celda = max(c[1].height for c in lote) + 26
    lienzo = Image.new("RGB", (COLS * (ANCHO_CELDA + 14) + 14,
                               filas * (alto_celda + 14) + 14), (252, 252, 251))
    d = ImageDraw.Draw(lienzo)
    for k, (idf, im) in enumerate(lote):
        cx = 14 + (k % COLS) * (ANCHO_CELDA + 14)
        cy = 14 + (k // COLS) * (alto_celda + 14)
        d.rectangle([cx - 2, cy - 2, cx + ANCHO_CELDA + 2, cy + alto_celda + 2],
                    outline=(200, 199, 190))
        d.text((cx + 4, cy + 4), idf, fill=(11, 11, 11))
        lienzo.paste(im, (cx + (ANCHO_CELDA - im.width) // 2, cy + 22))
    r = SAL / f"HOJA_GRISES_{h // por_hoja + 1}.png"
    lienzo.save(r)
    hojas.append(str(r.relative_to(W)))

# Recuento de tonos distintos: una figura que sólo use color colapsa a pocos grises.
resumen = []
for m in ORDEN:
    im = Image.open(W / m["rutas"]["png"]).convert("L")
    hist = im.histogram()
    tonos = sum(1 for c in hist if c > im.width * im.height * 0.0004)
    resumen.append({"id": m["id"], "tonos_de_gris_relevantes": tonos})

(SAL / "PRUEBA_GRISES.json").write_text(
    json.dumps({"hojas": hojas, "n_figuras": len(ORDEN), "por_figura": resumen},
               ensure_ascii=False, indent=1), encoding="utf-8")
print(f"hojas: {len(hojas)} · figuras en grises: {len(ORDEN)}")
print("tonos <4 (revisar):",
      [r["id"] for r in resumen if r["tonos_de_gris_relevantes"] < 4] or "ninguna")
