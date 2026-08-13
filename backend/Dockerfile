FROM python:3.11-slim@sha256:c20888b6acdd1e63e1c433a185bf3ad162c0288fe484616ce062e0d28add2900

WORKDIR /app

# Perfil completo por defecto. Los build args permiten desactivar ML local u
# OCR local en imagenes livianas de desarrollo cuando sea necesario.
ARG INSTALL_LOCAL_ML=1
ARG INSTALL_LOCAL_EXTRACTION=1

RUN if [ "$INSTALL_LOCAL_EXTRACTION" = "1" ]; then \
      apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng \
      && rm -rf /var/lib/apt/lists/*; \
    fi

RUN addgroup --system --gid 10001 hemovet \
    && adduser --system --uid 10001 --ingroup hemovet --home /app hemovet

# Instalar dependencias Python
COPY backend/requirements.txt ./requirements.txt
COPY backend/requirements.ml.txt ./requirements.ml.txt
COPY backend/requirements.local-extraction.txt ./requirements.local-extraction.txt
RUN pip install --no-cache-dir --timeout=120 -r requirements.txt \
    && if [ "$INSTALL_LOCAL_ML" = "1" ]; then pip install --no-cache-dir --timeout=120 -r requirements.ml.txt; fi \
    && if [ "$INSTALL_LOCAL_EXTRACTION" = "1" ]; then pip install --no-cache-dir --timeout=120 -r requirements.local-extraction.txt; fi

# La revisión cambia en cada despliegue. Declararla después de las dependencias
# evita invalidar las capas costosas de Tesseract y Python al reconstruir código.
ARG HEMOVET_BUILD_REVISION=dev
ARG HEMOVET_BUILD_CREATED=unknown
ARG HEMOVET_SOURCE_URL=https://github.com/xPshycho/hemogramas-proyectoICC
ENV HEMOVET_BUILD_REVISION=${HEMOVET_BUILD_REVISION}

LABEL org.opencontainers.image.title="HemoVet backend" \
      org.opencontainers.image.description="FastAPI application runtime for HemoVet" \
      org.opencontainers.image.source="${HEMOVET_SOURCE_URL}" \
      org.opencontainers.image.revision="${HEMOVET_BUILD_REVISION}" \
      org.opencontainers.image.created="${HEMOVET_BUILD_CREATED}"

# Copiar solo el codigo del backend (modelos y datos se montan como volumenes)
COPY --chown=hemovet:hemovet backend/ ./backend/
COPY --chown=hemovet:hemovet shared/ ./shared/

# Named volumes inherit these mount-point permissions on first creation.
RUN mkdir -p /app/media /app/.cache/fastembed \
    && chown -R hemovet:hemovet /app/media /app/.cache /app/backend

WORKDIR /app/backend

USER hemovet

EXPOSE 8000

CMD ["sh", "-c", "alembic -c alembic.ini upgrade head && python -m app.db.bootstrap_admins && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${BACKEND_WEB_CONCURRENCY:-1}"]
