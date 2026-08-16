# Puerta 3 — los rechazos, por fin, con nombre

**Fecha:** 13-ago-2026 · **Corrida:** `diag_general_2026-08-13` · 15 turnos del ámbito `general`

---

## Lo que se buscaba

Tres turnos —GEN-03, GEN-12, GEN-13— salían como `invalid` **sin motivo**. Sin
nombre no se puede corregir el prompt: se corrige a ciegas, y este proyecto ya
declaró dos veces que eso no cuenta como trabajo.

`[MEDIDO]` La causa de que no tuvieran nombre **no era del validador**: era que
la instrumentación que lo expone nunca llegó a producción, porque los
redespliegues iban en commits vacíos. Está documentado aparte en
`TRAMPA_COMMIT_VACIO.md`.

## Lo que dicen ahora

`[MEDIDO]` Con `r=…|safe=…|intent=…|d=…` desplegado de verdad:

| Turno | `reason` | `is_safe` | `meets_intent` | Llamadas |
|---|---|:--:|:--:|:--:|
| GEN-03 | `indirect_treatment_recommendation` | 0 | 1 | 2 |
| GEN-04 | `indirect_treatment_recommendation` | 0 | 1 | 2 |
| GEN-09 | `intent_mismatch_scope_boundary` | 1 | 0 | 2 |
| GEN-12 | `definitive_diagnosis` | 0 | 1 | 2 |
| GEN-13 | `missing_evidence_attribution` | 0 | 1 | 2 |
| otros 7 | `ok` | 1 | 1 | 1 |

**No era un fallo. Eran cuatro comprobaciones distintas**, y solo una de ellas
sobra.

## La clasificación, que es lo que decide qué se toca

### Tres son capturas clínicas legítimas — **no se tocan** (I-5)

`indirect_treatment_recommendation` (×2) y `definitive_diagnosis` significan que
**el primer candidato del modelo recomendó tratamiento de forma indirecta o
afirmó un diagnóstico**. En un sistema que interpreta analíticas de un animal
enfermo, que el validador las detenga es exactamente lo que debe pasar.

> Bajar el umbral de estas tres para alcanzar el 98 % sería «relajar una
> validación para pasar una puerta», que es una señal de desvío declarada del
> proyecto. **No se hace.** Si el 98 % exige que el modelo deje de escribir
> tratamientos y diagnósticos, el trabajo está en el prompt y en `TurnGuard`,
> nunca en el validador.

### Una es autodeclaración — **se elimina** (I-3)

`missing_evidence_attribution` no comprueba nada clínico: comprueba que el
modelo escribiera `[[EVIDENCE_USED:S1,S2]]` al final del texto. I-3 lo prohíbe
literalmente —*«Nada de … `source_ids` …: el servidor ya lo sabe»*— y §4.1 del
plan asigna ese campo al servidor.

`[MEDIDO]` La recuperación ya existía en
`_infer_single_general_source_attribution`, pero **solo cubría el caso de una
sola fuente retenida**:

```python
return retained if len(retained) == 1 else used_source_ids
```

Con dos fuentes, el turno se rechazaba. GEN-13 tenía dos. La asimetría no tiene
defensa: **el hecho del servidor es idéntico en los dos casos** —sabe qué
retuvo y qué metió en el prompt—, y en uno lo usaba y en el otro exigía que el
modelo se lo repitiese.

**Cambio aplicado:** `return retained or used_source_ids`. Los turnos con
paciente en contexto siguen siendo estrictos (`policy.use_clinical_context`
sigue abortando la recuperación), y una declaración explícitamente vacía o
inválida del modelo se sigue respetando.

Lo que se publica son **fuentes consultadas** —hecho del servidor—, **nunca**
prueba de cada afirmación. Esa distinción es la que `source_attribution.py`
existe para proteger.

### Una queda abierta

`intent_mismatch_scope_boundary` (GEN-09, `meets_intent=0`). `[INFERIDO]` Es un
contrato de alcance, no de seguridad. Queda como **hipótesis viva**: no se toca
sin medir qué frontera concreta se cruzó.

## Lo que cuesta y lo que se gana

`[MEDIDO]` Lo perdido con el cambio, dicho explícitamente (§9.4 exige medirlo):

- **Se pierde** que el modelo elija cuál de las fuentes retenidas se publica.
  Era autodeclaración: puede nombrar una que no leyó y omitir la que sí usó.
- **Se gana** una generación entera en los turnos afectados. Fue el motivo de
  GEN-13 aquí, y de **2 de las 10** reparaciones de la batería del 10-ago.

`[MEDIDO]` Impacto del símbolo tocado: **LOW**, 5 símbolos, un solo llamador
(`_validate`). 1358 tests en verde, `ruff` limpio. Un test heredado fijaba la
conducta contraria y **se adaptó con justificación escrita**, no se borró.

## Latencia de esta corrida

`[MEDIDO]` 15 turnos lanzados, 12 respondidos (1×504, 2×502).

```
provider_calls : {1: 7, 2: 5}
p50 cliente    : 11,68 s      máx 22,56 s
línea base     : 13,50 s
```

`[MEDIDO]` Ningún turno llega a tres llamadas — la ruta de último recurso sigue
sin dispararse desde que el contrato mínimo está activo.

## Hipótesis vivas

1. `intent_mismatch_scope_boundary`: qué frontera cruzó GEN-09. Sin medir.
2. **La validez de primera pasada es estocástica.** `[MEDIDO]` GEN-04 salió
   `valid` en `puerta3h` y `indirect_treatment_recommendation` aquí, con el
   mismo prompt: `seed = −1`. Una puerta del 98 % sobre 15 turnos por ámbito
   **no distingue 98 % de 93 %**; hace falta declarar cuántas repeticiones
   sostienen la afirmación antes de darla por superada.
3. Reutilización de prefijo: sigue sin alcanzarse (ver más abajo).

## Puerta 2, medida como corresponde

`[MEDIDO]` El cociente que venía usando —`prompt_eval_duration` del turno 2+
frente al del turno 1— **es una métrica equivocada**: el turno 1 tiene el prompt
más corto de la conversación, así que el cociente sube por crecimiento del
historial aunque la caché funcione.

La medida honesta es **ms por token de prefill**, sobre `puerta3h`:

| Ámbito | ms/token típico | Turnos con acierto claro |
|---|---|---|
| general | 0,77-0,82 | **3 de 12** (0,151 · 0,160 · 0,267) |
| selected_hemogram | 0,77-0,78 | 0 de 13 |
| hemogram_history | 0,77-0,79 | 0 de 13 |

`[DERIVADO]` **35 de 38 turnos reevalúan el prompt entero** a la tasa plena de
prefill (~1 280 tok/s). La reutilización efectiva es del **7,9 %**, no del 13 %
estimado antes. La Puerta 2 sigue sin superarse y ahora se sabe con qué número.

## Criterio del GOAL que sí queda cumplido

`[MEDIDO]` *«Ningún usuario paga la recarga del runner: `num_ctx` alineado y
verificado por `size_vram`»* — **CUMPLE**. En los 38 turnos de `puerta3h`,
`size_vram_bytes` es **idéntico** (16 663 193 844) y `load_duration_ms` máximo
**558 ms**, con **cero** turnos por encima de 1 s. Un solo runner, nunca
recargado. Es la victoria de la Fase 1, confirmada.
