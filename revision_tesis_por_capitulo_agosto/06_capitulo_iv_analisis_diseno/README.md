# 06 - Capítulo IV - Análisis y diseño (pasada de agosto)

La pasada de julio (`../../revision_tesis_por_capitulo/06_capitulo_iv_analisis_diseno/README.md`)
cerró este capítulo como **"completo, alineado con la arquitectura actual"**
el 11/7. Esta pasada verificó las 6 figuras de diseño (`image9`–`image14` del
`.md` exportado) contra el código y la infraestructura real. Veredicto:
**3 de 6 necesitan actualizarse**; ver detalle abajo. Imágenes extraídas del
documento y sus reemplazos ya generados están en `imagenes/`.

## Figuras revisadas

| # | Sección | Contenido | Veredicto |
| --- | --- | --- | --- |
| image9 | 4.1.2 Casos de uso | Propietario / Administrador técnico / Servicios IA | Vigente en general. El bloque "Administrador técnico" (panel técnico, métricas) sobre-representa lo que existe: no hay panel de validación LLM en `frontend_4`, solo el dashboard de calidad del modelo ML (`backend/app/modules/dashboard`). Aclarar el alcance real o marcar como "planeado". |
| image10 | 4.2.1 Diseño modular del backend | 12 dominios, Postgres, artefactos ML, ChromaDB, Ollama | **Vigente.** Coincide con los 12 módulos reales de `backend/app/modules/` y sus conexiones (confirmado por `backend/app/api/v1/api.py` y grep de cada router). Menciona `OpenRouter/Gemini` correctamente (existe `openrouter_extractor.py`). |
| image11 | 4.2.2 Flujo de análisis hematológico | "Extracción asistida: Gemma → Nemotron → Gemini → fallback local" | **DESACTUALIZADA.** El orden real en `backend/app/modules/gemini_extraction/service.py:31-66` (`build_default_attempts`) es **Gemini → Gemma (OpenRouter) → Nemotron (OpenRouter) → fallback local** — Gemini va primero, no tercero. También dice "Inferencia XGBoost v3" / "43 características"; el Capítulo VI describe una evolución v3→v4, así que la cifra de versión debe reconciliarse con el artefacto de modelo realmente desplegado antes de dar esto por bueno (no se pudo verificar `model_metadata_v2.json` en este repo — el artefacto de modelo no está versionado en git). |
| image12 | 4.2.3 Persistencia y modelo de datos | Entidades: users, pets, hematology, chat_conversations, rag_sources, surveillance_events | Estructuralmente vigente. Deriva menor: la tabla real se llama `chat_sessions` (`backend/app/modules/llm_chat/models.py:13`), no `chat_conversations` — a nivel de API sí se llama "conversation", pero el nombre físico de tabla difiere. Ajustar la etiqueta si el diagrama pretende mostrar nombres de tabla. |
| image13 | 4.2.4 Diseño del módulo LLM/RAG | Usuario → FastAPI → auth/sesión → orquestador → ChromaDB → Ollama → validador de salida | **INCOMPLETA.** No muestra las etapas que sí existen en `composition.py`/`send_chat_message.py`: `SafetyPolicy` (rechazo adversarial antes de tocar el modelo), `intent_classifier`/`chat_profile_policy`, `clinical_context_selector` (snapshot autorizado por `analysis_id`/historial), ni `nearby_veterinary_care`. Reemplazo ya generado y verificado (7 diagramas renderizados) en `docs/arquitectura_completa.md` sección 6 / `docs/diagramas/06_pipeline_llm_rag.png`. |
| image14 | 4.2.5 Diseño de despliegue | Un único host Docker Compose (Caddy, frontend, backend, rag_ingest, Ollama, ChromaDB, Postgres) | **DESACTUALIZADA respecto a lo verificado en vivo hoy.** No es "incorrecta" en el sentido de que sí hay un solo host activo — pero no menciona que ese host es una VM específica de GCP (`hemovet-prod`, `e2-standard-8`, CPU-only) ni que existe una segunda VM (`hemovet-llm-gpu`, con GPU) actualmente **apagada y desconectada** del despliegue automatizado. Ver `evidencia/verificacion_vms_2026-08-02.md` para la verificación SSH completa (incluye un hallazgo operativo real: 11h de `unhealthy` en el backend por descarga de Ollama en idle, ya resuelto). Reemplazo verificado: `imagenes/propuesta_4.2.5_despliegue_gcp_real.png`. |

## Qué hacer con esto

1. **image11**: corregir el orden de la cadena de extracción en el texto y el
   diagrama (Gemini primero). Verificar la versión real del modelo (v3 vs v4)
   contra el artefacto desplegado antes de tocar la cifra — no asumir.
2. **image13**: reemplazar por el diagrama de `docs/diagramas/06_pipeline_llm_rag.png`
   (ya renderizado, ya verificado contra `composition.py`) o redibujar con el
   mismo nivel de detalle (SafetyPolicy, intent classifier, context selector,
   RAG, prompt builder, validador de salida, persistencia).
3. **image14**: reemplazar por `docs/diagramas/01_deployment_gcp.png` o
   redibujar mostrando explícitamente las dos VMs de GCP y su estado real
   (una activa autosuficiente, una apagada y desconectada) — no presentar el
   caso GPU como si fuera un balanceo activo de carga.
4. **image9 / image12**: ajustes menores de redacción, no bloqueantes.
5. **image10**: sin cambios.

## Actualización 2026-08-02 (tarde): diagrama objetivo de las 2 VMs

Se agregó un segundo diagrama de despliegue, **`propuesta_4.2.5_despliegue_gcp_2vm_objetivo.png`**,
que muestra la arquitectura hacia la que se está migrando: `hemovet-llm-gpu`
como **fuente única del LLM** (Ollama corriendo ahí, `OLLAMA_BASE_URL` del
backend apuntando a su IP privada `10.128.0.3:11434`), separada de
`hemovet-prod` (que se queda con Caddy, frontend, backend, Postgres y
ChromaDB). **Esto todavía no está desplegado** — hoy `hemovet-llm-gpu` sigue
apagada y desconectada, como documenta `evidencia/verificacion_vms_2026-08-02.md` —
pero es el plan de migración en curso, así que se documenta como diagrama
objetivo, distinto del diagrama de estado verificado
(`propuesta_4.2.5_despliegue_gcp_real.png`). Ambos coexisten en
`docs/arquitectura_completa.md` sección 1/1.1 con esa distinción explícita.

También se agregaron a `imagenes/`, para referencia cruzada con otros
capítulos: `propuesta_4.2.1_modulos_backend.png` (corresponde a image10, sin
cambios de fondo pero útil como figura limpia), `propuesta_4.2.2_flujo_extraccion_orden_correcto.png`
(corrige el orden Gemini→Gemma→Nemotron→local que image11 tiene invertido) y
`propuesta_4.2.3_modelo_datos.png` (corresponde a image12).

## Evidencia incluida

- `evidencia/verificacion_vms_2026-08-02.md` — verificación SSH en vivo de
  ambas VMs (independencia real, hallazgo operativo del healthcheck).
- `imagenes/actual_4.2.2_flujo_analisis_DESACTUALIZADA.png` — extraída del
  `.md` original.
- `imagenes/actual_4.2.4_diseno_llm_rag_INCOMPLETA.png` — extraída del `.md`
  original.
- `imagenes/actual_4.2.5_diseno_despliegue_DESACTUALIZADA.png` — extraída del
  `.md` original.
- `imagenes/propuesta_4.2.1_modulos_backend.png`,
  `imagenes/propuesta_4.2.2_flujo_extraccion_orden_correcto.png`,
  `imagenes/propuesta_4.2.3_modelo_datos.png` — figuras limpias por sección.
- `imagenes/propuesta_4.2.4_pipeline_llm_rag_completo.png` — reemplazo
  verificado contra código.
- `imagenes/propuesta_4.2.5_despliegue_gcp_real.png` — estado verificado hoy
  (una VM autosuficiente, la GPU desconectada).
- `imagenes/propuesta_4.2.5_despliegue_gcp_2vm_objetivo.png` — arquitectura
  objetivo en migración (GPU como fuente única del LLM).
- Fuente completa con todos los diagramas y su justificación línea por línea:
  `../../docs/arquitectura_completa.md`.
