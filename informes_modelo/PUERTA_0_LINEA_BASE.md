# Puerta 0 — línea base verificada e instrumentación desplegable

**Rama:** `fase-0-instrumentacion` · **Commit:** `3baafc10`
**Fecha:** 2026-08-12
**Alcance:** instrumentación pura. Cero cambios de comportamiento.

Toda cifra lleva su marca: `[MEDIDO]` sale de un fichero de este repositorio y
se puede recalcular; `[DERIVADO]` es aritmética sobre cifras medidas;
`[INFERIDO]` es una lectura razonada que **no** está medida.

---

## 1. Verificación de las premisas antes de tocar nada

El prompt maestro y los tres informes de `informes_modelo/` afirman cosas sobre
el código y sobre la batería. Se comprobaron **una a una** antes de escribir
código, porque el plan entero depende de que sean ciertas.

### 1.1 Estructura del código — todas las rutas y líneas citadas existen

| Afirmación | Verificación | Estado |
|---|---|---|
| `payload["format"] = request.response_schema` | `openai_compatible_client.py:870` | `[MEDIDO]` ✅ |
| Sobre `GeneratedResponseEnvelope` con `claim_id` regex, `fact_ids`, `source_ids`, `policy_rule_ids`, `evidence_spans` | `structured_response.py:117-263` | `[MEDIDO]` ✅ |
| Reparación tras `needs_repair` | `send_chat_message.py:1723` | `[MEDIDO]` ✅ |
| `_steered_candidate` como rescate posterior | `send_chat_message.py:1933` → def. `4644` | `[MEDIDO]` ✅ |
| `_last_resort_candidate` como rescate posterior | `send_chat_message.py:1969` → def. `4503` | `[MEDIDO]` ✅ |
| Selección de hechos por *tool call* | `_facts_the_model_asked_for`, def. `4429` | `[MEDIDO]` ✅ |
| `httpx.AsyncHTTPTransport(retries=…)` | `composition.py:674-675` | `[MEDIDO]` ✅ |
| `_stream_mode()` devuelve siempre `buffered_validated` | `send_chat_message.py:4408` y su comentario | `[MEDIDO]` ✅ |

**Cinco vías llegan al proveedor**, no dos. Están confirmadas y ahora, además,
etiquetadas en el código.

### 1.2 Cifras de la batería A100 — cuadran exactamente

Recalculadas desde `validacion_llm/resultados/rondas45_2026-08-10/bateria_a100.jsonl`:

| Métrica | Informe | Recalculado | |
|---|---|---|---|
| Turnos | 45 | **45** | ✅ |
| Reparados | 10 · 22,2 % | **10 · 22,2 %** | ✅ |
| Válidos en primera pasada | 35 · 77,8 % | **35 · 77,8 %** | ✅ |
| Fallos finales | 0 | **0** | ✅ |
| Mediana sin reparación | 16,3 s | **16,30 s** | ✅ |
| Mediana con reparación | 44,05 s | **44,05 s** | ✅ |
| Factor | ×2,7 | **×2,70** | ✅ |
| General | 0/15 | **0/15 · 0 %** | ✅ |
| Seleccionado | 3/15 | **3/15 · 20,0 %** | ✅ |
| Historial | 7/15 | **7/15 · 46,7 %** | ✅ |
| Longitud de respuesta | mediana 71 · p95 120 · máx 126 palabras | **71 · 120 · 126** | ✅ |

`[MEDIDO]`. Ni una discrepancia.

### 1.3 La afirmación que sostiene el orden de las fases

El campo `etapas` de cada turno reparado conserva el motivo. Desglose completo:

| Motivo | n | Clase |
|---|---|---|
| `structured_patient_fact_id_required` | 3 | semántico |
| `missing_evidence_attribution` | 2 | semántico |
| `content_free_answer` | 2 | semántico |
| `ambiguous_parameter_claim` | 1 | semántico |
| `structured_json_invalid` | 1 | **estructural** |
| `structured_schema_invalid` | 1 | **estructural** |

**8 semánticas · 2 estructurales.** `[MEDIDO]`

Consecuencia directa, y es la que gobierna todo el plan: cambiar de serializador
o de formato habría arreglado **2 de 10**. Quitar el requisito de metadatos
arregla **8 de 10**. Y poner `CHAT_MAX_GENERATION_ATTEMPTS=1` **hoy** convertiría
los 10 en fallos: 22,2 % global y 46,7 % en historial. El arbitraje A-1 del
prompt maestro queda sostenido por medición.

### 1.4 Una corrección a la configuración citada

`[MEDIDO]` El fichero local `.env.production` (5-ago, **sin versionar**) dice
`OLLAMA_NUM_PREDICT=2048`, `OLLAMA_CONTEXT_LENGTH=65536`,
`CHAT_MAX_INPUT_TOKENS=60000`. **No es lo que se despliega.**

Lo que se despliega es `secrets.PRODUCTION_ENV_B64`, actualizado por última vez
el **2026-08-06T16:08:23Z**, y `scripts/actualizar_secreto_produccion.sh`
(6-ago) sobrescribe esas tres claves con **16 384 / 12 000 / 1 280** — los
valores que cita el prompt maestro. La desalineación de `num_ctx` (app 16 384
frente a servidor 65 536) **sigue activa**.

Y el script conserva el motivo de haberla creado:

> «Los prompts reales pesan ~1.700 tokens; 65536 era ×20 y la VRAM ociosa es lo
> que impedía una segunda ranura de generación.»

`[INFERIDO]` Ese motivo era válido para la **L4 de 24 GB**. Sobre la A100 de
40 GB con `OLLAMA_NUM_PARALLEL=1` no hay segunda ranura que habilitar, así que
el argumento que justificó bajar a 16 384 ya no aplica. Esto refuerza la Fase 1,
pero conviene decirlo: **la decisión no fue un descuido, fue una decisión
correcta para otro hardware.**

---

## 2. Qué se ha construido

Instrumentación, nada más. `999` tests pasan (12 nuevos), `ruff` limpio.

### 2.1 `domain/provider_call_ledger.py` — el contador

Un registro por turno en un `ContextVar`. Cuenta **cada POST de generación**,
etiquetado por ruta.

Dos decisiones que importan:

- **Se cuenta ANTES del POST, no al recibir la respuesta.** Una petición que
  sale y muere por red también consumió su llamada; contar solo las que
  responden ocultaría justo el caso que hay que vigilar.
- **Vive en el dominio, no en infraestructura.** Es una primitiva pura sin E/S,
  y así tanto la aplicación como el adaptador lo importan en la dirección
  correcta de la arquitectura.

**No cuenta**, por diseño: calentamiento (`/api/generate`), sondeos de salud,
`/api/show`, `/api/ps`, `/api/tags`, recuperación RAG y embeddings. Un turno que
no llega al proveedor cuenta **0**, que es un valor legítimo del invariante.

### 2.2 Las cinco rutas, etiquetadas

Vocabulario en `domain/entities.py`; campo `generation_route` en `ModelRequest`
con valor por defecto, de modo que los 18 constructores existentes siguen
siendo válidos sin tocarlos.

| Ruta | Sitio |
|---|---|
| `main` | `_execute`, generación principal |
| `repair` | `_execute`, reparación |
| `tool` | `_facts_the_model_asked_for` |
| `last_resort` | `_last_resort_candidate` |
| `steer` | `_steered_candidate` |

La ruta **se declara** en cada llamada a `_generate`. No se deduce del número de
intento, porque `generation_attempt` no distingue reconducción de último recurso.

### 2.3 Telemetría nueva por llamada

Ya existían `total_duration`, `load_duration`, `prompt_eval_duration`,
`eval_duration`, `prompt_eval_count`, `eval_count`. Se añaden:

- **`done_reason`** — la que decide si el bucle de reparación funcionó alguna vez.
- **`residual_duration_ms`** = `total − (carga + prefill + decode)`. Es el tiempo
  que el proveedor gasta fuera de las tres fases que sí desglosa: compilación de
  gramática, serialización, cola. Sin él, un turno lento parece inexplicable
  aunque las tres fases sumen poco.
- Segregación por `generation_route`, `provider_call_index`, `num_ctx_requested`,
  `num_predict_requested`, `structured_output`, `profile_name`, `size_vram`.

### 2.4 La aserción del invariante

`provider_call_ledger` y `single_call_invariant_violated` se emiten al cerrar el
turno. **Solo registran.** Convertirlo en excepción es trabajo de la Fase 4:
hacerlo ahora convertiría los 10 turnos que hoy se reparan en 10 turnos
fallidos, que es exactamente el error que el orden de fases existe para impedir.

---

## 3. Qué NO puede responder esta puerta sin una corrida en vivo

La línea base `bateria_a100.jsonl` guarda diez campos: `id_caso`, `pregunta`,
`respuesta`, `scope`, `segundos`, `etapas`, `reparo`, `codigo_error`,
`n_case_facts`, `n_fuentes`. **Ninguna métrica de servidor.**

Por tanto quedan abiertas, y solo se cierran con la instrumentación desplegada:

| Pregunta de la Puerta 0 | Por qué no se puede contestar hoy |
|---|---|
| ¿Cuántas llamadas hace **realmente** cada turno? | `reparo` es booleano; no distingue reparación de reconducción ni de último recurso |
| ¿Las reparaciones terminan por EOS o por `length`? | `done_reason` no consta en ningún registro |
| ¿Cuál es el `prompt_eval_duration` real, y por tanto el acierto de caché? | No consta |
| ¿Cuánta VRAM ocupa el runner y con qué `num_ctx` efectivo? | No consta |

`[INFERIDO]` — la hipótesis que más importa contrastar: la reparación usa
`CHAT_REPAIR_NUM_PREDICT` (1 024) mientras la principal usa `OLLAMA_NUM_PREDICT`
(1 280). Si el fallo original fue truncamiento, **reparar con un 20 % menos de
presupuesto trunca antes**. Si `done_reason == "length"` domina en las
reparaciones, el bucle nunca funcionó y llevamos meses pagando ×2,7 de latencia
por un rescate que no rescata. El valor 1 024 procede del `.env.production`
local del 5-ago y el script del 6-ago no lo sobrescribe, así que es plausible
que sea el desplegado, pero **no está verificado contra el secreto**.

---

## 4. Lo que hace falta para cerrar la Puerta 0

El arnés de la batería apunta a `https://hemovet.app`, es decir, al código
desplegado. La telemetría nueva solo produce datos si se despliega.

Secuencia mínima, y ninguno de los pasos cambia el comportamiento del chat:

1. Mezclar `fase-0-instrumentacion` y desplegar. Es instrumentación pura: 999
   tests en verde y ni una rama de decisión nueva.
2. Encender la GPU. Correr las 45 preguntas.
3. Recoger `provider_calls`, `done_reason` por ruta, `prompt_eval_duration` del
   turno 1 frente al 2+, `size_vram` y `num_ctx` efectivo.
4. **Apagar la GPU verificando `TERMINATED`.**

Sin ese paso, las Fases 1 a 6 se pueden diseñar pero no se pueden puntuar: no
habría con qué comparar el después.

---

## 5. Hipótesis vivas

1. **El bucle de reparación nunca funcionó.** Se contrasta con `done_reason` por
   ruta. Si domina `length`, el rescate reproduce el fallo que debía arreglar.
2. **La reutilización de caché de prefijo es ~13 %.** Cifra que circula en los
   informes; **no se ha recalculado en esta auditoría** y el indicador correcto
   es `prompt_eval_duration`, no `prompt_eval_count`.
3. **La utilización de ancho de banda del 44,6 % sigue sin explicar.** Candidatos
   citados: kernels de Gated DeltaNet y descuantización de la KV `q8_0`. No es
   una palanca hasta medirla.
4. **El `CHAT_REPAIR_NUM_PREDICT` desplegado.** Plausiblemente 1 024; no
   verificado contra el secreto.
