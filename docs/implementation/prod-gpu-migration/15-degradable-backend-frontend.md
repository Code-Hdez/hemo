# Etapa 5 — Backend y frontend degradables

Fecha: 2026-08-02. Estado: **COMPLETADA Y VALIDADA EN RAMA; NO DESPLEGADA**.

Commits funcionales:

- `1c234329a948d433b3968233b5d176fe3e0830d0`;
- `105e8aa105795356d67a1f682849799033e8cd98`.

## Objetivo

Mantener disponible el núcleo de HemoVet y la lectura del historial cuando el
proveedor LLM esté apagado, inaccesible o todavía no validado. La generación se
modela como una capacidad recuperable y no como una condición de arranque de
FastAPI.

## Estado inicial

- la composición ejecutaba warmup e inspección de `/api/ps` antes de construir
  repositorios y persistencia;
- una identidad no residente en VRAM podía impedir crear el contenedor del
  chat, aunque el modelo estuviera instalado;
- los errores públicos conservaban códigos y mensajes específicos de Ollama;
- el frontend no consultaba disponibilidad ni se recuperaba sin recarga;
- RAG, proveedor, chat y readiness del núcleo compartían una proyección, pero
  no disponían de probes HTTP independientes para todos sus consumidores.

## Alcance aplicado

- composición, ports, adaptadores y health de `llm_chat`;
- proyección de readiness de FastAPI;
- errores HTTP/SSE y errores persistidos que cruzan la frontera pública;
- consulta de disponibilidad y estado degradado del frontend;
- pruebas unitarias, de integración y E2E;
- documentación de contratos, riesgos y rollback.

## Elementos fuera de alcance

- no se desplegó ni reinició producción;
- no se encendió, adjuntó ni modificó `hemovet-llm-gpu`;
- no se cambió GCP, red, firewall, IAM, IPs, discos o metadata;
- no se cambió GitHub Actions, secrets, variables o environments;
- no se modificaron archivos Compose;
- no se retiró el Ollama local que pueda existir en el runtime productivo
  anterior;
- no se implementó todavía la reconciliación GPU de la Etapa 6.

## Contrato backend implementado

### Arranque y persistencia

`build_chat_container()` construye el cliente HTTP, los repositorios
SQLAlchemy, el repositorio de contexto, el RAG local y el caso de uso antes de
cualquier warmup. El warmup opcional se ejecuta como tarea best-effort y se
cancela ordenadamente al cerrar la aplicación.

Por tanto, una conexión rechazada, timeout, GPU apagada o `/api/ps` no
disponible no impide construir:

- persistencia conversacional;
- restauración/listado de conversaciones;
- `turn_history()` y estado de turnos;
- contexto de hemogramas y mascotas;
- autenticación y el resto del monolito.

No se añadió un fallback que omita filtros de usuario o
`browser_session_hash`.

### Identidad frente a residencia

El port `LLMProvider` distingue `identity_status()` de `runtime_status()`:

- `/api/tags` confirma que el modelo está instalado;
- `/api/show` aporta identidad y cuantización;
- `/api/ps` aporta únicamente telemetría de residencia y GPU.

Un modelo instalado y autorizado sigue dejando `provider_ready=true` aunque
no esté cargado en VRAM. Un fallo exclusivo de `/api/ps` deja
`residency_observed=false`, sin derribar el chat. Un timeout del probe de
identidad se clasifica como `LLM_PROVIDER_UNAVAILABLE`, reintentable; no se
presenta falsamente como digest incorrecto.

### Probes y estados

| Probe | Endpoint | Semántica |
| --- | --- | --- |
| Liveness | `GET /health` | proceso vivo; no consulta dependencias |
| Core readiness | `GET /health/operational` | PostgreSQL/modelo local/gates del núcleo |
| Chat | `GET /health/llm`, `GET /api/v1/chat/health` | proveedor + RAG + módulo |
| Proveedor | `GET /api/v1/chat/health/provider` | disponibilidad e identidad sanitizadas |
| RAG | `GET /api/v1/chat/health/rag` | Chroma, colección e índice requeridos |

Matriz normativa:

| Escenario | `core_ready` | `chat_ready` | `status` |
| --- | --- | --- | --- |
| proveedor apagado/inaccesible | `true` | `false` | `degraded` |
| proveedor válido y RAG válido | `true` | `true` | `ok` |
| `/api/ps` no responde, identidad válida | `true` | `true` | `ok` |
| identidad/digest/cuantización no coinciden | `true` | `false` | `degraded` |
| RAG requerido no disponible | `true` | `false` | `degraded` |
| PostgreSQL no disponible | `false` | `false` | `fail` |

### Semántica normativa de RAG requerido

Cuando `RAG_ENABLED=true`, RAG es obligatorio para `chat_ready`, pero no para
`core_ready`. Si Chroma, la colección activa o el índice validado no están
listos:

- el núcleo, autenticación, datos e historial siguen disponibles;
- el frontend no inicia una generación nueva;
- las rutas clínicas del caso de uso continúan fallando cerradas ante evidencia
  insuficiente;
- no se selecciona silenciosamente una colección anterior;
- no se muta el puntero RAG ni la colección.

Cuando `RAG_ENABLED=false`, `rag_ready=true` significa que la dependencia no es
requerida, no que exista un índice disponible.

## Contrato público de errores

Los códigos específicos del adaptador se normalizan antes de salir por HTTP,
incluido el generador SSE real, health o historial:

```text
LLM_PROVIDER_CONNECT_TIMEOUT
LLM_PROVIDER_READ_TIMEOUT
LLM_PROVIDER_OVERLOADED
LLM_PROVIDER_UNAVAILABLE
LLM_PROVIDER_INVALID_RESPONSE
LLM_PROVIDER_IDENTITY_UNVERIFIED
LLM_PROVIDER_MODEL_MISMATCH
LLM_PROVIDER_DIGEST_MISMATCH
LLM_PROVIDER_QUANTIZATION_MISMATCH
LLM_PROVIDER_REVISION_MISMATCH
```

La ausencia temporal devuelve 503 con `retryable=true`,
`recovery_action=retry_same_turn`, `request_id` y `retry_after_ms`. Los mensajes
públicos usan “asistente” o “proveedor LLM”; Ollama permanece como detalle del
adaptador/composición. Los códigos históricos del proveedor se traducen al
leerlos sin reescribir registros existentes.

## Contrato frontend

- consulta `GET /api/v1/chat/health` cada 15 segundos;
- no usa reintentos internos adicionales ni sondea en background;
- vuelve a consultar al recuperar foco y después de un 503 del proveedor;
- el estado se aísla por usuario en la cache;
- un probe fallido falla cerrado para generación;
- deshabilita textarea, envío, sugerencias y reintento, pero conserva historial,
  contexto y navegación;
- presenta un aviso estable sin IP, puerto, modelo interno o nombre de
  infraestructura;
- se rehabilita automáticamente tras un probe válido, sin recargar ni limpiar
  la conversación.

El intervalo de 1 segundo de `playwright.config.ts` existe solo en el servidor
E2E mediante `VITE_CHAT_AVAILABILITY_POLL_MS`; el build normal conserva 15
segundos.

## Validaciones

La evidencia completa está en `09-test-evidence.md`. Resultado final:

- Python 3.11.15: `924 passed`, `1 skipped`, `1 warning`, `4 subtests passed`;
- `llm_chat`: `608 passed`, `1 skipped`, `1 warning`;
- Ruff completo: aprobado;
- frontend: `108 passed`, Biome/TypeScript/build aprobados;
- dashboard E2E: `22 passed`, incluida recuperación por polling;
- Compose: local, producción y GPU válidos e inalterados.

## Riesgos pendientes

1. **ALTO — validación real GPU pendiente:** drivers, toolkit, modelo, digest,
   cuantización, persistencia e inferencia L4 siguen `NO VERIFICADO`; Etapa 6.
2. **ALTO — red privada pendiente:** el contrato no demuestra todavía que
   `11434` sea accesible solo desde producción; Etapa 7.
3. **ALTO — workflow legado:** CI/CD todavía no consume estos gates ni los
   artefactos inmutables; Etapa 8.
4. **MEDIO — costo de probes:** cada cliente activo consulta cada 15 segundos y
   el backend inspecciona proveedor y RAG. Es deliberadamente acotado, pero
   deberá observarse antes de escalar; una cache corta puede añadirse si las
   métricas lo justifican.
5. **MEDIO — compatibilidad temporal:** `llm_ready` continúa como alias de
   `provider_ready` para consumidores anteriores.
6. **BAJO — bundle grande:** Vite mantiene el warning preexistente del chunk de
   mapas superior a 500 kB; no está relacionado con disponibilidad del chat.

## Rollback

No hubo migración de datos, cambio de esquema ni estado runtime. El rollback es
un commit normal que revierta los commits funcionales y los cierres
documentales de la Etapa 5. Debe revertirse conjuntamente backend y frontend
para no dejar un cliente que espere endpoints/códigos ausentes.

No usar `git reset`, `git clean`, force push ni borrado de conversaciones. No
se requiere tocar GCP, Compose, volúmenes, modelos o colecciones RAG.

## Confirmación operativa

Todos los cambios funcionales son locales y versionados en la rama dedicada.
La única operación remota fue el push inicial de respaldo expresamente
autorizado; no creó PR, merge, run o despliegue. Producción, las VMs, GCP,
GitHub Actions, red, discos y datos persistentes no fueron modificados.
