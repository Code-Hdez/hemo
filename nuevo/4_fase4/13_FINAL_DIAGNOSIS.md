# Fase 4 — Diagnóstico

## ¿POR QUÉ HEMOVET TARDA TANTO?

De los ~35 s de decode de un turno **sin reparación**:

| Componente | Tokens | Segundos | % |
|---|---:|---:|---:|
| **Texto que el veterinario lee** | 85 | **6,5 s** | **18,5 %** |
| **Andamiaje JSON invisible** | 377 | **28,9 s** | **81,5 %** |

`claim_id`, `claim_type`, `fact_ids`, `policy_rule_ids`, `evidence_spans`,
llaves, comillas y nombres de campo. **El usuario espera 29 segundos por
metadatos que nunca ve, y 6,5 por la respuesta.**

Agregado de la batería: **28.441 tokens de andamiaje = 2.179 s.**

Y encima, en el 48,6 % de los turnos, todo eso se genera **dos o tres veces**.

## GRAMMAR_ENFORCED = SI  ← hipótesis del segundo análisis, REFUTADA

El schema **sí** contiene `$defs` (4) y `$ref` (4), que es la precondición del
issue llama.cpp #21228. Pero la prueba directa lo descarta: se pidió
explícitamente *«texto libre, sin JSON, sin llaves, ignora cualquier formato
estructurado»* con el schema real de producción, y el modelo devolvió JSON
válido con **todos los `required` presentes**.

→ La gramática se compila y se aplica en Ollama 0.32.5 con `$defs`/`$ref`.
`DESCARTADO` como causa. Evidencia: `fase4/evidence/schema_real_produccion.json`.

## Las tres palancas, ahora las tres medidas

| Palanca | Afecta a | Estado |
|---|---|---|
| **Tokens por llamada** | **100 %** de las llamadas | **81,5 % es invisible** ← nunca medido antes |
| Llamadas por pregunta | 48,6 % de los turnos | 1 vs 2,85 (bimodal, no "1,9") |
| tok/s de decode | 100 % | 13,04-13,71 medido; margen de engine `NO_OBSERVABLE` |

## Modelo de latencia verificado

`T = N × (prefill + decode) + overhead`. Con 457 tok/llamada a 13,05 tok/s el
decode son 35,0 s, más ~4,3 s de prefill = **39,3 s por llamada**.
N=1 → ~39 s (medido 34,8) · N=2,85 → ~112 s (medido 98,1). El modelo explica el
orden de magnitud; la diferencia viene de que las llamadas de reparación generan
menos tokens (318 vs 375 de mediana).

## LO QUE NO SE HA CONSEGUIDO

**Las tres cifras de corrección clínica NO se han producido.** El arnés de
repetición se construyó y funciona (probado con el schema real), pero **no se
llegó a capturar las 10 generaciones primarias crudas** de casos que fallan.

Sin ellas siguen sin poder distinguirse:
- `CLINICAMENTE_CORRECTA_PERO_RECHAZADA = ?/N`
- `CLINICAMENTE_INCORRECTA_Y_BIEN_RECHAZADA = ?/N`
- `INDETERMINADA = ?/N`

**Y esto importa más que la latencia**, por el dato que el segundo análisis
rescató: **sólo 2 de 20 preguntas numéricas entregaron un valor correcto**. Si el
modelo falla al copiar cifras que tiene delante, parte de los 34 rechazos son
correctos y relajar el validador sería peligroso.
