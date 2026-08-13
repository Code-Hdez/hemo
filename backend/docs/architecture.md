# Arquitectura backend HemoVet

`app/main.py` es el entrypoint ASGI. La API funcional se publica bajo
`/api/v1`; los healthchecks de plataforma permanecen en `/health*`. Los dominios
viven en `app/modules`, mientras que configuración, autenticación, sesiones y
persistencia compartida viven en `app/core`, `app/dependencies` y `app/db`.

Los módulos actuales son auth, users, pets, pet_history, hematology, ml,
population_surveillance, maps, llm_chat, gemini_extraction, files y dashboard.
Cada modelo SQLAlchemy pertenece al módulo dueño del dato y `app/db/base.py` lo
registra para Alembic.

## Bounded context conversacional

El chat v2 está separado en capas explícitas:

| Capa | Responsabilidad |
| --- | --- |
| `api` | Autenticación, validación Pydantic, JSON/SSE y traducción de errores. |
| `application` | Enrutamiento del turno, memoria, resolución de referencias, prompt, recuperación y validación de salida. |
| `domain` | Contexto clínico tipado, políticas, entidades y puertos sin FastAPI, SQLAlchemy, Chroma ni HTTP. |
| `infrastructure` | Repositorios SQLAlchemy, Chroma/FastEmbed/BM25, catálogo documental y adaptadores de generación. |
| `composition.py` | Construcción y reutilización de clientes en el lifespan de FastAPI. |

El modelo no se carga dentro del proceso web. El adaptador seleccionado por
`CHAT_LLM_PROVIDER` llama por HTTP a Ollama o a un runtime compatible con OpenAI.
Esto permite cambiar infraestructura sin cambiar el caso de uso.

```text
POST /api/v1/chat[/stream]
  → autenticar y validar modo
  → cargar conversación propia + memoria híbrida
  → recuperar hemograma(s) autorizados desde PostgreSQL
  → resolver seguimiento e intención
  → construir hechos exactos y límites de seguridad de forma determinista
  → recuperar evidencia vectorial + BM25 cuando corresponde
  → encargar al LLM la redacción permitida y validar seguridad/coherencia
  → proyectar bibliografía y evidencia clínica pública mínima
  → persistir el turno, estado, uso y métricas
```

Los errores, autorización, selección, hechos numéricos y estados de turno son
deterministas. Las explicaciones, comparaciones narrativas y redirecciones
permitidas se redactan con el modelo. Las respuestas clínicas se almacenan
temporalmente hasta terminar la validación; SSE transporta el resultado
validado y los eventos de estado, no un borrador clínico sin revisar.

## Datos clínicos y autorización

El backend es la fuente de verdad. Un `analysis_id` o `pet_id` del cliente solo
sirve para localizar el recurso; el repositorio vuelve a consultar PostgreSQL y
comprueba `Analysis.user_id`, `Analysis.pet_id` y `Pet.owner_id` antes de crear el
contexto. Una consulta no autorizada se comporta como un recurso no disponible y
no revela si el identificador existe.

`analysis_parameters` guarda el nombre original y canónico, valor decimal,
unidad original/normalizada, intervalo de referencia, origen del intervalo,
flags registrados/derivados, confianza y procedencia. Los datos JSON legados se
mantienen como compatibilidad, pero el contexto v2 prioriza las filas
normalizadas. No se comparan series con unidades ausentes o incompatibles.

Los datos clínicos completos se usan para autorización, generación y validación,
pero no forman parte del DTO visible. `case_facts` permite únicamente
`parameter` y `value`; las filas legadas con rangos, flags, confianza o
procedencia se descartan en la frontera pública. El nombre `HemoVet` también se
normaliza antes de persistir, emitir por SSE o proyectar historial.

## Memoria y cambios de contexto

La conversación se persiste en `chat_sessions` y `chat_messages`. La memoria
combina una ventana de turnos recientes, un resumen acotado y estado estructurado
(tema, parámetro, mascota, hemograma y comparación activos). Los valores clínicos
no se memorizan como fuente de verdad: se vuelven a obtener de la base de datos
para cada turno contextual.

La clave de contexto separa chat general, hemograma seleccionado e historial de
una mascota. Cambiar de modo, mascota o análisis incrementa la revisión de
contexto; el cliente puede enviar `expected_context_revision` para detectar una
respuesta iniciada sobre una selección ya obsoleta. Las conversaciones expiran
según `CHAT_SESSION_TTL_SECONDS` y siempre están aisladas por usuario.

El cliente activo conserva en `sessionStorage` solo un marcador efímero de la
conversación actual para poder solicitar su eliminación. Cambiar de modo,
mascota o análisis, recargar o abandonar la pestaña limpia ese marcador y el
estado visible; al regresar, el cliente crea una conversación remota nueva con
el contexto autorizado. El transcript anterior no se restaura ni se transfiere
entre contextos o propietarios.

## Migraciones y administradores

```bash
cd backend
alembic -c alembic.ini upgrade head
python -m app.db.bootstrap_admins
```

La cadena conversacional y clínica se completa con estas revisiones:

- `0006_chat_context_memory`: sesiones, mensajes, memoria y revisión de contexto;
- `0007_analysis_parameters`: parámetros clínicos normalizados y procedencia;
- `0008_chat_turn_order`: orden determinista de turnos por revisión;
- `0009_chat_turn_state`: turnos canónicos e intentos auditables;
- `0010_chat_turn_leases`: idempotencia global, fingerprint de solicitud y leases;
- `0011_chat_context_snapshot`: fingerprint clínico y etapa de procesamiento.

La aplicación no ejecuta DDL desde código de negocio; la imagen Docker ejecuta
Alembic antes de iniciar Uvicorn.

`users.role` es la fuente de verdad de autorización. `ADMIN_EMAILS` alimenta
únicamente el bootstrap idempotente.

## Retención del chat

```bash
cd backend
python -m app.db.retention --dry-run   # cuenta sin tocar nada
python -m app.db.retention
```

Barrido periódico, nunca automático al arrancar. Cierra (`status='expired'`) las
conversaciones cuyo `expires_at` ya pasó y borra la telemetría vieja
(`chat_turn_attempts` terminados, `retrieval_events`). No borra transcripciones:
`chat_messages` y `chat_turns` cascadean desde `chat_sessions`, así que eliminar
una conversación destruiría su historial.

## Verificación

```bash
APP_ENV=test \
DATABASE_URL=sqlite+pysqlite:///:memory: \
SECRET_KEY=test-secret-key-with-at-least-32-characters \
HEMOVET_ENABLE_LOCAL_ML=0 \
HEMOVET_ENABLE_LOCAL_EXTRACTION=0 \
PYTHONPATH=backend \
python -m pytest backend/tests -q

cd frontend_4
npm test
npm run check
npm run build
```

El contrato, operación, reindexación y evaluación del asistente se documentan en
[`llm-rag.md`](llm-rag.md).
