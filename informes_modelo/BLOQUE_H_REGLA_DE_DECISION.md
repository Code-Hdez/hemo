# Bloque H — regla de decisión, escrita antes de medir

**Fecha:** 2026-08-15 · **Pre-registro que la gobierna:** `PUERTAS_v3_PREREGISTRO.md`
**Árbol:** `4cca5683` · **GPU usada: cero** · **VMs:** las tres `TERMINATED`, verificado.

> **Este bloque está DOBLEMENTE condicionado y no se implementa hasta que las dos
> condiciones se cumplan.** Escribirlo ahora no lo adelanta: lo deja listo y con
> la regla sellada, para que cuando lleguen los datos la decisión ya esté tomada.

Toda cifra va marcada `[MEDIDO]`, `[DERIVADO]` o `[INFERIDO]`.

---

## 0. Las dos condiciones, y por qué ninguna se puede saltar

### Condición 1 · F.1 debe decir que Ollama propaga `enum`

`[MEDIDO]` Ollama **no expone GBNF crudo** (`ollama/ollama#11911`, cerrado como
duplicado; `#6237` lista nueve PRs de gramática sin resolver). El único camino es
`format` con JSON Schema. El conversor **de llama.cpp** sí soporta `enum`, `const`
y `pattern` — pero **Ollama tiene su propia ruta Go**, y su documentación no los
menciona.

**Si F.1 dice que no propaga, este bloque no es viable en el motor actual** y la
decisión pasa a ser de arquitectura, con su propio informe de coste y riesgo.
`validacion_llm/scripts/experimento_gramatica.py`, ~10 min.

### Condición 2 · Hay que saber QUÉ ataca, y hasta hoy no se sabía

`[MEDIDO]` H tiene asignada `unsupported_numeric_claim`, 6 fallos. De esos seis,
**cinco eran terminales y llegaron sin parámetro**:

| Pregunta | Ámbito | Parámetro | Desenlace |
|---|---|---|---|
| `HIS-01` | `hemogram_history` | **desconocido** | TERMINAL |
| `HIS-02` | `hemogram_history` | **desconocido** | TERMINAL |
| `HIS-02` | `hemogram_history` | **desconocido** | TERMINAL |
| `HIS-12` | `hemogram_history` | **desconocido** | TERMINAL |
| `SEL-09` | `selected_hemogram` | `hct` | REPARADO |
| `SEL-09` | `selected_hemogram` | **desconocido** | TERMINAL |

`[DERIVADO]` Diseñar una gramática de slots numéricos sin saber qué parámetros
producen los fallos es exactamente el «ir a ciegas» que este proyecto ya pagó
cuatro veces. **Ese hueco ya está cerrado** —`_terminal_error_code` conserva ahora
el detalle— pero el dato **no existe todavía**: hace falta una campaña con la
instrumentación nueva.

> **H no se implementa antes de la primera campaña v3.** Su regla de decisión
> queda sellada aquí; su implementación espera al dato.

---

## 1. El principio, y lo que NO promete

**Si el modelo no puede escribir un número que no esté autorizado, no puede
inventarlo.** No es una instrucción: es una imposibilidad mecánica. Y por eso es
la única vía que queda después de que el eje del prompt quedara agotado.

El modelo emite un objeto pequeño donde cada slot numérico y cada slot de estado
son un `enum` del conjunto autorizado **de este turno**:

```json
{
  "afirmaciones": [
    {"parametro": "WBC", "valor_id": "v_wbc_1", "estado_id": "alto",
     "comentario": "texto libre SIN cifras"}
  ],
  "cierre": "texto libre SIN cifras"
}
```

Y **el servidor ensambla la prosa final**, interpolando los literales
autorizados. El comentario libre es prosa sin cifras: ahí el modelo escribe como
quiera.

**Lo que NO promete, y el GOAL lo dice en I-4:**

> Una gramática garantiza que el modelo escriba `4,52` en vez de `4,25`. **No**
> garantiza que `4,52` sea el eritrocito y no el leucocito. La exactitud
> semántica sigue siendo del modelo.
>
> **Por eso el validador no se retira. Nunca.** Y por eso H no puede sustituir a
> `unsupported_status_claim`, solo reforzarla: el estado sigue siendo una
> elección del modelo entre estados autorizados.

**Respaldo:** *Decode-Time Grammars* (arXiv:2607.18357) demuestra que la
pertenencia a un conjunto dependiente del entorno **exige síntesis de gramática
en tiempo de ejecución**, y mide SQL *execution match* 76 % → 100 % con un coste
de 10,6-17,8 % de throughput. *Trie Automata* (arXiv:2608.12574) mide 0,65 µs por
paso de enmascarado y cita explícitamente *«dynamic per-query constraints from RAG
systems»*, que es este caso.

---

## 2. El riesgo real, que está medido y va contra este bloque

`[MEDIDO en la literatura]` *Capacity, Not Format* (arXiv:2606.09410): la
degradación por formato depende de la capacidad del modelo.

| Modelo | Efecto de restringir el formato |
|---|---|
| Sonnet 4.6 | neutro (88,7 % vs 89,3 %) |
| Haiku 4.5 | **−36,2 pp** |
| GPT-4o-mini | **−28,0 pp** |

**Un 27B en Q4_K_M está en la banda de riesgo**, no en la de Sonnet. Y BAML midió
**−2,3 pp** de exactitud al restringir en una tarea de parsing.

**Mitigación pre-declarada:** **no meter el razonamiento en JSON, solo los
slots.** Prosa libre por defecto; restricción únicamente donde va una cifra o un
estado. Es la forma híbrida que *CRANE* (arXiv:2502.09061) propone tras demostrar
colapso de expresividad bajo restricción total.

`[DERIVADO]` **Y hay un contrapeso a favor que no es intuitivo:** restringir puede
salir **más barato** que reparar. El *jump-forward decoding* de SGLang hace
prefill directo de los tramos deterministas sin muestrear —hasta 2× menos
latencia—, y el sobrecoste por token del enmascarado es de microsegundos sobre un
decode de 25-40 ms. `[MEDIDO]` Frente a eso, una segunda llamada cuesta **×2,20**
de latencia medido en esta campaña. Tres o cuatro órdenes de magnitud a favor de
la gramática.

---

## 3. Y un aviso que sale de este proyecto, no de la literatura

`[MEDIDO]` **HemoVet ya tuvo un contrato estructurado y lo retiró midiendo.** El
«sobre» (`CHAT_STRUCTURED_OUTPUT_ENABLED=1`) perdió contra el contrato mínimo en
todos los ejes el 13-ago:

| | sobre activo | contrato mínimo |
|---|---|---|
| validez de 1.ª pasada | 75,56 % | **89,47 %** |
| `provider_calls` | {1:34, **3:11**} | {1:34, 2:4} |
| p50 | 17,12 s | **10,02 s** |
| p95 | 48,63 s | **17,14 s** |

> **H no es «volver al sobre».** El sobre pedía al modelo `intent`,
> `response_type`, `claim_id`, `fact_ids`, `source_ids`, `policy_rule_ids`,
> `evidence_spans` y banderas de seguridad — metadatos que el servidor ya sabe, y
> que I-3 del GOAL anterior prohíbe expresamente. H pide **exactamente dos cosas**:
> qué valor autorizado y qué estado autorizado. Todo lo demás sigue siendo prosa.
>
> **Pero el precedente obliga a medir la latencia y las llamadas, no solo la
> validez.** Un H que arregle `unsupported_numeric_claim` y devuelva el p95 a los
> 48 s es un fracaso, y su regla lo dice.

---

## 4. La regla, decidida antes de ver el resultado

| Resultado | Decisión |
|---|---|
| `unsupported_numeric_claim` cae a **0** y el total de fallos de contrato baja | **Se conserva** |
| Cae a 0 pero **sube otra clase** y el total no mejora | **Se revierte.** Cambiar un rechazo por otro no es una mejora |
| **No cae a 0** | **Se revierte.** El mecanismo era «imposibilidad mecánica»: si el modelo sigue escribiendo cifras no autorizadas, la premisa es falsa y hay que rehacerla, no ajustarla |
| Cae, pero **p50 > 15 s o p95 > 25 s** | **Se revierte.** Son los dos criterios de latencia que el contrato mínimo ya había conquistado; H no los gasta |
| Cae, pero `provider_calls` medio **sube** | **Se revierte.** H existe para acercar `provider_calls == 1`, no para alejarlo |
| Cae, pero la revisión veterinaria ciega califica las respuestas **peores** | **Se revierte.** Es el riesgo de *Capacity, Not Format* materializándose, y una respuesta que pasa el validador y no sirve no es una mejora |

**n de la medición:** el plan v3 completo, **400 turnos**. Y se publican, además
de la validez, **la latencia p50/p95 y la distribución de `provider_calls`**,
porque el precedente del sobre dice que ahí es donde este tipo de cambio se paga.

---

## 5. Lo que este bloque NO hace

- **No retira el validador.** Ni una comprobación, ni para los slots restringidos.
- **No mete el razonamiento en JSON.** Solo los slots numérico y de estado.
- **No reintroduce el sobre.** Nada de `intent`, `claim_id`, `fact_ids`,
  `source_ids`, `policy_rule_ids` ni banderas de seguridad: el servidor ya lo sabe.
- **No se implementa antes de F.1** ni **antes de la primera campaña v3** con la
  instrumentación del detalle terminal.

## Hipótesis vivas

1. **Qué parámetros producen los 5 `unsupported_numeric_claim` terminales.** Ya
   instrumentado; falta la campaña.
2. **Si un 27B en Q4 sufre la degradación de *Capacity, Not Format*** con
   restricción parcial, o solo con la total. La literatura mide la total.
3. **Si el `enum` por turno es barato de compilar en Ollama.** F.1 lo mide con un
   `enum` de 300 valores frente a uno de 3.
