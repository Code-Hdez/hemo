# Etapa 7 — Red, acceso administrativo y protección GCP

Fecha de ejecución: 2026-08-02.

## Resultado

La frontera de red del runtime GPU quedó cerrada. `hemovet-prod` puede alcanzar
`10.128.0.3:11434`; cualquier otro origen interno o externo es rechazado. La VM
GPU solo admite administración por IAP a TCP/22, tiene OS Login activo, no
conserva tags web y quedó apagada. No se desplegó ni reinició la aplicación de
producción.

La aplicación pública continuó disponible con la GPU apagada:

```text
https://hemovet.app/                    HTTP 200
/api/v1/chat/health                    HTTP 200
status                                 degraded
rag_ready / chroma_ready               true / true
llm_ready / gpu_active                 false / false
inference_device                       not_loaded
```

El endpoint público todavía corresponde al despliegue anterior y no expone los
campos nuevos `core_ready`/`chat_ready`; desplegar Etapa 5 está fuera del alcance
de esta etapa.

## Inventario previo

| Área | Estado anterior |
| --- | --- |
| GPU | `TERMINATED`, Spot `g2-standard-4`, NVIDIA L4 |
| IPs GPU | privada `10.128.0.3`; externa estática `34.45.75.48` |
| Puerto Ollama | regla `allow-ollama-internal`, `10.128.0.0/20 → tcp:11434`, sin target |
| Red interna | `default-allow-internal`, prioridad `65534`, todo TCP/UDP/ICMP desde `10.128.0.0/9` |
| Administración | `default-allow-ssh` y `default-allow-rdp` desde `0.0.0.0/0` |
| Tags GPU | `http-server`, `https-server` |
| OS Login | no configurado en metadata de proyecto ni de instancia |
| IAP API | deshabilitada |
| Identidad GPU | `hemovet-gpu-runtime@project-5b36701c-f44f-4c03-a12.iam.gserviceaccount.com` |
| Protección VMs | `deletionProtection=false` en ambas |
| Boot disks | `autoDelete=true` en ambos |
| Snapshot | `hemovet-llm-gpu-pre-stage6-20260802`, `READY` |

Se conservaron inventarios JSON privados de firewall, rutas, VPC/subred, VMs,
discos, direcciones, metadata, IAM, APIs y snapshot. No se copiaron valores SSH
a la documentación versionada.

## Matriz de firewall final

Las cinco reglas nuevas pertenecen a la VPC `default` y están habilitadas:

| Regla | Prioridad | Acción | Origen | Destino/selector | Protocolo |
| --- | ---: | --- | --- | --- | --- |
| `hemovet-allow-prod-to-gpu-ollama` | 700 | ALLOW | `10.128.0.2/32` | SA GPU dedicada | TCP 11434 |
| `hemovet-deny-other-to-gpu-ollama` | 800 | DENY | `0.0.0.0/0` | SA GPU dedicada | TCP 11434 |
| `hemovet-allow-iap-ssh-gpu` | 700 | ALLOW | `35.235.240.0/20` | SA GPU dedicada | TCP 22 |
| `hemovet-allow-iap-ssh-prod` | 700 | ALLOW | `35.235.240.0/20` | tag `hemovet` | TCP 22 |
| `hemovet-deny-unapproved-ingress-gpu` | 900 | DENY | `0.0.0.0/0` | SA GPU dedicada | todos |

La prioridad 700 autoriza únicamente los dos caminos necesarios; las
denegaciones 800/900 prevalecen sobre `default-allow-internal` y las reglas
públicas heredadas. Se eliminaron:

- `allow-ollama-internal`, que autorizaba toda la subred;
- `default-allow-rdp`, que publicaba TCP/3389 globalmente.

`default-allow-ssh` se conserva temporalmente. La regla total de la GPU la
anula para ese destino, pero sigue permitiendo el mecanismo SSH productivo del
workflow actual. Eliminarla antes de migrar `.github/workflows/deploy.yml` a
IAP/OS Login rompería el rollback autorizado y contradiría la prohibición de
modificar GitHub Actions en Etapa 7. Su retiro es un gate de Etapa 8, después de
dos despliegues IAP/WIF y un rollback.

## IAM e identidades administrativas

| Recurso | Rol | Principal | Restricción |
| --- | --- | --- | --- |
| Proyecto | `roles/iap.tunnelResourceAccessor` | `user:cdavidh1962@gmail.com` | `destination.port == 22` y destino `10.128.0.2` o `10.128.0.3` |
| `hemovet-prod` | `roles/compute.osAdminLogin` | mismo usuario | binding de instancia |
| `hemovet-llm-gpu` | `roles/compute.osAdminLogin` | mismo usuario | binding de instancia |
| SA producción actual | `roles/iam.serviceAccountUser` | mismo usuario | binding sobre esa SA |
| SA GPU | `roles/iam.serviceAccountUser` | mismo usuario | binding sobre esa SA |

El intento inicial de colocar `roles/iap.tunnelResourceAccessor` sobre una
instancia fue rechazado por GCP porque ese rol no es soportado allí; no creó
ningún binding. Se corrigió con un binding condicionado a nivel de proyecto.

Persisten dos miembros humanos con `roles/owner`, anteriores a la migración.
No se retiraron porque excede el alcance y podría bloquear administración del
proyecto. Por tanto, los bindings nuevos son mínimos, pero el privilegio
efectivo global de esos miembros sigue siendo un riesgo **ALTO** preexistente.

## IAP, OS Login y acceso de emergencia

- `iap.googleapis.com` quedó habilitada.
- `hemovet-llm-gpu` tiene metadata de instancia `enable-oslogin=TRUE`.
- Se realizaron dos conexiones IAP/OS Login independientes; la segunda validó
  `sudo` no interactivo.
- Después de activar la denegación total se repitió el acceso IAP con éxito.
- Una clave OS Login efímera fue retirada. El conjunto de material público
  preexistente se restauró semánticamente y el material privado local fue
  destruido.
- Producción se alcanzó por IAP con una clave de metadata efímera; sus cinco
  entradas previas se restauraron como conjunto exacto y la clave temporal no
  permanece.

OS Login de producción queda deliberadamente `UNSET`: activarlo haría que el
guest ignorase las claves de metadata usadas por el workflow productivo actual.
IAP ya está listo y probado, pero la activación definitiva se realizará junto
al rediseño del workflow en Etapa 8.

Procedimiento normal:

```bash
gcloud compute ssh hemovet-llm-gpu \
  --project=project-5b36701c-f44f-4c03-a12 \
  --zone=us-central1-a --tunnel-through-iap

gcloud compute ssh hemovet-prod \
  --project=project-5b36701c-f44f-4c03-a12 \
  --zone=us-central1-a --tunnel-through-iap
```

Procedimiento de emergencia si OS Login GPU impide acceso:

1. Confirmar que la VM está apagada y que el snapshot sigue `READY`.
2. Ejecutar por API de control:

   ```bash
   gcloud compute instances add-metadata hemovet-llm-gpu \
     --project=project-5b36701c-f44f-4c03-a12 \
     --zone=us-central1-a --metadata=enable-oslogin=FALSE
   ```

3. Mantener la regla IAP, añadir una clave temporal solo a metadata de
   instancia, acceder por IAP y corregir la causa.
4. Retirar solo esa clave, restaurar el valor anterior y volver a probar IAP.
5. No abrir SSH público de la GPU.

## Tags, IP y protección de recursos

La GPU conserva únicamente el tag `hemovet-gpu-runtime`; se retiraron
`http-server` y `https-server`. Producción conserva sus tags originales.

Decisión de direccionamiento:

```text
Decisión: conservar 10.128.0.3 ligada a la NIC de la instancia.
Alternativas: reserva interna independiente o Cloud DNS privado.
Opción: NIC existente + deletion protection + boot disk preservado.
Motivo: una sola consumidora, sin recreación prevista y menor complejidad/costo.
Consecuencia: la dirección no sobrevive a eliminar/recrear la instancia.
Rollback: no aplica; no se creó ni cambió ninguna dirección.
```

Las dos IP externas estáticas permanecen `IN_USE` y sin cambios. La externa de
la GPU se conserva por requisito, pero no tiene puertos de servicio accesibles.

Ambas VMs quedaron con `deletionProtection=true`. Sus boot disks quedaron con
`autoDelete=false`. Detener, iniciar y reiniciar sigue permitido; eliminar una
VM requiere retirar primero la protección y aun así el boot disk se conserva.

El primer comando de `autoDelete` usó por error `deviceName=persistent-disk-0` y
GCP lo rechazó sin mutar el disco. Se resolvió usando los nombres reales
`hemovet-prod` y `hemovet-llm-gpu`.

## Snapshot y almacenamiento

El snapshot exigido no se eliminó:

```text
name:          hemovet-llm-gpu-pre-stage6-20260802
status:        READY
location:      us-central1
sourceDiskId:  574351621454120040
storageBytes:  58,891,150,336 (54.847 GiB)
```

A la tarifa regional consultada el 2026-08-02, su almacenamiento cuesta
aproximadamente `USD 0.0038/h` o `USD 2.74/730 h`. Debe conservarse hasta que
exista otro respaldo probado y aprobación explícita de eliminación.

La raíz GPU continúa al 74%:

```text
size=102,888,095,744 used=75,715,837,952 available=27,155,480,576
images=15.07 GB; containers=128.9 MB; volumes=26.81 GB; build cache=6.581 GB
17 contenedores heredados; 13 volúmenes; 1 contenedor runtime activo al medir
```

No se borró nada. Una etapa posterior deberá inventariar propietarios,
respaldos y referencias; primero podrá proponer eliminar cache no activo y
después stacks/volúmenes heredados con aprobación destructiva específica. No
usar `docker system prune` ni eliminar volúmenes a ciegas.

## Apagado automático por fallo

El bundle `sha256:b781a68bd132c7c29ddd5def3c1309c933b55026a3782ecd27494372476aaf65`
añade `OnFailure=hemovet-gpu-failure-shutdown.service`. La unidad escribe
`/var/lib/hemovet-gpu/bootstrap-failure.json` con modo `0600`, registra un
evento sanitizado y ejecuta `systemctl --no-block poweroff`.

La prueba real instaló una revisión con estado no permitido. El contrato
devolvió `ERROR: only pending_boot_validation may be applied`, la evidencia
registró `state=shutdown_requested` y Compute Engine emitió
`compute.instances.guestTerminate`; no fue un stop administrativo ni una
preempción. La revisión, imagen y modelo anteriores se conservaron.

Después se restauró el manifiesto válido, se arrancó de nuevo y se comprobó:

```text
release=515d343ac805779f94be9277376bdadf5516154d
runtime=sha256:b526b1d4bc30d0cc641e0d2a186034b327c97de0171b1a47ce1c917d79604e5f
model=qwen3:4b-instruct-2507-q4_K_M
inference_device=full_gpu
latency_ms=19044
service Result=success
```

La reinstalación del mismo bundle fue idempotente. Journald tuvo cero
coincidencias sensibles y el `DOCKER_CONFIG` efímero estaba ausente.

## Evidencia de red

| Prueba | Resultado |
| --- | --- |
| Curl real desde `hemovet-prod` a `10.128.0.3:11434/api/tags` | HTTP 200 |
| Connectivity Test `hemovet-prod → GPU:11434` | `REACHABLE`, regla allow prioridad 700 |
| Fuente interna simulada `10.128.0.4 → GPU:11434` | `UNREACHABLE`, deny prioridad 800 |
| Internet `198.51.100.10 → 34.45.75.48:11434` | `UNREACHABLE`, deny prioridad 800 |
| IAP `35.235.240.1 → 10.128.0.3:22` | `REACHABLE`, allow prioridad 700 |
| Internet a GPU 22/80/443/3389 | `UNREACHABLE` |
| Prueba TCP real desde Internet a 22/80/443/3000/3389/11434 | todos rechazados/filtrados |

Los ocho recursos temporales de Connectivity Tests se eliminaron después de
guardar los resultados; no quedó ninguno con prefijo `hemovet-stage7-`.

## Incidentes operativos observados

- **MEDIO — preempción Spot:** el primer ciclo fue interrumpido por
  `compute.instances.preempted`. La VM quedó apagada y el disco persistió.
- **MEDIO — stockout L4:** un intento posterior devolvió
  `ZONE_RESOURCE_POOL_EXHAUSTED_WITH_DETAILS`. No se cambió zona, máquina ni
  GPU; el reintento posterior funcionó.
- **BAJO — rollback preventivo de firewall:** una conexión IAP coincidió con la
  preempción. Se deshabilitó temporalmente la denegación total, se comprobó la
  causa mediante operaciones GCP, se volvió a habilitar y se validó IAP con la
  regla activa. Esto probó el rollback sin dejar la GPU abierta al cierre.
- **BAJO — perfil OS Login:** la gestión automática omitió una clave pública
  preexistente al limpiar la clave temporal. Se detectó por comparación con la
  línea base y se restauró el mismo material público. El conjunto final de dos
  claves coincide semánticamente con el inicial.

## Costo incremental estimado

- Tiempo GPU conservador: `916.241 s` (`15.27 min`). Al precio on-demand usado
  como techo (`USD 0.706832276/h`): `USD 0.1799`; Spot real es variable y menor
  o igual al techo, sujeto a Cloud Billing.
- Ocho Connectivity Tests: dentro de los primeros 20 mensuales cuestan `USD
  0`; si el proyecto ya agotó el nivel gratuito, el máximo incremental es
  `8 × USD 0.15 = USD 1.20`.
- IAP para recursos alojados en GCP no añade tarifa del producto; aplican los
  cargos normales de red/cómputo.
- Firewall, IAM, OS Login, tags y protecciones no tienen tarifa directa.
- Snapshot: cargo recurrente aproximado `USD 2.74/mes`, ya existente desde la
  Etapa 6.

Fuentes consultadas el 2026-08-02:

- <https://cloud.google.com/products/network-intelligence-center/pricing>
- <https://cloud.google.com/iap/pricing>
- <https://cloud.google.com/compute/disks-image-pricing>
- <https://cloud.google.com/products/compute/pricing/accelerator-optimized>
- <https://cloud.google.com/spot-vms/pricing>

## Estado final y riesgos pendientes

```text
hemovet-prod:       RUNNING, sin restart, deletionProtection=true, autoDelete=false
hemovet-llm-gpu:    TERMINATED, deletionProtection=true, autoDelete=false
GPU tags:           hemovet-gpu-runtime
GPU OS Login:       TRUE
snapshot:           READY, conservado
private path:       10.128.0.2/32 -> 10.128.0.3:11434
public GPU ports:   cerrados
```

Riesgos pendientes:

1. `default-allow-ssh` permanece global para no romper el workflow productivo
   legado; Etapa 8 debe migrarlo y retirarlo.
2. OS Login de producción sigue `UNSET` por la misma dependencia.
3. Producción aún usa la Default Compute Engine service account; asociar
   `hemovet-prod-runtime@...` requiere una ventana y está fuera de esta etapa.
4. Los dos miembros `Owner` preexistentes impiden afirmar privilegio mínimo
   efectivo para administración humana.
5. La IP privada GPU depende de conservar la instancia; deletion protection
   reduce, pero no elimina, ese acoplamiento.
6. El 74% de disco exige retención/cleanup controlado posterior.

No se modificaron backend, frontend, Caddy, PostgreSQL, ChromaDB, RAG, datos
clínicos, imágenes OCI, modelo, GitHub Actions, secrets, variables,
environments, `main` o `dev/agosto`.
