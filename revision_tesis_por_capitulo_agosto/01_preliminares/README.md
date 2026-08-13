# 01 - Preliminares (pasada de agosto)

## Estado verificado: los bloqueantes de julio están resueltos

Julio pedía agregar Lista de tablas, Lista de figuras y Lista de anexos. Las
tres **ya existen** en el `.md (1)` actual (líneas 301, 354, 406). También
verificado: Resumen ejecutivo y Abstract (líneas 423-446) usan las cifras
finales reconciliadas — PR-AUC macro 0.9529, F1 macro 0.8727, recall macro
0.9205, kappa DAP 0.629/0.704, kappa M1-M2 0.684 — todas coinciden
exactamente con las tablas de Cap VI. 43 características, mencionado de forma
consistente (la contradicción 38-vs-43 que julio marcó ya no aparece en
ninguna parte leída de este documento).

## Único punto a revisar: la Lista de Anexos

La Tabla de Anexo C (línea 412) describe: *"CSV/JSON de red-teaming, baterías
A-E, robustez, memoria, consistencia, rúbricas y evaluación veterinaria"* —
esto es correcto como inventario de archivos (existen), pero implica que la
evaluación veterinaria está completa y vigente. Como se documenta en
`08_capitulo_vi_resultados/README.md`, la evaluación veterinaria de la Batería
E (rúbrica de exactitud) es de julio, anterior a la re-corrida del pipeline
del 1 de agosto — no es falso que exista, pero conviene no dejar que el
resumen ejecutivo/preliminares insinúen que certifica el sistema actual sin
esa salvedad.

## No verificado en esta pasada

Formato IEEE de citas, numeración consecutiva de tablas/figuras a lo largo de
todo el documento, agradecimientos/dedicatoria (quedaron con encabezado vacío
en las líneas 415-421, aparentemente opcional según julio).
