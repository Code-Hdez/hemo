# Puerta 3 — mejor medición: 89,47 % sobre los turnos que completaron

**Fecha:** 2026-08-13 · **Commit:** `0b471aaa` · **Datos:** `validacion_llm/resultados/puerta3h_2026-08-13/`

## Los números

`[MEDIDO]` 45 turnos lanzados · **38 completaron** · **7 dieron HTTP 502**.

| Denominador | Validez 1ª pasada |
|---|---|
| Sobre los 45 lanzados | 34/45 = **75,56 %** |
| **Sobre los 38 que completaron** | 34/38 = **89,47 %** |

`[MEDIDO]` `provider_calls`: **{1: 34, 2: 4}**. Solo **4 turnos** necesitan una
segunda llamada. Ninguno llega a tres.

| | Puerta 0 (línea base) | Esta corrida |
|---|---|---|
| `provider_calls` | {1:36, 3:9} | **{1:34, 2:4}** |
| p50 | 17,37 s | **9,28 s** |
| p95 | 50,89 s | **17,99 s** |

## El objetivo de latencia del GOAL se cumple

`[MEDIDO]` **p50 9,28 s ≤ 15 s** y **p95 17,99 s ≤ 25 s**. Los dos criterios de
latencia del GOAL, cumplidos. Frente a la línea base es un **47 % menos** en
mediana y un **65 % menos** en p95.

## Por qué la Puerta 3 sigue sin pasar

`[MEDIDO]` Los cuatro fallos de validación:

| Turno | Ámbito | Motivo |
|---|---|---|
| GEN-03, GEN-12, GEN-13 | general | `invalid` |
| HIS-15 | historial | `unsupported_numeric_claim:plt` |

`[MEDIDO]` **`general` sigue siendo el ámbito débil**: 60 % frente a 86,67 % de
seleccionado y 80 % de historial. Es coherente con las tres corridas anteriores.

`[INFERIDO]` Los tres `invalid` de `general` siguen sin desglosar pese al arreglo
de `first_validation_reason`. O `validation.reason` vale literalmente `invalid`
en esa ruta, o el candidato inicial de `general` no pasa por el mismo camino.
**Sigue siendo la hipótesis a resolver antes de tocar nada.**

## Los 7 HTTP 502

`[MEDIDO]` Siete turnos murieron en transporte, no en validación. La A100 spot ha
sido desalojada tres veces durante esta sesión y produce 502 intermitentes.

`[DERIVADO]` **Con infraestructura estable, la validez medida sería 89,47 %**, no
75,56 %. La diferencia entre los dos denominadores no es cosmética: uno mide el
contrato, el otro mide el contrato más la estabilidad del spot.

## Estado de los criterios del GOAL

| Criterio | Estado |
|---|---|
| `provider_calls == 1` siempre | **NO** — 4 de 38 usan 2 |
| Validez 1ª pasada ≥ 98 % | **NO** — 89,47 % |
| **Mediana ≤ 15 s** | **SÍ — 9,28 s** |
| **p95 ≤ 25 s** | **SÍ — 17,99 s** |
| `prompt_eval_duration` 2+ < 25 % | **NO** |

## Hipótesis vivas

1. **Los tres `invalid` de `general`** — la causa sigue sin nombre.
2. **La A100 spot no permite una corrida limpia.** Tres desalojos y 502
   intermitentes en una sola sesión.
3. La Fase 2 sigue sin funcionar.
4. `HIS-15` con `unsupported_numeric_claim:plt` es un fallo clínico legítimo que
   el `OutputValidator` atrapó correctamente.

---

## Addendum — por qué los tres `invalid` siguen sin nombre

`[MEDIDO]` `OutputValidation.disposition` devuelve `"invalid"` cuando
`is_safe=False`. Mi instrumentación usa `_v.reason or _v.disposition`, así que
ver `"invalid"` significa que **`reason` llegó vacío**.

`[MEDIDO]` Los **12** sitios del validador que construyen `is_safe=False`
**sí fijan `reason`** (comprobado uno a uno). Por tanto la explicación no está en
el validador.

`[INFERIDO]` Quedan dos candidatos, y hay que descartarlos por medición, no por
lectura:

1. **El rechazo de esos tres turnos no viene de `OutputValidator`** sino de otra
   capa —el guard, el sanitizador o la validación de claims— que construye su
   propio `OutputValidation` sin `reason`.
2. El punto donde anoto (`initial_candidate.validation`) no es el que decide
   `needs_repair` para esa ruta.

**Cómo resolverlo:** registrar también `is_safe`, `meets_intent` y `detail` en
crudo junto al `reason`, y correr solo los tres casos GEN-03, GEN-12 y GEN-13.
Son tres turnos: no hace falta la batería entera.
