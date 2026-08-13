# E-A · Ablación de gramática — resultado

**Sello:** A100-SXM4-40GB · driver 580.159.03 · CUDA 13.0 · Ollama 0.32.6 ·
modelo `qwen3.6:27b-q4_K_M` digest `a50eda8ed977ab48…` · 17 420 432 739 B ·
FLASH_ATTENTION=1 · KV_CACHE_TYPE=q8_0 · NUM_PARALLEL=1 · KEEP_ALIVE=-1.
Ventana: 2026-08-11T23:10:08Z → 23:21:52Z. Camino A (Ollama directo).

**Diseño:** n=30 por brazo, intercalado A/B/A/B, 5 descartes de warm-up,
pausa 500 ms, `temperature 0`, `seed 20260811`, `num_predict 200`,
`num_ctx 65536` (el del runner residente, para no forzar recarga),
`keep_alive -1`. 6 prompts rotados. **0 respuestas con modelo distinto al sellado.**

| Métrica | Con `format` | Sin `format` | Δ |
|---|---|---|---|
| decode tok/s (p50) | 40,097 | 40,639 | −0,542 |
| TPOT ms (p50) | 24,939 | 24,607 | **+0,332** |
| TPOT IQR | 24,752–25,004 | 24,361–24,890 | — |
| tokens de salida (p50) | 200 | 200 | 0 |
| residual ms (p50) | 2,89 | 2,70 | +0,19 |
| `done_reason` | `length` | `length` | — |

## H-2: REFUTADA

Pre-registro: «la sobrecarga de gramática es ≥10 ms/token». **Medido: 0,332 ms/token
(1,33 % del TPOT).** La literatura citada (+14,6 ms/token) **no reproduce en este
despliegue**: es ~44× mayor que lo observado.

Consecuencia: **el residual de 20,20 ms/token de la L4 no era gramática.** La
explicación hay que buscarla en otro sitio, y este diseño no dice dónde.

## Limitaciones de este resultado

- Ambos brazos alcanzaron `num_predict=200` con `done_reason: length`, así que se
  compara TPOT en régimen de decode puro. **No mide el coste de la gramática en la
  terminación**, que es donde §10.7-8 sitúa el fallo duro.
- `Δ_tokens = 0` por construcción (tope alcanzado), así que el sesgo de «la
  gramática genera menos» no se pudo evaluar.
- **Sólo se conservaron estadísticos resumen, no los valores crudos**, así que
  **no hay IC bootstrap BCa** — sólo mediana e IQR. Es un incumplimiento de I-4
  que se declara aquí: la siguiente corrida debe persistir los arrays.
- Sin log de throttling concurrente. La ventana fue de 12 min sobre una A100 de
  400 W con `persistence_mode Disabled`.
