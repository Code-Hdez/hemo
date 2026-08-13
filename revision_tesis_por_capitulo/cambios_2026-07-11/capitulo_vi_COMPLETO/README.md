# Capítulo VI — COMPLETO (para armar todo el capítulo)

Carpeta autocontenida con **el Capítulo VI entero listo para pegar** en el `.docx`: el
contenido actual del documento + los agregados nuevos de las validaciones, todo en un solo
archivo con sus 29 figuras locales.

## Contenido

- **`6_capitulo_vi_COMPLETO.md`** — el capítulo completo (6.1 a 6.8) con tablas y figuras.
- **29 figuras `.png`** — todas las del capítulo, referenciadas con ruta local (se ven al
  abrir el `.md`).

## Qué es contenido actual y qué es nuevo

| Sección | Origen | Estado |
| --- | --- | --- |
| 6.1 Motor de clasificación | documento actual | sin cambios |
| 6.2 Validación externa DAP | documento actual | sin cambios |
| 6.3 Validación clínica | documento actual | sin cambios |
| **6.4 Módulo LLM/RAG** | **validaciones nuevas** | **REEMPLAZA el "50/50" inválido** (notebooks 13/14/15) |
| 6.5 Rendimiento técnico | documento actual | sin cambios (Tabla renumerada 6.10→6.13) |
| 6.6 Vigilancia poblacional | documento actual | sin cambios (Tabla renumerada 6.11→6.14) |
| **6.7 Usabilidad del prototipo** | **validación nueva** | **SECCIÓN NUEVA** (notebook 16, n=44) |
| 6.8 Síntesis crítica | documento actual (era 6.7) | actualizada con LLM real + usabilidad |

## Numeración

- **Tablas:** 6.1–6.15 (nuevas: 6.9–6.12 LLM, 6.15 usabilidad).
- **Figuras:** 6.1–6.29 (nuevas: 6.15–6.23 LLM, 6.24–6.29 usabilidad).
- Es **provisional**; confirmar al maquetar y actualizar las listas de tablas/figuras de los
  preliminares.

## Trazabilidad

- Notebooks fuente: `notebooks/validacion/13` (seguridad), `14` (exactitud), `15` (baterías
  A–D), `16` (usabilidad); las figuras del modelo/clínica salen de los notebooks 06–12.
- Datos: `validacion_llm/resultados/`, `tools/llm_cbc_eval/results/`,
  `Respuestas - Validación HemoVet.xlsx`.
- El borrador aislado de cada sección nueva vive en las carpetas hermanas
  `capitulo_vi_6.4_resultados_llm/` y `capitulo_vi_6.7_usabilidad/`.
