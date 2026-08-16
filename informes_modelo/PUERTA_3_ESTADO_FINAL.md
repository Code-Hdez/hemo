# Puerta 3 — estado final del 13-ago-2026

Todas las cifras son `[MEDIDO]` salvo marca en contra.

---

## Las cuatro corridas comparables

| | 10-ago (base) | 3i · sobre ON | **3j · contrato mínimo** | 3k · +prompt |
|---|---|---|---|---|
| Respondidos | 45/45 | **45/45** | 38/45 | 40/45 |
| `provider_calls` | {1:35, 2:10} | {1:34, **3:11**} | **{1:34, 2:4}** | {1:33, 2:7} |
| Primera pasada global | 77,8 % | 75,56 % | **89,47 %** | 82,50 % |
| · general | **0 %** | **100 %** | 78,6 % | 76,9 % |
| · seleccionado | 20 % | 73,3 % | **100 %** | 92,9 % |
| · historial | 46,7 % | 53,3 % | 91,7 % | 76,9 % |
| p50 | 16,3 s | 17,12 s | **10,02 s** | 11,44 s |
| p95 | — | 48,63 s | **17,14 s** | 19,58 s |

## Lo que se consiguió

**El contrato mínimo gana en todos los ejes.** Frente al sobre activo medido el
mismo día, con el mismo modelo y el mismo hardware: **+13,9 puntos** de validez
en primera pasada, **la mitad de latencia mediana**, p95 de 48,63 s a 17,14 s, y
**ningún turno llega a tres llamadas** — la ruta de último recurso, que salvaba
9 de 45 turnos en la línea base, dejó de dispararse.

**Los dos criterios de latencia del GOAL se cumplen:** mediana caliente ≤ 15 s
(10,02 s) y p95 ≤ 25 s (17,14 s).

**`num_ctx` alineado, verificado por `size_vram`:** en 38 turnos el valor es
idéntico (16 663 193 844) y `load_duration_ms` máximo 558 ms, cero por encima de
1 s. Ningún usuario paga la recarga del runner. Criterio cumplido.

**El ámbito `general` pasó de 0/15 a 15/15** con el sobre activo, gracias al
arreglo de atribución de fuentes. Era el ámbito peor de la línea base.

## Lo que NO se consiguió, y por qué

**La Puerta 3 no se supera: 89,47 % frente al 98 % exigido.** No se pasa a la
Fase 4, así que `provider_calls == 1` sigue sin cumplirse en el 100 %.

Los cuatro rechazos que sobreviven en 3j:

| Motivo | n | Naturaleza |
|---|---|---|
| `indirect_treatment_recommendation` | 3 | **Captura clínica legítima** |
| `unsupported_numeric_claim:plt` | 1 | **Captura clínica legítima** |

> **Los cuatro son el validador haciendo su trabajo.** Bajar el umbral para
> alcanzar el 98 % sería «relajar una validación para pasar una puerta», señal
> de desvío declarada. **No se hizo y no debe hacerse.**

**Tres intentos de mover esto por prompt, tres fracasos**, todos declarados:

1. «di las cifras» → `seleccionado` +20 pts, `general` −47 pts.
2. La misma instrucción condicionada al ámbito → `general` no se recuperó.
3. Prohibición concreta de indicar qué hacer → el objetivo
   (`indirect_treatment_recommendation` = 3) **no se movió ni un caso**, y el
   global cayó a 82,50 %. Revertido.

`[INFERIDO]` La palanca, si existe, no es una línea más de prompt: es `TurnGuard`
decidiendo **antes** de generar, que es donde el propio plan la coloca.

## Puerta 2 — medida bien por primera vez

El cociente que usaba el arnés es una **métrica equivocada**: el turno 1 tiene el
prompt más corto de la conversación, así que el cociente sube por crecimiento
del historial aunque la caché funcione.

La medida honesta es **ms por token de prefill**. Sobre `puerta3h`:

| Ámbito | ms/token típico | Aciertos claros |
|---|---|---|
| general | 0,77-0,82 | **3 de 12** (0,151 · 0,160 · 0,267) |
| selected_hemogram | 0,77-0,78 | 0 de 13 |
| hemogram_history | 0,77-0,79 | 0 de 13 |

**35 de 38 turnos reevalúan el prompt entero.** Reutilización efectiva **7,9 %**,
no el 13 % que se venía citando. Se aplicó el defecto de orden encontrado —la
memoria iba **antes** del historial, y §4.4 la manda a la cola volátil— pero la
puerta sigue sin superarse.

## Dos defectos de método, propios, documentados

1. **El commit vacío no despliega** (`TRAMPA_COMMIT_VACIO.md`). Tres «éxitos»
   verdes que saltaron build, deploy y smoke. Medí una batería entera creyendo
   que ejecutaba instrumentación que nunca llegó a la VM.
2. **Los apagados de la GPU los provocaba yo.** No eran desalojos spot: las
   operaciones dicen `guestTerminate`. El canario `/api/chat` del reconciliador
   tiene `--max-time 60` y Ollama corre con `NUM_PARALLEL=1`; mis sondas de
   `/api/v1/chat/health` durante el arranque le ocupaban la única ranura, el
   canario recibía 0 bytes, el servicio fallaba y su `OnFailure` ejecutaba
   `poweroff`. Sin sondear, el arranque valida: `/api/generate` ≈204 s, canario
   ≈1,4 s, `release=applied state=validated`.

Y un error que conviene no repetir: **empujé una vez con tres tests en rojo**
porque encadené mal el commit al resultado de la suite. Corregido en el commit
siguiente.

## Estado de producción

`CHAT_STRUCTURED_OUTPUT_ENABLED=0` — **contrato mínimo activo, con la red de
reparación intacta**.

Es una decisión con su razón: I-7 dice que la medición propia gana, y la
medición del mismo día dice que el contrato mínimo es mejor que el sobre en
validez (+13,9 pts), en llamadas (ningún turno llega a tres) y en latencia (la
mitad), **sin un solo turno que acabara sin respuesta** en ninguna de las dos
configuraciones. La Puerta 3 gobierna si se **quita la red** (Fase 4), y la red
sigue puesta.

Para volver al sobre basta poner el secreto a `1` y desplegar. **El secreto se
captura en el job «Deployment configuration», temprano**, así que hay que
cambiarlo *antes* de empujar, y con un commit nuevo: el guardián de
inmutabilidad rechaza redesplegar el mismo SHA con otro entorno.

## Hipótesis vivas

1. **La validez de primera pasada es estocástica** (`seed = −1`). GEN-04 salió
   `valid` en una corrida e `indirect_treatment_recommendation` en la siguiente
   con el mismo prompt. Una puerta del 98 % sobre 12-15 turnos por ámbito **no
   distingue 98 % de 93 %**. Antes de darla por superada hay que declarar
   cuántas repeticiones la sostienen.
2. Qué frontera cruza `intent_mismatch_scope_boundary` (visto una vez).
3. Por qué la reutilización de prefijo sigue en el 7,9 % tras reordenar.
4. Los 502/504 dispersos (5-7 por batería) siguen sin explicación; contaminan
   toda comparación de denominadores entre corridas.

## Lo que queda del plan

- **Fase 4** (una sola generación): bloqueada por la Puerta 3. Correcto.
- **Fase 5** (error terminal tipado): no empezada.
- **Fase 6** (ablación A/B/C y revisión veterinaria ciega): no empezada.
