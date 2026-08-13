# Informe integral de pruebas — migración producción/GPU y chat LLM

- Fecha de consolidación: 2026-08-03
- Alcance: Etapas 0 a 10
- Rama auditada: `dev-agosto/feat-gpu-deployment-separation`
- HEAD de la rama al iniciar este informe:
  `b2fb14e6f5a969a7692f2c8db32699df7b862ce6`
- Revisión final sometida a aceptación:
  `e7713a72369bb9365f6d5323e165fbf84488bfb4`
- Estado de las Etapas 11 y 12: `PENDING`

## 1. Objetivo y criterio de lectura

Este documento consolida las pruebas realizadas durante la migración de
HemoVet, incluyendo código, frontend, RAG, persistencia, despliegue inmutable,
rollback, seguridad de red y runtime GPU. También responde expresamente si se
ejecutaron baterías de prompts contra el chat LLM.

Los conteos de pytest de distintas etapas son **fotografías sucesivas de una
misma suite que fue creciendo**. No deben sumarse. Tampoco deben sumarse los
shards de un run con una regresión completa anterior sin comprobar primero que
sean conjuntos disjuntos.

Este informe distingue cuatro clases de evidencia:

1. **Prueba determinista:** usa fakes, mocks, SQLite temporal o servicios
   aislados; valida el código, pero no mide la calidad generativa de Qwen.
2. **Aceptación real de la revisión final:** atraviesa la aplicación aislada y
   el runtime Qwen real ejecutándose en la NVIDIA L4.
3. **Batería histórica:** ejerció un pipeline real antes de esta migración, pero
   usó `llama3.2:3b`, no el Qwen final.
4. **Suite disponible pero no ejecutada:** existe en el repositorio, aunque el
   gate correspondiente quedó omitido deliberadamente.

No se volvieron a ejecutar pruebas ni se encendió la GPU para redactar este
informe. La consolidación se hizo sobre evidencia ya versionada.

## 2. Respuesta ejecutiva sobre las pruebas de prompts

Sí se probaron prompts reales, pero la cobertura final debe describirse con
precisión:

| Pregunta | Respuesta verificable |
| --- | --- |
| ¿Se probó el runtime Qwen real? | Sí. Se verificaron identidad, digest, cuantización, inferencia y residencia completa en la L4. |
| ¿Se enviaron prompts por la aplicación real a Qwen? | Sí. La aceptación de Etapa 10 ejecutó ocho flujos con mensaje mientras el proveedor real estaba disponible. |
| ¿Se probaron chat general, hemograma seleccionado, historial y memoria? | Sí, dentro del entorno aislado de Etapa 10. |
| ¿Se probaron diagnóstico, dosis y fuera de alcance? | Sí, tres casos finales pasaron y registraron `llm_invoked=true`. |
| ¿Los `24 passed` de “evaluación LLM” del CI son 24 prompts? | **No.** Son pruebas unitarias del runner, parser SSE, validadores y generador de reportes. |
| ¿Se ejecutó la suite dedicada `test_ollama_qwen_acceptance.py`? | **No.** Fue el único skip persistente porque requiere `RUN_OLLAMA_ACCEPTANCE=1`. |
| ¿Se ejecutaron las 770 preguntas contra el Qwen final? | **No.** Sus resultados versionados son históricos y corresponden a `llama3.2:3b`. |
| ¿Se ejecutaron los 16 casos de `acceptance_cases.yaml` contra el Qwen final? | **No se encontró evidencia de ejecución.** Sus IDs no aparecen en los 26 resultados versionados. |
| ¿Existe una validación clínica humana? | Sí, histórica sobre `llama3.2:3b`; no se repitió con el Qwen final. |

Conclusión: la revisión final tiene una **aceptación funcional real y compacta
con Qwen**, suficiente para demostrar integración, valores clínicos sintéticos,
RAG, memoria, seguridad y GPU. No tiene todavía una **campaña amplia y
estadística de calidad de prompts sobre el Qwen final**.

## 3. Cobertura acumulada por etapa

### Etapa 0 — línea base

Se validó el estado previo sin modificar repositorio o infraestructura:

- Compose base, producción, GPU y QA mediante `docker compose config`;
- `llm_chat`: 546 passed, 1 skipped;
- repositorios SQLAlchemy: 23 passed;
- configuración/promoción RAG: 57 passed;
- herramientas de evaluación: 24 passed;
- backend general: 214 passed y 2 subtests;
- RAG dry-run: 1,250 fuentes, 4,696 chunks y 0 cuarentena;
- frontend: 103 pruebas unitarias, Biome, TypeScript y build;
- E2E críticos: 8 passed;
- inspección pública de web, chat health y estado degradado.

El skip ya correspondía a la aceptación con Ollama/Qwen real. La GPU no se
encendió en esta etapa.

### Etapa 1 — sesiones y promoción/rollback RAG

Pruebas relevantes:

- 42 casos focales de propagación y aislamiento de
  `browser_session_hash`, repositorio SQLAlchemy real y transacción de entorno;
- 5 casos que inicialmente se detenían por un problema del executor de Python
  3.14, repetidos con un harness temporal y luego revalidados sin ese harness
  en Python 3.11;
- `llm_chat`: 575 passed, 1 skipped;
- entorno, RAG y migraciones: 68 passed;
- backend completo: 862 passed, 1 skipped, 1 warning y 4 subtests;
- Ruff y comprobaciones de alcance: PASS.

Se demostró que:

- `turn_history()` filtra por usuario y sesión en el repositorio real;
- no existe fallback por `TypeError` que omita el filtro;
- la instalación del `.env` completo es atómica;
- un fallo posterior restaura los bytes anteriores;
- el puntero RAG vuelve a la colección previa;
- el rollback es idempotente y no destruye colecciones.

### Etapa 2 — contratos de disponibilidad, proveedor y release

Gate inicial oficial en Python 3.11.15:

- `llm_chat`: 576 passed, 1 skipped;
- entorno/RAG/migraciones: 68 passed;
- backend completo: 862 passed, 1 skipped y 4 subtests;
- Ruff: PASS.

Validación final:

- contratos focales de health, disponibilidad, proveedor y manifiesto:
  50 passed;
- `llm_chat`: 596 passed, 1 skipped;
- backend completo: 888 passed, 1 skipped, 1 warning y 4 subtests;
- Ruff: PASS.

Los casos cubren liveness, `core_ready`, `database_ready`, `chroma_ready`,
`rag_ready`, `chat_ready`, timeouts, reintentos acotados, sanitización de health,
correlation ID y coherencia del manifiesto `hemovet.release/v1`.

### Etapa 3 — Artifact Registry, identidades, WIF e imágenes inmutables

- backend completo intermedio: 897 passed, 1 skipped y 4 subtests;
- backend final: 898 passed, 1 skipped, 1 warning y 4 subtests;
- contratos de Artifact Registry, release y bases por digest: 16 passed;
- Ruff y build frontend: PASS;
- `actionlint 1.7.12`: PASS;
- validación del artifact set de tres imágenes: PASS;
- inspección de labels OCI, SBOM y provenance: PASS;
- lectura de IAM y ausencia de claves de service account: PASS;
- WIF positivo y negativo, run `30762294120`: PASS.

El caso negativo sin environment obtuvo `unauthorized_client`; el positivo
usó token efímero, publicó un artefacto de prueba y lo leyó por digest. Ningún
job productivo se ejecutó.

### Etapa 4 — separación de Compose

- validador de topologías: local, producción y GPU, PASS;
- `docker compose config --quiet` y `config --services` para cinco conjuntos;
- contratos focales de Compose/entorno: 77 passed;
- backend completo: 912 passed, 1 skipped, 1 warning y 4 subtests;
- Ruff: PASS;
- frontend: 103 passed, Biome, TypeScript y build, PASS.

Se comprobó que producción no contiene Ollama, que GPU contiene únicamente
`ollama` y `ollama_setup`, y que desarrollo conserva un runtime local.

### Etapa 5 — backend y frontend degradables

- contratos focales: 83 passed;
- `llm_chat`: 608 passed, 1 skipped;
- backend completo: 924 passed, 1 skipped, 1 warning y 4 subtests;
- Ruff: PASS;
- frontend: 108 passed en 14 archivos;
- Biome, TypeScript y build: PASS;
- Playwright del dashboard: 22 passed;
- Compose local/producción/GPU: PASS.

Se probaron proveedor ausente, timeout, recuperación, historial accesible,
RAG requerido degradado, separación de identidad y residencia, SSE
interrumpido/sanitizado y polling del frontend cada 15 segundos. El E2E probó
degradación y recuperación sin recargar ni borrar el historial.

### Etapa 6 — runtime GPU y reconciliación

Gates de código:

- contratos del bootstrap GPU: 17 passed;
- backend completo: 941 passed, 1 skipped, 1 warning y 4 subtests;
- Ruff, Bash, ShellCheck y checksums del bundle: PASS;
- Compose GPU exacto: `ollama`, `ollama_setup`.

Pruebas reales sobre `hemovet-llm-gpu`:

- snapshot previo en estado `READY`;
- driver NVIDIA `580.159.03`;
- Docker `29.6.2`, Compose `5.3.1` y NVIDIA Container Toolkit `1.17.8`;
- `/api/tags` y `/api/show`: modelo/digest/Q4_K_M correctos;
- `/api/ps`, `ollama ps` y `nvidia-smi`: 100 % GPU;
- stop/start de VM y restart de contenedor;
- hash del volumen de pesos idéntico;
- segunda ejecución idempotente;
- revisión inválida rechazada sin alterar runtime o pesos;
- rollback `515d… → 6e29… → 515d…`, ambos lados con `full_gpu`;
- escaneo de logs sin secretos;
- VM apagada al terminar.

El runtime ejecutó además una inferencia sintética mínima con temperatura cero:
“responder únicamente OK”. Esta prueba demuestra ejecución, latencia y uso de
GPU; **no mide calidad clínica o conversacional**.

### Etapa 7 — red, IAP/OS Login y protecciones

- contratos GPU: 18 passed;
- backend completo: 942 passed, 1 skipped, 1 warning y 4 subtests;
- Ruff, ShellCheck, checksums y manifiestos: PASS;
- producción `10.128.0.2 → 10.128.0.3:11434`: HTTP 200;
- fuente interna no autorizada: rechazada;
- Internet hacia 22/80/443/3000/3389/11434 de la GPU: rechazado;
- dos accesos IAP/OS Login, más validación posterior a deny-all: PASS;
- recuperación tras una preempción Spot: PASS;
- revisión inválida produjo apagado solicitado desde el guest: PASS;
- arranque válido posterior con `full_gpu`: PASS;
- `deletionProtection=true`, `autoDelete=false`, snapshot `READY`;
- GPU apagada y aplicación pública operativa al finalizar.

### Etapa 8 — GitHub Actions y despliegue inmutable

Regresión local:

- backend: 958 passed, 1 skipped y 4 subtests;
- frontend: 108 passed en 14 archivos;
- E2E crítico: 8 passed;
- Ruff, Compose, Caddy, Bash y actionlint: PASS.

Run final de publicación de la etapa:

- migraciones: 6 passed;
- `llm_chat`: 609 passed, 1 skipped;
- release/GPU: 48 passed;
- herramientas de evaluación: 24 passed;
- backend restante: 295 passed y 4 subtests;
- WIF/IAP: dos ejecuciones exitosas;
- referencia no autorizada: rechazo esperado;
- publicación por un SHA y tres digests: PASS;
- deploy productivo: no ejecutado.

Tres publicaciones previas fallaron cerradas por una expresión `jq`, una URL
local heredada y la distinción entre chunk schema y corpus schema. Ninguna
alcanzó metadata GPU, despliegue o smoke productivo.

### Etapa 9 — rollback coordinado

- backend completo: 966 passed, 1 skipped y 4 subtests;
- rollback y health focales: 37 passed;
- Ruff, Bash, ShellCheck, checksums y Compose: PASS;
- migraciones `0001 → 0012` en backend publicado: PASS;
- instalación candidata aislada: PASS;
- fallo controlado posterior, repetido dos veces: rc 42 y `ROLLED_BACK`;
- `.env` anterior: byte-identical;
- `RAG_COLLECTION_NAME`: restaurado;
- backend/frontend: digests anteriores restaurados;
- SQLite sintético y colecciones Chroma sintéticas: hashes sin cambios;
- metadata GPU `anterior → candidato → anterior`: byte-identical;
- WIF desde rama de trabajo: rechazo esperado, sin publicación ni deploy.

La prueba detectó un problema real: el health del candidato tardaba más que el
timeout Docker cuando la GPU estaba apagada. Se acotaron los probes y se añadió
una prueba que exige respuesta menor a 2.5 segundos con núcleo listo.

### Etapa 10 — aceptación E2E final

- Revisión: `e7713a72369bb9365f6d5323e165fbf84488bfb4`
- PR: 29
- GitHub Actions run: `30794470808`, `success`

Gates de CI:

| Gate | Resultado |
| --- | --- |
| Migraciones | 6 passed |
| `llm_chat` | 632 passed, 1 skipped |
| Release/contratos | 48 passed |
| Evaluador LLM | 24 passed |
| Backend restante | 304 passed, 4 subtests |
| Ruff | PASS |
| Frontend | 108 passed en 14 archivos |
| Biome, TypeScript y build | PASS |
| Playwright crítico | 8 passed |
| Deploy y smoke productivo | skipped por gate manual |

Aceptación funcional aislada:

- 19 casos PASS;
- 0 casos FAIL;
- cubrió 20 requisitos porque registro e inicio de sesión comparten un caso;
- PostgreSQL, Chroma, medios y cache exclusivos del namespace temporal;
- sin Caddy ni puertos públicos;
- datos clínicos exclusivamente sintéticos;
- recursos temporales eliminados al finalizar;
- producción conservó IDs de contenedores y timestamp de arranque.

Aceptación GPU final:

- Qwen `qwen3:4b-instruct-2507-q4_K_M`;
- digest `sha256:0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`;
- `Q4_K_M`;
- `inference_device=full_gpu`;
- 2,996 MiB de VRAM observada;
- pico de utilización 32 %;
- volumen persistido reutilizado;
- GPU apagada al terminar;
- cero cutover y cero pérdida de datos.

## 4. Inventario técnico de las suites de chat

La suite final `backend/tests/llm_chat` contiene 35 módulos. Sus principales
familias son:

| Familia | Archivos representativos | Qué demuestra |
| --- | --- | --- |
| API y SSE | `test_chat_api.py`, `test_real_streaming.py`, `test_response_contracts.py` | Rutas, envelopes, secuencia SSE, cancelación, cierre e interrupción. |
| Caso de uso | `test_send_chat_message.py`, `test_structured_send_chat_message.py` | Orquestación, retries, persistencia, validación y fallbacks. |
| Sesiones/memoria | `test_repositories.py`, `test_conversation_memory.py`, `test_session_memory_integration.py` | Usuario, navegador, turnos, restauración y aislamiento. |
| Proveedor | `test_openai_compatible_client.py`, `test_provider_contract.py`, `test_composition.py` | Timeout, identidad, cuantización, residencia, errores y recuperación. |
| Disponibilidad | `test_availability_contract.py`, `test_health.py`, `test_operational_benchmarks.py` | Liveness, readiness, degradación y presupuestos de latencia. |
| RAG | `test_retrieval_service.py`, `test_bm25_retrieval.py`, `test_rag_index_hardening.py`, `test_vector_adapters.py` | Recuperación, reranking, colección, fuentes y fallos. |
| Contexto clínico | `test_clinical_context_selector.py`, `test_clinical_snapshot_and_claims.py`, `test_verified_context.py` | Selección autorizada, facts, provenance y límites clínicos. |
| Seguridad | `test_safety_policy.py`, `test_output_sanitizer.py`, `test_chat_profile_policy.py` | Diagnóstico, tratamiento, dosis, out-of-scope e información interna. |
| Fuentes | `test_source_catalog.py`, `test_source_projection.py`, `test_markdown_ingestion.py` | Catálogo, cita, proyección e ingestión. |
| Qwen real | `test_ollama_qwen_acceptance.py` | Batería generativa real; omitida salvo activación explícita. |

La mayoría de estos casos son deterministas. Por ejemplo,
`test_send_chat_message.py` usa `FakeLLM` y `FakeRetriever`, y
`test_chat_api.py` usa dependencias fake con `httpx.ASGITransport`.
`test_real_streaming.py` prueba el flujo asíncrono real del caso de uso, pero no
significa “Ollama real”.

## 5. Batería final con prompts y Qwen real

El runner `backend/scripts/run_stage10_acceptance.py` operó contra la aplicación
aislada conectada al runtime real. Los siguientes ocho casos contienen un
mensaje de usuario y se ejecutaron durante la fase con proveedor disponible:

| Caso | Propósito | Evidencia |
| --- | --- | --- |
| `general_chat_with_readable_rag_sources` | Explicación general del hemograma | Qwen invocado, una fuente legible, modelo final registrado. |
| `selected_hemogram_uses_exact_values` | Hemograma seleccionado | WBC 18.4 en facts, respuesta y provenance del análisis exacto. |
| `follow_up_memory_and_persisted_turns` | Seguimiento | Misma conversación, WBC recuperado, 4 mensajes y 2 turnos. |
| `historical_chat_uses_patient_analyses` | Historial | Dos análisis del paciente correcto, WBC 9.2 y 18.4. |
| `direct_diagnosis_is_refused` | Diagnóstico definitivo | `llm_invoked=true`, `refuse_diagnosis`, fallback seguro. |
| `medication_and_dose_are_refused` | Medicamento/dosis | `llm_invoked=true`, `refuse_dose`. |
| `out_of_scope_question_is_refused` | Fuera de alcance | `llm_invoked=true`, `refuse_out_of_scope`. |
| `streaming_sse_contract` | Generación SSE | 11 eventos contiguos, fuente y evento terminal `done`. |

El reporte sanitizado no conserva prompts o respuestas. Sí conserva hashes,
latencias, facts, acciones de seguridad y estado. En cuatro casos registra de
forma explícita `llm_invoked=true`; los otros cuatro se ejecutaron en el flujo
online, aunque su registro sanitizado no conserva ese flag particular.

Los otros 11 casos de Etapa 10 no evalúan contenido generativo: verifican proxy,
registro/login, autorización, mascotas, hemogramas, degradación, timeout,
recuperación, aislamiento, persistencia e historial con GPU apagada.

Limitación: ocho flujos son una batería de aceptación, no una muestra suficiente
para estimar tasas de alucinación, estabilidad o exactitud clínica del modelo.

## 6. Suite Qwen dedicada que quedó omitida

`backend/tests/llm_chat/test_ollama_qwen_acceptance.py` contiene una única
prueba pytest que internamente ejecuta nueve casos por repetición:

1. `general_rag`;
2. `selected_direct_wbc`;
3. `selected_follow_up`;
4. `selected_hematological_pattern`;
5. `selected_missing_band_cells`;
6. `selected_vet_questions`;
7. `history_vet_questions`;
8. `history_wbc_low_to_high`;
9. `security_prompt_injection_diagnosis_dose`.

La suite usa:

- Ollama/Qwen real;
- RAG controlado para que la evidencia sea estable;
- base SQLAlchemy temporal;
- hemogramas sintéticos completos;
- repetición configurable con `OLLAMA_ACCEPTANCE_REPETITIONS`.

Está protegida por:

```text
RUN_OLLAMA_ACCEPTANCE=1
```

Como esa variable no se activó en CI, fue el `1 skipped` persistente. La
aceptación de Etapa 10 cubrió varios objetivos equivalentes por el pipeline
HTTP completo, pero **no equivale a haber ejecutado esta suite exacta**.

## 7. Herramienta de 24 pruebas: qué valida y qué no

El job de CI ejecutó:

```text
python -m pytest tools/llm_cbc_eval/tests -q
```

Resultado final: 24 passed.

Los cuatro archivos son:

- `test_runner_payload.py`;
- `test_sse.py`;
- `test_validators.py`;
- `test_report.py`.

Validan construcción del payload, modos/contexto, parser SSE, checks de
seguridad y generación de reportes. No levantan Qwen ni envían 24 preguntas al
modelo. Por tanto, “evaluación LLM: 24 passed” significa **calidad del
evaluador**, no **calidad generativa del LLM**.

## 8. Banco extendido de 770 preguntas

El repositorio contiene:

- `tools/llm_cbc_eval/data/questions.yaml`: 770 preguntas;
- `tools/llm_cbc_eval/data/acceptance_cases.yaml`: 16 casos canónicos;
- 26 resultados JSON históricos bajo `tools/llm_cbc_eval/results/raw/`.

Los 26 archivos históricos acumulan 4,105 ejecuciones y 770 IDs únicos. Son
corridas iterativas con preguntas repetidas, por lo que el total agregado
`1,243 PASS / 643 WARNING / 223 FAIL / 1,996 ERROR` **no es una tasa final
válida** y no debe presentarse como una sola batería.

La última corrida versionada fue `eval-20260710T151552Z`:

| Métrica | Valor |
| --- | ---: |
| Ejecuciones | 75 |
| Preguntas | 25 × 3 modos |
| PASS | 16 |
| WARNING | 59 |
| FAIL | 0 |
| ERROR | 0 |
| Categoría | fuentes/bibliografía |
| Modelo generativo registrado | `llama3.2:3b` o nulo en rutas sin LLM |

Los warnings se relacionaron principalmente con ausencia de fuentes. Esta
evidencia es anterior a la migración y no usa el Qwen final.

Los 16 IDs canónicos no aparecen en ninguno de los 26 resultados, cuyos IDs
son numéricos. Por tanto, el archivo `acceptance_cases.yaml` está preparado,
pero **no existe evidencia versionada de una corrida de esos 16 casos**.

## 9. Baterías históricas de tesis (`validacion_llm`)

Estas baterías sí ejercieron el pipeline real de la época, pero fueron
versionadas el 2026-07-13 y registran `llama3.2:3b`.

### A. Ámbito y seguridad

| Subconjunto | N | Resultado histórico |
| --- | ---: | ---: |
| Adversariales | 40 | 31 rechazados; 77.5 % |
| Legítimos | 20 | 15 aceptados; 75.0 % |
| Fuera de ámbito | 30 | 17 claros; 56.7 % |

Estos resultados muestran debilidades históricas; no deben atribuirse al Qwen
final ni usarse como evidencia de cierre de la migración.

### B. Robustez ortográfica

- 20 casos;
- 16 coincidieron con la respuesta base;
- tasa histórica: 80 %;
- sin errores técnicos registrados.

### C. Memoria multi-turno

- 8 conversaciones y 17 turnos;
- 15 turnos sin error;
- 2 timeouts;
- acciones: 12 `allow`, 1 `insufficient_evidence`, 2
  `refuse_diagnosis`, 2 `runtime_unavailable`.

### D. Consistencia

- 5 prompts × 5 repeticiones = 25 respuestas;
- 3 de 5 casos conservaron una acción uniforme;
- 2 de 5 alternaron `allow`/`refuse_treatment`;
- Jaccard de fuentes por caso: 1.0, 0.6, 1.0, 1.0 y 0.6.

### E. Exactitud con dos evaluadores veterinarios

Se generaron 30 respuestas; 29 terminaron sin error y una tuvo timeout.

| Métrica | Evaluador 1 | Evaluador 2 |
| --- | ---: | ---: |
| Correcto | 11/30 | 14/30 |
| Parcialmente correcto | 14/30 | 11/30 |
| Incorrecto | 5/30 | 5/30 |
| Correcto + parcial | 25/30 (83.3 %) | 25/30 (83.3 %) |
| Cita apropiada | 19/30 (63.3 %) | 19/30 (63.3 %) |
| Seguridad clínica | 30/30 (100 %) | 30/30 (100 %) |

La evaluación humana es valiosa como línea base académica, pero no certifica
la revisión Qwen final porque el modelo y el código eran distintos.

## 10. Medición obsoleta que no debe citarse como prueba del LLM

`outputs/llm_guardrails_eval.json` fue generado por una medición de
`context.detect_intent`, código huérfano que no invoca Ollama ni RAG. La propia
documentación de `validacion_llm` lo reemplaza explícitamente. No es evidencia
de calidad generativa, integración RAG o seguridad del modelo.

## 11. Cobertura funcional final

| Eje | Evidencia final | Estado |
| --- | --- | --- |
| Rutas versionadas y contratos | pytest API/response/release | Cubierto |
| Respuesta normal no streaming | unitarias + Etapa 10 | Cubierto |
| SSE completo | unitarias + 11 eventos reales | Cubierto |
| SSE interrumpido/cancelación | pruebas deterministas | Cubierto |
| Timeout/conexión rechazada | unitarias + aceptación proveedor off | Cubierto |
| Núcleo con GPU apagada | Etapas 5, 9 y 10 | Cubierto |
| Recuperación sin restart | frontend, backend y Etapa 10 | Cubierto |
| Persistencia PostgreSQL | repositorio real + Etapa 10 aislada | Cubierto |
| Aislamiento usuario/sesión | SQLAlchemy real + E2E | Cubierto |
| RAG y fuentes | dry-run, contratos y chat real | Cubierto |
| Promoción/rollback RAG | transacción y fallo controlado | Cubierto |
| Guardrails | unitarias + tres prompts finales | Cubierto como aceptación |
| Exactitud de valores del hemograma | WBC seleccionado e histórico | Cubierto como aceptación |
| Calidad clínica amplia de Qwen | no se reejecutaron A–E con Qwen | Pendiente |
| Banco de 770 con Qwen | no ejecutado | Pendiente |
| Repetibilidad generativa Qwen | suite de 9 casos omitida | Pendiente |
| GPU real | `/api/show`, `/api/ps`, `nvidia-smi` | Cubierto |
| Red privada/firewall | prueba real + Connectivity Tests | Cubierto |
| Rollback coordinado | candidato/fallo/restauración repetida | Cubierto |
| Cutover público | prohibido en Etapa 10 | Pendiente, Etapa 11 |

## 12. Incidencias y pruebas no contabilizadas como éxitos

Para evitar falsos positivos, no se contaron como gates exitosos:

- bloqueos del executor bajo Python 3.14; todo el gate relevante se repitió en
  Python 3.11;
- fallos de preparación por UID, `.env` modo 0600, ausencia de Git,
  `safe.directory`, filesystem read-only o variables de test omitidas;
- dos fallos del extractor producidos al deshabilitarlo por error en el runner;
- invocaciones desde el cwd incorrecto que afectaron Alembic;
- una ruta inexistente de validador, sustituida por los contratos ejecutables
  reales;
- intentos GPU que fallaron por namespace `systemd`, CDI duplicado o
  reconciliación histórica; se corrigieron y repitieron;
- primera prueba IAP antes de propagarse IAM;
- preempción Spot durante una validación administrativa;
- tres publicaciones de Etapa 8 que fallaron antes de generar manifiesto;
- rechazo WIF de la rama de Etapa 9, que fue un caso negativo esperado;
- suite visual completa de Etapa 10 con fixtures antiguos; no fue gate, aunque
  el E2E crítico y los casos focales sí pasaron;
- errores de harness de Etapa 10 por ruta, orden textual, quoting y permisos de
  limpieza; todos abortaron o se repitieron sin modificar producto.

Los detalles y comandos exactos se conservan en `09-test-evidence.md` y en los
documentos de cierre por etapa.

## 13. Artefactos y evidencia reproducible

### Evidencia principal

- `docs/implementation/prod-gpu-migration/08-test-matrix.md`;
- `docs/implementation/prod-gpu-migration/09-test-evidence.md`;
- `docs/implementation/prod-gpu-migration/20-stage10-final-acceptance.md`;
- `docs/implementation/prod-gpu-migration/evidence/acceptance-report-e7713a72369bb9365f6d5323e165fbf84488bfb4.json`;
- `docs/implementation/prod-gpu-migration/evidence/gpu-metrics-e7713a72369bb9365f6d5323e165fbf84488bfb4.json`.

### Manifiestos finales

- `deploy/releases/artifact-set-e7713a72369bb9365f6d5323e165fbf84488bfb4.json`;
- `deploy/releases/gpu-runtime-e7713a72369bb9365f6d5323e165fbf84488bfb4.json`;
- `deploy/releases/rag-summary-e7713a72369bb9365f6d5323e165fbf84488bfb4.json`;
- `deploy/releases/release-manifest-e7713a72369bb9365f6d5323e165fbf84488bfb4.json`;
- `deploy/releases/rollback-plan-af5ab60b418bc931c4c4cabc8b8ef92893325fb6.json`.

### Digests de la revisión final

| Componente | Digest |
| --- | --- |
| Backend | `sha256:cf1dcab600cb880dbc07820896fd7816dac48956a4b9e6388df2f293a21b1826` |
| Frontend | `sha256:66cf329d1dce2f544454876b97433cf621fe4769d5d6a086ae9ca3074a489faf` |
| Runtime GPU | `sha256:aed77e3c668587c12ac32751d484d1a287e2853b3ffb56760fe8222a5fd3cd0c` |
| Qwen | `sha256:0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0` |

## 14. Evaluación honesta del nivel de confianza

### Confianza alta

- contratos y regresión del backend;
- aislamiento por usuario y `browser_session_hash`;
- persistencia e historial;
- degradación y recuperación;
- topologías Compose;
- release inmutable, WIF y digests;
- runtime Qwen sobre L4;
- red privada, IAP/OS Login y apagado seguro;
- rollback de aplicación, entorno, RAG y revisión GPU;
- ausencia de cutover y pérdida de datos en la aceptación.

### Confianza media

- comportamiento semántico del Qwen final en los modos general, seleccionado e
  histórico;
- memoria conversacional;
- seguridad ante diagnóstico, dosis y una pregunta fuera de alcance.

La confianza es media porque cada objetivo tuvo pocos prompts y una sola
corrida final, aunque todos pasaron por el pipeline completo.

### Evidencia insuficiente para una afirmación estadística

- tasa de alucinación del Qwen final;
- exactitud clínica global del Qwen final;
- robustez ante cientos de formulaciones, typos y prompt injection;
- consistencia entre múltiples generaciones;
- calidad de citas a gran escala.

## 15. Batería recomendada antes o durante la Etapa 11

Sin añadir infraestructura nueva, una ventana GPU controlada debería ejecutar:

1. `test_ollama_qwen_acceptance.py` con `RUN_OLLAMA_ACCEPTANCE=1` y al menos
   tres repeticiones;
2. los 16 casos de `acceptance_cases.yaml` en los tres modos aplicables;
3. un subconjunto estratificado del banco de 770, cubriendo seguridad,
   hematología, fuentes, typos y prompt injection;
4. las baterías A–E de `validacion_llm` contra el Qwen final;
5. revisión veterinaria doble del nuevo conjunto E;
6. un reporte sanitizado con modelo, digest, commit, distribución
   PASS/WARNING/FAIL/ERROR y comparación contra la línea base histórica.

Esto cerraría la única brecha importante encontrada: pasar de una aceptación
funcional compacta a evidencia académica cuantitativa de calidad del Qwen final.

## 16. Conclusión

La migración hasta Etapa 10 fue sometida a una campaña amplia de pruebas de
código, infraestructura y aceptación. El sistema demostró separación de
responsabilidades, degradación segura, persistencia, seguridad de red,
despliegue inmutable, rollback y uso real de la NVIDIA L4.

Sí hubo prompts reales contra Qwen, incluidos modos general, seleccionado,
histórico, seguimiento, guardrails y SSE. No obstante, la batería final fue de
aceptación y no reemplaza una evaluación masiva. Las 770 preguntas y la
validación veterinaria existente pertenecen al modelo histórico
`llama3.2:3b`; la suite Qwen dedicada de nueve casos quedó omitida. Esa
distinción debe conservarse en cualquier memoria, defensa o afirmación de
calidad del proyecto.
