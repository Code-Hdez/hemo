# 03 - Capitulo I - Marco teorico

## Estado actual

El marco teorico es amplio y util. No falta estructura principal.

## Cambios necesarios

- Actualizar la parte de LLM/RAG para alinearla con el sistema real:
  - RAG con corpus Markdown curado.
  - Recuperacion semantica con embeddings.
  - Validacion de salida.
  - Guardrails deterministas para diagnostico, tratamiento y dosis.
- Reforzar la explicacion de validacion clinica:
  - La interpretacion hematologica tiene variabilidad interobservador.
  - Por eso no basta medir modelo contra etiquetas de maquina; tambien se comparo contra medicos veterinarios.
  - Usar kappa como medida de concordancia.
- Agregar una definicion de Cohen's kappa en glosario si no esta.

## Conceptos que conviene agregar al glosario

- Cohen's kappa.
- Validacion clinica externa.
- Concordancia interevaluador.
- Guardrail deterministico.
- Streaming SSE, si se describe el chat en tiempo real.
- Cookie HttpOnly, si se describe seguridad de sesion.

## Evidencia

La evidencia numerica de validacion clinica esta en `08_capitulo_vi_resultados/evidencia/`.



---

## Estado 11/7/2026 (revisión sobre `.docx (4)`)

> Bloque nuevo del 11/7/2026. Todo lo de arriba es el plan original; esto es el estado verificado hoy.

**Estado:** completo y extenso, alineado con el sistema actual (P190–P316).
**Pendiente menor:** cifras de datos consistentes aquí (2,454 IDEXX + 1,301 DAP, P233). No requiere cambios de fondo.
