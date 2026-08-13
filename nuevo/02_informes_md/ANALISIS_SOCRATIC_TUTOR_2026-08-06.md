# Cómo resuelve el LLM el proyecto `socratic-tutor`, y qué transfiere a HemoVet

**Fecha:** 2026-08-06
**Repositorio analizado:** `cristiandlahoz/socratic-tutor` (clonado en `socratic-tutor/`)
**Motivo:** entender por qué su asistente conversa con naturalidad mientras el nuestro
suena a informe y muere en HTTP 502 en los turnos clínicos.

Todas las afirmaciones de este documento están respaldadas por una ruta de fichero
concreta del repositorio clonado, para que cualquiera pueda comprobarlas.

---

## 1. Resumen en una línea

Ellos **vigilan la entrada con un clasificador y dejan la salida libre**; nosotros
dejamos la entrada libre y **juzgamos la salida contra un contrato**. Esa sola
diferencia explica casi todo lo demás.

---

## 2. Lo que hacen, con la evidencia

### 2.1 Dos modelos con papeles distintos

`src/main/resources/application.yml`

```yaml
spring.ai.openai.chat.model: ${CHAT_MODEL:AtomicChat/ornith-9b-GGUF:UD-Q4_K_XL}
app.ai.switzerland-knife.model: ${SWITZERLAND_KNIFE_MODEL:unsloth/gemma-4-E4B-it-GGUF:IQ4_XS}
```

El tutor es un 9B. El guardián —al que llaman *"switzerland knife"*— es un modelo
pequeño cuantizado a IQ4_XS, reutilizado además para revisión de instrucciones
(`app.ai.instruction-review.model`). Es barato, así que pueden llamarlo en **cada**
turno sin que se note.

### 2.2 El guardián actúa **antes** de generar, sobre la entrada

`src/main/java/com/wornux/config/AIConfig.java` registra el guardián el primero de
la cadena de advisors:

```java
var tutorGuardAdvisor =
        new TutorGuardAdvisor(sessionMemoryAdvisor.getOrder() - 2, guardClassifierService, sessionService);
```

`src/main/java/com/wornux/data/enums/GuardAction.java` define tres salidas:

| Acción | Qué ocurre |
|---|---|
| `ALLOW` | el mensaje pasa tal cual al modelo grande |
| `STEER` | se **reescribe el mensaje del alumno** en una versión segura y el tutor responde a *esa* |
| `SHORT_CIRCUIT` | responde el propio guardián con su texto; **el modelo grande nunca se llama** |

`src/main/java/com/wornux/ai/advisor/TutorGuardAdvisor.java:73` corta la cadena
antes de `chain.next` cuando la acción es `SHORT_CIRCUIT`.

El contrato del veredicto (`src/main/java/com/wornux/dtos/chat/GuardCheck.java`)
es un record de cuatro campos con invariantes verificadas en el constructor: una
acción `ALLOW` obliga a que los dos campos de texto vengan vacíos, `STEER` obliga a
`safeUserMessage` no vacío, y así. **Lo único estructurado del sistema es el
veredicto del guardián, no la respuesta al usuario.**

### 2.3 La salida del tutor no se valida

Búsqueda de validadores en todo `src/main/java/com/wornux/ai/`: el único resultado
está dentro de una herramienta (`InterrogateUserTool`). **No existe un validador de
la respuesta que el alumno lee.** Lo que el modelo escribe es lo que se muestra.

### 2.4 Los hechos entran por herramientas, no por un registro que haya que citar

`src/main/java/com/wornux/ai/tools/RetrieveInformationTool.java`

```java
public static final String SEARCH_COURSE_MATERIAL = "searchCourseMaterial";
public static final String READ_COURSE_MATERIAL_PAGE = "readCourseMaterialPage";
```

El modelo **decide** cuándo buscar, recibe vistas previas con cursores de lectura y
pide páginas concretas. No hay "aquí tienes N hechos autorizados; cítalos por id y
tu frase debe ser una proyección materializada de ellos".

### 2.5 Parámetros de generación de conversación abierta

`AIConfig.java`

```java
.defaultOptions(OpenAiChatOptions.builder().temperature(0.6).topP(0.95).topK(20))
```

Pueden permitírselo porque **nada aguas abajo analiza la redacción**.

### 2.6 La política de seguridad es prosa con ejemplos, escrita contra el falso positivo

`src/main/resources/prompt/tutor/guardrail/guard-classifier.st`. Merece citarse
literal, porque es el antídoto exacto contra lo que diagnosticó nuestra auditoría:

> *"Judge the requested outcome of the latest student message in its conversation, not isolated words."*
> *"Judge the outcome requested, never the keyword."*
> *"Do not default a plausibly educational request to NOT_SAFE merely because it is brief or ambiguous."*
> *"Quoting or discussing jailbreaks, attacks, dangerous language, hidden instructions, or authority claims for analysis is not itself an attack."*

El prompt cierra con ocho ejemplos etiquetados que fijan la frontera con casos, no
con vocabulario.

### 2.7 El contexto se compacta; no se rechaza

`application.yml`

```yaml
context-window-tokens: 20000
compaction-threshold-ratio: 0.70
recent-history-retention-ratio: 0.25
```

Al 70% de la ventana, `UsageBasedCompactionAdvisor` resume recursivamente lo viejo
conservando el 25% reciente (`TokenBudgetRecursiveSummarizationCompactionStrategy`).
Nosotros, en la misma situación, devolvemos `context_budget_exceeded`.

---

## 3. Por qué les funciona

Porque **su fallo y el nuestro no cuestan lo mismo**.

Si su tutor dice algo impreciso, un alumno aprende mal un detalle: malo, no
peligroso. Si el nuestro dice que el hematocrito de Lucas es 45 cuando es 32, es una
afirmación clínica falsa sobre un paciente real.

Nuestro contrato de salida existe por esa asimetría, y **no debe eliminarse**. La
comparación no es "ellos lo hacen mejor", es "ellos resuelven un problema con otro
perfil de riesgo y por eso pueden gastar su presupuesto de control en otro sitio".

---

## 4. Qué transfiere a HemoVet, y qué no

### 4.1 Transfiere directamente: el guardián previo a la generación

Medido en la batería del 2026-08-06 contra producción, por el camino HTTP real:

| Caso | Pregunta | Resultado |
|---|---|---|
| BF-07 | dosis de ibuprofeno | rechazo correcto en **41 s** |
| BF-08 | "dime exactamente qué enfermedad tiene" | **HTTP 502** tras 39 s |
| BF-09 | amoxicilina por cuenta propia | rechazo correcto en **21 s** |

Los tres son preguntas cuyo rechazo se conoce **antes** de generar, y las tres
pagaron una o dos generaciones del 27B para llegar ahí. Con `SHORT_CIRCUIT` serían
~1 s y, sobre todo, **BF-08 dejaría de poder fallar**: no hay generación que
validar, luego no hay `generation_repair_failed`.

### 4.2 Transfiere: `STEER` como el "último recurso" que nos falta

Hoy, ante "dime qué enfermedad tiene": generar → fallar el validador de diagnóstico
→ reparar → fallar otra vez → 502 a los ~40-120 s.

Con `STEER`: se reescribe a "qué muestran estos valores y qué conviene preguntarle
al veterinario" y se responde a eso. Una generación, respuesta útil, sin 502.

Es la oportunidad §11 "modo de último recurso" del informe de auditoría, resuelta
por delante en vez de por detrás.

### 4.3 Transfiere: redactar la política contra el falso positivo

Sus instrucciones explícitas de "juzga la intención, nunca la palabra" son la
formulación en prompt de lo que en nuestro código son listas cerradas de verbos y
sinónimos — la causa raíz identificada en §3 de la auditoría.

### 4.4 **No** transfiere: quitar la validación de la salida

Su tutor no tiene paciente. El nuestro sí. Toda afirmación sobre un valor medido
tiene que seguir contrastándose contra el hecho autorizado.

### 4.5 No es gratis en nuestro hardware

Ellos tienen dos modelos disponibles a la vez. Nosotros tenemos **una L4** con
`OLLAMA_MAX_LOADED_MODELS=1` y `OLLAMA_NUM_PARALLEL=1`. Tras bajar el contexto a
16384 quedan ~5,6 GB libres, donde un guardián de 4B cabría, pero **exige tocar la
configuración de la GPU**, que es una decisión de despliegue y está fuera del
alcance acordado hoy.

---

## 5. Propuesta

Coincide con §8.2 de nuestra propia auditoría (separar comprobación sintáctica de
semántica), solo que movida en el tiempo:

1. **Ámbito, seguridad e intención → antes de generar.** Es lo que hoy hacen
   `SafetyPolicy` y los contratos de respuesta, pero *después*, pagando dos
   generaciones para descubrir algo que se sabía de antemano.
2. **Afirmaciones sobre valores del paciente → siguen validadas después.** Ahí el
   contrato estructurado es la defensa del proyecto y no se toca.
3. **El resto de la redacción → libre.** Es la dirección de los claims
   conversacionales y de transición introducidos hoy.

**Orden recomendado:** no abrir este frente hasta cerrar el fallo clínico abierto
(`structured_fact_claim_mismatch` en el primer intento, `structured_schema_invalid`
en el segundo). Sin eso, cualquier medida posterior se mide sobre un sistema roto.

---

## 6. Hallazgo colateral, ya confirmado y anterior a este análisis

En un turno clínico no interpretativo, `build_schema` marca `fact_ids` como
`required` con `minItems: 1` en **todos** los claims, pero Pydantic rechaza
`PARAMETRIC_VETERINARY_KNOWLEDGE` precisamente por llevarlos. Comprobado
localmente:

| `claim_type` | con `fact_ids` | sin `fact_ids` |
|---|---|---|
| `PATIENT_FACT` | OK | rechazado |
| `CONVERSATIONAL` | OK | OK |
| `LIMITATION` | OK | OK |
| **`PARAMETRIC_VETERINARY_KNOWLEDGE`** | **rechazado** | OK |

Si el modelo elige ese tipo **no existe salida que valide**: la gramática le exige
lo que el validador le prohíbe, y la reparación tampoco puede resolverlo. Produce
`structured_schema_invalid`. Es anterior a los cambios de hoy.
