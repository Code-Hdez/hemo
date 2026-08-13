# Auditoría forense del chat LLM de HemoVet

**Fase de diagnóstico. No se corrigió nada.**

> `audit_run_id`: `bateria-2026-08-07` · Entorno: `https://hemovet.app` (GCP
> `project-5b36701c-f44f-4c03-a12`) · 70 preguntas · 133 llamadas al modelo
> correlacionadas.
>
> **Producción no fue modificada.** Ni código, ni `.env`, ni contenedores, ni
> reinicios, ni commits. La batería consume la API pública como el navegador;
> la inspección del servidor es estrictamente de lectura (`docker ps`,
> `docker logs`, `printenv`, `nvidia-smi`, `ss`, `/api/ps`). El estado del
> repositorio al terminar: HEAD en `21f18fd8`, cero ficheros modificados.

---

## 1. Resumen ejecutivo

Se instrumentó el ciclo de vida completo de 70 turnos y se correlacionaron
**tres fuentes independientes** que no comparten identificador: el cliente
(SSE), la telemetría del backend y el runtime `llama-server` de la VM de GPU.
La correlación está **verificada por contenido en los 70 casos**, no supuesta
por proximidad temporal (§5).

Cuatro conclusiones, todas con evidencia:

**1. La latencia no es de infraestructura. Es cómputo del modelo, repetido.**
De 4.940 s de latencia observada, **4.922 s (99,6 %) transcurren dentro de
Ollama**. Backend, validadores, RAG, cola y red suman **18 s (0,4 %)**. La cola
tiene mediana 0 ms y máximo 1 ms: nunca se esperó a otro usuario.

**2. El sistema llama al modelo 1,9 veces por pregunta, y el 60 % de esas
generaciones se descarta.** 133 llamadas para 70 preguntas. De las 133
validaciones: 53 válidas, 57 inválidas, 23 reparables. **El 41,6 % de todo el
cómputo del modelo se gastó en reparaciones**, y **1.875 s —el 38,1 % del total
de GPU de la batería— se consumieron en los 17 turnos que terminaron sin
entregar nada**. Media de 110,3 s desperdiciados por cada
`generation_repair_failed`.

**3. La causa del rechazo no es clínica: es de contabilidad estructural.** El
motivo dominante no es que el modelo se equivoque, invente o diga algo inseguro,
sino que no adjunta identificadores que el contrato exige:
`policy_rule_id_missing` (15), `patient_fact_ids_missing` (6), y la
materialización de `ANALITO:value,ANALITO:unit` como hecho estructurado. Sólo
**7 de 133** rechazos corresponden a barreras de seguridad reales, que es
justamente donde el rechazo es correcto.

**4. Ante entrada idéntica, el resultado es una lotería, y está medido.**
`SEL-08` y `MT-B-1` son la misma pregunta, con el mismo contexto y **exactamente
3.871 tokens de prompt en ambas**. Una pasó la validación a la primera; la otra
falló tres veces seguidas y devolvió una pantalla vacía tras 77 s (§7).

**Lo que no se pudo observar:** el texto que el modelo generó. Está confirmado
por tres vías independientes que no se persiste ni se registra (§4). Esa es la
laguna principal, y la instrumentación para cerrarla **ya existe en el código,
desactivada** (§16).

---

## 2. Arquitectura real del turno

Reconstruida leyendo el código, no supuesta. Cada componente con el archivo
donde vive.

```
navegador
  └─ POST /api/v1/chat/stream          api/router.py:576  stream_chat
       ├─ autenticación JWT + X-HemoVet-Browser-Session-ID
       ├─ routing                      → llm_chat.routed
       │    route, intent, intent_confidence, safety_action,
       │    use_clinical_context, use_rag
       ├─ perfil de generación         → llm_chat.profile_selected
       ├─ plan de respuesta            → llm_chat.response_plan
       │    allowed_claim_types, required_fact_count,
       │    context_bundle_patient_loaded, context_bundle_omitted_fact_count
       ├─ alcance de hechos clínicos   → llm_chat.clinical_claim_scope
       │    authorized_code_count, materialized_fact_count
       ├─ RAG (sólo si use_rag)        → llm_chat.retrieval
       ├─ cola de generación           → llm_chat.queue_acquired
       ├─ GENERACIÓN #1                → llm_chat.generation_config
       │    └─ Ollama                  → llm_chat.ollama_metrics
       ├─ validación                   → llm_chat.validation
       │    result ∈ {valid, repairable, invalid}
       ├─ si repairable → REGENERACIÓN → llm_chat.regeneration
       │    perfil ..._structured_repair, temperature 0.3 → 0.1
       ├─ si vuelve a fallar → ÚLTIMO RECURSO → llm_chat.last_resort
       │    perfil original, prompt recortado
       ├─ terminal                     → llm_chat.completed | llm_chat.terminal_error
       └─ SSE al cliente
```

**Confirmado que sí existe reconstrucción del prompt y segunda generación**
(§6 lo exigía demostrar, no suponer): hay **dos eventos `generation_config`
distintos** con perfiles y temperaturas distintas para el mismo `request_id`, y
**dos entradas `prompt eval` independientes** en el log de `llama-server`. No es
un reintento del mismo prompt: cambia el perfil, la temperatura y el tamaño.

### Validadores identificados

| Motivo | Archivo | Nivel |
|---|---|---|
| `missing_required_clinical_facts` | `use_cases/send_chat_message.py:381` | reparable |
| `structured_schema_invalid` | `services/structured_response.py:961` | inválido |
| `policy_rule_id_missing` | `services/structured_response.py:645` | detalle |
| `structured_patient_fact_id_required` | `use_cases/send_chat_message.py:4801` | inválido |
| `structured_patient_fact_not_materialized` | `use_cases/send_chat_message.py:4720` | inválido |
| `ambiguous_parameter_claim` | `services/output_claim_validator.py:638` | inválido |
| último recurso | `use_cases/send_chat_message.py:4283` `_last_resort_candidate` | — |

---

## 3. Configuración exacta del modelo y la infraestructura

Leída del runtime, no del repositorio.

### Modelo (`/api/ps` de Ollama)

| | |
|---|---|
| Nombre | `qwen3.6:27b-q4_K_M` |
| Digest | `a50eda8ed977ab48a12431878896b27ffd5cef552c17af3317d9623b939a7f1e` |
| Familia · parámetros | `qwen35` · **27,8 B** |
| Cuantización · formato | **Q4_K_M** · gguf |
| Tamaño · en VRAM | 16.926.501.764 B (**16,9 GB**), `size_vram` idéntico → **100 % en GPU** |
| `context_length` | 16.384 |
| `expires_at` | año **2318** → keep_alive infinito, el modelo no se descarga |

### Parámetros de inferencia (`llm_chat.generation_config`, por llamada)

`temperature` **0,3** (0,1 en el perfil de reparación) · `top_k` 20 ·
`top_p` 0,8 · `repeat_penalty` 1,0 · `num_ctx` 16.384 · `num_predict` 1.280
(1.024 en reparación) · `keep_alive` −1 · `timeout_seconds` 120 ·
`max_generation_attempts` 2 · `thinking` false · sin `seed`.

> **Corrección respecto a lo asumido antes:** la temperatura en producción es
> **0,3**, no 0,6 como indicaba `ESTADO_LLM_2026-08-06.md`. La reparación baja a
> 0,1. Esto importa porque debilita —sin anularla— la explicación de que la
> variabilidad venga de una temperatura alta (§7).

### Runtime real (`llama-server`, flags del proceso)

```
-c 16384  -np 1  --cache-type-k q8_0  --cache-type-v q8_0  --flash-attn on
-b 512 -ub 512  --context-shift  --keep 4  --no-mmap  --chat-template chatml
--log-verbosity 4
```

**`-np 1` confirma en el propio runtime que hay una sola ranura de generación.**

### Infraestructura

| | |
|---|---|
| GPU | NVIDIA **L4**, driver 580.159.03, 23.034 MiB |
| VRAM en uso | 17.418 MiB (proceso `llama-server`: 17.410 MiB) |
| Ollama | contenedor `hemovet-gpu-ollama-1`, escuchando en `10.128.0.3:11434` |
| Env del servicio | `OLLAMA_CONTEXT_LENGTH=16384`, `OLLAMA_KEEP_ALIVE=30m`, `OLLAMA_MAX_LOADED_MODELS=1` |
| Backend | `hemogramas-proyectoicc-backend-1`, sano, 5 contenedores en `hemovet-prod` |

**CPU fallback: descartado.** `inference_device = "full_gpu"` y
`gpu_active = true` en **133 de 133** llamadas. No hay una sola inferencia con
capas en CPU. `load_duration_ms` mediana 527 ms → el modelo estaba caliente en
todos los turnos; no hubo ningún arranque en frío durante la batería.

---

## 4. Observabilidad: lo que se ve y lo que no

### Se puede observar (CONFIRMADO)

Número real de llamadas al modelo · configuración completa por llamada ·
tokens de prompt y de salida reales · duraciones de carga, evaluación de prompt
y generación · velocidad en tokens/s · dispositivo de inferencia · tiempo de
cola · veredicto de cada validador con motivo y detalle · intención y ruta ·
tipos de claim autorizados · nº de hechos requeridos y materializados · hechos
omitidos del contexto · métricas de RAG · regeneraciones y último recurso ·
estado final del turno · cronología SSE completa.

### NO se puede observar (`NO_OBSERVABLE`, confirmado por tres vías)

**El texto que el modelo generó** — ni la generación rechazada, ni la de
reparación, ni el prompt efectivo (sólo su tamaño).

Evidencia de la ausencia, no suposición:

1. `docker exec ... printenv CHAT_STRUCTURED_DEBUG_DIR` en el contenedor de
   producción devuelve **vacío**, y `/tmp/structured-debug` contiene
   **0 ficheros**. El volcado de envolturas rechazadas está apagado.
2. El log del backend publica **hashes** (`client_message_hash`,
   `conversation_hash`) y códigos, nunca texto clínico. Es una decisión de
   diseño explícita.
3. El log de `llama-server`, pese a `--log-verbosity 4`, **no contiene texto**:
   la búsqueda de `hemograma|leucocit|plaqueta|veterinari|HemoVet` sobre 17.344
   líneas devuelve **0 coincidencias**. Sólo publica tiempos y recuentos.

**Dónde desaparece:** la generación se evalúa en memoria; si el validador la
rechaza, se descarta sin escribirla en ninguna parte. `response` queda a `null`
en los 17 turnos fallidos (verificado vía
`GET /conversations/{id}/turns`: **0 de 17** conservan contenido).

---

## 5. Metodología de correlación

Las tres fuentes no comparten clave: la telemetría hashea deliberadamente el
mensaje y la conversación. Sólo hay tiempo.

El primer intento —emparejar por ventana temporal— produjo un **desplazamiento
de uno** que habría contaminado todo el informe: el caso N recibía los datos del
N+1, porque con turnos consecutivos cualquier holgura invade el siguiente. Se
detectó porque `llm_chat.routed` publica `message_length`, y esa longitud no
cuadraba con la de la pregunta.

El emparejamiento definitivo avanza ambas listas en orden temporal **exigiendo
que `message_length` coincida con la longitud real del texto**. Resultado:
**70/70 verificados por contenido** → nivel `CONFIRMADO`. Un turno ajeno a la
batería se salta en lugar de descolocar el resto.

Las 133 llamadas correlacionadas frente a las 138 tareas del log de Ollama
cuadran: las 5 restantes son de la prueba de humo previa a la batería.

---

## 6. Latencia: descomposición

| Componente | Tiempo | % |
|---|---:|---:|
| **Dentro de Ollama** | **4.922 s** | **99,6 %** |
| Backend + validación + RAG + cola + red | 18 s | 0,4 % |
| Total observado | 4.940 s | 100 % |

Y dentro del cómputo del modelo:

| | Tiempo | % del cómputo |
|---|---:|---:|
| Generación primaria | 2.876 s | 58,4 % |
| **Generaciones de reparación** | **2.046 s** | **41,6 %** |

| Serie | n | mediana | p90 | máx |
|---|---:|---:|---:|---:|
| Total | 70 | 59,1 s | 128,8 s | 212,3 s |
| TTFB | 70 | 0,2 s | 0,2 s | 0,2 s |
| `general` | 17 | 23,0 s | 65,9 s | 128,8 s |
| `selected_hemogram` | 32 | 71,9 s | 140,7 s | 181,8 s |
| `hemogram_history` | 21 | 90,6 s | 112,7 s | 212,3 s |

### Con y sin reparación

| | Sin reparación | Con reparación |
|---|---:|---:|
| Casos | 36 | 34 |
| Mediana | **34,8 s** | **98,1 s** |
| Máximo | 89,0 s | 212,3 s |

`repair_latency_penalty` = **+63,4 s (+182 %)**.

### Rendimiento del modelo

| | n | input | output | generación | tok/s |
|---|---:|---:|---:|---:|---:|
| Primaria | 70 | 3.884 tok | 375 tok | 28,8 s | **13,05** |
| Reparación | 63 | 3.882 tok | 318 tok | 24,0 s | **13,06** |

> **Hipótesis descartada con datos.** Se sospechaba que la reparación fuera lenta
> por inflar el prompt. **No lo hace**: 3.882 frente a 3.884 tokens de mediana.
> La reparación cuesta cara simplemente porque **es otra generación completa** a
> la misma velocidad. La velocidad tampoco varía: 13,05 vs 13,06 tok/s.

### RAG

Se activó en **8 de 70** preguntas. Estrategia `dense_bm25_rrf`, selecciona 3
fragmentos de entre 10 y 35 candidatos, `top_score` 0,70–0,74, reranker
`heuristic-lexical-v1`. Duración total **183–655 ms**.

**El RAG no participa en el problema de latencia.** Su coste máximo es tres
órdenes de magnitud menor que una generación.

---

## 7. El hallazgo central: misma entrada, distinto desenlace

`SEL-08` y `MT-B-1` son la pregunta *«¿Cómo están las plaquetas?»*, ambas en
primer turno, mismo hemograma seleccionado, misma cuenta.

| | `SEL-08` | `MT-B-1` |
|---|---|---|
| `required_fact_count` | 12 | 12 |
| `materialized_fact_count` | 1 | 1 |
| `authorized_code_count` | 18 | 18 |
| **Prompt llamada #1** | **3.871 tok** | **3.871 tok** |
| Output llamada #1 | 286 tok / 22,1 s | 277 tok / 21,5 s |
| Veredicto #1 | `repairable` · `missing_required_clinical_facts` · `PLT:value,PLT:unit` | **`valid` · `ok`** |
| Llamadas totales | **3** | **1** |
| Resultado | error tras 77,4 s | respuesta correcta en 28,5 s |

El prompt es idéntico **hasta el token**. El contexto es idéntico. La
configuración es idéntica. Lo único que difiere son los 9 tokens de más que
produjo el muestreo.

Las tres llamadas de `SEL-08`:

| # | Perfil | temp | input | output | Veredicto |
|---|---|---:|---:|---:|---|
| 1 | `hemogram_interpretation` | 0,3 | 3.871 | 286 | `missing_required_clinical_facts` → `PLT:value,PLT:unit` |
| 2 | `hemogram_interpretation_structured_repair` | **0,1** | 3.966 | 299 | **el mismo fallo** → `PLT:value,PLT:unit` |
| 3 | `hemogram_interpretation` (último recurso) | 0,3 | **1.374** | 259 | `structured_schema_invalid` → `policy_rule_id_missing` |

Dos observaciones que sólo se ven con esta traza:

- La reparación **baja la temperatura a 0,1 y falla exactamente igual**. Si el
  problema fuera sólo variabilidad de muestreo, reducirla debería ayudar; no lo
  hizo. `EVIDENCIA_FUERTE` de que el contrato pide algo que el modelo no
  produce de forma fiable, no de que simplemente «tuvo mala suerte dos veces».
- El último recurso **recorta el prompt de 3.871 a 1.374 tokens** —descarta
  contexto— y entonces tropieza con un error **distinto**
  (`policy_rule_id_missing`). Es decir: la última red de seguridad cambia el
  problema en lugar de resolverlo.

**Nivel de evidencia: CONFIRMADO** para «la entrada era idéntica y el desenlace
no». `HIPOTESIS` para la atribución causal exacta al muestreo, porque el texto
generado no es observable y no puede compararse (§4).

---

## 8. Taxonomía de rechazos

De las 133 validaciones: **53 válidas, 57 inválidas, 23 reparables** → el
**60 % de las generaciones se descartó**.

| Motivo | n | ¿Rechazo legítimo? |
|---|---:|---|
| `structured_schema_invalid` | 24 | contrato de formato |
| `missing_required_clinical_facts` | 21 | contrato de formato |
| `structured_patient_fact_id_required` | 8 | contrato de formato |
| `ambiguous_parameter_claim` | 5 | ambigüedad clínica — defendible |
| `structured_patient_fact_not_materialized` | 5 | contrato de formato |
| `definitive_diagnosis` | 2 | **sí, seguridad** |
| `mandatory_diagnosis_boundary` | 2 | **sí, seguridad** |
| `indirect_treatment_recommendation` | 2 | **sí, seguridad** |
| `limitation_claim_invalid` | 2 | redacción |
| `structured_json_invalid` | 2 | formato |
| `medical_refusal_contract` | 1 | **sí, seguridad** |
| otros (7 motivos) | 6 | varios |

Y el detalle de **qué falta exactamente**:

| Detalle | n |
|---|---:|
| `policy_rule_id_missing` | **15** |
| `patient_fact_ids_missing` | 6 |
| `ambiguous_parameter_claim:neu` | 5 |
| `PLT:value,PLT:unit` | 4 |
| `RBC:value,RBC:unit` | 2 |
| `MCHC:value,MCHC:unit` (×2) | 2 |
| `NEU:value,NEU:unit` (×2) | 2 |
| `EOS:value,EOS:unit,EOS:reference_min,EOS:reference_max` | 2 |
| `WBC:value,WBC:unit` (×2) | 2 |
| `parametric_fact_ids_forbidden` | 2 |
| `MCHC:flag` | 2 |

**Lectura:** de 133 rechazos, sólo **7** son barreras de seguridad clínica
—donde rechazar es acertar—. El resto es contabilidad: identificadores de regla
de política, identificadores de hecho y materialización de `valor`+`unidad`.
El validador no está impidiendo que el asistente diga algo peligroso; está
impidiendo que entregue algo correcto mal etiquetado.

### Rechazo por alcance

| Alcance | Turnos | Llamadas | Llam./turno | Rechazos | Errores |
|---|---:|---:|---:|---:|---:|
| `general` | 17 | 24 | 1,41 | 8 | 1 |
| `selected_hemogram` | 32 | 68 | **2,12** | 45 | 9 |
| `hemogram_history` | 21 | 41 | 1,95 | 27 | 7 |

El modo contextual no es lento por tener más tokens —el prompt es casi igual—
sino porque **activa más contrato y por tanto más llamadas**.

---

## 9. `generation_repair_failed`: el coste

17 casos. Todos con `final_state: failed`, `state: failed_retryable`,
`response: null`.

- GPU consumida por esos 17 turnos: **1.875 s = 38,1 % de todo el cómputo de la
  batería**.
- Desperdicio medio por caso: **110,3 s**.
- Contenido entregado al usuario: **cero**.

Más de un tercio del tiempo de GPU de la batería se gastó en producir nada.

---

## 10. Contexto clínico: ¿llegó al modelo?

Para los casos con hemograma seleccionado, la telemetría publica
`context_bundle_patient_loaded: true` y **`context_bundle_omitted_fact_count: 0`**
y `authorized_code_count: 18` (los 18 analitos del panel).

**El contexto clínico se cargó completo y no se omitió ningún hecho.** Por
tanto, cuando el asistente respondió *«No tengo acceso a los valores específicos
del paciente»* (`SEL-07`), esa afirmación es **falsa respecto del estado del
backend**: los datos estaban cargados y autorizados.

Ahora bien — y esto es la distinción que el encargo exige mantener — que
estuvieran **cargados en el backend** no demuestra que estuvieran **dentro del
prompt**: el texto del prompt no es observable (§4). Lo que sí está confirmado
es que `estimated_input_tokens` ≈ 3.900 y `prompt_eval_count` ≈ 3.871, cifras
coherentes con un panel de 18 analitos inyectado. 

**Clasificación:** `FALSE_DATA_ACCESS_DENIAL` con nivel **EVIDENCIA_FUERTE**,
no `CONFIRMADO`. Confirmarlo exige ver el prompt.

---

## 11. Lo que NO causa los problemas

Descartado con datos, para que la siguiente etapa no persiga fantasmas:

| Sospechoso | Veredicto | Evidencia |
|---|---|---|
| Cola / concurrencia | **descartado** | `queue_duration_ms` mediana 0 ms, máx 1 ms |
| Red / TTFB | **descartado** | TTFB 0,2 s en las 70 |
| RAG | **descartado** | 8 activaciones, 183–655 ms |
| CPU fallback | **descartado** | `full_gpu` en 133/133 |
| Arranque en frío | **descartado** | `load_duration_ms` mediana 527 ms |
| Prompt de reparación inflado | **descartado** | 3.882 vs 3.884 tokens |
| Velocidad degradada en reparación | **descartado** | 13,05 vs 13,06 tok/s |
| Backend lento | **descartado** | 0,4 % de la latencia total |
| Contexto clínico no cargado | **descartado** | `omitted_fact_count: 0` |
| El modelo «no sabe» | **descartado** | misma pregunta responde bien (§7) |

---

## 12. Causa raíz

**CONFIRMADO** — La latencia es cómputo de modelo repetido. 99,6 % del tiempo
está dentro de Ollama; el sistema invoca al modelo 1,9 veces por pregunta y
descarta el 60 % de lo generado.

**CONFIRMADO** — El contrato estructurado, no la seguridad clínica, es lo que
dispara la mayoría de los rechazos: 7 de 133 son barreras de seguridad.

**CONFIRMADO** — Con entrada idéntica hasta el token, el desenlace difiere.

**EVIDENCIA_FUERTE** — El modelo produce el contenido correcto y falla al
etiquetarlo: en `SEL-08` la reparación a temperatura 0,1 reincide en el mismo
detalle (`PLT:value,PLT:unit`), lo que sugiere una exigencia que el modelo no
satisface de forma fiable más que mala suerte.

**HIPOTESIS** — Que el texto de la primera generación fuera clínicamente
correcto. No es verificable con la instrumentación actual.

**NO_OBSERVABLE** — El texto generado, el prompt efectivo y los fragmentos de
RAG inyectados.

---

## 13. Lagunas de observabilidad y la instrumentación mínima

**No se implementa nada en esta fase.** Se documenta qué haría falta.

| # | Laguna | Dónde desaparece | Instrumentación mínima | Coste |
|---|---|---|---|---|
| 1 | **Texto generado y rechazado** | Se evalúa en memoria y se descarta | **Ya existe**: `CHAT_STRUCTURED_DEBUG_DIR` (`send_chat_message.py:301`) vuelca la envoltura íntegra con sus claims. Está vacía en producción | Cambio de entorno. Escribe texto de paciente en disco: encender para un diagnóstico y apagar |
| 2 | **Prompt efectivo** | Nunca se registra; sólo su tamaño | Registrar hash + tamaño por sección, o el texto bajo la misma bandera que #1 | Sin instrumentación no hay forma de comparar prompt 1 y 2 |
| 3 | **Fragmentos de RAG inyectados** | `llm_chat.retrieval` publica recuentos y scores, no `chunk_id` ni texto | Añadir `chunk_ids` a la telemetría (no requiere texto) | Bajo, y sin exponer contenido |
| 4 | **`request_id` en el cliente** | El sobre de error lo trae, pero no los turnos correctos | Que el evento `final` incluya `request_id` | Evitaría toda la correlación temporal de §5 |
| 5 | **`ollama_metrics` sin `request_id`** | Se emite suelto | Añadir `request_id` | Hoy se recupera por cercanía temporal |
| 6 | **Sobre de error completo en SSE** | El cliente sólo captura `code` y `message` | Es del arnés, no de producción: ya corregido para futuras ejecuciones | — |

---

## 14. Prioridades para una futura etapa de mitigación

Sin implementar nada. Ordenadas por evidencia disponible y coste.

| # | Acción | Por qué, con la cifra que lo respalda |
|---|---|---|
| 1 | **Encender `CHAT_STRUCTURED_DEBUG_DIR` para un diagnóstico acotado** | Es lo único que convierte la hipótesis principal en hecho. Sin ello no se sabe si el contenido rechazado era correcto |
| 2 | **Revisar la exigencia de `policy_rule_id`** | Es el detalle que más rechazos causa (15 de todos), y es un identificador, no contenido clínico |
| 3 | **Activar el «salvage» de envoltura ya escrito** | El commit `bd70e0d8` lo implementa y dice explícitamente que **no está conectado a un turno**. Evitaría regenerar entero por un claim malo: hoy eso cuesta 41,6 % del cómputo |
| 4 | **Reconsiderar el último recurso** | Recorta el prompt de 3.871 a 1.374 tokens y falla con un error distinto. Gasta 20 s más para cambiar de problema |
| 5 | **Corregir la falsa afirmación de incapacidad** | `omitted_fact_count: 0` demuestra que el contexto estaba cargado cuando el asistente dijo no tenerlo |
| 6 | **No tocar el modelo ni la GPU** | 100 % en GPU, 13 tok/s estables, sin cold start, sin cola. La infraestructura no es el problema |

---

## 15. Artefactos y verificación de integridad

Todos en `validacion_llm/resultados/auditoria_2026-08-08/`.

| Fichero | Contenido |
|---|---|
| `AUDITORIA_CORRELACIONADA.json` | Autopsia por caso: entrada, routing, plan, cada llamada al modelo con config/tokens/veredicto, SSE, estado del turno y eventos crudos |
| `AUDITORIA_LLM_TIMELINE_2026-08-08.csv` | 1.792 filas — un evento por fila, cliente y backend |
| `AUDITORIA_LLM_METRICAS_2026-08-08.csv` | 133 filas — **una por llamada al modelo** |
| `AUDITORIA_LLM_INTEGRIDAD_2026-08-08.json` | SHA-256 de cada artefacto + comprobaciones |
| `backend_telemetry_raw.log` | 1.502 líneas de telemetría cruda, sin transformar |
| `ollama_timings_raw.log` | 4.472 líneas de `llama-server`, 138 tareas |
| `repeticion_plt_2026-08-08.jsonl` | Repetición diagnóstica (§16) |

Comprobaciones, todas en verde: 70/70 casos presentes, con pregunta, inicio,
respuesta o error, eventos SSE, latencia, estado de servidor y **correlación
verificada por contenido**; ninguna respuesta truncada. La única comprobación
en falso es `raw_generation_observable: false`, que es el gap de §13.

---

## 16. Repetición diagnóstica: el paso de reparación no repara

Se relanzó *«¿Cómo están las plaquetas?»* —la pregunta de §7— **diez veces** en
conversaciones independientes, misma configuración, sin tocar nada. El prompt de
la primera llamada fue de **3.871 tokens en las diez** (`CONFIRMADO`: valor
único en el conjunto), así que la entrada es constante y lo único que varía es
el muestreo.

| Ejecución | Llamadas | Veredicto #1 | Veredicto #2 (reparación) | Veredicto #3 (último recurso) | Final |
|---|---:|---|---|---|---|
| REP-PLT-01 | 3 | `PLT:value,PLT:unit` | `PLT:value,PLT:unit` | `policy_rule_id_missing` | ❌ |
| REP-PLT-02 | 3 | `PLT:value,PLT:unit` | `PLT:value,PLT:unit` | `valid` | ✅ |
| **REP-PLT-03** | **1** | **`valid`** | — | — | ✅ **26,0 s** |
| REP-PLT-04 | 3 | `PLT:value,PLT:unit` | `PLT:value,PLT:unit` | `policy_rule_id_missing` | ❌ |
| REP-PLT-05 | 3 | `PLT:value,PLT:unit` | `PLT:value,PLT:unit` | `policy_rule_id_missing` | ❌ |
| REP-PLT-06 | 3 | `PLT:value,PLT:unit` | `PLT:value,PLT:unit` | `policy_rule_id_missing` | ❌ |
| REP-PLT-07 | 3 | `PLT:value,PLT:unit` | `PLT:value,PLT:unit` | `valid` | ✅ |
| REP-PLT-08 | 3 | `PLT:value,PLT:unit` | `PLT:value,PLT:unit` | `valid` | ✅ |
| REP-PLT-09 | 3 | `PLT:value,PLT:unit` | `PLT:value,PLT:unit` | `valid` | ✅ |
| REP-PLT-10 | 3 | `PLT:value,PLT:unit` | `PLT:value,PLT:unit` | `policy_rule_id_missing` | ❌ |

### Lo que esto establece

**1. La primera generación satisface el contrato 1 de cada 10 veces.**
`CONFIRMADO`. Nueve de diez fallan, **siempre por el mismo detalle**:
`PLT:value,PLT:unit`. No es ruido disperso; es una exigencia concreta que el
modelo incumple de forma sistemática.

**2. El paso de reparación tiene una tasa de éxito del 0 %.** `CONFIRMADO`.
Nueve intentos, **cero correcciones**, y las nueve fallan con el mismo detalle
que motivó la reparación. Bajar la temperatura a 0,1 y usar el perfil
`..._structured_repair` no cambió el resultado ni una sola vez.

> Ese paso consumió **~23 s de GPU en cada una de las nueve ejecuciones —unos
> 207 s— sin arreglar nada**. Extrapolado a la batería completa, es la mayor
> parte de los 2.046 s gastados en reparaciones.

**3. Lo que salva el turno es el último recurso, no la reparación.** 4 de 9.
Pero introduce un fallo nuevo, `policy_rule_id_missing`, en los otros 5. La
probabilidad compuesta (10 % + 90 % × 0 % + 90 % × 44 % ≈ 50 %) coincide con el
**5/10** observado.

**4. La variabilidad no es «temperatura alta».** A 0,3 en la primaria y **0,1**
en la reparación, el desenlace sigue partido por la mitad. La causa no es que el
muestreo sea ruidoso, sino que **el contrato pide una estructura que el modelo
acierta rara vez**, y el mecanismo previsto para corregirlo no corrige.

### Consecuencia para la etapa de mitigación

La prioridad #3 de §14 —conectar el «salvage» de envoltura ya escrito en
`bd70e0d8`— sube al primer puesto en cuanto a relación coste/beneficio: el paso
de reparación tal y como está hoy es **coste puro**. Y la prioridad #2 —revisar
la exigencia de `policy_rule_id`— se confirma como el segundo cuello: es lo que
mata al último recurso 5 de 9 veces.

Datos crudos: `repeticion_plt_2026-08-08.jsonl`,
`AUDITORIA_REPETICION.json`, `backend_telemetry_repeticion.log`.

---

*Auditoría del 8 de agosto de 2026. Fase de diagnóstico: no se corrigió,
optimizó ni modificó nada del sistema medido.*
