# Puerta 3 — NO SUPERADA. Tres mediciones, la misma conclusión

**Fecha:** 2026-08-13 · **Commit:** `eab9f89d` · **Datos:** `validacion_llm/resultados/puerta3e_2026-08-13/puerta_3e.jsonl`
**Corrida:** completa, 45/45 turnos, con el contrato mínimo activo y el prompt corregido.

## Veredicto

`[MEDIDO]` Validez de primera pasada:

| Ámbito | Validez | Umbral |
|---|---|---|
| General | 14/15 = **93,33 %** | 98 % |
| Seleccionado | 11/15 = **73,33 %** | 98 % |
| Historial | 9/15 = **60,00 %** | 98 % |
| **GLOBAL** | 34/45 = **75,56 %** | 98 % |

**NO SUPERADA. No se pasa a la Fase 4.**

`[MEDIDO]` `provider_calls`: **{1: 34, 3: 11}**. Rutas: `main 45 · repair 11 · last_resort 11`.

## El arreglo del prompt no funcionó

Se añadió a `rag_es.txt` una instrucción explícita de citar nombre, valor, unidad,
rango y fecha cuando la pregunta se refiera a datos presentes en el contexto
autorizado. **Efecto medido: ninguno.**

| | Antes del arreglo | Después |
|---|---|---|
| Validez global | 82,76 % (parcial 29) | **75,56 %** (45) |
| Turnos con >1 llamada | 5/29 = 17,2 % | **11/45 = 24,4 %** |
| Tokens de salida p50 | 342 | **328** |
| Latencia p50 | 16,37 s | **17,85 s** |

> **I-9: si un cambio no da el efecto esperado, se dice y se revierte.** El arreglo
> del prompt se dice: **no dio el efecto esperado.** Las dos corridas no son
> estrictamente comparables (29 turnos parciales frente a 45 completos), pero
> ninguna se acerca al 98 %, y la hipótesis de que faltaba pedir las cifras queda
> **refutada**.

## Los once turnos que fallan

`GEN-11 · SEL-01, 05, 11, 14 · HIS-04, 05, 06, 08, 12, 13`

`[MEDIDO]` Los tres ámbitos empeoran conforme aumenta el contexto clínico:
General 93 % → Seleccionado 73 % → Historial 60 %. **El fallo escala con la
cantidad de datos del paciente que hay que citar**, no con la longitud de la
respuesta.

## Comparación con la línea base

`[MEDIDO]` La Puerta 0, **con el sobre puesto**, dio 77,8 % de validez de primera
pasada. Con el contrato mínimo: **75,56 %**. Dentro del ruido de dos corridas.

> **Conclusión que hay que decir sin adornos: quitar el sobre no mejora la validez
> de primera pasada, no reduce los tokens de salida y no mejora la latencia.** Las
> tres cosas que el plan predecía no se cumplen en la medición.

## Hipótesis vivas

1. **El validador es más estricto de lo que el modelo puede satisfacer en prosa
   libre.** `_acknowledges_abnormal_fact` y `_mentioned_absent_parameter` operan
   igual con sobre y sin él; lo que cambia es que el sobre forzaba un formato que
   los satisfacía por construcción. Habría que medir **qué código de validación
   falla** en cada uno de los 11 turnos — el arnés no lo captura hoy.
2. **La Fase 2 sigue sin funcionar**: prefijo en 71-329 %, lejos del 25 %. En
   `selected_hemogram` **empeoró** respecto a la medición anterior.
3. **El objetivo de 10-15 s no depende del contrato.** p50 17,85 s con contrato
   mínimo frente a 17,37 s con sobre.

## Qué hacer

**No pasar a la Fase 4.** Antes hay que instrumentar `validation_reason` por
turno en el arnés y saber exactamente qué comprobación rechaza cada uno de los 11
turnos. Sin eso, cualquier cambio en el prompt es a ciegas — y ya se ha
comprobado que a ciegas no funciona.
