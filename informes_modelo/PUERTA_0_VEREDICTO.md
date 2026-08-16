# Puerta 0 — veredicto sobre medición en vivo

**Corrida:** 45 turnos, 13-ago-2026, contra `https://hemovet.app` (camino del navegador)
**Código desplegado:** `a3aeb9b5` · **Datos:** `validacion_llm/resultados/puerta0_2026-08-13/puerta_0.jsonl`
**GPU:** encendida solo para medir; apagada y verificada `TERMINATED` al terminar.

Toda cifra `[MEDIDO]` sale de ese fichero. `[DERIVADO]` es aritmética sobre ella.
`[INFERIDO]` es lectura razonada sin medir.

---

## 0. La puerta pasa

`[MEDIDO]` 45/45 turnos con respuesta · `validation_status: passed` en los 45 ·
cero fallos finales. La instrumentación no cambió el comportamiento: la latencia
mediana es **17,37 s** frente a **17,60 s** de la línea base del 10-ago, y por
ámbito la diferencia no llega al segundo. Eso era el requisito de la Fase 0.

---

## 1. Las tres preguntas de la puerta

### P1 · ¿Cuántas llamadas hace realmente cada turno?

`[MEDIDO]`

| provider_calls | turnos |
|---|---|
| 1 | **36** |
| 3 | **9** |

Rutas efectivamente usadas: `main` 45 · `repair` 9 · `last_resort` 9 ·
`steer` **0** · `tool` **0**.

**Tres hallazgos, y los tres corrigen a los informes:**

1. **El techo real es 3, no 2 ni 4.** Los informes hablaban de «hasta cuatro
   respuestas». Medido: como mucho tres. `_steered_candidate` **no se activó ni
   una sola vez** en 45 turnos, y la ruta de herramientas tampoco
   (`CHAT_TOOLS_ENABLED=0`).

2. **La reparación tiene una tasa de éxito del 0 %.** Las **9** veces que se
   disparó, las **9** acabaron necesitando `last_resort`. No hay ni un caso en
   que reparar bastara. La secuencia observada es siempre exactamente
   `main → repair → last_resort`.

3. **Quien salva el turno es el último recurso, no la reparación.** Esto
   reordena la culpa: el bloque de reparación de `send_chat_message.py:1723-1830`
   no está rescatando nada; está añadiendo una llamada entera antes de que otra
   cosa rescate el turno.

`[DERIVADO]` Coste: los turnos de 1 llamada van a **16,35 s** de mediana; los de
3, a **47,80 s**. **×2,92.**

`[MEDIDO]` Coincidencia con la línea base: 6 de 10 identificadores
(`SEL-05, SEL-14, HIS-06, HIS-12, HIS-13, HIS-15`). Aparecen tres nuevos
(`GEN-15, HIS-05, HIS-09`) y desaparecen cuatro (`SEL-01, HIS-03, HIS-10,
HIS-14`). La población de turnos frágiles es parecida pero no idéntica.

> **Consecuencia para la Fase 4, y es nueva:** `CHAT_MAX_GENERATION_ATTEMPTS=1`
> **no** basta para conseguir una llamada por turno. Esa variable solo gobierna
> la reparación; `_last_resort_candidate` es una ruta aparte y seguiría
> disparándose. Un turno pasaría de `main → repair → last_resort` (3) a
> `main → last_resort` (2). Sigue violando el invariante.

### P2 · ¿Las reparaciones terminan por EOS o por `length`?

`[MEDIDO]` `done_reason` = `stop` en **los 45 turnos**. Ninguno por `length`.

> **La hipótesis principal de los informes queda refutada.** Sostenían que si la
> reparación usa `num_predict=1024` frente a los 1 280 de la principal, y el
> fallo original fue truncamiento, reparar truncaría antes. **No hay
> truncamiento: nada topa en el límite.** El problema no es de presupuesto de
> tokens.

**Limitación que hay que declarar, y es un defecto de mi instrumentación:** el
`done_reason` que viaja al contrato público es el del **candidato entregado**, no
el de cada llamada por separado. Que la llamada final termine por `stop` no
demuestra que la reparación intermedia también lo hiciera. Para afirmarlo haría
falta segregar `done_reason` por ruta, y eso hoy solo consta en los logs del
servidor. **Queda como hipótesis viva, no como hecho.**

### P3 · ¿Cuál es el `prompt_eval_duration` real y la reutilización de caché?

`[MEDIDO]`

| Ámbito | Turno 1 | p50 turnos 2+ | Ratio |
|---|---|---|---|
| general | 233,5 ms (3 127 tok) | 3 194,9 ms (3 828 tok) | **1 368 %** |
| selected_hemogram | 4 136,4 ms (5 053 tok) | 4 359,2 ms (5 284 tok) | **105 %** |
| hemogram_history | 6 178,4 ms (7 629 tok) | 4 444,7 ms (5 406 tok) | **72 %** |

La Puerta 2 exige que los turnos 2+ bajen **por debajo del 25 %** del turno 1.
Hoy están entre el 72 % y el 1 368 %.

`[DERIVADO]` El turno 1 de `general` procesó 3 127 tokens en 233 ms — unos
13 400 tok/s, imposible como prefill real. **Fue un acierto de caché casi total**,
heredado del turno de prueba anterior. Los turnos siguientes costaron 3 195 ms
para 3 828 tokens, es decir **1 198 tok/s: prefill completo desde cero**.

> **El prefijo no se reutiliza entre turnos de una misma conversación. Cada turno
> reprocesa el prompt entero.** El diagnóstico de §3.5 del plan queda confirmado
> con medición, y el caso de `general` lo demuestra por contraste: cuando el
> prefijo sí coincide, el prefill cuesta 14 veces menos.

---

## 2. Lo que la medición cambia del plan

### 2.1 `num_predict=512` truncaría una de cada seis respuestas

`[MEDIDO]` Tokens de salida reales:

| | p50 | p90 | p95 | máx |
|---|---|---|---|---|
| tokens | **321** | 562 | 649 | **900** |

El plan estimaba «115-200 tokens» a partir de las 71 palabras de mediana. **La
medición dice 321 tokens de mediana**, casi el doble, y un máximo de 900.

`[DERIVADO]` A los 36,7 tok/s medidos:

| `num_predict` | techo de decode | cubre |
|---|---|---|
| 384 | 10,5 s | 57,8 % |
| **512** | 14,0 s | **84,4 %** |
| 640 | 17,4 s | 93,3 % |
| **768** | 20,9 s | **97,8 %** |
| 1 280 (actual) | 34,9 s | 100 % |

> **Recomendación corregida para la Fase 1: 768, no 512.** Con 512 se truncaría
> el 15,6 % de las respuestas medidas — cambiar un problema de latencia por uno
> de contenido incompleto. Con 768 el techo de decode baja de 34,9 s a 20,9 s y
> se conserva el 97,8 %. Y el objetivo de 10-15 s **no** depende del techo sino
> de la salida real: 321 tokens a 36,7 tok/s son **8,7 s**.

### 2.2 El decode real es 36,7 tok/s, no 40,85

`[MEDIDO]` decode p50 **36,70 tok/s** · TPOT p50 **27,25 ms/token**, frente a los
40,849 tok/s y 24,480 ms del canario de la campaña anterior.

`[DERIVADO]` La diferencia es de **+2,77 ms/token, un 11,3 %**, y es **ocho veces
mayor** que el coste de gramática medido en la ablación (+0,332 ms/token). El
canario corría sin gramática, con `num_predict=128` y prompts cortos; esto es la
ruta real. **Hipótesis viva:** la diferencia no está explicada y no debe
atribuirse a la gramática sin medirla.

### 2.3 El prompt pesa el doble de lo que decían los informes

`[MEDIDO]` Tokens de prompt, mediana por ámbito: general **3 731**, seleccionado
**5 261**, historial **5 591** (máximo 9 029). Los informes hablaban de ~1 700
tokens de esquema sobre un prompt total no medido.

### 2.4 El tiempo se va dentro del proveedor

`[MEDIDO]` Fuera del proveedor: **0,44 s** de mediana. `queue_wait` mediano **0 ms**.
Residuo dentro del proveedor: **591 ms** de mediana.

> No hay un cuello de botella oculto en la red, la cola o el backend. **El tiempo
> es prefill más decode**, que es exactamente donde las Fases 1 a 3 actúan.

---

## 3. Hipótesis vivas

1. **¿Termina la reparación por `length`?** No se puede afirmar ni negar: el
   `done_reason` público es el del candidato entregado. Requiere segregarlo por
   ruta.
2. **¿Por qué el decode real es un 11,3 % más lento que el canario?** No es la
   gramática, cuyo coste medido es ocho veces menor. Sin explicar.
3. **¿Por qué `_steered_candidate` no se activa nunca?** Cero de 45. O el guard
   no ofrece `STEER` en este corpus, o la ruta está efectivamente muerta. Si lo
   está, eliminarla en la Fase 4 no pierde nada — pero hay que comprobarlo antes
   de decirlo.
4. **La reutilización de caché del ~13 %** que citan los informes no se ha
   recalculado; lo medido aquí es el ratio turno-1/turnos-2+, que es otra cosa y
   sale peor.
