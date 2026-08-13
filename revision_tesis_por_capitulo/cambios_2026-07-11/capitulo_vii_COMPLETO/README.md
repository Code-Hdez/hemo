# Capítulo VII — COMPLETO (para pegar en el docx, que está vacío)

Carpeta con el **Capítulo VII entero redactado** desde cero, listo para pegar en el `.docx (7)`,
donde hoy solo existe el encabezado (párrafo 702) y salta directo a Referencias.

## Contenido

- **`7_capitulo_vii_COMPLETO.md`** — el capítulo completo (7.1 a 7.6).

**Es solo texto.** El Capítulo VII de conclusiones no lleva figuras ni outputs propios: los
resultados y las figuras viven en el Capítulo VI y aquí únicamente se referencian con sus cifras.
La única tabla es la **7.1 (cumplimiento de objetivos específicos)**.

## Estructura (alineada con los 7 sub-ítems del guía institucional del Cap. VII)

| Sección | Sub-ítem del guía | Contenido |
| --- | --- | --- |
| 7.1 Conclusiones | Conclusión | Cumplimiento del objetivo general, respaldado por las 3 validaciones (sin repetir resultados) |
| 7.2 Resultados de los objetivos planteados | Resultados de los objetivos planteados | Tabla 7.1 (OE1–OE5 + evidencia + estado) |
| 7.3 Limitaciones | Limitaciones | Sistema/modelo + asistente LLM + usabilidad |
| 7.4 Resultados inesperados o no planificados | Resultados inesperados o no planificados | Discrepancia interevaluador, sobredetección estrés, policitemia conservadora, etc. |
| 7.5 Recomendaciones | Recomendaciones | Validación, producto y vigilancia (hoja de ruta priorizada) |
| 7.6 Puesta en funcionamiento e implementación | Puesta en funcionamiento / implementación | Despliegue en VM `hemovet-prod`, contenedores Docker, estado READY_FOR_PRODUCTION_WITH_LIMITATIONS, flujo verificado |
| 7.7 Sostenibilidad de la plataforma | Sostenibilidad de la plataforma | Docker, PostgreSQL/Alembic, corpus RAG versionado, CI/CD, auditoría de artefactos |

Cubre los **siete** sub-ítems que pide la plantilla institucional para el Capítulo VII.

## Trazabilidad de cifras

- Objetivos: extraídos del `.docx (7)`, párrafos 63–70.
- Modelo: PR-AUC 0.9529 / F1 0.8727 / recall 0.9205; clínica κ 0.629 vs κ interevaluador 0.684 (Cap. VI, 6.1 y 6.3).
- LLM: seguridad 30/30, exactitud 83.3 %, κ 0.841, *prompt injection* 61→1 (Cap. VI, 6.4).
- Usabilidad: n = 44, índice 84/100, 81.6 % favorable (Cap. VI, 6.7).
- Incorpora el material de la carpeta hermana `capitulo_vii_7.3_limitaciones/`.
