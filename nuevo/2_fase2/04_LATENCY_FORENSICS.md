# 04 — Descomposición de latencia

## Doble corroboración independiente

| Fuente | prefill | decode | % decode |
|---|---:|---:|---:|
| Telemetría backend (133 llamadas) | 551 s | 4.241 s | **88,5 %** |
| Log `llama-server` (138 tareas) | 572 s | 4.360 s | **88,4 %** |

Verificación cruzada de tokens entre ambas fuentes:
- `eval_count`: **133/133 coinciden (100 %)**
- `prompt_eval_count`: 98/133 (73,7 %) — **la diferencia es el caché**: Ollama
  informa del prompt completo, `llama-server` de lo que realmente evaluó

## Reparto global

| Componente | Tiempo | % |
|---|---:|---:|
| Dentro de Ollama | 4.922 s | **99,6 %** |
| Backend + validación + RAG + cola + red | 18 s | 0,4 % |

Dentro del modelo: decode 4.241 s (87,2 %), prefill 551 s (11,3 %), load 73 s (1,5 %).

## Por alcance

| Serie | n | mediana | p90 | máx |
|---|---:|---:|---:|---:|
| Total | 70 | 59,1 s | 128,8 s | 212,3 s |
| TTFB | 70 | 0,2 s | 0,2 s | 0,2 s |
| `general` | 17 | 23,0 s | 65,9 s | 128,8 s |
| `selected_hemogram` | 32 | 71,9 s | 140,7 s | 181,8 s |
| `hemogram_history` | 21 | 90,6 s | 112,7 s | 212,3 s |

## Amplificación por reparación

- Sin reparación (n=36): mediana **34,8 s**
- Con reparación (n=34): mediana **98,1 s** → **+182 %**
- `latencia real / latencia de una válida a la primera` = 98,1/34,8 = **2,82×**

## TTFT: NO_OBSERVABLE

No hay eventos `delta`/`token` en el flujo SSE; `t_primer_texto_s` es `null` en
las 70. El usuario no ve nada hasta que la validación termina. **TTFB (0,2 s) no
es TTFT** — es sólo el momento en que el servidor abre el flujo.
