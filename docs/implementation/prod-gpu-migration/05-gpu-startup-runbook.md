# Runbook de arranque GPU

Estado: `IMPLEMENTED` y validado en la Etapa 6 el 2026-08-02.

## Contrato operativo

`hemovet-llm-gpu` permanece apagada por defecto. Un operador la enciende de
forma explícita; ningún push, backend o workflow de esta etapa puede hacerlo.
El servicio persistente `hemovet-gpu.service` se ejecuta una vez por boot y
consume `hemovet-gpu-desired-release` desde metadata.

Solo se acepta una proyección `hemovet.gpu-runtime-release/v1` con:

- `revision_state=pending_boot_validation`;
- `apply_on=next_boot`;
- `update_while_running=false`;
- imagen `ollama-runtime` del repositorio autorizado y fijada con `@sha256`;
- digest del bundle instalado;
- nombre, digest y cuantización exactos del modelo aprobado.

El marcador `/run/hemovet-gpu/reconciler-boot-id` autoriza la sustitución del
runtime únicamente durante la primera ejecución de un boot. Una ejecución
posterior en el mismo boot valida la revisión vigente o deja una revisión nueva
en `pending-release.json`; nunca actualiza el runtime en caliente.

Cada boot ejecuta una inferencia mínima aunque la revisión deseada ya sea la
aplicada. Esto carga el modelo antes de exigir residencia en `/api/ps` y evita
aceptar un contenedor meramente saludable pero sin offload validado. Solo las
reejecuciones posteriores dentro del mismo boot usan `action=validate_only` y
no recrean ni recargan el runtime.

## Estado persistente

| Ruta/recurso | Propósito |
| --- | --- |
| `/opt/hemovet-gpu/current` | symlink atómico al bundle versionado activo |
| `/opt/hemovet-gpu/bundles/<sha256>` | bundles inmutables conservados |
| `/var/lib/hemovet-gpu/applied-release.json` | revisión validada vigente |
| `/var/lib/hemovet-gpu/previous-release.json` | revisión anterior para rollback |
| `/var/lib/hemovet-gpu/pending-release.json` | revisión diferida mientras el runtime estaba activo |
| `/var/lib/hemovet-gpu/bootstrap-failure.json` | última evidencia sanitizada de un bootstrap fallido |
| `/var/lib/hemovet-gpu/releases/<sha>/` | manifiesto, entorno Compose y métricas por revisión |
| `hemovet_gpu_ollama_models` | volumen Docker persistente de pesos |
| `/run/hemovet-gpu/docker-config` | credencial AR efímera; debe desaparecer al terminar |

El Compose autónomo contiene exactamente `ollama` y `ollama_setup`. El
servicio host `ollama.service` y los stacks heredados quedan detenidos con
`restart=no`; sus contenedores y volúmenes se conservan para rollback y no se
eliminan.

## Preflight antes de encender

```bash
gcloud compute instances describe hemovet-llm-gpu \
  --project=project-5b36701c-f44f-4c03-a12 \
  --zone=us-central1-a \
  --format='yaml(status,machineType,serviceAccounts,metadata.items.key)'

gcloud compute snapshots describe \
  hemovet-llm-gpu-pre-stage6-20260802 \
  --project=project-5b36701c-f44f-4c03-a12
```

Comprobar además que el manifiesto deseado es el versionado y aprobado. No
imprimir el documento completo en logs compartidos; son suficientes
`release_id`, digests, estado y modelo. Cuando se actualice metadata con la VM
encendida, confirmar que el guest ve el valor nuevo antes del siguiente
stop/start. Esto evita una carrera de propagación observada durante la Etapa 6.

## Encendido manual

```bash
gcloud compute instances start hemovet-llm-gpu \
  --project=project-5b36701c-f44f-4c03-a12 \
  --zone=us-central1-a
```

Seguir el boot sin exponer secretos:

```bash
gcloud compute instances get-serial-port-output hemovet-llm-gpu \
  --project=project-5b36701c-f44f-4c03-a12 \
  --zone=us-central1-a --port=1

sudo systemctl status hemovet-gpu.service --no-pager
sudo journalctl -u hemovet-gpu.service -b --no-pager
```

El acceso administrativo normal se realiza por IAP y OS Login:

```bash
gcloud compute ssh hemovet-llm-gpu \
  --project=project-5b36701c-f44f-4c03-a12 \
  --zone=us-central1-a --tunnel-through-iap
```

El éxito exige `ActiveState=active`, `SubState=exited`, `Result=success` y las
líneas `runtime=valid`, `inference_device=full_gpu`, `release=applied` o
`release=already_applied ... action=boot_inference`. La ausencia en `/api/ps`
antes de una inferencia no invalida los pesos instalados; identidad y
cuantización se obtienen de `/api/tags` y `/api/show`, y la inferencia de boot
es la que demuestra residencia GPU.

## Validación focal

```bash
sudo docker compose --project-name hemovet-gpu \
  --env-file /var/lib/hemovet-gpu/releases/<sha>/compose.env \
  -f /opt/hemovet-gpu/current/docker-compose.gpu.yml config --services

sudo docker ps --format '{{.Names}} {{.Image}} {{.Status}} {{.Ports}}'
nvidia-smi
curl --fail --silent http://10.128.0.3:11434/api/tags
curl --fail --silent http://10.128.0.3:11434/api/ps
```

Los servicios deben ser solo `ollama` y `ollama_setup`, el único contenedor en
ejecución debe ser `hemovet-gpu-ollama-1`, y el listener debe ser exactamente
`10.128.0.3:11434`. La validación completa se ejecuta mediante
`deploy/gpu/validate-runtime.sh`; no registra el prompt ni la respuesta.

## Apagado

```bash
gcloud compute instances stop hemovet-llm-gpu \
  --project=project-5b36701c-f44f-4c03-a12 \
  --zone=us-central1-a
```

Confirmar `status=TERMINATED`. El disco, el volumen de pesos, la IP estática y
la revisión deseada permanecen.

## Fallo definitivo y apagado automático

`hemovet-gpu.service` declara
`OnFailure=hemovet-gpu-failure-shutdown.service`. Si falla el contrato, host,
pull, modelo o inferencia, la unidad auxiliar:

1. escribe atómicamente y con modo `0600`
   `/var/lib/hemovet-gpu/bootstrap-failure.json`;
2. registra únicamente unidad, boot ID, fecha y estado sanitizados en journald
   y consola;
3. solicita `systemctl --no-block poweroff`;
4. no elimina runtime, pesos, manifiestos ni la revisión anterior.

Diagnóstico antes de un nuevo arranque:

```bash
sudo systemctl status hemovet-gpu.service \
  hemovet-gpu-failure-shutdown.service --no-pager
sudo journalctl -u hemovet-gpu.service \
  -u hemovet-gpu-failure-shutdown.service -b --no-pager
sudo cat /var/lib/hemovet-gpu/bootstrap-failure.json
```

La Etapa 7 probó el camino con una revisión inválida: se generó evidencia
`shutdown_requested` y Compute Engine registró
`compute.instances.guestTerminate`. Después se restauró la metadata válida y
un boot posterior terminó `Result=success`, `inference_device=full_gpu`. No
deshabilitar la unidad para ocultar fallos; corregir la causa o aplicar el
rollback versionado.
