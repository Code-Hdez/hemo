# Etapa 3 — Artifact Registry, IAM y WIF

Estado: `COMPLETED`.

El aprovisionamiento, el privilegio mínimo, la publicación OCI y el intercambio
OIDC real quedaron validados. La prueba positiva usó exactamente `main`,
`.github/workflows/deploy.yml` y el environment `production`; la prueba negativa
demostró que el mismo workflow sin ese environment es rechazado por el
provider. Ningún job de despliegue fue ejecutado.

## Línea base antes de mutaciones

### APIs habilitadas

```text
analyticshub.googleapis.com
bigquery.googleapis.com
bigqueryconnection.googleapis.com
bigquerydatapolicy.googleapis.com
bigquerydatatransfer.googleapis.com
bigquerymigration.googleapis.com
bigqueryreservation.googleapis.com
bigquerystorage.googleapis.com
cloudapis.googleapis.com
cloudquotas.googleapis.com
cloudtrace.googleapis.com
compute.googleapis.com
dataform.googleapis.com
dataplex.googleapis.com
datastore.googleapis.com
logging.googleapis.com
monitoring.googleapis.com
networkmanagement.googleapis.com
osconfig.googleapis.com
oslogin.googleapis.com
servicemanagement.googleapis.com
serviceusage.googleapis.com
sql-component.googleapis.com
storage-api.googleapis.com
storage-component.googleapis.com
storage.googleapis.com
telemetry.googleapis.com
```

No estaban habilitadas las APIs de Artifact Registry, IAM, Service Account
Credentials, Security Token Service ni Cloud Resource Manager.

### GitHub

- Remoto: `xPshycho/hemogramas-proyectoICC`.
- Workflow productivo actual: `.github/workflows/deploy.yml`.
- Autenticación actual observada en el archivo: SSH mediante los nombres
  `GCP_HOST`, `GCP_USER`, `GCP_SSH_KEY` y `PRODUCTION_ENV_B64`.
- Existencia real de esos secrets en GitHub: `NO VERIFICADO`; `gh auth status`
  informó un token API local inválido y no se intentó extraer otra credencial.
- WIF/OIDC en el workflow: ausente.
- GitHub Environment de producción: `NO VERIFICADO` externamente y no declarado
  en el workflow actual.

Esta fue la línea base inicial. Tras el cierre bloqueado, el usuario autorizó
explícitamente lo restante de la Etapa 3. Se añadió un gate manual no
desplegable con `environment: production`, `id-token: write` y la acción oficial
de autenticación fijada por SHA; la autenticación SSH productiva no fue retirada
ni utilizada por la prueba.

## Recursos creados

| Tipo | Identificador | Alcance | Propósito |
| --- | --- | --- | --- |
| API | `artifactregistry.googleapis.com` | proyecto | almacenar imágenes OCI |
| API | `iam.googleapis.com` | proyecto | service accounts y WIF |
| API | `iamcredentials.googleapis.com` | proyecto | credenciales efímeras por impersonación |
| API | `sts.googleapis.com` | proyecto | intercambio OIDC por tokens cortos |
| API | `cloudresourcemanager.googleapis.com` | proyecto | contexto y autorización del proyecto para WIF |
| Docker repository | `projects/project-5b36701c-f44f-4c03-a12/locations/us-central1/repositories/hemovet-images` | `us-central1` | backend, frontend y runtime Ollama |
| Service account | `hemovet-github-cicd` | proyecto | publicación OCI desde GitHub |
| Service account | `hemovet-prod-runtime` | proyecto | lectura OCI futura desde producción |
| Service account | `hemovet-gpu-runtime` | proyecto | lectura OCI futura desde GPU |
| Workload Identity Pool | `hemovet-github` | global | confianza externa GitHub OIDC |
| OIDC provider | `github-main-production` | pool anterior | repo, rama, workflow y environment autorizados |

Las cinco APIs se habilitaron juntas mediante la operación
`operations/acat.p2-371832959385-643e1fe0-4642-4d15-92d7-6644eac9b93b`.
No se habilitó Container Scanning ni ninguna API adicional.

El repositorio fue creado como `DOCKER`, `STANDARD_REPOSITORY`, cifrado con
clave administrada por Google y tags inmutables. URI:

```text
us-central1-docker.pkg.dev/project-5b36701c-f44f-4c03-a12/hemovet-images
```

Etiquetas de recurso: `application=hemovet`, `environment=shared` y
`migration_stage=artifact_identity`.

## Matriz IAM efectiva

| Principal | Recurso | Rol | Justificación |
| --- | --- | --- | --- |
| `hemovet-github-cicd@…` | `hemovet-images` | `roles/artifactregistry.writer` | publicar y leer artefactos del build |
| `hemovet-prod-runtime@…` | `hemovet-images` | `roles/artifactregistry.reader` | pull futuro de aplicación |
| `hemovet-gpu-runtime@…` | `hemovet-images` | `roles/artifactregistry.reader` | pull futuro del runtime GPU |
| identidad GitHub filtrada | service account CI/CD | `roles/iam.workloadIdentityUser` | impersonación efímera sin clave JSON |

No se asignaron permisos Artifact Registry a nivel de proyecto. Las cuentas
runtime se crearon y autorizaron en el repositorio, pero no se adjuntaron a
ninguna VM. La lectura posterior de la política confirmó exactamente estos tres
bindings. No hay `roles/owner`, `roles/editor`,
`roles/artifactregistry.admin` ni roles de proyecto para las identidades nuevas.

## Configuración WIF efectiva

El provider mapea `sub`, repositorio, propietario, referencia, workflow,
environment y claims numéricos disponibles. La condición admite únicamente:

```text
repository == xPshycho/hemogramas-proyectoICC
repository_id == 1148021152
repository_owner == xPshycho
repository_owner_id == 115911218
ref == refs/heads/main
workflow_ref == xPshycho/hemogramas-proyectoICC/.github/workflows/deploy.yml@refs/heads/main
environment == production
```

El binding de impersonación se limita además al atributo `repository`; no se
autoriza el pool completo. La API autenticada de GitHub verificó el repositorio
`1148021152` y el propietario `115911218`; ambos IDs inmutables se añadieron a
la condición y se leyeron de vuelta desde GCP después de converger la operación.

Pool:

```text
projects/371832959385/locations/global/workloadIdentityPools/hemovet-github
```

Provider:

```text
projects/371832959385/locations/global/workloadIdentityPools/hemovet-github/providers/github-main-production
```

Issuer: `https://token.actions.githubusercontent.com`. El provider y el pool
quedaron `ACTIVE`. El mapping completo y la condición se conservan, sin
secretos, en `deploy/gcp/stage3-resource-contract.json`.

La impersonación usa exclusivamente:

```text
roles/iam.workloadIdentityUser
principalSet://iam.googleapis.com/projects/371832959385/locations/global/workloadIdentityPools/hemovet-github/attribute.repository/xPshycho/hemogramas-proyectoICC
```

No se concedió `roles/iam.serviceAccountTokenCreator`. Las tres cuentas
reportaron cero claves administradas por usuario.

## Validación WIF real

El commit aislado `e30c422445e6c2e096b851895ea495858e6cc531` añadió el
gate manual a `main` con el mensaje `[skip ci]`. La consulta posterior confirmó
que ese push generó cero ejecuciones; luego se lanzó exclusivamente
`workflow_dispatch` `30762294120`.

El run terminó `success` con:

Evidencia remota: <https://github.com/xPshycho/hemogramas-proyectoICC/actions/runs/30762294120>.

| Job | Resultado | Evidencia |
| --- | --- | --- |
| `WIF authenticates and publishes proof` | `success` | obtuvo un access token de 600 segundos para `hemovet-github-cicd`, sin archivo JSON, y publicó/leyó el digest de prueba |
| `WIF rejects missing environment` | `success` | STS rechazó el token con `unauthorized_client` porque no cumplía la condición de atributos; el assertion step exigió ese fallo |
| Backend, frontend y configuración | `skipped` | el trigger manual los excluye explícitamente |
| `Deploy to Production` | `skipped` | conserva su condición exclusiva `push` a `main` |

La acción oficial quedó fijada al commit verificado
`google-github-actions/auth@7c6bc770dae815cd3e89ee6cdf493a5fab2cc093`.
El environment `production` fue creado por GitHub al ejecutar el job y no
contiene secrets, reviewers, timers ni reglas de protección. La seguridad de la
federación no depende solo de ese nombre: el provider exige además IDs de
repositorio/propietario, rama y workflow exactos.

## Inmutabilidad y retención

- Repositorio Docker regional estándar con tags inmutables.
- Tag informativo: `sha-<GITHUB_SHA completo>`.
- Referencia canónica: `IMAGE@sha256:<digest>`.
- `latest` queda prohibido como publicación y fuente de verdad.
- Tags reservados adicionales: `deployed-<SHA>` y `rollback-<SHA>`; al ser
  inmutables no pueden moverse a otro digest.
- Política de limpieza aplicada en `dry-run`: eliminar únicamente artefactos
  sin tag con más de 30 días y conservar al menos las 20 versiones más recientes
  de cada paquete.
- No se activará borrado real hasta contar con evidencia del dry-run, manifiesto
  publicado, tags protegidos y aprobación expresa.

## Artefactos OCI publicados

La revisión canónica construida desde un checkout limpio es:

```text
515d343ac805779f94be9277376bdadf5516154d
```

| Paquete | Tag informativo inmutable | Referencia canónica |
| --- | --- | --- |
| `backend` | `sha-515d343ac805779f94be9277376bdadf5516154d` | `backend@sha256:c20b932993c97d6078d04033f72d2de132381f6a6a06580dc65be74d52b5191f` |
| `frontend` | `sha-515d343ac805779f94be9277376bdadf5516154d` | `frontend@sha256:55b82e9e868247fc71d764f932610f0849db93fbe88b60261683f7894d305d7f` |
| `ollama-runtime` | `sha-515d343ac805779f94be9277376bdadf5516154d` | `ollama-runtime@sha256:b526b1d4bc30d0cc641e0d2a186034b327c97de0171b1a47ce1c917d79604e5f` |

Todas las referencias anteriores pertenecen a:

```text
us-central1-docker.pkg.dev/project-5b36701c-f44f-4c03-a12/hemovet-images
```

El inventario legible por máquinas está en
`deploy/releases/artifact-set-515d343ac805779f94be9277376bdadf5516154d.json`.
La consulta remota confirmó que tag y digest coinciden y que no existe un tag
`latest`.

Las tres imágenes incluyen labels OCI `source`, `revision` y `created`. El
runtime declara además Ollama `0.30.10` y fija su base como
`docker.io/ollama/ollama:0.30.10@sha256:bfc9c6d53cc6989aa5131a6fde6b162b2802d4d337657f3253b5f69579bddeee`.
Buildx publicó un predicado SPDX SBOM y un predicado de provenance para cada
imagen. Artifact Registry informa el nivel SLSA como `unknown`; por tanto no se
afirma un nivel SLSA que no esté demostrado.

El manifiesto completo `hemovet.release/v1` no se generó: la identidad/digest
real del modelo aprobado, el bundle de startup y la colección RAG desplegable
pertenecen a etapas posteriores y siguen `NO VERIFICADOS`. El enlazador queda
preparado y falla cerrado antes que inventar esos campos.

### Artefactos bootstrap supersedidos

Una primera construcción inmutable de la revisión
`6e2969d6fa735473097d4f1c19af46263436bd66` publicó los índices siguientes:

| Paquete | Digest de índice supersedido |
| --- | --- |
| `backend` | `sha256:08432f81416aa168b9fbc17624268d698c52912d3f03d11396c1cb6f427109f8` |
| `frontend` | `sha256:3a79ec9d1021af0b4345f80be862835ff40ab35d55c9149fdc24eb31f75dfab3` |
| `ollama-runtime` | `sha256:f2a4fc8d74c6b13c4db860ab316144bd41b130281f7c0f5b9b37cb5d34064f2f` |

No se desplegaron. Durante su inspección se detectó que el runtime heredaba el
label ambiguo `org.opencontainers.image.version=24.04` de la imagen base,
aunque el label específico de Ollama sí era correcto. El hallazgo se clasificó
`MEDIO`, se corrigió en `515d343` y se volvió a construir y validar. Como el
repositorio usa tags inmutables, los tags bootstrap se conservan como evidencia
y no se intentó moverlos ni borrarlos; las capas compartidas quedan
deduplicadas por contenido.

### Prueba OCI publicada mediante WIF

El run `30762294120`, autenticado exclusivamente mediante federación, publicó:

```text
us-central1-docker.pkg.dev/project-5b36701c-f44f-4c03-a12/hemovet-images/wif-validation:run-30762294120-1
us-central1-docker.pkg.dev/project-5b36701c-f44f-4c03-a12/hemovet-images/wif-validation@sha256:0998efbb07674eeb14b282c60bca44651feae2a6b83b632d9c650dce9cfaf989
```

Es una imagen `scratch` sin capas de aplicación ni datos. Se conserva como
evidencia inmutable del permiso de publicación y no forma parte del manifiesto
desplegable de HemoVet.

## Rollback previsto

Orden: retirar binding WIF, retirar IAM del repositorio, eliminar provider,
eliminar pool, evaluar artefactos, eliminar repositorio solo con aprobación,
eliminar las tres cuentas y finalmente deshabilitar únicamente las APIs que
esta etapa habilitó y que no tengan otros consumidores.

La eliminación del repositorio es destructiva y no se ejecutará como rollback
automático si ya contiene un digest referenciado.

## Ciclo de vida y eliminación por recurso

| Recurso | Dependencias/principales | Procedimiento de eliminación | Riesgo |
| --- | --- | --- | --- |
| APIs | repositorio, service accounts y WIF | `gcloud services disable <api> --project=...` solo después de retirar consumidores | puede afectar consumidores no inventariados; comprobar antes |
| `hemovet-images` | tres bindings IAM e imágenes referenciadas | `gcloud artifacts repositories delete hemovet-images --location=us-central1 --project=...` únicamente con aprobación destructiva y después de exportar referencias | elimina imágenes y rompe rollback |
| `hemovet-github-cicd` | IAM del repositorio y binding WIF | retirar ambos bindings y luego `gcloud iam service-accounts delete <email>` | bloquea publicación futura |
| `hemovet-prod-runtime` | lector del repositorio; no adjunta a VM | retirar binding y eliminar la cuenta | bloquea pull futuro al adjuntarla |
| `hemovet-gpu-runtime` | lector del repositorio; no adjunta a VM | retirar binding y eliminar la cuenta | bloquea pull futuro al adjuntarla |
| provider `github-main-production` | pool y binding sobre CI | retirar binding; `gcloud iam workload-identity-pools providers delete ...` | OIDC deja de funcionar; eliminación lógica recuperable por tiempo limitado |
| pool `hemovet-github` | provider anterior | eliminar provider y luego `gcloud iam workload-identity-pools delete ...` | invalida toda federación dentro del pool |

Los comandos completos y el orden seguro están en `06-rollback-runbook.md`.

## Costo y operación

- Service accounts, bindings y configuración WIF no mantienen una VM activa.
- Artifact Registry factura almacenamiento y, según origen/destino, transferencia;
  el repositorio está en la misma región objetivo para evitar transferencia
  interregional en el pull normal.
- La tarifa publicada incluye los primeros `0.5 GiB-mes` por cuenta de
  facturación y cobra el excedente; debe verificarse nuevamente antes de
  presupuestar. Referencia: <https://cloud.google.com/artifact-registry/pricing>.
- La limpieza está en simulación y no reducirá almacenamiento hasta ser
  revisada y activada explícitamente.
- El escaneo automático está deshabilitado porque no se habilitó
  `containerscanning.googleapis.com`; añadirlo exige una decisión posterior de
  costo y seguridad.
- Después de publicar las dos revisiones, sus attestations y la prueba WIF,
  `gcloud` reportó `4216.688 MB` (aproximadamente `4.12 GiB`). Con la tarifa publicada de
  `USD 0.10/GiB-mes` después de los primeros `0.5 GiB-mes` gratuitos por cuenta
  de facturación, la referencia aproximada es `USD 0.36/mes` solo por
  almacenamiento, antes de transferencia, impuestos o futuros artefactos.

## Evidencia de estado

- `gcloud artifacts repositories describe`: inmutabilidad `true`, política en
  `dry-run`, tamaño inicial `0 MB` y tamaño final reportado `4216.688 MB`.
- `get-iam-policy`: un writer CI y dos readers runtime a nivel del repositorio.
- `service-accounts keys list --managed-by=user`: salida vacía para las tres
  identidades.
- `workload-identity-pools ... describe`: pool/provider `ACTIVE` y condición
  exacta.
- `projects get-iam-policy --filter=hemovet-`: sin bindings de proyecto.
- Lectura posterior de Compute Engine: producción siguió `RUNNING` y la GPU
  `TERMINATED`; ambas conservan la cuenta default anterior. No se modificaron.
- Artifact Registry confirmó los tres tags finales y sus digests, además de los
  tres tags bootstrap supersedidos; ninguno se llama `latest`.
- Regresión final en Python 3.11: `898 passed`, `1 skipped`, `1 warning` y
  `4 subtests passed`; Ruff completo aprobado.
- Build frontend: `tsc -b && vite build` aprobado, con el warning preexistente
  de chunk mayor de 500 kB.
- Contratos focales de Artifact Registry: `16 passed`.

- `actionlint 1.7.12`, descargado del release oficial y comprobado contra su
  checksum, validó el workflow sin hallazgos.
- El intercambio real desde GitHub, la impersonación de la service account, la
  publicación y lectura por digest y el rechazo sin environment quedaron
  demostrados en el run `30762294120`.
- La lectura posterior de Compute Engine mantuvo producción `RUNNING` y GPU
  `TERMINATED`, sin cambios de identidades, IPs ni discos.

## Riesgos que permanecen fuera del cierre

- `main` no tiene branch protection ni rulesets y el environment `production`
  no tiene reglas; configurarlos requiere privilegios administrativos que la
  credencial actual no posee. El provider compensa parcialmente exigiendo IDs,
  `main`, workflow y environment exactos, pero la protección de rama debe
  abordarse antes de retirar el acceso legado.
- La autenticación SSH y sus secrets no se eliminaron. Su migración gradual
  continúa en la etapa de GitHub Actions.
- Container Scanning continúa deshabilitado y la limpieza permanece en
  `dry-run`.
- El gate manual publica una prueba inmutable por ejecución autorizada; debe
  usarse solo para validaciones explícitas y no como workflow de despliegue.

```text
ESTADO DE LA ETAPA: COMPLETADA Y VALIDADA
ESPERANDO APROBACIÓN PARA LA SIGUIENTE ETAPA
```
