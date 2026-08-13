# Auditoría del asistente LLM de HemoVet — 5 de agosto de 2026

> Informe de la revisión pedida el 5-ago: ejecutar la batería completa de
> `preguntas_prueba_llm_contextos_reales.md` contra el sistema real y revisar
> backend, frontend, base de datos y servidor en busca de fallos,
> inconsistencias y oportunidades de mejora, con foco en el LLM en sus tres
> modos de contexto.

---

## 1. Resumen ejecutivo

El asistente **no falla por el modelo**. Falla porque, entre el modelo y el
usuario, hay una capa de validadores que exigen que la respuesta contenga
**palabras exactas de una lista cerrada**. Cuando el modelo dice lo correcto
con otras palabras — que es lo normal, sobre todo con `OLLAMA_TEMPERATURE=0.6`
en producción — el validador rechaza el turno, se reintenta una vez, la
reparación tampoco acierta la fórmula, y **el usuario recibe HTTP 502 sin
ninguna respuesta**.

Ese patrón único explica la mayoría de los fallos observados. No es un
problema de capacidad del modelo: en varios casos la respuesta generada era
correcta y se descartó por la redacción.

Tres hallazgos adicionales, fuera del LLM, son igual de importantes:

| Hallazgo | Impacto |
|---|---|
| **El logout borra permanentemente el historial de chat** (`ON DELETE CASCADE`) | Explica directamente la queja "el chat no recuerda nada" |
| **La app no soporta dos usuarios a la vez**: con 3 peticiones simultáneas, 2 murieron con HTTP 429 | Riesgo alto en una demostración con público |
| **`save_analysis` puede abortar en PostgreSQL** por texto sin truncar | Un hemograma se pierde en silencio al subirlo |

---

## 2. Metodología

- **Entorno probado:** producción real (`https://hemovet.app`), cuenta de
  prueba, mascota Lucas, hemograma del 4-jul-2026 con 19 parámetros.
- **Modelo desplegado:** `qwen3.6:27b-q4_K_M`, contexto 65536, verificado por
  digest (`/api/v1/chat/health` → `identity_verified: true`).
- **Transporte:** el mismo endpoint SSE que usa el frontend
  (`POST /api/v1/chat/stream`), no el POST simple, para reproducir el camino
  real del usuario.
- **Ejecución secuencial, no concurrente.** Se comprobó primero que la
  concurrencia no es viable (ver §4.1): lanzar las preguntas en paralelo
  habría fabricado fallos de cola que no dicen nada del asistente.
- **Registro por pregunta:** eventos SSE completos, etapas, motivo de
  reparación, código de error, intención detectada, política de recuperación,
  tokens y tiempo.

> **Importante para leer los resultados:** la batería se ejecutó contra el
> código **desplegado**, que no incluye ninguna de las correcciones de este
> informe. En §6 se indica, fallo por fallo, cuál queda ya corregido en el
> árbol de trabajo y cuál sigue abierto.

---

## 3. La causa raíz común: validadores de lista cerrada

Casi todos los validadores del contrato de respuesta comprueban la redacción
con una expresión regular que enumera unas pocas frases. Si la respuesta no
contiene ninguna, el turno se descarta.

Ejemplo medido antes de corregir — 12 formas correctas de expresar una
limitación clínica, **9 rechazadas**:

| Frase del modelo | Veredicto del validador |
|---|---|
| "No puedo emitir diagnósticos ni recomendar tratamientos." | ❌ rechazada |
| "No realizo diagnósticos; consulta a un veterinario." | ❌ rechazada |
| "No tengo acceso a datos clínicos en este momento." | ❌ rechazada |
| "Un valor alto no significa que haya enfermedad." | ❌ rechazada |
| "Esta información no reemplaza la evaluación profesional." | ❌ rechazada |
| "Este análisis no sustituye la consulta veterinaria." | ✅ aceptada |

Lo que agrava el problema: **el modelo nunca es informado de la lista**. El
prompt de reparación le dice el código de error (`limitation_claim_invalid`)
pero no qué redacción se espera, así que el segundo intento cae fuera de la
lista igual que el primero. Dos fallos → 502.

Y como la temperatura de producción es 0.6 (en desarrollo es 0.1), la misma
pregunta produce redacciones distintas en cada intento: **por eso el fallo es
intermitente** y por eso aparecía "a veces" desde el frontend y no al probar
con curl.

---

## 3.bis Familias de fallo observadas y estado de corrección

Cada fila es un código de error real capturado en producción durante la
batería, con el archivo donde vive la causa y si ya está corregido en el árbol
de trabajo (pendiente de desplegar).

| Código de error | Causa | Dónde | Estado |
|---|---|---|---|
| `limitation_claim_invalid` | Lista cerrada de ~10 frases para expresar una limitación; 9 de 12 redacciones correctas rechazadas | `structured_response.py` (`validate_support`) | ✅ corregido |
| `structured_numeric_support_required` | Cualquier dígito invalidaba un claim conversacional, incluso sin hemograma cargado; la propia instrucción pide enumerar "los tres contextos" | `send_chat_message.py` | ✅ corregido |
| `intent_mismatch_capabilities` | Exigía la cadena literal "hemogramas caninos"; "el hemograma de tu perro" se rechazaba | `response_contracts.py` (`_SCOPE`) | ✅ corregido |
| `intent_mismatch_identity` | Exigía "inteligencia artificial"; "asistente digital" se rechazaba. La regla estaba **duplicada** en dos archivos con contenido distinto | `response_contracts.py` + `send_chat_message.py` | ✅ corregido y unificado |
| `structured_fact_claim_mismatch` | Un claim que cita más `fact_ids` de los que su texto nombra mata el turno entero. Cuantos más parámetros tiene el estudio, más probable (el de Lucas tiene 19) | `send_chat_message.py` | ✅ corregido (se descartan los sobrantes) |
| `structured_patient_fact_not_materialized` | El texto debía usar **solo** palabras del propio dato. De 4 redacciones correctas del mismo valor, 3 rechazadas; el nombre del propio paciente contaba como invención | `send_chat_message.py` | ✅ corregido |
| `evidence_claim_mismatch` / `evidence_span_not_found` | La cita debía reproducir literalmente una frase de una fuente en inglés dentro de una respuesta obligatoriamente en español | `structured_response.py` | ✅ corregido (se descarta la cita, no la respuesta) |
| `mandatory_diagnosis_boundary` | Cuatro frases admitidas para expresar incertidumbre diagnóstica; "no significa necesariamente que exista una enfermedad" no era una de ellas | `response_contracts.py` (`_UNCERTAINTY`) | ✅ corregido |
| `structured_patient_fact_id_required` | En chat general **sin ningún hemograma**, nombrar "hematocrito" se trataba como filtrar un dato del paciente | `send_chat_message.py` | ✅ corregido |
| `structured_unlinked_clinical_claim` | La regla no distinguía afirmar de negar: "no puedo decirte qué causa la anemia" se bloqueaba igual que "la anemia causa debilidad" | `send_chat_message.py` | ✅ corregido |
| `missing_veterinary_referral` | El contrato anunciaba al modelo `veterinary_referral_required: false` y otro validador la exigía | `send_chat_message.py` | ✅ corregido (ambos lados) |
| `LLM_PROVIDER_READ_TIMEOUT` | `OLLAMA_TIMEOUT_SECONDS=90` es menor que lo que tarda un resumen completo con `OLLAMA_NUM_PREDICT=2048` en el 27B | `.env.production` | ⚙️ configuración, §4.3 |
| `generation_queue_timeout` | Un solo turno a la vez con 20 s de espera máxima | `.env.production` | ⚙️ configuración, §4.1 |
| `structured_schema_invalid` | El modelo devolvió JSON que no cumple el esquema | modelo | ❌ abierto |

**Verificación:** cada corrección se comprobó con un banco de pruebas local
que reproduce el fallo antes del cambio y lo resuelve después, incluyendo
casos que **deben seguir fallando** (afirmaciones clínicas inventadas, valores
que no existen, identidad humana, temas fuera de ámbito). Suite completa del
backend: **966 pasando, 4 fallos preexistentes idénticos al baseline, 0
regresiones**.

---

## 4. Hallazgos de servidor e infraestructura

### 4.1 La aplicación no admite dos usuarios simultáneos — CRÍTICO

Prueba directa contra producción, 3 peticiones a la vez:

| Petición | Resultado | Tiempo |
|---|---|---|
| 1 | HTTP 502 `generation_repair_failed` | 114,7 s |
| 2 | **HTTP 429 `generation_queue_timeout`** | 21,4 s |
| 3 | **HTTP 429 `generation_queue_timeout`** | 20,8 s |

Configuración responsable (`.env.production`):

```
CHAT_MAX_CONCURRENT_GENERATIONS=1     # una generación a la vez
CHAT_QUEUE_TIMEOUT_SECONDS=20         # se espera como máximo 20 s en cola
OLLAMA_NUM_PARALLEL=1
BACKEND_WEB_CONCURRENCY=1
```

Una generación tarda entre 20 s y 115 s, pero la cola solo espera 20 s. **La
segunda persona que escriba mientras otra está esperando recibe un error.** En
una defensa de tesis, si la profesora y un estudiante preguntan a la vez, uno
de los dos ve el chat caído.

**Corrección:** subir `CHAT_QUEUE_TIMEOUT_SECONDS` por encima del tiempo de
generación real (p. ej. 150 s, alineado con `CHAT_TOTAL_TIMEOUT_SECONDS`), o
elevar `OLLAMA_NUM_PARALLEL`/`CHAT_MAX_CONCURRENT_GENERATIONS` a 2 y medir el
impacto en VRAM de la L4. Lo mínimo e inmediato es el timeout de cola: no
cuesta memoria, solo hace esperar en vez de rechazar.

### 4.3 El timeout del proveedor corta respuestas legítimas — ALTO

`SEL-03` ("Resume el hemograma completo de Lucas en palabras sencillas")
murió a los **90,5 s** con `LLM_PROVIDER_READ_TIMEOUT`. No es casualidad:

```
OLLAMA_TIMEOUT_SECONDS=90        # límite por generación
OLLAMA_NUM_PREDICT=2048          # hasta 2048 tokens de salida
CHAT_TOTAL_TIMEOUT_SECONDS=150   # límite total del turno
```

Un resumen de 19 parámetros con un modelo de 27B cuantizado no cabe en 90 s.
El presupuesto por generación es menor que lo que la propia configuración
permite generar, así que la pregunta más natural sobre un hemograma —
"resúmemelo" — está condenada a fallar por reloj.

**Corrección:** subir `OLLAMA_TIMEOUT_SECONDS` (p. ej. 120 s, dejando margen
bajo los 150 s totales) o bajar `OLLAMA_NUM_PREDICT` a un valor alcanzable.
Las dos palancas están en `.env.production`, no en código.

### 4.2 Latencias de 20 a 120 segundos

Tiempos medidos: 18–30 s cuando la respuesta sale al primer intento; 40–123 s
cuando hay reparación (son dos generaciones completas). Cada fallo de
validación **duplica** la espera antes de devolver un error.

Esto convierte cada bug de §3 en un problema doble: el usuario espera dos
minutos para no recibir nada.

---

## 5. Hallazgos de base de datos

Verificados directamente sobre el código, no solo reportados.

### 5.1 El logout destruye el historial de conversaciones — CRÍTICO

`backend/app/modules/auth/router.py:76` ejecutaba:

```python
db.execute(delete(ChatSession).where(...))
```

Y en `backend/app/modules/llm_chat/models.py:98,181`, tanto `chat_messages`
como `chat_turns` referencian `chat_sessions` con `ondelete="CASCADE"`.
**Cerrar sesión borraba para siempre todas las transcripciones de ese login.**

El propio repositorio del chat documenta que esto no debe pasar nunca
(`sqlalchemy_repositories.py`, `get_or_create`):

> *"it must never hard-delete a ChatSession row, because that cascades
> (ondelete="CASCADE") to every ChatMessage/ChatTurn and permanently destroys
> the transcript this method is supposed to be resuming"*

El endpoint de autenticación rompía esa invariante desde fuera del módulo.
Esta es, con diferencia, la explicación más probable de la queja repetida de
que **el asistente no recuerda conversaciones anteriores**.

**Estado: corregido.** El logout ahora marca las sesiones como `closed`
(`status` ya es el filtro que usan `get_or_create` y `list_active`), y el
historial sobrevive en PostgreSQL.

### 5.2 Un hemograma puede perderse al guardarse — ALTO

`backend/app/db/queries.py` escribía `analysis_parameters` **sin truncar** los
campos de texto, mientras la migración `0007` que rellena esas mismas filas sí
trunca a `[:80]`, `[:120]`, `[:180]`, `[:60]`.

`original_name` procede literalmente del PDF extraído y no tiene longitud
acotada; la columna es `VARCHAR(180)`. En PostgreSQL eso lanza
`StringDataRightTruncation` y **aborta toda la transacción de `save_analysis`**:
el hemograma completo no se guarda. En SQLite las longitudes se ignoran, por
eso la suite de tests nunca lo detectó.

**Estado: corregido.** Se replicaron los mismos truncados de la migración 0007.

### 5.3 Otros hallazgos de BD (no corregidos, documentados)

| # | Ubicación | Problema |
|---|---|---|
| 1 | `alembic/versions/0001_*.py:16` | La migración base es `Base.metadata.create_all()`, es decir, el modelo *actual*. Una columna añadida sin migración se crea igual en BD nueva → el test de migraciones no puede detectar deriva. Su `downgrade()` es `drop_all` (borra `analyses`, `pets`, `users`). |
| 2 | `config.py:248` + repositorios | `CHAT_SESSION_TTL_SECONDS` nunca purga nada: `expires_at` solo filtra listados. No hay retención para `chat_turn_attempts`, que crece sin techo. Una conversación "vencida" desaparece de la lista pero sigue siendo recuperable por id. |
| 3 | `sqlalchemy_repositories.py:611` | El manejador de `IntegrityError` asume que el conflicto siempre es `idempotency_key`, pero la tabla tiene 3 constraints únicas. Dos pestañas del mismo usuario producen un 500 en vez de un 409. |
| 4 | `sqlalchemy_repositories.py:2368` | `classifier_outcome` devuelve `None` cuando `active_labels` está vacío, sin distinguir "el clasificador no detectó patrón" de "no hay salida del clasificador". El asistente no puede decir *"el motor ML no detectó ningún patrón"*, se comporta como si nunca hubiera corrido. |
| 5 | `db/queries.py:247` ← `formatter.py:364` | `Analysis.extraction_confidence` guarda la confianza **del clasificador ML**, y el chat la presenta al modelo como calidad de digitalización del documento. Son cosas distintas. |
| 6 | `conversation_facts.py:69`, `sqlalchemy_repositories.py:1316,1818,275` | Cuatro consultas sin `LIMIT` en el camino caliente del chat, incluida la que carga **todos** los análisis y parámetros de la mascota en cada turno del modo historial. |
| 7 | `models.py:172`, `:84` | Los índices ponen `context_revision` en segunda posición, pero las consultas reales filtran solo por `session_id` y ordenan por `turn_index`: el índice no sirve el `ORDER BY`. |
| 8 | `db/session.py:12` | El engine usa los defaults de pool (15 conexiones) y lo comparten el ejecutor bloqueante del chat (hasta 16 hilos), los endpoints síncronos y `db/queries.py`. `CHAT_DB_BLOCKING_MAX_CONCURRENCY=16` agota el pool. |
| 9 | `db/queries.py:232`, `formatter.py:356` | `datetime.now()` (hora local del contenedor) mezclado con `utc_now()` del resto del sistema, en columnas sin `timezone`. Un cambio de zona horaria desordena el historial longitudinal. |
| 10 | `models.py:232` | `RetrievalEvent` es una tabla muerta: no se persiste qué fuentes vio el modelo para responder sobre un paciente. |

---

## 6. Hallazgos de frontend

| # | Ubicación | Problema | Gravedad |
|---|---|---|---|
| 1 | `AssistantPage.tsx:634-650` | Si se recarga la página mientras se genera una respuesta, el chat queda **en punto muerto**: sin respuesta, sin spinner y sin botón para consultar estado. La guarda `isRetryableTurn` devuelve `false` justo para los estados transitorios que el backend fija mientras procesa. Reescribir la pregunta lleva a un 409 → 404 → "conversación no disponible" → bucle sin salida. | CRÍTICA |
| 2 | `api.ts:604-625` | Reintento automático ciego ante **cualquier** HTTP 422. `context_budget_exceeded` viaja como 422, así que el cliente reenvía el turno entero en silencio, vuelve a fallar igual, duplica la espera y ocupa dos veces el único slot de generación. | CRÍTICA |
| 3 | `chatSession.ts:154`, `AssistantPage.tsx:597` | El mapeo contexto→conversación vive en `sessionStorage`. Otra pestaña o cerrar el navegador = historial visible perdido, **aunque el backend lo tenga en BD**. El endpoint `GET /chat/conversations` existe y está indexado por usuario, pero `api.ts` no lo llama nunca. | ALTA |
| 4 | `AssistantPage.tsx:366-379` | Un fallo puntual de `/chat/health` deshabilita el cuadro de texto **y el botón Reintentar**. La sonda del proveedor tiene presupuesto de 2 s y la GPU puede estar ocupada 115 s → aparece "Generación en pausa" mientras la respuesta se está generando. | ALTA |
| 5 | `AssistantPage.tsx:148-160` | Los errores se muestran con el texto técnico del backend: *"La reparación no cumplió el contrato estructurado"*. Para `context_budget_exceeded` se ofrece "Iniciar chat compatible", que no arregla nada. | ALTA |
| 6 | `api.ts:408-419` | El SSE no tiene watchdog. El backend emite `heartbeat` cada 15 s y el frontend lo ignora; si un proxy corta la conexión, el spinner gira indefinidamente. | MEDIA |
| 7 | `api.ts:80` | `retry_after_ms` se lee, se tipa y **no se usa**: tras un 429 el botón Reintentar queda activo al instante y el usuario vuelve a chocar con la cola. | MEDIA |
| 8 | `AssistantPage.tsx:1673` | Durante 20–115 s el único feedback es una línea de texto congelada. Sin tiempo transcurrido, sin burbuja de progreso. | MEDIA |
| 9 | `AssistantPage.tsx:1710` | El cuadro de texto se bloquea durante toda la generación: no se puede ni redactar la siguiente pregunta. | MEDIA |
| 10 | `AssistantPage.tsx:554-575` | Cambiar de mascota en el selector global cancela un turno en vuelo y borra el borrador, sin confirmación. | MEDIA |
| 11 | `AssistantPage.tsx:512-525` | Si se pulsa Detener antes del evento `start`, la cancelación no llega al backend: sigue generando y retiene el slot único. | MEDIA |

Ninguno de los 28 tests de `AssistantPage.test.tsx` cubre
`generation_repair_failed`, `generation_queue_timeout` ni
`context_budget_exceeded` — precisamente los tres códigos que el usuario ve.

---

## 7. Las dos máquinas: recursos reales y qué cambiar

Medido en vivo el 5-ago con `gcloud` y `nvidia-smi`, con la batería en curso.

| | `hemovet-prod` | `hemovet-llm-gpu` |
|---|---|---|
| Tipo | `e2-standard-8` (AMD Rome) | `g2-standard-4` (Cascade Lake) |
| vCPU / RAM | 8 / 32 GB | **4 / 15 GB** |
| GPU | — | 1× **NVIDIA L4, 23.034 MiB** |
| Disco | 50 GB | 100 GB |
| Provisión | STANDARD, `automaticRestart` | STANDARD, `automaticRestart`, `onHostMaintenance: TERMINATE` |

Estado de la GPU durante la prueba:

```
NVIDIA L4 | 23034 MiB total | 19288 MiB en uso | 96 % utilización | 77 °C
ollama ps → qwen3.6:27b-q4_K_M  18 GB  100% GPU  context 65536
```

### 7.1 El modelo está bien colocado, pero el contexto está sobredimensionado ×20

**El modelo corre 100 % en GPU**, sin descarga a CPU: eso está correcto y no
hay que tocarlo. Con 4 vCPU y 15 GB de RAM, cualquier descarga a CPU sería
catastrófica, así que conviene mantenerlo así.

El problema es otro. Medido sobre las respuestas reales de la batería:

| Métrica | Valor medido | Configurado |
|---|---|---|
| Tokens de prompt | media **1.682**, máx **2.884** | `CHAT_MAX_INPUT_TOKENS=60000` |
| Contexto usado | ~3 % | `OLLAMA_CONTEXT_LENGTH=65536` |
| Tokens generados | media 263, máx 427 | `OLLAMA_NUM_PREDICT=2048` |
| Velocidad | **~10,8 tok/s** | — |

Se está reservando un contexto de 64 K para prompts de menos de 3 K. Y la
documentación de Ollama es explícita: **la memoria requerida escala con
`OLLAMA_NUM_PARALLEL × OLLAMA_CONTEXT_LENGTH`**. Es decir, ese contexto sin
usar es exactamente lo que impide atender a dos usuarios: quedan ~3,7 GB
libres de VRAM y no caben dos ranuras de 64 K.

**Cambio recomendado (sin tocar el modelo ni la máquina):**

```
OLLAMA_CONTEXT_LENGTH=16384      # 5,7× el prompt más grande observado
CHAT_MAX_INPUT_TOKENS=12000      # coherente con lo anterior
OLLAMA_NUM_PARALLEL=2            # dos usuarios simultáneos
CHAT_MAX_CONCURRENT_GENERATIONS=2
CHAT_QUEUE_TIMEOUT_SECONDS=150   # esperar en cola en vez de rechazar
OLLAMA_TIMEOUT_SECONDS=120       # § 4.3
```

Esto resuelve §4.1 y §4.3 **sin coste de hardware y sin cambiar de modelo**.
Conviene aplicarlo y volver a medir `nvidia-smi` antes de dar por buena la
concurrencia.

### 7.2 La lentitud es inherente al 27B en una L4

10,8 tok/s con un 27B cuantizado Q4 en una L4 es lo esperable: la L4 tiene
~300 GB/s de ancho de banda y el modelo ocupa 18 GB, así que el techo teórico
ronda los 16 tok/s. **No es un problema de configuración, es la elección de
modelo.** Cada respuesta de ~260 tokens cuesta ~24 s, y con reparación se va a
40–120 s.

Opciones, de menor a mayor esfuerzo:

1. **Bajar `OLLAMA_NUM_PREDICT`** de 2048 a ~768. Las respuestas reales usan
   263 de media y 427 como máximo; el techo actual solo sirve para permitir
   respuestas larguísimas que además chocan con el timeout de 90 s.
2. **Modelo más pequeño para las rutas conversacionales.** Identidad, saludo,
   capacidades y fuera de ámbito no necesitan 27B. Un 8B serviría esas rutas
   en 3–5 s y liberaría la GPU. `OLLAMA_MAX_LOADED_MODELS` ya está en 1;
   habría que subirlo a 2 y comprobar VRAM (18 GB + ~5 GB = ajustado, pero
   viable si se baja el contexto como en §7.1).
3. **Cambiar de motor de servido.** Los benchmarks 2026 dan a vLLM ~2,3× más
   throughput que Ollama con 8 peticiones concurrentes (187 vs 82 tok/s) por
   el *continuous batching*, mientras que con un solo usuario ambos rinden
   igual. Es decir: **vLLM no haría más rápida una respuesta suelta, pero sí
   permitiría varias a la vez**. Es un cambio grande y no lo recomendaría
   antes de la defensa.

### 7.3 La máquina de aplicación está sobrada

`e2-standard-8` (8 vCPU / 32 GB) sirve el backend, el frontend, PostgreSQL,
Chroma y Caddy con `BACKEND_WEB_CONCURRENCY=1`. No hay indicio de que sea un
cuello de botella; el cuello está en la GPU. **No cambiar.**

Sí conviene revisar el pool de base de datos (§5.3-8): el engine usa los
valores por defecto (15 conexiones) y `CHAT_DB_BLOCKING_MAX_CONCURRENCY` puede
llegar a 16, lo que agotaría el pool antes que la CPU.

---

## 8. Qué dice la literatura y la industria sobre este problema exacto

La revisión de papers y proyectos confirma que **el patrón que rompe HemoVet
es un antipatrón conocido y documentado**, y que existe un diseño estándar
para resolverlo.

### 8.1 El diagnóstico está en la literatura, con estas palabras

> *"Guardrails demasiado estrictos hacen que el modelo rechace peticiones
> legítimas; un chatbot médico que se niega a hablar de cualquier síntoma es
> inútil. El patrón de producción es una cascada: primero una heurística
> barata, después una comprobación con clasificador, y solo en los casos
> límite un LLM como juez."*
> — [AI Guardrails, Production LLM Safety Guide (2026)](https://myengineeringpath.dev/genai-engineer/ai-guardrails/)

HemoVet implementa **solo el primer escalón** de esa cascada (heurísticas de
expresiones regulares) y lo usa como veredicto **final y fatal**. La
literatura lo describe como el primer filtro de tres, no como el juez.

### 8.2 Separar comprobación sintáctica de comprobación semántica

La arquitectura de referencia para salida estructurada en 2026 separa
explícitamente dos cosas que HemoVet mezcla:

> *"Una arquitectura de referencia separa las comprobaciones sintácticas
> (a cargo de la gramática compilada) de las semánticas (reglas de validación
> en la pasarela), con un bucle de reparación que reintenta cuando los valores
> violan reglas de negocio."*
> — [Structured Outputs and Constrained Decoding in Production](https://www.tmls.nyc/research/structured-outputs-constrained-decoding)

En HemoVet, comprobaciones puramente **estilísticas** (¿dijo "hemogramas
caninos"? ¿usó la palabra "intervalo" y no "rango"?) están en la misma ruta
fatal que las **clínicas** (¿inventó un valor?). Separarlas es el cambio
estructural más importante que queda pendiente:

- **Fatal** (debe seguir rompiendo el turno): valor inventado, parámetro no
  autorizado, diagnóstico afirmado, dosis, fuente fabricada.
- **Degradable** (no debe romper nada): la cita no se puede probar → se quita
  la cita; el `fact_id` no está nombrado → se quita el `fact_id`; falta la
  frase de derivación → se pide en la reparación, y si no llega, se entrega
  igual con la advertencia que ya existe.

Las correcciones de este informe ya mueven varias comprobaciones al segundo
grupo; queda hacerlo de forma sistemática en vez de caso por caso.

### 8.3 Decodificación restringida: ya se usa, pero se puede aprovechar más

El backend **ya envía el esquema JSON a Ollama** (`payload["format"]` en
`openai_compatible_client.py:700`), lo que activa la gramática GBNF de
llama.cpp. Eso es correcto y está alineado con el estado del arte:
[XGrammar](https://arxiv.org/pdf/2501.10868) es hoy el backend por defecto de
vLLM, SGLang y TensorRT-LLM.

Aun así, `structured_schema_invalid` aparece **3 veces** en la batería. Con
gramática activa eso apunta a dos causas, ambas comprobables:

1. **Truncamiento**: el sobre JSON no cabe en `OLLAMA_NUM_PREDICT` y se corta
   a media estructura. Un hemograma de 19 parámetros puede requerir muchos
   *claims*.
2. **Límites del conversor JSON-Schema→GBNF de llama.cpp**, que no soporta
   bien `minItems`/`maxItems` ni `$defs` anidados — justo lo que usa este
   esquema.

**Acción sugerida:** registrar `finish_reason` junto a
`structured_schema_invalid` para distinguir ambas causas antes de tocar nada.

### 8.4 Verificación de afirmaciones: NLI en vez de expresiones regulares

El problema de "¿esta frase está respaldada por esta fuente?" —hoy resuelto
con solapamiento de palabras y por eso roto entre español e inglés— tiene una
solución estándar:

> *"La verificación por entrañamiento a nivel de afirmación descompone la
> respuesta en afirmaciones atómicas y puntúa cada una contra el contexto.
> Las implementaciones ejecutan primero un clasificador NLI y recurren al LLM
> como juez solo en los casos límite."*
> — [LLM Hallucination: A 2026 Architectural Deep Dive](https://futureagi.com/blog/llm-hallucination-deep-dive-2026/)

Un clasificador NLI multilingüe pequeño (tipo mDeBERTa-XNLI, ~300 MB en CPU)
sustituiría el solapamiento léxico actual y resolvería de raíz
`evidence_claim_mismatch`: una frase en español **sí** puede entrañar una
oración en inglés, cosa que la comparación de palabras nunca podrá ver. Como
corre en la máquina sin GPU, no compite por la L4.

Este es, además, **un aporte defendible para la tesis**: pasar de "coincidencia
léxica" a "verificación por entrañamiento" es una mejora metodológica
justificable con literatura.

### 8.5 Herramientas concretas que encajan en el proyecto

| Herramienta | Para qué serviría aquí | Coste |
|---|---|---|
| [**RAGAS**](https://github.com/explodinggradients/ragas) / [**DeepEval**](https://github.com/confident-ai/deepeval) | Medir *faithfulness*, *answer relevancy* y *contextual recall* de forma reproducible. Convierte la batería manual de este informe en una **métrica citable para el documento de tesis**, que es justo lo que falta en la sección de resultados | Bajo: se ejecuta offline, sobre las respuestas ya guardadas |
| [**NVIDIA NeMo Guardrails**](https://github.com/NVIDIA-NeMo/Guardrails) | Referencia de arquitectura: separa *input rails*, *dialog rails*, *retrieval rails* y *output rails*. Es exactamente la separación que aquí está mezclada. NVIDIA publica un caso de asistente clínico con RAG + guardrails | Medio: como referencia de diseño, no necesariamente adoptarlo |
| **mDeBERTa-v3-XNLI** (Hugging Face) | El verificador NLI de §8.4 | Bajo: CPU, en `hemovet-prod` |
| **vLLM** | Concurrencia real por *continuous batching* | Alto: cambio de motor, no antes de la defensa |

### 8.6 Lo que NO recomiendo

- **Fine-tuning / LoRA.** Aparecía como opción en las notas anteriores del
  proyecto. Los fallos medidos **no son del modelo**: son de validadores que
  rechazan respuestas correctas. Entrenar el modelo para adivinar la redacción
  que espera una expresión regular sería resolver el problema equivocado con
  la herramienta más cara.
- **Cambiar a un modelo más grande.** Ya se probó (14B → 27B) y el problema
  persistió, porque nunca fue de capacidad.
- **Quitar los validadores.** La capa de seguridad es correcta y es un aporte
  real del proyecto; el defecto está en *qué* considera fatal, no en que exista.

---

## 9. Qué queda pendiente en este informe

Estado tras las correcciones aplicadas:

| Pendiente | Dónde | Prioridad |
|---|---|---|
| Aplicar los cambios de `.env` de §7.1 y medir VRAM | `.env.production` | **Alta** — resuelve concurrencia y timeouts sin código |
| Desplegar las correcciones de backend (§3.bis) y repetir la batería | — | **Alta** — hasta que no se despliegue, producción sigue igual |
| Frontend #1 y #2 (punto muerto tras F5, reintento ciego ante 422) | `AssistantPage.tsx:634`, `api.ts:604` | **Alta** |
| Recuperar conversación desde el backend en vez de `sessionStorage` | `api.ts` + `AssistantPage.tsx:597` | Alta |
| Distinguir "sin patrón detectado" de "sin salida del clasificador" | `sqlalchemy_repositories.py:2368` | Media |
| `LIMIT` en las 4 consultas del camino caliente | §5.3-6 | Media |
| Purga real de conversaciones y `chat_turn_attempts` | §5.3-2 | Media |
| Índices `(session_id, turn_index)` | §5.3-7 | Media |
| Verificador NLI en lugar de solapamiento léxico | §8.4 | Media — alto valor para la tesis |
| Registrar `finish_reason` junto a `structured_schema_invalid` | §8.3 | Baja, pero es diagnóstico previo necesario |
| Copy de errores en lenguaje de usuario | §6-5 | Baja |

---

## 10. Fuentes consultadas

- [AI Guardrails — Production LLM Safety Guide (2026)](https://myengineeringpath.dev/genai-engineer/ai-guardrails/)
- [LLM Hallucination: A 2026 Architectural Deep Dive](https://futureagi.com/blog/llm-hallucination-deep-dive-2026/)
- [Structured Outputs and Constrained Decoding in Production](https://www.tmls.nyc/research/structured-outputs-constrained-decoding)
- [JSONSchemaBench: A Rigorous Benchmark of Structured Outputs for Language Models](https://arxiv.org/pdf/2501.10868)
- [Trust but Verify: Mitigating Medical Hallucinations via Post-Hoc Adversarial Auditing and Multi-Agent Feedback Loops](https://arxiv.org/pdf/2606.14149)
- [Develop Secure, Reliable Medical Apps with RAG and NVIDIA NeMo Guardrails](https://developer.nvidia.com/blog/develop-secure-reliable-medical-apps-with-rag-and-nvidia-nemo-guardrails/)
- [NVIDIA NeMo Guardrails (GitHub)](https://github.com/NVIDIA-NeMo/Guardrails)
- [DeepEval — The LLM Evaluation Framework (GitHub)](https://github.com/confident-ai/deepeval)
- [Faithfulness | DeepEval](https://deepeval.com/docs/metrics-faithfulness)
- [Ollama FAQ — concurrencia y memoria](https://docs.ollama.com/faq)
- [Ollama vs. vLLM: a deep dive into performance benchmarking (Red Hat)](https://developers.redhat.com/articles/2025/08/08/ollama-vs-vllm-deep-dive-performance-benchmarking)
- [Benchmarking Ollama and vLLM for Concurrent LLM Serving (MDPI)](https://www.mdpi.com/2076-3417/16/11/5435)
- [Lost in the Middle: How Language Models Use Long Contexts (TACL)](https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00638/119630/Lost-in-the-Middle-How-Language-Models-Use-Long)

---

## 11. Oportunidades de mejora por capa

### Modelo
- La temperatura de producción (0.6) es alta para un contrato estructurado
  estricto. Bajarla a 0.2–0.3 reduciría la variabilidad de redacción que hoy
  dispara los validadores, sin volverla robótica.
- El prompt de reparación debe decir **qué** se espera, no solo el código de
  error. Hoy el modelo reintenta a ciegas.

### Backend
- Los validadores de redacción deberían ser **degradantes**, no fatales:
  quitar la cita que no se puede probar, quitar el `fact_id` que el texto no
  nombra, y dejar pasar la respuesta. Un contrato de seguridad debe impedir
  afirmaciones falsas, no vetos por sinónimos.
- Falta un modo de "último recurso": si tras dos intentos no hay candidato
  válido, hoy se devuelve 502. Sería preferible entregar el mejor candidato
  seguro con una advertencia, antes que nada.

### Frontend
- Recuperar la conversación desde el backend (`GET /chat/conversations`) en
  vez de depender de `sessionStorage`. Es lo que la profesora entiende por
  "un asistente que recuerda".
- Traducir los códigos de error a lenguaje de usuario y ofrecer la acción que
  de verdad resuelve cada uno.

### Servidor
- Timeout de cola por encima del tiempo real de generación (§4.1).
- Evaluar `OLLAMA_NUM_PARALLEL=2` midiendo VRAM en la L4.

### Base de datos
- Purga real de conversaciones vencidas y de `chat_turn_attempts`.
- Índices `(session_id, turn_index)` para las consultas que se ejecutan en
  cada turno.
- Normalizar la salida del clasificador (hoy solo vive dentro de un blob de
  texto), que es la raíz de los problemas 5.3-4 y 5.3-5.

---

*Documento generado durante la sesión de auditoría del 5-ago-2026.*
