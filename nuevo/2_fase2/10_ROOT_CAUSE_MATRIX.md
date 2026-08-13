# 10 — Matriz de causas raíz

`SÍNTOMA → EVIDENCIA → MECANISMO → CAUSA INMEDIATA → CAUSA RAÍZ → IMPACTO → MITIGACIÓN → EXPERIMENTO → PRIORIDAD`

## C-1 · Decode lento — `CONFIRMADO`
- **Síntoma:** una respuesta de 300 tokens tarda ~23 s aunque todo vaya bien
- **Evidencia:** decode 88,4 % (doble fuente); 13,04–13,71 tok/s medidos **directamente contra el modelo**, sin pipeline
- **Mecanismo:** decode autoregresivo con batch 1 es memory-bound: cada token exige leer los 16,93 GB de pesos
- **Causa raíz:** L4 con 300 GB/s ⇒ techo 17,7 tok/s; se alcanza el **77 %**
- **Impacto:** suelo físico de toda la latencia
- **Mitigación:** MTP/speculative (1,71× publicado en Qwen3.6 27B) · GPU con más ancho de banda · modelo menor
- **Experimento:** E-7, E-10 · **P2**

## C-2 · Fallo semántico del contrato — `CONFIRMADO`
- **Síntoma:** 60 % de generaciones descartadas; 1/10 pasa a la primera
- **Evidencia:** `payload["format"]` activo ⇒ la forma está garantizada; los detalles son `policy_rule_id_missing`, `PLT:value,PLT:unit`
- **Mecanismo:** la gramática fija la estructura pero no puede validar **qué identificador** va en cada campo
- **Causa raíz:** el contrato exige referencias (ids de política, de hecho, valor+unidad) que el modelo acierta raramente
- **Impacto:** dispara toda la amplificación
- **Mitigación:** reparación dirigida por campo · revisar `policy_rule_id`
- **Experimento:** E-1, E-2 · **P0**

## C-3 · Amplificación de llamadas — `CONFIRMADO`
- **Evidencia:** 133 llamadas / 70 preguntas; 34 turnos con reparación; +182 % de latencia
- **Causa raíz:** consecuencia de C-2 multiplicada por C-1
- **Impacto:** 2,82× frente a un turno válido a la primera
- **Experimento:** E-2 · **P0**

## C-4 · La reparación no repara — `CONFIRMADO` (n=9)
- **Evidencia:** 0/9 correcciones; mismo detalle las 9 veces; temp 0,1 no ayuda; ~23 s cada intento
- **Mecanismo:** el prompt de reparación no comunica el defecto de forma accionable (**contenido `NO_OBSERVABLE`**)
- **Impacto:** 41,6 % del cómputo; 1.875 s (38,1 %) en turnos que no entregaron nada
- **Experimento:** E-1, E-4 · **P0**

## C-5 · El salvage no cubre el caso de un solo claim — `CONFIRMADO`
- **Evidencia:** `_claim_rejection` invocado en `send_chat_message.py:4941`, **activo en producción**; `materialized_fact_count=1` en `SEL-08`
- **Mecanismo:** salva claims supervivientes; si sólo hay uno y falla, no hay nada que salvar
- **Experimento:** instrumentar supervivencia de claims · **P1**

## C-6 · Clasificador de ámbito regex — `CONFIRMADO`
- **Evidencia:** `intent_classifier.py` usa `re` con confianzas fijas (0,96/0,97/0,99); 3 de 5 preguntas de cortesía rechazadas
- **Impacto:** no en latencia; sí en la primera impresión
- **Experimento:** E-5 · **P1**

## Hipótesis descartadas

| Hipótesis | Estado | Evidencia decisiva |
|---|---|---|
| Thinking oculto | `DESCARTADO` | **Experimento directo**: `think=False` → 0 chars de thinking, `eval_count` 400→115 |
| Prefill / caché ausente | `DESCARTADO` | Checkpoints activos; ahorro 24,2 %; techo restante 8,7 % |
| CPU fallback / offload | `DESCARTADO` | `full_gpu` 133/133; `size_vram == size` |
| Cola / concurrencia | `DESCARTADO` | mediana 0 ms, máx 1 ms |
| Arranque en frío | `DESCARTADO` | `load_duration` 554 ms; `expires_at` 2318 |
| Truncación por `num_predict` | `DESCARTADO` | 2 de 138 con `finish_reason=length` |
| La gramática ralentiza | `DESCARTADO` como causa | ratio 0,951 (−5 %) |
| El pipeline añade coste de decode | `DESCARTADO` | 13,05 en pipeline vs 13,04–13,71 directo |
| Constrained decoding pendiente | `DESCARTADO` | ya implementado |
| Salvage pendiente de conectar | `DESCARTADO` | ya conectado y activo |
