# Inventario GCP

Proyecto: `project-5b36701c-f44f-4c03-a12`.
Número: `371832959385`.
Organización: `504414443697`.

## Línea base previa a la Etapa 3

Capturada el 2026-08-02 mediante una copia temporal privada de la configuración
de `gcloud`; la configuración original no se modificó.

| Recurso | Estado verificado antes de mutar |
| --- | --- |
| Región y zona principal | `us-central1`, `us-central1-a` |
| VM producción | `hemovet-prod`, `RUNNING`, service account default de Compute Engine |
| VM GPU | `hemovet-llm-gpu`, `TERMINATED`, service account default de Compute Engine |
| Identidad de ambas VMs | `371832959385-compute@developer.gserviceaccount.com` |
| IP producción | externa `136.64.136.49`, privada `10.128.0.2` |
| IP GPU | externa `34.45.75.48`, privada `10.128.0.3` |
| Service accounts de usuario | solo la cuenta default de Compute Engine |
| Claves administradas por usuario de la cuenta default | ninguna |
| Custom roles del proyecto | ninguno |
| Workload Identity Pools | ninguno |
| Artifact Registry API | deshabilitada |
| Repositorios Artifact Registry | `NO VERIFICADO` hasta habilitar la API; no se asumió ausencia |

No se modificaron instancias para obtener este inventario. La Etapa 3 no
adjuntará las nuevas identidades a las VMs porque esa operación está fuera de
alcance.

## IAM preexistente del proyecto

| Rol | Principal |
| --- | --- |
| `roles/compute.instanceGroupManagerServiceAgent` | `serviceAccount:371832959385@cloudservices.gserviceaccount.com` |
| `roles/compute.serviceAgent` | `serviceAccount:service-371832959385@compute-system.iam.gserviceaccount.com` |
| `roles/owner` | dos usuarios humanos preexistentes |
| `roles/resourcemanager.organizationAdmin` | un usuario humano preexistente |
| `roles/resourcemanager.projectMover` | un usuario humano preexistente |
| `roles/serviceusage.serviceUsageAdmin` | un usuario humano preexistente |

La Etapa 3 no retirará ni alterará estos bindings. Ninguna identidad nueva
recibirá `Owner`, `Editor` o un rol básico.

## Inventario posterior a la Etapa 3

| Recurso | Identidad/estado |
| --- | --- |
| APIs nuevas | `artifactregistry`, `iam`, `iamcredentials`, `sts` y `cloudresourcemanager` |
| Artifact Registry | `hemovet-images`, Docker regional `us-central1`, tags inmutables, cleanup `dry-run` |
| URI | `us-central1-docker.pkg.dev/project-5b36701c-f44f-4c03-a12/hemovet-images` |
| CI/CD | `hemovet-github-cicd@project-5b36701c-f44f-4c03-a12.iam.gserviceaccount.com` |
| Producción futura | `hemovet-prod-runtime@project-5b36701c-f44f-4c03-a12.iam.gserviceaccount.com` |
| GPU futura | `hemovet-gpu-runtime@project-5b36701c-f44f-4c03-a12.iam.gserviceaccount.com` |
| WIF pool | `projects/371832959385/locations/global/workloadIdentityPools/hemovet-github` |
| WIF provider | `github-main-production`, GitHub OIDC, estado `ACTIVE` |
| Claves SA de usuario | ninguna en las tres cuentas nuevas |
| Almacenamiento reportado | `4216.688 MB` después de imágenes, attestations y prueba WIF |
| Identidad GitHub verificada | repositorio `1148021152`; propietario `115911218` |
| GitHub Environment | `production`, creado por el run WIF, sin secrets ni reglas de protección |

Las nuevas cuentas no están asociadas a las VMs. Al cerrar el aprovisionamiento,
`hemovet-prod` seguía `RUNNING` y `hemovet-llm-gpu` seguía `TERMINATED`; sus
cuentas, IPs y discos coincidían con la línea base.

La matriz IAM, dependencias, riesgos y comandos de eliminación están en
`13-artifact-registry-iam-wif.md`.

## Revisiones OCI presentes

La revisión canónica `515d343ac805779f94be9277376bdadf5516154d` quedó
publicada con los índices siguientes:

| Paquete | Digest canónico |
| --- | --- |
| `backend` | `sha256:c20b932993c97d6078d04033f72d2de132381f6a6a06580dc65be74d52b5191f` |
| `frontend` | `sha256:55b82e9e868247fc71d764f932610f0849db93fbe88b60261683f7894d305d7f` |
| `ollama-runtime` | `sha256:b526b1d4bc30d0cc641e0d2a186034b327c97de0171b1a47ce1c917d79604e5f` |

También permanecen los tres tags inmutables de la revisión bootstrap
`6e2969d6fa735473097d4f1c19af46263436bd66`. Nunca se desplegaron y están
documentados como supersedidos en `13-artifact-registry-iam-wif.md`. No se
publicó ningún tag `latest`.

La prueba federada publicó además el paquete no desplegable
`wif-validation:run-30762294120-1`, digest
`sha256:0998efbb07674eeb14b282c60bca44651feae2a6b83b632d9c650dce9cfaf989`.
Es evidencia del gate WIF y no pertenece a `hemovet.artifacts/v1`.

La validación final read-only mantuvo:

| VM | Estado | Service account | IP privada | IP externa | Disco |
| --- | --- | --- | --- | --- | --- |
| `hemovet-prod` | `RUNNING` | default Compute Engine | `10.128.0.2` | `136.64.136.49` | `hemovet-prod`, 50 GB |
| `hemovet-llm-gpu` | `TERMINATED` | default Compute Engine | `10.128.0.3` | `34.45.75.48` | `hemovet-llm-gpu`, 100 GB |

## Inventario posterior a la Etapa 6

La Etapa 6 modificó únicamente la VM GPU y creó su respaldo. El inventario
final, leído después del apagado, es:

| Campo | Estado final |
| --- | --- |
| VM | `hemovet-llm-gpu`, `TERMINATED` |
| Provisioning | `SPOT`, preemptible |
| Máquina/GPU | `g2-standard-4`, 1 × `nvidia-l4` |
| IPs | privada `10.128.0.3`; externa estática `34.45.75.48` |
| Service account | `hemovet-gpu-runtime@project-5b36701c-f44f-4c03-a12.iam.gserviceaccount.com` |
| Scopes | `cloud-platform`; acceso efectivo limitado por IAM |
| Claves SA de usuario | ninguna |
| Boot disk | `hemovet-llm-gpu`, 100 GB, sin cambio de tipo/tamaño, `autoDelete=true` |
| Metadata | `install-nvidia-driver`, `ssh-keys` originales y `hemovet-gpu-desired-release` |
| Tags | `http-server`, `https-server`, sin cambios |
| Deletion protection | `false`, sin cambios |
| Revisión deseada | `515d343ac805779f94be9277376bdadf5516154d` |
| Runtime deseado | `sha256:b526b1d4bc30d0cc641e0d2a186034b327c97de0171b1a47ce1c917d79604e5f` |
| Bundle | `sha256:5e2a5eb03f9fcdf5a1373447f3d6da13a16617a599db697e515d4039396a2c26` |

Respaldo creado antes de modificar el boot disk:

| Campo | Valor |
| --- | --- |
| Snapshot | `hemovet-llm-gpu-pre-stage6-20260802` |
| Estado/ubicación | `READY`, `us-central1` |
| Source disk ID | `574351621454120040` |
| Tamaño lógico | 100 GB |
| Almacenamiento reportado | 58,891,150,336 bytes |

No se creó, eliminó, redimensionó ni reasoció ningún disco. La IP regional
`hemovet-llm-gpu-static-ip` continúa `IN_USE` y asociada a la misma VM.

Producción se verificó después de la prueba: `hemovet-prod` seguía `RUNNING`,
con `lastStartTimestamp=2026-07-02T06:45:52.411-07:00`, IPs
`10.128.0.2`/`136.64.136.49`, service account default y boot disk originales.

El detalle del runtime, mutaciones, costos y rollback está en
`16-gpu-runtime-reconciliation.md`. Firewall, VPC, subred, reglas, tags e IPs
no fueron modificados en esta etapa.

## Inventario posterior a la Etapa 7

Estado leído después del apagado final de la GPU:

| Recurso | Estado final |
| --- | --- |
| `hemovet-prod` | `RUNNING`; `deletionProtection=true`; boot disk `autoDelete=false`; sin restart de aplicación |
| `hemovet-llm-gpu` | `TERMINATED`; `deletionProtection=true`; boot disk `autoDelete=false` |
| IPs producción | privada `10.128.0.2`; externa estática `136.64.136.49`, sin cambios |
| IPs GPU | privada NIC-bound `10.128.0.3`; externa estática `34.45.75.48`, sin cambios |
| Identidad GPU | `hemovet-gpu-runtime@project-5b36701c-f44f-4c03-a12.iam.gserviceaccount.com` |
| Tags GPU | solo `hemovet-gpu-runtime` |
| OS Login | GPU `TRUE`; producción `UNSET` hasta migrar el workflow legado |
| API nueva | `iap.googleapis.com` |
| Snapshot | `hemovet-llm-gpu-pre-stage6-20260802`, `READY`, conservado |
| Revisión GPU deseada | `515d343ac805779f94be9277376bdadf5516154d`, `pending_boot_validation` |
| Bundle GPU | `sha256:b781a68bd132c7c29ddd5def3c1309c933b55026a3782ecd27494372476aaf65` |

Reglas específicas de la VPC `default`:

| Regla | Prioridad | Acción | Origen | Destino | Puerto |
| --- | ---: | --- | --- | --- | --- |
| `hemovet-allow-prod-to-gpu-ollama` | 700 | ALLOW | `10.128.0.2/32` | SA GPU | TCP 11434 |
| `hemovet-deny-other-to-gpu-ollama` | 800 | DENY | `0.0.0.0/0` | SA GPU | TCP 11434 |
| `hemovet-allow-iap-ssh-gpu` | 700 | ALLOW | `35.235.240.0/20` | SA GPU | TCP 22 |
| `hemovet-allow-iap-ssh-prod` | 700 | ALLOW | `35.235.240.0/20` | tag `hemovet` | TCP 22 |
| `hemovet-deny-unapproved-ingress-gpu` | 900 | DENY | `0.0.0.0/0` | SA GPU | todos |

Se eliminaron `allow-ollama-internal` y `default-allow-rdp`. Se preservó
temporalmente `default-allow-ssh` porque el workflow productivo sin modificar
aún lo utiliza; la denegación de prioridad 900 impide que esa regla alcance la
GPU. La aplicación productiva, los datos y los recursos de Artifact Registry
no se modificaron. El inventario ampliado, IAM y rollback están en
`17-gcp-network-security.md`.

## Inventario posterior a la Etapa 8

| Recurso | Estado final |
| --- | --- |
| Artifact Registry | `hemovet-images`, 7,190.672 MB, cleanup `dry-run=true` |
| Release OCI | `af5ab60b418bc931c4c4cabc8b8ef92893325fb6`, tres digests |
| WIF provider | `ACTIVE`, restringido nuevamente a repo/IDs/environment/`main`/workflow exactos |
| CI SA keys | cero claves administradas por usuario |
| Rol nuevo | `hemovetGpuReleasePublisher`: `instances.get/setMetadata` |
| Binding GPU | condicionado a `hemovet-llm-gpu` exacta |
| Binding IAP CI | condicionado a `10.128.0.2:22` |
| Producción | `RUNNING`, Default Compute SA, OS Login `UNSET`, sin restart |
| GPU | `TERMINATED`, sin cambio de metadata de release durante la etapa |
| Snapshot | `hemovet-llm-gpu-pre-stage6-20260802`, `READY`, 58,891,150,336 bytes |

No se cambiaron firewall, VPC, subred, rutas, IPs, discos o service accounts de
las VMs. La matriz IAM, los digests y los comandos de reversión están en
`18-github-actions-immutable-deployment.md` y `06-rollback-runbook.md`.

## Inventario posterior a la Etapa 9

La única mutación GCP fue una prueba reversible de la metadata
`hemovet-gpu-desired-release` con la GPU detenida:

```text
515d343a… / sha256:b526b1d4…
  -> af5ab60… / sha256:de0833bd…
  -> 515d343a… / sha256:b526b1d4…
```

El valor completo final coincide con el inicial, SHA-256
`5bf601f00844b4276de21f7932256dc39e9274d1ec4a99127f717502c6f7e57e`.
La VM permaneció `TERMINATED`; sus timestamps no cambiaron.

| Recurso | Estado final |
| --- | --- |
| Producción | `RUNNING`; start `2026-07-02T06:45:52.411-07:00`; sin restart |
| GPU | `TERMINATED`; revisión `515d343a…`; runtime `sha256:b526b1d4…` |
| Snapshot | `hemovet-llm-gpu-pre-stage6-20260802`, `READY`, 58,891,150,336 bytes |
| Artifact Registry | ningún tag `sha-ee9fa759…`; ningún objeto eliminado |
| IPs, firewall, IAM, discos | sin cambios |

No se encendió la GPU ni se accedió a PostgreSQL/Chroma productivos. La
evidencia ampliada está en `19-integral-rollback-validation.md`.
