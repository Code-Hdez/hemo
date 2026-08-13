# 14 — Informe final integrado · Fase 2

## 1. Executive Summary

HemoVet tarda una mediana de **59,1 s** por pregunta por dos causas que se
**multiplican**: el modelo genera a **13,7 tok/s** —el 77 % del techo físico de
una L4— y el pipeline **le pide que genere 1,9 veces por cada respuesta útil**.
El 88,4 % del tiempo es decode; el backend entero consume el 0,4 %.

La Fase 2 **corrigió tres conclusiones de la Fase 1** con evidencia primaria:
la trazabilidad Git→producción está cerrada, la decodificación restringida ya
está en uso, y el salvage por claim ya está desplegado. Las dos últimas
invalidaban las mitigaciones P0 y P1 propuestas anteriormente.

## 2. Scope

Diagnóstico read-only. Ninguna mitigación aplicada. Sin commits, sin push, sin
cambios de configuración ni de código.

## 3. Methodology

Tres fuentes independientes correlacionadas (cliente SSE, telemetría del backend,
`llama-server`), verificación cruzada de tokens entre ellas, y **experimentos
directos contra el modelo** saltándose el pipeline.

## 4. Sources of Evidence

Ver `08_EXTERNAL_RESEARCH.md`. Jerarquía A (interna) → D (foros), con la regla de
que el nivel D sólo genera hipótesis.

## 5. Production Architecture · 6. Runtime Configuration

Ver `02_PRODUCTION_ARCHITECTURE.md`. **`HEMOVET_BUILD_REVISION` =
`21f18fd8889541dbd947c3692ccbdc0fc6ee0660` = HEAD local ⇒ `CONFIRMADO`.**

## 7. End-to-End Request Lifecycle

Ver `03_REQUEST_LIFECYCLE.md`.

## 8. Dataset

70 preguntas, 133 llamadas correlacionadas (70/70 verificadas por contenido),
más 10 repeticiones controladas y 4 pruebas directas contra Ollama.

## 9-11. Latency / Prefill / Decode

Ver `04_LATENCY_FORENSICS.md`. decode **88,4 %** (doble fuente), prefill 11,3 %,
load 1,5 %.

## 12. GPU Analysis

Ver `06_GPU_MODEL_PERFORMANCE.md`. **300 GB/s ÷ 16,93 GB = 17,7 tok/s de techo;
observado 13,7 = 77 %.** Sin margen de tuning.

## 13. KV/Prefix Cache · 14. Context Growth · 15. 10-Turn Memory

Ver `07_CONTEXT_MEMORY_CACHE.md`. Caché **activo**, ahorra 24,2 % de tokens de
entrada; techo de cualquier mejora de prefill: **8,7 %**. `history_limit=12`
mensajes = **6 pares**, frente a los 10 requeridos.

## 16-21. Amplificación, validadores, repair, `generation_repair_failed`, ×10, salvage

Ver `05_GENERATION_REPAIR_FORENSICS.md`. **1,9 llamadas/pregunta · 60 %
descartado · sólo 7 de 133 rechazos son de seguridad · reparación 0/9 · salvage
activo pero inútil con un solo claim.**

## 22. Clinical Correctness Observability Gap

`NO_OBSERVABLE`, por tres vías comprobadas. Es la incógnita de mayor valor: dado
que la gramática garantiza la forma, lo que se descarta es un sobre **bien
formado** cuyo contenido no podemos juzgar. **E-1** lo cierra.

## 23. Git-to-Production Traceability

**CERRADA.** Ver §5.

## 24-29. External Research

Ver `08_EXTERNAL_RESEARCH.md`.

## 30. Socratic Tutor

Ver `09_SOCRATIC_TUTOR_COMPARISON.md`.

## 31. Root Causes · 32. Rejected Hypotheses

Ver `10_ROOT_CAUSE_MATRIX.md`. Seis causas confirmadas, diez hipótesis
descartadas.

## 33-35. Mitigations, Prioritization, Combined Scenarios

Ver `11_MITIGATION_MATRIX.md`.

| Escenario | Mediana estimada |
|---|---|
| Baseline | 59,1 s |
| A · sin 2.ª llamada inútil | ~43 s |
| B · reparación dirigida por campo | ~35 s |
| C · decode 1,71× (MTP) | ~35 s |
| D · prefill perfecto | ~54 s |
| **E · A+B+C** | **~21 s** |

**Arreglar el pipeline rinde tanto como duplicar el hardware, y son ortogonales.**

## 36. Experimental Plan · 37. Risks · 38. Open Questions

Ver `12_EXPERIMENT_BACKLOG.md` y `13_OPEN_QUESTIONS.md`.

**Riesgo principal declarado:** E-1 exige recrear el contenedor del backend; con
un warmup de 79 s frente a un timeout de 20 s, el chat puede aparecer caído
varios minutos. **No debe ejecutarse sin ventana acordada.**

## 39. Final Conclusions — las 50 preguntas, respondidas

1. **59,1 s** de mediana (p90 128,8; máx 212,3).
2. 99,6 % dentro de Ollama; 0,4 % todo el backend.
3. Prefill **11,3 %**. 4. Decode **87,2-88,4 %**. 5. Reparaciones **41,6 %** del cómputo.
6. **1,9 llamadas/pregunta** (36 turnos con 1, 8 con 2, 23 con 3, 3 con 4).
7-8. ~60 % de lo generado se descarta; por incumplir referencias del contrato.
9. `structured_schema_invalid` (24), `missing_required_clinical_facts` (21), `structured_patient_fact_id_required` (8).
10. **Sólo 7 de 133 (5,3 %)** son seguridad clínica.
11-12. La reparación reincide en el mismo detalle 9 de 9 veces, incluso a temp 0,1. **Por qué exactamente: `NO_OBSERVABLE`** sin E-1.
13-14. **`NO_OBSERVABLE`**. Falta ver el sobre rechazado (E-1).
15-16. GPU 100 % en uso por el modelo, **sin CPU fallback** (133/133 `full_gpu`).
17-18. **Sí, 13,7 tok/s es razonable: es el 77 % del techo de 17,7** que impone el ancho de banda de 300 GB/s.
19-22. **Sí hay caché**: checkpoints de 149,6 MiB; ahorra **24,2 %** de tokens de entrada; lo invalida un cambio de prefijo; los repairs comparten prefijo y se benefician.
23. El contexto **crece lógicamente pero no se reprocesa entero**: ésa fue la confusión inicial de la Fase 1.
24-25. Hoy 12 mensajes (6 pares). Para 10 pares: ventana por presupuesto de tokens anclada a pares, con resumen **no** cada turno.
26-28. `bd70e0d8` añadió `_claim_rejection` (salvage) **y** tool calling. **Está desplegado.** No resuelve el caso de un único claim.
29. Reparación dirigida por campo; salvage (ya está); validación incremental.
30. MTP/speculative; GPU con más ancho de banda; modelo menor.
31. Prefix caching, compresión de RAG, recorte de historial — techo del **8,7 %**.
32. Constrained decoding (ya está), prefix caching (ya está), `NUM_PARALLEL` (cola 0 ms), Flash Attention (ya activo).
33-35. **No por throughput**: HemoVet corre `-np 1` con cola de 0 ms. vLLM/SGLang sólo entrarían por MTP.
36. **Sí, es la técnica mejor respaldada para la causa dominante**: 1,71× publicado en Qwen3.6 27B — pero en RTX 3090, no en L4.
37. Ya implementado.
38. Q4_K_M es equilibrado; bajar degradaría fidelidad numérica.
39-40. Un modelo menor daría ~3×, con revalidación clínica completa.
41. `eval_count` mediana 375; sólo 2 de 138 truncan.
42. El sobre gasta tokens en identificadores — candidato, con riesgo.
43-45. Socratic Tutor: 9 B + modelo pequeño para guardrails + memoria por resumen. Transferible lo primero y lo tercero; **no** la ausencia de validadores.
46-48. Ver `11_MITIGATION_MATRIX.md`.
49. **E-5** (gratis, local), **E-3** (sólo lectura), **E-1** (mayor valor, requiere ventana).
50. Ver `10_ROOT_CAUSE_MATRIX.md`.

## 40. References

Especificación NVIDIA L4 · model card de Qwen3.6 · documentación y API de Ollama
0.32.5 · llama.cpp (flags y checkpoints observados en vivo) · PagedAttention ·
FlashAttention · speculative decoding · benchmarks comunitarios de Qwen3.6 27B
con MTP. Detalle y limitaciones de cada uno en `08_EXTERNAL_RESEARCH.md`.

---

## Cierre

**Por qué HemoVet tarda lo que tarda:** porque genera **dos respuestas completas
a 13,7 tok/s para entregar una** — y en 17 de 70 casos, ninguna. La velocidad es
un límite físico honesto de la L4; la duplicación **no lo es**.

**La conclusión con mayor consecuencia práctica** es la corrección de la Fase 1:
las dos soluciones que parecían pendientes —gramática y salvage— **ya están
puestas**. El problema no es que falte estructura, sino que el contrato exige
referencias semánticas que el modelo acierta 1 de cada 10 veces, y que el
mecanismo previsto para corregirlo tiene una tasa de éxito medida del **0 %**.
