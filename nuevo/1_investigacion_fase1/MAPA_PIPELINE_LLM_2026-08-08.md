# Mapa del pipeline real — un turno del chat de HemoVet

Reconstruido leyendo el código y **verificado contra la telemetría** de 133
llamadas reales. Cada etapa indica el evento que emite, que es lo que permite
comprobar desde fuera que se ejecutó.

---

## Call graph

```
navegador  frontend_4/src/app/api.ts :: streamChatOnce
   │  POST /api/v1/chat/stream   Accept: text/event-stream
   │  headers: Authorization Bearer, X-HemoVet-Browser-Session-ID
   ▼
api/router.py:576  stream_chat
   ├─ autenticación JWT + hash de sesión de navegador
   ├─ _command()  → construye el comando del caso de uso
   ▼
application/use_cases/send_chat_message.py  SendChatMessageUseCase.stream()
   │
   ├─ 1. ROUTING ......... services/conversation_routing.py:92  route()
   │      usa   services/intent_classifier.py     (REGEX, sin LLM)
   │      usa   services/safety_policy.py
   │      → evento llm_chat.routed
   │        route, intent, intent_confidence, safety_action,
   │        use_clinical_context, use_rag, is_follow_up, message_length
   │      ⚠ puede terminar el turno aquí con SafetyAction.REFUSE_OUT_OF_SCOPE
   │
   ├─ 2. PERFIL .......... services/chat_profile_policy.py
   │      → evento llm_chat.profile_selected
   │        profile, history_limit(12), num_ctx(16384), num_predict(1280),
   │        max_input_tokens(12000), temperature(0.3), rag_top_k(3)
   │
   ├─ 3. PLAN ............ _build_response_plan()
   │      → evento llm_chat.response_plan
   │        allowed_claim_types, required_fact_count,
   │        context_bundle_patient_loaded, context_bundle_omitted_fact_count
   │
   ├─ 4. CONTEXTO CLÍNICO  services/clinical_facts.py, clinical_context_revision.py
   │      → evento llm_chat.clinical_claim_scope
   │        authorized_code_count(18), materialized_fact_count
   │
   ├─ 5. RAG (si use_rag)  ChromaDB, estrategia dense_bm25_rrf
   │      → evento llm_chat.retrieval
   │        candidate_count, selected_count(3), top_score, total_ms(183-655)
   │      ⚠ sólo 8 de 70 preguntas lo activaron
   │
   ├─ 6. PROMPT .......... services/prompt_budget_planner.py
   │      ✖ NO se registra el texto. Sólo tamaños.
   │
   ├─ 7. COLA ............ semáforo del backend (1 generación)
   │      → evento llm_chat.queue_acquired   queue_duration_ms (mediana 0)
   │
   ├─ 8. GENERACIÓN #1 ... provider Ollama → llama-server (-np 1)
   │      → evento llm_chat.generation_config  (modelo, temp, thinking=false…)
   │      → evento llm_chat.ollama_metrics
   │        prompt_eval_count/duration, eval_count/duration,
   │        load_duration, inference_device(full_gpu), gpu_memory_bytes
   │      ✖ NO se registra el texto generado
   │
   ├─ 9. PARSER + VALIDACIÓN
   │      services/structured_response.py     (esquema del sobre)
   │      services/output_claim_validator.py  (claims)
   │      services/response_contracts.py
   │      → evento llm_chat.validation
   │        result ∈ {valid, repairable, invalid}, reason,
   │        validation_detail_code, finish_reason, envelope_chars
   │
   ├─ 10. ¿REPARABLE? .... send_chat_message.py:1735
   │       condición: max_generation_attempts >= 2
   │       → evento llm_chat.regeneration (reason)
   │       └─► GENERACIÓN #2  perfil *_structured_repair, temp 0.1, num_predict 1024
   │            (vuelve a 9)
   │
   ├─ 11. ¿SIGUE MAL? .... send_chat_message.py:4283  _last_resort_candidate()
   │       → evento llm_chat.last_resort
   │       └─► GENERACIÓN #3  perfil original, prompt RECORTADO (3.871 → 1.374 tok)
   │            (vuelve a 9)
   │
   ├─ 12. TERMINAL
   │       éxito → llm_chat.candidate_selected + llm_chat.completed
   │       fallo → llm_chat.terminal_error  (error_code, final_state, request_id)
   │
   ├─ 13. PERSISTENCIA ... infrastructure/repositories/sqlalchemy_repositories.py
   │       ⚠ en turnos `failed`, response = null (0 de 17 conservan texto)
   │
   └─ 14. SSE ............ api/sse.py  encode_sse
           eventos: start, context_ready, retrieval_completed,
                    generation_started, heartbeat(15 s), status(stage),
                    final | error, done
           ✖ NO hay eventos delta/token → sin streaming de texto
```

---

## Validadores localizados

| Motivo | Archivo:línea | Nivel | n en la batería |
|---|---|---|---:|
| `structured_schema_invalid` | `services/structured_response.py:961` | invalid | 24 |
| `missing_required_clinical_facts` | `use_cases/send_chat_message.py:381` | repairable | 21 |
| `structured_patient_fact_id_required` | `use_cases/send_chat_message.py:4801` | invalid | 8 |
| `ambiguous_parameter_claim` | `services/output_claim_validator.py:638` | invalid | 5 |
| `structured_patient_fact_not_materialized` | `use_cases/send_chat_message.py:4720` | invalid | 5 |
| `policy_rule_id_missing` (detalle) | `services/structured_response.py:645` | detalle | 15 |
| `definitive_diagnosis` | seguridad | invalid | 2 |
| `mandatory_diagnosis_boundary` | seguridad | invalid | 2 |
| `indirect_treatment_recommendation` | seguridad | invalid | 2 |
| `medical_refusal_contract` | seguridad | invalid | 1 |
| `limitation_claim_invalid` | redacción | invalid | 2 |
| `structured_json_invalid` | formato | invalid | 2 |
| otros (6 motivos) | varios | — | 6 |

**Sólo 7 de 133 rechazos son barreras de seguridad clínica.**

---

## Dónde se pierde información

| Punto | Qué se pierde | Consecuencia |
|---|---|---|
| Paso 6 | El texto del prompt | No se puede comparar prompt primario y de reparación salvo por tamaño |
| Paso 8 | El texto generado | No se puede saber si la respuesta rechazada era correcta |
| Paso 9 | La envoltura rechazada | `CHAT_STRUCTURED_DEBUG_DIR` la volcaría, pero está apagado |
| Paso 5 | `chunk_id` y texto del RAG | Sólo hay recuentos y scores |
| Paso 13 | `response` en turnos fallidos | 0 de 17 conservan contenido |
| Paso 14 | Tokens intermedios | El usuario no ve nada hasta que la validación termina |

---

## Timeouts y reintentos

| Parámetro | Valor |
|---|---|
| `OLLAMA_TIMEOUT_SECONDS` | 120 |
| `CHAT_TOTAL_TIMEOUT_SECONDS` | 240 |
| `CHAT_QUEUE_TIMEOUT_SECONDS` | 60 |
| `max_generation_attempts` | 2 (+ último recurso ⇒ hasta 3–4 llamadas) |
| `OLLAMA_KEEP_ALIVE` (servicio) | 30 m, sobreescrito por `keep_alive: -1` en la petición |

---

## Perfil temporal real (`SEL-08`, medido)

```
0.000 s   POST enviado
0.151 s   SSE start · context_ready · retrieval_completed · generation_started
          (las cuatro marcas llegan juntas al abrir el flujo)
0.151 s   LLAMADA #1 — 3.871 tok in
15.153 s  heartbeat
22.3  s   generación #1 completa — 286 tok out, 12,9 tok/s
29.148 s  status validating  → repairable · PLT:value,PLT:unit
29.148 s  status repairing
          LLAMADA #2 — 3.966 tok in, temp 0,1
52.4  s   generación #2 completa — 299 tok out
          → repairable · EL MISMO detalle
          LLAMADA #3 (último recurso) — 1.374 tok in
72.2  s   generación #3 completa — 259 tok out
          → invalid · structured_schema_invalid · policy_rule_id_missing
77.387 s  evento error — generation_repair_failed
```

Suma de generación pura: **65,2 s de GPU para entregar cero contenido.**
