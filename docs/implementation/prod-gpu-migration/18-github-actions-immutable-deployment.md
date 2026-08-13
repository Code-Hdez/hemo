# Etapa 8 — GitHub Actions y despliegue inmutable

Fecha operativa: 2026-08-02 (`America/Santo_Domingo`; los runs de GitHub
terminaron el 2026-08-03 UTC).

Estado: `COMPLETED` para implementación, publicación OCI y validación técnica.
No se realizó un despliegue productivo ni el cutover administrativo de
`hemovet-prod`.

## Objetivo

Versionar un único workflow proporcional al proyecto que pruebe la revisión,
publique imágenes inmutables mediante WIF, genere `hemovet.release/v1` y deje
preparado un despliegue transaccional por IAP. Toda mutación de metadata GPU o
de la aplicación exige un dispatch manual `DEPLOY`, desde `main`, confirmando
el SHA completo.

## Estado inicial y gates

- Rama: `dev-agosto/feat-gpu-deployment-separation`.
- HEAD inicial de Etapa 8: `046377be`.
- Se publicaron como respaldo los ocho commits locales comprendidos entre
  `ce8a82ea` y `046377be`, sin PR, merge ni cambio de `main`.
- `dips.md` permaneció sin seguimiento y con SHA-256
  `22ef723ec15957e215ef5dadc207572b8dc11b9e8b715b41dc89d9b8e0e145da`.
- `hemovet-llm-gpu` estaba y quedó `TERMINATED`.
- El snapshot `hemovet-llm-gpu-pre-stage6-20260802` estaba y quedó `READY`.
- El working tree rastreado estaba limpio antes de implementar.
- GitHub conservaba los secrets `GCP_HOST`, `GCP_SSH_KEY`, `GCP_USER`,
  `PRODUCTION_ENV_B64`, `PRODUCTION_SMOKE_EMAIL` y
  `PRODUCTION_SMOKE_PASSWORD`. Solo se inventariaron sus nombres.
- No existían variables de repositorio. El environment `production` existía
  sin secrets ni reglas de protección.
- `main` permaneció en `e30c422445e6c2e096b851895ea495858e6cc531`.

## Alcance realizado

### Workflow único

`.github/workflows/deploy.yml` distingue cuatro caminos:

| Evento/operación | Pruebas | OCI + manifiesto | Metadata GPU | Producción |
| --- | --- | --- | --- | --- |
| Pull request a `main` | sí | no | no | no |
| Push no documental a `main` | sí | sí | no | no |
| `VALIDATE_WIF_IAP` | WIF/IAP | no | no | no |
| `PUBLISH` | sí | sí | no | no |
| `DEPLOY` | sí | sí/reutiliza | sí, diferida | sí, transaccional |

`DEPLOY` requiere simultáneamente:

1. evento `workflow_dispatch`;
2. input `operation=DEPLOY`;
3. `refs/heads/main`;
4. `confirm_sha == github.sha`;
5. build, manifiesto y publicación GPU satisfactorios;
6. environment `production`.

El gate se aplica tanto a `publish_gpu_release` como a `deploy_prod`. Por lo
tanto, un push o una validación nunca cambia metadata de la GPU ni la
aplicación. Esto prioriza la autorización manual solicitada sobre la propuesta
anterior de actualizar metadata automáticamente en cada push.

La secuencia desplegable queda:

```text
scope
  ├── backend tests
  ├── frontend tests
  └── configuration
          |
          v
build_and_push
          |
          v
publish_gpu_release  [solo DEPLOY manual + main + SHA]
          |
          v
deploy_prod          [solo DEPLOY manual + main + SHA]
          |
          v
production_smoke_tests
```

`concurrency` serializa por workflow y ref, y no cancela un despliegue activo.
Todas las Actions externas están fijadas por SHA. Los permisos por defecto son
`contents: read`; `id-token: write` aparece únicamente en los jobs WIF.

### Artefactos y manifiesto

`deploy/ci/build-and-publish-images.sh`:

- usa un tag informativo `sha-<GITHUB_SHA completo>`;
- obtiene el digest desde el índice remoto y lo cruza con metadata de BuildKit;
- verifica la referencia canónica `<paquete>@sha256:<digest>`;
- genera SBOM SPDX y provenance SLSA v1 como attestations OCI;
- no usa `latest` ni claves JSON;
- puede reutilizar el tag exacto si una repetición del mismo SHA ya existe.

La revisión publicada y validada fue:

```text
af5ab60b418bc931c4c4cabc8b8ef92893325fb6
```

| Paquete | Digest canónico |
| --- | --- |
| `backend` | `sha256:c710984c1c3d42959bf54ef387490903a06aa9eb92a4c00acdeb6c26ee5c72ae` |
| `frontend` | `sha256:8feb146ec8092fc4df480331015a71e5271eaa255daa8cb3b5454d97aedbb296` |
| `ollama-runtime` | `sha256:de0833bd3afd746a50281ba867b1504a836bcde54b493bf9c65c3d9c2a389179` |

Cada índice contiene predicates `https://slsa.dev/provenance/v1` y
`https://spdx.dev/Document`. Container Analysis no se habilitó; la evidencia se
leyó directamente de los manifiestos OCI.

El artefacto GitHub `hemovet-release-30776245995-1` contiene solo:

- `artifact-set.json`;
- `release-manifest.json`;
- `gpu-runtime.json`;
- `rag-summary.json`.

No contiene `.env`, URLs privadas, passwords ni valores de secrets. Su tamaño
es 2,995 bytes, retención 30 días e ID `8842261324`.

`hemovet.release/v1` enlaza el mismo SHA con los tres digests, digest de
configuración, Caddy, Qwen, cuantización, colección RAG y versiones de
contratos. Valores validados:

```text
release_id=af5ab60b418bc931c4c4cabc8b8ef92893325fb6
model=qwen3:4b-instruct-2507-q4_K_M
model_digest=sha256:0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0
quantization=Q4_K_M
rag_collection=hemovet_canine_hematology_v2__6832f37d4287
rag_fingerprint=6832f37d428731520ce903de60d0781df543df3a10c84f1fcdbf27056bef9b60
rag_schema=hemovet-rag-v2
gpu_state=pending_boot_validation
update_while_running=false
```

### Entorno y RAG transaccionales

La release deriva de `PRODUCTION_ENV_B64` un candidato privado de modo `0600`.
Solo reemplaza claves versionadas: revisión, referencias por digest, endpoint
privado verificado y colección derivada del fingerprint. La reconstrucción
previa al deploy debe producir exactamente el mismo digest de configuración.

Se corrigieron dos divergencias encontradas por el gate real:

- el entorno legado conserva temporalmente `http://ollama:11434/`, mientras la
  release nueva debe proyectar `http://10.128.0.3:11434/`;
- `markdown-v5` es el esquema de chunking y `hemovet-rag-v2` el esquema del
  corpus. El dry-run ahora publica ambos campos y el manifiesto compara el
  correcto.

Una URL pública, un esquema divergente, una colección vacía, cuarentena no
cero, un digest ausente o un entorno inválido eliminan el candidato temporal y
detienen el workflow antes de cualquier despliegue.

`deploy/prod/deploy-release.sh` queda versionado para:

1. validar manifiesto, candidato y source exactos;
2. autenticarse desde la service account runtime, sin key file;
3. ejecutar `docker compose pull` por digest;
4. validar o crear la colección RAG inmutable;
5. instalar el entorno completo con `manage_deploy_env.py`;
6. hacer `up -d --no-build`;
7. exigir `core_ready`, base de datos y RAG;
8. restaurar entorno, source, Compose y punteros previos ante fallo.

No usa `git pull`, `reset`, `clean`, builds remotos ni `--remove-orphans`; el
Ollama local productivo se conserva hasta el cutover autorizado.

## IAM y WIF

Provider final:

```text
hemovet-github/github-main-production
state=ACTIVE
repository=xPshycho/hemogramas-proyectoICC
repository_id=1148021152
owner=xPshycho
owner_id=115911218
environment=production
ref=refs/heads/main
workflow_ref=.../.github/workflows/deploy.yml@refs/heads/main
```

La condición se amplió temporalmente a la rama de trabajo para las pruebas y
se restauró a `main` al finalizar. La validación final desde la rama fue
rechazada por la condición.

Matriz efectiva adicional de la identidad CI:

| Rol | Alcance/condición | Uso |
| --- | --- | --- |
| `roles/artifactregistry.writer` | repositorio `hemovet-images` | push y read-back OCI |
| `roles/compute.viewer` | proyecto, solo lectura | inventario previo y estado de VMs |
| `roles/iap.tunnelResourceAccessor` | `10.128.0.2:22` | túnel IAP a producción |
| `hemovetGpuReleasePublisher` | instancia GPU exacta | `get` y `setMetadata` únicamente |

El rol personalizado contiene exclusivamente:

```text
compute.instances.get
compute.instances.setMetadata
```

No concede start, stop, reset, SSH, IAM ni escritura sobre producción. La
service account CI no tiene claves administradas por usuario.

## Ejecuciones y evidencia

| Run | Resultado | Evidencia |
| --- | --- | --- |
| `30774528618` | fallo esperado | rama no autorizada rechazada por WIF |
| `30774595816` | fallo | primer IAP antes de propagación IAM; no cuenta |
| `30774662155` | éxito | WIF + IAP a `10.128.0.2:22` |
| `30774700108` | éxito | segunda validación consecutiva WIF + IAP |
| `30774761230` | fallo cerrado | expresión `jq` sobre-escapada; solo backend parcial |
| `30775171002` | fallo cerrado | entorno legado con URL local; sin manifiesto |
| `30775635187` | fallo cerrado | esquema chunk/corpus confundido; sin manifiesto |
| `30776245995` | éxito | 3 imágenes, attestations y release completa |
| `30776824293` | fallo esperado | provider final volvió a rechazar la rama |

En todos los runs de validación/publicación, `publish_gpu_release`,
`deploy_prod` y `production_smoke_tests` quedaron `skipped`. Los fallos parciales
no son releases desplegables porque carecen del artefacto completo validado.

Los logs de los cuatro runs representativos se escanearon sin coincidencias de
private keys, tokens, API keys, credenciales PostgreSQL o payloads de
`PRODUCTION_ENV_B64`.

## Pruebas

- Python 3.11.15, regresión local final: `958 passed`, `1 skipped`, `4 subtests`.
- Ruff completo: `PASS`.
- Run final backend: migraciones `6 passed`; chat `609 passed`, `1 skipped`;
  contratos release/GPU `48 passed`; evaluación `24 passed`; resto backend
  `295 passed`, `4 subtests`.
- Frontend: 14 archivos, `108 passed`; Biome, TypeScript y build `PASS`.
- Playwright crítico: `8 passed`.
- Compose local/producción/GPU: servicios exactos y `config` válidos.
- Caddy, Bash y `actionlint 1.7.12`: `PASS`.
- Preflight privado real: release, entorno, RAG y los tres digests `PASS`; el
  temporal fue eliminado inmediatamente.
- Aplicación pública posterior: HTTP 200; `rag_ready=true`,
  `chroma_ready=true`, 4,696 chunks y chat degradado con GPU apagada.

## Migración administrativa diferida

Se validaron dos ejecuciones WIF/IAP consecutivas. No se activó OS Login en
producción ni se sustituyó su Default Compute SA porque ambos cambios forman un
cutover real: el cambio de identidad puede exigir stop/start y el workflow que
sigue en `main` aún necesita el acceso de emergencia.

Estado seguro de transición:

- `hemovet-prod`: `RUNNING`, sin restart desde 2026-07-02, OS Login `UNSET`,
  Default Compute SA;
- `default-allow-ssh`: conservada para producción;
- secrets SSH: conservados por nombre, sin lectura ni rotación;
- el nuevo workflow no referencia esos tres secrets;
- `authenticate-artifact-registry.sh` falla cerrado hasta que producción use
  `hemovet-prod-runtime`;
- `main` y su workflow anterior siguen intactos y recuperables.

Antes del primer `DEPLOY` deben ejecutarse en ventana aprobada: asociar la SA
runtime, habilitar OS Login, probar guest login/sudo por IAP dos veces, probar
emergencia y solo entonces restringir SSH público. No se deben retirar secrets
ni accesos antes de ese gate.

## Costos

- GPU: USD 0 atribuible a Etapa 8; nunca se encendió.
- Artifact Registry: pasó de 4,216.688 MB a 7,190.672 MB por las revisiones y
  attestations. Incremento: 2,973.984 MB. La tarifa oficial es gratuita hasta
  0.5 GiB-mes por cuenta de facturación y después equivale aproximadamente a
  USD 0.10/GiB-mes. Según la unidad del reporte, el incremento ronda USD
  0.28–0.29/mes; el total del repositorio ronda USD 0.62–0.65/mes si ese free
  tier no está consumido por otro proyecto. Fuente:
  <https://cloud.google.com/artifact-registry/pricing>.
- GitHub Actions: 2,696 segundos de runtime de jobs medido (`44m56s`) entre
  pruebas exitosas y fallos cerrados. El costo real depende de la cuota del
  plan y queda `NO VERIFICADO`; a la tarifa Linux excedente de USD 0.006/min,
  el techo sería aproximadamente USD 0.27.
- Artefacto GitHub: 2,995 bytes durante 30 días; costo material despreciable.
- GitHub solo factura por encima de la cuota del plan; Linux 2-core cuesta USD
  0.006/min y artifacts excedentes USD 0.25/GB-mes. Fuente:
  <https://docs.github.com/en/billing/concepts/product-billing/github-actions>.
- IAP: solo túneles breves; las funciones para recursos alojados en Google
  Cloud no tienen cargo IAP, aunque aplican cargos normales de red/compute.
  Fuente: <https://cloud.google.com/iap/pricing>.

El repositorio mantiene cleanup en `dry-run=true`, KEEP 20 y propuesta DELETE
untagged después de 30 días. No se activó borrado durante esta etapa para
preservar evidencia y rollback.

## Rollback

No hay rollback productivo que ejecutar: la aplicación, GPU y datos no se
modificaron. El procedimiento preparado es:

1. revertir con commits normales los commits funcionales de Etapa 8; no usar
   reset, clean ni force push;
2. mantener `main=e30c4224…` mientras no exista aprobación de merge;
3. para una release futura fallida, seleccionar el manifiesto anterior y sus
   digests, no mover tags;
4. el script remoto restaura `.env`, colección, source y Compose previos;
5. metadata GPU conserva `hemovet-gpu-previous-release` para volver al SHA
   previo en el próximo arranque;
6. retirar IAM Stage 8 solo después de restaurar otro método operativo, según
   `06-rollback-runbook.md`;
7. conservar el snapshot y no borrar imágenes referenciadas.

## Fuera de alcance confirmado

No se desplegó backend/frontend, no se inició la GPU, no se modificaron
PostgreSQL, ChromaDB, colecciones o datos clínicos, no se retiró Ollama local,
no se cambió red/firewall/IP/disco, no se creó PR/merge y no se modificó
`main`. Tampoco se añadieron Kubernetes, Terraform, microservicios, regiones o
plataformas externas.

## Riesgos pendientes

- `main` y el environment no tienen protección/revisores por limitaciones de
  permisos/configuración GitHub; el doble gate manual está en YAML.
- OS Login, SA runtime productiva y retirada de SSH requieren una ventana real.
- Las Actions fijadas son seguras por SHA pero algunas emiten warning de Node 20
  forzado a Node 24; no bloquea y debe actualizarse en mantenimiento posterior.
- Container/vulnerability scanning permanece deshabilitado; SBOM/provenance sí
  están embebidos y verificados.
- Las revisiones parciales consumen almacenamiento hasta que una limpieza
  aprobada las retire sin afectar las 20 retenidas o los rollbacks.
- El primer `DEPLOY` real y su rollback pertenecen a Etapas 9–11.
