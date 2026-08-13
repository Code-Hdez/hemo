# Etapa 11 — Puesta en servicio controlada

## Resultado ejecutivo

La aplicación pública fue desplegada correctamente mediante WIF e IAP en la
revisión inmutable:

```text
069df45f7becbf1bf698a3ee6a8a9305e3aa4d1f
```

Backend, frontend, Caddy, PostgreSQL, ChromaDB y RAG quedaron operativos. Con
la GPU apagada, el núcleo permanece listo y el chat se declara degradado. No
hubo pérdida de datos. La validación live de la GPU y el cutover administrativo
se detuvieron por instrucción posterior del usuario de no ejecutar más tests;
no se presentan como realizados.

Estado documental de la etapa: `IN_PROGRESS` por validaciones diferidas.

## Ventana y responsables

| Elemento | Valor |
| --- | --- |
| Inicio operativo | 2026-08-03T13:56:45Z |
| Workflow exitoso | 2026-08-03T15:25:29Z–15:38:16Z |
| GPU encendida | 2026-08-03T15:39:39Z–15:42:07Z |
| Fin de mutaciones | 2026-08-03T15:42:09Z |
| Ejecutor | sesión Codex autorizada por el usuario |
| Proyecto | project-5b36701c-f44f-4c03-a12 |
| Zona | us-central1-a |

## Estado inicial y respaldos

Antes del cutover se capturaron revisión, entorno, RAG, contenedores y metadata.
Se creó el snapshot `hemovet-prod-pre-stage11-20260803`, estado `READY`, boot
disk 50 GB y `storageBytes=36,768,355,008`. Se conservó
`hemovet-llm-gpu-pre-stage6-20260802`, estado `READY`, boot disk 100 GB y
`storageBytes=58,891,150,336`.

El respaldo inmediato en producción quedó bajo:

```text
/var/backups/hemovet-stage11/pre-e7713a...
```

Incluye entorno completo, revisión, colección RAG, inspección de contenedores,
volúmenes, hashes y dump PostgreSQL en formato custom. `pg_restore -l` validó
el dump. El directorio usa modo `0700` y sus archivos privados `0600`.

Línea base de datos:

```text
users=46
pets=81
analyses=140
analysis_parameters=2575
chat_sessions=313
chat_turns=351
chat_messages=683
```

## Revisión finalmente desplegada

La revisión inicialmente autorizada `e7713a…` encontró tres defectos de
portabilidad del despliegue, no del dominio clínico. Cada intento falló cerrado
y se corrigió mediante PR antes de construir un SHA nuevo:

| Hallazgo | Corrección | PR / merge |
| --- | --- | --- |
| host sin alias `python` | helpers host usan `python3` | `1be07112`, PR 30 / `9d775cbb…` |
| host sin Pydantic | payload validado dentro de imagen backend inmutable, sin red y read-only | `cbf61217`, PR 31 / `130994a8…` |
| corpus extraído inaccesible al UID no root | árbol Git `0755/0644`; entorno/manifiesto `0600` | `44b9fbf0`, PR 32 / `069df45f…` |

La última corrección añadió una prueba de extracción real. Resultado focal:
21 passed, Ruff PASS, `bash -n` PASS y `git diff --check` PASS. El pipeline
completo del PR 32 pasó antes del merge.

## Artefactos y manifiestos

| Componente | Digest canónico |
| --- | --- |
| Backend | `sha256:1d27af423b399f3328311271e6929100de3083c37d71f75b6d9288e0769fe57c` |
| Frontend | `sha256:1681df1c434c2373d981817460a522b902762e3107f1068f7098a06f1ec6cf7f` |
| Runtime GPU | `sha256:e85e87e1fdd596307cda6a9e2871af3cdef74a3f164c5cc13c0d64fe2f0dd154` |
| Qwen | `sha256:0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0` |

Los tres manifests OCI se descargaron en crudo y su SHA-256 coincidió con el
digest declarado. `hemovet.artifacts/v1`, `hemovet.release/v1` y
`hemovet.gpu-runtime-release/v1` validaron y comparten exactamente el SHA
`069df45f…`. No se utilizó `latest`.

Hashes de la evidencia de publicación `30826650657`:

```text
artifact-set.json      d7aad64db7942f0e2d1614d45fd16b440921b1d4c7aceda3a2e789e767f28856
gpu-runtime.json       f29f97d1b505ca3148275aca6437b14389cc0215769522254f170ef9e9f06340
rag-summary.json       dd94f63a206c1d23934c0ca42a5bf2497f0e01d4b24682d1eff6ff14a0a2c196
release-manifest.json  03960bca167fa913ca45dd03c90fe520f5aca0f6a7fb880e99330c3a2c823ed2
```

## Workflow y transacción

El gate manual ejecutado fue:

```text
workflow run 30827420990
operation=DEPLOY
git ref=main
confirm_sha=069df45f7becbf1bf698a3ee6a8a9305e3aa4d1f
```

Tests, configuración, build, publicación, metadata GPU, deploy IAP y smoke
terminaron `success`. La transacción remota fue:

```text
20260803T153601.245677433Z-73024
```

El entorno completo se instaló con modo `0600`, hash
`29eda538e8c77ea2e774e9c0d02abd37ed7d00c23fb57f984e130cdd23a92d16`.
Los enlaces quedaron:

```text
current  -> /opt/hemovet-prod/releases/069df45f.../source
previous -> /home/ubuntu/hemogramas-proyectoICC
```

## Estado productivo observado

```text
public root             HTTP 200
public chat health      HTTP 200
backend                 healthy, digest 1d27af...
frontend                healthy, digest 1681df...
caddy                   healthy
postgresql              healthy
chroma                   healthy
rag_ingest               exit 0
alembic                  0012_chat_browser_session (head)
RAG                      4,696 chunks
core_ready               true
database_ready           true
chroma_ready             true
rag_ready                true
provider_ready           false
chat_ready               false
status                   degraded
```

El código público de disponibilidad fue `LLM_PROVIDER_NOT_READY` y el contrato
del proveedor `LLM_PROVIDER_UNAVAILABLE`, `retryable=true`. La ausencia de GPU
no hizo fallar el núcleo.

Los conteos posteriores coincidieron exactamente con la línea base. No se
eliminó, sobrescribió ni promovió una colección distinta. La colección activa
sigue siendo `hemovet_canine_hematology_v2__6832f37d4287`.

Ollama local quedó preservado como orphan saludable por rollback, pero el
Compose productivo activo ya no contiene `ollama` ni `ollama_setup`; el backend
nuevo usa la URL privada configurada para la GPU.

## GPU y costo

La metadata deseada se publicó como:

```text
release_id=069df45f7becbf1bf698a3ee6a8a9305e3aa4d1f
revision_state=pending_boot_validation
runtime_digest=sha256:e85e87e...
model_digest=sha256:0edcdef3...
```

La VM comenzó `TERMINATED`, se encendió manualmente y volvió a `TERMINATED`.
Tiempo entre timestamps de Compute Engine: aproximadamente 147.878 segundos.
El costo exacto facturado es `NO VERIFICADO`; no se infiere una factura desde
precios estimados. Las IPv4 y snapshots conservados pueden generar cargos
independientes.

Por orden del usuario no se inspeccionó ni probó después de ese arranque:

- estado aplicado del reconciliador;
- `/api/tags`, `/api/show` y `/api/ps`;
- identidad y cuantización live;
- uso `full_gpu` de la L4;
- latencia, VRAM, RAM y disco de ese arranque;
- chat general, seleccionado e histórico;
- memoria, fuentes, streaming y recuperación automática.

Todos se marcan `NO VERIFICADO` para Etapa 11. La evidencia real de Etapa 10
permanece válida como antecedente, pero no se atribuye a este arranque.

## Identidades y acceso administrativo

Producción usa ahora:

```text
hemovet-prod-runtime@project-5b36701c-f44f-4c03-a12.iam.gserviceaccount.com
```

La lectura de Artifact Registry y el despliegue mediante WIF/IAP funcionaron.
No obstante, el primer acceso directo IAP/OS Login a GPU fue rechazado por
clave pública y no se corrigió ni repitió después de que el usuario detuvo las
pruebas. Por ello:

- no se activó el cutover administrativo final en producción;
- no se retiró SSH público heredado;
- no se eliminaron `GCP_HOST`, `GCP_USER` ni `GCP_SSH_KEY`;
- no se eliminó el acceso de emergencia;
- no se presenta una doble validación IAP/OS Login inexistente.

Los permisos puente temporales creados para el despliegue requieren revisión y
retirada posterior, solo después de validar el reemplazo.

## Rollback disponible

Rollback inmediato de la aplicación:

1. preservar evidencia y detener nuevos deploys;
2. restaurar el entorno desde la transacción o backup byte-exacto;
3. mover `current` al valor de `previous`;
4. levantar el Compose anterior con `--no-build`;
5. verificar migración `0012`, DB, RAG y HTTP;
6. si fuera necesario, restaurar desde el snapshot productivo y dump validado.

Además se conserva la revisión inmutable `af5ab60b…`, sus digests/manifiestos,
la metadata GPU anterior y el snapshot GPU. El rollback RAG cambia el puntero;
no reescribe colecciones.

## Diferencias pendientes

1. Validar la revisión GPU `069df45f…` en un arranque autorizado.
2. Validar chat y recuperación contra ese runtime.
3. Completar dos accesos IAP/OS Login y el procedimiento de emergencia.
4. Retirar permisos puente, SSH público y secrets antiguos solo después.
5. Decidir cuándo detener permanentemente Ollama local; no borrar todavía sus
   volúmenes.

Hasta resolver o aceptar expresamente estos puntos, la Etapa 11 no se declara
`COMPLETED AND VALIDATED`.
