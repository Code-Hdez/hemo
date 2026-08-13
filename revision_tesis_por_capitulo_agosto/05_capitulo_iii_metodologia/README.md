# 05 - Capítulo III - Metodología (pasada de agosto)

## Bien: las dos metodologías nuevas que pedía julio ya están incorporadas

Julio dejó como "borrador listo, falta pegar al documento" la metodología de
validación LLM (3.7) y la de usabilidad (3.8). **Ambas ya están en el `.md (1)`
actual**, con el mismo contenido que los borradores de
`cambios_2026-07-11/`: 3.7 describe las 5 baterías A-E con su dimensión e
indicador (Tabla 3.8, línea 1217-1227), el diseño de dos fases del
red-teaming (3.7.2), y la rúbrica veterinaria con kappa ponderado y PABAK/AC1
de Gwet para la paradoja del kappa (3.7.3). 3.8 describe el instrumento de
usabilidad de 13 ítems, n=44, con la fórmula exacta del índice
`(media-1)×100/4` (línea 1291) — coincide con lo reportado en Cap VI 6.7.
Cifras cruzadas y consistentes: 2,454 IDEXX + 1,301 DAP, PR-AUC macro test
v3 = 0.9577, validación clínica 526 casos / 509 evaluables, 7 etiquetas
oficiales + 2 por regla + 1 excluida — todo coincide con Cap II y Cap VI.

## Gap nuevo: la metodología no describe el reentrenamiento v3→v4

3.5 (línea 1126) dice explícitamente: *"El modelo final fue
xgb_v3_reticulocytes"* y describe el freeze de umbrales solo para v3 (Tablas
3.4 y 3.5). El capítulo se detiene ahí — **nunca describe el reentrenamiento
clínico que produjo v4**.

Sin embargo, Capítulo V (5.2, línea 1558) dice *"la versión final del sistema
se documentó como versión lógica 4.0.0"*, y Capítulo VI (6.1.3, 6.3.3)
documenta con tablas completas que v4 se generó **porque** las discrepancias
observadas en las semanas S1-S3 de validación clínica motivaron un
reentrenamiento, evaluado luego en S4 (14-18 jun 2026). Es decir: v4 es el
modelo que realmente se desplegó y evaluó al final, pero el Capítulo III
(que es justamente donde debería documentarse *cómo* se hizo ese
reentrenamiento — datos usados, si se re-congelaron umbrales, criterio de
promoción v3→v4) no dice nada al respecto.

Esto no es una contradicción de cifras (como el caso 38 vs 43 que ya se
corrigió) sino un **hueco metodológico real**: falta una subsección 3.5.2 o
similar ("Reentrenamiento clínico y promoción a v4") con el mismo nivel de
detalle que 3.5.1 tiene para v3 (freeze de umbrales, trazabilidad de
artefactos, criterio de promoción).

## Evidencia

- Confirmación v3→v4 vía código: `models/best_model_v2.pkl` y afines
  (`backend/app/modules/ml/predictor.py:246-304`) usan sufijo de esquema de
  artefacto `_v2`, que es un versionado distinto del número de iteración de
  modelo (v3/v4) usado en la narrativa de la tesis — no se pudo verificar cuál
  de los dos (v3 o v4) es el artefacto realmente cargado hoy en producción sin
  acceso al `model_metadata_v2.json` desplegado (no versionado en git). Antes
  de escribir la subsección nueva, confirmar contra ese archivo en la VM cuál
  es el modelo activo.
- Texto fuente: `.md (1)` líneas 1120-1163 (3.5/3.5.1), 1811-1945 (Cap VI
  6.1.3/6.3.3).
