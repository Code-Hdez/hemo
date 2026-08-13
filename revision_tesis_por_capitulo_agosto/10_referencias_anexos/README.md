# 10 - Referencias y anexos (pasada de agosto)

## Referencias: completas, formato IEEE correcto

69 referencias (líneas 2255-2394), numeradas [1]-[69], todas con formato IEEE
consistente (autor, título, revista, volumen, DOI). Incluye las 3 referencias
nuevas de metodología de validación LLM que julio pedía agregar (Tam et al.
2024, Singhal et al. 2025, Ekram 2026, Corbeil et al. 2025 — red-teaming,
QUEST, Med-PaLM). Sin cambios necesarios detectados.

## Anexos: los 4 están presentes y poblados — pero cambiaron de estructura vs. lo que pedía julio

Julio recomendaba 5 anexos (A. Matriz de riesgos, B. Manual de usuario, C.
Evidencia validación clínica, D. Evidencia trazabilidad modelo, E. Figuras
extendidas). El documento actual tiene **4 anexos con contenido distinto**:

| Anexo actual | Contenido | Corresponde a lo pedido por julio |
| --- | --- | --- |
| A. Matriz de riesgos actualizada | 16 riesgos con P/I/exposición + mitigaciones (Tablas A.1-A.2) | Sí — y más completo: incluye riesgos de RAG/LLM/despliegue que julio pedía agregar |
| B. Evidencia oficial de validación clínica | Inventario de 20 CSV + métricas TP/FP/FN/TN por etiqueta (Tablas B.1-B.6) | Cubre lo que julio pedía para el antiguo "Anexo C" |
| C. Evidencia oficial de validación LLM/RAG | Inventario de 11 archivos + resultados baterías A-E, incluida la rúbrica veterinaria (Tablas C.1-C.8) | Cubre el "Anexo nuevo" que julio sugirió para la validación LLM |
| D. Instrumento y resultados de usabilidad | Estructura del cuestionario + resultados por dimensión e ítem (Tablas D.1-D.3) | No estaba en la lista de julio (la validación de usabilidad es posterior, de julio-agosto) |

**El "Anexo B - Manual de usuario" que julio pedía redactar (registro, carga
de hemograma, chat, historial, vigilancia) no aparece en ningún anexo actual.**
No es un error — es una omisión: parece que el equipo priorizó documentar
evidencia de validación (clínica, LLM, usabilidad) sobre un manual de usuario
paso a paso. Confirmar con la asesora si el manual de usuario sigue siendo
requerido por la plantilla institucional o si se decidió conscientemente
omitirlo.

## Hallazgo heredado: Anexo C hereda la salvedad de la Batería E

Tabla C.7/C.8 (líneas 2589-2600) repite los mismos números de
`08_capitulo_vi_resultados/README.md` (83.3 % correcto/parcial, κ=0.841) con
el mismo matiz pendiente: son de una evaluación veterinaria de julio sobre
respuestas del asistente anteriores a la re-corrida del 1 de agosto.

## Hallazgo curioso: el Anexo A ya anticipa el riesgo que Cap V todavía tiene

Tabla A.1, riesgo **R-06** (línea 2404): *"Contradicción documental de
métricas... Versiones antiguas pueden conservar cifras obsoletas como 50/50 o
38 variables."* — el equipo ya identificó este riesgo explícitamente, pero la
instancia real (Tabla 5.9 de Cap V, "50/50 adversariales") sigue sin
corregirse. Ver `07_capitulo_v_desarrollo/README.md`.

## Evidencia

Líneas 2255-2641 del `.md (1)`. No se copiaron archivos nuevos — los CSV que
respaldan los Anexos B y C viven en `validacion_llm/resultados/` y en las
carpetas de validación clínica ya inventariadas por el propio documento
(Tabla B.3).
