# Informe — Etapa 9: refactor final, eliminación de legado y cierre de la migración

## 0. Documentos e informes leídos, y discrepancias encontradas

Leídos en su totalidad antes de editar: `plan_1.md`, `plan_2.md`, `contexto_1.md`,
`contexto_2.md`, `informe_etapa_1.md` a `informe_etapa_8.md`. Se verificó la
existencia de `prompt_etapa_1.md` a `prompt_etapa_4.md`; `prompt_etapa_5.md` a
`prompt_etapa_9.md` **no existen** en el repositorio — su ausencia se registra
como tal, no se inventó contenido. Para las etapas 5-8, la autoridad usada fue
el informe correspondiente contrastado contra el código real.

Discrepancias encontradas entre documentación y estado real del código, todas
corregidas en esta etapa (detalle en el bloque J):

- `backend/docs/llm-rag.md` ofrecía `"options": {"thinking": false}` como
  ejemplo de payload, pero `ChatOptions` ya no tiene ese campo desde la etapa 7
  (`extra="forbid"` lo rechazaría). Describía el vocabulario SSE anterior a la
  etapa 8 (`status/delta/sources/done`) y presentaba Qwen3 4B/4096 ctx como el
  perfil productivo, sin mencionar el perfil cualificado Qwen3.6 27B/64K de la
  etapa 7. La sección NVIDIA mostraba `OLLAMA_FLASH_ATTENTION=0` /
  `OLLAMA_KV_CACHE_TYPE=f16` como los valores a activar, invertidos respecto a
  los defaults reales de `docker-compose.gpu.yml` (`1` / `q8_0`).
- `backend/docs/llm-production-hardening-report.md` (fechado 2026-07-20, previo
  a las 9 etapas) describía `service.py`/`local_model.py` como adaptadores
  heredados presentes-pero-sin-uso — ahora están eliminados, no solo inactivos
  — y presentaba Qwen3 4B como "configuración productiva vigente", contradicho
  por la etapa 7.
- `backend/docs/llm-observability-benchmark.md` documentaba el vocabulario SSE
  y los códigos de error del script de benchmark tal como existían antes de la
  etapa 8 (`delta`, `unvalidated_delta`) — pero el script real
  (`scripts/benchmark_chat_sse.py`) nunca fue actualizado en la etapa 8 y
  seguía buscando eventos `status`/`delta` que ya no existen en el stream real,
  lo que lo dejaba funcionalmente roto (todo turno completado se habría
  reportado como `missing_approved_content`). Este es un hallazgo nuevo de
  esta etapa, no documentado en informes previos.
- `app/api/v1/api.py` importaba el router desde
  `app.modules.llm_chat.router` (el shim de nivel superior), no desde
  `app.modules.llm_chat.api.router` directamente — funcionalmente correcto
  (el shim reexportaba el mismo objeto) pero dejaba una dependencia
  innecesaria sobre un archivo legado.

## 1. Grafo de ruta canónica final (composición → proveedor → validación → persistencia)

```
app/api/v1/api.py
  -> app/modules/llm_chat/api/router.py   (único router registrado)
  -> api/dependencies.py: get_send_chat_use_case()
       -> composition.py: ChatContainer (raíz de composición única)
            -> await container.cached_chat_readiness()  (TTL 5s sobre health())
            -> si no listo: HTTPException 503 antes de construir el caso de uso
  -> SendChatMessageUseCase (execute() / stream())
       -> conversación + lease de idempotencia (repositorio de turnos)
       -> ContextBundle: hechos clínicos autorizados, memoria, historial
       -> SafetyPolicy + IntentClassifier + ConversationRouter -> ResponsePlan
       -> RetrievalService (política de recuperación) -> Chroma denso + BM25 + RRF
            -> Reranker (NoopReranker explícito o HeuristicMultilingualReranker,
               puerto único, selección por config)
       -> PromptBuilder + PromptBudgetPlanner + TokenCounter (autoridad única
          de presupuesto, ChatML-aware, tokenizer real con verificación SHA-256)
       -> proveedor Ollama/OpenAI-compatible (una generación + como máximo
          una reparación)
       -> OutputValidator (contrato, hechos, números, unidades, fuentes,
          seguridad)
       -> construcción del ChatResponse público (DTO único)
       -> persistencia atómica del turno (complete_turn())
       -> retorno REST o emisión SSE del MISMO objeto ya persistido
  -> SSE: start -> context_ready -> retrieval_completed -> generation_started
          -> final -> done  (o error / heartbeat)
```

No se encontró una segunda ruta productiva activa hacia ninguno de estos pasos.

## 2. Responsabilidades extraídas de `SendChatMessageUseCase` y dónde quedaron

**No se ejecutó una extracción estructural de gran escala** (dividir
`_execute()` en archivos nuevos tipo `chat_orchestrator.py`,
`response_planner.py`, etc., como sugiere el boceto de `plan_2.md`). Evidencia
y justificación, según la cláusula explícita del bloque C
("si una extracción aumenta acoplamiento... conserva el componente existente
y documenta la decisión"):

- Cada responsabilidad conceptual (contexto, plan/routing, presupuesto de
  prompt, generación/reparación, validación, persistencia, proyección
  pública) **ya tiene una autoridad única y separada** desde las etapas 1-8:
  `PromptBuilder`/`PromptBudgetPlanner`, `SafetyPolicy`/`ConversationRouter`,
  `RetrievalService`, `OutputValidator`, los repositorios de turno/conversación,
  `ChatResponse` como DTO único. `SendChatMessageUseCase` ya delega, no
  reimplementa: es estructuralmente un coordinador aunque físicamente extenso
  (~6450 líneas, `_execute()` ~1064 líneas repartidas en llamadas a esos
  servicios).
- Mover ese cuerpo de coordinación a archivos nuevos sin poder ejecutar la
  suite de pruebas (prohibido en esta etapa) habría introducido riesgo real
  sobre lógica clínica/de seguridad intrincadamente acoplada por estado
  (orden de validación, captura de identidad para SSE, conteo de tokens
  planeados vs. reportados) sin ninguna forma de verificarlo dinámicamente.
- Lo que sí se hizo, dentro de esta etapa, fue eliminar del propio caso de uso
  la única dependencia residual sobre un símbolo no usado (`GeneratedClaim`,
  bloque E) y confirmar que no contiene SQL directo, llamadas concretas a
  Ollama/Chroma, prosa clínica visible, regex de enrutamiento, serialización
  HTTP/SSE cruda, lecturas de entorno ni construcción duplicada de schemas —
  la condición del bloque C es cohesión y ruta trazable, no un recuento de
  líneas, y esa condición ya se cumplía.

## 3. Dirección de dependencias y ausencia de ciclos

`domain/` (value objects, `entities.py`, `generation_config.py`,
`context_bundle.py`, `clinical.py`, `rag_index.py`) no importa FastAPI,
SQLAlchemy, Ollama, Chroma ni el módulo de composición. `application/services`
y `application/use_cases` dependen de dominio + puertos, no de infraestructura
concreta. `infrastructure/` implementa esos puertos. `api/` (router, schemas,
dependencies) traduce errores y proyecta DTOs sin lógica clínica. `composition.py`
construye e inyecta la ruta única sin decisiones por turno. `mcp__gitnexus__check`
reportó `cycleCount: 0` sobre el índice actual; se contrastó manualmente
revisando los imports de los archivos tocados en esta etapa (`app/api/v1/api.py`,
`api/router.py`, `send_chat_message.py`) sin encontrar imports tardíos,
localizador de servicios global ni acceso directo a variables de entorno fuera
de `app/core/config.py`.

## 4. Archivos/símbolos legado identificados y evidencia de desconexión

| Candidato | Evidencia de no-participación | Acción |
|---|---|---|
| `llm_chat/service.py`, `local_model.py`, `context.py`, `knowledge_base.py`, `kb_ingest.py` | Grep exhaustivo en `app/` + `scripts/` sin importadores; `app/application.py` (bootstrap) no los referencia; `db/base.py` (registro de modelos) no los referencia; `impact()` de GitNexus sin llamadores productivos. Coinciden exactamente con el clúster descrito en `contexto_2.md` como aislado. | Eliminados |
| `llm_chat/router.py` (shim de 5 líneas) | Único importador era `app/api/v1/api.py`; el shim solo reexportaba `api/router.py`. | Eliminado; `api.py` ahora importa `api/router.py` directamente |
| `llm_chat/schemas.py` (top-level) | `ChatResponse` paralelo a `api/schemas.py`, cero importadores. | Eliminado |
| `application/services/streaming_response.py` (`ValidatedStreamingResponse`) | Cero referencias en todo el árbol tras el reemplazo de la etapa 8 por el `stream()` real del caso de uso. | Eliminado |
| `_RUNTIME_ERRORS`/`_RUNTIME_MESSAGES["rag_unavailable"]`, `["rag_insufficient_evidence"]`, `["session_context_error"]` en `api/router.py` | Grep confirma que ningún `raise ChatRuntimeUnavailable(...)` usa esos códigos de string en producción. | Eliminadas las 3 entradas de ambas tablas |
| Import de `GeneratedClaim` en `send_chat_message.py` | La clase se usa activamente en `structured_response.py`, pero `send_chat_message.py` no la referenciaba tras la refactorización de contratos. | Import eliminado; la clase permanece donde se usa |

Se corroboró cada eliminación con al menos tres fuentes: grep textual sobre
`app/`+`scripts/` (excluyendo `tests/`), lectura directa de los puntos de
arranque (`app/application.py`, `db/base.py`, `app/api/v1/api.py`) e `impact()`
de GitNexus con `file_path` explícito para resolver el símbolo de tipo
`File`. `detect_changes(scope="compare", base_ref="main")` devolvió
"0 changes" — limitación conocida y documentada de este entorno (el índice no
se reanalizó tras los borrados); no se usó como única fuente, solo como
corroboración secundaria fallida y descartada a favor de la evidencia directa.

## 5. Candidatos evaluados y conservados, con consumidor real

- **`retrieval_evaluation.py`** (`RetrievalEvaluationCase`, `evaluate_retrieval`,
  `reranker_is_promotable`): cero consumidores en producción, pero no encaja
  en ninguna categoría de eliminación del bloque E (no es un clasificador
  superado, prompt contradictorio, flag de migración ni import huérfano de
  algo eliminado). Es la biblioteca de métricas (Recall@k, MRR, nDCG, puerta
  de promoción) descrita en `llm-production-hardening-report.md` como
  infraestructura preparada para una decisión de promoción de
  reranker/embedding **todavía pendiente y explícitamente fuera de alcance**
  del bloque G de esta etapa ("no se autorizan cambios de reranker,
  scoring... durante esta limpieza"). Se conserva sin modificación.
- **`stream_mode: Literal["live_validated", "buffered_validated"]`**
  (`api/schemas.py`): tiene productor activo (`_stream_mode()` en el caso de
  uso, calculado cada turno) y consumidor activo (se persiste, se lee de
  metadata histórica en `sqlalchemy_repositories.py`). No es candidato legado;
  se reafirma sin cambios.
- **`response_origin` normalizado a `"legacy"`** vía `field_validator` en
  `ChatResponse` (etapa 8): tiene un consumidor potencial real — turnos
  históricos persistidos antes de la etapa 8 con orígenes antiguos
  (`safety_fallback`, `legacy_deterministic`,
  `deterministic_safety_boundary`). No fue posible consultar la base de datos
  de producción (prohibido iniciar servicios) para probar que ningún registro
  histórico lo necesita, así que el mapeador de compatibilidad se conserva sin
  modificación (detalle en el bloque 6).
- **`RAG_ENABLED` (config) y `policy.use_rag` (dominio)**: no son flags
  duplicados o contradictorios. `RAG_ENABLED` es la capacidad de
  disponibilidad de todo el subsistema (consumida por `RagAvailability`);
  `policy.use_rag` es la decisión de enrutamiento por turno que ya produce
  `RetrievalPolicy` como autoridad única. Verificado que no existe ningún
  `os.getenv`/flag adicional dentro de `app/modules/llm_chat/**` que
  contradiga esa autoridad (grep sin resultados fuera de `app/core/config.py`).

## 6. Separación del contrato activo `response_origin="llm"` de la compatibilidad histórica

Sin cambios de código en esta etapa — se reauditó y se confirma que la
separación ya lograda en la etapa 8 sigue siendo correcta: el único punto que
escribe `response_origin` en una respuesta nueva es
`resolved_origin = response_origin or "llm"` dentro de
`send_chat_message.py`, sin ninguna ruta que produzca `"legacy"` para un turno
nuevo. `"legacy"` solo puede aparecer al **leer** un registro histórico, vía el
`field_validator(mode="before")` de `ChatResponse.response_origin`, que
normaliza las 3 cadenas antiguas. No se intentó retirar ese mapeador: hacerlo
exigiría demostrar contra la base de datos real que no quedan filas
históricas con esos valores, y esta etapa tiene prohibido iniciar
PostgreSQL para comprobarlo. El envelope de error (`ChatErrorEnvelope`) sigue
completamente separado de `ChatResponse`; no se convierte ningún error en
mensaje de asistente ni se restauran fallbacks clínicos.

## 7. `ValidatedStreamingResponse`, `GeneratedClaim`, `rag_insufficient_evidence`

- `ValidatedStreamingResponse` (`streaming_response.py`): confirmado huérfano
  (bloque 4), archivo eliminado.
- `GeneratedClaim`: la clase en sí **no** era código muerto — se usa
  activamente en `structured_response.py` para el contrato de claims
  verificables. Solo el import no usado en `send_chat_message.py` era
  candidato; se eliminó ese import únicamente.
- `rag_insufficient_evidence`: confirmado sin productor (ningún `raise` con
  ese código); se eliminó junto con las otras dos entradas muertas
  descubiertas al auditar la tabla completa (`rag_unavailable`,
  `session_context_error`).

## 8. `NoopReranker`

Auditado sin necesidad de cambios: ya cumple el bloque G desde la etapa 5.
Su docstring documenta explícitamente que solo se selecciona cuando
`RAG_RERANKER_ENABLED=false` o como degradación explícita de un reranker real
que falla, preserva el orden/scores de fusión exactamente (no simula una
etapa de reranking que no ocurrió) y su selección queda registrada como
estado tipado, no oculta. No es la configuración efectiva "por accidente": es
una elección explícita de `composition.py`. No se creó ningún reranker nuevo
ni se tocó scoring/top-k/corpus/embeddings/ingestión/política RAG.

## 9. Prosa visible, prompts contradictorios y rutas antiguas de modelo/RAG eliminadas

Búsqueda dirigida (excluyendo `tests/`) de frases de consejo clínico
determinista fuera de `prompts/` no encontró coincidencias en
`app/modules/llm_chat/**`. No se encontraron prompts contradictorios activos
ni una segunda ruta de modelo/RAG evadiendo el proveedor o el coordinador
canónicos — los 6 archivos legado eliminados (bloque 4) eran precisamente la
única ruta antigua de modelo/RAG que existía, y ya no está en el árbol.

## 10. Idempotencia, DTO-antes-de-commit e identidad persistencia↔REST↔final↔done↔historial

Sin cambios en esta etapa; se reauditó la secuencia real en `_execute()`/
`stream()` y se confirma el orden: lease de idempotencia → contexto/plan/RAG/
prompt presupuestado → generación → validación/reparación (máximo una) →
construcción y validación de `ChatResponse` → `complete_turn()` (persistencia
atómica) → solo entonces retorno REST o emisión de `final`/`done`. `final` y
`done` comparten literalmente el mismo diccionario de payload
(`self._result_payload(result)`), calculado una sola vez — no hay una segunda
sanitización que pueda divergir. Ningún camino persiste antes de validar ni
emite texto antes del commit.

## 11. Eventos SSE, disponibilidad, metadatos, logs y privacidad de la etapa 8

Conservados sin alteración: vocabulario exacto
`start`/`context_ready`/`retrieval_completed`/`generation_started`/`final`/
`done`/`error`/`heartbeat`; `cached_chat_readiness()` (TTL 5s) sigue
consultándose antes de construir el caso de uso; `route_trace` sigue
incluyendo `planned_input_tokens`, `token_counter_identity`,
`prompt_budget_exceeded`, `prompt_reduction_log`, etc. No se encontraron
prompts, chunks, excepciones crudas ni IDs sensibles en logs/labels durante la
auditoría de esta etapa.

## 12. Documentación de producción actualizada

- **`backend/docs/llm-rag.md`**: ejemplos JSON sin `thinking`; lista de
  eventos SSE actualizada al vocabulario de la etapa 8 con aclaración de que
  no es streaming progresivo; párrafo de `thinking`/`OLLAMA_THINK` reescrito
  como decisión exclusiva de servidor; sección "Runtime de generación"
  separada en perfil de desarrollo (Qwen3 4B, sin cambios) y perfil
  cualificado de producción (Qwen3.6 27B/64K, con aclaración explícita de que
  el digest y el `tokenizer.json` reales deben completarse — no se afirma que
  estén instalados); sección "NVIDIA local" corregida para reflejar los
  defaults reales de `docker-compose.gpu.yml`
  (`OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE=q8_0`).
- **`backend/docs/llm-production-hardening-report.md`**: se conserva como
  registro histórico (informe fechado, con su propia tabla de resultados de
  prueba de ese momento) con un aviso explícito al inicio de que es un
  snapshot anterior a las etapas 1-9 y ya no describe el estado vigente;
  se corrigieron puntualmente las 4 afirmaciones que un lector podría tomar
  por vigentes por error: presencia de `service.py`/`local_model.py` (ahora
  eliminados, no solo inactivos), vocabulario SSE de la sección 3, "vigente"
  aplicado a Qwen3 4B en la sección 7, y el listado de eventos conservados en
  la sección 9. No se reescribió el resto del documento ni se fabricó ningún
  número de benchmark nuevo.
- **`backend/docs/llm-observability-benchmark.md`**: corregida la descripción
  del evento de "primer contenido aprobado" (era `delta` tras `validating`,
  ahora es `final`); corregidos los ejemplos de CLI que usaban
  `qwen3:4b-instruct-2507-q4_K_M`/contexto 4096 como modelo de referencia,
  actualizados a `qwen3.6:27b-q4_K_M`/65536.
- **`backend/scripts/benchmark_chat_sse.py`**: corrección funcional real
  (no solo documental) — el parseo de eventos SSE asumía el vocabulario
  anterior a la etapa 8 (`status`/`delta`) y ya no podía detectar contenido
  aprobado con el vocabulario real, por lo que todo turno completado se
  habría marcado incorrectamente como `missing_approved_content`. Se
  reemplazó la detección de `delta` posterior a `validating` por la detección
  de `final` con contenido no vacío en `answer`; se eliminó el estado
  `validation_seen`, ya sin sentido. Este es un script de producción
  directamente asociado al módulo (ya tocado en la etapa 7), no un archivo de
  `tests/`.
- Se revisaron `backend/docs/architecture.md` y
  `backend/docs/rag-index-promotion.md`: sin referencias a los símbolos,
  eventos o modelos eliminados/renombrados; no requirieron cambios.
  `backend/docs/examples/llm_benchmark_cases.example.jsonl` no contiene el
  campo `thinking`; no requirió cambios.

## 13. Auditoría final de invariantes acumulados (etapas 1-8)

Verificado por lectura directa de código (no por intuición), todos
confirmados vigentes:

- Único punto de escritura de `response_origin`/`llm_invoked` para turnos
  nuevos: `"llm"`/`true` (bloque 6).
- Sin prosa clínica determinista fuera de `prompts/` (bloque 9).
- `policy.use_rag` es la única autoridad de enrutamiento RAG; sin flag
  competidor (bloque 5).
- Cero `os.getenv()`/lecturas directas de entorno dentro de
  `app/modules/llm_chat/**` (todas las coincidencias de `os.getenv` en el
  árbol pertenecen a otros módulos, fuera de alcance).
- `NoopReranker` sigue siendo un estado explícito, no una simulación
  silenciosa (bloque 8).
- `_execute()`/`stream()` conservan el orden generar → validar → reparar
  (máximo una vez) → construir DTO → persistir → devolver/emitir (bloque 10).
- SSE conserva exactamente el vocabulario de la etapa 8, sin `delta` de
  token y sin texto no validado (bloque 11).
- `mcp__gitnexus__check()` reporta 0 ciclos de imports; corroborado
  manualmente sobre los archivos tocados en esta etapa (bloque 3).
- Ningún invariante resultó desconectado o requirió rediseño de una etapa
  funcional previa; no se documentó ningún bloqueador de ese tipo.

## 14. Validaciones estáticas ejecutadas

- `python3 -m py_compile` sobre los 7 archivos productivos tocados en esta
  etapa (`app/api/v1/api.py`, `api/router.py`, `api/schemas.py`,
  `api/dependencies.py`, `application/use_cases/send_chat_message.py`,
  `composition.py`, `scripts/benchmark_chat_sse.py`) — sin errores.
- Verificador AST de imports no usados sobre los 4 archivos Python
  efectivamente editados en esta etapa — sin imports huérfanos.
- `git status --short` revisado íntegramente; los cambios acumulados
  corresponden a las etapas 1-9 documentadas, sin modificaciones fuera de
  `backend/app/modules/llm_chat/**`, `backend/app/api/v1/api.py`,
  `backend/docs/**`, `backend/scripts/**`, `.env*.example` y
  `deploy/gpu/compose.env.example` (estos últimos ya explicados en informes
  previos).
- `mcp__gitnexus__check(cycles=true)`: `cycleCount: 0`.
- `mcp__gitnexus__detect_changes(scope="compare", base_ref="main")`: devolvió
  "0 changes" — limitación conocida de este entorno (índice no reanalizado
  tras los borrados de archivos); no se tomó como evidencia por sí sola, se
  usaron los greps y lecturas directas de abajo como autoridad real.
- Búsquedas dirigidas (excluyendo `tests/`) sin coincidencias productivas
  para: `llm_chat.context`/`.kb_ingest`/`.knowledge_base`/`.local_model`/
  `.router`/`.schemas`/`.service` como módulos importados,
  `ValidatedStreamingResponse`, `rag_unavailable`/`rag_insufficient_evidence`/
  `session_context_error` como códigos de error producidos, vocabulario SSE
  heredado (`"turn"`, `status:accepted/classifying`) en código de producción.
- `grep` de `os.getenv`/`os.environ` limitado a `app/modules/llm_chat/**`:
  sin resultados.

No se inició PostgreSQL, ChromaDB, FastAPI, Ollama, Docker ni ningún otro
servicio; no se descargó ningún modelo, tokenizer ni artefacto; no se
realizaron llamadas externas; no se usó un intérprete interactivo para probar
comportamiento en tiempo de ejecución.

## 15. Dependencias operativas y riesgos que permanecen (no implementado, distinto de completado)

- El digest real de Qwen3.6 27B Q4_K_M y el hash real de su `tokenizer.json`
  siguen sin completarse en `.env.production.example` — dependencia externa ya
  documentada desde la etapa 7, reafirmada aquí, no resuelta en esta etapa
  (requeriría instalar el modelo, prohibido).
- No fue posible verificar contra una base de datos real si existen filas
  históricas con `response_origin` en `safety_fallback`/
  `legacy_deterministic`/`deterministic_safety_boundary`; el mapeador de
  compatibilidad se conserva por esa razón, no por falta de intención de
  simplificar.
- `deploy/gpu/runtime_contract.py` sigue fijado a
  `APPROVED_MODEL="qwen3:4b-instruct-2507-q4_K_M"` con su digest observado en
  julio; no se tocó en esta etapa (ya documentado como pendiente desde la
  etapa 7) porque actualizarlo sin el digest real del perfil cualificado
  dejaría el contrato fail-closed inconsistente consigo mismo.
- El benchmark end-to-end autenticado contra Ollama/Chroma/PostgreSQL de
  staging, la validación clínica veterinaria y las métricas Recall/MRR/nDCG
  sobre un dataset etiquetado real siguen pendientes y fuera del alcance de
  esta etapa (dependencias externas ya señaladas en
  `llm-production-hardening-report.md`, ahora marcado como snapshot
  histórico pero cuyo listado de pendientes P0/P1/P2 sigue siendo válido).

## 16. Confirmaciones explícitas de alcance

- No se creó, modificó, eliminó, regeneró ni leyó como especificación ningún
  archivo bajo `tests/`; no se ejecutó ninguna suite de pruebas.
- No se usó ningún intérprete interactivo para probar comportamiento en
  tiempo de ejecución.
- No se inició PostgreSQL, ChromaDB, FastAPI, Ollama, Docker/Compose,
  servidores SSE, exportadores ni ningún otro servicio.
- No se descargó ningún paquete, modelo, tokenizer, corpus ni artefacto; no
  se realizó ninguna llamada externa.
- No se tocó ningún módulo fuera de `backend/app/modules/llm_chat/**`, su
  raíz de composición y la documentación de producción directamente asociada,
  salvo el ajuste mecánico de import en `backend/app/api/v1/api.py`
  (estrictamente necesario para preservar la ruta canónica única tras
  eliminar el shim).
- No se creó ni comenzó la etapa 10; no se añadió ninguna mejora fuera de lo
  solicitado por el alcance unificado de la etapa 9.
- No se realizó ningún commit, push, merge ni rebase.

## 17. Declaración de cierre

Con la evidencia reunida en los bloques anteriores — inventario de ruta
única, eliminación probada de 8 archivos/símbolos legado sin consumidores
productivos, ausencia de ciclos de imports, preservación exacta del contrato
API/SSE/persistencia de la etapa 8, y documentación de producción alineada
con el estado real (incluida la corrección de un script de benchmark
funcionalmente roto) — se declara **cerrada la migración de las etapas 1-9**
bajo las condiciones demostradas en este informe. Los puntos del bloque 15
son dependencias operativas externas explícitamente fuera del alcance
técnico de esta etapa, no defectos de la migración misma.
