# Observabilidad y benchmarking del chat LLM

Esta guía describe los adaptadores y scripts preparados para medir HemoVet sin
registrar prompts, conversaciones, respuestas clínicas ni razonamiento interno.
No despliega infraestructura, no descarga modelos y no cambia el runtime activo.

## Telemetría OTLP/HTTP

`app.modules.llm_chat.infrastructure.observability` proporciona:

- `StructuredChatLogger`: JSON allowlisted, correlación por `request_id` y HMAC
  para sesión, usuario, mascota, paciente, conversación y análisis.
- `ChatTelemetry`: spans, histograma de duración por etapa y contador de
  resultados mediante OpenTelemetry.
- bootstrap versionado de SDK/exportadores OTLP/HTTP durante el lifespan de
  FastAPI, instrumentación HTTP y cierre/flush acotado;
- modo no-op seguro cuando OpenTelemetry está desactivado.

Producción exige `OTEL_ENABLED=1`, un endpoint OTLP/HTTP privado y
`OTEL_IDENTIFIER_HMAC_SECRET`. Los headers del exportador son `SecretStr` y ni el
preflight ni el estado público imprimen sus valores. La instrumentación elimina
URL, query, IP, user-agent y headers de los spans HTTP; el span hijo
`llm_chat.request` solo recibe códigos allowlisted. En desarrollo puede usarse el
modo no-op; sin secreto HMAC se genera una clave efímera que no correlaciona IDs
entre reinicios.

La composición productiva integra la fachada así:

```python
telemetry = ChatTelemetry(
    enabled=telemetry_enabled,
    hmac_secret=telemetry_hmac_secret,
)

with telemetry.bind(request_id=request_id, session_id=session_id):
    with telemetry.span("retrieval", {"intent": intent, "mode": mode}):
        chunks = await retrieve()
    telemetry.record_result("valid", attributes={"intent": intent, "mode": mode})
```

No se deben pasar a estos métodos `message`, `prompt`, `answer`, `content`, chunks
completos, hechos clínicos completos o chain-of-thought. Aunque se pasen por
error, el logger los descarta. Las métricas admiten únicamente etiquetas de baja
cardinalidad: etapa, intención, modo, proveedor, resultado y código de error.

## Inspección segura de Ollama y GPU

Ejecutar en la VM objetivo desde un namespace que pueda resolver la URL interna
de Ollama. Si existe un puerto enlazado exclusivamente a loopback:

```bash
python backend/scripts/inspect_llm_runtime.py \
  --ollama-url http://127.0.0.1:11434 \
  --model qwen3.6:27b-q4_K_M \
  --ollama-container hemovet-ollama-1 \
  --output /tmp/hemovet-runtime.json
```

Ollama no debe publicarse a Internet para facilitar esta inspección. En la
topología Compose interna se pueden generar dos artefactos: metadatos de Ollama
desde el contenedor backend y métricas GPU desde el host.

```bash
docker compose exec -T backend \
  python scripts/inspect_llm_runtime.py \
  --ollama-url http://ollama:11434 \
  --model qwen3.6:27b-q4_K_M \
  --skip-gpu > /tmp/hemovet-ollama-runtime.json

python backend/scripts/inspect_llm_runtime.py \
  --skip-ollama \
  --ollama-container hemovet-ollama-1 \
  --output /tmp/hemovet-gpu-runtime.json
```

El resultado contiene versión de Ollama, etiqueta, digest, cuantización, tamaño,
contexto, `size_vram`, clasificación `full_gpu`/`mixed_cpu_gpu`/`cpu`, consulta
segura de `nvidia-smi` y estadísticas limitadas del contenedor. `full_gpu` exige
`size_vram / size >= 0.98`; un valor de VRAM mayor que cero no basta.

El script nunca incluye `system`, `template`, Modelfile, prompts o vocabularios
devueltos por `/api/show`. Los fallos se reportan como código y componente, sin
volcar respuestas ni `stderr`. Si `nvidia-smi` o Docker no están disponibles,
conserva los datos restantes y termina con código distinto de cero.

## Benchmark SSE

Copiar el dataset de ejemplo fuera del repositorio y reemplazar únicamente los
IDs de prueba por recursos autorizados:

```bash
cp backend/docs/examples/llm_benchmark_cases.example.jsonl /tmp/hemovet-cases.jsonl
```

El token se transmite mediante una variable de entorno para que no aparezca en
la línea de comandos:

```bash
HEMOVET_BENCHMARK_TOKEN='TOKEN_TEMPORAL' \
python backend/scripts/benchmark_chat_sse.py \
  --base-url http://127.0.0.1:8000/api/v1 \
  --dataset /tmp/hemovet-cases.jsonl \
  --concurrency 1,2,4,8 \
  --repetitions 20 \
  --warmup 3 \
  --timeout-seconds 90 \
  --cancel-fraction 0.05 \
  --cancel-after-ms 500 \
  --model-name qwen3.6:27b-q4_K_M \
  --model-digest REEMPLAZAR_DIGEST \
  --quantization Q4_K_M \
  --context-length 65536 \
  --prompt-version REEMPLAZAR_VERSION \
  --retriever-version REEMPLAZAR_VERSION \
  --embedding-version REEMPLAZAR_FINGERPRINT \
  --output /tmp/hemovet-chat-benchmark.json
```

Cada escenario informa solicitudes completadas, errores, cancelaciones,
throughput, códigos de error y distribuciones p50/p75/p90/p95/p99/máximo para:

- primer evento SSE;
- primer evento `final`, es decir, el primer punto en que el stream entrega el
  `ChatResponse` completo ya validado y persistido (idéntico al que luego
  repite `done`);
- duración total.

Un stream sin evento terminal se marca `missing_terminal_event`; un `done` sin
que haya llegado antes un `final` con contenido se marca
`missing_approved_content`. Las cancelaciones intencionales se separan de los
errores. Los resultados por muestra contienen nombre de caso, tiempos, estado y
código técnico, nunca la pregunta, la respuesta, el token, la mascota o el
análisis.

Para una comparación válida:

1. Capturar primero el runtime con `inspect_llm_runtime.py`.
2. Calentar el modelo y mantener iguales corpus, prompt, contexto y perfiles.
3. Ejecutar 50–100 solicitudes por escenario cuando el tiempo lo permita.
4. Repetir para cada configuración y conservar los JSON crudos.
5. No promover una configuración con violaciones críticas, OOM, descarga parcial
   a CPU o degradación de exactitud aunque mejore la latencia.

`--allow-unauthenticated` existe solo para un backend local deliberadamente sin
autenticación. No debe usarse contra producción. `--fail-on-error` permite hacer
fallar un job de evaluación si cualquier muestra termina en error.
