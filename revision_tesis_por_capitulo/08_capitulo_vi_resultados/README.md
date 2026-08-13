# 08 - Capitulo VI - Analisis de resultados

## Prioridad alta

Este capitulo falta como seccion independiente. Debe absorber el analisis que ahora esta mezclado en Capitulo V.

## Estructura recomendada

### 6.1 Resultados del modelo

Usar:

- `evidencia/tabla_metricas_completas.csv`
- `evidencia/tabla_bootstrap_ci.csv`
- `evidencia/final_system_state.json`
- `imagenes/roc_pr_curves.png`
- `imagenes/shap_importancia_por_etiqueta.png`

Puntos clave:

- PR-AUC macro v3: `0.9577`.
- Estado final: `READY_FOR_PRODUCTION_WITH_LIMITATIONS`.
- PR-AUC macro final system state: `0.9529`.
- F1 macro final: `0.8727`.
- Recall macro final: `0.9205`.

### 6.2 Validacion externa DAP

Usar:

- `evidencia/nb06_validation_summary.json`
- `evidencia/activation_rates_comparison.csv`
- `imagenes/nb06_activation_rates_comparison.png`

Puntos clave:

- DAP tiene 1,301 registros.
- Shift severo: `Monocytes`, `RDW`.
- Shift moderado: `WBC`, `Neutrophils`, `Platelets`, `HCT`, `MCHC`, `MPV`, `MCV`.
- No hay F1 ni PR-AUC en DAP porque no hay etiquetas compatibles.

### 6.3 Validacion clinica

Esta es la parte que mas debe reforzarse.

Usar:

- `evidencia/resumen_validacion.json`
- `evidencia/resumen_metricas.csv`
- `evidencia/comparacion_larga.csv`
- `imagenes/kappa_heatmap_completo.png`
- `imagenes/kappa_v3_vs_v4.png`
- `imagenes/metricas_por_clase_global.png`
- `imagenes/panel_fig1_kappa_m1_m2.png`
- `imagenes/panel_fig2_modelo_v3_vs_medicos.png`
- `imagenes/panel_fig3_impacto_reentrenamiento.png`
- `imagenes/panel_fig4_rendimiento_final.png`

Cifras finales verificadas desde CSV:

| Metrica | Valor |
| --- | ---: |
| Casos totales | 526 |
| Casos evaluables con modelo | 509 |
| Evaluadores | 2 |
| Semanas | 4 |
| Macro kappa M1 vs M2 | 0.684 |
| Macro kappa modelo vs M1 | 0.629 |
| Macro F1 modelo vs M1 | 0.704 |

Resultados globales modelo vs medico 1:

| Etiqueta | F1 | Sensibilidad | Especificidad |
| --- | ---: | ---: | ---: |
| QC_REQUIERE_FROTIS | 0.788 | 0.768 | 0.884 |
| PATRON_INFLAMATORIO | 0.863 | 0.901 | 0.876 |
| PATRON_LEUCOGRAMA_ESTRES | 0.689 | 0.841 | 0.733 |
| PATRON_ANEMIA_NO_REGENERATIVA | 0.652 | 0.548 | 0.974 |
| PATRON_HEMOLISIS_MCHC | 0.597 | 0.597 | 0.944 |
| PATRON_POLICITEMIA | 0.592 | 0.463 | 0.981 |
| PATRON_ANEMIA_REGENERATIVA | 0.610 | 0.514 | 0.987 |
| QC_AGREGADOS_PLAQUETARIOS | 0.839 | 0.743 | 0.998 |

Interpretacion:

- Mejor desempeno: inflamatorio y agregados plaquetarios.
- Debilidades: leucograma de estres por falsos positivos; policitemia por falsos negativos; hemolisis MCHC por desacuerdo clinico.
- La concordancia interevaluador no es perfecta, por lo que las discrepancias no deben interpretarse automaticamente como error del modelo.

### 6.4 Resultados del LLM/RAG

**Estado (12 jul 2026): ✅ COMPLETO.** Redacción consolidada y lista para pegar en
**`cambios_2026-07-11/capitulo_vi_6.4_resultados_llm/6.4_resultados_llm.md`** (este directorio), con seis subsecciones:

- **6.4.1 Seguridad conversacional** (banco de 770 preguntas, dos rondas; notebook 13):
  *prompt injection* 61→1, diagnóstico definitivo 25→2. Figuras `cambios_2026-07-11/capitulo_vi_6.4_resultados_llm/6.4.1_seg_*.png`.
- **6.4.2 Ámbito y seguridad — batería A** (pipeline real): 31/40 adversariales (77.5%),
  15/20 legítimos (75%), 17/30 fuera de ámbito claro (56.7%). Figura `cambios_2026-07-11/capitulo_vi_6.4_resultados_llm/6.4.2_ambito_bateriaA.png`.
- **6.4.3 Robustez y memoria — baterías B y C:** 20/20 typos, 15/17 turnos. Figura `cambios_2026-07-11/capitulo_vi_6.4_resultados_llm/6.4.3_robustez_memoria.png`.
- **6.4.4 Consistencia — batería D:** Jaccard medio 0.84. Figura `cambios_2026-07-11/capitulo_vi_6.4_resultados_llm/6.4.4_consistencia_jaccard.png`.
- **6.4.5 Exactitud de contenido — batería E (rúbrica de 2 veterinarios):** 30/30 seguras,
  83.3% correcto/parcial, 0 alucinadas, citas 63.3%; concordancia κ 0.841 / κ ponderado 0.904
  (+ PABAK y AC1 de Gwet por la paradoja de kappa). Tablas 6.11 y 6.12; figuras `cambios_2026-07-11/capitulo_vi_6.4_resultados_llm/6.4.5_*.png`.
- **6.4.6 Síntesis.**

Reemplaza el 50/50 inválido de `llm_guardrails_eval.json`. Notebooks fuente: 13 (seguridad),
15 (baterías A–D), 14 (exactitud). Evidencia cruda: `validacion_llm/resultados/` y
`tools/llm_cbc_eval/results/`.

> Decisión de producto/tesis aún abierta: definir si preguntas como "¿este hemograma
> indica anemia?" son educación orientativa (permitido) o diagnóstico (a desviar); de ello
> depende el criterio de los FAIL residuales de `diagnostico_directo` (no son inseguros).

### 6.5 Resultados de rendimiento y pruebas

Usar:

- `evidencia/api_bench_predict.json`
- `evidencia/backend_test_report.json`

Cifras:

- Latencia media inferencia in-process: `28.73 ms`.
- p50: `27.93 ms`.
- p95: `33.9 ms`.
- Backend: `25 passed`.

### 6.6 Vigilancia poblacional

Usar:

- `evidencia/population_surveillance_report_v3.json`

Debe presentarse como orientativo, no como prevalencia real.

### 6.7 Validación de usabilidad del prototipo

Usar:

- `Respuestas - Validación HemoVet.xlsx` (fuente, 44 respuestas)
- `validacion_usabilidad/resultados/usabilidad_por_item.csv` y `_por_dimension.csv`
- Redacción lista: `cambios_2026-07-11/capitulo_vi_6.7_usabilidad/6.7_usabilidad.md`
- Notebook: `notebooks/validacion/16_validacion_usabilidad.ipynb`
- Figuras: `cambios_2026-07-11/capitulo_vi_6.7_usabilidad/6.7_usab_*.png` (perfil, media por ítem, distribución, índice por dimensión, comentarios, positivos)

Cifras clave:

- Media global **4.37/5**, índice de usabilidad **84/100**, **81.6 %** favorable, **0 %** desfavorable.
- Muestra: 50 % dueños de mascota, 77 % nunca había visto un hemograma (público lego).
- Aciertos: diccionario, guía de 3 pasos, corrección de valores, colores semánticos, aviso de no reemplazar al veterinario, modo invitado.
- Mejoras priorizadas: velocidad y memoria del chat, leyenda de colores fija, compartir por WhatsApp/correo, alto contraste, mini-tutorial (el tour no arrancaba).



---

## Estado 11/7/2026 (revisión sobre `.docx (4)`)

> Bloque nuevo del 11/7/2026. Todo lo de arriba es el plan original; esto es el estado verificado hoy.

**6.4 — quitar el 50/50 inválido (P1916/Tabla 6.9, P1931) y reemplazar por las cifras reales.** Redacción lista en `cambios_2026-07-11/capitulo_vi_6.4_resultados_llm/6.4_resultados_llm.md`. Estructura:

- **6.4.1 Seguridad y alcance — evaluación del compañero** (`tools/llm_cbc_eval/`, 770 preguntas, dos rondas). LISTO: `cambios_2026-07-11/capitulo_vi_6.4_resultados_llm/6.4_resultados_llm.md` + notebook `13_validacion_llm_chat.ipynb` + figuras `fig1–3`. Resultado: resistencia a prompt injection 61→1, diagnóstico definitivo 25→2.
- **6.4.2–6.4.3 Baterías formales A–D** (`validacion_llm/`, corridas en la VM 11-12 jul con datos REALES del sistema): A ámbito/seguridad 31/40 adversariales rechazados (77.5%), 15/20 legítimos (75%), 17/30 fuera de ámbito claro (56.7%); B robustez 20/20; C memoria 17 turnos; D consistencia Jaccard medio 0.84. CSV en `validacion_llm/resultados/`.
- **6.4.4 Exactitud de contenido (rúbrica de 2 veterinarios) — ✅ COMPLETA (12/7/2026).** Los dos veterinarios llenaron la rúbrica (`validacion_llm/resultados/evaluador_1.csv`, `evaluador_2.csv`). Redacción con Tablas 6.10 y 6.11 en `cambios_2026-07-11/capitulo_vi_6.4_resultados_llm/6.4_resultados_llm.md`; análisis y figuras en `notebooks/validacion/14_validacion_llm_exactitud.ipynb` (figuras `cambios_2026-07-11/capitulo_vi_6.4_resultados_llm/6.4.5_correctitud.png`, `fig64_seguridad_citas.png`, `fig64_concordancia.png`). Resultado: **30/30 seguras según ambos**, 83.3 % correctas/parciales (IC95 70–97 %), 0 alucinadas, citas apropiadas 63.3 %, 5 incorrectas de contenido (no de seguridad). Concordancia casi perfecta: κ Cohen 0.841, κ ponderado 0.904, reforzada con PABAK y AC1 de Gwet por la *paradoja de kappa* (seguridad al 100 % anula la varianza).

**Alineado y correcto (sin cambios):** 6.1 (PR-AUC macro 0.9529, F1 0.8727, recall 0.9205, P1491), 6.2 DAP, 6.3 clínica (526/509, 60 batches, 4 semanas, P1806), 6.5 rendimiento (28.73 ms), 6.6 vigilancia.

**6.7 Usabilidad — ✅ NUEVA (12/7/2026).** Encuesta de 44 participantes. Redacción lista en `cambios_2026-07-11/capitulo_vi_6.7_usabilidad/6.7_usabilidad.md`, análisis en `notebooks/validacion/16_validacion_usabilidad.ipynb`, figuras `cambios_2026-07-11/capitulo_vi_6.7_usabilidad/6.7_usab_*.png`. Media global 4.37/5 (índice 84/100), 81.6 % favorable, 0 % desfavorable; muestra mayoritariamente lega (77 % nunca vio un hemograma). Mejoras accionables priorizadas → alimentan 7.5.
