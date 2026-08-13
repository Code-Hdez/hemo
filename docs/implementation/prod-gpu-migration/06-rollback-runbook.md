# Runbook de rollback

## Entorno completo y colección RAG

Cada instalación conserva `previous.env` y `transaction.json` en el directorio
privado de la revisión. Para restaurar el entorno y su puntero RAG:

```bash
python3 backend/scripts/manage_deploy_env.py rollback \
  --active-env .env \
  --transaction-dir \
  /var/lib/hemovet-prod/transactions/<release-id>/<attempt-id>
```

Invariantes:

- el respaldo debe coincidir con su digest privado;
- el destino debe seguir siendo exactamente la revisión instalada;
- si otra revisión sustituyó `.env`, el rollback se niega a sobrescribirla;
- la restauración es atómica e idempotente;
- no se reescribe ni elimina ninguna colección Chroma;
- el puntero anterior se recupera al restaurar `RAG_COLLECTION_NAME` dentro del
  archivo completo.

## Cambios de código de la Etapa 1

La recuperación se realizará mediante un commit de reversión sobre esta rama,
no con `git reset --hard`, `git clean` ni reescritura de historial. `dips.md`
no forma parte del cambio y debe permanecer intacto.

## Limitación actual

El workflow preexistente aún no invoca este comando. No debe asumirse que un
despliegue productivo posee transacción hasta completar la integración CI/CD y
probarla en una ventana autorizada.

## Contratos de la Etapa 2

Los cambios de contrato se revierten mediante un commit de reversión de esta
rama. El contrato de release establece que el rollback futuro debe seleccionar
un manifiesto `hemovet.release/v1` anterior completo; no se permite sustituir
solo backend, modelo o RAG y crear una combinación no registrada.

No existe todavía un puntero productivo de manifiestos ni se modificó una
revisión desplegada. El rollback operativo de aplicación/GPU continúa pendiente
de las Etapas 8 y 9.

## Recursos creados en la Etapa 3

No ejecutar esta sección como un script ciego. Primero conservar el inventario
de digests y comprobar que ninguna revisión desplegada o de rollback depende del
repositorio.

1. Retirar el binding `roles/iam.workloadIdentityUser` de la cuenta CI para el
   `principalSet` exacto documentado en
   `13-artifact-registry-iam-wif.md`.
2. Retirar del repositorio el writer CI y los dos readers runtime mediante
   `gcloud artifacts repositories remove-iam-policy-binding`.
3. Eliminar `github-main-production` y luego `hemovet-github` con los comandos
   `gcloud iam workload-identity-pools providers delete` y
   `gcloud iam workload-identity-pools delete`.
4. Eliminar las tres service accounts solo después de comprobar que siguen sin
   estar adjuntas a VMs ni referenciadas por automatización.
5. Conservar `hemovet-images` si tiene cualquier digest referenciado. Su
   eliminación requiere aprobación destructiva explícita:

   ```bash
   gcloud artifacts repositories delete hemovet-images \
     --project=project-5b36701c-f44f-4c03-a12 \
     --location=us-central1
   ```

6. Deshabilitar únicamente las cinco APIs habilitadas por la etapa después de
   verificar que ningún otro recurso del proyecto las consume.

7. Revertir el gate manual mediante un commit normal que revierta
   `e30c422445e6c2e096b851895ea495858e6cc531` en `main`. El commit de reversión
   debe incluir `[skip ci]` y comprobarse que no generó un run de push antes de
   continuar. No se reescribe historia.
8. El environment `production` no contiene secrets. Su eliminación es opcional
   y requiere una credencial GitHub administradora; el token usado durante esta
   etapa recibió `404` al intentar administrarlo. No eliminarlo es necesario
   para retirar WIF si primero se elimina el provider/binding.
9. La imagen `wif-validation:run-30762294120-1` se conserva como evidencia. Su
   borrado individual es destructivo y no forma parte del rollback automático;
   si se aprueba, registrar antes el digest
   `sha256:0998efbb07674eeb14b282c60bca44651feae2a6b83b632d9c650dce9cfaf989`.

La política de limpieza está en `dry-run`; no requiere rollback de datos. Para
retirarla sin borrar artefactos se usa
`gcloud artifacts repositories delete-cleanup-policies` con los dos IDs. No se
eliminan imágenes individualmente como parte del rollback automático.

Los cambios del repositorio se revierten con commits normales sobre la rama.
No se usa `git reset`, `git clean`, force push ni reescritura de historia.

## Separación Compose de la Etapa 4

No existe estado runtime que restaurar: no se ejecutaron builds, pulls, `up`,
reinicios o cambios de volumen. El rollback es un commit normal que revierta
conjuntamente Compose, ejemplos de entorno, validador, pruebas y documentación.

Precauciones:

- no eliminar `ollama-data`; el overlay local conserva esa clave para reutilizar
  el volumen histórico;
- no eliminar `hemovet_gpu_ollama_models`; en esta etapa no fue creado;
- no sustituir solo un digest de backend/frontend: seleccionar un manifiesto
  completo anterior;
- no mezclar `docker-compose.gpu.yml` con los archivos de aplicación durante
  rollback;
- `dips.md` sigue fuera de Git y no forma parte de ninguna reversión.

## Backend y frontend degradables de la Etapa 5

No existe estado productivo que restaurar porque la etapa no se desplegó. No
hubo migraciones, cambios de esquema, escrituras en PostgreSQL/Chroma ni cambios
de configuración runtime.

Rollback de rama:

1. crear un commit normal que revierta el cierre documental de la Etapa 5;
2. revertir `105e8aa105795356d67a1f682849799033e8cd98` y después, conjuntamente,
   `1c234329a948d433b3968233b5d176fe3e0830d0`;
3. ejecutar en Python 3.11 la regresión completa, Ruff, frontend y Compose;
4. comprobar que `dips.md` continúa no rastreado e intacto;
5. no desplegar el rollback sin una autorización y ventana posteriores.

Backend y frontend deben volver juntos: un frontend que espere
`hemovet.availability/v1` y códigos `LLM_PROVIDER_*` no debe combinarse con un
backend anterior sin esos endpoints/proyecciones. No borrar conversaciones ni
reescribir códigos persistidos; la compatibilidad se realiza al leer.

El rollback no requiere cambiar GCP, la VM GPU, firewall, IAM, IPs, discos,
metadata, Compose, GitHub Actions o el puntero RAG.

## Runtime GPU de la Etapa 6

### Rollback de runtime/modelo con la VM encendida

La operación es manual y explícita; no forma parte de un push. Antes de
ejecutarla, registrar revisión, contenedor, modelo y estado de conversaciones
activas. El comando probado es:

```bash
sudo /opt/hemovet-gpu/current/deploy/gpu/rollback-release.sh --previous
```

El script valida el manifiesto histórico, genera una proyección temporal ligada
al bundle instalado, vuelve a validar el contrato cerrado, obtiene la imagen
por digest, recrea solo Ollama, reutiliza el volumen y exige inferencia
`full_gpu`. El manifiesto histórico original no se modifica.

La prueba de Etapa 6 demostró:

```text
515d343a... / sha256:b526b1d4... -> 6e2969d6... / sha256:f2a4fc8d...
6e2969d6... / sha256:f2a4fc8d... -> 515d343a... / sha256:b526b1d4...
```

En ambos sentidos se conservaron el digest Qwen, `Q4_K_M`, `full_gpu` y el hash
del árbol de pesos. El segundo comando restauró la revisión aprobada.

### Rollback diferido para el próximo boot

Para que un rollback sobreviva al siguiente stop/start, publicar como metadata
el manifiesto anterior completo mientras la VM está apagada:

```bash
gcloud compute instances add-metadata hemovet-llm-gpu \
  --project=project-5b36701c-f44f-4c03-a12 \
  --zone=us-central1-a \
  --metadata-from-file=hemovet-gpu-desired-release=\
deploy/releases/gpu-runtime-6e2969d6fa735473097d4f1c19af46263436bd66.json
```

Después se enciende manualmente y se exige la validación del runbook de
arranque. No usar solo un tag, no editar campos de modelo y no aplicar una
revisión con estado distinto de `pending_boot_validation`.

### Restauración del boot disk

El respaldo previo es
`hemovet-llm-gpu-pre-stage6-20260802`, estado `READY`, source disk ID
`574351621454120040`. Primero crear un disco nuevo sin tocar la VM:

```bash
gcloud compute disks create hemovet-llm-gpu-stage6-restore \
  --project=project-5b36701c-f44f-4c03-a12 \
  --zone=us-central1-a \
  --source-snapshot=hemovet-llm-gpu-pre-stage6-20260802 \
  --type=pd-balanced
```

Validar ese disco antes de cualquier sustitución. Desasociar o reemplazar el
boot disk, recrear la VM o eliminar discos es destructivo y requiere una
aprobación/ventana separada. El snapshot no debe eliminarse mientras sea el
único respaldo pre-Etapa 6.

### Rollback de identidad

Solo con la VM apagada y si la identidad GPU dedicada resulta ser la causa:

```bash
gcloud compute instances set-service-account hemovet-llm-gpu \
  --project=project-5b36701c-f44f-4c03-a12 \
  --zone=us-central1-a \
  --service-account=371832959385-compute@developer.gserviceaccount.com \
  --scopes=default
```

Esto restaura la identidad previa, pero amplía nuevamente la compartición con
producción y solo es un rollback temporal. No eliminar la cuenta dedicada ni su
binding reader hasta completar la migración.

### Rollback del código versionado

Revertir con commits normales, en orden inverso, el cierre documental y los
commits `58a1c15`, `70c32b38`, `52dfa378`, `4d96835d` y `ce8a82ea`. No usar
reset, clean, force push ni borrar `dips.md`. La reversión del código no
desinstala el bundle ya persistido; esa operación debe seguir el rollback de
runtime o snapshot.

## Red, acceso administrativo y protecciones de la Etapa 7

Este rollback no se ejecuta como bloque único. Primero se identifica el control
que causa la incidencia, se registra el estado actual y se revierte únicamente
ese control. La VM GPU debe estar `TERMINATED` antes de cambiar tags, OS Login,
identidad o metadata. No eliminar el snapshot
`hemovet-llm-gpu-pre-stage6-20260802`.

### Firewall de inferencia

Estado seguro de referencia:

```text
allow 10.128.0.2/32 -> SA GPU tcp:11434 priority 700
deny  0.0.0.0/0     -> SA GPU tcp:11434 priority 800
deny  0.0.0.0/0     -> SA GPU all       priority 900
```

Si una regla nueva rompe el acceso autorizado, el rollback preferido es
deshabilitar temporalmente solo la regla sospechosa, comprobar mediante
Connectivity Tests y volver a habilitarla después de corregir el selector:

```bash
gcloud compute firewall-rules update \
  hemovet-deny-unapproved-ingress-gpu \
  --project=project-5b36701c-f44f-4c03-a12 --disabled

# corregir/probar; nunca dejar este estado como cierre

gcloud compute firewall-rules update \
  hemovet-deny-unapproved-ingress-gpu \
  --project=project-5b36701c-f44f-4c03-a12 --no-disabled
```

Este procedimiento se probó en la etapa: la denegación total se deshabilitó,
se determinó que la interrupción había sido una preempción Spot y se reactivó;
IAP volvió a pasar con la regla activa.

La retirada total, solo con aprobación explícita, usa
`gcloud compute firewall-rules delete` para estas reglas:

```text
hemovet-allow-prod-to-gpu-ollama
hemovet-deny-other-to-gpu-ollama
hemovet-allow-iap-ssh-gpu
hemovet-allow-iap-ssh-prod
hemovet-deny-unapproved-ingress-gpu
```

Restaurar `allow-ollama-internal` reabre toda `10.128.0.0/20` y solo es un
rollback de emergencia temporal:

```bash
gcloud compute firewall-rules create allow-ollama-internal \
  --project=project-5b36701c-f44f-4c03-a12 \
  --network=default --direction=INGRESS --priority=1000 \
  --allow=tcp:11434 --source-ranges=10.128.0.0/20
```

No restaurar `default-allow-rdp` salvo incidente y autorización expresa. Su
definición anterior era TCP/3389 desde `0.0.0.0/0` con prioridad 65534 y
reintroduce exposición administrativa pública.

### IAP, OS Login e IAM

Para recuperar acceso GPU sin abrir SSH público:

1. confirmar snapshot `READY` y VM apagada;
2. poner temporalmente `enable-oslogin=FALSE` en metadata de la GPU;
3. añadir una única clave temporal a metadata de instancia;
4. acceder únicamente por IAP y corregir IAM/OS Login;
5. retirar esa clave y restaurar `enable-oslogin=TRUE`;
6. realizar dos conexiones IAP y verificar `sudo -n true`.

Ese patrón se probó tanto en GPU como en producción, y se comprobó que no
permanecieran las claves temporales. Una clave pública preexistente que la
gestión automática omitió durante el cleanup se restauró desde la línea base;
el conjunto final volvió a dos claves OS Login equivalentes al inicial.

Para retirar IAM de Etapa 7 después de recuperar otro administrador:

```bash
gcloud projects remove-iam-policy-binding project-5b36701c-f44f-4c03-a12 \
  --member=user:cdavidh1962@gmail.com \
  --role=roles/iap.tunnelResourceAccessor \
  --condition="expression=destination.port == 22 && (destination.ip == '10.128.0.2' || destination.ip == '10.128.0.3'),title=hemovet_stage7_iap_ssh,description=IAP SSH only to HemoVet VM private IPs"

gcloud compute instances remove-iam-policy-binding hemovet-llm-gpu \
  --project=project-5b36701c-f44f-4c03-a12 \
  --zone=us-central1-a --member=user:cdavidh1962@gmail.com \
  --role=roles/compute.osAdminLogin

gcloud compute instances remove-iam-policy-binding hemovet-prod \
  --project=project-5b36701c-f44f-4c03-a12 \
  --zone=us-central1-a --member=user:cdavidh1962@gmail.com \
  --role=roles/compute.osAdminLogin
```

Retirar además `roles/iam.serviceAccountUser` del mismo principal en las SAs
GPU y producción mediante
`gcloud iam service-accounts remove-iam-policy-binding`. No deshabilitar
`iap.googleapis.com` hasta confirmar que ningún otro consumidor la usa.

### Tags y direccionamiento

Con la GPU apagada, el rollback de tags es:

```bash
gcloud compute instances add-tags hemovet-llm-gpu \
  --project=project-5b36701c-f44f-4c03-a12 \
  --zone=us-central1-a --tags=http-server,https-server
gcloud compute instances remove-tags hemovet-llm-gpu \
  --project=project-5b36701c-f44f-4c03-a12 \
  --zone=us-central1-a --tags=hemovet-gpu-runtime
```

No es recomendable: vuelve a hacer aplicables las reglas web públicas. No hay
rollback de IP porque ninguna dirección se cambió o recreó; conservar la VM
mantiene `10.128.0.3` y las reservas externas existentes.

### Protección de VM y discos

Solo si una operación de recuperación aprobada exige eliminar una VM:

```bash
gcloud compute instances update hemovet-llm-gpu \
  --project=project-5b36701c-f44f-4c03-a12 \
  --zone=us-central1-a --no-deletion-protection
gcloud compute instances update hemovet-prod \
  --project=project-5b36701c-f44f-4c03-a12 \
  --zone=us-central1-a --no-deletion-protection

gcloud compute instances set-disk-auto-delete hemovet-llm-gpu \
  --project=project-5b36701c-f44f-4c03-a12 \
  --zone=us-central1-a --disk=hemovet-llm-gpu --auto-delete
gcloud compute instances set-disk-auto-delete hemovet-prod \
  --project=project-5b36701c-f44f-4c03-a12 \
  --zone=us-central1-a --disk=hemovet-prod --auto-delete
```

Estos comandos reintroducen riesgo de pérdida y no se ejecutaron como prueba.
La reversibilidad se validó mediante read-back de Compute Engine; la prueba
destructiva sería desproporcionada. El procedimiento seguro de restauración
continúa siendo crear un disco nuevo desde el snapshot y validarlo antes de
cualquier sustitución.

### Apagado automático y bundle GPU

La unidad de fallo conserva runtime/modelo y puede diagnosticarse sin retirarla.
Si ella fuese la causa, instalar el bundle previo desde su directorio inmutable
y restaurar, con la VM apagada, un manifiesto cuyo `startup.bundle_digest`
coincida. No editar un único digest a mano ni deshabilitar `OnFailure` dejando
una revisión incoherente.

El camino de fallo se probó con metadata inválida y terminó en
`compute.instances.guestTerminate`; luego se restauró el manifiesto válido y el
arranque terminó `full_gpu`. El runtime anterior, los pesos y el snapshot
permanecieron disponibles durante toda la prueba.

### Rollback del código

Crear commits normales que reviertan primero el cierre documental de Etapa 7 y
después `cf0f4c5f`. Esto no cambia automáticamente GCP ni el bundle instalado.
No usar reset, clean, force push, no borrar `dips.md` y no iniciar un despliegue
de aplicación como parte del rollback de red.

## Rollback de GitHub Actions y release inmutable — Etapa 8

Mientras no exista merge, `main=e30c422445e6c2e096b851895ea495858e6cc531`
es el workflow recuperable y no requiere ninguna acción. Para revertir la rama,
crear commits normales que reviertan, en orden inverso, el cierre documental y
los commits `778ecda0`, `af5ab60b`, `2aac3598`, `f97fb1ce` y `42300ced`. No usar
reset, clean, force push ni borrar `dips.md`.

Para retirar IAM añadido por Etapa 8 después de restaurar otro camino:

```bash
gcloud projects remove-iam-policy-binding project-5b36701c-f44f-4c03-a12 \
  --member='serviceAccount:hemovet-github-cicd@project-5b36701c-f44f-4c03-a12.iam.gserviceaccount.com' \
  --role='projects/project-5b36701c-f44f-4c03-a12/roles/hemovetGpuReleasePublisher' \
  --condition='expression=resource.type == "compute.googleapis.com/Instance" && resource.name == "projects/project-5b36701c-f44f-4c03-a12/zones/us-central1-a/instances/hemovet-llm-gpu",title=hemovet_stage8_gpu_release_metadata,description=Only desired release metadata on hemovet-llm-gpu'

gcloud iam roles delete hemovetGpuReleasePublisher \
  --project=project-5b36701c-f44f-4c03-a12
```

Retirar `roles/iap.tunnelResourceAccessor` y `roles/compute.viewer` de CI solo
si el workflow anterior u otra identidad ya cubren diagnóstico y acceso. El
binding IAP tiene título `hemovet_stage8_ci_iap_prod_ssh` y condición
`destination.ip == "10.128.0.2" && destination.port == 22`.

Una release fallida se revierte seleccionando el `hemovet.release/v1` anterior
y sus referencias por digest. Nunca mover tags. `deploy-release.sh` conserva
`current`/`previous`, restaura el `.env` completo mediante
`manage_deploy_env.py rollback`, vuelve al source anterior y levanta Compose
con `--no-build`. El rollback RAG cambia el puntero a la colección inmutable
anterior. GPU restaura `hemovet-gpu-previous-release` y lo aplica en el próximo
arranque; no exige encenderla.

Los runs fallidos de Etapa 8 no requieren rollback porque no alcanzaron
metadata GPU o producción. Sus imágenes parciales pueden retirarse solo después
de verificar que ningún manifiesto/rollback las referencia y con autorización
explícita.

## Rollback coordinado validado — Etapa 9

### Preflight obligatorio

1. detener la concurrencia de deploy y registrar los enlaces `current` y
   `previous`;
2. confirmar que la GPU está `TERMINATED` y el snapshot pre-Etapa 6 `READY`;
3. copiar a un directorio privado el manifiesto, artifact set, entorno, source
   archive y proyección GPU de una única revisión;
4. validar antes de mutar:

   ```bash
   PYTHONPATH=backend python backend/scripts/validate_rollback_bundle.py \
     --release-manifest <release-manifest.json> \
     --artifact-set <artifact-set.json> \
     --candidate-environment <candidate.env> \
     --source-root <source-root> \
     --gpu-release <gpu-runtime.json> \
     --bundle-manifest deploy/gpu/bundle-manifest.sha256
   ```

La salida solo puede contener release, digests, modelo y RAG. Si cualquier
identidad diverge, no ejecutar el rollback.

### Aplicación, entorno y RAG

`deploy/prod/deploy-release.sh` conserva una transacción distinta por intento
en `/var/lib/hemovet-prod/transactions/<release>/<attempt>`. Ante fallo después
de instalar el candidato:

- restaura los bytes completos del entorno anterior;
- restaura `RAG_COLLECTION_NAME` como parte de ese mismo archivo;
- vuelve los enlaces `current` y `previous` a sus valores anteriores;
- levanta backend/frontend anteriores por digest con `--no-build`;
- no elimina ni modifica colecciones Chroma;
- devuelve el código original, o `70` si el rollback mismo falla.

Si devuelve `70`, detener cualquier automatización. Verificar
`previous.env`, su digest y `transaction.json`; ejecutar `manage_deploy_env.py
rollback` únicamente contra ese attempt y luego levantar el source anterior.
No seleccionar una colección o imagen de otra revisión.

El modo `--isolated-root` existe solo para pruebas, exige
`HEMOVET_ALLOW_ISOLATED_DEPLOY_TEST=1`, un path temporal restringido, modo
`0700` y sentinel exacto. No usarlo como mecanismo productivo.

### GPU diferida

Con la VM apagada:

```bash
deploy/gpu/select-desired-release.sh \
  --manifest <gpu-runtime-anterior.json> \
  --previous-output <respaldo-privado-0600.json>
```

El script valida contrato/bundle, conserva la metadata anterior, compara el
read-back byte por byte y restaura automáticamente si la selección falla. No
enciende la VM ni actualiza un runtime activo. El ciclo
`515d… → af5… → 515d…` fue probado y la metadata final coincidió exactamente.

### Comprobaciones posteriores

- `core_ready`, `database_ready` y la política RAG deben pasar;
- backend/frontend deben corresponder a los digests del manifiesto anterior;
- entorno y colección deben coincidir con la transacción restaurada;
- verificar usuarios, mascotas, hemogramas y conversaciones sin escribirlos;
- mantener la GPU apagada salvo una ventana separada;
- conservar revisión fallida, imágenes, colecciones y snapshot como evidencia.

Los escenarios, limitaciones y hashes están en
`19-integral-rollback-validation.md`.

## Revisión de rollback seleccionada en Etapa 10

La revisión completa anterior es
`af5ab60b418bc931c4c4cabc8b8ef92893325fb6`. Su plan ejecutable y
sanitizado está en
`deploy/releases/rollback-plan-af5ab60b418bc931c4c4cabc8b8ef92893325fb6.json`.
Debe validarse contra
`release-manifest-af5ab60b418bc931c4c4cabc8b8ef92893325fb6.json`; no copiar
digests manualmente.

El orden para un cutover posterior es:

1. bloquear despliegues concurrentes y capturar el manifiesto activo;
2. ejecutar el preflight coordinado anterior con la revisión `af5…`;
3. restaurar backend, frontend, entorno completo y puntero RAG en una misma
   transacción;
4. comprobar core, base, Chroma y RAG antes de reabrir tráfico;
5. con la GPU apagada, seleccionar
   `gpu-runtime-af5ab60b418bc931c4c4cabc8b8ef92893325fb6.json`;
6. encender la GPU solo en una ventana separada y validar identidad,
   cuantización e inferencia antes de habilitar chat.

Durante Etapa 10 este procedimiento no tuvo que aplicarse sobre producción,
porque el stack público nunca fue sustituido. El ciclo coordinado fue probado
en Etapa 9 y el manifiesto anterior continúa disponible por digest.
