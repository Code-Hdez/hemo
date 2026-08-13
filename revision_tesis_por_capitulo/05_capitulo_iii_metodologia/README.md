# 05 - Capitulo III - Metodologia

## Problema actual

El documento actual usa el Capitulo III para describir modulos como si fuera desarrollo. La plantilla pide metodologia. Hay que separar metodo de implementacion.

## Estructura recomendada

### 3.1 Metodologia de desarrollo del software

Contenido:

- Gestion incremental por tareas y entregables.
- Control de versiones con Git/GitHub.
- Separacion backend/frontend/modelos/datos.
- Docker Compose para reproducibilidad.
- Pruebas backend y frontend.
- CI/CD y despliegue productivo.
- Manejo de secretos por variables de entorno.

### 3.2 Metodologia del componente de tecnologia emergente

Contenido:

- Construccion del corpus IDEXX.
- Incorporacion del DAP como validacion externa.
- Limpieza y estandarizacion.
- Feature engineering.
- Etiquetado multilabel desde `idexx_comments`.
- Split temporal 70/15/15.
- Seleccion de XGBoost.
- Calibracion, umbrales y policy freeze.
- Validacion clinica con dos medicos.
- Validacion del modulo LLM/RAG.

## Cifras que deben aparecer

- 7 etiquetas oficiales de modelo.
- 2 etiquetas por regla deterministica.
- 1 etiqueta excluida.
- PR-AUC macro del modelo v3: `0.9577`.
- Validacion DAP: 1,301 registros.
- Validacion clinica: 526 casos totales y 509 evaluables con modelo.

## Evidencia incluida

- `final_label_policy.json`
- `policy_freeze_v3.json`
- `threshold_freeze_record_v3.json`
- `artifact_manifest_v3.json`
- `metrics_test_v3.json`
- `cv_results_v3_summary.csv`
- `calibration_metrics_v3.csv`
- `threshold_freeze_metrics_v3.csv`
- `nb06_validation_summary.json`



---

## Estado 11/7/2026 (revisión sobre `.docx (4)`)

> Bloque nuevo del 11/7/2026. Todo lo de arriba es el plan original; esto es el estado verificado hoy.

**Estado:** completo (3.1–3.9, P670–P972), alineado.
**Reconciliar cifra de features:** P734 dice **43 características** (coherente con la corrección de Cap. II). Asegurar que quede 43 en TODO el documento.
**Alineado:** 2,454 / 1,301 (P713, P724), PR-AUC macro v3 = 0.9577 (P790), validación clínica 526/509 (P924).
**Metodología de validación del LLM (borrador listo):** `cambios_2026-07-11/capitulo_iii_3.7_metodologia/3.7_metodologia_validacion.md` cubre las dos vías, con respaldo bibliográfico en `cambios_2026-07-11/capitulo_iii_3.7_metodologia/METODOLOGIA_VALIDACION_LLM_LITERATURA.md` (QUEST, Med-PaLM, red-teaming, RAG):
- **Evaluación de seguridad/alcance del compañero** (`tools/llm_cbc_eval/`): banco de 770 preguntas por categoría de riesgo contra el endpoint real, dos rondas (línea base vs. endurecimiento de guardrails).
- **Baterías formales A–E** (`validacion_llm/`): ámbito/seguridad, robustez ortográfica, memoria multi-turno, consistencia y exactitud de contenido con rúbrica de dos veterinarios y kappa de Cohen.

**Pendiente:** pegar 3.7 al `.docx`. La subsección de exactitud de contenido debe describirse como validación con dos médicos veterinarios; **los datos reales de esa rúbrica ya están completos** (12/7/2026, ver Cap. VI 6.4.4).

**Metodología de validación de usabilidad (nueva, 12/7/2026):** describir el tercer eje de validación —la **encuesta de usabilidad del prototipo** (`Respuestas - Validación HemoVet.xlsx`), n = 44—. Instrumento propio de 13 ítems Likert (1–5) organizados por etapa del recorrido (pantalla principal, proceso de análisis, resultados/comprensión, ayuda/utilidad) más 3 preguntas abiertas. Métricas: media e índice de usabilidad `(media−1)/4×100`, % favorable (top-2-box) y análisis temático de comentarios. Resultados en Cap. VI 6.7; análisis en `notebooks/validacion/16_validacion_usabilidad.ipynb`. Declarar como usabilidad *percibida* con muestra de conveniencia (no un SUS estandarizado, sin medición cronometrada de tareas).
