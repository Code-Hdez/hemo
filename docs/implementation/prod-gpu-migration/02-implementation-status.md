# Estado de implementación

Estados permitidos: `PENDING`, `IN_PROGRESS`, `BLOCKED`, `COMPLETED` y
`ROLLED_BACK`.

| Etapa | Estado | Fecha | Próxima condición |
| --- | --- | --- | --- |
| 0 — Inspección y línea base | COMPLETED | 2026-08-02 | Aprobación recibida |
| 1 — Bloqueos preexistentes | COMPLETED | 2026-08-02 | Aprobación explícita para Etapa 2 |
| 2 — Contratos y arquitectura | COMPLETED | 2026-08-02 | Aprobación explícita para Etapa 3 |
| 3 — Artifact Registry e identidades | COMPLETED | 2026-08-02 | Aprobación recibida |
| 4 — Separación de Compose | COMPLETED | 2026-08-02 | Aprobación explícita para Etapa 5 |
| 5 — Backend y frontend degradables | COMPLETED | 2026-08-02 | Aprobación explícita para Etapa 6 |
| 6 — Runtime reconciliador GPU | COMPLETED | 2026-08-02 | Aprobación recibida |
| 7 — Red y seguridad GCP | COMPLETED | 2026-08-02 | Aprobación explícita para Etapa 8 |
| 8 — GitHub Actions | COMPLETED | 2026-08-02 | Aprobación explícita para Etapa 9 |
| 9 — Rollback integral | COMPLETED | 2026-08-03 | Aprobación recibida |
| 10 — Aceptación E2E | COMPLETED | 2026-08-03 | Aprobación explícita para Etapa 11 |
| 11 — Puesta en servicio | IN_PROGRESS | 2026-08-03 | Cutover aplicado; validación GPU y administrativa diferida por instrucción del usuario |
| 12 — Documentación final | PENDING | — | Cerrar primero las diferencias `NO VERIFICADO` de Etapa 11 o aceptar expresamente su diferimiento |

## Registro de la Etapa 1

- **Estado:** `COMPLETED`.
- **Fecha:** 2026-08-02.
- **Commit:** `293eff5` (`fix: harden chat sessions and RAG rollback`);
  cierre documental en el commit posterior de esta rama. No se realizó push.
- **Archivos modificados:** port y dependencias del chat, router, caso de uso,
  repositorio SQLAlchemy, fakes/pruebas, scripts de promoción/transacción y esta
  fuente documental. El inventario exacto se obtiene con
  `git diff --name-status origin/dev/agosto...HEAD`.
- **Recursos GCP modificados:** ninguno.
- **Pruebas ejecutadas:** ver `09-test-evidence.md`.
- **Resultado:** `862 passed`, `1 skipped`, `1 warning` y `4 subtests passed`
  en la regresión completa del backend; lint aprobado.
- **Evidencias:** resultados locales sin datos productivos ni secretos.
- **Riesgos pendientes:** el workflow actual todavía no consume el instalador
  transaccional por prohibición expresa de esta etapa; el runner local usa
  Python 3.14.4 aunque el proyecto fija 3.11 y su puente nativo de executor queda
  bloqueado, por lo que la regresión se ejecutó con un harness temporal
  documentado y no versionado.
- **Rollback disponible:** reversión de rama para código y comando transaccional
  para entorno/RAG.
- **Próxima etapa:** Etapa 2, exclusivamente tras aprobación explícita.

La rama se publicó como respaldo al iniciar la Etapa 2, por autorización
expresa, conservando `main` y `dev/agosto` sin cambios.

## Registro de la Etapa 2

- **Estado:** `COMPLETED`.
- **Fecha:** 2026-08-02.
- **Commit funcional:** `9d92e795` (`feat: formalize runtime and release
  contracts`). El cierre documental se registra en el commit posterior de esta
  rama.
- **Archivos modificados:** contratos de disponibilidad, ports y contrato del
  proveedor, composición/health del chat, correlación HTTP, modelo y esquema de
  release, pruebas de contrato y documentación arquitectónica. El inventario
  exacto está en el diff del commit.
- **Recursos GCP modificados:** ninguno.
- **GitHub modificado:** únicamente publicación de esta rama como respaldo; no
  se modificaron Actions, secrets, variables, environments, PR ni `main`.
- **Pruebas ejecutadas:** ver `09-test-evidence.md`.
- **Resultado:** `596 passed`, `1 skipped`, `1 warning` para `llm_chat`;
  `68 passed` para entorno/RAG/migraciones; `888 passed`, `1 skipped`,
  `1 warning` y `4 subtests passed` para todo el backend; Ruff aprobado.
- **Evidencias:** Python 3.11.15, checkout escribible del commit exacto y sin el
  harness temporal de Python 3.14.
- **Riesgos pendientes:** la separación de Compose, la eliminación del warmup
  bloqueante, el firewall privado, la reconciliación GPU y la publicación del
  manifiesto pertenecen a etapas posteriores. El ejemplo de release no es
  desplegable.
- **Rollback disponible:** revertir el commit funcional y el commit documental
  de esta etapa. No existe estado productivo ni recurso cloud que restaurar.
- **Próxima etapa:** Etapa 3, exclusivamente tras aprobación explícita.

## Registro de la Etapa 3

- **Estado:** `COMPLETED`.
- **Fecha:** 2026-08-02.
- **Commits funcionales:** `cae76eec` (`feat: establish immutable artifact
  identities`), `6e2969d6` (`test: require digest-pinned build bases`) y
  `515d343a` (`fix: identify Ollama runtime OCI version`) y `7b9cd4da`
  (`ci: validate WIF federation without deployment`). El inventario de digests
  y los cierres documentales se registran en commits separados de esta rama.
- **Archivos modificados:** Dockerfiles de backend/frontend/runtime, contratos
  y validadores de artefactos, política/contrato declarativo de GCP, inventario
  de digests, pruebas, workflow manual y documentación. No se modificaron
  archivos Compose.
- **Recursos GCP modificados:** cinco APIs habilitadas; repositorio regional
  `hemovet-images`; tres service accounts; pool `hemovet-github`; provider
  `github-main-production`; IAM mínimo a nivel de repositorio y service account;
  condición endurecida con IDs numéricos verificados.
- **GitHub modificado:** commit aislado de `main` `e30c4224` con `[skip ci]`,
  trigger manual WIF y environment `production` sin secrets ni protección. El
  push produjo cero runs; la única ejecución fue el dispatch manual autorizado.
- **Imágenes publicadas:** backend, frontend y `ollama-runtime` para el SHA
  `515d343ac805779f94be9277376bdadf5516154d`, todas con referencia canónica por
  digest, SBOM y provenance. Ver `13-artifact-registry-iam-wif.md`.
- **Pruebas ejecutadas:** ver `09-test-evidence.md`.
- **Resultado local/remoto:** regresión Python 3.11 con `898 passed`, `1
  skipped`, `1 warning` y `4 subtests passed`; Ruff aprobado; frontend aprobado;
  contratos focales `16 passed`; IAM, claves, inmutabilidad y digests leídos de
  vuelta desde GCP.
- **WIF real:** run `30762294120` `success`; autenticación sin clave, publicación
  `wif-validation@sha256:0998efbb07674eeb14b282c60bca44651feae2a6b83b632d9c650dce9cfaf989`
  y rechazo explícito del job sin environment. Deploy y jobs productivos
  quedaron `skipped`.
- **Riesgos pendientes:** `main` y el environment carecen de protección porque
  la credencial GitHub actual no es administradora; SSH permanece como acceso
  legado; Container Scanning sigue deshabilitado y cleanup en `dry-run`.
- **Rollback disponible:** retirada ordenada de bindings, provider, pool y
  cuentas; conservar el repositorio mientras existan digests referenciables;
  deshabilitar APIs solo tras comprobar consumidores. Ver
  `06-rollback-runbook.md`.
- **Próxima etapa:** Etapa 4 únicamente tras aprobación explícita; la
  autorización de cierre de Etapa 3 no se interpreta como permiso de avance.

## Registro de la Etapa 4

- **Estado:** `COMPLETED`.
- **Fecha:** 2026-08-02.
- **Commit funcional:** `b2169408c6baa5b109bbf235907c5cf3658959b1`
  (`feat: separate application and GPU compose`). El cierre de estado se
  registra en el commit documental posterior de esta rama.
- **Archivos modificados:** Compose base/local/producción/GPU y Caddy local;
  ejemplos de entorno separados; validador de topología y entorno productivo;
  pruebas; README y fuente documental. Inventario detallado en
  `14-compose-separation.md` y en el commit funcional.
- **Recursos GCP modificados:** ninguno.
- **GitHub modificado:** ninguno; no se cambiaron workflow, secrets, variables,
  environments, ramas protegidas ni `main`.
- **Pruebas ejecutadas:** ver `09-test-evidence.md`.
- **Resultado:** tres topologías válidas y exactas; contratos focales `77
  passed`; regresión Python 3.11 con `912 passed`, `1 skipped`, `1 warning` y `4
  subtests passed`; Ruff completo aprobado; frontend `103 passed`, Biome,
  TypeScript y build aprobados.
- **Evidencias:** producción efectiva sin Ollama ni builds; GPU efectiva con
  dos servicios, digest único, bind privado, reserva NVIDIA y volumen de
  modelos; desarrollo conserva Ollama local sin publicar `11434`.
- **Riesgos pendientes:** health/backend/frontend degradables (Etapa 5),
  reconciliación y validación real GPU (Etapa 6), firewall exclusivo (Etapa 7)
  e integración del workflow inmutable (Etapa 8).
- **Rollback disponible:** reversión normal del commit funcional y documental;
  no existe estado de contenedor/volumen/cloud que restaurar porque no se
  ejecutó ningún stack.
- **Próxima etapa:** Etapa 5 únicamente tras aprobación explícita. Este cierre
  no autoriza adaptación del backend/frontend ni despliegues.

## Registro de la Etapa 5

- **Estado:** `COMPLETED`.
- **Fecha:** 2026-08-02.
- **Commits funcionales:** `1c234329a948d433b3968233b5d176fe3e0830d0`
  (`feat: degrade chat without blocking core`) y
  `105e8aa105795356d67a1f682849799033e8cd98` (`fix: normalize streamed
  provider errors`). El cierre documental y su adenda se registran en commits
  posteriores de esta rama.
- **Archivos modificados:** composición, ports/adaptadores, health, errores
  públicos y pruebas de `llm_chat`; API/tipos/página/mocks/pruebas del frontend;
  fuente documental. El inventario detallado está en
  `15-degradable-backend-frontend.md` y en ambos commits.
- **Recursos GCP modificados:** ninguno.
- **GitHub modificado:** solo se publicó al inicio el respaldo autorizado de
  los commits de Etapa 4. No se cambiaron Actions, secrets, variables,
  environments, PR, `main` o `dev/agosto`.
- **Pruebas ejecutadas:** ver `09-test-evidence.md`.
- **Resultado:** Python 3.11.15 con `924 passed`, `1 skipped`, `1 warning` y `4
  subtests passed`; `llm_chat` con `608 passed`, `1 skipped`; Ruff completo;
  frontend `108 passed`, Biome, TypeScript y build; dashboard E2E `22 passed`;
  tres topologías Compose válidas e inalteradas.
- **Evidencias:** proveedor ausente/timeout/recuperación, historial accesible,
  RAG requerido degradado, identidad separada de residencia y polling de 15
  segundos probados sin runtime productivo.
- **Riesgos pendientes:** GPU real e inferencia siguen `NO VERIFICADO`; red
  privada/firewall, workflow inmutable y gates de despliegue corresponden a
  Etapas 6, 7 y 8. Se mantiene temporalmente `llm_ready` como alias.
- **Rollback disponible:** revertir conjuntamente commit funcional y cierre
  documental; no hay datos, schema, GCP o runtime que restaurar. Ver
  `06-rollback-runbook.md`.
- **Próxima etapa:** Etapa 6 únicamente tras aprobación explícita. Este cierre
  no autoriza modificar o encender la VM GPU.

## Registro de la Etapa 6

- **Estado:** `COMPLETED`.
- **Fecha:** 2026-08-02.
- **Commits funcionales:** `ce8a82ea` (`feat: reconcile immutable GPU runtime
  at boot`), `4d96835d` (`fix: prepare GPU service namespace before startup`),
  `52dfa378` (`fix: install NVIDIA CDI spec atomically`), `70c32b38` (`fix:
  preserve historical GPU releases across bootstrap upgrades`) y `58a1c15`
  (`fix: validate GPU residency on every boot`). El cierre documental se
  registra en el commit que contiene esta actualización.
- **Archivos modificados:** Compose GPU, contrato/manifiestos de release,
  scripts y unidad `systemd` bajo `deploy/gpu/`, pruebas de runtime y esta
  fuente documental. El inventario técnico completo está en
  `16-gpu-runtime-reconciliation.md`.
- **Recursos GCP modificados:** snapshot regional recuperable del boot disk;
  asociación de la service account GPU dedicada; metadata
  `hemovet-gpu-desired-release`; instalación persistente del bundle, unidad,
  estado y volumen en el boot disk. El acceso SSH temporal fue retirado y su
  metadata original restaurada.
- **Pruebas ejecutadas:** contratos focales, checksum del bundle, Bash,
  ShellCheck, Ruff, regresión Python 3.11, topologías Compose, arranque real,
  identidad del modelo, inferencia L4, stop/start, reinicio de contenedor,
  idempotencia, revisión inválida y rollback en ambos sentidos. Ver
  `09-test-evidence.md`.
- **Resultado:** Python 3.11.15 con `941 passed`, `1 skipped`, `1 warning` y `4
  subtests passed`; contratos GPU `17 passed`; Ruff y ShellCheck aprobados;
  tres topologías Compose válidas; runtime final `full_gpu`, modelo y
  cuantización exactos, revisión aprobada restaurada y VM `TERMINATED`.
- **Evidencias:** `/api/tags`, `/api/show`, `/api/ps`, `nvidia-smi` host y
  contenedor, métricas versionadas, hashes del volumen, estados GCP y logs
  sanitizados. Ver `16-gpu-runtime-reconciliation.md`.
- **Riesgos pendientes:** firewall interno amplio, tags públicos heredados,
  deletion protection deshabilitada y datos/volúmenes históricos conservados.
  Red y endurecimiento corresponden a la Etapa 7.
- **Rollback disponible:** snapshot previo `READY`; revisión anterior
  conservada; `rollback-release.sh --previous` probado de ida y vuelta sin
  cambiar pesos. Ver `06-rollback-runbook.md`.
- **Próxima etapa:** Etapa 7 únicamente tras aprobación explícita. Este cierre
  no autoriza firewall, OS Login/IAP, tags o protección contra eliminación.

## Registro de la Etapa 7

- **Estado:** `COMPLETED`.
- **Fecha:** 2026-08-02.
- **Commit funcional:** `cf0f4c5f31f952f02a0227a050e2be84ffcabc3d`
  (`feat: power off GPU after failed bootstrap`). El cierre documental se
  registra en el commit que contiene esta actualización.
- **Archivos modificados:** unidad `OnFailure`, script de evidencia y apagado,
  instalador y manifiesto del bundle GPU, pruebas de bootstrap, manifiestos de
  release y documentación bajo `docs/implementation/prod-gpu-migration/`.
  El inventario exacto está en `17-gcp-network-security.md` y en ambos commits.
- **Recursos GCP modificados:** cinco reglas de firewall específicas; retirada
  de las reglas amplias `allow-ollama-internal` y `default-allow-rdp`; API IAP;
  bindings condicionados IAP, OS Admin Login y Service Account User; OS Login
  en la GPU; tags de la GPU; `deletionProtection` y `autoDelete` de ambos boot
  disks; instalación del bundle y metadata de revisión GPU. No se cambiaron
  VPC, subred, rutas, IPs, discos, imágenes ni modelo.
- **Pruebas ejecutadas:** acceso IAP/OS Login repetido, recuperación
  administrativa, conectividad real producción→GPU, Connectivity Tests
  positivos/negativos, sondas TCP públicas, fallo real con guest poweroff,
  posterior arranque válido, idempotencia, checksums, ShellCheck, Ruff,
  contratos focales y regresión completa Python 3.11. Ver
  `09-test-evidence.md`.
- **Resultado:** `18 passed` en contratos GPU; `942 passed`, `1 skipped`, `1
  warning` y `4 subtests passed` en backend; Ruff y ShellCheck aprobados;
  `10.128.0.2/32 → 10.128.0.3:11434` permitido y el resto rechazado; IAP
  funcional; apagado automático probado; snapshot `READY`; GPU final
  `TERMINATED`.
- **Evidencias:** matriz exacta, IAM, operaciones, métricas, costos y estado
  final en `17-gcp-network-security.md`. No se versionaron claves, tokens,
  prompts, respuestas ni valores secretos.
- **Riesgos pendientes:** `default-allow-ssh` continúa público para no romper
  el workflow legado; OS Login de producción sigue sin activarse; producción
  conserva la Default Compute SA; dos miembros humanos mantienen `Owner`; la
  IP privada GPU depende de conservar la instancia; el disco GPU está al 74%.
- **Rollback disponible:** la denegación total se deshabilitó/revalidó de forma
  controlada; claves temporales y perfiles administrativos se restauraron; el
  runtime anterior y snapshot siguen disponibles. La reversión integral y
  segura de cada control está en `06-rollback-runbook.md`.
- **Próxima etapa:** Etapa 8 únicamente tras aprobación explícita. Este cierre
  no autoriza modificar GitHub Actions, secrets, variables, environments ni
  desplegar la aplicación.

## Registro de la Etapa 8

- **Estado:** `COMPLETED` para workflow, WIF/IAP, artefactos y manifiesto; no
  se realizó un despliegue productivo.
- **Fecha:** 2026-08-02 local; evidencia GitHub finalizada 2026-08-03 UTC.
- **Commits funcionales:** `42300ced` (`feat: publish and deploy immutable
  releases via WIF`), `f97fb1ce` (`fix: validate build metadata digest`),
  `2aac3598` (`fix: project private provider into releases`), `af5ab60b`
  (`fix: bind release to RAG corpus schema`) y `778ecda0` (`fix: gate GPU
  metadata behind manual deploy`). El cierre documental es el commit siguiente.
- **Archivos modificados:** workflow productivo, health gate Compose, contratos
  y scripts de artefactos/release/RAG, scripts versionados `deploy/ci` y
  `deploy/prod`, pruebas backend/frontend y documentación. Inventario completo
  en `18-github-actions-immutable-deployment.md`.
- **Recursos GCP modificados:** IAM de la identidad CI para viewer, túnel IAP
  condicionado y metadata GPU condicionada mediante un rol personalizado. El
  provider WIF se amplió temporalmente y quedó restaurado a `main` exacto.
- **GitHub modificado:** nueva definición solo en la rama; runs manuales de
  validación/publicación y un artefacto no secreto. Secrets, variables,
  environment, `main` y ramas protegidas no cambiaron.
- **Resultado:** release `af5ab60b…` publicada con tres digests, SBOM SPDX,
  SLSA provenance y manifiesto coherente; dos validaciones WIF/IAP consecutivas;
  rechazo final de rama/environment no autorizados.
- **Pruebas:** Python 3.11 `958 passed`, `1 skipped`, `4 subtests`; Ruff,
  frontend `108 passed`, E2E `8 passed`, Compose, Caddy, Bash y actionlint.
- **Riesgos pendientes:** OS Login/SA runtime/SSH de producción requieren
  cutover; no se ejecutó deploy o rollback real; scanning deshabilitado;
  environment sin reviewers. No impiden cerrar la validación limitada, pero sí
  impiden afirmar puesta en servicio.
- **Rollback:** workflow anterior continúa en `main`; selección por manifiesto
  previo y scripts transaccionales preparados; IAM Stage 8 es removible. Ver
  `06-rollback-runbook.md`.
- **Próxima etapa:** Etapa 9 únicamente tras aprobación explícita. Este cierre
  no autoriza desplegar ni retirar el acceso de emergencia.

## Registro de la Etapa 9

- **Estado:** `COMPLETED` para la validación integral aislada; no se ejecutó
  rollback ni cutover productivo.
- **Fecha:** 2026-08-02 local; evidencia GitHub finalizada 2026-08-03 UTC.
- **Commit funcional:** `ee9fa759670caa56eaceadc40b6561516ab9949f`
  (`feat: validate coordinated immutable rollback`). El cierre documental se
  registra en el commit que contiene esta actualización.
- **Archivos modificados:** validador coordinado, deploy transaccional,
  selector de metadata GPU, contratos de health, pruebas, manifiestos reales y
  documentación. Inventario completo en `19-integral-rollback-validation.md`.
- **Recursos GCP modificados:** metadata GPU se cambió de forma reversible
  `515d… → af5… → 515d…` con la VM apagada; el valor final coincide byte por
  byte con el inicial. No se modificó producción, red, IAM, discos o datos.
- **GitHub modificado:** commit funcional publicado en la rama y run manual
  `30778878989`; WIF rechazó correctamente la rama no autorizada, por lo que no
  hubo build/push, metadata, deploy ni smoke.
- **Resultado:** regresión Python 3.11 con `966 passed`, `1 skipped` y `4
  subtests`; gates focales, Ruff, Bash, ShellCheck, checksums y tres topologías
  Compose aprobados. El candidato real arrancó aisladamente y dos fallos
  consecutivos restauraron entorno, RAG, enlaces, digests y datos sintéticos.
- **Evidencias:** manifiesto `af5…`, tres digests reales, entorno reconstruido
  con digest exacto, rollback repetible y ciclo real de metadata GPU. Ver
  `09-test-evidence.md` y `19-integral-rollback-validation.md`.
- **Riesgos pendientes:** solo existe un release completo histórico; la imagen
  publicada `af5…` conserva un probe lento ya corregido en código, pero aún no
  republicado por la restricción WIF. El rollback vivo entre dos manifiestos
  completos queda para una ventana autorizada posterior.
- **Rollback disponible:** revertir con commits normales el cierre documental
  y `ee9fa759`; metadata GPU ya restaurada, snapshot conservado y producción
  intacta. Ver `06-rollback-runbook.md`.
- **Próxima etapa:** Etapa 10 únicamente tras aprobación explícita. Este cierre
  no autoriza publicar desde `main`, desplegar ni encender la GPU.

## Registro de la Etapa 10

- **Estado:** `COMPLETED` para publicación y aceptación integral aislada; no
  se realizó cutover público.
- **Fecha:** 2026-08-03.
- **Revisión funcional:** `e7713a72369bb9365f6d5323e165fbf84488bfb4`
  (merge controlado de PR 29); contiene `ee9fa759` y la cadena funcional
  `0b41fd95`, `fbeec829`, `8a24cdf5`, `8b0666fa` y
  `c81950b31d0fb3f8018537e7c792fe7016c97dd2`. El cierre documental se
  registra en los commits posteriores de esta rama.
- **Archivos modificados:** contratos y validaciones de chat seguro incluidos
  en la revisión funcional; manifiestos finales y de rollback; prueba
  versionada de evidencia; informe y métricas sanitizadas; documentación.
  Inventario completo en `20-stage10-final-acceptance.md`.
- **Recursos GCP modificados:** tres imágenes nuevas en Artifact Registry; la
  GPU se encendió 449.523 segundos para validar la revisión y quedó
  `TERMINATED`; su metadata deseada volvió exactamente al valor previo y el
  snapshot siguió `READY`. La metadata SSH temporal de producción fue
  restaurada byte por byte sin reinicio.
- **GitHub modificado:** PR 29 fusionado a `main`; run
  `30794470808` exitoso para tests/build/publicación. Los jobs
  `publish_gpu_release`, `deploy_prod` y smoke productivo quedaron
  `skipped` al no existir aprobación manual.
- **Resultado:** CI Python 3.11, Ruff, frontend y E2E crítico aprobados; 19 casos
  de aceptación aislada pasaron; Qwen y el runtime exactos ejecutaron en la
  NVIDIA L4; persistencia, aislamiento, RAG, SSE, seguridad clínica,
  recuperación y modo degradado quedaron demostrados.
- **Evidencias:** manifiestos en `deploy/releases/`, informe JSON y métricas
  GPU sanitizados bajo `evidence/`, y detalle reproducible en
  `20-stage10-final-acceptance.md`.
- **Riesgos pendientes:** no hubo cutover vivo ni prueba sobre datos clínicos
  productivos; producción conserva Ollama local, identidad/SSH heredados y la
  revisión pública anterior. Una caída por descarte de red recorrió el contrato
  de timeout reintentable `504` en 10.2 segundos, mientras la ausencia
  inmediata conserva el contrato unitario `503`; Etapa 11 debe confirmar si
  ese presupuesto operativo es aceptable antes del cutover.
- **Rollback disponible:** revisión completa
  `af5ab60b418bc931c4c4cabc8b8ef92893325fb6` con backend, frontend, runtime
  GPU, modelo y RAG fijados por digest; snapshot GPU preservado; estado público
  anterior nunca fue sustituido.
- **Próxima etapa:** Etapa 11 únicamente tras aprobación explícita. Este cierre
  no autoriza cutover, retirar Ollama local, modificar datos o retirar accesos
  de emergencia.

## Registro de la Etapa 11

- **Estado:** `IN_PROGRESS`. El cutover de aplicación terminó correctamente;
  las pruebas live de GPU/chat y el cutover administrativo quedaron
  expresamente detenidos por la instrucción del usuario de no ejecutar más
  tests el 2026-08-03.
- **Fecha:** 2026-08-03.
- **Revisión activa:** `069df45f7becbf1bf698a3ee6a8a9305e3aa4d1f`.
- **Commits correctivos:** `1be07112`, `cbf61217` y `44b9fbf0`; PR 30, PR 31
  y PR 32. Los dos primeros corrigieron portabilidad del host y el tercero
  restauró lectura del corpus para contenedores no root.
- **Archivos modificados:** workflow y despliegue ya versionados en las
  revisiones anteriores; prueba de permisos del release; informe integral de
  pruebas y documentación de puesta en servicio. Inventario en
  `22-stage11-controlled-service.md`.
- **Recursos GCP modificados:** snapshot
  `hemovet-prod-pre-stage11-20260803`; service account de producción cambiada
  a `hemovet-prod-runtime`; metadata GPU deseada actualizada a `069df45f…`;
  GPU encendida temporalmente y detenida; Artifact Registry recibió los tres
  artefactos de la revisión. No cambiaron IPs, discos de datos, VPC, subred ni
  firewall en esta etapa.
- **GitHub modificado:** PR 30–32 fusionados a `main`; workflow manual
  `30827420990` completado con `success`. Los secrets SSH antiguos siguen
  presentes y no se modificaron porque IAP/OS Login no alcanzó las dos
  validaciones requeridas.
- **Resultado verificado:** backend/frontend por digest, entorno modo `0600`,
  RAG activo con 4,696 chunks, migración `0012`, HTTP público 200, núcleo/DB/
  Chroma/RAG listos y chat degradado con proveedor apagado. Los conteos
  productivos permanecieron exactamente en 46 usuarios, 81 mascotas, 140
  análisis, 2,575 parámetros, 313 sesiones, 351 turnos y 683 mensajes.
- **No verificado por instrucción posterior:** aplicación de la revisión GPU
  durante ese arranque, `/api/show`, `/api/ps`, inferencia `full_gpu`, los tres
  modos de chat, memoria/streaming live, recuperación posterior, dos accesos
  IAP/OS Login en producción y retirada de SSH público/secrets antiguos.
- **Evidencias:** workflow `30827420990`, transacción
  `20260803T153601.245677433Z-73024`, hashes/digests en
  `22-stage11-controlled-service.md`, snapshots `READY` y backup inmediato en
  `/var/backups/hemovet-stage11/pre-e7713a…` sobre producción.
- **Riesgos pendientes:** la aplicación opera intencionalmente degradada con
  GPU apagada; la metadata GPU queda `pending_boot_validation`; el acceso SSH
  de emergencia, la regla abierta heredada y los secrets antiguos se conservan
  hasta una validación administrativa posterior. Ollama local sigue preservado
  como orphan y no forma parte del Compose activo.
- **Rollback disponible:** `previous` apunta a
  `/home/ubuntu/hemogramas-proyectoICC`; el entorno anterior está respaldado
  byte por byte; RAG anterior coincide con el activo; existe dump PostgreSQL
  validado; revisión `af5ab60b…`, snapshots y metadata previa permanecen
  disponibles.
- **Próxima condición:** no declarar `COMPLETED AND VALIDATED` ni retirar
  accesos de emergencia hasta resolver o aceptar explícitamente los elementos
  `NO VERIFICADO` anteriores.
