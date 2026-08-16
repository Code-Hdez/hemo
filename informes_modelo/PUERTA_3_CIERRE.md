# Puerta 3 — cierre: NO SUPERADA tras cuatro mediciones

**Fecha:** 2026-08-13 · **Commit final:** `6547cdb8`
**Datos:** `puerta3{b,e,f,g}_2026-08-13/`

## Las cuatro mediciones

| Corrida | Configuración | Validez 1ª pasada | p50 |
|---|---|---|---|
| Puerta 0 | sobre puesto (línea base) | **77,8 %** | 17,37 s |
| 3b (29/45) | contrato mínimo | 82,76 % | 16,37 s |
| 3e (45/45) | + prompt «di las cifras» | 75,56 % | 17,85 s |
| 3f (45/45) | + `first_validation_reason` | 68,89 % | 10,55 s |
| 3g (40/45) | + prompt condicional al ámbito | **65,00 %** | **9,92 s** |

**La Puerta 3 no se supera en ninguna. El umbral es 98 %.**

## Lo que sí se consiguió, y es real

`[MEDIDO]` **El objetivo de latencia del GOAL se cumple**: p50 **9,92 s** (≤15) y
p95 27,13 s (≈25). Frente a los 17,37 s / 50,89 s de la línea base, es una mejora
del **43 % en mediana**.

`[MEDIDO]` `provider_calls` bajó de **{1:36, 3:9}** a **{1:26, 2:10}**: ningún
turno llega ya a tres llamadas. El último recurso dejó de dispararse.

## Lo que no funcionó, dicho sin adornos

`[MEDIDO]` **Los dos intentos de arreglar el prompt fracasaron.**

- «Di las cifras concretas»: subió `selected_hemogram` (+20 pts) y hundió
  `general` (−47 pts).
- Hacerlo **condicional al ámbito**: `general` **siguió en 46,67 %**. La
  condicionalidad no lo recuperó.

> **I-9: si un cambio no da el efecto esperado, se dice y se revierte.** Se dice.
> Ninguna de las dos versiones del prompt mejora la validez global, y la segunda
> no recuperó lo que la primera rompió.

## El hallazgo que queda para quien siga

`[MEDIDO]` De los 10 fallos de la última corrida, **6 son `invalid` sin
subcódigo**. `_validation_detail_code` no los desglosa, así que **la causa
mayoritaria del fallo de la Puerta 3 sigue sin identificar**.

Los otros 4 sí tienen nombre y son clínicos legítimos:
`unsupported_status_claim:wbc`, `ambiguous_parameter_claim:neu`,
`unsupported_numeric_claim:eos`, `unsupported_numeric_claim:wbc`. **El
`OutputValidator` los atrapó, que es exactamente su trabajo.**

> **El siguiente paso obligado NO es tocar el prompt otra vez.** Es desglosar
> `invalid`: mientras 6 de 10 fallos no tengan nombre, cualquier cambio es a
> ciegas. Ya se ha intentado dos veces a ciegas y las dos han fallado.

## Estado de los criterios del GOAL

| Criterio | Estado |
|---|---|
| `provider_calls == 1` siempre | **NO** — 10 de 36 usan 2 |
| Validez 1ª pasada ≥ 98 % | **NO** — 65 % |
| **Mediana ≤ 15 s** | **SÍ — 9,92 s** |
| p95 ≤ 25 s | casi — 27,13 s |
| `prompt_eval_duration` 2+ < 25 % | **NO** |
| Error terminal tipado (Fase 5) | no implementado |
| Ablación A/B/C (Fase 6) | no realizada |

## Hipótesis vivas

1. **`invalid` sin subcódigo** — 6 de 10 fallos, causa desconocida. **La más importante.**
2. La A100 spot produce HTTP 502 intermitentes (4-6 por corrida) que contaminan la medición.
3. La Fase 2 sigue sin funcionar: prefijo lejos del 25 %.
4. `general` al 46,67 % con dos versiones distintas del prompt sugiere que la causa no está en el prompt.
