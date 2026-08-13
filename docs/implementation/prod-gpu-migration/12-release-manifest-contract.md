# Contrato de manifiesto de release

Versión: `hemovet.release/v1`.

Fuentes versionadas:

- modelo Pydantic: `backend/app/core/release_manifest.py`;
- JSON Schema: `deploy/releases/release-manifest-v1.schema.json`;
- ejemplo no desplegable: `deploy/releases/release-manifest.example.json`.

Una prueba compara el JSON Schema generado con el archivo versionado para evitar
deriva.

## Identidad de la revisión

`release_id`, `source.github_sha`, `application.revision` y
`gpu_runtime.revision` deben ser el mismo SHA completo de 40 caracteres. El
origen registra además repositorio, workflow run, intento y timestamp con zona
horaria.

## Artefactos requeridos

- backend y frontend mediante referencias OCI `...@sha256:<64 hex>`;
- digest de configuración de aplicación y Caddy;
- runtime GPU por referencia OCI y digest;
- digest del bundle de startup y versión de su contrato;
- tag explícito de modelo, digest y cuantización;
- nombre de colección RAG, revisión del corpus, fingerprint del índice, esquema,
  modelo de embeddings y revisión de embeddings;
- versiones de contratos de disponibilidad y proveedor.

El validador rechaza `latest`, referencias OCI cuyo digest declarado no
coincide, timestamps sin zona, campos desconocidos y revisiones cruzadas.

## Aplicación diferida de GPU

El manifiesto exige:

```json
{
  "apply_on": "next_boot",
  "initial_validation_state": "pending_boot_validation",
  "update_while_running": false
}
```

Publicar este documento no enciende, reinicia ni actualiza la VM. El estado
observado (`applied`, `failed`, `rolled_back`) será un registro aparte para no
mutar la revisión firmable.

## Compatibilidad y promoción

Un manifiesto solo es candidato cuando existen todos los digests y el puntero
RAG ya identifica una colección validada. Las Etapas 3, 6 y 8 definirán dónde
se publica, cómo se firma/protege y cómo se marca su estado. Hasta entonces el
ejemplo no debe consumirse como una release real.

## Rollback contractual

El rollback selecciona un manifiesto anterior completo. No cambia tags, no
reconstruye imágenes, no reescribe colecciones y no modifica el manifiesto
anterior. El rollback ejecutable de despliegue y GPU se implementa y prueba en
la Etapa 9.
