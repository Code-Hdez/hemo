# Endurecimiento para producción del chat LLM de HemoVet

Fecha de cierre técnico local: 2026-07-20.

> **Snapshot histórico.** Este informe describe el endurecimiento realizado
> hasta la fecha indicada arriba. Desde entonces, las etapas 1-9 de
> estabilización del chat LLM (`informe_etapa_1.md` a `informe_etapa_9.md`)
> modificaron sustancialmente lo descrito aquí: eliminaron los adaptadores
> heredados citados en la sección 1 (ya no están presentes en el árbol, no
> solo "sin usar"), reemplazaron el vocabulario SSE de las secciones 3 y 9 por
> `start`/`context_ready`/`retrieval_completed`/`generation_started`/`final`/
> `done`/`error`/`heartbeat`, y sustituyeron el modelo productivo de la
> sección 7 por el perfil cualificado Qwen3.6 27B de 64K descrito en
> `.env.production.example`. Para el estado vigente del runtime, el contrato
> SSE y el perfil de modelo, consultar `llm-rag.md`. Este documento se
> conserva como registro histórico de la auditoría original y de sus
> resultados de prueba en ese momento; no describe el estado actual.

Este informe distingue tres niveles de evidencia:

- **Implementado y probado**: comportamiento cubierto por pruebas automatizadas o
  por una inspección reproducible del runtime local.
- **Configurado, no medido en la VM objetivo**: valores conservadores listos para
  desplegar, pero que todavía requieren benchmark en GCP.
- **Pendiente externo**: necesita la VM NVIDIA, credenciales de prueba,
  infraestructura de telemetría o revisión veterinaria. No se atribuye una mejora
  clínica o de latencia sin esos datos.

## 1. Estado inicial encontrado

### Flujo productivo real

El frontend utiliza `POST /api/v1/chat` y `POST /api/v1/chat/stream`, además de
los endpoints de creación, historial, turnos y borrado de conversaciones. El
flujo productivo está compuesto por `app/application.py` y
`app/modules/llm_chat/composition.py`; no utilizaba como ruta principal los
adaptadores heredados `service.py` o `local_model.py`. Esos adaptadores y sus
dependencias (`context.py`, `knowledge_base.py`, `kb_ingest.py`) confirmaron
en la etapa 9 no tener ningún consumidor en producción y fueron eliminados
del árbol; ya no existen como código muerto, no solo como ruta inactiva.

```text
AssistantPage / api.ts
  -> app/modules/llm_chat/api/router.py
  -> SendChatMessageUseCase
  -> SafetyPolicy + IntentClassifier + ConversationRouter
  -> repositorio de conversación y contexto clínico autorizado
  -> hechos clínicos y memoria estructurada
  -> recuperación densa Chroma + BM25 + RRF
  -> PromptBuilder
  -> cliente HTTP asíncrono de Ollama/OpenAI compatible
  -> saneamiento + validación factual, contractual y de seguridad
  -> persistencia del candidato aprobado
  -> respuesta HTTP o SSE
```

### Componentes que ya existían

- FastAPI modular, repositorios SQLAlchemy y persistencia de conversaciones.
- Memoria acotada, contexto seleccionado e histórico y hechos clínicos
  estructurados.
- Recuperación híbrida Chroma/BM25 con RRF.
- Clasificación por reglas, perfiles de chat, guardrails, validación posterior y
  reparación.
- Cliente compatible con Ollama y streaming SSE.
- Ingesta Markdown, catálogo de fuentes y pruebas de regresión clínica.

Por ello no se creó un segundo módulo de chat ni un segundo RAG. Se fortalecieron
las fronteras existentes.

### Problemas confirmados

1. El SSE podía publicar prefijos del modelo antes de conocer el resultado de las
   validaciones de intención, hechos y evidencia.
2. La selección de candidatos podía conservar una respuesta reparable cuando la
   reparación no alcanzaba un contrato obligatorio.
3. No todas las rutas funcionales tenían un contrato explícito y el fallback de
   clasificación podía conducir una entrada ambigua al RAG general.
4. La atribución por marcador de fuente no demostraba soporte por afirmación.
5. La sesión persistente no constituía por sí sola una frontera de navegador y
   podía reanudarse fuera de la sesión efímera prevista.
6. Había operaciones síncronas de embeddings, BM25, Chroma y SQLAlchemy accesibles
   desde rutas asíncronas.
7. El ID del chunk no incorporaba toda la configuración incompatible del embedding
   y la ingesta productiva no tenía una promoción atómica completa.
8. Los errores del proveedor no distinguían conexión, lectura, sobrecarga,
   contrato, evidencia, sesión y cancelación.
9. La telemetría carecía de una frontera uniforme de anonimización y parte de los
   metadatos internos podía llegar a la respuesta pública.
10. Docker no verificaba de forma fail-closed el digest y la cuantización exactos
    del modelo; el perfil GPU tampoco expresaba toda la línea base que debía
    medirse.

### Suposiciones previas que no aplicaban

- El RAG híbrido, el motor de hechos y la memoria ya existían; reemplazarlos habría
  duplicado responsabilidades.
- No era necesario migrar de FastAPI, Chroma u Ollama.
- No había evidencia local para promover un reranker pesado, otro embedding o un
  modelo generador mayor.
- `size_vram > 0` no se tomó como prueba suficiente. La clasificación solo es
  `full_gpu` cuando `size_vram / size >= 0.98`.

## 2. Cambios implementados

| Problema y causa raíz | Archivos principales | Solución | Riesgo y mitigación | Prueba asociada |
|---|---|---|---|---|
| Tokens irreversibles antes de validar la respuesta completa | `streaming_response.py`, `send_chat_message.py`, `api/router.py` | El proveedor se consume en buffer. SSE emite `accepted`, `classifying`, `retrieving`, `generating`, `validating` y, si aplica, `repairing`; solo después publica el `delta` aprobado y `done`. Desconexión cancela y marca el turno. | Aumenta el tiempo hasta contenido visible; se mantienen eventos de estado y heartbeat. | `test_real_streaming.py`, `test_chat_api.py`, `test_send_chat_message.py` |
| Entrega del candidato “menos malo” | `response_contracts.py`, `send_chat_message.py` | Jerarquía tipada `VALID`, `COSMETIC_WARNING`, `REPAIR_REQUIRED`, `MANDATORY_CONTRACT_FAILURE`, `CLINICAL_SAFETY_FAILURE`, `EVIDENCE_FAILURE`, `FACT_CONTRADICTION`, `TECHNICAL_FAILURE`. Solo los dos primeros son entregables. Una generación inicial y una reparación como máximo. | Una respuesta inválida ahora termina en error reintentable; evita exposición clínica insegura. | `test_response_contracts.py`, `test_structured_send_chat_message.py`, regresiones de reparación |
| Router incompleto o fallback implícito a RAG | `intent_classifier.py`, `conversation_routing.py`, `safety_policy.py`, `response_contracts.py` | Decisión tipada con intención primaria, secundarias, confianza, ruta, servicios permitidos y fallback seguro. Se añadieron contratos para todas las familias solicitadas, incluida ambigüedad y evidencia insuficiente. | Las formulaciones nuevas pueden abstenerse con mayor frecuencia; las paráfrasis están cubiertas por pruebas semánticas. | `test_intent_routing_regressions.py`, `test_safety_policy.py`, `test_response_contracts.py` |
| Confusión entre educación y recomendación clínica | `safety_policy.py`, `intent_classifier.py`, `output_validator.py` | Taxonomía separa concepto educativo, riesgo general y explicación de resultado de dosis, frecuencia, duración, selección de tratamiento y diagnóstico confirmado. | Falsos bloqueos; se agregaron casos permitidos con hierro, transfusión y riesgo de medicamentos humanos. | `test_safety_policy.py`, `test_send_chat_message.py` |
| Evidencia declarada, pero no demostrada por afirmación | `structured_response.py`, `response_contracts.py`, `send_chat_message.py` | Salida interna `hemovet-response-v2` con claims tipados, `fact_ids`, `source_ids`, `policy_rule_ids` y spans que deben existir literalmente en el chunk retenido. Pydantic prohíbe campos adicionales. | Mayor exigencia de cumplimiento JSON; una única reparación limitada y error técnico si vuelve a fallar. | `test_structured_response.py`, `test_structured_send_chat_message.py`, `test_clinical_snapshot_and_claims.py` |
| Números, unidades, estados o fuentes no autorizados | `clinical_facts.py`, `clinical_response.py`, `output_validator.py`, `domain/clinical.py` | Hechos con ID estable y procedencia; validación determinista de número, unidad, estado, analito, fecha, paciente, análisis, tendencia y fuente. Estados incompletos usan `unknown`, `insufficient_data` o `not_applicable`, no booleanos engañosos. | Conversión conservadora puede impedir comparaciones dudosas; se abstiene en vez de adivinar. | `test_clinical_snapshot_and_claims.py`, pruebas factuales en `test_send_chat_message.py` |
| Tendencias calculadas o mezcladas por el LLM | `domain/clinical.py`, repositorios y selector de contexto | Comparación histórica determinista con control de paciente, fecha, unidad, laboratorio, analizador e intervalo. Solo se materializan tendencias comparables. | Menor cobertura cuando faltan metadatos, pero sin tendencias inventadas. | pruebas históricas, de unidades y de aislamiento |
| Reanudación fuera de la sesión del navegador | migración `0012_chat_browser_session.py`, repositorios, `api/router.py`, `chatSession.ts`, `api.ts`, `AssistantPage.tsx` | UUID efímero en `sessionStorage`; el backend almacena solo HMAC/hash y enlaza `session_id + mode + pet_id + analysis_id`. TTL de una hora, limpieza y restauración autorizada dentro de la misma sesión. | Clientes antiguos no envían el header; la exigencia es configurable y se activa en producción. | `test_session_memory_integration.py`, `test_repositories.py`, pruebas frontend de sesión y restauración |
| Retry duplicaba o dejaba la vista inutilizable | caso de uso, repositorio de turnos, API SSE y `AssistantPage.tsx` | Lease/idempotencia por turno, estados terminales tipados, preservación de `client_message_id`, reintento del mismo turno y recuperación tras `pagehide` sin recargar. | Cambia la máquina de estados visible; se conserva compatibilidad de eventos `delta`, `done` y `error`. | pruebas SSE de error/cancelación/reintento y `AssistantPage.test.tsx` |
| Embeddings incompatibles y actualización no atómica | `domain/rag_index.py`, `ingest_markdown.py`, `ingest_rag.py`, Chroma/BM25 | Fingerprint completo, nombre de colección versionado, `--stage`, `--validate-only`, promoción por variable y rollback. Se prohíbe `--reset` sobre la colección activa. BM25 intercambia snapshots de forma atómica tras ingesta. | Requiere operación explícita de promoción; documentada y validada en deploy. | `test_rag_index_hardening.py`, `test_markdown_ingestion.py`, `test_vector_adapters.py` |
| Trabajo bloqueante en el event loop | `blocking_work.py`, `fastembed_client.py`, `bm25_store.py`, `chroma_store.py`, repositorios SQLAlchemy | Executors acotados, semáforos y `asyncio.to_thread` para operaciones sin cliente asíncrono nativo. | Más hilos y colas; límites configurables `RAG_BLOCKING_MAX_CONCURRENCY=2` y `CHAT_DB_BLOCKING_MAX_CONCURRENCY=4`. | pruebas de adaptadores, repositorios y benchmarks operativos |
| Reranker añadido sin evidencia | `rerankers.py`, `retrieval_service.py`, `retrieval_evaluation.py` | Puerto extensible y línea base explícita `NoopReranker(model_name="none")`. La puerta de promoción exige no degradar Recall@5 y mejorar MRR/nDCG con latencia registrada. | No mejora aún el ranking; evita añadir RAM/VRAM y latencia sin benchmark real. | pruebas de recuperación y promoción |
| Cliente Ollama frágil | `openai_compatible_client.py`, configuración y composición | `httpx.AsyncClient` reutilizable, pool, timeouts por fase, cancelación y un único retry de conexión con backoff/jitter. Nunca reintenta una lectura o validación. Errores tipados. | Un fallo posterior al inicio no se reintenta automáticamente; conserva idempotencia y permite retry explícito. | `test_openai_compatible_client.py`, pruebas de timeout y error SSE |
| Modelo distinto al autorizado | warmup/health en `application.py`, configuración, `inspect_llm_runtime.py` | Producción exige etiqueta, digest y cuantización exactos y falla readiness ante divergencia. El inspector no imprime prompt, plantilla ni Modelfile. | Un cambio deliberado de modelo exige actualizar entorno y evaluación. | `test_health.py`, `test_llm_settings.py`, `test_deploy_env.py` |
| Falta de trazabilidad segura | `infrastructure/observability.py`, `application.py`, caso de uso, router | OpenTelemetry OTLP/HTTP durante lifespan, resultados terminales, métricas por etapa, IDs con HMAC y allowlists. Los logs heredados eliminan texto clínico y hashean IDs. La API pública elimina IDs internos de hechos, claims y chunks. | Cardinalidad/volumen del collector; sampler configurable y ningún fallo de telemetría altera la respuesta. | `test_observability.py`, `test_observability_lifecycle.py`, `test_chat_api.py` |
| Contenedores y despliegue demasiado permisivos | `backend/Dockerfile`, Compose, workflow, `validate_deploy_env.py` | Python 3.11 fijado por digest, usuario UID 10001, capabilities eliminadas, servicios internos sin puertos públicos en producción, GPU explícita, colección validada antes del rollout y secretos fuera del repositorio. | Volúmenes antiguos pueden pertenecer a root; job limitado de corrección de permisos. | contrato de entorno, cinco variantes `docker compose config`, build y `pip check` |
| Acoplamiento futuro al clasificador ML | `domain/verified_context.py`, puertos de contexto | Interfaces `VerifiedContextProvider`, `ClinicalFactsProvider`, `HistoricalTrendProvider`, `MLPredictionContextProvider` y `DocumentEvidenceProvider`; la predicción conserva versión, probabilidad y limitaciones. | La integración visual y un proveedor ML real siguen fuera del alcance de este cambio. | `test_verified_context.py` |

Todo texto conversacional visible continúa originándose en el LLM. Las únicas
respuestas fijas son errores técnicos HTTP/SSE tipados; si generación y reparación
fallan, no se sustituye la respuesta por un texto clínico prefabricado.

## 3. Arquitectura final

```text
Usuario / navegador
  -> UUID efímero en sessionStorage
  -> FastAPI: autenticación, tamaño, sesión y contexto
  -> SafetyPolicy + clasificador jerárquico + router obligatorio
  -> contrato funcional tipado
  -> contexto verificado
       -> hechos clínicos estructurados del análisis seleccionado
       -> tendencias deterministas del paciente correcto
       -> puerto versionado para predicción ML futura
  -> RAG cuando el contrato lo permite
       -> consulta contextualizada
       -> Chroma denso + BM25 (fuera del event loop)
       -> Reciprocal Rank Fusion
       -> filtros de especie, autoridad, revisión y procedencia
       -> Reranker Noop de línea base / puerta de promoción medible
       -> puerta de evidencia o abstención
  -> prompt separado en políticas, hechos, evidencia, memoria y consulta
  -> Ollama asíncrono reutilizable
  -> buffer completo de generación
  -> JSON hemovet-response-v2
  -> validación de contrato, claims, hechos, números, unidades, fuentes y seguridad
       -> VALID/COSMETIC_WARNING: persistir y publicar
       -> REPAIR_REQUIRED: una reparación y nueva validación
       -> fallo obligatorio: error técnico tipado, sin contenido clínico
  -> SSE: estados -> primer delta aprobado -> done
```

El vocabulario SSE anterior (`accepted`/`classifying`/`retrieving`/`generating`/
`validating`/`repairing`/`delta`/`done`) fue reemplazado en la etapa 8 por
`start`/`context_ready`/`retrieval_completed`/`generation_started`/`final`/
`done`/`error`/`heartbeat`, sin `delta` de token: `final` y `done` transmiten
el mismo `ChatResponse` ya validado y persistido. Ver `llm-rag.md` para el
contrato vigente.

La clave efectiva de conversación incorpora la sesión efímera, modo, mascota y
análisis. Chroma contiene conocimiento documental; los valores particulares del
animal siempre provienen del repositorio clínico autorizado.

## 4. Pruebas

### Comandos y resultados finales

| Comando | Resultado |
|---|---:|
| `docker run ... python -m pytest tests/llm_chat -q` en Python 3.11.15, con el corpus montado como en Compose | **544 passed, 1 skipped** |
| `PYTHONPATH=backend .venv/bin/python -m pytest backend/tests --ignore=backend/tests/llm_chat -q` | **264 passed, 4 subtests passed** |
| `pytest backend/tests/test_migrations.py -q` | **6 passed** (incluidas en las 264) |
| `pytest tools/llm_cbc_eval/tests -q` | **23 passed** |
| `ruff check backend/app backend/scripts backend/tests` | **passed** |
| `git diff --check` | **passed** |
| `npm run check` | **passed** |
| `npm test -- --run` | **13 archivos, 100 tests passed** |
| `npm run build` | **passed**; solo advertencia de chunks grandes de Vite |
| Compose base, producción, GPU, producción+GPU y QA con `config --quiet` | **5/5 passed** |
| Build backend liviano Python 3.11 fijado + `pip check` | **passed; no broken requirements** |

La línea base registrada antes de los cambios era **634 passed, 1 skipped y 4
subtests**. El incremento de conteo corresponde a nuevas pruebas; no se eliminaron
casos útiles para hacer pasar la suite.

### Casos nuevos relevantes

- Saludo, identidad, capacidades, social, programación y fuera de ámbito no
  invocan RAG clínico accidentalmente.
- Dosis, frecuencia, duración, tratamiento y diagnóstico confirmado nunca son
  entregables.
- Números, unidades, estados, fechas, analitos, fuentes o pacientes inventados
  bloquean el candidato completo antes del primer `delta`.
- Una reparación insegura no se entrega y no existe una tercera generación.
- `done` público no expone IDs internos de claims, facts o chunks.
- Desconexión, timeout y cancelación liberan el lease y terminan en estado
  recuperable.
- Retry conserva identidad de turno y no mezcla streams.
- Sesiones, modos, mascotas y análisis quedan aislados.
- Migración desde esquemas legados con o sin columna `status` conserva datos.
- BM25 refleja la ingesta sin reiniciar el backend.
- Cambios de embedding, pooling, dimensión, prefijos, chunking, metadatos o
  contenido producen un fingerprint incompatible.

### Ejecuciones fallidas observadas, no ocultas

1. Pytest desde la raíz sin `PYTHONPATH=backend` produjo tres errores de importación;
   la invocación corregida pasó 176 pruebas focalizadas.
2. La imagen ejecutada sola, sin el volumen `knowledge_base`, falló dos pruebas del
   catálogo. Compose monta deliberadamente `./knowledge_base:/app/knowledge_base:ro`;
   con esa topología la suite LLM pasó completa.
3. Una ruta de intérprete no normalizada `backend/../.venv` hizo que cinco
   subprocesos Alembic no localizaran `alembic.ini`. Desde la raíz, como en CI,
   las seis pruebas de migración pasaron.
4. El primer dry-run local usó `HEMOVET_PROJECT_ROOT=/app` heredado del `.env` de
   Docker y encontró un corpus vacío. Al declarar el root real del host produjo el
   fingerprint esperado.
5. `nvidia-smi` del host local no puede comunicarse con el driver. Esto no invalida
   lo que Ollama reporta dentro de Docker, pero impide afirmar utilización física,
   temperatura o VRAM total de la VM objetivo.

## 5. Evaluación

| Dimensión | Evidencia actual | Resultado local |
|---|---|---|
| Intención | contratos y paráfrasis en pruebas | Todas las rutas obligatorias tienen contrato; saludos e identidad mantienen intención |
| Exactitud factual | hechos estructurados y validadores de número/unidad/estado | 0 candidatos con violación factual entregados en el corpus de regresión automatizado |
| Seguridad | casos de dosis, medicación, tratamiento, diagnóstico, urgencia, maltrato e injection | 100 % de los casos críticos automatizados aprobados |
| Evidencia | claims v2, IDs autorizados y spans presentes en chunks | fuentes inexistentes o claims clínicos sin soporte bloqueados |
| Memoria | integración repositorio/API/frontend | sin fugas detectadas entre sesión, modo, paciente o análisis en pruebas |
| Histórico | comparación determinista | cambios no comparables producen abstención o datos insuficientes |
| Streaming | contrato de orden SSE | ningún `delta` antes de la validación; todo stream probado termina en `done`, `error` o cancelación |
| Abstención | contrato `INSUFFICIENT_EVIDENCE` | el sistema no sustituye evidencia ausente por conocimiento paramétrico silencioso |

Dry-run reproducible del corpus aprobado:

```text
sources:             1250
chunks:              4696
quarantined:         0
schema:              markdown-v5
corpus_revision:     20bb18ffff6684dba53b9f09f38c37d578268fe6377cdb6c4ab70304e75e6736
content_version:     2b653343dd66ccac1255999d2973beddd5bc2a8a30fb360ee5487b3ac5e723b2
index_fingerprint:   418d1c49000cbbbbd8847494895d85eaf53f95c995ea7e2d995f77a06b7698f9
```

Recall, MRR, nDCG y calidad clínica sobre un dataset veterinario etiquetado real
siguen como **N/D**. La implementación incluye el evaluador y la puerta de
promoción, pero no fabrica resultados sin juicios de relevancia y revisión
veterinaria.

## 6. Rendimiento

| Métrica | Antes | Después | Diferencia demostrable | Configuración |
|---|---:|---:|---|---|
| TTFT del proveedor p50/p95/p99 | N/D | N/D | No medido | Requiere benchmark autenticado en GCP |
| Tiempo hasta primera respuesta válida | Prefijos podían publicarse antes de validación | Ningún contenido hasta aprobar la respuesta completa | Garantía de seguridad estructural, no una mejora en ms | SSE con buffer completo |
| Latencia total p50/p95/p99 | N/D | N/D | No se atribuye mejora | Script preparado para 50–100 solicitudes |
| Tokens/s de prompt y generación | N/D | N/D | No medido | Ollama expone contadores que la traza ya captura |
| Dry-run de corpus | N/D | 1.56 s observado | Sin línea base comparable | host local, 1250 fuentes/4696 chunks |
| Reranking | no explícito | `NoopReranker` | 0 latencia adicional deliberada | pendiente benchmark multilingüe |
| VRAM cargada reportada por Ollama | N/D | 2,895,118,335 bytes | no comparable | Qwen3 4B Q4_K_M, contexto 4096 |
| Relación `size_vram / size` | N/D | 1.0 (`full_gpu`) | carga completa según Ollama | runtime Docker local |
| Utilización GPU y VRAM total del host | N/D | N/D | host sin driver consultable | medir en VM GCP con DCGM/`nvidia-smi` |
| Tasa real de reparación, error y abstención | N/D | N/D | instrumentada, sin tráfico representativo | OTLP pendiente de despliegue |

La suite verifica el orden seguro y la cancelación, pero no se presenta su tiempo
de ejecución como benchmark de inferencia. Flash Attention, KV q8, contexto y
paralelismo quedan como configuración experimental conservadora hasta medirlos en
la VM de 24 GB.

## 7. Modelos comparados

> Configuración productiva en la fecha de este informe (2026-07-20):
> `.env.production` seleccionaba la línea base calificada
> `qwen3:4b-instruct-2507-q4_K_M`, digest
> `0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`.
> **Esta ya no es la configuración vigente.** El perfil cualificado actual es
> Qwen3.6 27B Q4_K_M con ventana de 64K, definido en
> `.env.production.example` (`OLLAMA_MODEL=qwen3.6:27b-q4_K_M`,
> `OLLAMA_CONTEXT_LENGTH=65536`); ver `llm-rag.md`. El digest y el
> `tokenizer.json` reales de ese perfil deben completarse en el entorno antes
> de operar el modelo — no se afirma aquí que estén instalados. Los modelos
> candidatos no se promueven sin superar primero el benchmark autenticado y la
> validación clínica correspondiente.

### Runtime realmente verificado

| Campo | Valor observado |
|---|---|
| Ollama | `0.30.10` |
| Etiqueta | `qwen3:4b-instruct-2507-q4_K_M` |
| Digest | `0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0` |
| Familia/formato | `qwen3` / `gguf` |
| Parámetros | `4.0B` (`4,022,468,096` en metadatos) |
| Cuantización | `Q4_K_M` |
| Tamaño instalado | `2,497,293,803` bytes |
| Tamaño cargado | `2,895,118,335` bytes |
| `size_vram` | `2,895,118,335` bytes |
| Dispositivo inferido | `full_gpu`, ratio `1.0` |
| Contexto efectivo cargado | `4096` |
| Capacidad declarada del artefacto | `262144`; no se usa como contexto productivo |

No se descargaron ni promovieron Qwen3.5 9B/27B, Qwen3 14B/30B-A3B,
Qwen3-Embedding, BGE-M3 o un reranker externo. Hacerlo sin el mismo dataset,
contexto, cuantización, calentamiento y 50–100 solicitudes por escenario no habría
producido una comparación válida.

Recomendación actual: conservar Qwen3 4B Q4_K_M como línea base; comparar primero
una variante intermedia que deje margen de KV cache. Ningún candidato debe
promoverse hasta superar seguridad y exactitud, además de reportar p50/p95/p99,
throughput, VRAM y errores. El embedding continúa siendo
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` y el reranker
continúa en `none` por falta de evidencia de mejora local.

## 8. Cambios de configuración

| Variable/configuración | Antes | Nuevo valor productivo | Justificación / riesgo |
|---|---|---|---|
| Imagen backend | `python:3.11-slim` mutable | digest `sha256:c20888…2900` (Python 3.11.15) | build reproducible; actualizar digest de forma controlada |
| Usuario backend | root | UID/GID 10001 | menor privilegio; job acotado migra permisos de volúmenes |
| `OLLAMA_EXPECTED_MODEL_DIGEST` | no existía | digest exacto observado | readiness fail-closed ante modelo incorrecto |
| `OLLAMA_EXPECTED_QUANTIZATION` | no existía | `Q4_K_M` | evita confiar solo en la etiqueta |
| `OLLAMA_MAX_RETRIES` | `0` | `1`, solo conexión | resiliencia sin duplicar una generación iniciada |
| Pool HTTP | implícito | 8 conexiones, 4 keep-alive, expiry 30 s | cliente reutilizable; pendiente carga real |
| `OLLAMA_CONTEXT_LENGTH` | 4096 | 4096 | no se aumenta sin medir |
| `OLLAMA_NUM_PARALLEL` | 1 | 1 | línea base segura; comparar 2 en GCP |
| GPU Flash Attention | 0 | 1 en perfil GPU | candidato de benchmark, no mejora atribuida todavía |
| GPU KV cache | `f16` | `q8_0` en perfil GPU | libera VRAM; validar calidad/latencia en VM |
| GPU queue | 16 | 32 | absorbe ráfagas; la API conserva timeout y semáforo |
| `RAG_COLLECTION_NAME` | colección base mutable | colección con sufijo fingerprint | promoción/rollback atómicos |
| Fingerprint embedding | parcial | proveedor, modelo/revisión, librería/versión, pooling, dimensión, normalización, métrica, prefijos, chunking, overlap, schema y contenido | nunca mezcla vectores incompatibles |
| `CHAT_STRUCTURED_OUTPUT_ENABLED` | no existía | 1 | claims verificables |
| `CHAT_REQUIRE_BROWSER_SESSION_ID` | no existía | 1 en producción | impide reanudar desde otra sesión del navegador |
| `CHAT_SESSION_TTL_SECONDS` | 3600 | 3600 | sesión breve; no se restaura durante días |
| Concurrencia bloqueante | no explícita | RAG 2, DB 4 | protege event loop y conexiones |
| OpenTelemetry | no integrado | OTLP/HTTP + HMAC obligatorio en producción | collector privado y retención aún deben desplegarse |

## 9. Compatibilidad

### API y SSE

- Los cuerpos principales de `POST /chat` y `/chat/stream` se conservan.
- Se añade `X-HemoVet-Browser-Session-ID`. Es opcional en desarrollo para no
  romper clientes heredados y obligatorio en producción.
- `delta`, `done` y `error` eran el vocabulario SSE vigente en la fecha de
  este informe; `delta` fue retirado en la etapa 8 en favor de `final`/`done`
  con el `ChatResponse` completo ya persistido (ver nota de la sección 3).
- Las fuentes públicas conservan títulos legibles y ya no exponen path, score,
  texto crudo o ID interno.
- `route_trace` público mantiene métricas operativas allowlisted, no IDs clínicos
  internos.

### Frontend mínimo

- `sessionStorage` sustituye cualquier identificador conversacional de larga
  vida; cerrar el navegador genera otra frontera.
- Reload/BFCache en la misma sesión restaura el transcript desde el backend
  autorizado.
- Error, cancelación o `pagehide` dejan disponible el mismo retry y no requieren
  recargar la página.
- No hubo rediseño visual.

### Migración y rollback

- Alembic `0012_chat_browser_session` añade una columna nullable y dos índices;
  acepta esquemas legados sin `status`. Las seis pruebas de migración pasan.
- Rollback de código puede desactivar temporalmente
  `CHAT_REQUIRE_BROWSER_SESSION_ID`; el downgrade elimina índices y columna.
- Rollback de RAG restaura juntos el SHA anterior, la colección fingerprinted y
  su configuración. Las colecciones anteriores no se borran durante despliegue.
- El workflow valida la candidata antes de reemplazar servicios y no resetea la
  colección activa.

## 10. Problemas pendientes

| Prioridad | Pendiente y evidencia | Impacto | Próximo paso concreto | Dependencia externa |
|---|---|---|---|---|
| P0 | Validación clínica con veterinario y dataset de aceptación real | Las pruebas demuestran contratos, no idoneidad clínica completa | revisar y congelar casos normales, anormales, históricos, urgencias y abstención; exigir 100 % en críticos | especialista veterinario y datos anonimizados |
| P0 | E2E autenticado contra Ollama, Chroma y PostgreSQL de staging | No hay métrica real de respuesta completa ni evidencia sobre datos de staging | ejecutar `benchmark_chat_sse.py` con IDs autorizados y 50–100 solicitudes por escenario | token e IDs de prueba |
| P0 | GPU de la VM GCP | El host local devuelve fallo de driver; `full_gpu` solo fue confirmado por Ollama dentro de Docker | ejecutar inspector, `nvidia-smi`, `/api/ps`, DCGM y carga concurrente en la VM | acceso a GCP/NVIDIA Toolkit |
| P1 | Recall@k, MRR, nDCG y precisión/recall de contexto | No puede seleccionarse chunking, embedding o reranker por calidad real | etiquetar consultas reales y ejecutar la puerta de promoción | juicios de relevancia veterinarios |
| P1 | Benchmark de embeddings y rerankers multilingües | MiniLM/Noop siguen como baseline | comparar Qwen3-Embedding 0.6B, BGE-M3 y 2–3 rerankers con misma colección staged | descarga de modelos, CPU/GPU y dataset |
| P1 | Comparación de generadores | No se cumple aún el criterio de que un candidato supere la línea base | probar 4B, variante intermedia y candidato de calidad con mismo prompt/seed/contexto | VRAM de VM y artefactos disponibles |
| P1 | Concurrencias 1, 2, 4 y 8 | Configuración conserva `parallel=1`; p95/p99 y equidad son N/D | ejecutar benchmark con warmup, colas, cancelación y OOM; promover 2 solo con evidencia | VM de 24 GB |
| P1 | Collector OTLP y métricas GPU | Código y variables existen, pero no hay series históricas | desplegar collector privado, retención, dashboards y alertas; integrar DCGM | infraestructura de observabilidad |
| P2 | `nvidia-smi` del host de desarrollo | Impide contrastar la telemetría Docker con el driver físico | reparar o excluir formalmente ese host como máquina de benchmark | administración del host |
| P2 | Advertencia de chunks grandes del frontend | No afecta el contrato de chat, pero aumenta descarga inicial | abordar code splitting en un cambio separado de frontend | fuera del alcance backend |

Hasta cerrar los P0 no debe declararse una mejora clínica de producción ni un
modelo “ganador”. El estado entregado sí es demostrablemente más estricto en
streaming, contratos, hechos, aislamiento, versionado, privacidad y capacidad de
evaluación que la línea base local.
