# 07 - Capitulo V - Desarrollo

## Que debe contener

Este capitulo debe explicar como se construyo el sistema, no analizar en profundidad los resultados. Los resultados van en Capitulo VI.

## Estructura recomendada

### 5.1 Construccion del pipeline de datos

- Extraccion de PDFs.
- Normalizacion de campos.
- Fusion IDEXX/DAP.
- Trazabilidad de artefactos.

### 5.2 Desarrollo del motor ML

- Feature set.
- Entrenamiento XGBoost.
- Calibracion y umbrales.
- Reglas deterministicas.
- Manifiestos y hashes.

### 5.3 Desarrollo del backend

- FastAPI.
- Routers por dominio.
- PostgreSQL/Alembic.
- Autenticacion y cookie HttpOnly.
- Endpoints `/api/v1`.

### 5.4 Desarrollo del frontend

- Resumen personal.
- Carga y revision de hemograma.
- Historial/evolucion.
- Chat.
- Biblioteca.
- Vigilancia.

### 5.5 Desarrollo del modulo LLM/RAG

- Ingesta offline.
- ChromaDB/FastEmbed/Ollama.
- Guardrails.
- Validacion de salida.
- SSE para streaming.

### 5.6 Desarrollo de vigilancia poblacional

- Agregacion.
- Umbrales de privacidad.
- Mapas y reporte.

### 5.7 Pruebas y despliegue

- Docker Compose.
- CI/CD.
- Smoke tests.
- Benchmark de inferencia.

## Evidencia incluida

- `evidencia/e2e_demo_run.json`
- `evidencia/api_bench_predict.json`
- `evidencia/backend_test_report.json`
- `evidencia/eval_llm_pipeline_real.json` (validación del LLM sobre el pipeline real; reemplaza a `llm_guardrails_eval.json`, que medía `context.detect_intent`, código no integrado a la ruta de producción). Metodología completa en `validacion_llm/`.
- `evidencia/final_system_state.json`
- `evidencia/population_surveillance_report_v3.json`
- `evidencia/architecture.md`
- `evidencia/llm-rag.md`

## Imagenes sugeridas

- `imagenes/nb05_metricas_test_barras.png`
- `imagenes/nb05_precision_recall_curves.png`
- `imagenes/nb05b_label_policy_visual.png`
- `imagenes/nb06_activation_rates_comparison.png`
- `imagenes/shap_feature_importance.png`



---

## Estado 11/7/2026 (revisión sobre `.docx (4)`)

> Bloque nuevo del 11/7/2026. Todo lo de arriba es el plan original; esto es el estado verificado hoy.

**A CORREGIR:** el número inválido del guardrail **también está aquí**, en P1432 ("50 de 50 prompts adversariales rechazados y 20 de 20 legítimos"). Ese dato viene de `llm_guardrails_eval.json` (código huérfano `context.detect_intent`). Quitarlo de Cap. V o reemplazarlo por una frase remitiendo a los resultados reales del Cap. VI 6.4.
**Estado:** el resto del capítulo (5.1–5.8) está completo y describe construcción, correcto para Cap. V.
