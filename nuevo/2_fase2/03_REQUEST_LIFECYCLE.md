# 03 — Ciclo de vida de una pregunta

Perfil temporal real de `SEL-08`, con las tres llamadas al modelo medidas:

```
 0.000 s  POST /api/v1/chat/stream
 0.151 s  SSE: start · context_ready · retrieval_completed · generation_started
          (las cuatro marcas llegan juntas al abrir el flujo — el servidor las
           emite en bloque, así que no miden fases separadas)
 0.151 s  LLAMADA #1  hemogram_interpretation · temp 0.3 · 3.871 tok in
15.153 s  heartbeat
22.3   s  fin generación #1 — 286 tok out · 12,9 tok/s
29.148 s  status validating  → repairable · missing_required_clinical_facts
                               detalle: PLT:value,PLT:unit
29.148 s  status repairing
          LLAMADA #2  *_structured_repair · temp 0.1 · 3.966 tok in
52.4   s  fin generación #2 — 299 tok out → MISMO fallo
          LLAMADA #3  último recurso · prompt recortado a 1.374 tok
72.2   s  fin generación #3 — 259 tok out
          → invalid · structured_schema_invalid · policy_rule_id_missing
77.387 s  SSE error — generation_repair_failed · response persistida: null
```

**65,2 s de GPU para entregar cero contenido.**

## Qué ocurre en los N segundos que el usuario espera

- **0,4 %** del tiempo total: todo el backend (routing, contexto, RAG, cola,
  validación, persistencia, red)
- **99,6 %**: dentro de Ollama, del cual 88,4 % es decode
- **0 %**: el usuario no recibe ningún token intermedio — no hay eventos
  `delta`/`token`; sólo `heartbeat` cada 15 s

## Etapas y dónde viven

Ver `MAPA_PIPELINE_LLM_2026-08-08.md` de la Fase 1 para el call graph completo
con archivo y función por etapa; sigue siendo válido y ahora está respaldado por
la confirmación de que HEAD **es** producción.
