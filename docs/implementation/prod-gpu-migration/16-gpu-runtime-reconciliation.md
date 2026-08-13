# Etapa 6 — Runtime y reconciliación de la VM GPU

Fecha de ejecución: 2026-08-02.

## Resultado

La VM `hemovet-llm-gpu` quedó apagada con un runtime autónomo y reconciliable
al arranque. La revisión aprobada es:

| Componente | Identidad validada |
| --- | --- |
| Release | `515d343ac805779f94be9277376bdadf5516154d` |
| Bundle de arranque | `sha256:5e2a5eb03f9fcdf5a1373447f3d6da13a16617a599db697e515d4039396a2c26` |
| Imagen OCI | `ollama-runtime@sha256:b526b1d4bc30d0cc641e0d2a186034b327c97de0171b1a47ce1c917d79604e5f` |
| Ollama | `0.30.10` |
| Modelo | `qwen3:4b-instruct-2507-q4_K_M` |
| Digest del modelo | `sha256:0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0` |
| Cuantización | `Q4_K_M` |
| Dispositivo | `full_gpu`, NVIDIA L4 |

La revisión anterior `6e2969d6fa735473097d4f1c19af46263436bd66`, con
runtime `sha256:f2a4fc8d74c6b13c4db860ab316144bd41b130281f7c0f5b9b37cb5d34064f2f`,
permanece disponible y fue utilizada en una prueba real de rollback.

## Inventario previo

| Elemento | Estado antes de mutar |
| --- | --- |
| VM | `TERMINATED`, Spot/preemptible |
| Máquina/GPU | `g2-standard-4`, 1 × NVIDIA L4 de 24 GiB |
| Red | privada `10.128.0.3`, externa estática `34.45.75.48` |
| Disco | boot `hemovet-llm-gpu`, 100 GB `pd-balanced`, `autoDelete=true` |
| Identidad | Default Compute Engine service account |
| Metadata | `install-nvidia-driver=True`, claves SSH heredadas; sin startup script |
| Driver | `580.159.03`, CUDA reportada `13.0` |
| Docker | `29.6.2`; Compose `5.3.1`; containerd `2.2.6` |
| NVIDIA toolkit | `1.17.8`; runtime Docker `nvidia` disponible |
| Runtime host | Ollama `0.32.1`, habilitado y escuchando `*:11434` |
| Runtime heredado | dos proyectos Compose completos con backend, frontend, Caddy, PostgreSQL, Chroma y Ollama |
| Almacenamiento | raíz 102,888,095,744 bytes; 73,055,055,872 usados; 29,816,262,656 libres |

El driver, Docker y NVIDIA Container Toolkit ya estaban instalados en las
versiones finalmente aprobadas. No se forzó una reinstalación riesgosa: el
driver conserva el mecanismo GCP `install-nvidia-driver=True`, el bundle valida
versiones exactas y falla cerrado, y la configuración CDI se instala de forma
atómica. Por tanto, esta etapa demuestra idempotencia sobre la VM respaldada;
no afirma una reconstrucción desde una VM vacía.

El runtime heredado constituía un hallazgo **ALTO**: la VM alojaba servicios de
aplicación y datos fuera de la arquitectura autorizada. Se aplicó una
cuarentena reversible: servicios detenidos y `restart=no`, sin borrar
contenedores, imágenes o volúmenes.

## Respaldo previo

Antes del primer cambio persistente se creó el snapshot regional recuperable:

```text
name:             hemovet-llm-gpu-pre-stage6-20260802
status:           READY
location:         us-central1
sourceDiskId:     574351621454120040
diskSizeGb:       100
storageBytes:     58,891,150,336
creationTime:     2026-08-02T13:43:16.215-07:00
```

No se eliminó ni sustituyó el boot disk. La restauración debe crear primero un
disco nuevo desde el snapshot y validarlo; cualquier sustitución del disco de
la VM requiere una ventana y autorización destructiva separadas.

## Recursos y metadata modificados

| Recurso | Cambio | Rollback |
| --- | --- | --- |
| Snapshot regional | creado el snapshot anterior | conservar; eliminar solo con aprobación cuando deje de ser necesario |
| Service account de la VM | asociada `hemovet-gpu-runtime@...` con scope `cloud-platform` | con VM apagada, reasociar la cuenta anterior |
| IAM | ningún binding nuevo; la SA ya tenía `roles/artifactregistry.reader` en `hemovet-images` | no aplica |
| Claves SA | ninguna; `keys list --managed-by=user` devuelve cero | no aplica |
| Metadata deseada | añadida `hemovet-gpu-desired-release` | restaurar o retirar el valor anterior durante rollback autorizado |
| Metadata SSH | acceso temporal añadido y luego restaurado a las cuatro entradas originales | completado; la clave temporal devuelve `Permission denied` |
| Boot disk | bundle, unidad `systemd`, estado y volumen Docker persistidos | snapshot + rollback runtime documentados |

Las IP, NIC, subred, VPC, tags, firewall, tipo/tamaño de disco y metadata
`install-nvidia-driver` no cambiaron. No se añadió `startup-script` a metadata:
la unidad `systemd` versionada y habilitada en el boot disk es el mecanismo de
arranque.

## Diseño implementado

El bundle versionado en `deploy/gpu/` proporciona:

- instalación atómica por digest bajo `/opt/hemovet-gpu/bundles`;
- unidad `hemovet-gpu.service` de tipo oneshot y habilitada al boot;
- generación CDI reproducible y atómica;
- validación exacta de SO, driver, Docker, Compose, toolkit y L4;
- autenticación Artifact Registry con token del metadata server y
  `DOCKER_CONFIG` efímero en `/run`;
- lock no bloqueante mediante `flock`;
- pull por referencia canónica `@sha256`, tres intentos y espera acotada;
- Compose GPU autónomo con solo `ollama` y `ollama_setup`;
- volumen `hemovet_gpu_ollama_models`;
- identidad del modelo mediante `/api/tags` y `/api/show`;
- residencia y offload mediante `/api/ps`, sin convertirlo en fuente de
  identidad;
- inferencia mínima no clínica y métricas sin prompt ni respuesta;
- estado aplicado, anterior, pendiente y fallido con permisos privados;
- actualización solo en el primer reconcile de cada boot;
- inferencia de residencia obligatoria en cada boot, incluso cuando la revisión
  ya coincide con la aplicada;
- rollback manual con proyección explícita del manifiesto histórico hacia el
  bundle actual, sin mutar la evidencia histórica.

## Evidencia funcional

### Revisión diferida y ausencia de hot update

Con la revisión `6e2969d6…` activa se publicó como deseada `515d343a…`. Una
ejecución normal devolvió:

```text
release=deferred current=6e2969d6... desired=515d343a... reason=runtime_running
```

El ID del contenedor, su `StartedAt`, el manifiesto aplicado y los pesos no
cambiaron. La revisión quedó en `pending-release.json` hasta el siguiente boot.

### Arranque y Compose

En el boot que aplicó por primera vez la revisión final:

```text
host_runtime=valid os=24.04 driver=580.159.03 docker=29.6.2 \
  compose=5.3.1 toolkit=1.17.8 gpu=NVIDIA_L4
artifact_registry_auth=ok credentials=metadata_token
runtime=valid release=515d343a... inference_device=full_gpu latency_ms=93088
release=applied id=515d343a... state=validated
```

El gate adicional de arranque repetido se ejecutó en el boot
`307e64cd-6e20-444a-af69-54a749c00145`, con la misma revisión ya aplicada:

```text
runtime=valid release=515d343a... inference_device=full_gpu latency_ms=18989
release=already_applied id=515d343a... action=boot_inference
```

`systemd` terminó `active/exited`, `Result=success`. El Compose efectivo listó
exactamente `ollama` y `ollama_setup`; solo
`hemovet-gpu-ollama-1` quedó corriendo. El listener fue exclusivamente
`10.128.0.3:11434`; una conexión a `34.45.75.48:11434` expiró con `curl rc=28`.
No se cambió el firewall; la restricción de origen definitiva sigue en Etapa 7.

### Modelo y GPU

`/api/tags` y `/api/show` devolvieron:

```text
name:                 qwen3:4b-instruct-2507-q4_K_M
digest:               0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0
family:               qwen3
parameter_count:      4,022,468,096
quantization_level:   Q4_K_M
```

Después de inferencia, `/api/ps` informó
`size=2,895,118,335` y `size_vram=2,895,118,335`. `ollama ps` indicó `100% GPU`;
`nvidia-smi` funcionó dentro del contenedor y en el host sobre `NVIDIA L4`.
Esto demuestra offload completo y descarta CPU como dispositivo principal.

Métricas observadas:

| Escenario | Latencia | VRAM | Pico GPU | RAM contenedor |
| --- | ---: | ---: | ---: | ---: |
| Primer boot de revisión final | 93,088 ms | 2,980 MiB | 38% | 3.13 GiB |
| Boot repetido, misma revisión | 18,989 ms | 2,988 MiB | 43% | 3.09 GiB |
| Reinicio de contenedor, pesos persistidos | 4,840 ms | 2,988 MiB | 37% | 304.3 MiB al muestrear |
| Rollback al runtime anterior | 77,993 ms | 2,980 MiB | validación `full_gpu` | registrada en evidencia de revisión |
| Restauración del runtime aprobado | 77,135 ms | 2,980 MiB | 43% | 583.2 MiB al muestrear |

La VM tenía 14,521,536 KiB de RAM disponible después de la validación final. La
raíz terminó con 75,701,837,824 bytes usados de 102,888,095,744 (74%); el
volumen del modelo usa 2,497,296,445 bytes. Los runtimes e imágenes heredados
se conservaron, por lo que queda un riesgo **MEDIO** de presión de disco que
debe vigilarse antes de retención/cleanup posterior.

### Persistencia e idempotencia

Antes y después de reiniciar el contenedor y de múltiples ciclos stop/start:

```text
model files:       9
model bytes:       2,497,296,445
model tree SHA256: 56a69d7f542435eee19b0265d8185e9eddbddef8256bbb7e3c13c29697559dbd
```

No se descargó nuevamente el modelo. Tras reiniciar solo el contenedor, una
inferencia `full_gpu` tardó 4,840 ms y el árbol permaneció idéntico.

Una segunda ejecución del bootstrap en el mismo boot produjo
`boot_authorized=false` y `release=already_applied ... action=validate_only`.
El ID y `StartedAt` del contenedor, el digest del manifiesto aplicado y el hash
del modelo fueron exactamente iguales antes y después.

### Revisión inválida y rollback

Una copia con `revision_state=validated` fue rechazada con:

```text
ERROR: only pending_boot_validation may be applied
```

El código fue distinto de cero y no cambió contenedor, revisión ni pesos.

El procedimiento `rollback-release.sh --previous` se ejecutó realmente:

```text
515d343a... / b526b1d4... -> 6e2969d6... / f2a4fc8d...
6e2969d6... / f2a4fc8d... -> 515d343a... / b526b1d4...
```

Ambos extremos pasaron identidad, cuantización e inferencia `full_gpu`. El
hash del volumen no cambió y el estado final volvió a la revisión aprobada.

## Hallazgos durante la ejecución

### ALTO — stacks heredados de aplicación en la GPU

- **Causa:** dos despliegues Compose históricos completos tenían políticas de
  restart.
- **Impacto:** infringían el aislamiento e intentaban levantar datos y
  aplicación al encender la VM.
- **Corrección:** cuarentena idempotente; servicio Ollama host deshabilitado y
  todos los contenedores heredados detenidos con `restart=no`.
- **Riesgo residual:** los datos e imágenes siguen consumiendo disco porque no
  se autorizaron eliminaciones.

### ALTO — especificación CDI temporal visible

- **Causa:** `nvidia-ctk --output` añadió `.yaml` al temporal dentro de
  `/etc/cdi`, creando dispositivos duplicados.
- **Comportamiento:** el boot falló antes de aplicar la revisión y conservó el
  runtime anterior.
- **Corrección:** generación fuera del directorio de descubrimiento, staging
  no-YAML y rename atómico; limpieza limitada al patrón transitorio propio.
- **Prueba:** `nvidia_cdi=unchanged` en la segunda ejecución e inferencia L4.

### ALTO — manifiesto histórico ligado al bundle anterior

- **Causa:** al consultar la revisión aplicada, el reconciliador exigía que su
  digest histórico coincidiera con el bundle recién instalado.
- **Comportamiento:** falló cerrado y conservó la revisión anterior.
- **Corrección:** lectura histórica con validación estructural y proyección
  explícita, inmutable y revalidada al bundle actual solo para rollback.
- **Prueba:** rollback real en ambos sentidos y evidencia histórica conservada.

### ALTO — residencia no reconciliada cuando la revisión ya estaba aplicada

- **Causa:** después de un stop/start, Docker restauraba el contenedor antes
  del reconciliador, pero `/api/ps` estaba vacío. La rama de revisión ya
  aplicada validaba residencia sin ejecutar primero una inferencia.
- **Comportamiento:** el boot de reproducción
  `66b6c021-7093-41f3-aa7e-a1c63ada1fa7` falló cerrado; el contenedor siguió
  saludable y los 2,497,296,445 bytes del modelo permanecieron intactos.
- **Corrección:** espera acotada de health e inferencia mínima únicamente en
  modo boot; las reejecuciones del mismo boot siguen siendo no disruptivas.
- **Prueba:** el boot `307e64cd-6e20-444a-af69-54a749c00145` terminó con
  `Result=success`, `action=boot_inference`, `/api/ps` completamente en VRAM y,
  después, `action=validate_only` sin cambiar ID ni `StartedAt` del contenedor.

### BAJO — acceso SSH temporal

El primer intento de `gcloud compute ssh` añadió una clave local a metadata
común del proyecto. Se identificó y retiró inmediatamente solo esa línea. Para
las pruebas posteriores se usó una clave temporal de instancia con fingerprint
`SHA256:SvtxEa6rHdxDf2N1TAIDR8pANBSFLYHjOvePf0WyIB4`. Al finalizar se restauró
la metadata SSH original, la cuenta temporal quedó expirada, el acceso devolvió
`Permission denied` y todo el material local fue destruido de forma segura.

## Coste estimado

Las operaciones registran 3,386.448 segundos (56.44 minutos) de VM encendida.
Usando el precio on-demand de `g2-standard-4` en Iowa
(`USD 0.706832276/h`) como techo conservador, el cómputo fue como máximo
`USD 0.6649`; la factura Spot real debe consultarse en Cloud Billing porque su
precio es variable.

El snapshot usa 54.847 GiB comprimidos. A
`USD 0.000068493/GiB-h`, su primera hora mínima es aproximadamente
`USD 0.0038`; durante las primeras dos horas el techo es `USD 0.0075`, y
mantenerlo 730 horas cuesta aproximadamente `USD 2.74`. No hubo egress
interregional porque disco y snapshot están en `us-central1`. La IP
externa estática y el boot disk eran recursos preexistentes y conservan sus
cargos habituales.

Fuentes de precios consultadas el 2026-08-02:

- <https://cloud.google.com/products/compute/pricing/accelerator-optimized>
- <https://cloud.google.com/spot-vms/pricing>
- <https://cloud.google.com/compute/disks-image-pricing>

## Estado final y alcance

```text
hemovet-llm-gpu:     TERMINATED
last stop:           2026-08-02T15:28:08.659-07:00
private IP:          10.128.0.3
external static IP:  34.45.75.48
service account:     hemovet-gpu-runtime@project-5b36701c-f44f-4c03-a12.iam.gserviceaccount.com
desired release:     515d343ac805779f94be9277376bdadf5516154d
snapshot:            READY
```

`hemovet-prod` permaneció `RUNNING`, con `lastStartTimestamp` del 2026-07-02,
IP `136.64.136.49`, service account y disco originales. No se modificaron
PostgreSQL, Chroma, RAG, datos clínicos, firewall, VPC, subred, IPs,
configuración/tipo/tamaño/asociación de discos, GitHub Actions, secrets,
variables, environments, `main` o `dev/agosto`.

## Riesgos pendientes

- La regla `allow-ollama-internal` aún admite toda la subred y existen reglas
  internas/públicas heredadas; su restricción pertenece exclusivamente a la
  Etapa 7.
- La GPU conserva tags `http-server` y `https-server`; se evaluarán en Etapa 7.
- La VM sigue con `deletionProtection=false` y el boot disk con
  `autoDelete=true`; el snapshot mitiga, pero no elimina, el riesgo.
- Los stacks y volúmenes heredados siguen en disco; su eventual eliminación es
  destructiva y requiere autorización posterior.
- El apagado automático tras fallo definitivo no está habilitado porque no se
  aprobó esa política automática.
- La integración de publicación del manifiesto en GitHub Actions corresponde a
  la Etapa 8; Stage 6 solo instaló y probó el consumidor.
- Una reconstrucción desde una VM vacía aún requeriría formalizar la imagen o
  el aprovisionamiento host; el gate actual se apoya en el snapshot recuperable,
  metadata GCP del driver y validación exacta de versiones.
