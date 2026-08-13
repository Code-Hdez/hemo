# 07 — Contexto, memoria y caché

## Caché de prefijo: activo y cuantificado

Mecanismo real: **context checkpoints de llama.cpp** para la arquitectura híbrida
de Qwen3.6, de **149,626 MiB** cada uno.

```
task 157291 | restored context checkpoint (n_past = 1370) | prompt eval = 4 tokens
task 157527 | restored context checkpoint (n_past = 3454) | prompt eval = 417 tokens
```

**Ahorro medido:** `llama-server` procesó **376.870** tokens de los **496.909**
contenidos en los prompts → **24,2 % ahorrado**. 37 de 138 tareas entraron con
menos de 1.000 tokens de prefill.

Coste del mecanismo: `prompt cache update` tarda **501–666 ms** por ocurrencia.

### El techo aritmético de cualquier optimización de prefill

```
prefill = 11,5 % del tiempo del modelo
ya se ahorra el 24,2 % de él
techo de eliminar el 100 % restante = 11,5 % × 75,8 % ≈ 8,7 % de la latencia total
```

**Una optimización de prefill perfecta recortaría ~5 s de los 59 s de mediana.**
Ésa es la razón —aritmética, no de opinión— por la que prefix caching no puede
presentarse como solución principal.

## Memoria conversacional actual

`history_limit = 12` en **todos** los perfiles, y es límite de **mensajes**:
→ **6 pares**, frente a los **10** que pide el objetivo de producto.

Crecimiento medido (hilo MT-B):

| Turno | `prompt_eval_count` | `prompt_eval_duration` |
|---|---:|---:|
| 1 | 3.871 | 5.736 ms |
| 2 | 5.151 | 7.660 ms |
| 3 | 5.167 | 7.666 ms |
| 4 | 5.378 | 7.974 ms |

~500 tokens por par. Diez pares ≈ +5.000 sobre una base de ~3.900 → **~8.900 de
los 12.000** de `max_input_tokens` (74 %). Cabe.

> **Distinción que la Fase 1 confundió inicialmente y aquí queda clara:**
> `prompt_eval_count` es la **longitud lógica** del prompt; los tokens
> **realmente reevaluados** son los de `llama-server`, y son un 24,2 % menos.
> Crecer el historial no cuesta lo que parece, porque el prefijo se reutiliza.

## Estrategias para los 10 pares

| Estrategia | Latencia | Calidad | Riesgo específico de HemoVet |
|---|---|---|---|
| **Ventana por tokens** (no por mensajes) | Baja | Alta | Ninguno. Preserva el prefijo → mantiene el checkpoint |
| Ventana por pares | Baja | Alta | Evita partir un par, que hoy sí puede ocurrir |
| **Resumen + turnos recientes** (estilo Socratic Tutor) | **Riesgo** | Alta | **Un resumen recalculado cada turno cambia el prefijo e invalida el checkpoint de 149,6 MiB.** Recalcular cada N turnos lo evita |
| Memoria semántica / externa | Media | Variable | Añade recuperación a un camino que hoy sólo la usa 8 de 70 veces |

**Recomendación de investigación (no de implementación):** ventana por
presupuesto de tokens anclada a pares completos, con resumen sólo al superar el
presupuesto y **no en cada turno**, para no destruir la reutilización de prefijo.
