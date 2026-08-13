# 12 — Backlog experimental

| ID | Hipótesis | Var. independiente | Var. dependiente | N | Criterio de éxito | Riesgo | P |
|---|---|---|---|---:|---|---|---|
| **E-1** | La generación descartada era clínicamente correcta | `CHAT_STRUCTURED_DEBUG_DIR` activo | contenido del sobre rechazado | 10 | Poder clasificar cada rechazo como TRUE/FALSE positive | **Escribe texto de paciente en disco. Recrear el contenedor puede dejar el chat caído minutos (warmup 79 s vs timeout 20 s)** | **P0** |
| **E-2** | La reparación dirigida por campo evita la 2.ª inferencia | prototipo fuera de producción | llamadas/pregunta, latencia | 70 | <1,3 llamadas/pregunta sin perder validaciones | Bajo (banco de pruebas) | P0 |
| **E-3** | La GPU sube en generación y baja en validación | muestreo `nvidia-smi -l 1` | utilización vs fase | 10 | Patrón visible correlacionado por timestamp | **Ninguno: sólo lectura** | P1 |
| **E-4** | La tasa 0/9 de reparación se mantiene | repetir `SEL-08` | éxito de la reparación | 50 | IC 95 % de la tasa | Bajo: tráfico normal | P1 |
| **E-5** | Una regla regex concreta causa el rechazo de ámbito | ejecutar `intent_classifier.py` local | patrón que casa | 5 | Identificar la regla | **Ninguno: local, sin producción** | P1 |
| **E-6** | `seed` fijo elimina la variabilidad | `seed` fijo vs libre | veredicto del validador | 2×25 | Si con seed es determinista, la causa es muestreo | Bajo | P1 |
| **E-7** | MTP da 1,71× en L4 | motor con MTP, banco de pruebas | tok/s, acceptance rate | — | >1,3× con aceptación >50 % | Medio: motor distinto | P2 |
| **E-8** | Un modelo pequeño mantiene la seguridad | modelo 3-8 B | 22 preguntas de identidad/ámbito/seguridad | 22 | **4/4 en seguridad o se descarta** | Medio | P2 |
| **E-9** | El resumen periódico invalida el checkpoint | historial largo | tasa de acierto de checkpoint | 15 turnos | Medir prefill por turno | Bajo | P2 |
| **E-10** | `llama-bench` confirma el techo de 17,7 tok/s | benchmark directo | tok/s | 3 | Coherencia con 13,7 medido | Ocupa la GPU; requiere ventana | P2 |

## E-1 en detalle, por ser el de mayor valor y mayor riesgo

**No debe ejecutarse sin ventana acordada.** Requiere recrear el contenedor
(`docker restart` no recarga el entorno), y el informe del 6-ago documenta que la
carga en frío tarda 79 s frente a un `OLLAMA_WARMUP_TIMEOUT_SECONDS` de 20 s: el
chat quedaría marcado como caído varios minutos.

Procedimiento propuesto: ventana fuera de horario → activar → lanzar **sólo** los
10 casos `REP-PLT` → desactivar → recoger ficheros → restaurar. Rollback:
devolver el `.env` a su copia previa y recrear.
