# Fuentes investigadas

Jerarquía usada: **A** evidencia interna · **B** fuentes primarias ·
**C** comunidad · **D** foros. El nivel D sirve para *generar* hipótesis, nunca
para confirmarlas.

---

## Nivel A — evidencia interna (la que sostiene las conclusiones)

| Fuente | Qué aportó |
|---|---|
| `AUDITORIA_CORRELACIONADA.json` (2,4 MB, 70 casos, 133 llamadas) | Correlación verificada por contenido 70/70 |
| Telemetría `llm_chat.*` del contenedor backend (1.502 líneas) | Config, validación, métricas de Ollama, regeneraciones |
| Log de `llama-server` (4.472 líneas, 138 tareas) | Tokens y tiempos reales, **checkpoints de contexto** |
| `GET /api/v1/chat/conversations/{id}/turns` | Estado de los 70 turnos; `response: null` en los 17 fallidos |
| `/api/ps` de Ollama (`10.128.0.3:11434`) | Modelo, digest, `size_vram`, `context_length` |
| `nvidia-smi`, `ps`, `ss`, `docker inspect` | GPU, flags de `llama-server`, digest de imagen |
| Código: `send_chat_message.py`, `structured_response.py`, `output_claim_validator.py`, `conversation_routing.py`, `intent_classifier.py` | Ubicación exacta de cada validador |
| `git log`/`git show` de `587ef41d` y `bd70e0d8` | El volcado de depuración y el *salvage* sin conectar |
| Experimento de repetición ×10 | Tasa 1/10 de la 1.ª generación; 0/9 de la reparación |

---

## Nivel B — fuentes primarias

### Qwen3.6

- **Model card / documentación oficial.** Qwen3.6-27B opera en **modo thinking
  por defecto**; se desactiva con `enable_thinking: false`. Contexto nativo muy
  superior al configurado aquí. Soporte de serving en vLLM y SGLang, con
  configuración MTP para inferencia especulativa.
  → **Relevancia:** confirma que HemoVet **desvía del comportamiento por
  defecto** al enviar `thinking: false`, lo cual es coherente con un caso de uso
  de seguimiento de instrucciones. **No es una desviación problemática.**
  → **Limitación:** la documentación no cubre el comportamiento de thinking bajo
  Ollama + gguf Q4_K_M.

- **Recomendaciones de serving.** Qwen recomienda vLLM/SGLang para despliegues
  exigentes.
  → **Relevancia:** aplica a escenarios de concurrencia. HemoVet corre `-np 1`
  con un usuario. **No trasladable sin experimento.**

### Ollama

- **API:** expone `total_duration`, `load_duration`, `prompt_eval_count`,
  `prompt_eval_duration`, `eval_count`, `eval_duration`.
  → **Relevancia:** es exactamente lo que HemoVet ya registra en
  `llm_chat.ollama_metrics`, y lo que permitió el desglose prefill/decode.

- **Structured outputs por JSON Schema.**
  → **Relevancia:** sostiene la mitigación nº 4 (constrained decoding). El
  proyecto ya usa `model_json_schema() → format`, así que el camino existe.

- **Contexto y memoria:** `num_ctx` afecta directamente a la VRAM; el
  paralelismo multiplica la memoria del contexto.
  → **Relevancia:** explica por qué `-np 1` y `num_ctx 16384` dejan 5,6 GB
  libres.

- **Versión instalada: 0.32.5** (verificada en el contenedor).

### llama.cpp (backend real de Ollama)

- Flags observados en el proceso: `--flash-attn on`, `--cache-type-k q8_0`,
  `--cache-type-v q8_0`, `--context-shift`, `-np 1`.
- **Mecanismo de *context checkpoint*** para modelos híbridos/recurrentes:
  observado en vivo, 149,626 MiB por checkpoint.
  → **Relevancia:** es la evidencia que **descartó** la hipótesis de
  reprocesado completo.

### Papers

| Trabajo | Qué resuelve | ¿Aplica a HemoVet? |
|---|---|---|
| **PagedAttention / vLLM** (Kwon et al., 2023) — 2–4× de throughput reportado | Fragmentación del KV cache en servicio **concurrente** | **No directamente.** Mejora throughput agregado; HemoVet tiene 1 usuario y cola de 0 ms. No acelera el decode de una petición aislada |
| **FlashAttention** (Dao et al.) | Reduce tráfico de memoria de la atención | **Ya activo** (`--flash-attn on`). Nada que ganar |
| **Speculative decoding** — 2–3× reportado en ciertos modelos/hardware | Acelera **decode**, que aquí es el 87,2 % | **Es la técnica que ataca la causa dominante.** Pero depende del *acceptance rate* y su interacción con structured output no está verificada |

> **Advertencia metodológica aplicada:** ninguna de estas cifras se ha
> trasladado a HemoVet. Los benchmarks publicados usan GPUs, modelos,
> cuantizaciones y concurrencias distintas.

---

## Nivel C/D — comunidad y foros

| Búsqueda | Hallazgo | Uso |
|---|---|---|
| Rendimiento de 27B Q4_K_M en GPUs de consumo | ~40 tok/s en RTX 4090; ~42 tok/s Gemma-4-27B en RTX 5090 | **Comparación de orden de magnitud.** La L4 tiene ~30 % del ancho de banda de una 4090 y mide 13,05 tok/s → 33 %. Consistente |
| Issues de structured output en Ollama/llama.cpp | Existen incidencias con schemas y parsers en versiones concretas | **NO se atribuye causalidad.** No se verificó coincidencia de versión, componente y patrón contra 0.32.5. Queda como hipótesis no confirmada |
| Reprocesado de prompt en modelos híbridos/SWA | Reportes de pérdida de reutilización de caché | **Refutado localmente:** el log muestra checkpoints restaurados con éxito |

### Benchmark externo registrado con su contexto

```json
{
  "source": "búsqueda web agregada (nivel C/D)",
  "date": "2026-08",
  "engine": "llama.cpp",
  "engine_version": "no especificada en la fuente",
  "model": "27B clase Gemma/Qwen",
  "quantization": "Q4_K_M",
  "gpu": "RTX 4090 / RTX 5090",
  "tokens_per_second": "40-42",
  "concurrency": 1,
  "relevance_to_hemovet": "Sitúa el orden de magnitud esperable para 27B Q4_K_M. HemoVet mide 13,05 tok/s en L4",
  "limitations": "GPU distinta y de gama muy superior; versión de engine no especificada; no es una medida sobre L4. Sirve para acotar, no para concluir"
}
```

**Por eso el plan futuro incluye E-7 (`llama-bench` sobre la propia L4): una
medida directa vale más que esta comparación.**

---

## Repositorios inspeccionados

| Repositorio | Acceso | Resultado |
|---|---|---|
| `hemogramas-proyectoICC` (local) | lectura, `git log`/`show` | HEAD `21f18fd8`, sin ficheros modificados |
| `cristiandlahoz/socratic-tutor` | **clonado read-only** (`--depth 20`) | Ver `COMPARATIVA_SOCRATIC_TUTOR_2026-08-08.md` |
| `xPshycho/hemogramas-proyectoICC` (remoto) | no verificado contra el despliegue | Deja `H-15` en `EVIDENCIA_FUERTE`, no `CONFIRMADO` |

---

## Contradicciones con informes anteriores, declaradas

| Afirmación previa | Qué dice la evidencia | Corrección |
|---|---|---|
| «`OLLAMA_TEMPERATURE=0.6` en producción» (`ESTADO_LLM_2026-08-06.md`) | `llm_chat.generation_config` publica **0,3** (0,1 en reparación) en 133/133 | Corregido |
| «RAG 0,4 s» (auditoría del 7-ago) | Rango real **183–655 ms** | Era la mediana; se declara el rango completo |
| Lectura inicial propia: «el multiturno reprocesa todo el contexto» | `restored context checkpoint` baja el prefill a 4–417 tokens | **Refutada por mí mismo** |
| «La lotería se debe a la temperatura» | A temp 0,1 la reparación falla 9 de 9 veces | Insuficiente como explicación |
