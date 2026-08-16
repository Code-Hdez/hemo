# Formato de salida y eliminación de reintentos — HemoVet

**Investigación sobre `Code-Hdez/hemo` @ `50954156` · agosto 2026**
Fuentes: código del repositorio, `cristiandlahoz/socratic-tutor` @ `29b8c22`, documentación oficial de
Qwen/Ollama/Anthropic/OpenAI, issues de GitHub, papers de arXiv 2024-2026, foros y blogs de ingeniería.

---

## 0. El titular: la premisa está invertida

Tú planteaste que *«no hay un formato de salida en específico… no está devolviendo un Markdown, no
está devolviendo un JSON, no está devolviendo algo con lo cual se pueda manipular de forma sencilla»*.

**Es exactamente al revés, y esa inversión es el hallazgo más importante de esta investigación.**

HemoVet tiene un contrato de salida **extraordinariamente específico**: un JSON estricto,
compilado a gramática GBNF, que el modelo está obligado a cumplir token a token. Vive en
`backend/app/modules/llm_chat/application/services/structured_response.py` (1 593 líneas) y se envía
a Ollama en `infrastructure/llm/openai_compatible_client.py:870`:

```python
payload["format"] = request.response_schema
```

El problema no es que falte formato. **El problema es que sobra**, y que la respuesta clínica —el
texto que lee el usuario— está metida dentro de un campo `string` de ese JSON. Eso reproduce, punto
por punto, un modo de fallo documentado y **abierto** en Ollama.

Corregir la premisa importa porque cambia por completo qué hay que arreglar: no hay que *añadir*
estructura, hay que *sacar la prosa de dentro de ella*.

---

## 1. Qué contrato tiene HemoVet exactamente

El sobre es `GeneratedResponseEnvelope`. Esto es lo que el modelo debe producir **en cada turno**:

```python
class GeneratedResponseEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")          # → additionalProperties: false
    schema_version: Literal["hemovet-response-v2"]
    response_type: str = Field(min_length=1, max_length=80)
    intent:        str = Field(min_length=1, max_length=80)
    claims: list[GeneratedClaim] = Field(min_length=1, max_length=48)
    safety: GeneratedSafety

class GeneratedClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_id:        str  = Field(pattern=r"^claim_[A-Za-z0-9_-]{1,80}$")   # ← regex
    text:            str  = Field(min_length=1, max_length=1800)            # ← la prosa clínica
    claim_type:      ClaimType                                              # ← enum
    fact_ids:        list[str] = Field(max_length=32)
    source_ids:      list[str] = Field(max_length=16)
    policy_rule_ids: list[str] = Field(max_length=16)
    evidence_spans:  list[EvidenceSpan] = Field(max_length=16)

class EvidenceSpan(BaseModel):
    source_id: str = Field(min_length=1, max_length=160)
    text:      str = Field(min_length=1, max_length=600)

class GeneratedSafety(BaseModel):   # SIETE booleanos obligatorios en CADA sobre
    dx, med, dose, freq, dur, pers, urg: bool
```

Más validadores semánticos en `@model_validator`: las claims basadas en hechos exigen `fact_ids`; el
conocimiento documentado exige `source_ids` **y** `evidence_spans`; la guía de seguridad exige
`policy_rule_ids`; las claims conversacionales tienen prohibido citar. Esas son las **seis puertas al
afirmar frente a una al declinar** que el diagnóstico previo ya había identificado.

Un sobre mínimo válido —una sola claim conversacional, texto de un carácter— ocupa **345 caracteres
≈ 108 tokens** de andamiaje antes de escribir una palabra clínica. El informe de fases midió el suelo
real en **204 tokens**. A los 40,849 tok/s medidos en la A100 eso son **4,99 segundos de reloj** —
**la mitad de un presupuesto de 10 segundos**, gastados en metadatos.

---

## 2. Por qué falla — cuatro mecanismos, todos activos a la vez

### 2.1 El bug de repetición en cascada: HemoVet cumple las tres condiciones

**[ollama#15502](https://github.com/ollama/ollama/issues/15502) — ABIERTO.** Patrón: la generación va
bien → una palabra se duplica → colapsa en un único token repetido hasta agotar el presupuesto → **el
JSON queda sin cerrar**. Tasa de reproducción **60–100 %** sobre 39 ensayos.

El issue documenta que hacen falta **tres condiciones simultáneas**:

| Condición | ¿HemoVet? |
|---|---|
| 1 · Modelo **denso** (los MoE no se ven afectados) | ✅ Qwen3.6-27B es denso |
| 2 · Parámetro `format=` con esquema JSON | ✅ `payload["format"]` en `openai_compatible_client.py:870` |
| 3 · **Campos string de texto libre** en el esquema | ✅ `claim.text`, hasta 1 800 caracteres |

**Las tres.** Y la causa raíz explica por qué la reparación no puede arreglarlo: *«dentro del valor de
un string JSON cualquier contenido válido está permitido»* — la gramática garantiza la sintaxis, **no
puede rechazar texto degenerado**. El reportante probó `repeat_penalty` a 1,0 / 1,15 / 1,5 con la
misma semilla y obtuvo **fallos idénticos**.

HemoVet repara con `repeat_penalty=1.1`. Eso está probado como inútil para este fallo.

### 2.2 El esquema usa justo los keywords que rompen GBNF

Verificado: **no hay poda** de keywords antes de enviar el esquema. Van tal cual:

| Keyword en el esquema | Issue documentado |
|---|---|
| `pattern` en `claim_id` | [ollama#8185](https://github.com/ollama/ollama/issues/8185) — error de validación con `pattern` |
| `maxLength` 1800 / 600 / 160 / 80, anidados en arrays | [llama.cpp#25923](https://github.com/ggml-org/llama.cpp/issues/25923) — **ABIERTO**: los `maxLength` grandes generan cuentas de repetición que exceden el tope de 2 000 del motor gramatical |
| `enum` / `const` (`ClaimType`, `schema_version`) | [ollama#8063](https://github.com/ollama/ollama/issues/8063) — «no se respetan» |
| `$defs` (Pydantic los genera) | [ollama#8444](https://github.com/ollama/ollama/issues/8444) — **ABIERTO**: el orden alfabético de `$defs` cambia el resultado |

Y una advertencia estructural de llama.cpp#25923 que aplica directamente: *«todos los esquemas se
compilan en un único GBNF combinado, así que un solo esquema problemático rompe todo»*.

### 2.3 El impuesto de capacidad: Qwen3.6-27B Q4_K_M está en el régimen malo

El debate «¿degrada la salida estructurada?» quedó resuelto en 2026, y no a favor de ninguno de los
dos bandos originales: **depende de la capacidad del modelo.**

**Capacity, Not Format** ([arXiv 2606.09410](https://arxiv.org/abs/2606.09410)), con controles de prosa
*information-matched* y 0 % de fallos de parseo:

| Modelo | Prosa | JSON | Δ |
|---|---|---|---|
| Sonnet 4.6 (MATH-Hard) | 89,3 % | 88,7 % | −0,6 pp (no significativo) |
| **Haiku 4.5** | 88,7 % | 52,5 % | **−36,2 pp** (p<0,0001) |
| **GPT-4o-mini** | 62,3 % | 34,3 % | **−28,0 pp** |

Interacción formato × capacidad confirmada estadísticamente (p = 3,8×10⁻³). Un 27B cuantizado a
4 bits **no es un modelo frontera**: la cuantización recorta precisamente el margen de capacidad que
el paper identifica como la variable moderadora.

**The Constraint Tax** ([arXiv 2605.26128](https://arxiv.org/html/2605.26128v1), 15 000 generaciones)
aporta el dato más incómodo. En una tarea donde **ambos modos alcanzan 100 % de validez de esquema**:

| Modo | Exactitud ejecutable |
|---|---|
| JSON solo por prompt | **91,5 %** |
| Decodificación con esquema duro | **48,0 %** |

**−43,5 pp con validez idéntica.** La tasa de «esquema válido pero incorrecto» pasa del 49,5 % al
**88,9 %**. La garantía del esquema no garantiza nada de lo que importa clínicamente.

En sentido contrario, y hay que decirlo: en **clasificación** la estructura ayuda mucho —DDXPlus,
diagnóstico diferencial médico, **+18,77 pp** ([arXiv 2408.02442](https://arxiv.org/abs/2408.02442))—.
Eso no contradice nada: dice que el JSON es correcto para el clasificador y equivocado para la prosa.

### 2.4 La economía del token: el esquema decide la respuesta, no la evidencia

Con seis puertas al afirmar y una al declinar, declinar es **la salida barata**. El diagnóstico del
proyecto ya lo midió: **6,50× más rechazos** (50/107 frente a 21/292). No es que el modelo sea
cauteloso; es que el contrato hace que callarse cueste menos tokens y menos riesgo de invalidación
que hablar. El 36,5 % que calla es una consecuencia de diseño, no una propiedad del modelo.

### 2.5 Un apunte de riesgo que conviene verificar

**[ollama#15260](https://github.com/ollama/ollama/issues/15260)**: `think:false` **rompía `format`** —
el enmascarado del esquema se difiere hasta detectar el token de fin de *thinking*, y con `think=false`
ese token nunca llega, **así que la máscara nunca se aplica**. Corregido en los PR #15678/#15392, que
deberían estar en 0.32.6, pero HemoVet usa exactamente esa combinación (`OLLAMA_THINK=0` + `format`).
Merece una comprobación de una tarde: enviar un esquema imposible de cumplir y ver si la respuesta lo
respeta o lo ignora.

---

## 3. Los reintentos: cómo funcionan y por qué probablemente nunca sirvieron

### 3.1 Dónde está el bucle

`application/use_cases/send_chat_message.py:1723`:

```python
needs_repair = (generated.finish_reason == "length" or validation.disposition != "valid")
...
if (needs_repair
        and self.generation_settings.max_generation_attempts >= 2
        and remaining_seconds >= repair_window):
```

Dos niveles distintos, y conviene no confundirlos:

| Nivel | Variable | Valor | Qué es |
|---|---|---|---|
| **Contenido** | `CHAT_MAX_GENERATION_ATTEMPTS` | 2 | 1 generación + 1 **reparación** (`num_predict=1024`, `temperature=0.1`, `repeat_penalty=1.1`) |
| **Transporte** | `OLLAMA_MAX_RETRIES` | 1 (tope duro) | Reintento HTTP ante 5xx / conexión caída |

**Eliminar la regeneración por contenido es un cambio de una variable**: `CHAT_MAX_GENERATION_ATTEMPTS=1`.
La guarda `>= 2` hace que todo el bloque quede muerto sin tocar código.

### 3.2 La aritmética dice que la reparación reproduce el fallo que debía arreglar

Con las cifras de la línea base: p50 reparando 98,1 s frente a 34,8 s sin reparar → la reparación
cuesta **63,3 s**. A esa tasa implícita (~16,2 tok/s en la L4), 63,3 s con `num_predict=1024`
significa que **la reparación consume su presupuesto entero**: no termina por EOS, **topa en el
límite**. Y las generaciones normales, a 34,8 s, rondan los 560 tokens — muy por debajo de su tope
de 1 280.

> **Si el fallo original fue truncamiento a 1 280 tokens, reparar con 1 024 garantiza truncar antes.**

La reparación tiene un presupuesto **un 20 % menor** que la generación que falló por falta de
presupuesto. Añadido a que `repeat_penalty=1.1` está desaconsejado para salida estructurada —*«suprime
agresivamente palabras estructurales y rompe fácilmente la sintaxis»*, y *«causa respuestas
innecesariamente largas»*—, la reparación tiene una vía mecánica para empeorar precisamente lo que
intenta arreglar.

**Verificación barata antes de tocar nada:** registrar `done_reason` y `eval_count` segregados por
intento normal y reparación. Si `done_reason == "length"` domina en las reparaciones, queda
confirmado que el bucle nunca funcionó — solo añadió ~63 s a turnos que iban a fallar igual.

### 3.3 Eliminarlos está justificado, pero arregla la cola, no la mediana

Esto hay que decirlo con claridad porque contradice la expectativa implícita:

| Palanca | Qué arregla | Qué NO arregla |
|---|---|---|
| Quitar la reparación | **p95/p99: 98,1 s → ~34,8 s** | La mediana. Sigue en ~35 s (L4) / 17,6 s (A100) |
| Quitar la gramática | Nada relevante: **+1,4 % de velocidad** | Todo lo demás |
| Quitar el sobre del decoder | **Libera 4,99 s** = 50 % de un presupuesto de 10 s | — |
| Recortar la salida a ~250 tok | **13,7 s → 6,1 s** de decode | — |
| Streaming real | La latencia **percibida** | El tiempo total |

**El objetivo de 10-15 s es un problema de mediana; los reintentos son un problema de cola.** Ninguna
palanca sola llega. La combinación que sí llega: quitar la reparación + sacar el sobre del decoder +
recortar la longitud de salida + streaming real.

### 3.4 Lo que se pierde, dicho honestamente

Un reintento **sí** es correcto para fallos de transporte: un 503, una conexión caída, un timeout de
red. Eso es idempotente y transitorio. Conserva `OLLAMA_MAX_RETRIES=1` con clasificación estricta de
errores, y elimina solo la regeneración por contenido. No son lo mismo y mezclarlos es un error
común.

Lo que se pierde al quitar la reparación es la recuperación de fallos genuinamente aleatorios de
generación. Con `seed=-1` (semilla aleatoria) y `temperature 0.15-0.3`, esos existen. Pero repetir
con **más restricción y menos presupuesto** no es la forma de recuperarlos.

Y la guía de UX conversacional de Microsoft es tajante sobre el reintento automático: *«es útil hacer
saber al usuario cuándo debería intentarlo de nuevo, **pero solo si volver a intentar tiene
probabilidad de éxito**»*. Si el fallo es estructural —esquema, presupuesto, prompt— reintentar es
deshonesto con el usuario y caro para todos.

---

## 4. Cómo lo resuelve socratic-tutor

El repositorio de referencia que pasaste ya tomó estas decisiones, y su arquitectura es la respuesta
a la pregunta:

**No usa Ollama para chat.** Usa `llama-swap` → `llama-server` (llama.cpp) con endpoint
OpenAI-compatible. Ollama queda relegado a embeddings.

**Arquitectura de dos velocidades:**

| Tipo de generación | Formato | Gramática |
|---|---|---|
| **Chat tutor** (la respuesta larga que lee el usuario) | **Markdown en streaming**, `Flux<String>` | **Ninguna** |
| Título de conversación, clasificador de seguridad, catálogo, temario | JSON | Sí, `outputSchema` |
| Panel interactivo de preguntas | **tool calling** | — |

`ChatService.chatStream()` devuelve tokens sueltos; el frontend los renderiza incrementalmente con
`marked` + `DOMPurify`. **Sin `outputSchema`, sin `format`, sin gramática.**

Y nunca mezclan `tools` + `format` en la misma llamada — evitando por diseño
[ollama#13750](https://github.com/ollama/ollama/issues/13750).

**Cero reintentos.** `grep -rn "retryWhen\|@Retryable\|RetryTemplate\|maxAttempts" src/main/` → **0
resultados.** En su lugar, cinco capas de defensa: filtros deterministas por regex **antes** de gastar
la llamada al modelo; parseo defensivo que quita fences y toma de la primera `{` a la última `}`;
fail-closed en el guardián; invariantes en el constructor del DTO que convierten «JSON válido pero
incoherente» en excepción; y ante timeout, **devolver el prompt al compositor** para que el usuario
decida, en lugar de reintentar solo.

En una frase: **la generación larga es texto libre; la generación corta es JSON.** HemoVet hace justo
lo contrario.

---

## 5. Recomendación

### 5.1 El principio

> **El modelo solo debe generar aquello que únicamente él puede generar.** Todo lo demás lo sabe ya
> el servidor, y hacérselo escribir al modelo cuesta tokens, cuesta latencia y cuesta fiabilidad.

Repasa el sobre con ese criterio:

| Campo | ¿Lo tiene que generar el modelo? | Quién debería producirlo |
|---|---|---|
| `schema_version` | **No** | Constante del servidor |
| `response_type` | **No** | El servidor ya enrutó la petición |
| `intent` | **No** | Ya existe `intent_classifier.py` |
| `claim_id` | **No** | Contador del servidor |
| `claim_type` | Discutible | Clasificador post-hoc |
| `fact_ids` | **No** | El servidor sabe qué hechos inyectó; verifica por coincidencia de valor |
| `source_ids` | **No** | El servidor sabe qué fuentes recuperó el RAG |
| `evidence_spans` | **No** | Coincidencia de texto contra el chunk recuperado, en el servidor |
| `policy_rule_ids` | **No** | Registro de políticas del servidor |
| `safety` (7 booleanos) | **No** | Clasificador determinista o modelo pequeño, **después** |
| **`text`** | **Sí** | **Es lo único que solo el modelo puede hacer** |

De once campos, **uno** necesita al LLM que escribe. Los otros diez son andamiaje que el sistema paga
a 24,48 ms por token, con riesgo de truncar la respuesta clínica.

Anthropic llegó a la misma conclusión por una vía distinta y la impone con un error 400:

> *«Las citaciones requieren intercalar bloques de citación con el texto, lo cual entra en conflicto
> con las restricciones estrictas de esquema JSON.»* — [Structured outputs, Claude Platform Docs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)

`policy_rule_ids` y `evidence_spans` son funcionalmente citaciones. Un proveedor frontera, con
equipos dedicados a esto, concluyó que **no se pueden tener las dos cosas en el mismo objeto**.

### 5.2 El formato objetivo

**Dos canales, no uno.**

**Canal A — la respuesta al usuario: Markdown, en streaming, sin gramática.**
Es lo que hace toda aplicación de chat en producción. El control de formato se hace **por prompt de
sistema**, no por GBNF —el prompt de sistema de Claude 4 es la demostración de cuánta ingeniería de
formato cabe sin ninguna restricción de decodificación—. Beneficios inmediatos y acumulativos:

- Desaparece la condición (3) de [ollama#15502](https://github.com/ollama/ollama/issues/15502): sin
  campos string bajo gramática, no hay cascada de repetición.
- Desaparece el JSON sin cerrar: un Markdown truncado sigue siendo legible; un JSON truncado no
  existe. **Ese solo cambio convierte un fallo duro en una degradación suave.**
- Se libera el suelo del sobre: **4,99 s** de reloj.
- Se habilita el streaming de verdad, que es lo que cambia la percepción de latencia.

**Canal B — los metadatos: fuera del camino de decodificación.**
La mayoría se resuelve en el servidor sin LLM (tabla de §5.1). Lo que sí requiera modelo —los siete
flags de seguridad, el `claim_type`— va en una **segunda llamada, con esquema mínimo, temperatura 0 y
un modelo pequeño**, ejecutada **en paralelo o después** de que el texto ya esté fluyendo al usuario.
Es el patrón *switzerland-knife* de socratic-tutor: un modelo grande para prosa, uno pequeño para
etiquetar.

Aquí la estructura **sí ayuda**: es clasificación con vocabulario cerrado, el caso donde la evidencia
muestra **+18,77 pp**.

**Y donde el JSON debe quedarse:** la extracción de valores del hemograma. Vocabulario cerrado, sin
razonamiento largo, consumidor de máquina. Es exactamente para lo que se diseñó la salida estructurada.

### 5.3 La regla de decisión, resumida

| Situación | Formato |
|---|---|
| El consumidor es **una persona leyendo** | Markdown, streaming, sin gramática |
| El consumidor es **código** (parser, BD, gráfica) | JSON estricto con gramática |
| **Clasificación** en taxonomía fija | JSON estricto — aquí **mejora** |
| **Razonamiento clínico en prosa** | Sin gramática |
| **Mezcla** de prosa + metadatos | **Separar en dos llamadas** |

---

## 6. Plan de migración, por orden de relación beneficio/riesgo

| # | Acción | Coste | Efecto esperado | Riesgo |
|---|---|---|---|---|
| **1** | **Instrumentar `done_reason` y `eval_count`** por intento normal vs reparación | 1 tarde, sin cambios de contrato | Confirma o refuta que la reparación nunca funcionó | Ninguno |
| **2** | `CHAT_MAX_GENERATION_ATTEMPTS=1` | Una variable | **p95: 98 s → ~35 s.** La mediana no se mueve | Bajo: se pierde recuperación de fallos aleatorios |
| **3** | `repeat_penalty` de 1,1 → **1,0** en reparación (si se conserva) | Una variable | Elimina una causa probable de truncamiento | Ninguno — Qwen recomienda 1,0 para todos los modos |
| **4** | **Podar el esquema**: quitar `pattern`, bajar los `maxLength`, validar esas restricciones en Python y no en el esquema | Horas | Elimina los keywords que rompen GBNF | Bajo — la validación se conserva, cambia de sitio |
| **5** | **Sacar del sobre lo que el servidor ya sabe** (`schema_version`, `response_type`, `intent`, `claim_id`, `fact_ids`, `source_ids`, `policy_rule_ids`) | Días | **Libera ~4,99 s** y quita puertas de invalidación | Medio: hay que reimplementar la verificación en el servidor |
| **6** | **Sacar la prosa de la gramática**: canal Markdown en streaming | Semanas | Elimina las tres condiciones de #15502; JSON truncado → Markdown truncado | Alto: es el cambio arquitectónico |
| **7** | Mover los 7 flags de seguridad a una segunda llamada con modelo pequeño | Días | Quita 7 booleanos del camino crítico | Medio |
| **8** | **Arreglar el arranque en frío**: alinear `OLLAMA_CONTEXT_LENGTH` con el `num_ctx` de la petición (ambos a 16 384) | Una variable | Elimina la recarga de ~101 s del primer turno, que causó los 2 únicos fallos de las baterías | Bajo |
| **9** | Recortar `num_predict` a ~400-600 y pedir brevedad en el prompt | Horas | **13,7 s → 6,1 s** de decode | Medio: respuestas más cortas (probablemente deseable) |
| **10** | Evaluar migrar Ollama → `llama-server` con `--spec-type draft-mtp --spec-draft-n-max 2` | Semanas | **~2× de velocidad**: el GGUF de Qwen3.6 trae tensores MTP que Ollama **no puede usar** en CUDA | Alto: cambio de runtime |

Los pasos 1-4 son configuración y no tocan la arquitectura. Los pasos 5-7 son el rediseño del
contrato. El 8 es la corrección más barata de todo el informe. Los 9-10 son la palanca de velocidad.

**Nota sobre el paso 10:** [ollama#5800](https://github.com/ollama/ollama/issues/5800) («enable
speculative decoding») lleva **abierto desde julio de 2024**. En Ollama 0.32.6 sobre CUDA/GGUF,
`draft_num_predict=0` no es configurable: los tensores MTP del artefacto son peso muerto (~1-2 GB de
VRAM sin usar). llama.cpp sí los aprovecha, con **1,4×-2,2×** documentado y `--spec-draft-n-max 2`
como punto óptimo (83 % de aceptación). socratic-tutor ya usa `llama-server`, aunque tampoco activa
MTP: también deja ese 2× sobre la mesa.

---

## 7. Lo que NO recomiendo

**No migres a vLLM ni a SGLang.** A batch = 1 —tu caso: `NUM_PARALLEL=1`— sus ventajas
(*continuous batching*, PagedAttention) no aplican, están diseñadas para amortizar sobre muchas
peticiones concurrentes. Además ninguno te da el path MTP-GGUF de Qwen3.6, y exigen rehacer la
cuantización. Si migras runtime, migra a `llama-server`.

**No subas la temperatura a 0,7** solo porque sea el valor oficial de Qwen para no-thinking. En
clínica, 0,1-0,3 es defendible. Pero **sí revisa la interacción**: `presence_penalty=1.5` está
heredado del artefacto y fue calibrado **para temperatura 0,7**. A 0,1 la distribución ya está muy
concentrada, y penalizar tokens ya usados dentro de un JSON —donde los nombres de campo se repiten
obligatoriamente— es cuestionable. Es un A/B de un parámetro.

**No actives el modo thinking** buscando calidad. En Qwen3.6-27B el razonamiento cuesta entre 3 175
tokens (GSM8K) y **10 777** (GPQA-Diamond) antes de empezar a responder — minutos de latencia. Y los
datos comparativos muestran que Qwen3.6 mejora en matemáticas pero **empeora frente a Qwen3.5 en
IFBench**, que mide exactamente el seguimiento de instrucciones que necesita un esquema.
`think:false` es la decisión correcta aquí.

**No conviertas el fallo en silencio.** Si una generación no cumple el contrato, el patrón correcto
no es reintentar ni callar: es **degradar de forma explícita**. Y en HemoVet hay una degradación
determinista disponible que ningún reintento te da — un hemograma es dato estructurado: la tabla de
parámetros con valores, unidades, rangos y marcado de fuera-de-rango se renderiza en milisegundos,
sin LLM y sin posibilidad de alucinar. En un contexto clínico, un error visible con datos correctos
vale más que una respuesta reparada de calidad dudosa.

---

## 8. Lo que la evidencia no sostiene

Por honestidad, y porque el proyecto ya ha pagado caro cerrar conclusiones antes de tiempo:

- **La gramática no es el cuello de botella de velocidad.** Tú mismo lo mediste: +0,332 ms/token,
  el 1,33 % del TPOT. Quitarla daría **+1,4 %**. La literatura reporta 27-30 ms/token para GBNF, pero
  esas cifras incluyen compilación por petición y esquemas mucho más complejos. **Tu medición es la
  correcta para tu stack.** Toda la ganancia está en *no generar los 204 tokens*, no en quitar la
  gramática. Son dos decisiones independientes.
- **Que quitar los reintentos mejore la mediana.** No lo hará. Arregla la cola.
- **Que el 27B con este contrato llegue a 10 s con respuestas de longitud útil.** A 40,849 tok/s,
  10 s son 408 tokens de decode puro y ~347 con un TTFT realista de 1,5 s — unas 200-215 palabras en
  español clínico. Es alcanzable, pero exige recortar la salida, no solo quitar reintentos.
- **Que la salida estructurada sea mala en general.** No lo es. En clasificación mejora. El problema
  es específico: **prosa larga dentro de un campo string bajo gramática, en un modelo cuantizado**.
- **Que el bug #15502 sea con certeza tu bug.** Está reportado sobre gemma4:31b, no sobre Qwen3.6.
  Cumples las tres condiciones necesarias, lo cual es una hipótesis fuerte — pero necesitas el paso 1
  del plan para confirmarlo con tus propios `done_reason`.

---

## 9. Fuentes

**Repositorios**
`Code-Hdez/hemo` @ `50954156` — `structured_response.py`, `send_chat_message.py:1723`, `openai_compatible_client.py:870`, `output_validator.py`, `response_contracts.py` ·
`cristiandlahoz/socratic-tutor` @ `29b8c22` — `ChatService.java`, `GuardClassifierService.java`, `TutorGuardAdvisor.java`, `application.yml`, `start-llama-server.sh`

**Issues abiertos que afectan directamente**
[ollama#15502](https://github.com/ollama/ollama/issues/15502) repetición en cascada ·
[llama.cpp#25923](https://github.com/ggml-org/llama.cpp/issues/25923) `maxLength` rompe GBNF ·
[ollama#8444](https://github.com/ollama/ollama/issues/8444) orden de `$defs` ·
[ollama#8185](https://github.com/ollama/ollama/issues/8185) `pattern` ·
[ollama#13750](https://github.com/ollama/ollama/issues/13750) `format` anula `tools` ·
[ollama#5800](https://github.com/ollama/ollama/issues/5800) decodificación especulativa, abierto desde 2024

**Issues cerrados relevantes**
[ollama#15260](https://github.com/ollama/ollama/issues/15260) `think:false` rompía `format` ·
[ollama#8063](https://github.com/ollama/ollama/issues/8063) esquemas no respetados ·
[ollama#7603](https://github.com/ollama/ollama/issues/7603) respuesta vacía durante la carga ·
[vLLM#18819](https://github.com/vllm-project/vllm/issues/18819) guided decoding roto con `enable_thinking=False`

**Papers**
[arXiv 2606.09410](https://arxiv.org/abs/2606.09410) *Capacity, Not Format* ·
[arXiv 2605.26128](https://arxiv.org/html/2605.26128v1) *The Constraint Tax* ·
[arXiv 2605.02363](https://arxiv.org/html/2605.02363v1) *When Correct Isn't Usable* ·
[arXiv 2408.02442](https://arxiv.org/abs/2408.02442) *Let Me Speak Freely?* ·
[arXiv 2501.10868](https://arxiv.org/abs/2501.10868) *JSONSchemaBench* ·
[dottxt — Say What You Mean](https://blog.dottxt.ai/say-what-you-mean.html) ·
[Dylan Castillo — Structured outputs can hurt performance](https://dylancastillo.co/posts/say-what-you-mean-sometimes.html)

**Documentación oficial**
[Anthropic — Structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) ·
[OpenAI — Structured model outputs](https://developers.openai.com/api/docs/guides/structured-outputs) ·
[Ollama — Structured outputs](https://docs.ollama.com/capabilities/structured-outputs) ·
[Qwen/Qwen3.6-27B](https://huggingface.co/Qwen/Qwen3.6-27B) ·
[Alibaba Cloud — Qwen structured output](https://www.alibabacloud.com/help/en/model-studio/qwen-structured-output) ·
[Unsloth — MTP](https://unsloth.ai/docs/models/mtp)

**Práctica de producción**
[Microsoft Copilot Studio — Handle errors](https://learn.microsoft.com/en-us/microsoft-copilot-studio/guidance/cux-handle-errors) ·
[AI Error Recovery patterns](https://www.aiuxdesign.guide/patterns/error-recovery) ·
[Claude 4 system prompt (Simon Willison)](https://simonwillison.net/2025/May/25/claude-4-system-prompt/) ·
[SqueezeBits — Guided decoding en vLLM y SGLang](https://blog.squeezebits.com/guided-decoding-performance-vllm-sglang)
