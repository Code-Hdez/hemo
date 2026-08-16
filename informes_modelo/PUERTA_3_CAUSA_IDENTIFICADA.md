# Puerta 3 — NO SUPERADA, pero la causa ya está identificada

**Fecha:** 2026-08-13 · **Commit:** `f561a99a` · **Datos:** `validacion_llm/resultados/puerta3f_2026-08-13/puerta_3f.jsonl`
**Corrida:** 45/45 con el contrato mínimo, el prompt corregido y `first_validation_reason` instrumentado.

## Veredicto

`[MEDIDO]` Validez de primera pasada **68,89 %** (31/45). **NO SUPERADA.**
`provider_calls`: **{1: 31, 2: 8}** sobre los 39 turnos que respondieron.
Seis turnos dieron **HTTP 502** por inestabilidad del proveedor.

## Lo que la instrumentación revela

`[MEDIDO]` Motivo del rechazo de la **primera** generación:

| Motivo | n |
|---|---|
| `valid` | 31 |
| **`invalid`** | **5** |
| `repairable` | 1 |
| `unsupported_status_claim:mchc` | 1 |
| `unsupported_numeric_claim:wbc` | 1 |

Y por turno:

| Turno | Motivo |
|---|---|
| GEN-02, GEN-03, GEN-07, GEN-10, GEN-13 | `invalid` |
| GEN-09 | `repairable` |
| HIS-02 | `unsupported_status_claim:mchc` |
| HIS-04 | `unsupported_numeric_claim:wbc` |

> **Hallazgo que reordena el diagnóstico: seis de los ocho fallos son de
> `general`, el ámbito SIN datos de paciente.** Las tres corridas anteriores
> apuntaban a lo contrario porque no se sabía el motivo, solo el recuento.

`[DERIVADO]` `general` cayó a **46,67 %** en esta corrida frente al 93,33 % de la
anterior, mientras `selected_hemogram` **subió a 93,33 %** desde el 73,33 %. La
instrucción añadida al prompt —«di las cifras concretas»— ayudó donde hay cifras
y **estorbó donde no las hay**: en preguntas generales el modelo no tiene valores
que citar, y la respuesta acaba clasificada `invalid`.

## Los dos fallos con nombre propio

`unsupported_status_claim:mchc` y `unsupported_numeric_claim:wbc` son
**afirmaciones sobre parámetros que el validador no pudo respaldar**. Son los
únicos dos fallos genuinamente clínicos de los ocho, y justamente los que el
`OutputValidator` está para atrapar. **Funcionó.**

## Latencia — la única métrica que sí mejoró

`[MEDIDO]` p50 **10,55 s** · p95 **20,28 s**.

| | Puerta 0 | Esta corrida |
|---|---|---|
| p50 | 17,37 s | **10,55 s** |
| p95 | 50,89 s | **20,28 s** |

> **El objetivo de latencia del GOAL —mediana ≤ 15 s, p95 ≤ 25 s— SE CUMPLE por
> primera vez.** No por el contrato mínimo en sí, sino porque hay menos turnos
> gastando llamadas extra: 8 de 39 frente a 9 de 45, y ninguno llega a tres.

## Estado de los invariantes

| Criterio | Estado |
|---|---|
| `provider_calls == 1` siempre | **NO** — 8 de 39 usan 2 |
| Validez 1ª pasada ≥ 98 % | **NO** — 68,89 % |
| Mediana ≤ 15 s | **SÍ** — 10,55 s |
| p95 ≤ 25 s | **SÍ** — 20,28 s |
| `prompt_eval_duration` turno 2+ < 25 % | **NO** |

## Qué hacer, ahora con evidencia

1. **Revisar la instrucción añadida al prompt para el ámbito `general`.** Pedir
   cifras concretas cuando no hay paciente en alcance es contraproducente: se
   midió el daño (93 % → 47 %) y el beneficio (73 % → 93 %) en la misma corrida.
   La instrucción debe ser **condicional al ámbito**.
2. **Averiguar qué significa `invalid` a secas.** Cinco turnos lo dan sin
   subcódigo; `_validation_detail_code` no lo desglosa. Hay que instrumentarlo
   más fino antes de volver a tocar el prompt.
3. **No pasar a la Fase 4** hasta que la Puerta 3 pase.

## Hipótesis vivas

1. `invalid` sin subcódigo — cinco turnos, causa desconocida.
2. La inestabilidad del proveedor (6 × HTTP 502) contamina la medición; con la
   A100 spot no hay corrida limpia garantizada.
3. La Fase 2 sigue sin funcionar.
