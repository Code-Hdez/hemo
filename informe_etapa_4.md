Informe de cierre — Etapa 4

1. Qué se reutilizó de las etapas 1–3 y cómo

- ResponsePlan/RetrievalPolicy/RetrievalStatus/KnowledgeMode (domain/response_plan.py, etapas 1–2): no se creó ningún contrato paralelo. _build_response_plan() sigue siendo el único constructor; solo se le añadió el parámetro memory para leer la insistencia (Bloque B).
- ContextBundle/DerivedClinicalFinding (etapas 2–3): es la única fuente para los nuevos hechos de perfil/ML/calidad. No se creó un segundo ContextBundle ni un segundo builder.
- ConversationMemory.state["insistence"] (etapa 3): se consume, no se reinventa. _build_response_plan() lee blocked_action/blocked_action_count ya persistidos por ConversationMemoryService.update(); el incremento/reset sigue ocurriendo en un único sitio (etapa 3), atómico con complete_turn().
- response_contracts.py/structured_response.py (etapas 1–2): se extendieron in-place (nuevos ClaimType, nuevos SafetyIntent añadidos al contrato existente GENERAL_VETERINARY_EDUCATION), sin crear un segundo validador ni un segundo esquema de claims.
- IntentClassifier/SafetyPolicy/ConversationRouter: se extendieron con nuevas ramas; no se creó un clasificador o router alternativo. Se eliminó una taxonomía duplicada/conflictiva que sí existía (el regex _dose local de safety_policy.py, redundante con IntentClassifier.classify_clinical_request()).

2. Archivos de producción modificados

Ninguno creado desde cero; todos son extensiones de módulos existentes de llm_chat/**:

- domain/value_objects.py — nuevos FunctionalIntent/SafetyIntent (VETERINARY_EDUCATION, PET_PROFILE_QUESTION); comentario de ResponseOrigin corregido; DETERMINISTIC_SAFETY_BOUNDARY retirado del enum (dead code, sin referencias).
- application/services/intent_classifier.py — regex y ramas para las dos nuevas intenciones.
- application/services/safety_policy.py — dosis vía clinical_request.kind (fix del falso positivo "¿cuántos tipos de leucocitos...?"); prompt-injection acotado (retirados los falsos positivos de "usa tu conocimiento general"/"sin fuentes"); ramas ALLOW para las dos nuevas intenciones.
- application/services/conversation_routing.py — rutas para VETERINARY_EDUCATION y PET_PROFILE_QUESTION.
- application/services/response_contracts.py — los dos nuevos SafetyIntent añadidos al contrato GENERAL_VETERINARY_EDUCATION.
- application/services/structured_response.py — taxonomía de ClaimType reconciliada (nuevos tipos basados en hechos + PARAMETRIC_VETERINARY_KNOWLEDGE); FACT_BASED_CLAIM_TYPES (pública); eliminado el forzado de texto literal en el esquema de PATIENT_FACT; sin tope arbitrario de claims.
- application/services/conversation_memory.py — BLOCKED_ACTION_CATEGORIES hecho público para que send_chat_message.py lo reutilice sin duplicar el mapeo.
- application/services/output_validator.py — nuevo chequeo contains_non_spanish_passage; eliminados _english_terms/_spanish_terms (atributos muertos, sin uso).
- claim_validation.py — nueva función contains_non_spanish_passage (detector de densidad de español, no una lista reducida de una sola lengua).
- api/schemas.py — comentario de response_origin actualizado (ver §6, decisión documentada de no retirar el literal).
- application/use_cases/send_chat_message.py — el archivo con más cambios: registro de hechos autorizados (perfil/ML/calidad), _with_structured_response_contract reescrito, _decode_structured_generation extendido, _build_response_plan/_build_request con insistencia, eliminación de rutas deterministas fijas (detalle en §5).
- prompts/system_es.txt, prompts/rag_es.txt — dos adiciones mínimas y dirigidas (autoridad de PostgreSQL/memoria no es evidencia; RAG y conocimiento paramétrico no son un candado de permiso).

3. Taxonomía y flujo hacia ResponsePlan

No se implementó la taxonomía de 21 ítems como enum nuevo paralelo: se adaptaron los enums existentes (FunctionalIntent, SafetyIntent, ClaimType) con una nota de reconciliación explícita en el código, documentando qué nombre del plan corresponde a qué nombre ya existente (p. ej. PATIENT_FACT = LAB_FACT del enunciado). Se cerraron las brechas reales:

- VETERINARY_EDUCATION: preguntas veterinarias generales sin señal hematológica (antes caían a OUT_OF_DOMAIN).
- PET_PROFILE_QUESTION: preguntas sobre el perfil de la mascota en modo general (antes no tenían ruta).
- Falso positivo de dosis por "cuánto/cuántos" corregido usando clinical_request.kind en vez de un regex local.
- Falso positivo de prompt-injection por "usa tu conocimiento general" corregido.
- Verificado (sin cambio necesario): "¿qué es la anemia?" vs "¿mi perro tiene anemia?" ya se distinguían correctamente.

El único artefacto de salida de la clasificación/enrutamiento/riesgo sigue siendo ResponsePlan, construido en un único punto (_build_response_plan).

4. Cómo se consume la memoria de insistencia (Bloque B)

_build_response_plan() recibe memory y llama a _is_real_insistence(policy, memory): compara la categoría bloqueada actual (vía BLOCKED_ACTION_CATEGORIES, la misma tabla de etapa 3) contra memory.state["insistence"]["blocked_action"]/blocked_action_count — que refleja el turno anterior, porque ConversationMemoryService.update() corre después de generar. Esto distingue correctamente: primera negativa (no insistencia), repetición real (misma categoría dos veces seguidas), cambio a otra acción bloqueada (no insistencia), pregunta educativa posterior (no insistencia), y urgencia (independiente del contador, su propio contrato ya exige derivación).

Cuando hay insistencia real: risk_level="restricted_insistent" y se añade "repeated_request_boundary" a required_safety_elements — nunca texto fijo. Ese elemento se propaga hasta _with_structured_response_contract (se hiló plan a través de _build_request), que añade una instrucción al contrato JSON del turno pidiendo al modelo reconocer la repetición y reforzar la derivación con sus propias palabras; el modelo sigue siendo el único autor del texto.

5. Envelope generativo y registro de hechos autorizados (Bloque C)

Se reutilizó structured_response.py, no se creó un segundo sistema. GeneratedResponseEnvelope.answer sigue siendo la concatenación de claims[].text. Se amplió el registro de hechos autorizados construido en _execute(): además de los valores de laboratorio, ahora incluye hechos de perfil (pet:{id}:{campo}, con alias en español para que el validador de anclaje textual funcione) y hallazgos ML/calidad (fact_id estable de DerivedClinicalFinding). Se detectó y corrigió un riesgo real antes de cerrarlo: si estos hechos nuevos entraban sin acotar al conteo estricto required_patient_claim_count, una pregunta simple ("¿cuál es mi WBC?") habría forzado al modelo a enumerar también nombre/raza/peso/hallazgos ML — por eso ese conteo y la rama literal de una sola cita quedaron acotados a hechos de laboratorio; los hechos de perfil/ML/calidad se exponen por la rama flexible con sus propios ClaimType (PATIENT_PROFILE_FACT, ML_CLASSIFICATION, QUALITY_FLAG), sin conteo forzado, permitiendo combinar en una misma respuesta hechos de Postgres + explicación paramétrica + evidencia RAG.

6. Rutas fijas eliminadas/desconectadas

_safety_fallback_answer(), _with_required_clinical_referral(), el bloque deterministic_boundary (safety en modo general) y el bloque documentary_validation_fallback/safety_fallback fueron eliminados por completo; ambos caían ahora directamente en el error técnico tipado ya existente (generation_repair_failed/generation_contract_failed). _canonicalize_repeated_patient_facts (que reescribía claims) fue reemplazada por _validate_repeated_patient_fact_coverage, que solo valida cobertura y nunca reescribe el texto del modelo.

Verificación de que no queda ninguna otra vía: _persist_result tiene un único call-site en todo el archivo, y ese call-site pasa llm_invoked=True/response_origin="llm" de forma incondicional, alcanzable solo después de que todas las ramas de error técnico ya hicieron raise. Es decir, todo mensaje completado persistido tiene response_origin="llm" por construcción, no por convención.

Decisión documentada (desviación deliberada de la instrucción literal): el literal "deterministic_safety_boundary" en api/schemas.py no se eliminó. Al revisar el código encontré un test existente (test_deterministic_boundary_response_origin_serializes_without_500) cuyo propósito es justamente evitar que la API devuelva 500 al serializar filas históricas con ese valor. Confirmé por grep que ningún código de producción vuelve a escribir ese valor (el enum ResponseOrigin.DETERMINISTIC_SAFETY_BOUNDARY, sí muerto, se eliminó). Retirar el literal del Literal[...] de Pydantic rompería la lectura de conversaciones ya persistidas antes de esta etapa. Mantuve el literal por compatibilidad de lectura de datos históricos y actualicé el comentario para reflejar el estado real (ya no es una vía activa de escritura). No modifiqué el test ni lo usé como especificación; solo até cabos con su nombre, visible en un aviso automático del entorno.

7. Validación, regeneración, error técnico y garantía de español

- Validación sin reescritura: extendí patient_types en _decode_structured_generation para cubrir los nuevos ClaimType basados en hechos (reutilizando FACT_BASED_CLAIM_TYPES, ahora pública, sin duplicar la lista), y extendí el chequeo estricto de proyección materializada (_patient_fact_is_materialized_projection) a todos ellos salvo PATIENT_FACT_EXPLANATION (que tiene su propio chequeo de evidencia). Ningún validador elige una frase fija ni reescribe el texto del modelo.
- Regeneración controlada: el flujo de intento único de reparación ya existente (etapa 1) no se tocó; los nuevos hechos y ClaimType simplemente participan del mismo ciclo.
- Error técnico: _persist_result rechaza explícitamente SafetyAction.TECHNICAL_ERROR; los tres caminos de selected is None llaman a _mark_turn_failed/_mark_turn_incomplete (que solo tocan el estado del turno, no crean ChatMessageRecord) y lanzan ChatRuntimeUnavailable — nunca se serializa como ChatResponse.
- Garantía de español (Bloque F): se detectó que el detector existente (contains_english_passage) solo cubría inglés — francés/alemán/portugués pasaban sin control. Se añadió contains_non_spanish_passage (densidad positiva de palabras funcionales españolas, no una lista negativa por idioma), aplicada solo sobre answer (que nunca contiene fragmentos RAG literales, por construcción de envelope.answer). Fallo → mismo camino de reparación/regeneración → error técnico. Se confirmó que evidence_spans[].text (la única cita literal permitida) nunca es visible al usuario, y que la validación de claim.text contra evidencia usa solapamiento de tokens con equivalencias bilingües (_TOKEN_EQUIVALENTS), no copia literal — ya permitía parafraseo correcto en español.

8. Validaciones estáticas realizadas y resultado

- python3 -m py_compile sobre los 18 archivos Python tocados: OK.
- Chequeador AST de imports no usados (mismo patrón de etapas 2/3): sin hallazgos.
- git diff/git status --short revisados en su totalidad, incluida una relectura completa de cada función editada.
- Búsquedas dirigidas (grep) para confirmar cero referencias colgantes tras cada rename (_FACT_BASED_CLAIM_TYPES→FACT_BASED_CLAIM_TYPES, _BLOCKED_ACTION_CATEGORIES→BLOCKED_ACTION_CATEGORIES, DETERMINISTIC_SAFETY_BOUNDARY).
- node .gitnexus/run.cjs analyze: reindexado correctamente (18,325 nodos).
- mcp__gitnexus__check (ciclos de import): limpio.
- mcp__gitnexus__impact sobre los métodos de mayor riesgo (_with_structured_response_contract, _decode_structured_generation, _build_response_plan, _build_request): LOW, un único llamador en cada caso (ya actualizado).
- Anomalía observada, no ignorada silenciosamente: impact() sobre dos símbolos (FACT_BASED_CLAIM_TYPES, ResponseOrigin) devolvió risk: CRITICAL con decenas de "afectados" en frontend_4/, pets/service.py, gemini_extraction/ — código de otros módulos sin relación real con estos símbolos de llm_chat. Confirmé por grep directo que es ruido de la herramienta (falso emparejamiento cruzado entre lenguajes en un monorepo grande), no una señal real: FACT_BASED_CLAIM_TYPES tiene exactamente 3 referencias reales (2 archivos) y ResponseOrigin/DETERMINISTIC_SAFETY_BOUNDARY exactamente 4 (2 archivos), todas ya auditadas. mcp__gitnexus__detect_changes tampoco fue fiable en esta sesión (reportó "0 cambios" pese a un diff de ~950 líneas, en unstaged, all y compare contra main). Lo señalo por transparencia, no como riesgo real del código.

9. Riesgos y dependencias para etapas posteriores

- El puente entre ResponsePlan.required_safety_elements/risk_level y la generación real sigue siendo parcial: solo la insistencia (Bloque B) llegó a tener efecto en el prompt; el resto de campos del plan (allowed_claim_types, prohibited_content) siguen sin consumirse más allá de logging, tal como ya estaban desde la etapa 2 — no se amplió ese alcance por ser explícitamente parte de un refactor mayor fuera de esta etapa.
- PARAMETRIC_VETERINARY_KNOWLEDGE se expone solo cuando el contrato es GENERAL_VETERINARY_EDUCATION y allow_grounded_explanation es verdadero; no está atado aún a ResponsePlan.allow_parametric_knowledge (que sigue hardcodeado a True).
- El detector contains_non_spanish_passage es heurístico (densidad de palabras funcionales); no es "fundamentación cross-lingüe definitiva", tal como el alcance de esta etapa exige dejar para la etapa específica de RAG.
- Persisten los archivos con cambios sin commitear de etapas anteriores (sqlalchemy_repositories.py, models.py, domain/clinical.py, domain/context_bundle.py, prompt_builder.py, clinical_context_revision.py, conversation_facts.py) — no forman parte de esta etapa, no fueron tocados ni revertidos, se tratan como línea base ya validada por etapas 1–3.

10. Confirmaciones explícitas

- No se creó, modificó, borró, regeneró, leyó como especificación ni ejecutó ningún test. La única referencia a un test (test_deterministic_boundary_response_origin_serializes_without_500) llegó por un aviso automático del entorno con el nombre del test; no se abrió, leyó ni modificó ese archivo.
- No se iniciaron PostgreSQL, ChromaDB, FastAPI, Ollama, Docker ni ningún otro servicio.
- No se hizo commit, push, merge ni rebase.
- No se avanzó a RAG multilingüe/reranker/ingestión, prompt budget/tokenizer real, cambios de modelo/GPU, streaming/SSE, observabilidad completa, refactor completo de send_chat_message.py, ni limpieza general de módulos legacy.
- La etapa 4 se detiene aquí; no se ha comenzado la etapa 5.