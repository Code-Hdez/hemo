# Inventario de evidencia — dónde vive cada cosa

Mapa de qué artefacto del repositorio respalda qué sección del informe. Sirve para dos cosas:
localizar rápido una fuente al redactar, y comprobar que ninguna afirmación del documento se
queda sin respaldo.

---

## 1 · Motor de aprendizaje automático

| Sección del informe | Evidencia |
| :--- | :--- |
| §3.3–§3.5, §5.1, §5.2, §6.1 | `outputs/` — `final_system_state.json`, `metrics_test_v3.json`, `cv_results_v3_*.csv`, `calibration_metrics_v3.csv`, `threshold_freeze_*.json`, `policy_freeze_v3.json`, `artifact_manifest_v3.json` |
| §6.1.2 intervalos *bootstrap* | `outputs/tabla_bootstrap_ci.csv`, `tabla_metricas_completas.csv` |
| §6.1.3 evolución v3 → v4 | `outputs/metrics_v3_v4_full.csv`, `comparacion_modelos.csv` |
| §6.1.4 explicabilidad | `outputs/shap_*`, figuras SHAP |
| Compuertas de calidad | `outputs/gate_*.json` (12 compuertas: paridad de características, fuga, integridad de manifiesto, congelamiento de política, deriva, cohorte, geocodificación, retención de metadatos, fuga por perro…) |
| Artefactos de modelo | `models/` — `best_model_v3.pkl`, `best_model_v4.pkl`, `calibrators_v3.pkl`, `model_metadata_v3.json` |

## 2 · Validación externa y clínica

| Sección | Evidencia |
| :--- | :--- |
| §6.2 Dog Aging Project | `outputs/nb06_validation_summary.json`, `activation_rates_comparison.csv`, `domain_shift_table.csv`, `domain_shift_distributions.png` |
| §6.3 validación clínica | `validacion_clinica/`, `outputs/resumen_validacion.json`, `resumen_metricas.csv`, `comparacion_larga.csv`, `manifest_s2..s4.csv` |
| §6.3.4 desacuerdos | `outputs/error_analysis_by_label.csv` |

## 3 · Usabilidad

| Sección | Evidencia |
| :--- | :--- |
| §3.8, §6.7 | `validacion_usabilidad/resultados/` — `usabilidad_por_item.csv`, `usabilidad_por_dimension.csv`; fuente: `Respuestas - Validación HemoVet.xlsx` (44 respuestas) |

## 4 · Asistente conversacional — validación de julio

| Sección | Evidencia |
| :--- | :--- |
| §6.4.1 seguridad y *guardrails* | `tools/llm_cbc_eval/results/` (banco de 770 preguntas, dos rondas) |
| §6.4.2 batería A · ámbito y seguridad | `validacion_llm/resultados/eval_ambito_seguridad.csv`, `eval_llm_pipeline_real.json` |
| §6.4.3 baterías B y C | `eval_robustez_ortografica.csv`, `eval_memoria_multiturno.csv` |
| §6.4.4 batería D · consistencia | `eval_consistencia.csv`, `resumen_consistencia.csv` |
| §6.4.5 batería E · rúbrica veterinaria | `evaluador_1.csv`, `evaluador_2.csv`, `rubrica_contenido_llm.csv`, `exactitud_contenido_crudo.csv`, `rubrica_veterinarios/` |
| Procedimiento de ejecución | `validacion_llm/COMO_CORRER_EN_VM.md`, `validacion_llm/scripts/`, `validacion_llm/casos/` |

## 5 · Asistente conversacional — rondas 4 a 6 (agosto)

| Sección propuesta | Evidencia |
| :--- | :--- |
| §5.10, §3.7.1 (batería F) | `validacion_llm/resultados/rondas45_2026-08-10/` — `bateria_ronda4.jsonl`, `bateria_ronda5_fresh.jsonl`, `bateria_ronda5_test5.jsonl`, `bateria_ronda6.jsonl`, `bateria_a100.jsonl`, `bateria_cierre.jsonl`, `sonda_final.jsonl` |
| Criterio operativo de «contenido real» | `validar_45.py`, `sonda.py` (mismo directorio) |
| Narrativa y mecanismos | `RESUMEN_PARA_EQUIPO_2026-08-11.md` |
| Verificación de citas | `backend/scripts/nli_support_verifier.py`, `cascade_support_verifier.py`, `evaluate_support_bench.py` |

> ⚠️ Estos ficheros contienen preguntas y respuestas completas. **Revisar privacidad antes de
> anexarlos** al documento entregable.

## 6 · Campaña de recaracterización (§3.11, §6.8, Anexo E)

| Contenido | Evidencia |
| :--- | :--- |
| Figuras | `06_analisis/figuras/` — 36 figuras + 9 paneles de ausencia, en PDF, SVG y PNG, con `MANIFIESTO.json` |
| Versiones en escala de grises | `06_analisis/grises/` |
| Tablas | `06_analisis/tablas/` — 37 CSV + `INDICE_TABLAS.csv` |
| Procedencia de fuentes | `06_analisis/PROCEDENCIA.json` |
| Trazabilidad figura → fuente | `06_analisis/TRAZABILIDAD.csv` |
| Pies de figura con notas de lectura | `06_analisis/PIES_DE_FIGURA.md` |
| Registro de verificación | `06_analisis/VERIFICACION_NOTEBOOK.txt` |
| Sello del sistema y canario | `06_analisis/fase2_canario_y_ic.json` |
| Ablación de gramática | `06_analisis/E-A_ablacion_gramatica.md` |
| Cuaderno de análisis | `06_analisis/HEMOVET_RECARACTERIZACION_A100_FIGURAS.ipynb` |
| Motor de figuras | `06_analisis/motor_figuras.py`, `construir_figuras.py`, `ensamblar_notebook.py` |

**Selección ya copiada y lista para el informe:**
`_entrega_final/08_capitulo_vi_resultados/6.9_recaracterizacion_a100/`

> ⚠️ **Los datos crudos de la campaña no están en este repositorio.** Las rutas que las tablas
> declaran como procedencia (`01_auditoria_previa/`, `02_fixtures/`, `03_hipotesis/`,
> `04_trazas/`, `05_derivados/`, `07_informes/`, `99_operacion/`) viven fuera del árbol
> versionado. **Lo que sí está aquí y es suficiente para el informe** son las tablas derivadas, las
> figuras y los ficheros de procedencia con los compendios SHA-256 que permiten verificar la
> cadena. Si el Anexo E va a incluir datos crudos, hay que localizarlos y traerlos antes de la
> entrega — y si no se localizan, **declararlo**, que es exactamente el criterio que la propia
> campaña aplica.

## 7 · Ingeniería del sistema

| Sección | Evidencia |
| :--- | :--- |
| §4.2.1, §5.3 backend | `backend/app/modules/` (12 módulos, 40 rutas), `backend/alembic/versions/` (15 migraciones) |
| §5.4 frontend | `frontend_4/` (95 ficheros versionados) |
| §5.5 corpus RAG | `knowledge_base/` (1 252 documentos: `raw_md`, `microcards`, `policies`, `expert_review`, `manifests`) |
| §5.7 pruebas | `backend/tests/` (35 archivos) |
| §5.9 cadena de release | `deploy/releases/` — `release-manifest-*.json`, `gpu-runtime-*.json`, `artifact-set-*.json`, `rag-summary-*.json` |
| §4.2.5, §5.9 arranque del nodo GPU | `deploy/gpu/` — `validate-host.sh`, `validate-runtime.sh`, `shutdown-on-failure.sh`, `hemovet-gpu-failure-shutdown.service`, `rollback-release.sh`, `reconcile-release.sh`, `switch-to-a100.sh`, `gpu-runtime-release-v1.schema.json`, `runtime_contract.py` |
| §5.7 despliegue | `docker-compose.{yml,local,local-caddy,qa,gpu,prod}.yml`, `deploy/Caddyfile`, `deploy/ci/build-and-publish-images.sh` |
| Arquitectura documentada | `docs/arquitectura_completa.md`, `docs/llm_architecture.md`, `docs/llm-ollama-acceptance.md`, `docs/diagramas/` |

## 8 · Historia del proyecto

| Contenido | Fuente |
| :--- | :--- |
| Migración a A100 y rondas 4-6 | commits `663094b` … `f9deedb` |
| Consolidación del frontend | commit `d3c06fa` |
| Revisión anterior por capítulos (eliminada del árbol) | `git show HEAD:revision_tesis_por_capitulo/` |

---

## Huecos conocidos de evidencia

| Hueco | Impacto | Acción |
| :--- | :---: | :--- |
| Datos crudos de la campaña fuera del repositorio | Medio | Localizar antes del Anexo E, o declarar su ubicación |
| `pytest` sin ejecutar recientemente | **Alto** | Ejecutar y registrar la salida con fecha |
| Facturación real de cómputo en nube | **Alto** | Obtener para §2.5; no estimarla |
| Manual de usuario | **Alto** | No existe; hay que producirlo |
| Reporte de vigilancia con fecha de abril | Bajo | Regenerar si se quiere una cohorte actual |
| Agradecimientos y dedicatorias | **Alto** | No existen; hay que redactarlos |
