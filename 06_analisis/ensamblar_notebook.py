#!/usr/bin/env python3
"""Ensambla el notebook de figuras a partir de construir_figuras.py.

El notebook NO es una copia decorativa: es el mismo código, partido en celdas por
bloque, de modo que Restart & Run All regenera el catálogo entero. El motor
(motor_figuras.py) se importa como módulo hermano, que es lo que hace el script.
"""
from __future__ import annotations
import pathlib
import re

import nbformat as nbf

AQUI = pathlib.Path(__file__).resolve().parent
FUENTE = AQUI / "construir_figuras.py"
SALIDA = AQUI / "HEMOVET_RECARACTERIZACION_A100_FIGURAS.ipynb"

PORTADA = """# Catálogo de figuras — HemoVet · RECARACTERIZACION-A100

Notebook único que produce **las 36 figuras del capítulo de resultados y los 9
paneles de ausencia**, cada una en PDF, SVG y PNG a 300 ppp, con su tabla gemela
en CSV y su procedencia hasta el fichero de origen.

## Cómo se ejecuta

`Restart & Run All`. No hace falta nada más: no toca la red, no enciende la GPU y
no escribe fuera de `06_analisis/`.

## Los invariantes que este notebook cumple

| | Invariante | Cómo se cumple aquí |
|---|---|---|
| **I-A** | **Cero GPU** | El notebook sólo lee ficheros. No hay ni una llamada de red. |
| **I-B** | **Cero cifras del dominio a mano** | Todo dato entra por `cargar()`, que hashea y registra procedencia. Las únicas constantes literales son físicas (ancho de banda de la A100) o de estilo, y están juntas y con fuente en `motor_figuras.py`. Cada cálculo que reproduce una cifra publicada lleva su `assert`. |
| **I-C** | **La evidencia no se toca** | Sólo se escribe en `06_analisis/`. |
| **I-D** | **Honestidad gráfica** | Cero no es ausencia: toda proporción lleva intervalo de Wilson y su *n*. No hay tendencias sobre dos puntos, ni suavizados con *n* pequeño. El arranque en frío y los turnos fallidos se dibujan; no se recortan. Todo eje truncado lleva marca de corte. |
| **I-E** | **Cada figura, su tabla** | `figura()` es la única puerta de salida y emite siempre los tres formatos más el CSV. |
| **I-F** | **Las ausencias se dibujan** | Nueve paneles de ausencia, con qué habría mostrado, por qué no se puede y qué haría falta. |
| **I-G** | **Los resultados incómodos, igual de bien** | La puerta de kappa que no pasa (E4), el intervalo de la alucinación con *n* = 9 (D7), la rúbrica que no llegó a operar (D8) y los veredictos del informe anteriores a la réplica (F1). |
| **I-H** | **Reproducible** | Semilla fija `20260811`. Mismos ficheros de entrada → mismas figuras. |
| **I-I** | **Mirarlas** | Cada figura exportada se abrió y se revisó. Las correcciones que salieron de esa revisión están comentadas en el código. |

## Una advertencia sobre una aserción que falla

La aserción `n verificables` **falla a propósito y se deja fallar**. El informe
publicó «~20 preguntas verificables»; `02_fixtures/verdad.json` contiene **9**.
Con *n* = 9 la cota superior de Wilson es **29,9 %**, no el 16,8 % publicado: la
cifra del informe subestimaba la incertidumbre casi a la mitad. No se relajó la
tolerancia; se corrigió la cifra y se declaró en la nota de lectura de D7.
"""

CIERRE = """## Qué ha quedado en disco

| Artefacto | Qué contiene |
|---|---|
| `figuras/fig_*.{pdf,svg,png}` | Las 36 figuras, tres formatos, 300 ppp |
| `figuras/ausencia_*.{pdf,svg,png}` | Los 9 paneles de ausencia |
| `figuras/MANIFIESTO.json` | Una entrada por figura con el SHA-256 de cada fichero exportado |
| `tablas/tab_*.csv` | La tabla gemela de cada figura (`;` de separador, coma decimal) |
| `PROCEDENCIA.json` | SHA-256, tamaño y número de registros de cada fichero de entrada |
| `TRAZABILIDAD.csv` | Figura → fichero fuente → hash del fuente |
| `PIES_DE_FIGURA.md` | Pie y nota de lectura de cada figura, listos para pegar |
| `VERIFICACION_NOTEBOOK.txt` | Las aserciones y las comprobaciones estructurales |
| `grises/` | El pase de supervivencia en escala de grises (`prueba_grises.py`) |

Para el pase de grises, ejecutar aparte `python prueba_grises.py`.
"""

TITULOS = {
    "BLOQUE A · TRAZABILIDAD": ("A · Trazabilidad y comparabilidad",
        "De dónde sale cada cosa: las ventanas de GPU, el corpus de evidencia previa, "
        "qué registra cada instrumento, qué se pudo reconstruir del protocolo antiguo y "
        "el veredicto doble de comparabilidad."),
    "BLOQUE B": ("B · Identidad del sistema medido",
        "Qué modelo, qué GPU, qué versión y qué limitaciones se declararon — y cuándo."),
    "BLOQUE C": ("C · Física de la A100",
        "Techos, TPOT, MBU, el coste real de la gramática y el determinismo intra-máquina. "
        "Todo caracterización **absoluta**: la física de la L4 no es verificable."),
    "BLOQUE D": ("D · Comportamiento conversacional",
        "Los 45 turnos de las tres baterías: desenlaces, latencia, la frontera de la "
        "ventana, la verificación contra la tabla de verdad y la cobertura de la rúbrica."),
    "BLOQUE E": ("E · La réplica estricta, pareada",
        "El mismo corpus de 70 turnos recorrido dos veces. Aquí está el único resultado "
        "de comparación legítimo y aquí está la puerta que no pasa."),
    "BLOQUE F": ("F · Balance",
        "Las diez hipótesis, los cinco efectos, la potencia del diseño y qué niveles del "
        "esquema de trazas llegó a poblar la campaña."),
    "PANELES DE AUSENCIA": ("Paneles de ausencia",
        "Nueve cosas que esta campaña **no** puede mostrar. Cada una dice qué habría "
        "mostrado, por qué no se puede producir y qué haría falta. Una ausencia declarada "
        "es un resultado; una ausencia callada es un error."),
    "ARTEFACTOS FINALES": ("Artefactos finales",
        "Manifiesto con hashes, trazabilidad, índice de tablas, pies de figura y el "
        "fichero de verificación."),
}


def celdas():
    src = FUENTE.read_text(encoding="utf-8")
    # Cabecera: todo lo anterior al primer marcador de bloque.
    corte = src.index("# ═══════════════ BLOQUE A")
    cabeza = src[:corte].rstrip()
    # El import del modulo hermano necesita que su carpeta este en sys.path.
    cabeza = cabeza.replace(
        "from motor_figuras import *  # noqa: F403",
        "import sys, pathlib as _pl\n"
        "sys.path.insert(0, str(_pl.Path.cwd()))\n"
        "from motor_figuras import *  # noqa: F403")
    yield nbf.v4.new_markdown_cell(PORTADA)
    yield nbf.v4.new_markdown_cell(
        "## Carga, derivados y aserciones\n\n"
        "`cargar()` es la **única** puerta de entrada de datos: lee el fichero, calcula su "
        "SHA-256 y lo registra en `PROCEDENCIA`. Ninguna celda posterior vuelve a tocar el "
        "disco para leer datos.\n\n"
        "A continuación se recalculan desde cero las cifras que los informes ya publicaron "
        "y se comprueban con `afirmar()`. Diez coinciden. La undécima no, y se deja constar.")
    yield nbf.v4.new_code_cell(cabeza)

    bloques = re.split(r"^(# ═+ ?(?:BLOQUE [A-F][^\n]*|PANELES DE AUSENCIA|ARTEFACTOS FINALES) ?═*)$",
                       src[corte:], flags=re.M)
    # bloques[0] es lo que va antes del primer marcador (vacio), luego pares (marca, cuerpo)
    for i in range(1, len(bloques), 2):
        marca, cuerpo = bloques[i], bloques[i + 1].strip("\n")
        clave = next((k for k in TITULOS if k in marca), None)
        if clave:
            titulo, intro = TITULOS[clave]
            yield nbf.v4.new_markdown_cell(f"## {titulo}\n\n{intro}")
        if cuerpo.strip():
            yield nbf.v4.new_code_cell(cuerpo)
    yield nbf.v4.new_markdown_cell(CIERRE)


nb = nbf.v4.new_notebook(cells=list(celdas()))
nb.metadata.update({
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python"},
})
nbf.write(nb, SALIDA)
print(f"{SALIDA.name}: {len(nb.cells)} celdas "
      f"({sum(1 for c in nb.cells if c.cell_type == 'code')} de código)")
