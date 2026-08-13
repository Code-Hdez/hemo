# Arquitectura backend HemoVet

## Estructura

`app/main.py` es el entrypoint ASGI y la API funcional se publica únicamente bajo `/api/v1`.
Los healthchecks permanecen en `/health*`. Los dominios viven en `app/modules`; configuración,
seguridad, sesiones y excepciones viven en `app/core`, `app/db` y `app/dependencies`.

Los módulos actuales son: auth, users, pets, pet_history, hematology, ml,
population_surveillance, maps, llm_chat, gemini_extraction, files y dashboard. Los modelos
SQLAlchemy pertenecen al módulo dueño del dato y `app/db/base.py` los registra para Alembic.

La arquitectura, contratos, ingesta y operación del chat se documentan en
[`llm-rag.md`](llm-rag.md).

## Responsabilidades

- Router: contrato HTTP y dependencias FastAPI.
- Schema: request/response Pydantic.
- Service: reglas, orquestación y transacciones.
- Repository: consultas SQLAlchemy.
- Model: persistencia del dominio.
- Cliente: integración técnica con Gemini u Ollama.

No existe fallback runtime en memoria. `DATABASE_URL` y un `SECRET_KEY` de al menos 32
caracteres son obligatorios fuera de tests. SQLite en memoria se usa únicamente en tests con
configuración explícita.

## Migraciones y administradores

```bash
cd backend
alembic -c alembic.ini upgrade head
python -m app.db.bootstrap_admins
```

`users.role` es la fuente de verdad de autorización. `ADMIN_EMAILS` solo alimenta el comando
idempotente de bootstrap. La aplicación no ejecuta DDL durante startup.

## Pruebas

```bash
python -m pytest backend/tests -q
ruff check backend/app backend/tests
black --check backend/app backend/tests
mypy backend/app
```

En `frontend_4`: `npm run check`, `npm test`, `npm run build` y `npm run test:e2e`.
