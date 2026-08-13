# Promoción y rollback del índice RAG

HemoVet trata cada índice como un artefacto inmutable. El nombre productivo tiene
la forma `hemovet_canine_hematology_v2__<12 hex>` y el sufijo deriva del
fingerprint completo de embeddings, chunking, metadatos y contenido. La
colección base sin sufijo es solo un namespace de construcción; producción la
rechaza.

## Construcción y validación

1. Conserva el `RAG_COLLECTION_NAME` productivo actual y el SHA de la imagen.
2. Ejecuta el dry-run con exactamente el corpus y configuración que se van a
   desplegar:

   ```bash
   docker compose run --rm rag_ingest \
     python scripts/ingest_rag.py index --dry-run
   ```

3. Construye la candidata sin modificar ni borrar la colección activa:

   ```bash
   docker compose run --rm rag_ingest \
     python scripts/ingest_rag.py index \
     --collection hemovet_canine_hematology_v2 --stage --prune
   ```

4. Copia el nombre de colección que aparece en
   `promotion.set_environment.RAG_COLLECTION_NAME` a una copia privada del
   entorno y valida esa candidata. El workflow automatizado hace esta operación
   con `backend/scripts/prepare_rag_promotion.py`, valida `.env.next` y usa ese
   archivo solamente para la comprobación de la candidata:

   ```bash
   RAG_COLLECTION_NAME=hemovet_canine_hematology_v2__0123456789ab \
   docker compose run --rm rag_ingest \
     python scripts/ingest_rag.py index --validate-only
   ```

   Sustituye el sufijo del ejemplo por el emitido por el comando. La validación
   comprueba cantidad de chunks, revisión del corpus, schema y fingerprint
   completo; compartir un ID de chunk no permite reutilizar embeddings
   incompatibles.

5. Instala el entorno validado de forma atómica y reinicia backend. El workflow
   productivo mueve `.env.next` sobre `.env` únicamente después de que la
   candidata supera `--validate-only`, antes de reemplazar los servicios. Si el
   nombre configurado no coincide con el fingerprint calculado, el despliegue se
   detiene y el entorno activo queda intacto.

El job nunca usa `--reset` sobre la colección activa. Una ingesta ejecutada
dentro del proceso puede intercambiar el snapshot BM25 de forma atómica después
de actualizar la rama densa. En un despliegue versionado, la promoción reinicia
el backend con el puntero nuevo y construye BM25 desde ese mismo snapshot antes
de declarar readiness.

## Rollback

Las colecciones anteriores se conservan. Un rollback requiere restaurar juntos:

- el SHA anterior de backend y corpus;
- su archivo de entorno privado, incluido `RAG_COLLECTION_NAME`;
- la imagen/modelo y configuración de embeddings correspondientes.

Después ejecuta `--validate-only` con ese conjunto antes de volver a iniciar el
backend. No apuntes una versión nueva del código a una colección antigua: el
runtime la rechazará si su fingerprint no coincide. El borrado de colecciones
obsoletas se realiza fuera del despliegue, tras el periodo de retención y con un
respaldo verificable.

## Recuperación de una ingesta fallida

Una candidata parcial no se promociona. Repite la ingesta sobre un fingerprint
nuevo después de corregir corpus o configuración. Si falla la colección que aún
está activa, el workflow aborta y no intenta repararla en vivo; conserva el
servicio anterior y exige investigación explícita.
