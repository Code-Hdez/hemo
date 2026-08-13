# 08 — Investigación externa

## Nivel 1 — fuentes primarias

### NVIDIA L4 (especificación)
- 24 GB GDDR6, **300 GB/s**, bus 192-bit, Ada Lovelace, 30,3 TFLOPS FP32, 72 W TDP
- **Uso:** base del cálculo del techo de decode (§06). Es la cifra que convierte
  «la L4 es lenta» en una predicción falsable: 300 ÷ 16,93 GB = 17,7 tok/s

### Qwen3.6-27B (model card)
- ~27 B parámetros, contexto nativo 262.144, arquitectura híbrida
- **Modo thinking activado por defecto**; se desactiva con `enable_thinking: false`
- Recomienda vLLM/SGLang para serving, con configuración MTP
- **Uso:** HemoVet envía `think: false`, lo que **se verificó experimentalmente**
  que suprime el razonamiento (§17). La desviación del defecto es correcta

### Ollama 0.32.5
- API expone `total_duration`, `load_duration`, `prompt_eval_count/duration`,
  `eval_count/duration` — es lo que HemoVet registra y permitió el desglose
- Structured outputs por JSON Schema vía `format` — **ya en uso**
- **Uso:** confirmó que `payload["format"]` es el camino de gramática

### llama.cpp
- Flags observados: `--flash-attn on`, `--cache-type-k/v q8_0`, `-np 1`
- **Context checkpoints** para modelos híbridos: 149,626 MiB, observados en vivo

## Nivel 2/3 — ingeniería y comunidad

| Fuente | Dato | Aplicabilidad a HemoVet | Limitaciones |
|---|---|---|---|
| Benchmark comunidad | **Qwen3.6 27B + MTP en RTX 3090: 38 → 65 tok/s (1,71×)** | **Alta**: mismo modelo, misma familia | GPU distinta (3090 ≈ 936 GB/s vs L4 300) |
| Benchmark comunidad | Gemma 2 27B: 67 → 120 tok/s (1,8×) | Media: mismo tamaño, otro modelo | Hardware no especificado |
| Blogs de ingeniería | Speculative decoding: **20-50 % en latencia de petición única** | **Alta**: HemoVet es petición única | Genérico |
| llama.cpp discussions | Si la aceptación del borrador cae del 50 %, **ralentiza** | Alta: condición de fracaso a vigilar | — |
| Benchmarks 27B Q4_K_M | ~40 tok/s en RTX 4090 | Media | Sirve para validar la relación de anchos de banda, no para extrapolar |

## Papers

| Trabajo | Qué resuelve | ¿Aplica? |
|---|---|---|
| **PagedAttention / vLLM** (2–4× throughput) | Fragmentación del KV en servicio **concurrente** | **No directamente**: HemoVet tiene `-np 1` y cola de 0 ms. Mejora throughput agregado, no la latencia de una petición aislada |
| **FlashAttention** | Tráfico de memoria de la atención | **Ya activo** |
| **Speculative decoding** (2–3×) | Rompe la relación 1 token = 1 lectura completa de pesos | **Sí**: ataca decode, que es el 88,4 % |

## Advertencia metodológica aplicada

Ninguna cifra externa se ha trasladado a HemoVet como predicción. El único uso
legítimo que se les ha dado es **acotar órdenes de magnitud** y **generar
hipótesis experimentales**. La medida que sostiene la conclusión de hardware es
interna: 13,04–13,71 tok/s medidos directamente contra el modelo desplegado.
