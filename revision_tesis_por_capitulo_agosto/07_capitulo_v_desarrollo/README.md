# 07 - Capítulo V - Desarrollo del proyecto (pasada de agosto)

## Bien: este capítulo ya reconcilia v3→v4, mejor que Cap II y Cap III

5.2 (línea 1558) dice explícitamente: *"La versión final del sistema se
documentó como versión lógica 4.0.0... Algunos artefactos de tiempo de
ejecución dejaron nombres de versiones antiguas, como best_model_v2.pkl o
decision_thresholds_v2.json, pero el estado final del sistema incluye
explícitamente la política de umbrales, la versión lógica y las
restricciones de implementación."* Esto es exactamente la aclaración que
falta en Capítulo II y III (ver esos README) — Cap V ya lo hace bien y puede
usarse como referencia de redacción para completar los otros dos.

La tabla de módulos backend (5.3, línea 1619-1634) coincide con los 12
módulos reales verificados en `backend/app/modules/` (auth, users, pets,
pet_history, hematology, ml, population_surveillance, maps, llm_chat,
gemini_extraction, files, dashboard).

## Único punto pendiente: la cifra de guardrails 50/50 sigue sin corregirse

Julio ya marcó esto como "A CORREGIR" el 11/7 y **sigue exactamente igual**
en el documento actual. Tabla 5.9 (línea 1726): *"Guardrails LLM/RAG | 50/50
adversariales rechazados; 20/20 legítimos aceptados"*.

Esta cifra viene de `outputs/llm_guardrails_eval.json`
(`scripts/llm_guardrails_eval.py`), que mide `context.detect_intent` — código
huérfano nunca conectado a la ruta de producción real. El propio
`validacion_llm/scripts/correr_eval_pipeline_real.py` lo dice en su
docstring: *"Reemplaza la evidencia previa outputs/llm_guardrails_eval.json...
código no conectado a la ruta de producción"*.

Los números reales, ya calculados y citados correctamente en **Capítulo VI**
(6.4.2, sección "Ámbito y seguridad batería A"): **31/40 adversariales
rechazados (77.5 %), 15/20 legítimos aceptados (75.0 %)** — verificados por
esta sesión contra `validacion_llm/resultados/eval_llm_pipeline_real.json`
(regenerado 2026-08-01). Cap V solo necesita reemplazar la fila de la Tabla
5.9 por estos números o por una remisión a 6.4.2, tal como julio recomendó.

## Evidencia

- `validacion_llm/scripts/correr_eval_pipeline_real.py` (docstring, líneas 1-8).
- `validacion_llm/resultados/eval_llm_pipeline_real.json` (regenerado 2026-08-01).
- Cruce completo en `../../docs/arquitectura_completa.md`, sección 8.
