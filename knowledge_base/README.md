# Base de conocimiento de HemoVet

Esta carpeta separa el workspace local de curación del corpus que puede
desplegarse. Git usa una lista permitida: cualquier ruta nueva queda ignorada
salvo que se incorpore explícitamente al contrato de `.gitignore`.

## Contenido versionado

- `expert_review/approved/**/*.md`: corpus Markdown versionado seleccionado para
  el runtime. El nombre histórico de la ruta no acredita revisión veterinaria
  independiente.
- `manifests/production_corpus_manifest.json`: integridad, conteos y colección
  esperada del corpus productivo.
- `manifests/sources_manifest.json` y `manifests/curation_rules.json`:
  catálogo bibliográfico canónico, procedencia y reglas reproducibles del
  pipeline. El catálogo es la fuente de los títulos, autores y ediciones que se
  muestran al usuario; los filenames nunca son títulos públicos.
- `scripts/`: código offline de extracción y curación.
- `microcards/` y `policies/`: recursos auxiliares curados.
- `raw_md/hemograma_canino_prueba.md`: fixture mínimo para desarrollo y CI.

## Contenido exclusivamente local

Las fuentes PDF/EPUB, resultados Docling, staging, procesamiento, candidatos,
colas, reportes, chunks, embeddings e índices no se versionan.

## Contrato de ejecución

Desarrollo local y checkout versionado:

```env
RAG_SOURCE_DIR=knowledge_base/expert_review/approved
RAG_COLLECTION_NAME=hemovet_canine_hematology_v2
RAG_SCHEMA_VERSION=hemovet-rag-v2
RAG_SOURCE_MANIFEST=knowledge_base/manifests/sources_manifest.json
RAG_CHUNK_SIZE_WORDS=90
RAG_CHUNK_OVERLAP_WORDS=15
```

Producción:

```env
RAG_SOURCE_DIR=knowledge_base/expert_review/approved
RAG_COLLECTION_NAME=hemovet_canine_hematology_v2
RAG_SCHEMA_VERSION=hemovet-rag-v2
RAG_SOURCE_MANIFEST=knowledge_base/manifests/sources_manifest.json
RAG_CHUNK_SIZE_WORDS=90
RAG_CHUNK_OVERLAP_WORDS=15
```

Validación desde la raíz:

```bash
HEMOVET_PROJECT_ROOT="$PWD" \
  python backend/scripts/ingest_rag.py index \
  --source-dir knowledge_base/expert_review/approved \
  --dry-run
```

El pipeline actual exige `status: approved`, `expert_reviewed: true`,
`review_required: false` y trazabilidad de aprobación para incorporar un
documento. Esos campos son estados técnicos heredados del flujo de curación, no
prueba de que un médico veterinario independiente haya revisado el contenido.
Gran parte del corpus conserva además una decisión provisional; cualquier
afirmación de validación clínica requiere evidencia externa por documento.

Además, su procedencia debe poder resolverse de forma inequívoca contra
`sources_manifest.json`. Los documentos no resueltos se ponen en cuarentena y no
se indexan. Las páginas solo se conservan cuando existen como metadata numérica;
no se deducen a partir del nombre del archivo.

## Migración a RAG v2

La colección v1 no es compatible con el esquema `hemovet-rag-v2`: v2 cambia la
segmentación semántica, IDs de chunks, revisión de catálogo y metadata pública.
No se debe renombrar una colección v1 para reutilizarla. Primero validar y luego
reconstruir la colección configurada:

```bash
docker compose run --rm rag_ingest \
  python scripts/ingest_rag.py index --dry-run

docker compose run --rm rag_ingest \
  python scripts/ingest_rag.py index --reset --prune
```

`--reset` borra únicamente `RAG_COLLECTION_NAME`; confirmar el nombre antes de
ejecutarlo. Una ingesta posterior normal usa `--prune`. Si cambia el catálogo,
el esquema de chunks, el modelo de embeddings o la revisión del corpus, el
script exige otra colección o un reset explícito en lugar de mezclar versiones.

## Metadata visible e interna

Chroma conserva IDs, paths, hashes y scores para actualización y recuperación.
Esos campos son internos. El API puede proyectar únicamente título real,
autores, edición, capítulo, sección, páginas explícitas y tipo de fuente. La
aplicación no distribuye PDFs/EPUB, libros completos ni fragmentos extensos del
corpus protegido.
