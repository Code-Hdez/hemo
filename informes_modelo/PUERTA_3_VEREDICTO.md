# Puerta 3 — NO PASA. El contrato mínimo no basta por sí solo

**Fecha:** 2026-08-13 · **Commit:** `37e9455e` · **Datos:** `validacion_llm/resultados/puerta3b_2026-08-13/puerta_3b.jsonl`
**Corrida:** parcial, **29 de 45 turnos** — se colgó en SEL-15 y se detuvo.

## Veredicto

`[MEDIDO]` Validez de primera pasada, con el sobre **realmente apagado**:

| Ámbito | Validez | Umbral |
|---|---|---|
| General | 14/15 = **93,33 %** | 98 % |
| Seleccionado | 10/14 = **71,43 %** | 98 % |
| **Parcial global** | 24/29 = **82,76 %** | 98 % |

**NO PASA. Por tanto NO se pasa a la Fase 4**, como manda el plan.

## El contrato mínimo sí se activó, y sí hizo algo

`[MEDIDO]` A diferencia del primer intento —donde el cambio no llegó a
aplicarse— aquí sí:

- `provider_calls` **{1: 24, 3: 5}**: 82,8 % de turnos con **una sola llamada**,
  frente al 80 % de la Puerta 0. Mejora, pero marginal.
- Rutas: `main 29 · repair 5 · last_resort 5`.

`[MEDIDO]` **Y aquí está la sorpresa que refuta una hipótesis del plan:** los
tokens de salida **no bajaron**. p50 **342** frente a **323** de la Puerta 0
sobre los mismos identificadores.

> El plan estimaba que quitar el sobre ahorraría el 67,7 % de los tokens de
> salida y con ellos 5,28 s de decodificación. **Medido: no ahorra nada.** El
> modelo, liberado del sobre, escribe más prosa en vez de escribir menos JSON.
> La latencia p50 tampoco mejoró: 16,37 s frente a 15,43 s.

`[INFERIDO]` La estimación del 67,7 % venía de dividir caracteres de prosa entre
tokens totales asumiendo 3,6 car/token. Esa razón sobreestimó la prosa o
subestimó el sobre. La conclusión operativa no cambia: **el contrato mínimo no
es una palanca de latencia**.

## Por qué falla la validez

`[MEDIDO]` Sonda sobre SEL-01 con el contrato activo: el turno gastó 3 llamadas
y acabó respondiendo *«En este turno no puedo confirmar los datos específicos de
tu mascota»* — es decir, el último recurso, que genera **sin datos del paciente
en alcance**. La respuesta es segura pero **inútil**: la pregunta era qué valores
están fuera de rango.

`[INFERIDO]` Al quitar el sobre se quitó también la estructura que forzaba al
modelo a declarar los hechos que usaba. Los derivados del servidor
(`fact_attribution`, `source_attribution`) calculan bien la atribución **a
posteriori**, pero no sustituyen a lo que el sobre hacía **durante** la
generación: obligar a mirar los hechos. Esa es la hipótesis a contrastar antes
de volver a intentarlo.

## Hipótesis vivas

1. **El prompt necesita reescribirse para el contrato mínimo.** Se quitó el
   sobre pero no se reescribió la guía que lo acompañaba. La Fase 3 §2 lo pedía
   («eliminar del prompt toda la guía para construir el sobre») y **no se hizo**.
2. **La Fase 2 no funcionó**: la reutilización de prefijo sigue en 70-117 %,
   lejos del 25 %. Qué la invalida sigue sin identificarse.
3. **El ahorro de tokens del contrato mínimo es cero**, contra lo previsto.
4. La corrida se colgó en SEL-15 y no se sabe por qué.

## Estado del invariante I-2

`provider_calls == 1` **no se cumple**: 5 de 29 turnos usan tres llamadas.

## Qué hacer a continuación

**Revertir a `CHAT_STRUCTURED_OUTPUT_ENABLED=1`** hasta reescribir el prompt sin
la guía del sobre. Dejarlo apagado deja producción con un 17 % de turnos que
responden sin datos del paciente, y eso es peor que la latencia que se quería
arreglar.
