# Diagnóstico del sistema LLM de HemoVet

**Documento de diagnóstico, no de resumen.** Se basa exclusivamente en las
mediciones producidas por las Fases 1, 2 y 3 del agente, más investigación
externa nueva realizada para este documento. Todo lo que es inferencia mía está
marcado como tal.

Fecha: 8 de agosto de 2026
Alcance: causa de la latencia + causa de los fallos de generación
Estado del sistema: no modificado

---

## 0. Conclusión en un párrafo

HemoVet no tiene un problema de latencia. Tiene **dos multiplicadores
independientes sobre una constante lenta**, y el agente sólo ha investigado uno
de ellos a fondo. La constante es el coste de decodificar una respuesta
(~28,7 s). El primer multiplicador es el **número de tokens que el sistema
decide generar por llamada** (375 de mediana — nunca se ha examinado qué
contienen). El segundo es el **número de llamadas por pregunta** (1 en la mitad
de los turnos, 2,85 en la otra mitad). El motivo por el que sientes que no te
está dando una respuesta directa es que el agente ha estado respondiendo
*"decode es el 88 %"*, que es una descripción, no una causa. La causa es que el
sistema genera aproximadamente **794 tokens por pregunta útil para entregar
unos 200**, a 13 tokens por segundo.

---

## 1. La respuesta directa: el modelo cerrado de la latencia

Esto es lo que faltaba en las tres fases. Con los números que el propio agente
midió, la latencia de HemoVet se describe por completo con **una sola ecuación
de dos variables**. La he reconstruido y verificado contra las medianas
observadas.

### 1.1 Los ingredientes medidos

| Magnitud | Valor | Origen |
|---|---|---|
| Velocidad de decode | 13,05 tok/s (pipeline), 13,04–13,71 tok/s (directo) | Fase 2, medición directa contra Ollama |
| Tokens de salida por llamada (mediana) | 375 | `eval_count` |
| Prefill total | ~568 s sobre 133 llamadas → **4,3 s/llamada** | Fase 1/2 |
| Llamadas totales | 133 | telemetría correlacionada |
| Turnos sin reparación | 36 | 70 − 34 |
| Llamadas en turnos con reparación | 97 | `TABLA_REPAIRS_COMPLETA.csv` |

### 1.2 La ecuación

```
T(turno) = N_llamadas × (T_prefill + T_decode) + overhead_fijo
         = N_llamadas × (4,3 s + 375/13,05 s) + ~1,8 s
         = N_llamadas × 33,0 s + 1,8 s
```

### 1.3 La verificación — y por qué esto importa

| Caso | N_llamadas | Predicción del modelo | Mediana medida | Error |
|---|---|---|---|---|
| Turno sin reparación | 1,00 | **34,8 s** | 34,8 s | 0,0 % |
| Turno con reparación | 97/34 = **2,85** | **95,9 s** | 98,1 s | 2,2 % |

El modelo predice ambas medianas con un error inferior al 3 %. **No queda
latencia sin explicar.** No hay un componente oculto, no hay contención, no hay
cola, no hay un backend lento. El sistema hace exactamente dos cosas: espera
prefill y espera decode, tantas veces como llamadas realice.

Y aquí está la conclusión que ninguna de las tres fases enunció:

> La latencia de HemoVet tiene **exactamente tres palancas**, y son
> multiplicativas entre sí:
> **(1)** tokens generados por llamada · **(2)** número de llamadas por
> pregunta · **(3)** velocidad de decode.
> El agente investigó a fondo la (2), cerró prematuramente la (3), y
> **nunca midió la (1)**.

### 1.4 Corrección importante a cómo se ha venido presentando el problema

El agente repite "1,9 llamadas al modelo por pregunta". Ese promedio es
engañoso y creo que ha desviado la investigación. La realidad es **bimodal**:

```
51,4 % de los turnos  →  1 llamada    →   34,8 s
48,6 % de los turnos  →  2,85 llamadas →   98,1 s
```

No existe ningún turno de 59 s. La mediana global de 59,1 s es un artefacto
estadístico de dos poblaciones separadas. Lo que el usuario experimenta es
*"a veces medio minuto, a veces minuto y medio, y una de cada cuatro veces nada
en absoluto"*. Esa varianza —no la media— es lo que hace que el producto se
perciba como roto.

---

## 2. El agujero de medición más grande de las tres fases

**Nadie ha abierto los 375 tokens.**

El sistema no genera prosa clínica. Genera un `GeneratedResponseEnvelope`: un
objeto JSON con `claims`, cada uno con `claim_id`, `text`, `claim_type`,
`policy_rule_ids`, `fact_ids`, `source_ids`, `evidence_spans`, más metadatos
globales. El texto que el veterinario acaba leyendo es sólo el campo `text` de
cada claim.

En la Fase 1 el propio agente registró que el sobre JSON de una respuesta medía
**924 caracteres**, y usó ese dato para *descartar* thinking. Pero nunca hizo la
pregunta inversa, que es la importante:

> De los 375 tokens que el modelo decodifica a 13 tok/s, **¿cuántos son
> contenido clínico visible y cuántos son andamiaje estructural?**

Esto importa porque el tiempo de decode es **estrictamente lineal** en el número
de tokens. Cada token de metadato cuesta exactamente lo mismo que un token de
diagnóstico: 76,6 milisegundos.

Aritmética de la magnitud en juego (inferencia mía, pendiente de medición):

| Escenario | Tokens de andamiaje | Segundos/llamada gastados en metadatos |
|---|---|---|
| Sobre ligero | 100 de 375 (27 %) | 7,7 s |
| Sobre medio | 175 de 375 (47 %) | 13,4 s |
| Sobre pesado | 250 de 375 (67 %) | 19,2 s |

Sobre 133 llamadas, el escenario medio equivale a **~29 minutos de GPU** en la
batería completa dedicados a emitir identificadores y llaves JSON. Y a
diferencia de la reparación —que sólo afecta al 48,6 % de los turnos— esto
afecta al **100 %** de las llamadas, incluidas las que van bien.

**Esta es, en mi opinión, la medición individual de mayor valor que queda
pendiente, y es completamente observable hoy**: las respuestas exitosas sí están
persistidas. No requiere tocar producción, no requiere `CHAT_STRUCTURED_DEBUG_DIR`,
no requiere reiniciar nada. Es tokenizar lo que ya está guardado.

---

## 3. Las cinco causas, ordenadas por segundos aportados

### CAUSA 1 — Volumen de salida × velocidad de decode
**Contribución: ~28,7 s en cada una de las 133 llamadas. Es el 100 % de la base.**

Dos subcomponentes, y sólo uno se ha investigado:

- **Velocidad (13,05 tok/s)**: medida tres veces por vías independientes. Sólida.
- **Volumen (375 tokens)**: medido pero **jamás descompuesto ni cuestionado**.

Estado: `CONFIRMADO` en la velocidad, `NO_MEDIDO` en la composición del volumen.

### CAUSA 2 — Desajuste entre el contrato que se impone y el contrato que se juzga
**Contribución: +63,4 s en el 48,6 % de los turnos. 1.989 s (40,3 %) del total.**

Éste es el hallazgo real de la Fase 3, y es correcto:

```
JSON Schema enviado como `format`
  GeneratedClaim.required = [claim_id, text, claim_type]
  policy_rule_ids / fact_ids / source_ids / evidence_spans
      → default_factory=list  →  NO required
                ↓
La gramática permite legítimamente  policy_rule_ids: []
                ↓
structured_response.py:140  →  `} and not self.policy_rule_ids:`
   exige el campo, pero SÓLO para ciertos claim_type
                ↓
Condición inexpresable en JSON Schema plano
                ↓
El modelo cumple el contrato que se le impone
y falla el contrato con el que se le juzga
```

Estado: `CONFIRMADO` por lectura de código y schema.

### CAUSA 3 — Arquitectura de rescate y reparación estructuralmente incapaz
**Contribución: convierte la Causa 2 en 17 fallos totales en lugar de 17 respuestas parciales.**

Tres defectos encadenados, todos confirmados en código:

1. **El salvage no puede salvar nada cuando hay un solo claim.**
   `if not kept: raise first_rejection`. Con `materialized_fact_count = 1`,
   `kept` está vacío por construcción. El mecanismo existe pero es inaplicable
   justo en el caso más común.
2. **La reparación no aporta información nueva.** El prompt de repair crece un
   **+2,48 %** de mediana. Se le vuelve a pedir al modelo que genere 375 tokens
   sin decirle prácticamente nada que no supiera. 11 de 19 repiten el mismo
   detalle de error.
3. **La reparación regenera el sobre completo** para corregir la ausencia de una
   cadena de ~20 tokens. Coste: ~29 s de GPU para insertar un identificador que
   el backend ya conoce.

Estado: `CONFIRMADO`.

### CAUSA 4 — La latencia percibida es igual a la latencia total
**Contribución: no añade segundos, pero es la que convierte la latencia en un problema de producto.**

Esto no aparece en ninguna de las tres fases y creo que es un fallo de encuadre
importante. Un pipeline *generar → validar → reparar* es **estructuralmente
incompatible con el streaming**: no puedes emitir al usuario tokens que todavía
podrías rechazar. Por tanto:

```
TTFB útil ≈ latencia total
```

El usuario no espera 35 s viendo texto aparecer. Espera 35 s —o 98 s— viendo
nada. Un sistema que streamea a 13 tok/s se percibe como "lento pero vivo". Uno
que entrega en bloque a los 98 s se percibe como "colgado".

El transcript lista TTFB entre las magnitudes a revalidar, pero **el valor nunca
se reporta en ninguna de las tres fases**. Es una omisión llamativa.

Estado: `HIPÓTESIS FUERTE` — se deduce de la arquitectura, falta confirmar con
el dato de TTFB que ya existe en la telemetría.

### CAUSA 5 — Router determinista con falsos negativos de ámbito
**Contribución: 0 s de latencia. Pero produce rechazos de preguntas obviamente del dominio.**

Clasificador regex con confianzas fijas 0,96–0,99. Una pregunta como
*"¿En qué puedes ayudarme con un hemograma canino?"* recibe *"no puedo determinar
si pertenece al ámbito"*. Es un defecto independiente y no debe mezclarse con el
validador de claims.

Estado: `CONFIRMADO`.

---

## 4. Auditoría de las tres fases: qué se concluyó mal y por qué

Esto es relevante porque explica el patrón de fallo del agente, y ese patrón
condiciona cómo debes configurarlo en la siguiente fase.

| # | Afirmación | Fase | Qué pasó | Lección |
|---|---|---|---|---|
| 1 | "El prompt se reprocesa entero cada turno" | 1 | Refutado por los logs de `llama-server` en Fase 1 misma | Confundió *crecimiento del prompt* con *ausencia de caché* |
| 2 | "El claim salvage no está conectado — mitigación P0" | 1 | Refutado en Fase 2: está desplegado desde el principio | Leyó un mensaje de commit en vez del código en `HEAD` |
| 3 | "Los fallos son semánticos, no estructurales, porque `format` está activo" | 2 | Refutado en Fase 3 al abrir el schema | Dedujo de la *existencia* de una feature su *cobertura* |
| 4 | "13,7 tok/s es el 77 % del máximo físico; no queda margen" | 2 | Retirado en Fase 3 tras evidencia upstream | Confundió un roofline aritmético con un límite alcanzable |
| 5 | "La única incógnita restante es X" | 1, 2 y 3 | Falso en las tres ocasiones | Patrón sistemático de cierre prematuro |
| 6 | "MTP daría 1,71×" | 2 | Sigue sin sustento para este stack | Extrapolación de otra GPU y otro engine |

**El patrón es único y se repite:** el agente concluye a partir de la existencia
de un mecanismo en lugar de a partir de su comportamiento medido. Encuentra
`format` → concluye que la gramática cubre el contrato. Encuentra
`_claim_rejection` → concluye que el salvage funciona. Encuentra un número de
ancho de banda → concluye que no hay margen.

**La instrucción operativa que se deriva de esto**, y que va incorporada en el
prompt de Fase 4: *ningún mecanismo cuenta como investigado hasta que exista una
medición de su cobertura real, no de su presencia en el código.*

---

## 5. Hipótesis nuevas surgidas de la investigación externa

Estas tres no aparecen en ninguna de las tres fases y salen de la búsqueda
realizada para este documento. Las dos primeras son, en mi valoración, las más
prometedoras que quedan sobre la mesa.

### H-NEW-1 — La gramática podría no estar aplicándose en absoluto (CRÍTICA)

Cadena de razonamiento:

1. HemoVet envía `payload["format"] = GeneratedResponseEnvelope.model_json_schema()`.
   *(confirmado en Fase 2, `openai_compatible_client.py:751`)*
2. Pydantic genera **`$defs` y `$ref` por defecto para modelos anidados** —y
   `GeneratedResponseEnvelope` contiene `GeneratedClaim` anidado.
   *(documentado por Pydantic; issue #12232)*
3. llama.cpp tiene un fallo documentado por el cual un `json_schema` con
   `$ref`/`$defs` **falla en silencio**: el servidor devuelve HTTP 200 y
   **cae a generación no restringida**, sin notificar al cliente. Los síntomas
   descritos literalmente son: *"campos requeridos ausentes por completo"*,
   *"nombres de campo que no están en el schema"*, *"ningún error devuelto al
   cliente"*, y sólo una línea en los logs del servidor delata el problema.
   *(llama.cpp issue #21228)*
4. Los síntomas de HemoVet son **exactamente ésos**: campos ausentes, sin error,
   fallo determinista.

Si esto se confirma, reordena todo el diagnóstico:

- Explica por qué la reparación falla **0 de 9 veces** y por qué **bajar la
  temperatura a 0,1 no cambia nada** — la temperatura es irrelevante si el
  problema no es de muestreo.
- Explica por qué el modelo omite campos que "debería" saber que necesita.
- Y explica parte del volumen de salida: sin gramática, la generación es libre y
  tiende a ser más larga.

Contra-evidencia que hay que reconciliar: la Fase 2 midió que la gramática cuesta
un −5 % de velocidad, lo que sugiere que *algo* se está aplicando. Pero ese
experimento pudo usar un schema plano, no el anidado real. **Hay que repetirlo
con el schema exacto de producción.**

**Verificación: trivial, gratuita y sin riesgo.** Volcar el JSON exacto que se
envía y comprobar si contiene `$defs`/`$ref`; y hacer `grep` en los logs de
`llama-server` buscando el mensaje de fallo de gramática. Minutos de trabajo.

Estado: `HIPÓTESIS PRIORITARIA — NO VERIFICADA`.

### H-NEW-2 — En una L4 el cuello no es el ancho de banda, es el kernel de decuantización

Un estudio cruzado de 44 celdas sobre decode en batch-1 mide que **la L4 alcanza
~81 % de su ancho de banda pico** — lo que corrobora el 77 % de HemoVet y valida
esa parte del análisis del agente. Pero el mismo estudio demuestra que en la L4
**el factor limitante no es el ancho de banda sino la calidad del kernel de
decuantización**, con una dispersión enorme sobre el mismo modelo y la misma GPU:

| Configuración en L4 | ms por paso de decode |
|---|---|
| bf16 (baseline) | 62,32 |
| bnb-nf4 | 59,36 |
| AutoAWQ + Marlin | 45,24 |
| GPTQ + ExLlamaV2 | **17,36** |

Un factor **3,6×** entre formatos de cuantización sobre hardware idéntico. La
conclusión de los autores es que *"el ahorro de memoria sólo importa cuando el
runtime lo materializa"*.

Esto **refuta definitivamente** el "no queda margen" de la Fase 2, y sitúa el
emparejamiento *formato de cuantización × kernel × engine* como una palanca de
primer orden **específicamente en L4**, no como una optimización marginal.

Salvedad honesta: el estudio usa Qwen-2.5-7B denso, no un híbrido de 27B, y los
kernels Q4_K_M de llama.cpp son razonablemente buenos. **No es una promesa de
3,6×.** Es la demostración de que la pregunta sigue abierta.

Estado: `HIPÓTESIS EXPERIMENTAL — refuta un cierre previo`.

### H-NEW-3 — Flash Attention y KV-quant probablemente no están disponibles para esta arquitectura

La lista de arquitecturas con soporte de Flash Attention en Ollama es explícita
(Gemma3, GPT-OSS, Mistral3, Qwen3/Qwen3MoE, Qwen3VL). Qwen3.6 es **híbrido**
—16 × (3 × Gated DeltaNet → 1 × Gated Attention), 64 capas— y no figura en esa
lista. Y cuando FA no está disponible, **el sistema cae en silencio a f16** sin
avisar.

Consecuencia práctica: dos de las optimizaciones de serving que uno probaría
primero puede que sencillamente no existan para este modelo. Hay que
comprobarlo antes de perder tiempo con ellas — y si es así, es un argumento a
favor de evaluar otro engine, no otra bandera de configuración.

Estado: `HIPÓTESIS — verificable con `ollama ps` y los logs de carga`.

### Nota de corrección sobre MTP

El "1,71×" que el agente citó no debe seguir apareciendo como estimación. La
evidencia real es contradictoria y **depende del engine, no del modelo**:

- Qwen3.6 con MTP en llama.cpp sobre Ampere: **pérdida neta del 3–12 %**, incluso
  con tasa de aceptación del 100 %, por sobrecoste de verificación.
- El mismo modelo con MTP de vLLM: **+27,5 %** de decode.

Conclusión: MTP es `NEEDS_BENCHMARK`, y el benchmark que importa es
*engine-específico*. No es una mitigación priorizable todavía.

---

## 6. Lo que sigue siendo NO_OBSERVABLE — y por qué el agente se equivocó al declararlo bloqueado

La incógnita central sigue siendo la misma:

> ¿La generación descartada era clínicamente correcta?

Las dos ramas llevan a proyectos completamente distintos:

```
RAMA A — el contenido era correcto
   → el validador destruye trabajo bueno por un metadato
   → el 40,3 % de la latencia es puro desperdicio
   → la solución es alinear schema y validador, o rellenar el metadato de forma determinista

RAMA B — el contenido era clínicamente incorrecto
   → el validador está protegiendo al usuario correctamente
   → el problema está antes: grounding, construcción de contexto, RAG
   → tocar el validador sería peligroso
```

**El agente concluyó que resolver esto exige encender `CHAT_STRUCTURED_DEBUG_DIR`,
recrear el contenedor y aceptar una ventana de caída. Eso es un falso dilema, y
es el error estratégico más costoso de las tres fases.**

Tienes todo lo necesario para reproducir el fallo **fuera de producción**:

| Ingrediente | Disponible |
|---|---|
| El modelo exacto, sellado por digest | Sí — `sha256:96367c03…` |
| El schema exacto | Sí — `GeneratedResponseEnvelope.model_json_schema()` |
| El validador exacto | Sí — `structured_response.py`, importable en solo-lectura |
| El código que construye el prompt | Sí — `HEMOVET_BUILD_REVISION == HEAD` |
| Las 70 preguntas y sus contextos clínicos | Sí — en los artefactos de la batería |
| Un Ollama funcionando con ese modelo cargado | Sí |

Con eso se construye un **arnés de repetición externo al repositorio** que
reconstruye la llamada, la ejecuta contra el mismo Ollama, y **captura el output
crudo que producción tira a la basura** — sin modificar una sola línea de
HemoVet, sin reiniciar nada, sin ventana de caída.

Después se importa el validador y se le pasa ese output capturado. Eso resuelve
la bifurcación A/B de forma definitiva.

**Ésa es la Fase 4.** No es "seguir investigando los mismos logs". Es dejar de
buscar evidencia que no existe y empezar a **fabricarla en un entorno
controlado**.

---

## 7. Veredicto: ¿debes seguir preguntando?

**Sí, pero exactamente una fase más, y de naturaleza distinta a las tres
anteriores.**

Las Fases 1–3 fueron *observacionales*: leer logs, leer código, correlacionar
telemetría. Ese pozo está seco — la Fase 3 agotó cinco vías y obtuvo cero
coincidencias. Pedir una Fase 4 observacional produciría otro informe elegante
sin la pieza que falta.

La Fase 4 debe ser **experimental y reproductiva**: fabricar en un arnés externo
la evidencia que producción no conserva.

Y después de la Fase 4, para y decides. Concretamente:

- Si el arnés reproduce el fallo → **tienes la causa raíz completa** y pasas a
  diseño de la corrección. Se acabó la investigación.
- Si el arnés **no** reproduce el fallo → eso también es información de primer
  orden: significa que la diferencia está en el estado de producción
  (conversación, caché, contexto acumulado), y entonces sí está justificada la
  ventana controlada para `CHAT_STRUCTURED_DEBUG_DIR`, con una hipótesis muy
  concreta que comprobar.

En ninguno de los dos casos hace falta una Fase 5 de investigación general.

### Lo que ya puedes dar por cerrado y no debes volver a preguntar

- Thinking → descartado experimentalmente. **Cerrado.**
- Caché de prefijos → funciona, ahorra el 24,2 % del prefill. **Cerrado.**
- GPU/offload/cola → limpio, 133/133 en GPU completa. **Cerrado.**
- Trazabilidad código↔producción → cerrada vía `HEMOVET_BUILD_REVISION`.
- Truncación → 2 de 138. **Irrelevante.**
- Compresión de historial / optimización de RAG → techo del 8,7 %. **No es la
  palanca; no dediques más esfuerzo aquí.**

### Lo que debe seguir abierto

1. Composición de los 375 tokens de salida ← **la mayor palanca no medida**
2. ¿Se está aplicando realmente la gramática? ← **H-NEW-1**
3. Contenido crudo de la primera generación ← vía arnés externo
4. Margen real de serving en L4 ← **H-NEW-2**, con el cierre previo ya retirado
5. TTFB / latencia percibida ← dato existente nunca reportado
6. Router de ámbito ← defecto independiente y confirmado

---

## 8. Cómo configurar al agente para la Fase 4

### Por qué termina antes de tiempo

En el transcript aparece `Goal achieved (11m · 1 turn · 50.9k tokens)` tras una
tarea que exigía una investigación forense completa. La causa es estructural: el
evaluador del goal **sólo juzga lo que aparece en la conversación**; no abre
ficheros ni ejecuta comandos por su cuenta. Un goal redactado como *"investiga
exhaustivamente y produce un informe"* se satisface con que el agente **afirme**
haberlo hecho.

La corrección no es pedirle que trabaje más tiempo. **La duración no es un
criterio de calidad**: un agente puede gastar una hora releyendo lo mismo. La
corrección es poner **puertas de evidencia**: condiciones que sólo se pueden
declarar cumplidas exhibiendo en el transcript un artefacto concreto —una ruta,
un comando, una salida, un conteo.

### Configuración recomendada

| Parámetro | Valor | Motivo |
|---|---|---|
| Modelo | El de mayor capacidad de razonamiento disponible en tu cuenta | Es una tarea de depuración causal larga |
| Goal | Sí, pero *default-FAIL* con checklist visible | Ver arriba |
| Límite | Máximo 30 turnos / 150 min. **Sin mínimo de tiempo** | Las puertas son el criterio, no el reloj |
| Permisos | `dontAsk` con allowlist estrictamente de lectura | Deniega por defecto lo no preautorizado |
| `bypassPermissions` | **No** | Hay producción de por medio |
| Escritura | Sólo fuera del worktree, en el directorio de investigación | Ya funciona bien así |
| Repositorio | Lectura | |
| Producción | Lectura + peticiones de diagnóstico no destructivas | El arnés necesita llamar a Ollama |
| Web | Obligatoria, con cuota mínima de fuentes primarias | |

Sobre el allowlist: evita comodines amplios del tipo `ssh ... --command=*`,
porque convierten SSH en una vía para ejecutar cualquier cosa en producción. Si
necesita mucho SSH, es preferible modo `default` con aprobación manual de cada
comando de lectura.

### Una advertencia operativa que debes trasladarle

El arnés de repetición llama al **mismo Ollama que sirve a producción**. Eso es
aceptable —son peticiones del mismo tipo que las que ya recibe— **con una
condición crítica**: debe usar exactamente el mismo nombre de modelo y las
mismas opciones de carga. Si pide un `num_ctx` distinto o un modelo distinto,
Ollama **descargará y recargará el modelo**, expulsando el que está sirviendo, y
provocará una caída de ~79 s de warmup. Eso es indistinguible de una caída de
producción.

Esta restricción va escrita explícitamente en el prompt de la Fase 4.

---

## 9. Fuentes de la investigación externa realizada para este documento

| Fuente | Uso |
|---|---|
| [llama.cpp issue #21228 — json_schema con $ref/$defs falla en silencio](https://github.com/ggml-org/llama.cpp/issues/21228) | H-NEW-1: fallback silencioso a generación no restringida |
| [Pydantic issue #12232 — model_json_schema() genera $defs/$ref](https://github.com/pydantic/pydantic/issues/12232) | H-NEW-1: confirma que el schema de HemoVet los contiene |
| [Ollama — Structured Outputs (docs)](https://docs.ollama.com/capabilities/structured-outputs) | `required` se respeta; recomienda incluir el schema en el prompt; nada sobre `$defs` ni streaming |
| [Ollama issue #8063 — no respeta structured outputs](https://github.com/ollama/ollama/issues/8063) | Campos requeridos ausentes, `const`/`enum` ignorados; abierto |
| [Ollama issue #13337 — arquitecturas soportadas por Flash Attention](https://github.com/ollama/ollama/issues/13337) | H-NEW-3: allowlist sin híbridos; fallback silencioso a f16 |
| [arXiv 2605.30571 — Memory-Bound but Not Bandwidth-Limited](https://arxiv.org/html/2605.30571) | H-NEW-2: L4 al 81 % del pico; dispersión 3,6× entre kernels |
| [Qwen/Qwen3.6-27B — model card](https://huggingface.co/Qwen/Qwen3.6-27B) | 64 capas, híbrido 3:1, 262 144 ctx, thinking por defecto, MTP oficial |
| [Benchmark MTP Qwen3.6 en RTX 3090 (llama.cpp)](https://github.com/thc1006/qwen3.6-speculative-decoding-rtx3090) | MTP: pérdida del 3–12 % en llama.cpp frente a +27,5 % en vLLM |
| [llama.cpp issue #25923 — GBNF inválido desde json-schema](https://github.com/ggml-org/llama.cpp/issues/25923) | Refuerza el patrón de fallos silenciosos de gramática |

---

## 10. Resumen operativo

```
LO QUE ESTÁ DEMOSTRADO
  T(turno) = N_llamadas × 33,0 s + 1,8 s          error < 3 %
  N = 1 en el 51,4 % de turnos, N = 2,85 en el 48,6 %
  Decode = 13,05 tok/s, verificado por tres vías independientes
  Schema no exige policy_rule_ids; el validador sí, condicionalmente
  El salvage no puede actuar con un único claim
  La reparación aporta +2,48 % de información y acierta 0 de 9 veces

LO QUE NO SE HA MEDIDO NUNCA
  Composición de los 375 tokens (prosa clínica vs andamiaje JSON)
  Si la gramática se está aplicando de verdad con el schema real
  TTFB / latencia percibida
  Margen de serving en L4 (formato de cuantización × kernel)

LO QUE ES NO_OBSERVABLE HOY — pero fabricable mañana
  El contenido crudo de la primera generación rechazada
  → arnés de repetición externo, sin tocar producción

LA DECISIÓN
  Una única Fase 4, experimental y no observacional.
  Después: diseño de corrección, no más investigación.
```

---

# ANEXO — Reconciliación con la segunda opinión técnica

Se ha incorporado un segundo análisis independiente. Converge con éste en los
puntos estructurales —incluida la sospecha sobre la gramática, que ambos
localizamos en el mismo issue de llama.cpp por vías separadas— y aporta cuatro
elementos que no estaban en mi análisis. Los integro, y señalo dónde discrepo.

## A.1 Convergencias (dos análisis independientes, misma conclusión)

| Punto | Estado |
|---|---|
| El coste base de generación es real e irreductible con el stack actual | Coincidencia total |
| El amplificador dominante es la regeneración completa por reparación | Coincidencia total |
| `SCHEMA_ACCEPTS → VALIDATOR_REJECTS` es una causa arquitectónica confirmada | Coincidencia total |
| **`FORMAT_SENT ≠ GRAMMAR_ENFORCED` debe demostrarse, no suponerse** | **Coincidencia independiente — refuerza mucho la prioridad de H-NEW-1** |
| El *token tax* del sobre estructurado es la medición prioritaria no hecha | Coincidencia total |
| MTP es hipótesis, no ganancia | Coincidencia total |
| "13,7 tok/s es el máximo" fue un exceso, correctamente retirado | Coincidencia total |

Que dos análisis independientes lleguen al mismo issue upstream
(llama.cpp #21228) partiendo de evidencia distinta eleva H-NEW-1 de sospecha a
**la primera comprobación que debe hacerse en la Fase 4**. Es además la más
barata de todas: un `grep` y un volcado de JSON.

## A.2 Lo que la segunda opinión aporta y yo no tenía

### 1. El dato que reordena las prioridades: 2 de 20 preguntas numéricas

> *"sólo 2/20 preguntas diseñadas para obtener valores consiguieron entregar al
> menos uno correctamente"*
> *"hubo respuestas que afirmaban no tener acceso a valores que sí estaban
> disponibles en el contexto"*

Esto estaba en la batería original y **las tres fases lo dejaron caer**. Es, con
diferencia, el hecho más grave del expediente, y obliga a un reencuadre:

> Un sistema que responde en 20 segundos con el hematocrito equivocado es peor
> producto que uno que responde en 60 con el correcto. **La latencia puede no
> ser el problema principal de HemoVet.**

Además desplaza el prior de la bifurcación A/B de la sección 6. Si el modelo
falla al reproducir valores que sí tiene en el contexto, entonces una parte de
los 34 rechazos son **rechazos correctos** (Historia B): el validador está
haciendo su trabajo y el problema está aguas arriba, en grounding o en el
ensamblado del contexto. Bajo esa lectura, "relajar el validador" no sólo no
arreglaría nada: sería **clínicamente peligroso**.

Corolario operativo, y es importante: **la Fase 4 no puede limitarse a medir
tiempo. Tiene que evaluar corrección clínica del contenido rechazado contra
ground truth.** Sin eso, cualquier mitigación sobre el validador se diseñaría a
ciegas.

Estado: `CONFIRMADO en la batería original`, `ignorado por las Fases 1-3`,
`elevado a causa de primer nivel`.

### 2. El requisito funcional de los 10 pares no está demostrado

`history_limit = 12` no prueba que se conserven 10 pares. No se sabe si esa
variable cuenta mensajes, turnos, pares o elementos serializados. Con 12
mensajes serían 6 pares, no 10 — la mitad del requisito. Se necesita una prueba
funcional de 15 pares con identificadores únicos, no una lectura de la
constante. Lo incorporo al prompt.

### 3. La crítica al análisis del prompt de reparación es justa

Yo di por buena la lectura del agente de que "+2,48 % ⇒ no hay información
nueva". Es un argumento de tamaño, no de contenido. **Diez tokens pueden
contener el dato decisivo.** La pregunta correcta no es cuánto crece el prompt,
sino qué sabe el segundo intento que no sabía el primero:

```
Feedback pobre:     "policy_rule_id_missing"

Feedback suficiente: "El claim C-02 requiere policy_rule_ids.
                      Valores admisibles: [POLICY_03, POLICY_08].
                      Produjiste [].
                      Corrige exclusivamente ese campo."
```

Son dos bucles radicalmente distintos, y existe literatura reciente sobre
exactamente esta interfaz: el feedback que aporta localización del error, valor
observado y alternativas admisibles mejora la tasa de reparación frente a
diagnósticos vagos.

### 4. Fuentes upstream adicionales — verificadas para este documento

He comprobado las dos más relevantes y **son más fuertes de lo que se describía**:

**llama.cpp #23322 — baja aceptación de MTP en modelos híbridos/SWA (Qwen3.6).**
Aceptación medida del **35–55 %**, no del 100 %. La causa declarada es directamente
aplicable a HemoVet: cuando la ventana de atención se desplaza, las entradas de
caché quedan invalidadas y el sistema *"fuerza el reprocesado completo del prompt
por falta de datos en caché"*. Abierto, sin solución.

Esto tiene **dos consecuencias**, y la segunda no la había visto nadie:

- MTP baja de `NEEDS_BENCHMARK` a `POCO PROMETEDOR` para esta arquitectura
  concreta. No merece ser experimento prioritario.
- **Y explica un coste de prefill que HemoVet ya está pagando hoy, sin MTP.** La
  Fase 1 observó `restored context checkpoint … n_past = 3454, size = 149,626 MiB`
  y "prompt cache update" de **500–670 ms**. Ese es el mismo mecanismo:
  checkpointing de estado recurrente en un modelo híbrido. El caché de prefijos
  funciona —eso está demostrado— pero en esta familia de modelos **el
  restablecimiento de estado tiene un coste propio que nadie ha contabilizado
  por separado** dentro del 11,5 % de prefill.

**Ollama #14861 — diferencia de velocidad Ollama vs llama.cpp.**
No es un 20 %: los números reportados son **~47–53 tok/s en llama.cpp frente a
~28–32 tok/s en Ollama**, es decir **40–45 % más lento**, consistente en todos
los tamaños de prompt. Abierto, etiquetado como bug y como regresión de
rendimiento.

**Salvedad que debe respetarse:** es Apple Silicon, no CUDA, y es qwen3.5:35b, no
Qwen3.6-27B. **No es transferible como cifra.** Pero sí es transferible como
conclusión metodológica: la diferencia entre engines sobre hardware idéntico
puede ser de primer orden, y por tanto "no queda margen de serving" seguirá sin
estar demostrado hasta que exista un benchmark *apples-to-apples* sobre la propia
L4 de HemoVet.

## A.3 Donde discrepo de la segunda opinión

**Sobre cómo capturar la primera generación.** El segundo análisis contempla
activar temporalmente `CHAT_STRUCTURED_DEBUG_DIR` si las vías no invasivas
fallan, con un protocolo de reversibilidad. El protocolo es correcto, pero el
orden debe ser explícito y no negociable:

```
1º  Arnés de repetición externo al repositorio        riesgo: ninguno
      reconstruye la llamada exacta y captura el crudo
2º  Sólo si el arnés NO reproduce el fallo → instrumentación temporal
      riesgo: ventana de caída de ~79 s de warmup
```

El motivo es que si el arnés **sí** reproduce el fallo —y con un fallo tan
determinista como 0/9 es probable que lo haga— la instrumentación en producción
deja de ser necesaria. Y si **no** lo reproduce, eso ya es un hallazgo de primer
orden por sí mismo: significaría que la diferencia está en el estado acumulado
de producción, lo que convierte la ventana de instrumentación en un experimento
con hipótesis concreta en vez de una pesca.

**Sobre la extensión del prompt.** La lista de fases del segundo análisis es
excelente en cobertura, pero un prompt de ~37 secciones con más de 200 campos
enumerados tiene un fallo predecible: el agente asigna esfuerzo uniforme y
diluye la prioridad. La Fase 4 tiene exactamente **cuatro objetivos**; todo lo
demás es subordinado. El prompt que acompaña a este documento conserva la
cobertura pero impone una jerarquía explícita, con puertas de bloqueo sólo en lo
que de verdad decide.

## A.4 Fuentes adicionales verificadas para este anexo

| Fuente | Hallazgo verificado |
|---|---|
| [llama.cpp #23322 — baja aceptación MTP en SWA/híbridos (Qwen3.6)](https://github.com/ggml-org/llama.cpp/issues/23322) | Aceptación 35–55 %; invalidación de caché fuerza reprocesado completo del prompt; abierto |
| [Ollama #14861 — diferencia de velocidad Ollama vs llama.cpp](https://github.com/ollama/ollama/issues/14861) | 47–53 tok/s vs 28–32 tok/s (Apple Silicon, qwen3.5:35b); abierto, etiquetado bug+performance |
| [llama.cpp #23335 — draft-mtp altera la salida determinista en Qwen3.6](https://github.com/ggml-org/llama.cpp/issues/23335) | Aportado por la segunda opinión; refuerza que MTP no está maduro para este modelo |
| [Structured Feedback Improves Repair in an LLM Agent Loop](https://huggingface.co/papers/2607.14167) | Aportado por la segunda opinión; base para la autopsia semántica del prompt de reparación |

## A.5 El diagnóstico, corregido

La incorporación del dato de 2/20 obliga a reordenar. El diagnóstico final es:

```
PROBLEMA 1 — CALIDAD CLÍNICA          ← elevado a primer lugar
  2 de 20 preguntas numéricas entregaron un valor correcto
  Respuestas que niegan tener datos que sí están en el contexto
  Estado: CONFIRMADO en la batería, NO INVESTIGADO en 3 fases
  Implicación: parte de los 34 rechazos podrían ser CORRECTOS

PROBLEMA 2 — LATENCIA
  T = N_llamadas × 33,0 s + 1,8 s
  Tres palancas multiplicativas: tokens/llamada · llamadas · tok/s
  Sólo se ha investigado a fondo la segunda

PROBLEMA 3 — DESAJUSTE DE CONTRATOS
  El schema permite lo que el validador prohíbe
  Y podría ser peor: la gramática quizá ni siquiera se aplica (H-NEW-1)

PROBLEMA 4 — ARQUITECTURA DE RECUPERACIÓN
  Salvage inaplicable con un solo claim
  Reparación que regenera 375 tokens para insertar 20
  Feedback de reparación de calidad no evaluada

PROBLEMA 5 — DEFECTOS INDEPENDIENTES
  Router de ámbito con falsos negativos
  Memoria de 10 pares no demostrada
  Latencia percibida = latencia total (sin streaming)
```

**Y la advertencia final, que es la más importante de este documento:**

> No optimices la latencia de HemoVet antes de saber si sus respuestas son
> correctas. Si el 90 % de las respuestas numéricas está mal, reducir 59 s a
> 21 s sólo consigue que el sistema se equivoque tres veces más rápido.