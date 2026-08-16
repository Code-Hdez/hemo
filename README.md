# HemoVet — Sistema de Apoyo Diagnóstico Hematológico Canino.

CDSS para interpretación automatizada de hemogramas caninos. Extrae parámetros CBC desde PDFs, CSV e imágenes, aplica clasificación multilabel con XGBoost (PR-AUC macro final 0.9529), y expone una API REST modular en `/api/v1` con persistencia PostgreSQL administrada por Alembic

## Stack

| Capa | Tecnología |
|------|-----------|
| API | FastAPI, Pydantic v2 |
| ML | XGBoost, scikit-learn |
| Persistencia | PostgreSQL / SQLAlchemy 2 |
| Extracción | OpenRouter Gemma → OpenRouter Nemotron → Google Gemini → fallback local pdfplumber/pandas/Tesseract |
| Asistente | Qwen3 4B por Ollama o un runtime externo compatible con OpenAI |
| RAG | ChromaDB, FastEmbed, BM25 y catálogo bibliográfico curado |
| Frontend | React 19, Vite, TypeScript |

El contrato de desarrollo y CI es Python 3.11 y Node.js 22; los archivos
`.python-version` y `.nvmrc` permiten seleccionar esas versiones sin depender
de la versión global de la máquina.

## Inicio rápido

```bash
cp .env.example .env
docker compose up --build
```

En local entra por `http://localhost:3000`. No uses `docker-compose.prod.yml`
para desarrollo en tu máquina: ese overlay está pensado para el servidor real y
usa Caddy con certificados públicos de Let's Encrypt.

El arranque inicial aplica las migraciones, verifica `qwen3:4b-instruct-2507-q4_K_M` en Ollama e
indexa la ruta configurada por `RAG_SOURCE_DIR`. El checkout versionado usa
`knowledge_base/expert_review/approved`, la colección
`hemovet_canine_hematology_v2` y el catálogo
`knowledge_base/manifests/sources_manifest.json`. La primera ejecución puede
tardar mientras descarga el modelo y los embeddings.

El nombre histórico de esa carpeta no acredita revisión veterinaria
independiente. El corpus conserva metadatos de revisión provisional y el
contrato de la colección activa usa chunks de 90 palabras con 15 palabras de
solapamiento. Cambiar esa segmentación requiere reindexar de forma controlada.

Una colección creada por RAG v1 no es compatible con la metadata ni con los IDs
de chunks de v2. Una colección activa no se borra ni se reconstruye en vivo. Para
migrar una instalación existente se crea una candidata inmutable y se cambia el
puntero solo después de validarla:

```bash
docker compose run --rm rag_ingest \
  python scripts/ingest_rag.py index --dry-run
docker compose run --rm rag_ingest \
  python scripts/ingest_rag.py index \
  --collection hemovet_canine_hematology_v2 --stage --prune
```

El segundo comando imprime el `RAG_COLLECTION_NAME` promovible. Debe copiarse a
`.env` antes de reiniciar backend. El procedimiento productivo completo y el
rollback están en [backend/docs/rag-index-promotion.md](backend/docs/rag-index-promotion.md).

El contenedor ejecuta `alembic upgrade head` antes de iniciar `uvicorn app.main:app`. En instalaciones manuales:

```bash
cd backend
alembic -c alembic.ini upgrade head
uvicorn app.main:app --reload
```

Una base creada por el backend anterior debe auditarse y marcarse primero con `alembic stamp 0001_current_schema`; después se aplica `upgrade head`.

El runtime NVIDIA dedicado se valida como un stack autónomo. No debe combinarse
con el Compose de la aplicación:

```bash
docker compose --env-file deploy/gpu/compose.env.example \
  -f docker-compose.gpu.yml config
```

Su arranque queda reservado al runbook reconciliador y a la puesta en servicio
de etapas posteriores; validar el archivo no enciende la VM GPU.

## Despliegue y proxy

Hay tres topologías deliberadas:

- Desarrollo local: `docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build`. `.env.example` declara esa misma combinación mediante `COMPOSE_FILE`. El overlay local es el único que añade Ollama; el frontend nginx publica `:3000` y el backend `:8000`.
- Proxy local opcional, sin TLS público: `docker compose -f docker-compose.yml -f docker-compose.local.yml -f docker-compose.local-caddy.yml up -d --build`. Caddy queda en `http://localhost:8080`; no usa `hemovet.app`, no expone `:443` y no solicita certificados ACME.
- Servidor productivo con terminación HTTPS dentro de Docker: la configuración soportada es exclusivamente `docker-compose.yml` + `docker-compose.prod.yml`. Consume backend y frontend por digest, publica solo Caddy en `:80/:443` y no contiene `ollama` ni `ollama_setup`. `OLLAMA_BASE_URL` apunta al endpoint privado de la VM GPU.
- VM GPU: `docker-compose.gpu.yml` se ejecuta solo y contiene exclusivamente `ollama`, `ollama_setup`, la reserva NVIDIA y el volumen persistente de modelos.

La Etapa 4 define estas topologías, pero todavía no autoriza ni integra el
despliegue inmutable en GitHub Actions. Esa integración corresponde a la Etapa
8. Hasta entonces no debe fusionarse esta rama esperando que el workflow
productivo adopte por sí solo las nuevas referencias OCI.

Ese healthcheck no constituye una prueba conversacional autenticada. Antes de
una defensa o release se debe ejecutar el evaluador con un usuario, una mascota
y hemogramas reales autorizados; el procedimiento reproducible está en
[`backend/docs/llm-rag.md`](backend/docs/llm-rag.md).
El mapa de arquitectura, cambios, evidencia, compatibilidad y pendientes del
endurecimiento está en
[`backend/docs/llm-production-hardening-report.md`](backend/docs/llm-production-hardening-report.md).
La vista end-to-end (topología GCP real, diagrama de flujo LLM actualizado y
relación con el frontend activo `frontend_4`) está en
[`docs/llm_architecture.md`](docs/llm_architecture.md).

La topología productiva solo debe ejecutarse donde el DNS real de
`hemovet.app` y `www.hemovet.app` apunte a ese host y los puertos `80` y `443`
estén disponibles desde Internet. En una laptop o desktop local, Let's Encrypt
validará contra el DNS público, no contra Docker local, y Caddy no podrá emitir
el certificado correcto.

La fuente de configuración es el secret `PRODUCTION_ENV_B64`, generado desde
`.env.production`, validado localmente y nunca versionado:

```bash
cp .env.production.example .env.production
# Completar valores <...> sin imprimirlos ni incorporarlos al historial.
python3 backend/scripts/validate_deploy_env.py .env.production
base64 -w0 .env.production | gh secret set PRODUCTION_ENV_B64
```

Para un despliegue manual en el servidor, Compose debe recibir ese mismo archivo
validado bajo el nombre runtime `.env`; usar solamente `--env-file` no sustituye
los bloques `env_file: .env` de `backend` y `rag_ingest`:

```bash
python3 backend/scripts/validate_deploy_env.py .env.production
install -m 600 .env.production .env
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-build
```

El `.env` del equipo de desarrollo conserva `APP_ENV=development` y valores
locales. El `.env` instalado en el servidor es una copia protegida del perfil
productivo; no se debe reutilizar el archivo de desarrollo en ese host.

También deben existir `GCP_HOST`, `GCP_USER` y `GCP_SSH_KEY` (nombres
históricos de los secrets SSH). Si se automatiza una prueba autenticada, debe
usar una cuenta dedicada sin permisos administrativos; el workflow actual no
crea esa cuenta ni almacena sus credenciales. El workflow migra una sola vez el
contenedor Caddy antiguo no administrado por Compose y conserva rollback durante
la validación.

Para un host con Cloudflare, balanceador o nginx externo, no se debe aplicar `docker-compose.prod.yml`; el proxy externo debe conservar `Cookie`, `Authorization`, `X-Forwarded-Proto`, `X-Forwarded-Host` y desactivar buffering para `/api/v1/chat/stream`.

Desactivar el buffering del proxy no significa exponer borradores clínicos. El
backend acumula las respuestas que usan datos del paciente hasta completar su
validación y entonces las publica por SSE. Los eventos de estado y las rutas de
bajo riesgo sí pueden emitirse mientras se procesa el turno.

Para volver de una configuración productiva a local, conserva los secretos fuera
del repo en `.env.production` y recrea `.env` desde `.env.example` antes de
levantar el stack local. `.env.example` documenta valores seguros para
`localhost`; `.env.production.example` documenta los valores del servidor real.

## Validación QA

Las pruebas backend se ejecutan con SQLite aislado y sin cargar el modelo local:

```bash
APP_ENV=test DATABASE_URL=sqlite+pysqlite:///:memory: \
SECRET_KEY=test-secret-key-with-at-least-32-characters \
HEMOVET_ENABLE_LOCAL_ML=0 PYTHONPATH=backend \
python -m pytest backend/tests -q
```

Para el frontend:

```bash
cd frontend_4
npm test
npm run check
npm run build
npm run test:e2e -- --project=desktop-1440 -g "un 401"
```

La suite Playwright completa también existe (`npm run test:e2e`), pero contiene
pruebas visuales y del tour ajenas al contrato crítico de despliegue. CI ejecuta
las suites backend/frontend, valida el corpus y comprueba los archivos de
despliegue. El workflow productivo comprueba salud y disponibilidad; la calidad
de respuestas se valida por separado con el evaluador autenticado.

El perfil temporal `docker-compose.qa.yml` crea PostgreSQL aislado y publica el frontend en el puerto `13000`. Omite dependencias ML/OCR locales pesadas; el endpoint ML debe responder con indisponibilidad controlada en ese perfil, mientras que los artefactos reales se validan por sus checksums y pruebas unitarias.

```bash
docker compose -p hemovet-qa -f docker-compose.yml -f docker-compose.qa.yml up -d --build db backend frontend
cd frontend_4 && npm exec -- playwright test -c playwright.real.config.ts
docker compose -p hemovet-qa -f ../docker-compose.yml -f ../docker-compose.qa.yml down -v --remove-orphans
```

## Datos de demostración

[`scripts/seed_demo_data.py`](scripts/seed_demo_data.py) crea usuarios
`@hemovet.demo`, mascotas y análisis a partir de los PDFs locales de `test/`
mediante la API pública. Las mascotas se distribuyen entre Santo Domingo,
Santiago y La Vega para producir agregados del mapa sin rebajar sus umbrales de
privacidad:

```bash
python scripts/seed_demo_data.py --api http://localhost:8000
```

El seed contiene credenciales conocidas, reutiliza usuarios y mascotas por
correo/nombre, crea una señal demo reciente para tres mascotas por zona y omite
los PDFs ya presentes mediante nombres anónimos derivados de su contenido. Es
exclusivo de desarrollo y no debe ejecutarse contra producción ni con datos
reales. Los documentos con valores fuera del contrato clínico quedan reportados
como cuarentena sin relajar la validación. `--limit N` permite una carga breve
sin afectar el baseline del mapa.

## Variables de entorno

| Variable | Descripción |
|----------|-------------|
| `DATABASE_URL` | Conexión SQLAlchemy obligatoria; usar PostgreSQL en despliegue y una URL SQLite explícita en pruebas |
| `SECRET_KEY` | Clave de firma JWT (**obligatoria en producción**) |
| `HEMOVET_BUILD_REVISION` | Revisión visible en `/health/operational`; definirla al construir/desplegar |
| `OPENROUTER_API_KEY` | API de OpenRouter para extracción primaria rápida |
| `GEMINI_API_KEY` | API de Google Gemini usada como segundo fallback remoto |
| `HEMOVET_ENABLE_LOCAL_ML` | Habilita inferencia ML local (default `1`) |
| `CORS_ORIGINS` | Orígenes permitidos, coma-separados (default `*`) |
| `ADMIN_EMAILS` | Correos con acceso al panel técnico |
| `CHAT_LLM_PROVIDER` | Adaptador de generación: `ollama` u `openai_compatible` |
| `OLLAMA_MODEL` | Modelo local no razonador (default `qwen3:4b-instruct-2507-q4_K_M`) |
| `OLLAMA_AUTO_PULL` | Descarga/exige el modelo Ollama durante el arranque (`1` recomendado para secrets/deploy autónomo) |
| `OLLAMA_KEEP_ALIVE` | Mantiene el modelo cargado entre requests (default `30m`) |
| `OLLAMA_CONTEXT_LENGTH` | Techo global del servidor Ollama (default `4096`); cada perfil de chat usa efectivamente `2048`, `3072` o `4096` |
| `OLLAMA_NUM_PREDICT` | Presupuesto máximo de generación visible (default `384`) |
| `OLLAMA_FLASH_ATTENTION` / `OLLAMA_KV_CACHE_TYPE` | Optimización de atención y tipo de caché KV del servidor Ollama; usar `1`/`q8_0` tras validar la GPU |
| `OLLAMA_THINK` | Canal privado para runtimes razonadores opcionales; desactivado para el modelo Instruct predeterminado (default `0`) |
| `OLLAMA_TOP_P` / `OLLAMA_TOP_K` / `OLLAMA_REPEAT_PENALTY` | Opciones reales de generación enviadas a Ollama por request |
| `OLLAMA_WARMUP_ENABLED` | Precalienta el modelo al iniciar; producción falla cerrada si el runtime o el artefacto esperado no pueden verificarse |
| `OLLAMA_EXPECTED_MODEL_DIGEST` / `OLLAMA_EXPECTED_QUANTIZATION` | Identidad exacta exigida al runtime Ollama; producción no acepta una etiqueta coincidente con pesos o cuantización distintos |
| `OPENAI_COMPATIBLE_BASE_URL` / `OPENAI_COMPATIBLE_MODEL` | Runtime externo compatible con `/v1/chat/completions`; la clave es opcional según el proveedor |
| `RAG_ALLOW_TEST_DOCUMENTS` | Permite corpus de prueba (`0` en producción) |
| `RAG_ALLOW_AI_PROVISIONAL` | Permite contenido provisional no versionado (`0` por defecto) |
| `RAG_SOURCE_DIR` | Corpus versionado con estado de revisión trazable o ruta local sobreescrita; el nombre de la carpeta no acredita revisión veterinaria |
| `RAG_COLLECTION_NAME` / `RAG_SCHEMA_VERSION` | Puntero a una colección promovida `v2__<fingerprint>` y contrato de corpus; un cambio requiere staging, validación y promoción controlada |
| `RAG_SOURCE_MANIFEST` | Catálogo que convierte IDs internos en títulos, autores y ediciones legibles |
| `RAG_EMBEDDING_MODEL` / `RAG_EMBEDDING_DIMENSION` | Identidad del embedding v2 (`paraphrase-multilingual-MiniLM-L12-v2`, dimensión `384`) |
| `RAG_CHUNK_SIZE_WORDS` / `RAG_CHUNK_OVERLAP_WORDS` | Segmentación de la colección activa (`90`/`15`); modificarla exige reindexación |
| `RAG_TOP_K` / `RAG_MAX_CONTEXT_CHARS` | Controlan cuánta evidencia entra al prompt (`3` fuentes como máximo por defecto) y su presupuesto |
| `CHAT_HISTORY_LIMIT` / `CHAT_SUMMARY_MAX_CHARS` | Ventana reciente y resumen acumulativo de memoria en servidor |
| `CHAT_SESSION_TTL_SECONDS` | Vigencia y limpieza de conversaciones temporales en servidor (default `3600`) |
| `CHAT_REQUIRE_BROWSER_SESSION_ID` | Exige el UUID efímero de `sessionStorage` para crear, restaurar o modificar una conversación |
| `CHAT_MAX_CONCURRENT_GENERATIONS` | Concurrencia de generaciones LLM; mantener `1` hasta validar la capacidad de la GPU |
| `CHAT_DB_BLOCKING_MAX_CONCURRENCY` | Límite del executor que saca SQLAlchemy síncrono del event loop sin compartir una sesión ORM entre threads |
| `VETERINARY_PLACES_OVERPASS_URL` / `VETERINARY_PLACES_TIMEOUT_SECONDS` | Proveedor público y timeout de la búsqueda voluntaria de centros veterinarios desde la zona aproximada de la mascota |
| `OTEL_ENABLED` / `OTEL_EXPORTER_OTLP_ENDPOINT` | Activa trazas y métricas OTLP/HTTP hacia un collector privado |
| `OTEL_IDENTIFIER_HMAC_SECRET` | Secreto independiente usado para anonimizar identificadores en telemetría; obligatorio en producción |

El backend usa la cookie HttpOnly `hemovet_session` como mecanismo principal del navegador y conserva `Authorization: Bearer` para clientes API. Todos los requests del frontend incluyen credenciales. Un 401 aislado del stream revalida `/auth/me`; solo una sesión confirmada como inválida dispara logout. El frontend genera un UUID efímero y lo guarda exclusivamente en `sessionStorage`; además conserva por contexto solo IDs opacos necesarios para restaurar desde el backend durante esa misma sesión del navegador. La clave de aislamiento incluye sesión, modo, mascota y análisis, por lo que cambiar de contexto no mezcla historiales. Una recarga dentro de la misma sesión puede restaurar el transcript autorizado; cerrar el navegador y abrir una sesión nueva produce otro UUID y el backend rechaza reanudar la conversación anterior. Los mensajes y hechos clínicos no se guardan en el navegador y expiran en el backend según `CHAT_SESSION_TTL_SECONDS`.

## Notebooks

| Notebook | Contenido |
|----------|-----------|
| `01_extraccion_hemogramas_NUEVO.ipynb` | ETL: extracción de PDFs IDEXX, integración DAP, deduplicación y QA |
| `02a_baseline_local.ipynb` | EDA y modelos baseline multilabel |
| `02b_pipeline_final.ipynb` | Pipeline XGBoost calibrado, ablation study, evaluación final |

## Modelo

XGBoost multilabel v3 — 7 etiquetas predictivas + 2 basadas en regla, 43 features (analitos CBC, flags clínicos, ratios hematológicos, reticulocitos). Calibración Platt scaling por etiqueta.
