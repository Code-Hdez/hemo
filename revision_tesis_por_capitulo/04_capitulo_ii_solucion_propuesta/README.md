# 04 - Capitulo II - Solucion propuesta

## Problema actual

La solucion propuesta describe una version anterior del sistema. Debe actualizarse con el estado real del programa.

## Cambios que hacer

- Cambiar la descripcion de endpoints a la API actual bajo `/api/v1`.
- Actualizar stack:
  - FastAPI y Pydantic v2.
  - PostgreSQL y SQLAlchemy 2.
  - Alembic para migraciones.
  - React 18, Vite y TypeScript.
  - ChromaDB, FastEmbed y Ollama para RAG.
  - Docker Compose con overlays para GPU, QA y produccion.
- Actualizar extraccion:
  - OpenRouter Gemma / Nemotron.
  - Google Gemini como fallback.
  - Fallback local con pdfplumber, pandas y Tesseract.
- Actualizar politica de etiquetas:
  - 7 etiquetas oficiales de modelo.
  - 2 etiquetas por regla deterministica.
  - 1 etiqueta excluida documentada.

## Texto base sugerido

> HemoVet se implementa como una plataforma web modular con API versionada en `/api/v1`. El backend organiza sus responsabilidades por dominios: autenticacion, usuarios, mascotas, historial, hematologia, inferencia ML, vigilancia poblacional, mapas, extraccion asistida y chat LLM/RAG. La persistencia se maneja con PostgreSQL, SQLAlchemy y Alembic. El frontend consume estos servicios desde una interfaz React orientada al propietario.

## Evidencia incluida

- `evidencia/README.md`: README actual del proyecto.
- `evidencia/architecture.md`: arquitectura backend real.
- `evidencia/llm-rag.md`: diseno real del modulo LLM/RAG.
- `evidencia/docker-compose.yml`: despliegue base.
- `evidencia/docker-compose.prod.yml`: despliegue productivo.



---

## Estado 11/7/2026 (revisión sobre `.docx (4)`)

> Bloque nuevo del 11/7/2026. Todo lo de arriba es el plan original; esto es el estado verificado hoy.

**CONTRADICCIÓN A CORREGIR:** el capítulo dice **43 características** en P322 ("XGBoost v3 ... 43 características ... reticulocitos") pero **38 características** en P326 ("38 características: 20 directos + 18 derivadas"). El número vigente es **43** (v3 con features de reticulocitos reincorporados); P326 quedó desactualizado → cambiar 38 por 43 y ajustar el desglose (20 directos + 18 derivadas = 38 NO cuadra con 43; recalcular el desglose real desde el artefacto del modelo).
**Alineado:** 2,454 IDEXX + 1,301 DAP (P327), 7 etiquetas modelo + 2 reglas.
