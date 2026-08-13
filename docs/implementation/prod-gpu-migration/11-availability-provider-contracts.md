# Contratos de disponibilidad y proveedor remoto

Estado: contrato `v1` implementado y validado en la Etapa 5. La red privada y
el startup reconciliador GPU siguen pendientes.

## Planos y probes de salud

| Plano | Endpoint | Qué demuestra | Qué no consulta |
| --- | --- | --- | --- |
| Liveness | `GET /health` | El proceso FastAPI puede responder | PostgreSQL, Chroma y Ollama |
| Readiness | `GET /health/operational` | El núcleo puede servir tráfico y expone capacidades degradadas | No exige que la GPU esté encendida |
| Chat agregado | `GET /health/llm` y `GET /api/v1/chat/health` | Módulo, proveedor, identidad y RAG | No decide por sí solo la salud del núcleo |
| Proveedor | `GET /api/v1/chat/health/provider` | Disponibilidad e identidad sanitizadas | RAG y base de datos |
| RAG | `GET /api/v1/chat/health/rag` | Chroma, colección e índice requeridos | Proveedor LLM |

Todos los payloads declaran `contract_version=hemovet.availability/v1`. Los
health operativos responden JSON sanitizado; los consumidores deben evaluar
`core_ready` y `chat_ready`, no inferir disponibilidad desde un único campo
legacy. El campo `probe` distingue `liveness`, `readiness`,
`chat_availability` y los objetos anidados `rag_availability` y
`provider_availability`. `llm_ready` se conserva temporalmente como alias de
`provider_ready`.

## Invariantes

- `core_ready` exige PostgreSQL, el modelo local de análisis cuando esté
  habilitado y ausencia de gates bloqueantes.
- Chroma, RAG, Ollama y la GPU no forman parte de `core_ready`.
- `chat_ready` agregado exige `core_ready`, módulo cargado, proveedor validado y,
  cuando `RAG_ENABLED=true`, Chroma, colección e índice RAG listos.
- Con `RAG_ENABLED=false`, `rag_ready=true` significa “dependencia satisfecha
  por no ser requerida”; no afirma que exista una colección.
- Un tag, digest o cuantización incorrectos dejan `provider_ready=false` y no
  son reintentables a ciegas.
- Una falla exclusiva de `/api/ps` no cambia `provider_ready`: ese endpoint
  describe residencia/telemetría, no instalación ni identidad.
- Un timeout del probe de identidad produce `LLM_PROVIDER_UNAVAILABLE`,
  reintentable, y no se clasifica como un digest incorrecto.
- El payload público no contiene URL privada, IP, credenciales ni prompts.

## Matriz normativa

| Escenario | `core_ready` | `chat_ready` | `status` |
| --- | --- | --- | --- |
| GPU/Ollama apagado y núcleo sano | `true` | `false` | `degraded` |
| GPU disponible, modelo y RAG válidos | `true` | `true` | `ok` |
| PostgreSQL no responde | `false` | `false` | `fail` |
| RAG requerido no disponible | `true` | `false` | `degraded` |
| RAG deshabilitado y proveedor válido | `true` | `true` | `ok` |
| Modelo autorizado no coincide | `true` | `false` | `degraded` |

Que `core_ready=true` con RAG degradado no autoriza generación clínica sin
evidencia. El frontend bloquea nuevas generaciones, pero mantiene navegación e
historial; los guardrails clínicos siguen fallando cerrados. No se selecciona
silenciosamente otra colección ni se cambia el puntero activo. Si
`RAG_ENABLED=false`, la dependencia se considera satisfecha sin afirmar que
exista un índice.

## Contrato `hemovet.llm-provider/v1`

El backend es dueño de autenticación, RAG, prompts, validación, persistencia y
errores públicos. El runtime remoto solo recibe una solicitud de inferencia y
devuelve tokens.

El caso de uso depende del port mínimo `LLMGenerationPort`; la composición del
runtime exige `LLMProvider`, que añade `identity_status()`, `health()` y
`runtime_status()`. La identidad instalada se evalúa por separado de la
residencia en acelerador. Si el probe de identidad falla, la disponibilidad
falla cerrada sin impedir construir repositorios o persistencia.

### Transporte

- URL: `OLLAMA_BASE_URL`, sin IP hardcodeada. En producción deberá resolver a la
  interfaz privada verificada en la Etapa 7.
- API del adaptador Ollama nativo: `/api/chat` para generación, `/api/tags` para
  instalación, `/api/show` para identidad/cuantización y `/api/ps` solo para
  residencia. La reconciliación completa se implementa en la Etapa 6.
- Header de correlación: `X-HemoVet-Correlation-ID`, opaco, máximo 128 caracteres
  y nunca incluido en el prompt.
- Streaming: el cierre del cliente se propaga como cancelación; un stream sin
  marcador terminal no se persiste como respuesta completa.
- Backpressure: continúa a cargo del semáforo y la cola del caso de uso en
  producción.

### Timeouts y reintentos actuales formalizados

| Límite | Variable | Valor por defecto |
| --- | --- | --- |
| Conexión | `OLLAMA_CONNECT_TIMEOUT_SECONDS` | 3 s |
| Lectura HTTP del proveedor | `OLLAMA_TOTAL_TIMEOUT_SECONDS` | 75 s |
| Escritura | `OLLAMA_WRITE_TIMEOUT_SECONDS` | 15 s |
| Pool | `OLLAMA_POOL_TIMEOUT_SECONDS` | 5 s |
| Deadline del turno/stream | `CHAT_TOTAL_TIMEOUT_SECONDS` | 150 s |
| Heartbeat SSE | `CHAT_STREAM_HEARTBEAT_SECONDS` | 15 s |

`OLLAMA_MAX_RETRIES` permite cero o un reintento y el transporte lo aplica solo
al establecimiento de conexión. No se reintenta automáticamente una lectura,
un HTTP error o una generación que pudo haber comenzado. El usuario puede
reintentar el mismo turno mediante el contrato idempotente existente.

### Errores públicos

| Clase | Código público | HTTP público | Reintentable |
| --- | --- | --- | --- |
| No disponible | `LLM_PROVIDER_UNAVAILABLE` | 503 | sí |
| Saturado | `LLM_PROVIDER_OVERLOADED` | 503 | sí |
| Timeout de conexión/lectura | `LLM_PROVIDER_CONNECT_TIMEOUT`, `LLM_PROVIDER_READ_TIMEOUT` | 504 | sí |
| Respuesta inválida | `LLM_PROVIDER_INVALID_RESPONSE` | 502 | no automático |
| Identidad inválida | `LLM_PROVIDER_IDENTITY_UNVERIFIED` y códigos de mismatch | chat no listo/503 | no |
| Stream interrumpido | contrato estructurado del turno | según estado | según estado del turno |

El envelope público conserva `code`, `retryable`, `recovery_action`,
`request_id` y `retry_after_ms`. Los códigos internos antiguos, incluidos los
específicos del adaptador, se normalizan antes de cruzar HTTP, SSE, health o
historial. La ausencia esperada de GPU usa 503 y no convierte el proceso en
crash loop.

## Arranque y recuperación

Repositorios, persistencia, contexto y caso de uso se construyen antes del
warmup. El warmup opcional se ejecuta en background, es best-effort y se
cancela durante shutdown. Cada probe vuelve a evaluar disponibilidad, por lo
que el proveedor puede recuperarse sin reiniciar FastAPI.

El frontend consulta el contrato cada 15 segundos, sin reintentos adicionales
ni polling en background. Deshabilita únicamente generación y conserva el
historial mostrado. Un probe fallido también bloquea generación hasta una
respuesta válida posterior.

## Diferencias aún pendientes

- La Etapa 6 verificará revisión aplicada, persistencia e inferencia real GPU.
- La Etapa 7 demostrará que la URL es privada y que `11434` no es público.
- La Etapa 8 utilizará estos campos como gates de CI/CD.
