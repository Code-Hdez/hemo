# 09 — Comparación con Socratic Tutor

Repositorio `cristiandlahoz/socratic-tutor` clonado en modo lectura fuera del
worktree. Ver también `COMPARATIVA_SOCRATIC_TUTOR_2026-08-08.md` (Fase 1).

| Aspecto | HemoVet | Socratic Tutor | Relevancia | ¿Transferible? |
|---|---|---|---|---|
| Modelo principal | Qwen3.6 **27 B** Q4_K_M | ornith **9 B** Q4_K_XL | **Alta**: 3× menos peso ⇒ ~3× tok/s | **Con revalidación clínica completa** |
| Segundo modelo | ninguno | gemma-4-E4B para **guardrails y clasificación** | **Alta**: HemoVet paga 27 B por decir «soy un asistente» | Sí, con E-8 |
| Motor | Ollama directo | `llama-swap` (multiplexa modelos) | Media | Sólo si se adopta el segundo modelo |
| Memoria | ventana fija de 12 mensajes | **resumen + turnos recientes**, registro de eventos con proyecciones | Alta | Sí, **pero cuidando el context checkpoint** |
| Structured output | sobre JSON con claims/fact_ids/policy_rule_ids, **gramática activa** | no se encontró | Alta | **NO transferible**: es el aporte clínico de HemoVet |
| Validadores | ~18 códigos de rechazo | no se encontraron | Alta | **NO transferible** |
| Repair | hasta 4 llamadas por turno | no se encontró | Alta | **NO transferible tal cual**; sí la idea de no regenerar entero |

## La lectura honesta

Socratic Tutor **no puede sufrir el fallo dominante de HemoVet** porque no tiene
contrato estructurado. Eso no lo hace mejor: lo hace **distinto**. Un tutor
socrático no cita `PLT 290`; HemoVet sí, y debe poder demostrar de dónde salió.

Lo transferible no es «quitar el contrato», sino dos cosas concretas:

1. **No pagar un modelo de 27 B por tareas triviales** (su *side-job model*).
2. **No pagar una inferencia completa por un fallo de forma** — que en HemoVet ya
   se intentó con el salvage por claim, y que la Fase 2 demuestra insuficiente
   cuando sólo hay un claim.
