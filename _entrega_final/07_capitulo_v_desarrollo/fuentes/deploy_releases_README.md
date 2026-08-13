# Contrato de release

`release-manifest.example.json` es un ejemplo sintáctico, no una revisión
desplegable ni evidencia de imágenes publicadas. Los digests son ilustrativos.

La fuente ejecutable del esquema `hemovet.release/v1` está en
`backend/app/core/release_manifest.py`; su representación JSON Schema versionada
es `release-manifest-v1.schema.json`. Una prueba exige que ambas permanezcan
idénticas. El manifiesto exige un único SHA de Git para aplicación y runtime
GPU, referencias OCI por digest, modelo no mutable, identidad RAG y las
versiones de los contratos compatibles.

Validación local:

```bash
PYTHONPATH=backend python -c \
  "from app.core.release_manifest import load_release_manifest; load_release_manifest('deploy/releases/release-manifest.example.json')"
```

La publicación automática, el registro de estado aplicado y Artifact Registry
pertenecen a etapas posteriores. Este directorio no autoriza un despliegue.

## Digests publicados

Un inventario `hemovet.artifacts/v1` registra el tag informativo
`sha-<GITHUB_SHA>` y la referencia canónica por digest de `backend`, `frontend`
y `ollama-runtime`. Se valida sin desplegar con:

```bash
PYTHONPATH=backend python backend/scripts/validate_artifact_set.py \
  deploy/releases/artifact-set-<GITHUB_SHA>.json
```

Para completar un manifiesto de release que ya contenga identidades reales de
configuración, startup, modelo y RAG:

```bash
PYTHONPATH=backend python backend/scripts/bind_release_artifacts.py \
  --manifest release-input.json \
  --artifact-set deploy/releases/artifact-set-<GITHUB_SHA>.json \
  --output release-bound.json
```

El enlazador no inventa los datos restantes ni publica el resultado. Rechaza
revisiones divergentes, `latest`, digests distintos a la referencia y conjuntos
incompletos.

## Inventario publicado en la Etapa 3

`artifact-set-515d343ac805779f94be9277376bdadf5516154d.json` es el
inventario verificado de las imágenes publicadas para esa revisión. Contiene
los digests reales de backend, frontend y `ollama-runtime`; no es por sí solo un
`hemovet.release/v1` desplegable.

No debe completarse el manifiesto de release con placeholders. El digest del
modelo, la identidad del bundle de startup y la colección RAG activa continúan
`NO VERIFICADOS` hasta sus etapas correspondientes.

## Primera release completa conservada

La revisión `af5ab60b418bc931c4c4cabc8b8ef92893325fb6`, producida por el run
`30776245995`, es la primera revisión de este directorio con las cuatro piezas
necesarias para una selección futura por identidad inmutable:

- `artifact-set-af5ab60b418bc931c4c4cabc8b8ef92893325fb6.json`;
- `release-manifest-af5ab60b418bc931c4c4cabc8b8ef92893325fb6.json`;
- `gpu-runtime-af5ab60b418bc931c4c4cabc8b8ef92893325fb6.json`;
- `rag-summary-af5ab60b418bc931c4c4cabc8b8ef92893325fb6.json`.

Los tres primeros archivos son copias byte a byte del artefacto GitHub
publicado. El resumen RAG elimina la ruta absoluta efímera del runner, pero
conserva conteos, versiones y digests. Ninguno contiene el entorno privado.

Antes de seleccionar esta o cualquier revisión anterior, reconstruir el
entorno privado desde el secreto autorizado y validar el conjunto cerrado:

```bash
PYTHONPATH=backend python backend/scripts/validate_rollback_bundle.py \
  --release-manifest deploy/releases/release-manifest-<SHA>.json \
  --artifact-set deploy/releases/artifact-set-<SHA>.json \
  --candidate-environment /ruta/privada/candidate.env \
  --source-root /ruta/al/source-del-SHA \
  --gpu-release deploy/releases/gpu-runtime-<SHA>.json \
  --bundle-manifest deploy/gpu/bundle-manifest.sha256
```

La salida solo contiene SHA, digests y colección. La validación no autoriza ni
ejecuta un despliegue. Un conjunto cuyo manifiesto, imágenes, entorno, fuente o
proyección GPU pertenezca a revisiones distintas se rechaza.

## Revisión final aceptada en la Etapa 10

La revisión `e7713a72369bb9365f6d5323e165fbf84488bfb4`, producida por el run
`30794470808`, incorpora la corrección de rollback `ee9fa759` y el cierre
funcional `c81950b3`. Conserva aquí su conjunto publicado completo:

- `artifact-set-e7713a72369bb9365f6d5323e165fbf84488bfb4.json`;
- `release-manifest-e7713a72369bb9365f6d5323e165fbf84488bfb4.json`;
- `gpu-runtime-e7713a72369bb9365f6d5323e165fbf84488bfb4.json`;
- `rag-summary-e7713a72369bb9365f6d5323e165fbf84488bfb4.json`.

La ruta absoluta efímera del resumen RAG fue normalizada de la misma forma que
en la revisión anterior. El entorno privado no se versiona. La revisión
canónica de retorno seleccionada para esta aceptación es
`af5ab60b418bc931c4c4cabc8b8ef92893325fb6`; su salida sanitizada y validada
`hemovet.rollback-plan/v1` se conserva en
`rollback-plan-af5ab60b418bc931c4c4cabc8b8ef92893325fb6.json`.

La aceptación se realizó en un namespace no público; esta revisión todavía no
es un cutover productivo.
