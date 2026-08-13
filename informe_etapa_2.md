
Informe final — Etapa 2 (ResponsePlan + ContextBundle)

1. Qué encontré de la etapa 1 y cómo lo reutilicé

La etapa 1 (commit 9401b2a6) ya había creado, pero sin integrar, los contratos fundacionales:
- domain/response_plan.py: enums RetrievalPolicy (NONE/OPTIONAL/REQUIRED), RetrievalStatus (NOT_REQUESTED/USED/NO_MATCH/UNAVAILABLE), KnowledgeMode (PARAMETRIC/DATABASE/RAG_AUGMENTED/DATABASE_AND_RAG/SAFETY_BOUNDARY), y el dataclass ResponsePlan (con docstring explícito: "Stage 1 defines this contract without replacing the current router").
- domain/generation_config.py: GenerationProfileSettings ya usado por el use case.
- En send_chat_message.py, los tres enums (no ResponsePlan) ya estaban parcialmente enhebrados en _ValidatedCandidate, ModelRequest, telemetría (_route_trace) y dos helpers ya correctos: _retrieval_policy() y _knowledge_mode().

Lo que no existía todavía: ResponsePlan se importaba pero nunca se instanciaba, y la decisión real de "¿puedo responder sin RAG?" seguía gobernada por el booleano policy.use_rag en tres puntos concretos (ver §3). El vocabulario canónico ya fijado por la etapa 1 coincide con el de plan_1.md (REQUIRED, USED, DATABASE) y no con las variantes de plan_2.md (REQUIRED_FOR_CITATIONS, HIT, DATABASE_GROUNDED); adopté ese vocabulario existente sin crear alias ni una segunda familia de enums.

2. Archivos de producción modificados

- backend/app/core/availability.py
- backend/app/modules/llm_chat/api/schemas.py
- backend/app/modules/llm_chat/application/use_cases/send_chat_message.py
- backend/app/modules/llm_chat/domain/__init__.py
- backend/app/modules/llm_chat/domain/clinical.py
- backend/app/modules/llm_chat/infrastructure/repositories/sqlalchemy_repositories.py

Nuevos:
- backend/app/modules/llm_chat/domain/context_bundle.py (ContextBundle, DerivedClinicalFinding)
- backend/app/modules/llm_chat/application/services/context_bundle_builder.py (build_context_bundle)

3. Bloque A — ResponsePlan y desacoplamiento del RAG

Añadí SendChatMessageUseCase._build_response_plan(), que construye un ResponsePlan real a partir de la decisión ya tomada por ConversationRouter/SafetyPolicy (sin tocar esos clasificadores) y de contract_for_policy(). A partir de ahí, la bifurcación de RAG-vacío en _execute lee plan.retrieval_policy, no el booleano crudo.

Eliminé las tres bifurcaciones activas que convertían "sin RAG" en prohibición de responder:
1. Pre-generación (antes forzaba safety_action=INSUFFICIENT_EVIDENCE + instrucción de abstención pura cuando no había datos clínicos, y prohibía "explicar causas" cuando sí los había): ahora, si retrieval_policy is OPTIONAL, se permite responder con conocimiento paramétrico/base de datos; solo si retrieval_policy is REQUIRED se añade una nota de transparencia (no inventar fuentes), sin forzar abstención.
2. Post-validación (action = SafetyAction.INSUFFICIENT_EVIDENCE reescribía una respuesta ya validada y segura): eliminado por completo — es exactamente el defecto #1 de contexto_1/contexto_2.
3. Corregí un efecto colateral que introducía mi propio cambio: rule_id="medication_education" fuerza el contrato MEDICATION_EDUCATION (use_rag=True obligatorio); al dejar de forzar rule_id="insufficient_evidence", ese rule_id sobrevivía con use_rag=False, lo que habría rechazado la respuesta por mandatory_contract_rag_policy. Lo neutralizo puntualmente (degraded_rule_id) preservando el resto de rule_id (p. ej. la subcadena "history" que contract_for_policy usa para elegir HISTORICAL_CBC).

Verifiqué que el tipo de claim CONVERSATIONAL (ya existente, sin fact_ids/source_ids/policy_rule_id) queda disponible en el contrato estructurado para estos casos — no fue necesario tocar structured_response.py ni el envelope generativo.

Disponibilidad: ChatAvailability.chat_ready dependía de rag_ready (module_ready and provider.ready and rag_ready). Lo corregí a module_ready and provider.ready; añadí degraded (chat_ready and not rag_ready) y actualicé status/ReadinessSnapshot.status para reportar degraded en vez de enmascarar una caída de Chroma como caída total del chat. Confirmé (grep) que ningún código de producción usa chat_ready para bloquear el envío de mensajes por turno — es solo un dato de salud/observabilidad, así que el cambio no tiene efecto en la ruta de mensajes, solo en el reporte de salud.

No toqué conversation_routing.py, intent_classifier.py ni safety_policy.py (routing/seguridad quedan para su propia etapa), ni _unsupported_pattern_interpretation (validador legítimo de interpretación de patrón, no relacionado con permiso de responder).

4. Bloque B — ContextBundle

ContextBundle (domain) reutiliza PatientContext, HemogramStudy y ConversationMemory ya existentes en domain/clinical.py (no duplica el modelo de hechos de laboratorio: ClinicalParameter/VerifiedFact siguen siendo la única representación de valores). Añadí DerivedClinicalFinding solo para lo que no tenía id estable: hallazgos ML (classifier_outcome.active_labels/classification_status con probabilidad) y señales de calidad (quality_flags, extraction_confidence), con ids analysis:{id}:ml:... / analysis:{id}:quality:.... Deliberadamente no convierto observations (texto libre) en hechos autorizados.

build_context_bundle() se invoca una vez por turno en send_chat_message.py, justo después de materializar facts/snapshot, y se actualiza con rag_evidence tras la recuperación. Se registra en el log response_plan (junto con el plan) para trazabilidad.

Por modo:
- General sin pet_id: patient_profile=None, sin estudios — igual que antes.
- General con pet_id: nuevo método _general_context() en el repositorio: valida propiedad (Pet.owner_id == user_id), carga solo el perfil (nunca consulta Analysis), y ahora incluye peso, notas (saneadas, truncadas a 500 car., vía _clean_text) y zona de residencia — esta última únicamente si residence_consent_at is not None (nunca lat/lng). Corregí ChatRequest.validate_context_reference para permitir pet_id opcional en general (analysis_id sigue prohibido) y corregí el corto-circuito de ClinicalContext.prompt_payload() que descartaba el perfil incluso cuando estaba cargado.
- Hemograma seleccionado / Historial: sin cambios en la carga (ya traían el inventario completo por estudio con ML/calidad/procedencia); ContextBundle los proyecta con ids trazables sin recortarlos.

omitted_fact_ids se calcula, cuando hay ClinicalContextSnapshot, como la diferencia real entre prioritized_fact_keys y materialized_fact_keys (mecanismo de presupuesto ya existente, no inventé uno nuevo) — no lo dejé en placeholder vacío salvo que no exista snapshot.

No reconstruí PromptBudgetPlanner, el tokenizer definitivo, ni el envelope generativo: ContextBundle es un punto de integración real y poblado, pero el prompt final se sigue construyendo con ClinicalContext.prompt_payload() como antes.

5. Verificación estática realizada

- py_compile sobre los 8 archivos tocados/creados.
- Importación real del árbol de módulos (SendChatMessageUseCase, ContextBundle, build_context_bundle, SqlAlchemyAnalysisContextRepository, ChatRequest, ChatAvailability) con settings mínimos — sin errores de import/circularidad.
- Pruebas funcionales manuales (no vía pytest, ejecutadas como script suelto): ChatRequest(general, pet_id=...) válido / ChatRequest(general, analysis_id=...) rechazado; ClinicalContext.prompt_payload() con perfil general incluido; ChatAvailability con Chroma caído → chat_ready=True, degraded=True; _patient() con/sin consentimiento de residencia y saneamiento de notas; ClinicalContextSnapshot.from_context() sin fallar con un perfil general cargado; build_context_bundle().
- impact() (GitNexus) sobre PatientContext, get_owned_context, prompt_payload, _execute tras reindexar: riesgo LOW/MEDIUM, sin llamadores rotos fuera de tests/ (no tocados).
- detect_changes() no arrojó señal útil tras el reindex (compara contra el índice recién reconstruido, no contra main como rama separada indexada); usé git diff --stat main y revisión manual completa de cada diff como sustituto, conforme al criterio de cierre explícito de la tarea.

6. Dependencias externas / riesgos pendientes

- Pet.species no existe como columna (hardcoded "canine" en PatientContext) — fuera de alcance (módulo pets).
- El fallback documentary_validation_fallback (~línea 1571, activado tras dos intentos de generación fallidos con policy.use_rag sin acotar a REQUIRED) sigue usando _safety_fallback_answer con prosa fija — deliberadamente no lo toqué: es "contrato generativo"/eliminación de prosa legada, reservado a una etapa posterior.
- El defecto preexistente de rule_id="medication_education" + use_rag=False sin RAG en la rama clinical.has_data (fuera de la bifurcación que reescribí) ya existía antes de esta etapa; lo neutralicé como efecto directo de mi cambio, pero no audité si hay otras combinaciones rule_id/contrato igualmente fràgiles — quedaría para la etapa del contrato generativo.
- ruff no está instalado en este entorno; no pude correr lint automatizado (sí py_compile + imports + smoke tests).

7. Confirmación explícita

No creé, modifiqué ni ejecuté ningún archivo bajo tests/, ni ejecuté suites de pruebas. No implementé la etapa 3 (memoria), etapa 4 (routing/seguridad), ni ninguna etapa posterior — routing, clasificador de intención, prompts, PromptBudgetPlanner, tokenizer, envelope generativo y streaming quedan intactos. Me detengo aquí, al cierre de la etapa 2 unificada.