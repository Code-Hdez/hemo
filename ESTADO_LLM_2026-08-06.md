# Estado del asistente LLM — jueves 6 de agosto de 2026

> Continuación de `INFORME_AUDITORIA_LLM_2026-08-05.md`. Aquel documento
> midió el problema; este registra qué se corrigió, con qué evidencia, qué
> queda abierto y en qué estado está el sistema ahora mismo.

---

## 1. Dónde estábamos y dónde estamos

La batería completa contra producción el 5-ago dio **10 de 62 preguntas
respondidas (16 %)**, con el desglose:

| Modo | 5-ago |
|---|---|
| Chat general | 10/17 |
| Hemograma seleccionado | **0/24** |
| Historial | **0/10** |
| Multiturno | 0/11 (9 murieron por expiración del token, no por el asistente) |

Todo lo demás fue HTTP 502: el usuario esperaba entre 40 y 123 segundos para
no recibir nada.

**La causa nunca fue el modelo.** En la mayoría de los casos la respuesta
generada era correcta y un validador la descartó por la redacción.

---

## 2. Lo corregido, con la evidencia que lo motivó

### 2.1 Los validadores de lista cerrada (causa raíz)

Casi todos los validadores comprobaban la redacción contra una expresión
regular que enumeraba unas pocas frases. Medido antes de tocar nada: de 12
formas correctas de expresar una limitación clínica, **9 eran rechazadas**.

Peor: el prompt de reparación solo le daba al modelo el código de error, no la
redacción esperada, así que el segundo intento caía igual. Y con
`OLLAMA_TEMPERATURE=0.6` en producción la redacción cambia en cada llamada —
por eso el fallo parecía intermitente.

| Código de error | Estado |
|---|---|
| `limitation_claim_invalid` | ✅ |
| `structured_numeric_support_required` | ✅ |
| `intent_mismatch_capabilities` / `intent_mismatch_identity` | ✅ |
| `structured_fact_claim_mismatch` | ✅ |
| `structured_patient_fact_not_materialized` | ✅ |
| `evidence_claim_mismatch` / `evidence_span_not_found` | ✅ |
| `mandatory_diagnosis_boundary` | ✅ |
| `structured_patient_fact_id_required` | ✅ |
| `structured_unlinked_clinical_claim` | ✅ |
| `missing_veterinary_referral` | ✅ |
| `structured_patient_fact_coverage_missing` | ✅ |
| `structured_schema_invalid` | ⏳ instrumentado, no resuelto |

### 2.2 El historial era irresoluble por construcción

Al darle a Lucas una serie real de estudios, **todas** las preguntas de
historial murieron con `structured_patient_fact_coverage_missing`. La regla
exigía citar todas las mediciones repetidas en alcance: con 8 estudios de 12
parámetros son ~96 hechos en un solo sobre JSON.

Ahora se exige solo de los analitos que la respuesta discute. Eso conserva la
propiedad que la regla protege de verdad — no puedes mostrar un punto de una
serie y esconder el resto — y permite responder sobre plaquetas sin recitar el
panel entero de cada estudio.

### 2.3 Un agujero de seguridad clínica, abierto y cerrado en esta sesión

Al relajar los validadores abrí un hueco real, que una revisión adversarial
demostró ejecutando el código:

| Aceptaba | Por qué |
|---|---|
| `"Lucas tiene anemia."` | La red que impide afirmar un diagnóstico se ancla en *"tu perro"/"el paciente"*. **No contemplaba el nombre propio** — y el asistente está autorizado a usarlo. |
| `"La edad de Lucas es 32.5 años"` (32,5 es el peso) | Al ampliar el vocabulario autorizado metí también **todos los números** de todos los hechos. |
| `"La anemia causa debilidad, consulta a tu veterinario"` | Puse `consulta` y `veterinario` entre los atenuantes… mientras el mismo turno **obliga** a incluir la derivación. |

Los tres están cerrados y con test de regresión. Además, mi propio test
destapó que `confirma una infección` se colaba mientras `confirma que hay una
infección` sí se bloqueaba.

### 2.4 Verificación de citas: de coincidencia léxica a entrañamiento

El corpus está mayormente en inglés y la respuesta es siempre en español. La
verificación por solapamiento de palabras es estructuralmente mala para eso.

Se construyó un banco de **70 casos con fragmentos literales del corpus del
proyecto** (verificados carácter a carácter contra su fuente), con positivos
y cuatro clases de negativos: negación invertida, cifra cambiada, tema
distinto y exageración diagnóstica.

| Verificador | Aciertos | Acepta inseguro | Rechaza fiel | Latencia |
|---|---|---|---|---|
| Léxico actual | 46/70 (66 %) | **11** | 13 | ~0 ms |
| **NLI multilingüe** (mDeBERTa-XNLI, ONNX/CPU) | **69/70 (99 %)** | **1** | **0** | 123 ms |

Negación: 10/14 → **14/14**. Positivos: 16/29 → **29/29**.

El léxico daba por buena el **27 % de las afirmaciones falsas**, incluidas
inversiones de sentido sin partícula negativa ("los eosinófilos son *más
pequeños*" cuando la fuente dice *larger*).

**Dos reservas, registradas y no maquilladas:**
1. El umbral (0.80) se calibró sobre el mismo banco con el que se puntúa. No
   hay conjunto retenido, así que el 99 % es una estimación de ajuste, no de
   generalización.
2. El único falso positivo que sobrevive es el peor clínicamente: cambia el
   sujeto de la frase (monocitos → linfocitos) y el modelo lo entraña a 0.985.
   Se midió la comprobación bidireccional para atraparlo y **empeora**.

Entra **desactivado por defecto** (`CHAT_CLAIM_ENTAILMENT_ENABLED=0`),
inyectado por constructor y fallando cerrado.

> **Nota de honestidad:** antes de este banco yo había concluido, con 6 pares
> elegidos por mí, que el enfoque semántico era peor que el léxico. La muestra
> era demasiado pequeña. El banco de 70 casos lo desmiente.

### 2.5 Fuera del LLM

| Hallazgo | Impacto | Estado |
|---|---|---|
| **El logout borraba el historial de chat** (`DELETE` + `ON DELETE CASCADE`) | Explicaba la queja "el chat no recuerda nada" | ✅ ahora cierra la sesión |
| **`save_analysis` podía abortar en PostgreSQL** por texto sin truncar | Un hemograma se pierde en silencio al subirlo | ✅ |
| **La app no admitía dos usuarios a la vez** (2 de 3 peticiones → HTTP 429) | Riesgo en la defensa | ⚙️ requiere el secreto |
| **Disco de la VM de GPU al 100 %** (970 MB libres de 96 GB) | Cualquier escritura rompía el servicio | ✅ 28 GB libres |
| Frontend: punto muerto tras F5 durante una generación | El chat quedaba mudo sin salida | ✅ |
| Frontend: reintento ciego ante cualquier 422 | Duplicaba la espera y el slot de GPU | ✅ |
| Frontend: historial perdido en otra pestaña | Aunque el backend lo tuviera en BD | ✅ recupera del backend |
| BD: consultas sin `LIMIT`, índices que no servían el `ORDER BY`, pool sin dimensionar | Latencia en el camino caliente | ✅ |
| BD: `classifier_outcome` confundía "no detectó nada" con "nunca corrió" | El asistente afirmaba un negativo que el modelo nunca produjo | ✅ tres estados |

---

## 3. Las dos máquinas

| | `hemovet-prod` | `hemovet-llm-gpu` |
|---|---|---|
| | `e2-standard-8` — 8 vCPU / 32 GB | `g2-standard-4` — 4 vCPU / 15 GB |
| GPU | — | NVIDIA L4, 23.034 MiB |
| Disco | 50 GB | 100 GB (**28 GB libres** tras la limpieza) |

Modelo: `qwen3.6:27b-q4_K_M`, 18 GB, **100 % en GPU**, ~11 tok/s.

**El contexto estaba sobredimensionado ×20.** Los prompts reales pesan 1.682
tokens de media (2.884 el mayor) contra un contexto configurado de 65.536. Como
la VRAM escala con `NUM_PARALLEL × CONTEXT_LENGTH`, ese contexto ocioso es lo
que impide una segunda ranura de generación.

**¿Es el modelo el adecuado?** Sí para lo que se le pide. Los fallos medidos no
eran de conocimiento: eran respuestas correctas descartadas. Lo que el caso
exige es seguir un esquema JSON, escribir español y copiar cifras de una tabla
— seguimiento de instrucciones, no razonamiento clínico, que lo aportan el RAG
y PostgreSQL. **MedGemma queda descartado**: está entrenado en medicina humana
y los rangos caninos son distintos. Lo que sobra es el tamaño, no la calidad.

---

## 4. 🚨 Riesgo nuevo, descubierto al aplicar la configuración

**El chat se marca como caído durante más de un minuto cada vez que el modelo
se recarga, aunque esté cargando perfectamente.**

Al cambiar `OLLAMA_CONTEXT_LENGTH`, Ollama recarga el modelo. Medido en vivo:

```
carga en frío del modelo   : 79 segundos
OLLAMA_WARMUP_TIMEOUT_SECONDS : 20 segundos
```

El backend da el warmup por fallido, publica `LLM_PROVIDER_UNAVAILABLE` y el
frontend deshabilita el chat. Producción estuvo así varios minutos hasta que se
forzó la carga a mano. Ocurre en **cualquier reinicio de la VM de GPU**, sin
que nadie toque nada.

Es el riesgo más concreto para la defensa: si la máquina se reinicia poco antes
de la presentación, el asistente aparece roto sin motivo real. **Corrección:
subir `OLLAMA_WARMUP_TIMEOUT_SECONDS` a ~120 s.** No aplicada todavía.

---

## 5. Estado actual

- **`main`**: PR #37 y #38 mergeados. **Despliegue de #38 completado con
  éxito** (15m46s).
- **Producción operativa**: `chat_ready: true`, provider `ready`, sin códigos
  de error.
- **Suite backend**: 1015 pasando, 4 fallos preexistentes (`pdfplumber`
  ausente en `test_extraction_pipeline`), 0 regresiones.
- **Suite frontend**: 118 en verde.
- **Datos de prueba ampliados**: se creó **Nala** (2 estudios, hallazgo
  *"Anemia no regenerativa"*) y Lucas pasó a **8 estudios**, para poder validar
  historial real, cambio de mascota y dos etiquetas ML distintas.

### 5.1 Configuración aplicada en la máquina

Aplicada directamente en `/var/lib/hemovet-prod/.env`, con copia previa en
`.env.antes-2026-08-06`, y **verificada dentro del contenedor**, no solo en el
fichero:

```
OLLAMA_CONTEXT_LENGTH      65536 → 16384
CHAT_MAX_INPUT_TOKENS      60000 → 12000
OLLAMA_NUM_PREDICT          2048 → 1280
OLLAMA_TIMEOUT_SECONDS        90 → 120
CHAT_TOTAL_TIMEOUT_SECONDS   150 → 240
CHAT_QUEUE_TIMEOUT_SECONDS    20 → 60
```

Detalle operativo que cuesta tiempo si no se sabe: **`docker restart` no
recarga el entorno**. Las variables se fijan al crear el contenedor, así que
hace falta `docker compose up -d --no-deps backend` con `--env-file`.

Efecto medido en la GPU:

| | Antes | Después |
|---|---|---|
| Tamaño del modelo en memoria | 18 GB | **16 GB** |
| VRAM usada | 19.288 MiB | **17.408 MiB** |
| VRAM libre | 3,7 GB | **5,6 GB** |

⚠️ **Este cambio vive solo en la máquina. El próximo despliegue lo pisa**,
porque el entorno se reconstruye desde el secreto `PRODUCTION_ENV_B64`.

---

## 6. Pendiente

| # | Pendiente | Por qué importa |
|---|---|---|
| 1 | **`OLLAMA_WARMUP_TIMEOUT_SECONDS` 20 → 120** | §4. Riesgo directo para la defensa |
| 2 | **Actualizar `PRODUCTION_ENV_B64`** con los valores de §5.1 | Sin esto, el próximo despliegue revierte todo lo aplicado en la máquina |
| 3 | **Batería ampliada completa** | 62 originales + 22 nuevas + 3 secuencias de cambio de contexto. Se lanzó y se detuvo a los pocos minutos: **no hay antes/después medido todavía** |
| 4 | Encender el verificador NLI y medir latencia real en la máquina | Está listo y desactivado |
| 5 | Segunda ranura de generación (`OLLAMA_NUM_PARALLEL=2`) | Ahora hay 5,6 GB libres. Necesita cortar una release de GPU: el contrato está sellado por digest |
| 6 | `structured_schema_invalid` | Ya se registra `finish_reason` para distinguir truncamiento de límites de gramática. Falta leer esos logs |
| 7 | Conjunto retenido para el umbral del NLI | Convierte el 99 % en una cifra defendible ante el tribunal |
| 8 | Dos estudios de sondeo con 3 parámetros en Lucas | Se crearon al preparar los datos y no hay endpoint de borrado |

### Valores para el secreto

```
OLLAMA_CONTEXT_LENGTH=16384         (era 65536; los prompts reales usan ~1.700)
CHAT_MAX_INPUT_TOKENS=12000         (era 60000)
OLLAMA_NUM_PREDICT=1280             (era 2048; es lo que la L4 genera en 120 s)
OLLAMA_TIMEOUT_SECONDS=120          (era 90, y una pregunta murió a los 90,4 s)
CHAT_TOTAL_TIMEOUT_SECONDS=240      (era 150; un turno son hasta dos generaciones)
CHAT_QUEUE_TIMEOUT_SECONDS=60       (era 20; el techo que admite config.py)
OLLAMA_WARMUP_TIMEOUT_SECONDS=120   (era 20; la carga en frío tarda 79 s)
```

`CHAT_MAX_CONCURRENT_GENERATIONS` se deja en 1 a propósito: la segunda ranura
vive en el servidor Ollama, y subir el semáforo del backend antes mandaría dos
peticiones a un servidor con una sola.

---

## 7. Lo que NO se debe hacer

- **Fine-tuning / LoRA.** Los fallos no eran del modelo. Entrenarlo para
  adivinar la redacción que espera una expresión regular sería resolver el
  problema equivocado con la herramienta más cara.
- **Modelo más grande.** Ya se probó (14B → 27B) y el problema siguió.
- **pydantic-ai.** El proyecto ya implementa el patrón que su documentación
  recomienda: `model_json_schema()` → `format` de Ollama (gramática GBNF) →
  `model_validate`. Es un framework de agentes; añadiría reintentos sobre
  `ValidationError`, que es justo lo que ya hace la reparación. El problema
  son los validadores semánticos propios, que no sustituye.
- **Quitar los validadores.** La capa de seguridad es un aporte real del
  proyecto. El defecto estaba en *qué* consideraba fatal, no en que exista.

---

*Sesión del 6-ago-2026.*
