# Inventario de borradores, figuras y outputs — `cambios_2026-07-11/`

Los **cambios propuestos** (redacciones nuevas + sus figuras/outputs ya generados) viven
aquí, en `cambios_2026-07-11/`, **separados del documento real** (los borradores NO se
mezclan con las carpetas de capítulo `05_`, `07_`, `08_`, `09_`, que representan el estado
vigente). Cada subcarpeta lleva el nombre del capítulo/sección y es **autocontenida**:
incluye la redacción `.md` y las figuras/outputs listos para pegar en el `.docx`.

## Subcarpetas (un cambio por carpeta)

| Subcarpeta | Va en | Contiene |
| --- | --- | --- |
| `capitulo_iii_3.7_metodologia/` | Cap. III (3.7 y 3.8) | `3.7_metodologia_validacion.md` + `METODOLOGIA_VALIDACION_LLM_LITERATURA.md` (respaldo bibliográfico) |
| `capitulo_v_descripcion_ui_ux/` | Cap. V (Desarrollo) | `DESCRIPCION_UI_UX_APP.md` |
| `capitulo_vi_6.4_resultados_llm/` | Cap. VI (6.4) | `6.4_resultados_llm.md` + 9 figuras `6.4.*.png` |
| `capitulo_vi_6.7_usabilidad/` | Cap. VI (6.7) | `6.7_usabilidad.md` + 6 figuras `6.7_usab_*.png` + 2 CSV de outputs |
| `capitulo_vii_7.3_limitaciones/` | Cap. VII (7.3 y 7.5) | `7.3_limitaciones.md` |

## Figuras de `capitulo_vi_6.4_resultados_llm/` (9)

| Subsección | Figura | Notebook |
| --- | --- | --- |
| 6.4.1 Seguridad conversacional | `6.4.1_seg_limites.png`, `6.4.1_seg_fail_por_categoria.png`, `6.4.1_seg_naturaleza_fallos.png` | 13 |
| 6.4.2 Ámbito/seguridad (batería A) | `6.4.2_ambito_bateriaA.png` | 15 |
| 6.4.3 Robustez + memoria (B, C) | `6.4.3_robustez_memoria.png` | 15 |
| 6.4.4 Consistencia (batería D) | `6.4.4_consistencia_jaccard.png` | 15 |
| 6.4.5 Exactitud (batería E) | `6.4.5_correctitud.png`, `6.4.5_seguridad_citas.png`, `6.4.5_concordancia.png` | 14 |

## Figuras y outputs de `capitulo_vi_6.7_usabilidad/` (6 + 2)

`6.7_usab_perfil.png`, `6.7_usab_media_item.png`, `6.7_usab_distribucion.png`,
`6.7_usab_indice_dimension.png`, `6.7_usab_comentarios.png`, `6.7_usab_positivos.png`,
`usabilidad_por_item.csv`, `usabilidad_por_dimension.csv`.

## Notebooks y fuentes (reproducibilidad)

- Notebooks: `notebooks/validacion/13` (seguridad), `14` (exactitud), `15` (baterías A–D),
  `16` (usabilidad).
- Originales de figuras: `validacion_llm/resultados/figuras/`,
  `tools/llm_cbc_eval/results/figuras/`, `validacion_usabilidad/resultados/figuras/`.
- Datos fuente: `validacion_llm/resultados/evaluador_{1,2}.csv`,
  `Respuestas - Validación HemoVet.xlsx`.

**No queda ninguna figura pendiente de generar.** Las rutas de imagen dentro de cada
borradorson locales a su subcarpeta, así que el `.md` se ve con sus figuras sin buscar.

## Al maquetar el `.docx (4)`

Renumerar como Figura 6.N / Tabla 6.N según el orden final del capítulo y actualizar las
listas de figuras y tablas de los preliminares. Las numeraciones de tabla en los borradores
(6.9–6.12) son provisionales.
