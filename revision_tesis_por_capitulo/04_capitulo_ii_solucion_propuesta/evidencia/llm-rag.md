# Módulo LLM + RAG de HemoVet

El pipeline usa únicamente documentos Markdown curados y aprobados. Un corpus vacío o sin chunks útiles bloquea la ingesta y el despliegue antes de servir tráfico.

## Arquitectura

El módulo sigue una separación por capas:

```text
app/modules/llm_chat/
├── api/                 # Contratos Pydantic, dependencias, router y SSE
├── application/         # Casos de uso y servicios de orquestación
├── domain/              # Entidades, valores, puertos y excepciones
├── infrastructure/      # ChromaDB, FastEmbed, Ollama, Markdown y SQLAlchemy
├── prompts/             # Prompt de sistema y plantilla RAG versionables
└── composition.py       # Clientes reutilizables creados durante lifespan
```

La ingesta es un proceso offline. Una petición de chat nunca lee Markdown, divide documentos ni vuelve a indexar. FastAPI reutiliza una colección Chroma, un modelo de embeddings y un cliente HTTP hacia Ollama durante toda la vida del proceso.

## Flujo de una consulta

1. FastAPI valida la misma autenticación que el resto de la aplicación: cookie HttpOnly `hemovet_session` para el navegador o bearer JWT para clientes API.
2. Se verifica que la conversación y, si aplica, el análisis pertenezcan al usuario.
3. La política determinista clasifica solicitudes de dosis, medicamentos, tratamientos, urgencias, decisiones clínicas o diagnóstico definitivo.
4. Una solicitud no permitida recibe una respuesta segura sin consultar Chroma ni Ollama.
5. Para una solicitud permitida se genera el embedding de consulta y se recuperan candidatos caninos aprobados o de prueba.
6. Se filtran por relevancia, se limita la repetición por fuente y se construye un prompt con hechos, contexto y referencias `[S1]`, `[S2]`, etc.
7. Ollama genera mediante su API compatible con OpenAI. La concurrencia está limitada globalmente.
8. Un validador de salida rechaza dosis, instrucciones clínicas, diagnósticos definitivos y referencias inexistentes.
9. Pregunta, respuesta, fuentes, latencia y uso de tokens se persisten. El razonamiento interno no se almacena ni se devuelve.

Si Chroma no aporta evidencia suficiente, el LLM no se invoca y se responde: “Con la información disponible no puedo confirmarlo”.

## Endpoints

Los endpoints de usuario aceptan la cookie HttpOnly emitida por `/auth/login` o `Authorization: Bearer <JWT>`. El navegador usa la cookie con `credentials: "include"`; no mantiene el JWT en JavaScript en producción. `GET /api/v1/chat/health` es un healthcheck sanitizado y público.

- `POST /api/v1/chat`: respuesta JSON completa.
- `POST /api/v1/chat/stream`: SSE con eventos `status`, `delta`, `sources`, `done` o `error`. La salida se entrega después de validarla.
- `GET /api/v1/chat/conversations/{id}/messages?limit=20&offset=0`: historial propio paginado.
- `GET /api/v1/chat/health`: estado sanitizado de Ollama, Chroma, colección, embeddings, `rag_ready` y `chunk_count`.

Ejemplo de solicitud general:

```json
{
  "client_message_id": "f02da308-d383-4b55-8e7e-81bb238e03da",
  "conversation_id": null,
  "message": "¿Qué función tienen las plaquetas?",
  "context_scope": "general",
  "analysis_id": null,
  "options": { "thinking": false }
}
```

Para usar un hemograma, `context_scope` debe ser `uploaded_analysis` o `historical_analysis` y `analysis_id` es obligatorio. El backend extrae únicamente hechos clínicos del análisis; no incluye nombre, dirección u otros datos de la mascota en el prompt.

Respuesta abreviada:

```json
{
  "conversation_id": "...",
  "message_id": "...",
  "answer": "... [S1].",
  "scope": "general",
  "case_facts": [],
  "sources": [
    {
      "id": "...",
      "source_id": "hemovet-test-cbc",
      "title": "Hemograma canino — documento de prueba",
      "heading_path": "Plaquetas",
      "source_path": "hemograma_canino_prueba.md",
      "score": 0.82
    }
  ],
  "warnings": ["La respuesta es educativa y no sustituye una evaluación veterinaria."],
  "safety_action": "allow",
  "model": "qwen3:4b",
  "usage": { "prompt_tokens": 120, "completion_tokens": 45 },
  "duration_ms": 900,
  "finish_reason": "stop"
}
```

## Configuración

Las variables están documentadas en `.env.example` y `.env.production.example`. Las principales son:

- Ollama: `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_API_KEY` opcional, `OLLAMA_NUM_PREDICT`, `OLLAMA_TEMPERATURE`.
- Chroma: `CHROMA_HOST`, `CHROMA_PORT`, `CHROMA_SSL`, `CHROMA_TENANT`, `CHROMA_DATABASE`.
- RAG: `RAG_SOURCE_DIR`, `RAG_COLLECTION_NAME`, `RAG_EMBEDDING_MODEL`, `RAG_CHUNK_SIZE_WORDS`, `RAG_CHUNK_OVERLAP_WORDS`, `RAG_FETCH_K`, `RAG_TOP_K`, `RAG_MIN_RELEVANCE_SCORE`.
- Chat: `CHAT_HISTORY_LIMIT`, `CHAT_TOTAL_TIMEOUT_SECONDS`, `CHAT_MAX_CONCURRENT_GENERATIONS`.

No se registran valores secretos ni se incluyen en healthchecks. En producción deben inyectarse desde el gestor de secretos del entorno, no incorporarse a la imagen ni al repositorio.

## Contrato Markdown e ingesta

Los documentos viven en `knowledge_base/raw_md/` y requieren frontmatter:

```markdown
---
source_id: identificador-estable
title: Título visible
language: es
species: canine
version: "1"
status: approved
---

# Encabezado

Contenido curado.
```

`status: test` solo se indexa cuando `RAG_ALLOW_TEST_DOCUMENTS=1` o se usa `--allow-test-documents`. Producción mantiene esa variable en `0`. Los IDs de chunk incluyen el hash del documento completo; por eso un cambio de frontmatter como `test` → `approved` fuerza la actualización de metadatos en Chroma. Una nueva ejecución omite fuentes idénticas, actualiza cambios y elimina chunks obsoletos. `--prune` elimina fuentes que ya no existen; `--reset` reconstruye la colección. Si no hay documentos aprobados o el procesamiento produce cero chunks, incluso `--dry-run` falla antes de modificar la colección existente.

Validación manual desde la raíz del proyecto:

```bash
docker compose run --rm rag_ingest python scripts/ingest_rag.py index --dry-run
docker compose run --rm rag_ingest python scripts/ingest_rag.py index --prune
```

La primera ejecución de FastEmbed descarga el modelo configurado y lo conserva en `embedding-cache`. Chroma persiste en `chroma-data`. `ollama_setup` comprueba el modelo y, con `OLLAMA_AUTO_PULL=1`, lo descarga en el volumen persistente antes de permitir que arranque el backend.

## Arranque y prueba manual

```bash
cp .env.example .env
docker compose up --build -d
docker compose ps
docker compose logs rag_ingest --tail=100
docker compose logs ollama_setup --tail=100
curl -fsS http://localhost:8000/health/operational
curl -fsS http://localhost:8000/api/v1/chat/health
```

El orden de arranque es estricto: Chroma y PostgreSQL saludables → ingesta RAG terminada → modelo Ollama disponible → backend → frontend. Alembic se ejecuta en el entrypoint del backend. En producción se usa además el overlay Caddy documentado en el README.

Después:

1. Confirmar que `/health/operational` responde `ok`, `rag_ready: true` y `chunk_count > 0`.
2. Confirmar que `/api/v1/chat/health` indica `chroma_ready`, `llm_ready`, `rag_ready` y al menos un chunk.
3. Iniciar sesión en React y preguntar un concepto general.
4. Abrir un análisis y usar “Preguntar al asistente”; verificar que la URL contiene el `analysis_id`.
5. Probar una pregunta de dosis o tratamiento y verificar `safety_action` de rechazo sin fuentes.
6. Probar una consulta sin evidencia y verificar que no inventa una respuesta.
7. Repetir el mismo `client_message_id` y verificar idempotencia.
8. Ejecutar nuevamente la ingesta y verificar que la fuente queda omitida, sin duplicados.

El proxy de producción envía `/api/v1/chat/stream` directamente a FastAPI con flush inmediato. nginx mantiene `proxy_buffering off`, `proxy_request_buffering off`, `proxy_cache off`, `Connection ""` y reenvía `Cookie` y `Authorization` para la topología sin Caddy.

## Verificación automatizada

```bash
cd backend
python -m pytest tests -q

cd ../frontend_4
npm run check
npm test -- --run
npm run build
```
