# HemoVet — Los siguientes pasos

**9 de agosto de 2026** · `main` = `2cf21876` · sucede a `PROMPT_EJECUCION_V2` y a `INFORME_ESTADO`

---

# 0 · Lo que cambia respecto al plan que ya tienes

El plan anterior decía: rama combinada → brazo de 84 minutos → veredicto. **Esa secuencia sigue siendo correcta, pero tiene tres agujeros que no se habían visto**, y los tres se tapan antes de correr nada, no después.

| # | el agujero | por qué importa ahora |
|---|---|---|
| **1** | **El estadístico está mal elegido.** Fisher supone dos muestras independientes; el diseño es **pareado** — los mismos 70 casos, antes y después | El escenario que se declaró «no concluyente» (11/70) **sí decide** con el test correcto. Fisher está tirando poder a la basura |
| **2** | **El suelo de ruido nunca se ha medido.** Temperatura 0,3, K=1, una sola corrida | Sin él, un resultado nulo o ambiguo **no se puede interpretar**: no se sabe si la mitigación no sirve o si el instrumento no distingue |
| **3** | **Apagar el poller dejó un confusor nuevo** | Si el runner deriva a mitad de la batería, ya no hay nada que lo corrija, y **los 70 turnos salen contaminados sin que nadie se entere** |

Ninguno de los tres se arregla con más código. Los tres se arreglan con **una decisión de diseño experimental tomada antes de mirar los datos**, que es exactamente el momento en el que todavía es legítimo tomarla.

---

# PASO 0 · Las tres medidas de la adenda — 40 min

Ya están escritas en `ADENDA_BLOQUE0_HEMOVET.md`. Se recuerdan aquí porque **van antes de crear la rama combinada**, y el motivo es concreto: T-1 y T-3 pueden cambiar el esquema que la combinada va a usar.

| | qué mide | por qué importa | coste |
|---|---|---|---|
| **T-1** | el mismo prompt con `format` y sin `format` | el decode va a 13,05 tok/s contra un techo de 17,7 (73,7 %). Ese 26 % se atribuyó a ancho de banda. **Las guías de salida estructurada reportan que la gramática frena entre un 30 % y un 80 %.** Si cuesta un 15 %, vale más que M-4 | 10 min |
| **T-2** | si el cliente fija `think` y si la respuesta trae razonamiento | Qwen3.6 razona; el espacio en blanco en `chat-template-kwargs` puede activarlo sin querer. Parte de los 204 tokens del «suelo del sobre» podrían ser razonamiento que nadie lee | 10 min |
| **T-3** | repetición en los campos de texto libre + `maxLength` | fallo abierto en Ollama: la gramática **no puede** suprimir la repetición en cascada, porque cualquier repetición de palabras es una cadena JSON válida. Podría explicar la cola de 212,3 s | 20 min |

**Regla:** si una sale negativa, se anota como falsificada **con su número** y se sigue. No abre investigación. La congelación de alcance sigue vigente.

---

# PASO 1 · La rama combinada — y la verificación que falta

`5517c431` (M-1+M-2) + `019e2149` (M-4) + `048b3971` (M-5), desde `21f18fd8`.

## El riesgo que nadie ha nombrado

El plan dice «verificar que mergean limpio y que la suite pasa». **Eso es necesario y no es suficiente** — y es la misma forma del patrón que atraviesa el proyecto entero.

> **Las tres mitigaciones tocan el mismo objeto: el sobre.**
>
> - **M-1 y M-2** *rellenan* campos del sobre (`policy_rule_ids`, `fact_id`).
> - **M-4** *renombra* campos del sobre con alias cortos (`dx`, `med`, `dose`, `freq`, `dur`, `pers`, `urgent`) y `populate_by_name=True`.
> - **M-5** cambia el *presupuesto* con el que se regenera el sobre.
>
> Un merge textualmente limpio puede quedar **semánticamente roto**: M-1 materializa un dato en un campo cuyo alias M-4 acaba de cambiar. `populate_by_name=True` debería salvarlo — **pero eso es una hipótesis, no una comprobación.** Y los tests unitarios de cada rama pasan por separado precisamente porque cada uno se escribió contra su propia versión del sobre.

## Las tres verificaciones, en orden de coste

1. **`ruff` + las cinco suites enteras con `-p no:asyncio`.** No sólo `tests/llm_chat`. Necesario.
2. **El esquema compila.** Volcar `GeneratedResponseEnvelope.model_json_schema()` de la rama combinada y mandarlo como `format` en **una llamada real** contra el Ollama de producción. Si la gramática no compila, el error **no aparece en ningún test unitario** — aparece como HTTP 400 en producción, a mitad de la batería. Coste: 2 minutos.
3. **Un campo materializado sobrevive al renombrado.** Un caso que dispare M-1 (regla de política única), con el sobre de la combinada, y comprobar que `policy_rule_ids` **llega poblado al validador**. Ésta es la que ningún test cubre hoy, porque ningún test ha visto las dos mitigaciones a la vez.

**Si (2) o (3) fallan, es un hallazgo de primer orden**, no un contratiempo: significaría que la cartera nunca podría haberse desplegado junta y que los cinco brazos del plan viejo habrían medido cosas incompatibles.

---

# PASO 2 · El estadístico correcto — y cómo cambiarlo sin romper el sello

## El problema

El criterio sellado usa **Fisher exacto de una cola**. Fisher compara dos muestras **independientes**. Pero el diseño de HemoVet no es ése:

```
brazo base        los 70 casos, código 21f18fd8
brazo combinado   LOS MISMOS 70 CASOS, código combinado
```

**Cada caso es su propio control.** Eso es un diseño pareado, y el test correcto es **McNemar exacto** sobre los pares discordantes: los casos que fallaban y pasan (**b**, rescatados) contra los que pasaban y fallan (**c**, rotos).

## Lo que cambia, en números

| escenario | b rescatados | c rotos | fallos finales | **Fisher** | **McNemar exacto** |
|---|---:|---:|---:|---:|---:|
| lo predicho | 13 | 0 | 4/70 | 0,0018 | **0,00012** |
| bueno con daño | 11 | 2 | 8/70 | 0,038 | **0,011** |
| **modesto y limpio** | **6** | **0** | **11/70** | **0,145** ❌ | **0,016** ✅ |
| modesto con daño | 8 | 2 | 11/70 | 0,145 ❌ | 0,055 |
| ruido puro | 8 | 7 | 16/70 | ~0,5 | ~0,5 |

**Lee la tercera fila y la cuarta.** Las dos dan **exactamente 11/70**. Fisher las ve idénticas y dice «no concluyente» en las dos. McNemar dice **p = 0,016 (decide)** en una y **p = 0,055 (al filo)** en la otra — porque a una no se le rompió nada y a la otra sí.

> **Y ésta es la traducción exacta de la propia instrucción del agente:**
> *«comparar los ids, no sólo el recuento: si baja el número pero cambian los ids, no se arregló nada».*
>
> **McNemar es esa instrucción convertida en estadístico.** El proyecto ya tenía la disciplina correcta; sólo le faltaba el test que la implementa.

Y la última fila enseña la otra mitad: **McNemar no se deja engañar por el ruido.** Un flip aleatorio es simétrico por definición — infla `b` y `c` por igual — así que **no produce falsos positivos, sólo cuesta poder.** Eso es una propiedad, no una suposición.

## El protocolo de enmienda que NO rompe el sello

El sello `sha256 797b4865e85a8332` existe para impedir que alguien mueva el criterio **después de ver los datos**. Cambiarlo ahora es legítimo porque **los datos no existen todavía** — pero sólo si se hace de forma que quede demostrado.

1. **No se toca `01_aceptacion.json`.** Fisher sigue siendo el criterio primario sellado. El sello se recalcula antes de escribir el veredicto y debe coincidir.
2. Se crea **`01b_aceptacion_pareada.json`**, con McNemar exacto de una cola como **secundario pre-registrado**, y se sella con su propio `sha256`.
3. El fichero nuevo lleva **el commit de `main` en el momento de escribirlo** (`2cf21876`) y la marca de tiempo. Eso es lo que prueba que se escribió antes de la corrida.
4. **Se reportan los dos, siempre**, ganen o pierdan. Si divergen, la divergencia **es** el hallazgo y se explica.

**Lo que NO se hace bajo ningún concepto:** sustituir Fisher por McNemar. Se añade. Un criterio que se reemplaza deja de ser un criterio.

---

# PASO 3 · El brazo, rediseñado — 160 min en vez de 84

Aquí está la recomendación central de este documento, y cuesta **76 minutos más** que el plan actual.

## Corre la base otra vez, esta noche, pegada al brazo combinado

```
PLAN ACTUAL      combinada (76 min)  ──  comparar contra la base del 7 de agosto
                 84 min · un brazo · control histórico

PLAN PROPUESTO   base (76 min)  →  combinada (76 min)  ──  comparar entre sí
                 ~160 min · dos brazos · control contemporáneo
```

**Los 76 minutos extra compran tres cosas a la vez:**

**1 · Un control contemporáneo.** La base del 7 de agosto se midió **antes** del rescate de la máquina, antes de que `main` se pusiera verde, antes de cinco despliegues. Se hizo un esfuerzo enorme por dejar el driver y el kernel exactamente como estaban — **y ese esfuerzo demuestra precisamente que alguien ya sabía que la comparabilidad estaba en riesgo.** Un control corrido esta noche no necesita ese argumento: es comparable por construcción.

**2 · El suelo de ruido, gratis.** La base de esta noche contra la base del 7 de agosto **es** la medida de reproducibilidad del instrumento. Nunca se ha hecho, y es la cifra que decide cómo se lee un resultado ambiguo.

**3 · Elimina el confusor del tiempo.** Entre el 7 de agosto y hoy cambiaron el driver, el kernel, seis commits y la configuración del poller. Dos brazos corridos con una hora de diferencia no tienen ese problema.

## Por qué el suelo de ruido no es opcional

HemoVet corre a **temperatura 0,3**, y la base se midió **una sola vez** (K=1). La literatura reciente sobre reproducibilidad de evaluaciones con LLM es directa al respecto:

- Fijar la temperatura a 0 es **necesario pero no suficiente** — el título del trabajo es, literalmente, el hallazgo arquitectónico de este proyecto. Con la temperatura sin fijar, los ítems cerca de la frontera de decisión **cambian de veredicto hasta en un ~50 % de las corridas idénticas** (20 corridas). Incluso con temperatura 0 quedan ítems inestables (6 vs 4 sobre 10 corridas): **la no-determinación viene del paso hacia adelante, no del muestreo.**
- Para detección de cambio fiable entre versiones, la práctica recomendada es el **índice de cambio fiable** (|RCI| > 1,96) sobre la fiabilidad test-retest, y **K=2 basta para r=0,80 · K=3 para r=0,90**. HemoVet está en **K=1**, que no permite estimar nada.

**Traducido a HemoVet:** los 17 fallos de la base son un punto, no una distribución. Si un 10 % de los casos son fronterizos y voltean, una re-corrida de la base podría dar **entre 14/70 y 20/70 sin que haya cambiado una sola línea de código.** Con el brazo combinado en 4/70 eso da igual — el efecto es enorme y lo atraviesa. **Con el brazo combinado en 11/70, es la diferencia entre un hallazgo y una ilusión.**

## Si de verdad no caben 160 minutos

La versión barata: **re-corre sólo un submuestreo estratificado de la base** — los **17 que fallaron** más **17 que pasaron**, elegidos con semilla fija y documentada. **34 casos, ~37 minutos.** Da las dos tasas de volteo (rescate por ruido y rotura por ruido), que es el 80 % del valor por el 45 % del coste.

**Y una tercera opción, la más honesta si el tiempo aprieta:** corre sólo la combinada esta noche, **pero declara por escrito, antes de correr, que el control es histórico y que el suelo de ruido es desconocido** — y ponlo en la sección de limitaciones del veredicto, no en una nota al pie. Un resultado con una limitación declarada vale; un resultado con una limitación no declarada envenena el registro.

## El confusor del runner, que ahora no lo corrige nadie

El poller está apagado desde `2cf21876`. La rama silenciosa que **sí** realineaba —sin decirlo— ya no corre. Si el runner deriva a 65536 a mitad de la batería, **cada turno posterior paga 101 s y nadie lo registra**.

**Instrumentación obligatoria, y cuesta cuatro llamadas a `/api/ps`:**

```
antes del brazo base        → size_vram  (esperado 16 926 501 764 = 16 384)
después del brazo base      → size_vram
antes del brazo combinado   → size_vram
después del brazo combinado → size_vram
```

Umbral: **±5 %**. La separación entre 16384 y 65536 es del **11,6 %**, así que el discriminador tiene margen de sobra. Si alguna de las cuatro lecturas se sale, **la corrida correspondiente queda marcada como contaminada** y se repite. No se «corrige a posteriori».

---

# PASO 4 · El árbol de decisión, completo

El plan actual sólo especifica los extremos. Éste cubre los casos mixtos, que son los más probables.

| resultado | Fisher | McNemar | qué se hace |
|---|---|---|---|
| **≤8/70, ambos p<0,05, clínica no empeora, ninguna validación relajada** | ✅ | ✅ | **ACEPTADA.** Parar y preguntar antes de dejarla permanente (condición 4 del prompt) |
| **≤8/70 pero alguna validación pasa algo que antes no pasaba** | — | — | **RECHAZADA sin discusión.** Es la puerta binaria. No se negocia con el recuento |
| **11/70 con `c = 0`** (nada se rompió) | ❌ 0,145 | ✅ 0,016 | **ACEPTADA con reserva.** Se reporta la divergencia entre los dos tests como el hallazgo que es. Y se corre el suelo de ruido antes de firmar |
| **11/70 con `c ≥ 2`** (algo se rompió) | ❌ | ~0,055 | **NO CONCLUYENTE.** Aquí sí toca atribuir: aparato local y los cinco brazos. Y antes, **mirar qué se rompió** — 2 casos rotos por una mitigación que sólo rellena datos es un hallazgo por sí solo |
| **b y c parecidos** (p. ej. 8 y 7) | ~0,5 | ~0,5 | **RUIDO.** La cartera no hace nada. Y el suelo de ruido lo confirma o lo desmiente en 37 min |
| **baja el recuento, cambian los ids** | puede dar p<0,05 | detecta `c>0` | **RECHAZADA.** Es el escenario que McNemar existe para cazar. Fisher lo aprobaría |
| **empeora cualquier cosa** | — | — | `revert` en 4 minutos, y a investigar por qué |
| **mejora sólo la latencia** | — | — | **OBSERVACIÓN**, según el criterio sellado. No es aceptación |

**Y la comprobación previa a escribir nada:** recalcular el `sha256` de `01_aceptacion.json`. Si no da `797b4865e85a8332`, el criterio se movió y el veredicto no vale.

---

# PASO 5 · Después del veredicto — el orden, por efecto entre riesgo

Con la cartera decidida, la cola queda así. **El orden no es por tamaño del efecto: es por efecto dividido entre riesgo clínico**, que es el criterio correcto en un producto que da orientación veterinaria.

| # | qué | efecto | riesgo clínico | coste |
|---|---|---|---|---|
| **1** | **4.1.d — pintar las etapas que el backend ya emite** | la espera pasa de barra muda a progreso visible | **cero.** No toca backend, no toca validación | 3 h |
| **2** | **M-10 — el contrato asimétrico** | utilidad 63 % → ~81 %. **El mayor problema que queda** | **alto.** Toca el prompt de sistema. **Exige revisión veterinaria, no sólo código** | 6 h + un brazo |
| **3** | **Las once instancias vivas del patrón** | cierra la deuda estructural | cero, son aserciones | 6 h |
| **4** | **Streaming de verdad** | espera percibida 34,8 s → ~1 s | **alto y no resuelto** (abajo) | 10 h |
| **5** | Cambiar de modelo (35B-A3B) | ~4,4 s reales | destruye la línea base | aparcado |

**El 4.1.d va primero y lleva cinco sesiones sin asignar.** Es frontend puro, cuesta tres horas, no toca una sola validación clínica, y es lo que convierte «no funciona» en «está trabajando» a ojos del usuario. De toda la lista es la mejor relación efecto/riesgo y con diferencia.

## Y el problema del streaming, que hay que resolver antes de empezarlo

**No es de transporte, es de contrato.** El proxy está bien —Caddy con `flush_interval -1` y sin compresión en el endpoint— y el backend ya emite eventos de etapa. Lo que no puede hacerse es emitir **texto clínico** mientras se genera, porque ese texto **todavía puede ser rechazado por las seis puertas**. Emitirlo antes de validarlo es exactamente lo contrario de lo que el contrato existe para garantizar.

Hay riesgo técnico documentado encima: en el endpoint `/v1/chat/completions` —el que usa el cliente de HemoVet— hay un fallo reportado en el que, con `stream=true`, **no se garantiza que la concatenación de los deltas cumpla el esquema.**

> **Decisión de diseño que hay que tomar antes de escribir una línea:** ¿qué se emite antes de validar? Si la respuesta es «nada», entonces el streaming real es imposible con este contrato y **el 4.1.d es la solución, no un parche**. Si la respuesta es «los claims que ya pasaron sus puertas», entonces hay que rediseñar el validador para que valide claim a claim en vez del sobre entero — y eso es un proyecto, no una tarea.

---

# El calendario

| | qué | horas | acumulado |
|---|---|---:|---:|
| **Paso 0** | T-1, T-2, T-3 | 0,7 | 0,7 |
| **Paso 1** | rama combinada + las tres verificaciones | 1,2 | 1,9 |
| **Paso 2** | enmienda pre-registrada y sellada | 0,3 | 2,2 |
| **Paso 3** | **los dos brazos, base y combinada** · *76 min medidos cada uno* | 2,7 | 4,9 |
| **Paso 4** | el veredicto, con los dos tests y el suelo de ruido | 0,7 | **5,6** |
| | ↑ **aquí se sabe si veintitrés sesiones sirvieron** ↑ | | |
| | 4.1.d | 3 | 8,6 |
| | M-10 + su brazo | 6 | 14,6 |
| | las once instancias | 6 | 20,6 |
| | streaming | 10 | **30,6** |

**≈ 5,6 h al veredicto** (frente a las 2,9 del plan anterior; la diferencia es el segundo brazo y las medidas previas) **· ≈ 31 h a cerrarlo todo.**

**Y sigue siendo una sola noche de trabajo para llegar al veredicto.** El plan viejo del aparato local eran 13 horas sólo para llegar al mismo sitio, con diecisiete divergencias de paridad que vigilar y una puerta de calibración que podía fallar.

---

# Lo que NO hay que hacer

- **No sustituir el criterio sellado.** Añadir, nunca reemplazar.
- **No escribir ninguna mitigación nueva antes del veredicto.** La congelación de alcance sigue vigente. Lo que aparezca se anota; no se ramifica. *Una rama sin brazo es deuda disfrazada de progreso.*
- **No correr el brazo si el preflight aborta.** Corriendo contra producción no debería dar ninguna divergencia; si da alguna, **eso es el hallazgo** y la corrida se cancela.
- **No tocar la cadena firmada del arranque de la GPU.** El modo de fallo es que la VM se apaga sola, con L4 escasas para recuperarla.
- **No actualizar Ollama** — aunque la 0.32.6 arregle el reporte de `finish_reason: "length"`. Se compensa verificando la terminación del JSON por cuenta propia al clasificar los fallos.
- **No relajar ninguna validación clínica**, en particular `missing_required_clinical_facts`. Una sola salida que pase algo que antes no pasaba **rechaza el brazo entero**, gane lo que gane en el recuento.
- **No dejar la combinada desplegada de forma permanente sin autorización explícita**, aunque salga ACEPTADA. Ésa es la condición 4 de parada.

---

# En cinco frases

1. **Antes de crear la rama, tres medidas de 40 minutos** que pueden reordenar la cartera entera — sobre todo cuánto cuesta la gramática.
2. **La combinada necesita una verificación que nadie ha pedido:** M-4 renombra campos que M-1 y M-2 rellenan, y ningún test ha visto nunca las dos cosas a la vez.
3. **El test estadístico está mal elegido.** El diseño es pareado; McNemar decide donde Fisher se rinde, y es la instrucción «compara los ids, no el recuento» convertida en estadístico. Se añade sellado, no se sustituye.
4. **Corre la base otra vez esta noche, pegada a la combinada.** Setenta y seis minutos extra compran un control contemporáneo, el suelo de ruido del instrumento y la eliminación del confusor temporal — y sin eso, un resultado ambiguo no se puede interpretar.
5. **Y cuando esté el veredicto, el 4.1.d va primero**, no M-10: tres horas, riesgo clínico cero, y es lo que el usuario nota.

---

## Fuentes

- [*Necessary but Not Sufficient: Temperature Control and Reproducibility in LLM-as-Judge Safety Evaluations*](https://arxiv.org/html/2606.26185) — temperatura 0 es necesaria y no suficiente; hasta ~50 % de desacuerdo por ítem en corridas idénticas; la no-determinación viene del paso hacia adelante
- [*Beyond the Mean: Within-Model Reliable Change Detection for LLM Evaluation*](https://arxiv.org/html/2604.27405) — índice de cambio fiable, |RCI| > 1,96; K=2 basta para r=0,80, K=3 para r=0,90
- [McNemar's Test for Paired Before-and-After Data](https://mcpanalytics.ai/articles/mcnemars-test-practical-guide-for-data-driven-decisions) · [McNemar vs Fisher](http://rstudio-pubs-static.s3.amazonaws.com/471666_ba75a44f19e34b8197c51d6ec618f114.html) · [StatPearls — McNemar](https://www.ncbi.nlm.nih.gov/books/NBK560699/)
- [Ollama #15502](https://github.com/ollama/ollama/issues/15502) — repetición en cascada con campos de texto libre bajo gramática
- [Ollama #14440](https://github.com/ollama/ollama/issues/14440) — el esquema no se impone al combinar streaming con salida estructurada
- [Ollama #10929](https://github.com/ollama/ollama/issues/10929) — pensamiento + salida estructurada produce JSON malformado
- [llama.cpp #25746](https://github.com/ggml-org/llama.cpp/issues/25746) — `maxLength ≥ 2000` anidado genera GBNF no parseable
- [Ollama v0.32.6](https://github.com/ollama/ollama/releases/tag/v0.32.6) — `finish_reason: "length"` mal reportado en 0.32.5
- [Mejores LLM locales para salida estructurada: Qwen 3.6, Gemma 4](https://insiderllm.com/guides/structured-output-local-llms/) — las gramáticas frenan la generación entre un 30 % y un 80 %
