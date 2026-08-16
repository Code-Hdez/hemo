# Diagnóstico y arreglo en caliente — GPU / chat LLM, 14-ago-2026

Revisión en solo lectura de la infraestructura GCP tras el reporte «la máquina
LLM está fallando», y arreglo en caliente **sin commits ni despliegue**.

Todo en **UTC**. Las operaciones de GCP se listan en `-07:00`; la conversión está
hecha en la línea de tiempo.

## Veredicto

**La GPU nunca estuvo rota.** Arrancó sana y validó su runtime. Lo que fallaba
eran dos cosas distintas superpuestas:

1. **Infra (ARREGLADO):** el modelo no estaba en VRAM, y cada intento de chat
   moría antes de terminar de cargarlo.
2. **Contrato (NO arreglado, requiere código):** parte de las respuestas se
   rechazan en la validación clínica y salen como `502`.

## Ficheros

| Fichero | Contenido |
|---|---|
| `gpu_hemovet-llm-gpu-a100.log` | journal de `hemovet-gpu.service`, `nvidia-smi`, `ollama ps`, entorno de Ollama, salida del warmup, puertos |
| `gpu_ollama_container.log` | log completo del contenedor de Ollama (30.878 líneas) |
| `prod_backend.log` | log completo del backend, incluida la telemetría `llm_chat.*` (8.431 líneas) |
| `prod_infra_y_caddy.log` | contenedores de `hemovet-prod` y últimas 400 líneas de Caddy |
| `gcp_operaciones.log` | últimas 40 operaciones de cómputo + estado de las instancias |
| `pruebas_end_to_end.log` | las 4 peticiones de chat reales lanzadas para verificar |
| `warm.sh` | el script de warmup que se ejecutó en la VM |

## Estado de partida (16:52 UTC)

Todo reportaba salud, y aun así el chat no respondía:

```
hemovet-llm-gpu-a100   RUNNING   us-central1-a   a2-highgpu-1g (SPOT)
hemovet-prod           RUNNING   us-central1-c   n2d-standard-4
hemovet-gpu-ollama-1   Up (healthy)      backend   Up (healthy)
GET /api/v1/chat/health → 200 OK
```

Pero:

```
nvidia-smi → 0 MiB usados        ollama ps → (vacío)
```

El arranque de la GPU sí había ido bien:

```
runtime=valid release=4cca5683 model=qwen3.6:27b-q4_K_M
inference_device=full_gpu latency_ms=107475
hemovet_gpu_startup=ready
```

## Causa raíz

### 1. Orden de encendido invertido

`hemovet-prod` se encendió **26 minutos antes** que la GPU:

| Evento | UTC |
|---|---|
| `start hemovet-prod` | 16:20:42 |
| `start hemovet-llm-gpu-a100` | 16:46:26 |
| GPU valida y queda `ready` | 16:49:45 |

El warmup del backend agotó su timeout contra una GPU que aún no existía:

```
llm_chat.provider_error {"duration_ms": 119999, "error_type": "warmup_failed"}
llm_chat.provider_warmup completed=False baseline_vram=None
```

El orden seguro es GPU primero, esperar a `hemovet_gpu_startup=ready`, y solo
entonces `hemovet-prod`.

### 2. El bucle que impedía cargar el modelo

Sin modelo residente, el primer chat paga la carga en frío (~107 s medidos en la
validación de arranque). Nadie espera tanto, y al abortar, la cancelación se
propaga hasta Ollama y **mata la carga en curso**. VRAM vuelve a 0 y el
siguiente intento empieza de cero: nunca converge.

Correlación al milisegundo entre las tres capas:

| Capa | UTC | Registro |
|---|---|---|
| Caddy | 16:51:26.705 | `aborting with incomplete response`, `duration 0.018`, `POST /api/v1/chat/stream`, `error: reading: context canceled` |
| Backend | 16:51:26.706 | `error_code: CancelledError`, `stage.failed` |
| Ollama | 16:51:28 | `499 \| 1m8s \| POST /api/chat` |

Los **0,018 s** de Caddy descartan un timeout del proxy: es el cliente cortando.
El **499** es Ollama registrando que el cliente colgó tras 68 s de trabajo.

## El arreglo aplicado

Una única petición de carga, **desacoplada de la sesión SSH** con `setsid` (si
muriera con la conexión, reproduciría el mismo fallo), y con los **mismos
parámetros que usa producción** para que no haya una recarga posterior:

```
POST 10.128.0.3:11434/api/generate
{"model":"qwen3.6:27b-q4_K_M","keep_alive":-1,
 "options":{"num_ctx":16384,"num_predict":1}}
```

`num_ctx=16384` es deliberado: el contenedor tiene `OLLAMA_CONTEXT_LENGTH=65536`
pero el backend pide 16384 en cada `generation_config`, y con
`OLLAMA_MAX_LOADED_MODELS=1` un contexto distinto obliga a evictar y recargar
aunque `OLLAMA_KEEP_ALIVE=-1`. Cargar con el valor de producción evita esa
recarga.

Resultado (`load_duration` 55,2 s, `curl_exit=0`):

```
NAME                  ID              SIZE     PROCESSOR    CONTEXT    UNTIL
qwen3.6:27b-q4_K_M    a50eda8ed977    16 GB    100% GPU     16384      Forever
nvidia-smi → 17418 MiB
```

**No se editó ningún fichero, ni `.env`, ni se reinició ningún contenedor, ni se
desplegó nada.** El cambio vive solo en la memoria de la GPU.

## Verificación end-to-end

Cuatro peticiones reales contra `https://hemovet.app` con el fixture
`test5@test.com`. Ninguna latencia corresponde ya a una carga en frío:

| Pregunta | Ámbito | HTTP | Tiempo |
|---|---|---|---|
| `Que es el hematocrito?` | general | 502 | 29,0 s |
| `Hola, en que me puedes ayudar?` | general | 502 | 13,8 s |
| `Cual es el hematocrito de este paciente?` | selected_hemogram | **200** | **6,6 s** |
| `Que significa una policitemia?` | general | **200** | 36,6 s |

La respuesta clínica es correcta y coincide con el fixture: HCT **63,6 %**, por
encima del rango. El chat funciona.

## Lo que sigue roto (necesita código, fuera de este arreglo)

### Validación de salida — los 502

Los 93 `ChatRuntimeUnavailable` del log **no son caídas del proveedor**: son
respuestas rechazadas por la validación clínica, una a una. Suman exactamente 93:

| `terminal_error` | Casos |
|---|---|
| `invalid_output_ambiguous_parameter_claim` | 55 |
| `invalid_output_indirect_treatment_recommendation` | 16 |
| `invalid_output_missing_evidence_attribution` | 13 |
| `invalid_output_unsupported_status_claim` | 5 |
| `invalid_output_unsupported_numeric_claim` | 4 |

El bloque dominante (55, el 59 %) es `ambiguous_parameter_claim`, justo lo que
atacaba el Bloque D revertido en `bd0da4e1`. Es el problema de la campaña pass^5,
no de infraestructura.

### Extracción con Gemini caída

```
google.genai.errors.ClientError: 401 UNAUTHENTICATED
reason: ACCESS_TOKEN_TYPE_UNSUPPORTED
extraction.attempt.fail extractor=gemini model=gemini-3.1-flash-lite
```

`ACCESS_TOKEN_TYPE_UNSUPPORTED` apunta a credencial del **tipo** equivocado (un
token OAuth donde se espera una API key), no a una caducada.

### Telemetría sin exportar

`OpenTelemetry lifecycle (sdk_status=invalid_otlp_endpoint, fastapi_status=sdk_unavailable)`

## Advertencias

- El modelo está en VRAM **solo mientras la VM siga encendida**. Si se apaga
  `hemovet-llm-gpu-a100`, hay que repetir el warmup al volver, respetando el
  orden GPU → `ready` → prod.
- La GPU es **SPOT** y sigue `RUNNING`, con coste corriendo. No se apagó porque
  está en uso.
- La hipótesis del `num_ctx` explica la recarga y es consistente con lo medido,
  pero **no se ha aislado experimentalmente**. Cuadrar `OLLAMA_CONTEXT_LENGTH`
  con el `num_ctx` de producción es candidato a arreglo permanente, y eso sí
  tocaría configuración.
