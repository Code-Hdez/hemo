# Investigación de causa raíz — chat LLM de HemoVet

**Fase de investigación. No se modificó nada: ni producción, ni el repositorio,
ni configuración. Todos los artefactos viven fuera del worktree, en
`~/investigacion_llm_hemovet_2026-08-08/`.**

> Evidencia base: batería de 70 preguntas del 7-ago-2026 (133 llamadas al modelo
> correlacionadas y verificadas por contenido en 70/70), telemetría del backend,
> log de `llama-server`, estado de turnos, y un experimento de repetición ×10.

---

## 0. Resumen: las cinco causas, en orden de peso

| # | Causa | Estado | Peso medido |
|---|---|---|---|
| 1 | **Decode de un 27B en una L4** es el suelo físico de la latencia | `CONFIRMADO` | 87,2 % del tiempo del modelo |
| 2 | **El contrato estructurado se incumple casi siempre**, y provoca 1,9 llamadas por pregunta | `CONFIRMADO` | 60 % de generaciones descartadas |
| 3 | **El paso de reparación no repara** | `CONFIRMADO` | 0/9 éxitos; 41,6 % del cómputo |
| 4 | **El clasificador de ámbito es regex y falla contra su propio dominio** | `CONFIRMADO` | 3/5 preguntas de cortesía |
| 5 | **Un único modelo 27B atiende también tareas triviales** | `EVIDENCIA_FUERTE` | guardarraíles y clasificación pagan 13 tok/s |

Y tres hipótesis **descartadas** que conviene no volver a perseguir: prefill/caché
(§6), GPU mal usada (§5) y thinking oculto (§4).

---

## 1. Runtime exacto (`CONFIRMADO`)

Leído del runtime, no del repositorio.

| | |
|---|---|
| Engine | **Ollama 0.32.5**, contenedor `hemovet-gpu-ollama-1` |
| Imagen | `ollama-runtime@sha256:96367c0305543e7ea17ecb30f7589602ebfc1ee48be3e3769333ce11d4d05a0e` |
| Modelo | `qwen3.6:27b-q4_K_M`, digest `a50eda8ed977ab48a12431878896b27ffd5cef552c17af3317d9623b939a7f1e` |
| Arquitectura | familia `qwen35`, **27,8 B**, Q4_K_M, gguf |
| Tamaño / VRAM | 16.926.501.764 B; `size_vram` **idéntico** → 100 % en GPU |
| GPU | **NVIDIA L4**, driver 580.159.03, 23.034 MiB (17.418 en uso) |
| `llama-server` | `-c 16384 -np 1 --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on -b 512 -ub 512 --context-shift --keep 4 --no-mmap --chat-template chatml` |
| Sampling | temp **0,3** (0,1 en reparación), top_k 20, top_p 0,8, repeat 1,0, **sin seed** |
| Presupuesto | `num_ctx` 16.384 · `max_input_tokens` 12.000 · `history_limit` 12 · `rag_top_k` 3 |

**Flash Attention: activo** (`--flash-attn on`). **KV cuantizado a q8_0.**
**`-np 1`**: una sola ranura de generación en el propio runtime.

### ¿El código local es el que produjo las 70 respuestas?

`NO_CONFIRMADO`. Se verificó el digest de la imagen de Ollama y el de la imagen
del runtime, pero **no se pudo cerrar la cadena `git SHA local → imagen del
backend → despliegue`**. El repositorio local está en `21f18fd8` sin ficheros
modificados, y el comportamiento observado es coherente con ese código (los
nombres de validador y los códigos de error coinciden exactamente), lo que da
`EVIDENCIA_FUERTE` pero no confirmación. **Cerrar esto es el experimento E-0
del plan futuro.**

---

## 2. Dónde se va el tiempo (`CONFIRMADO`)

Latencia total observada de la batería: **4.940 s**. De ellos, **4.922 s
(99,6 %) transcurren dentro de Ollama**; backend, validadores, RAG, cola y red
suman **18 s (0,4 %)**.

Y dentro del modelo, medido con `prompt_eval_duration` / `eval_duration` /
`load_duration` de las 133 llamadas:

| Fase | Tiempo | % |
|---|---:|---:|
| **decode** (`eval`) | **4.241 s** | **87,2 %** |
| prefill (`prompt_eval`) | 551 s | 11,3 % |
| carga de modelo | 73 s | 1,5 % |

> **Falsable así:** si prefill fuera el cuello, `prompt_eval_duration` superaría
> a `eval_duration`. Mide 551 s frente a 4.241 s. Cualquier técnica que sólo
> ataque el input (prefix caching, compresión de RAG, recorte de historial)
> tiene un techo teórico del **11,3 %**.

### Velocidad y si es normal

**13,05 tok/s** de decode (mín 12,59, máx 13,38: notablemente estable).
Prefill 632–675 tok/s.

Un 27B Q4_K_M rinde ~40 tok/s en una RTX 4090. La L4 tiene aproximadamente un
**30 % del ancho de banda de memoria** de una 4090, y el decode autoregresivo
está limitado por ancho de banda. **13/40 ≈ 0,33.** Es decir: la GPU **rinde lo
que le corresponde**. No hay margen de configuración que recupere ese factor;
sólo un modelo menor o una GPU con más ancho de banda.

---

## 3. El pipeline llama al modelo 1,9 veces por pregunta (`CONFIRMADO`)

133 llamadas para 70 preguntas.

| Llamadas en el turno | Turnos |
|---:|---:|
| 1 | 36 |
| 2 | 8 |
| 3 | 23 |
| 4 | 3 |

**Demostrado, no inferido de un evento `repairing`:** hay dos eventos
`llm_chat.generation_config` distintos con perfiles y temperaturas distintas
para el mismo `request_id`, y **dos entradas `prompt eval` independientes** en
el log de `llama-server`.

Veredicto de las 133 validaciones: **53 válidas, 57 inválidas, 23 reparables**
→ **el 60 % de lo que genera el modelo se descarta**.

### El repair prompt NO está inflado (`DESCARTADO`)

| | n | input mediana | output mediana | tok/s |
|---|---:|---:|---:|---:|
| Primaria | 70 | 3.884 | 375 | 13,05 |
| Reparación | 63 | 3.882 | 318 | 13,06 |

`repair_prompt_growth_pct` ≈ **−0,05 %**. La reparación no cuesta cara por
tamaño de prompt ni por degradación de velocidad: cuesta cara porque **es otra
generación entera**.

---

## 4. Thinking: descartado como causa (`EVIDENCIA_FUERTE`)

Qwen3.6 opera en modo thinking **por defecto** según su model card. HemoVet lo
**desactiva explícitamente**: `thinking: false` en **133/133** llamadas
(`llm_chat.generation_config`).

¿Se está pagando razonamiento invisible de todos modos? La evidencia dice que
no: `eval_count` mediana es **375 tokens** y `envelope_chars` observado ~924,
cifras coherentes con el sobre JSON visible. Una cadena de razonamiento haría
que `eval_count` superara ampliamente el tamaño del sobre, y no ocurre.

**Coste del thinking: 0 tokens medibles.** `NO_OBSERVABLE` en sentido estricto
—no hay campo `thinking` en la telemetría— pero la contabilidad de tokens no
deja hueco para él.

**Truncación por longitud: descartada.** `finish_reason`: 136 `stop`, sólo
**2 `length`** de 138.

---

## 5. GPU: correctamente utilizada (`CONFIRMADO` / `DESCARTADO` como causa)

- `inference_device = "full_gpu"` y `gpu_active = true` en **133/133**.
  **No hay CPU fallback.**
- `size_vram` == `size` → el modelo entero reside en VRAM. **No hay offload.**
- `load_duration_ms` mediana **554 ms**, y `expires_at` en el año 2318
  (keep_alive infinito) → **no hubo ningún arranque en frío** durante la
  batería. Cold start `DESCARTADO`.
- VRAM: 17.418 de 23.034 MiB → **5,6 GB libres**. No hay presión de memoria.
- Cola: `queue_duration_ms` mediana **0 ms**, máximo **1 ms**. Ninguna pregunta
  esperó a otra. `DESCARTADO`.

> Matiz honesto: no se muestreó `nvidia-smi` **durante** la batería, así que la
> correlación temporal «GPU alta → generación / GPU baja → validación» no está
> medida directamente. Se infiere de que la validación consume 0,4 % del tiempo
> total. Es el experimento **E-3**.

---

## 6. Caché de prefijo: YA FUNCIONA (`CONFIRMADO`)

Ésta era una hipótesis prioritaria y el resultado **corrige una lectura inicial
propia**. Un primer vistazo a `prompt_eval_count` en multiturno (3.871 → 5.151 →
5.167 → 5.378) sugería reprocesado completo. El log de `llama-server` lo
desmiente:

```
task 157291 | restored context checkpoint (n_past = 1370, size = 149.626 MiB)
task 157291 | prompt eval time = 262.78 ms /     4 tokens
task 157527 | restored context checkpoint (n_past = 3454, size = 149.626 MiB)
task 157527 | prompt eval time = 942.80 ms /   417 tokens
```

Cuando el prefijo coincide, **sólo se evalúan los tokens nuevos** (4, 417…).
llama.cpp guarda y restaura *context checkpoints* de **149,6 MiB** —el estado
recurrente que exige la arquitectura híbrida de Qwen3.6— con un coste de
`prompt cache update` de **501–666 ms**.

**Conclusión:** el reprocesado completo ocurre sólo en cache miss (conversación
nueva o prefijo cambiado). Prefix caching **no es una mitigación pendiente: ya
está operando**. Y aunque fuera perfecto, su techo sigue siendo el 11,3 % del §2.

---

## 7. `generation_repair_failed`: la cadena completa (`CONFIRMADO`)

Reconstruida para `SEL-08` (*«¿Cómo están las plaquetas?»*), con
`request_id d6d6761f-c453-48eb-b74a-7f5f11e1508b`:

```
routing        route=database_generation, intent=selected_value (0.82),
               use_clinical_context=true, use_rag=false, safety_action=allow
plan           required_fact_count=12, patient_loaded=true,
               context_bundle_omitted_fact_count=0
scope clínico  authorized_code_count=18, materialized_fact_count=1
   ↓
LLAMADA #1     hemogram_interpretation, temp 0.3, 3.871 tok in → 286 tok out (22,1 s)
VALIDACIÓN     repairable · missing_required_clinical_facts · PLT:value,PLT:unit
   ↓ regeneration(reason=missing_required_clinical_facts)
LLAMADA #2     ..._structured_repair, temp 0.1, 3.966 tok in → 299 tok out (23,3 s)
VALIDACIÓN     repairable · EL MISMO FALLO · PLT:value,PLT:unit
   ↓ last_resort
LLAMADA #3     hemogram_interpretation, temp 0.3, 1.374 tok in → 259 tok out (19,8 s)
VALIDACIÓN     invalid · structured_schema_invalid · policy_rule_id_missing
   ↓
terminal_error generation_repair_failed, final_state=failed, response=null
```

**El contexto clínico estaba cargado y completo** (`omitted_fact_count: 0`,
18 analitos autorizados). Lo que falló fue que el modelo no materializó
`PLT:value` y `PLT:unit` como hechos estructurados.

### ¿Estaba mal la primera respuesta?

`NO_OBSERVABLE`. El texto generado no se persiste ni se registra —confirmado por
tres vías: `CHAT_STRUCTURED_DEBUG_DIR` vacío con `/tmp/structured-debug` a 0
ficheros; el log del backend sólo publica hashes y códigos; y el log de
`llama-server` con `--log-verbosity 4` da **0 coincidencias** buscando términos
clínicos en 17.344 líneas.

**No se puede afirmar `VALIDATOR_FALSE_REJECTION` ni `MODEL_GENERATION_FAILURE`.**
Cerrarlo requiere encender el volcado (experimento **E-1**).

### Taxonomía de reparaciones

Clasificando los 80 rechazos por lo que exigían:

| Categoría | n | Ejemplos de detalle |
|---|---:|---|
| **FORMAT_REPAIR** | ~58 | `policy_rule_id_missing` (15), `patient_fact_ids_missing` (6), `structured_schema_invalid` |
| **NUMERIC_REPAIR** | ~21 | `PLT:value,PLT:unit`, `WBC:value,WBC:unit`, `MCHC:flag` |
| **SAFETY_REPAIR** | **7** | `definitive_diagnosis`, `mandatory_diagnosis_boundary`, `indirect_treatment_recommendation`, `medical_refusal_contract` |
| GROUNDING / otros | ~7 | `evidence_span_not_found`, `ambiguous_parameter_claim` |

> **Sólo 7 de 133 rechazos son barreras de seguridad clínica.** El resto es
> contabilidad estructural: identificadores de regla de política, identificadores
> de hecho, y materializar `valor`+`unidad`. El validador no está impidiendo que
> el asistente diga algo peligroso; está impidiendo que entregue algo correcto
> mal etiquetado.

---

## 8. No determinismo: medido, no supuesto (`CONFIRMADO`)

Experimento controlado: 10 ejecuciones de la misma pregunta, conversaciones
independientes. **Prompt de 3.871 tokens en las diez** (valor único).

| Etapa | Éxito |
|---|---|
| 1.ª generación válida | **1 / 10** |
| **Reparación corrige el fallo** | **0 / 9** |
| Último recurso salva el turno | 4 / 9 |
| Desenlace final | **5 OK / 5 fallo** |

Nueve de diez fallan **por el mismo detalle** (`PLT:value,PLT:unit`). La
reparación, a temperatura **0,1**, reincide en el mismo fallo las nueve veces.

**Qué introduce la variabilidad:** con entrada idéntica, contexto idéntico y
configuración idéntica, lo único que varía es el muestreo. Pero la explicación
«es la temperatura» es insuficiente: a 0,1 el resultado no mejora en absoluto.
La lectura defendible es que **el contrato exige una estructura que el modelo
acierta ~1 de cada 10 veces**, y que el mecanismo previsto para corregirlo no
corrige. `EVIDENCIA_FUERTE`.

Nota: **no hay `seed` fijado**, lo que impide reproducibilidad exacta.

---

## 9. Clasificador de ámbito: regex determinista (`CONFIRMADO`)

`application/services/intent_classifier.py` es **expresiones regulares** sobre
texto normalizado, con confianzas **codificadas a mano** (0,96 / 0,97 / 0,99) y
un enum `FunctionalIntent`. No hay LLM, no hay umbral aprendido, no hay modelo.
`conversation_routing.py` traduce el veredicto a `SafetyAction.REFUSE_OUT_OF_SCOPE`.

Se ejecuta **antes** del LLM y puede convertir un turno legítimo en `refused`.

Evidencia de fallo:

> `GEN-02` — *«¿En qué puedes ayudarme con un hemograma canino?»* →
> intent `identity`, pero la respuesta fue *«No puedo determinar si tu consulta
> pertenece estrictamente al ámbito de HemoVet. Si se trata sobre un hemograma
> canino, por favor reformula la pregunta.»*

La pregunta contiene literalmente «hemograma canino». 3 de las 5 preguntas de
identidad/cortesía sufren esto (`GEN-01`, `GEN-02`, `GEN-05`), y el servidor las
marca `refused` por su cuenta — el sistema **sabe** que rehusó.

**Causa:** un clasificador léxico sin cobertura de las formulaciones
meta-conversacionales («¿en qué puedes ayudarme…?», «gracias, eso era todo»).
Falla cerrado. `CONFIRMADO` como mecanismo; `HIPOTESIS_PLAUSIBLE` la regla
concreta que dispara, porque no se instrumentó qué patrón casó.

---

## 10. RAG y memoria conversacional

### RAG: no es un problema de rendimiento (`DESCARTADO` como causa)

Se activó en **8 de 70** preguntas. Estrategia `dense_bm25_rrf`, selecciona **3**
fragmentos de 10–35 candidatos, `top_score` 0,70–0,74, reranker
`heuristic-lexical-v1`, duración total **183–655 ms**.

> **Contradicción con el informe anterior, declarada:** aquel decía «RAG 0,4 s»
> tomando la mediana; el rango real es 183–655 ms. La cifra era correcta pero
> incompleta. En ningún caso es material frente a un decode de 22–38 s.

### Memoria: el diseño actual no cumple el objetivo de 10 pares (`CONFIRMADO`)

`history_limit = 12` en **todos** los perfiles, y es un límite de **mensajes**,
no de pares → **6 pares**, frente a los 10 requeridos.

Además, el crecimiento medido en multiturno:

| Turno | `prompt_eval_count` | `prompt_eval_duration` |
|---|---:|---:|
| MT-B-1 | 3.871 | 5.736 ms |
| MT-B-2 | 5.151 | 7.660 ms |
| MT-B-3 | 5.167 | 7.666 ms |
| MT-B-4 | 5.378 | 7.974 ms |

Cada par añade ~500 tokens. Diez pares ≈ **+5.000 tokens** sobre una base de
~3.900 → ~8.900, dentro de `max_input_tokens` 12.000 pero consumiendo el 74 %
del presupuesto. Con caché de prefijo funcionando (§6), el coste incremental es
manejable; sin él, cada turno pagaría ~13 s de prefill.

---

## 11. Qué funciona, y por qué (diff SUCCESS FAST vs FAIL SLOW)

| | `MT-B-1` (rápido, OK) | `SEL-08` (lento, falló) |
|---|---|---|
| Pregunta | idéntica | idéntica |
| Prompt | 3.871 tok | 3.871 tok |
| Llamadas | **1** | **3** |
| Latencia | **28,5 s** | 77,4 s |
| Validación #1 | **`valid`/`ok`** | `missing_required_clinical_facts` |

**La única diferencia es si la primera generación acertó el contrato.** Todo lo
demás —contexto, plan, configuración, GPU— es idéntico. Por eso el turno rápido
es el que **no entra en el pipeline de reparación**: 34,8 s de mediana sin
reparación frente a 98,1 s con ella (**+182 %**).

Los turnos de `general` son los más rápidos (mediana 23,0 s) porque activan
menos contrato: 1,41 llamadas por turno frente a 2,12 en `selected_hemogram`.

---

## 12. Coste desperdiciado (`CONFIRMADO`)

| Concepto | Segundos |
|---|---:|
| Generación primaria | 2.876 |
| **Generaciones de reparación** | **2.046 (41,6 % del cómputo)** |
| **GPU en los 17 turnos que no entregaron nada** | **1.875 (38,1 % del total)** |
| Media desperdiciada por `generation_repair_failed` | **110,3 s** |

En el experimento controlado, el paso de reparación consumió ~23 s × 9 ≈ **207 s
con tasa de éxito 0 %**.

---

## 13. Mapa causal

```
LATENCIA ALTA
│
├── Prefill ......................... 11,3 %  [techo bajo]
│   ├── contexto excesivo ........... DESCARTADO (3.884 tok de 16.384)
│   ├── RAG excesivo ................ DESCARTADO (8/70, <0,7 s)
│   ├── historial ................... MENOR (+500 tok/par)
│   └── cache no reutilizado ........ DESCARTADO (§6: checkpoints activos)
│
├── Decode .......................... 87,2 %  [CAUSA 1]
│   ├── 27B en L4 ................... CONFIRMADO (13 tok/s ≈ límite de banda)
│   ├── thinking .................... DESCARTADO (§4)
│   ├── demasiados output tokens .... DESCARTADO (mediana 375, 2/138 truncan)
│   └── GPU/offload ................. DESCARTADO (§5)
│
├── Pipeline ........................ ×1,9 llamadas  [CAUSAS 2 y 3]
│   ├── contrato incumplido ......... CONFIRMADO (1/10 acierta a la primera)
│   ├── reparación inútil ........... CONFIRMADO (0/9)
│   └── último recurso ............... recorta contexto y cambia de error
│
├── Infraestructura ................. DESCARTADA
│   ├── queue ....................... 0 ms mediana
│   ├── CPU fallback ................ 0/133
│   └── cold start .................. 554 ms
│
└── Percepción ...................... [CAUSA 4]
    └── sin streaming de tokens ..... el usuario espera a la validación completa
```

---

## 14. Lo que sigue sin poder demostrarse

| Incógnita | Por qué | Cómo se cerraría |
|---|---|---|
| Si la 1.ª generación era clínicamente correcta | El texto se descarta sin registrarse | E-1: encender `CHAT_STRUCTURED_DEBUG_DIR` |
| El prompt efectivo y su composición | Sólo se publican tamaños | E-1 |
| Qué chunks de RAG se inyectan | La telemetría da recuentos, no `chunk_id` | E-2 |
| Cadena `git SHA → imagen → despliegue` | No se cerró | E-0 |
| Correlación GPU-por-fase en vivo | No se muestreó durante la batería | E-3 |
| Qué patrón regex dispara el rechazo de ámbito | No instrumentado | E-4 |

---

*Investigación del 8-ago-2026. Ninguna mitigación aplicada. Ver
`MATRIZ_MITIGACIONES_LLM_2026-08-08.csv` y `PLAN_EXPERIMENTAL_FUTURO_2026-08-08.md`.*
