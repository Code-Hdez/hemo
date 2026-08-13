# HemoVet — Sistema de Apoyo Diagnóstico Hematológico Canino.

CDSS para interpretación automatizada de hemogramas caninos. Extrae parámetros CBC desde PDFs, CSV e imágenes, aplica clasificación multilabel con XGBoost calibrado (PR-AUC macro 0.9577), y expone una API REST modular en `/api/v1` con persistencia PostgreSQL administrada por Alembic.

## Stack

| Capa | Tecnología |
|------|-----------|
| API | FastAPI, Pydantic v2 |
| ML | XGBoost, scikit-learn |
| Persistencia | PostgreSQL / SQLAlchemy 2 |
| Extracción | OpenRouter Gemma → OpenRouter Nemotron → Google Gemini → fallback local pdfplumber/pandas/Tesseract |
| RAG | Ollama, ChromaDB, FastEmbed |
| Frontend | React 18, Vite, TypeScript |

## Inicio rápido

```bash
cp .env.example .env
docker compose up --build
```

En local entra por `http://localhost:3000`. No uses `docker-compose.prod.yml`
para desarrollo en tu máquina: ese overlay está pensado para el servidor real y
usa Caddy con certificados públicos de Let's Encrypt.

El arranque inicial también indexa `knowledge_base/raw_md/` en Chroma para que el chat tenga contexto desde el primer `up`.

El contenedor ejecuta `alembic upgrade head` antes de iniciar `uvicorn app.main:app`. En instalaciones manuales:

```bash
cd backend
alembic -c alembic.ini upgrade head
uvicorn app.main:app --reload
```

Una base creada por el backend anterior debe auditarse y marcarse primero con `alembic stamp 0001_current_schema`; después se aplica `upgrade head`.

Con GPU NVIDIA para Ollama:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

## Despliegue y proxy

Hay tres topologías deliberadas:

- Desarrollo o servidor con proxy TLS externo: `docker compose up -d --build`. El frontend nginx publica `:3000` y el backend `:8000`; nginx enruta `/api/v1/*` y desactiva buffering para los streams.
- Proxy local opcional, sin TLS público: `docker compose -f docker-compose.yml -f docker-compose.local-caddy.yml up -d --build`. El overlay añade Caddy HTTP-only en `http://localhost:8080`; no usa `hemovet.app`, no expone `:443` y no solicita certificados ACME.
- Servidor productivo actual, con terminación HTTPS dentro de Docker: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`. El overlay añade Caddy, publica únicamente `:80/:443` y enruta `/api/v1/*` directamente al backend. Caddy no forma parte del compose base.

El despliegue de cada push a `main` usa la topología productiva. Antes de reemplazar servicios valida tests, Compose, Caddy y el corpus; después espera a Ollama, ejecuta la ingesta RAG, exige `chunk_count > 0` y prueba login, cookie HttpOnly, SSE con fuentes y `/auth/me` después del chat. No requiere comandos manuales en el servidor.

La topología productiva solo debe ejecutarse donde el DNS real de
`hemovet.app` y `www.hemovet.app` apunte a ese host y los puertos `80` y `443`
estén disponibles desde Internet. En una laptop o desktop local, Let's Encrypt
validará contra el DNS público, no contra Docker local, y Caddy no podrá emitir
el certificado correcto.

La fuente de configuración es el secret `PRODUCTION_ENV_B64`, generado desde un `.env` local validado y nunca versionado:

```bash
cp .env.production.example .env.production
# Completar valores <...> sin imprimirlos ni incorporarlos al historial.
python3 backend/scripts/validate_deploy_env.py .env.production
base64 -w0 .env.production | gh secret set PRODUCTION_ENV_B64
gh secret set PRODUCTION_SMOKE_EMAIL
gh secret set PRODUCTION_SMOKE_PASSWORD
```

La cuenta smoke debe usar credenciales dedicadas y sin permisos administrativos; el workflow la registra idempotentemente si todavía no existe. También deben existir `GCP_HOST`, `GCP_USER` y `GCP_SSH_KEY` (nombres históricos de los secrets SSH). El workflow migra una sola vez el contenedor Caddy antiguo no administrado por Compose y conserva rollback durante la validación.

Para un host con Cloudflare, balanceador o nginx externo, no se debe aplicar `docker-compose.prod.yml`; el proxy externo debe conservar `Cookie`, `Authorization`, `X-Forwarded-Proto`, `X-Forwarded-Host` y desactivar buffering para `/api/v1/chat/stream`.

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

La suite Playwright completa también existe (`npm run test:e2e`), pero contiene pruebas visuales y del tour ajenas al contrato crítico de despliegue. CI ejecuta de forma bloqueante las regresiones de sesión del chat; el smoke productivo valida el flujo real completo.

El perfil temporal `docker-compose.qa.yml` crea PostgreSQL aislado y publica el frontend en el puerto `13000`. Omite dependencias ML/OCR locales pesadas; el endpoint ML debe responder con indisponibilidad controlada en ese perfil, mientras que los artefactos reales se validan por sus checksums y pruebas unitarias.

```bash
docker compose -p hemovet-qa -f docker-compose.yml -f docker-compose.qa.yml up -d --build db backend frontend
cd frontend_4 && npm exec -- playwright test -c playwright.real.config.ts
docker compose -p hemovet-qa -f ../docker-compose.yml -f ../docker-compose.qa.yml down -v --remove-orphans
```

## Variables de entorno

| Variable | Descripción |
|----------|-------------|
| `DATABASE_URL` | Conexión PostgreSQL (omitir = modo memoria) |
| `SECRET_KEY` | Clave de firma JWT (**obligatoria en producción**) |
| `OPENROUTER_API_KEY` | API de OpenRouter para extracción primaria rápida |
| `GEMINI_API_KEY` | API de Google Gemini usada como segundo fallback remoto |
| `HEMOVET_ENABLE_LOCAL_ML` | Habilita inferencia ML local (default `1`) |
| `CORS_ORIGINS` | Orígenes permitidos, coma-separados (default `*`) |
| `ADMIN_EMAILS` | Correos con acceso al panel técnico |
| `OLLAMA_AUTO_PULL` | Descarga/exige el modelo Ollama durante el arranque (`0` local, `1` producción) |
| `RAG_ALLOW_TEST_DOCUMENTS` | Permite corpus de prueba (`0` en producción) |

El backend usa la cookie HttpOnly `hemovet_session` como mecanismo principal del navegador y conserva `Authorization: Bearer` para clientes API. Todos los requests del frontend incluyen credenciales. Un 401 aislado del stream revalida `/auth/me`; solo una sesión confirmada como inválida dispara logout.

## Notebooks

| Notebook | Contenido |
|----------|-----------|
| `01_extraccion_hemogramas_NUEVO.ipynb` | ETL: extracción de PDFs IDEXX, integración DAP, deduplicación y QA |
| `02a_baseline_local.ipynb` | EDA y modelos baseline multilabel |
| `02b_pipeline_final.ipynb` | Pipeline XGBoost calibrado, ablation study, evaluación final |

## Modelo

XGBoost multilabel v3 — 7 etiquetas predictivas + 2 basadas en regla, 43 features (analitos CBC, flags clínicos, ratios hematológicos, reticulocitos). Calibración Platt scaling por etiqueta.
