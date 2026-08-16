# Bloque F — los dos experimentos que deciden la arquitectura

**Fecha:** 2026-08-15 · **Árbol:** `4cca5683` (el desplegado) · **Rama:** `puertas-v3`
**Estado de las VMs:** las tres `TERMINATED`, verificado. Nada de este documento las ha encendido.

> El GOAL I-6 dice: *«Dos experimentos de 40 min deciden medio plan. Sin esos
> veredictos, no se toca nada de eso.»* Este documento cierra **F.2 a medias sin
> gastar un segundo de GPU**, y deja F.1 y la otra mitad de F.2 listos para
> disparar en la primera ventana.

Toda cifra va marcada `[MEDIDO]`, `[DERIVADO]` o `[INFERIDO]`.

---

## Estado — LOS TRES RESUELTOS

| Experimento | Estado | Coste real |
|---|---|---|
| **F.1** ¿propaga Ollama `enum`/`pattern` al GBNF? | **PROPAGA** | 2 min (×2, ver §0.1) |
| **F.2a** ¿cuánta caché se reutiliza multi-turno *en vivo*? | **10,6 %**, sin GPU | 0 |
| **F.2b** ¿es capaz el motor de reutilizar en régimen? | **SÍ — la culpa es nuestra** | 3 min |

**Medidos el 15-ago-2026 en la ventana 1**, sobre la release `99c12ff1`
verificada en el journal de la VM, con la GPU validada
(`hemovet_gpu_startup=ready`, `latency_ms=207502`) y sin tráfico ajeno.

---

## 0. F.1 · Ollama **SÍ** propaga `enum` y `pattern` — pero hay una condición

### 0.1 Un defecto de método propio, cazado en la primera corrida

`[MEDIDO]` La primera ejecución de F.1 devolvió **«NO PROPAGA»** con 30 de 30
violaciones. Era **falso**, y la pista estaba en el dato: las 33 salidas eran
**cadenas vacías**, no valores erróneos.

Qwen3.6 es un modelo de *thinking*. Sin `think: false` explícito, el razonamiento
**consume el presupuesto de `num_predict`** —la sonda pedía 24 tokens— y
`content` vuelve vacío. Mi veredicto automático contaba una salida vacía como una
violación del enum.

`[MEDIDO]` **Lo cazó la sub-prueba de dos pasadas**, que sí enviaba `think:false`
y obtuvo `15.20` —dentro del enum— con el mismo modelo y el mismo esquema. Sin
ese control, la sesión habría publicado «los Bloques H e I no son viables» y
habría desviado el plan entero hacia un cambio de motor.

**Corregido:** `think: false` por defecto, `num_predict` de 24 a 160, y una salida
vacía deja de contarse como violación —se cuenta aparte y el veredicto avisa—.

### 0.2 El resultado, con la sonda arreglada

`[MEDIDO]` **A/B pareado — las tres parejas concluyentes:**

| Sonda | Sin restricción | Con `enum` | ¿dentro? |
|---|---|---|:--:|
| `aritmetica` | `cuatro` | `{"valor": "siete"}` | **sí** |
| `capital` | `La capital de Francia es **París**.` | `{"valor": "Lisboa"}` | **sí** |
| `leucocitos` | `8.40 × 10³/µL` | `{"valor": "15.20"}` | **sí** |

**El modelo dice la verdad sin restricción y una de las opciones falsas con
ella.** No es complacencia ni casualidad: no tenía ninguna razón para elegir esos
tokens.

`[MEDIDO]` **Recuento:** 30/30 dentro del enum, 0 vacías.
**Cota superior 95 % de la tasa de violación: 9,50 %** — que es lo máximo
afirmable con n = 30. **No es «garantizado», es «no refutado a este n».**

`[MEDIDO]` **`pattern` anclado:** `{"valor": "HCT=45.0"}`, casa con
`^HCT=[0-9]{2}\.[0-9]$`. **También se propaga.**

`[MEDIDO]` **Coste de compilación:** enum de 3 → **1 400 ms**; enum de 300 →
**2 574 ms**. Unos 1,2 s más por 300 valores; con las cifras de un hemograma el
enum es de decenas, no de cientos.

`[MEDIDO]` **Fuzz — el servidor sobrevive a los cuatro esquemas torcidos:**

| Esquema | Resultado | ¿vivo? |
|---|---|:--:|
| `enum` vacío | salida parcial | **sí** |
| `pattern` inválido `[` | `http 400` | **sí** |
| `$ref` recursivo a `#` | `http 400` | **sí** |
| literal de 4 000 caracteres | salida parcial | **sí** |

Ningún *crash* del grammar stack. Los dos que devuelven `400` lo hacen limpiamente
—rechazo, no caída—, que es la propiedad que se quiere en un sistema clínico.

### 0.3 La condición, y es obligatoria

`[MEDIDO]` Sonda de desambiguación, `format` activo y `think` **nulo**:

| `num_predict` | `thinking` | `eval_count` | `done_reason` | `content` |
|--:|:--:|--:|---|---|
| 64 | sí | 64 | `length` | **vacío** |
| **400** | sí | **400** | `length` | **vacío** |

> **El modelo gasta el presupuesto ENTERO pensando y nunca emite contenido.** No
> es que el `format` se ignore: es que **sin `think: false` no hay salida en
> absoluto**, ni con 400 tokens.
>
> **Enviar `think: false` explícito es OBLIGATORIO en toda petición con
> `format`.** No es una optimización de latencia: es la diferencia entre obtener
> una respuesta y no obtener ninguna.

`[MEDIDO]` **Y NO hay doble llamada.** El residuo de reloj —segundos de reloj
menos `total_duration` de Ollama— es de **~3 ms (0,1 %)** en las tres
condiciones. La lógica de dos pasadas de `routes.go` **no se activa en este
despliegue**. El riesgo de §3.2 del prompt maestro queda **descartado por
medición**, y el aviso operativo se mantiene por la razón de arriba, que es otra.

### 0.4 Veredicto F.1

> **PROPAGA.** Los Bloques **H** e **I** son viables en el motor actual, **sin
> cambiar de motor**, con dos condiciones: `think: false` explícito en toda
> petición con `format`, y enumerar literales decimales en vez de usar rangos
> numéricos.

---

## 0.5 F.2b · El motor SÍ reutiliza — y la culpa era nuestra

`[MEDIDO]` Tres brazos, 15 pasos cada uno, mismo crecimiento por paso,
`num_ctx=65536`, `seed` fija, sin tráfico ajeno. Referencia de prefill frío:
**0,8716 ms/token**; umbral de acierto 0,4358.

| Brazo | p50 ms/token | aciertos | patrón |
|---|--:|--:|---|
| **APPEND** | **0,2695** | 11/14 | mejora monótona: 1,8734 → **0,1437** |
| **VENTANA** | **0,8969** | 2/14 | acierta en 5-6 y **desde el paso 7 reprocesa siempre** |
| **MEDIO** | 0,3622 | **14/14** | plano y estable desde el paso 2 |

`[MEDIDO]` El brazo VENTANA es quirúrgico. Los tokens se estabilizan en 1 387
—la ventana ya no crece— y a partir del paso 7, **justo cuando empieza a tirar el
bloque más antiguo por delante**, el coste salta a `0,897 ms/token` y **se queda
ahí**: exactamente el prefill frío, once pasos seguidos.

> ### Veredicto F.2b
>
> **LA CULPA ES NUESTRA Y ES ARREGLABLE.** El append puro **sí** reutiliza en
> régimen —llega a 6× más rápido que el frío— y la ventana deslizante lo mata.
> La hipótesis que la sesión anterior marcó como `[INFERIDO]` a partir del código
> queda **confirmada experimentalmente**.

`[MEDIDO]` **Y el `llama.cpp#24587` NO aplica a este despliegue.** El brazo
MEDIO —prefijo estable con un bloque intermedio que cambia cada paso, que es
literalmente el caso descrito en ese issue— **acierta 14 de 14**. La preocupación
de que un RAG dinámico rompiera la caché por sí solo queda **refutada por
medición**.

### 0.6 Lo que esto NO cambia del orden del plan

`[DERIVADO]` G.3 sigue yendo **detrás**. Con la Puerta C en 21,33 % de fallo,
arreglar `_select_history` mejora la **latencia** y no mueve **ni un caso** de
validez. Que ahora se sepa que rinde no lo asciende en el camino crítico: lo
convierte en una optimización con veredicto, disponible cuando la validez esté
resuelta.

---

## Estado anterior de F.2a (se conserva)

---

## F.2a · Reutilización multi-turno en vivo — RESUELTO, y sin GPU

La campaña `campana_r_2026-08-14` ya guardaba `prompt_eval_count` y
`prompt_eval_duration_ms` de cada turno. No hacía falta medir nada nuevo: hacía
falta mirar.

`[MEDIDO]` Sobre los **198 turnos** que traen métricas de prefill (de 225; los 27
terminales no llegan a generar):

```
ms/token de prefill, p50        0,8241        ← el frío medido es 0,8716
aciertos claros de caché        15/198 = 7,6 %
reutilización efectiva          10,6 %
```

| Ámbito | n | p50 ms/token | aciertos |
|---|--:|--:|--:|
| `general` | 67 | 0,8253 | **13/67 = 19,4 %** |
| `hemogram_history` | 64 | 0,8206 | 1/64 = 1,6 % |
| `selected_hemogram` | 67 | 0,8260 | 1/67 = 1,5 % |

> **Veredicto F.2a: en régimen multi-turno NO se reutiliza casi nada.** El
> prefill mediano es indistinguible del frío. Las dos cosas eran ciertas a la
> vez, tal y como avisaba `llama.cpp#24587`: el A/B/C del Bloque C midió **un
> turno aislado sin historial** —el mejor caso posible— y dio 14,5×; encadenado,
> el sistema real reutiliza el 10,6 %.

**Criterio de suficiencia:** este número no viene de una corrida suelta. Son 198
turnos de 5 corridas independientes, con el reparto por ámbito estable entre
ellas. La comparación con el frío usa la cifra del Bloque C, medida con `seed`
fija y cero tráfico ajeno.

### Y la hipótesis heredada queda refutada

La explicación que circulaba desde el Bloque C es que la culpa era de
`{case_facts_json}`, tercer bloque de `rag_es.txt`, cuyo contenido cambia turno a
turno. `[MEDIDO]` **No basta:**

```
general, n_case_facts por turno:   0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
```

`general` tiene ese bloque **constante en los quince turnos** y aun así reutiliza
solo el 19,4 %. Si `case_facts` fuera la causa, `general` reutilizaría casi
siempre.

`[MEDIDO]` El cruce lo confirma: la estabilidad de `case_facts` ayuda, pero muy
poco, y otro candidato correlaciona **al revés**, que es señal de confusión y no
de causa:

| Condición respecto al turno anterior | n | aciertos |
|---|--:|--:|
| `n_case_facts` **igual** | 113 | 12 = 10,6 % |
| `n_case_facts` **cambió** | 78 | 1 = 1,3 % |
| `n_fuentes` **igual** | 138 | 3 = 2,2 % |
| `n_fuentes` **cambió** | 53 | 10 = 18,9 % |

---

## F.2a-bis · Lo que la lectura del código añade, y nadie había nombrado

`[MEDIDO]` Orden **real** de los bloques en
`backend/app/modules/llm_chat/prompts/rag_es.txt`:

```
14  {clinical_context_json}    estable dentro de la conversación
15  {observations_block}
17  {case_facts_json}          volátil
20  {history_json}             crece
23  {memory_state_json}        volátil
26  {memory_summary_json}      volátil
29  {sources_json}             volátil (chunks del RAG)
31  {corpus_catalog_block}     estable
34  {response_policy_json}     volátil
35  {turn_instruction_block}   volátil
37  {question_json}            volátil, y está bien donde está
```

> **Corrección al prompt maestro §2.5.** Describe un orden que empieza por
> `{response_policy_json}` y sitúa `{case_facts_json}` sexto. El fichero dice
> otra cosa: `clinical_context` va **primero** y `response_policy` **penúltimo**.
> Cualquier razonamiento sobre «el primer bloque ya es volátil» partía de un
> orden que no existe.

`[MEDIDO]` **Tres rompe-prefijos ya estaban corregidos**, y la reutilización
sigue en el 10 %:

1. El rol *system* es estable: `_compose_system_prompt` recibe la política del
   turno y **la ignora** (`return base`), con un comentario que explica por qué.
2. La memoria va **detrás** del historial (commit `75a29a03`).
3. `_select_history` ya **no** reordena por solapamiento léxico con la pregunta.

`[MEDIDO]` **Queda un cuarto, y es determinista.** En `prompt_builder.py`:

```python
max_groups = max(1, limit // 2)           # limit = CHAT_HISTORY_LIMIT = 12
selected = [item for group in groups[-max_groups:] for item in group]
```

Es una **ventana deslizante de 6 turnos**. A partir del séptimo, cada turno
**tira el turno más antiguo por delante** de `{history_json}` — que es el 4.º
bloque de 11. El prefijo muere ahí, y con él todo lo que viene detrás: memoria,
resumen, fuentes, catálogo, política, instrucción y pregunta.

`[MEDIDO]` Y no es un caso raro: en el log de producción del 14-ago,
**126 de 377** construcciones de prompt están en el tope de 12 mensajes, es decir
con la ventana ya deslizando:

```
num_history_messages:  0→109   2→40   4→27   6→32   8→24   10→19   12→126
```

`[INFERIDO]` **Esto es una hipótesis, no un hecho.** Que la ventana rompa el
prefijo es cierto por construcción; que *sea la causa* del 10,6 % no está medido,
y el propio dato de `general` avisa de que puede haber más de un rompe-prefijos
a la vez. Eso es exactamente lo que F.2b va a decidir.

---

## F.2b · El experimento que queda, ya afilado

`validacion_llm/scripts/diagnostico_cache_multiturno.py`, ~15 min de GPU. Tres
brazos con el **mismo crecimiento por paso**, para que ms/token sea comparable:

| Brazo | Qué simula | Prefijo común con el paso anterior (verificado en seco) |
|---|---|---|
| **APPEND** | append puro — el mejor caso alcanzable | paso 2: 50,0 % · paso 7: 85,7 % · paso 15: **93,3 %** |
| **VENTANA** | lo que hace hoy el backend | paso 2: 50,0 % · paso 7: **0,2 %** · paso 15: 0,2 % |
| **MEDIO** | bloque intermedio variable (el `#24587`, y `sources_json`) | plano en **75,1 %** |

### Regla de decisión, escrita ANTES de medir

| Resultado | Decisión |
|---|---|
| **APPEND reutiliza** (p50 < 0,4358 ms/token) **y VENTANA no** | La culpa es nuestra y es arreglable. **G.3 rinde**: arreglar `_select_history` y mandar lo volátil a la cola, con su propia puerta |
| **APPEND tampoco reutiliza** | La arquitectura híbrida muerde en régimen. **Reordenar NO rinde en este motor**: no se invierte ahí. Se documenta y se pasa a G, que ataca la validez y no la latencia |
| **APPEND y VENTANA reutilizan los dos** | La ventana no era el rompe-prefijos. Volver a los datos; el brazo MEDIO señala si el sospechoso es `sources_json` |

---

## F.1 · ¿Propaga Ollama `enum` y `pattern`? — pendiente

`validacion_llm/scripts/experimento_gramatica.py`, ~10 min de GPU. **Decide si
los Bloques H e I son viables en el motor actual.**

### El diseño, y por qué no es «repetir 30 veces»

`[DERIVADO]` Repetir 30 veces sin ver una violación **no demuestra** que la
restricción se aplique: con 0 de 30, Clopper-Pearson solo acota la tasa de
violación en **≤ 9,50 %**. Para acotarla en ≤ 1 % harían falta **299**
repeticiones.

Lo que sí decide con n pequeño es un **A/B pareado**: misma pregunta, misma
semilla, **sin** `format` y **con** `format`, sobre preguntas cuyo prior es
abrumador y cuya respuesta correcta **no está en el enum**:

| Sonda | Pregunta | `enum` | Prior |
|---|---|---|---|
| `aritmetica` | «¿Cuánto es 2+2?» | `siete · nueve · once` | cuatro |
| `capital` | «¿Cuál es la capital de Francia?» | `Lisboa · Oslo · Varsovia` | París |
| `leucocitos` | el valor **está en el prompt** y se excluye del enum | `4.52 · 6.10 · 15.20` | 8.40 |

- Si el brazo libre dice «cuatro» y el restringido dice «siete», **la gramática
  está haciendo el trabajo**: una sola pareja así es concluyente, porque el
  modelo no tenía ninguna razón para elegir ese token.
- **Una sola violación refuta.** Es asimétrico a propósito: refutar es barato,
  confirmar es caro, y por eso se publican las dos cosas —el pareado y la cota
  superior— y nunca se declara «propaga» sin decir con qué n.

El script mide además el **coste de compilación** (enum de 3 frente a enum de
300), comprueba un **`pattern` anclado**, y **fuzzea** cuatro esquemas torcidos
—enum vacío, patrón inválido, `$ref` recursivo, literal de 4 000 caracteres—
porque hay issues abiertos de agosto-2026 sobre *crashes* del grammar stack
(`#26530`, `#26535`, `#26658`, `#26600`, `#26787`) y una gramática generada por
turno es exactamente ese vector.

### Regla de decisión, escrita ANTES de medir

| Resultado | Decisión |
|---|---|
| Ninguna salida fuera del enum, y ≥ 1 pareja concluyente | **H e I son viables sin cambiar de motor.** Se declara con su cota: «no refutado a n=30», nunca «garantizado» |
| **Alguna** salida fuera del enum | Ollama no propaga. H e I no son viables tal cual. Evaluar `llama-server` (`-DLLAMA_LLGUIDANCE=ON`) o vLLM/SGLang, **con su propio informe** de coste y riesgo |
| Ninguna pareja concluyente | Sin veredicto: el brazo libre ya producía valores del enum. Rehacer con sondas de prior más fuerte |

---

## Lo que esto cambia del plan, hoy

1. **F.2 ya no cuesta 30 min de GPU, cuesta 15.** Su mitad en vivo estaba en los
   datos desde el 14-ago.
2. **`general` es el ámbito peor en las dos dimensiones a la vez**: 72,0 % de
   validez por turno (frente a 86,7 % de `selected_hemogram`) y solo 19,4 % de
   aciertos de caché pese a tener la cabecera estable. Merece su propia mirada.
3. `[DERIVADO]` **El coste de la caché no es el bloqueo.** Con la Puerta C en
   21,3 % de fallo, arreglar la reutilización mejoraría la latencia y no movería
   ni un caso de validez. G.3 es optimización; G.1, G.2 e I son el bloqueo. Si
   F.2b dijera que la ventana es la culpable, **el arreglo sigue yendo detrás**.

## Hipótesis vivas

1. **Si la ventana deslizante es la causa del 10,6 %.** La decide F.2b.
2. **Por qué `n_fuentes` correlaciona al revés** con el acierto de caché. Es
   señal de confusión con otra variable, probablemente el ámbito.
3. **Si `general` reutiliza más porque su prompt es más corto**, y no porque su
   cabecera sea estable. No separado.
4. **La desalineación `num_ctx`** app 16 384 / servidor 65 536 sigue viva, y el
   diagnóstico del 14-ago la señaló como causa de recargas del runner. Sin medir.
