# 08 - Capítulo VI - Análisis de resultados (pasada de agosto)

**Corrección sobre esta misma carpeta**: la primera versión de este README (escrita
antes de leer el cuerpo completo del `.md (1)` del P1 ICC) atribuía
`evaluador_1.csv`/`evaluador_2.csv` a la Batería A. Es incorrecto — el Anexo C del
propio documento (Tabla C.1, línea 2534-2535) confirma que son la evaluación
veterinaria de la **Batería E** (30 preguntas, exactitud de contenido). Corregido
abajo con evidencia cruzada.

## Hallazgo principal: los números de la Batería E que cita la tesis están desactualizados

Cap VI 6.4.5 y Cap VII 7.1/7.2 citan, como resultado vigente: **30/30 respuestas
clínicamente seguras, 83.3 % correctas o parcialmente correctas, 0 alucinadas,
κ (exactitud) = 0.841, κ ponderado = 0.904** (Tabla C.7/C.8 del Anexo C). Cruce de
evidencia:

- `revision_tesis_por_capitulo/cambios_2026-07-11/VALIDACION_LLM_2_PENDIENTE.md`
  confirma que esta cifra sale de una corrida **completada el 12/7/2026**, con
  `validacion_llm/resultados/evaluador_1.csv` y `evaluador_2.csv` (filas fechadas
  7-9 de julio) como fuente.
- El pipeline LLM cambió materialmente **después** de esa fecha: los hallazgos de
  la reunión del 20 de julio (`Minuta_analitica_corregida_HemoVet_2026-07-20 (1).md`)
  motivaron cambios en `classifier_outcome`/`classification_status` y en el manejo
  de fechas por estudio (ver `06_capitulo_iv_analisis_diseno/README.md`), y el
  harness técnico se volvió a correr el **2026-08-01**
  (`exactitud_contenido_crudo.csv`, mismo timestamp que el resto de baterías).
- Verificado directamente en el filesystem: `validacion_llm/rubrica_veterinarios/rubrica_contenido_llm_medico1.csv`
  y `_medico2.csv` existen con las 30 preguntas cargadas pero **las columnas de
  juicio (`correctitud`, `cita_apropiada`, `seguridad_clinica`, `comentario`) están
  completamente vacías** — es decir, hay una plantilla nueva generada para una
  segunda ronda de jueces sobre las respuestas post-integración, y esa ronda
  **no se ha completado**.

Conclusión: **la cifra 83.3 %/κ=0.841 no está mal citada — es real — pero corresponde
a respuestas del asistente anteriores a los arreglos de la reunión del 20 de julio
y a la re-corrida del 1 de agosto.** El documento las presenta como resultado
vigente sin esa salvedad. Antes de defender, hay dos caminos: (a) declarar
explícitamente que son resultados pre-integración y motivar por qué siguen siendo
representativos, o (b) completar la segunda ronda con los dos veterinarios sobre
`exactitud_contenido_crudo.csv` (ya generado, solo falta el juicio humano).

## Lo que SÍ está vigente: Batería A (6.4.2)

Los números de Cap VI 6.4.2 (31/40 adversariales rechazados 77.5 %, 15/20
legítimos aceptados 75.0 %, 17/30 fuera de ámbito con mensaje claro 56.7 %)
**coinciden exactamente** con `validacion_llm/resultados/eval_llm_pipeline_real.json`,
regenerado el 2026-08-01 contra el pipeline real post-integración. Esta sección
sí refleja el sistema actual — no requiere corrección.

## Cruce con la minuta del 20 de julio (P0 de la reunión)

Ver detalle completo en `06_capitulo_iv_analisis_diseno/README.md` y
`.../evidencia/verificacion_vms_2026-08-02.md`. Resumen para este capítulo:
`classification_status` con valor explícito `NO_TARGET_PATTERN_DETECTED`
(`backend/app/modules/llm_chat/snapshots.py:182-188`) y tests dedicados a evitar
mezclar valores/fechas entre hemogramas distintos ya existen en
`backend/tests/llm_chat/test_clinical_snapshot_and_claims.py`. Si se quiere citar
la corrección del hallazgo de la minuta como evidencia de resultados, falta un
test end-to-end que reproduzca literalmente las 6 preguntas de la demo — hoy la
corrección está inferida de tests adyacentes, no demostrada directamente contra
esas preguntas exactas.

## Evidencia incluida

- Cruce completo baterías A-E: `../../docs/arquitectura_completa.md`, secciones 7-8.
- Fuente primaria del hallazgo de julio: `../../revision_tesis_por_capitulo/cambios_2026-07-11/VALIDACION_LLM_2_PENDIENTE.md`.
- CSVs crudos (no copiados, referenciar directo): `../../validacion_llm/resultados/`,
  `../../validacion_llm/rubrica_veterinarios/`.
