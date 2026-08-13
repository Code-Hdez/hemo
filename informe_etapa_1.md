La implementación técnica de la Etapa 1 unificada quedó completada. No queda código pendiente dentro de su alcance y no se inició la Etapa 2.

## Archivos modificados

- Configuración y despliegue: .env.example, .env.production.example, backend/app/core/config.py, docker-compose.yml, docker-compose.prod.yml y backend/scripts/validate_deploy_env.py: configuración tipada,
perfiles explícitos, timeout canónico, memoria/RAG configurables y eliminación de valores históricos fijados.
- Contratos: backend/app/modules/llm_chat/domain/response_plan.py:7, backend/app/modules/llm_chat/domain/generation_config.py:245 y backend/app/modules/llm_chat/domain/__init__.py: contratos canónicos e
inmutables.
- Solicitudes y respuesta: backend/app/modules/llm_chat/domain/entities.py, backend/app/modules/llm_chat/application/dto.py, backend/app/modules/llm_chat/api/schemas.py:181, backend/app/modules/llm_chat/
api/router.py y backend/app/modules/llm_chat/application/use_cases/send_chat_message.py:4384: validación pública previa al commit y retorno del mismo objeto validado.
- Generación y memoria: backend/app/modules/llm_chat/application/services/chat_profile_policy.py, backend/app/modules/llm_chat/application/services/prompt_builder.py, backend/app/modules/llm_chat/
application/services/token_budget.py y backend/app/modules/llm_chat/application/services/conversation_memory.py:343: eliminación de clamps y corrección decimal.
- Composición/proveedor/RAG: backend/app/modules/llm_chat/composition.py:395, backend/app/modules/llm_chat/infrastructure/llm/openai_compatible_client.py:675, backend/app/modules/llm_chat/application/
services/retrieval_service.py y backend/app/modules/llm_chat/infrastructure/retrieval/bm25_store.py: inyección única y payload exacto.
- Concurrencia: backend/app/modules/llm_chat/domain/exceptions.py:58 y backend/app/modules/llm_chat/infrastructure/repositories/sqlalchemy_repositories.py:877: conflicto CAS tipado, rollback y error HTTP/
SSE 409.

## Contratos y configuración efectiva

Se definieron una sola vez RetrievalPolicy, RetrievalStatus, KnowledgeMode y ResponsePlan. ResponsePlan no contiene use_rag ni genera texto visible.

La precedencia final es:

entorno/.env → Settings → GenerationProfileSettings.from_settings() una sola vez → perfil principal por ámbito → overrides explícitos de reparación → ModelRequest inmutable → logging seguro → payload de
Ollama.

Se eliminaron los límites silenciosos de 3072, los perfiles 384/4096 fijados, salida forzada, clamps min()/_bounded(), límites RAG por fuente embebidos y modificaciones tardías de sampling, thinking o
timeout. keep_alive y los sub-timeouts también quedaron validados.

## Correcciones críticas

- 150, 150.00, 15.20, 500, 0 y 0.00 ahora conservan exactamente su significado sin pasar por float.
- ChatResponse se construye y serializa completamente antes de complete_turn().
- Ollama recibe los mismos valores efectivos registrados por cada intento, sin registrar prompts, transcript ni hechos clínicos.
- complete_turn() valida conversación, revisión, intento y estado antes de insertar el asistente; cualquier conflicto hace rollback y lanza ChatTurnConcurrencyConflict.
- Los errores técnicos no se persisten como mensajes clínicos.
- Logging y telemetría posteriores al commit no pueden convertir una respuesta persistida en un 500.

## Compatibilidad temporal

Se conservó temporalmente deterministic_safety_boundary en el schema público para la ruta legacy activa. Está identificado para eliminarse en la etapa posterior del contrato generativo. También permanecen
módulos legacy no importados por la ruta canónica que todavía usan os.getenv(); no se tocaron porque su eliminación pertenece a etapas posteriores.

## Verificación estática

Pasaron:

- git diff HEAD --check
- Ruff sobre los 20 archivos Python de producción modificados.
- Parseo AST de los 20 archivos.
- Búsquedas dirigidas de contratos duplicados, os.getenv(), clamps, límites históricos, construcción única de configuración y llamadas a complete_turn().
- Revisión del orden generación → validación pública → persistencia → retorno.
- Revisión del payload final de Ollama y del diff completo.

No se ejecutaron pytest, suites, servicios, Docker, PostgreSQL, ChromaDB, FastAPI ni Ollama. No se crearon, modificaron ni ejecutaron tests.

Salvedad obligatoria: una auditoría delegada ejecutó por error un rg demasiado amplio que mostró algunas coincidencias dentro de backend/tests. No abrió archivos completos ni utilizó pruebas como
especificación, pero por ello no puedo afirmar literalmente que ningún contenido de tests fue leído parcialmente. No oculto esta desviación.

## Pendientes fuera de alcance

- Migrar el .env.production real para retirar OLLAMA_TOTAL_TIMEOUT_SECONDS y declarar los campos nuevos; no se modificó porque es un archivo operativo con posibles secretos.
- Retirar la compatibilidad determinista y los módulos legacy en sus etapas posteriores.
- No se inició ni adelantó la Etapa 2.

Los cuatro Markdown obligatorios fueron leídos íntegramente y no edité su contenido. No hice commit, push, merge ni rebase.