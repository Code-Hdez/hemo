# 09 - Capitulo VII - Conclusiones y recomendaciones

## Este capitulo falta

Debe agregarse completo antes de referencias.

## Estructura recomendada

### 7.1 Conclusiones

Debe responder si se cumplio el objetivo general:

- Se construyo una plataforma web para interpretacion orientativa de hemogramas caninos.
- Integra extraccion, clasificacion multilabel, reglas de calidad, visualizacion, historial, vigilancia y chat controlado.
- No sustituye al veterinario.

### 7.2 Cumplimiento de objetivos especificos

Crear una tabla:

| Objetivo | Evidencia | Estado |
| --- | --- | --- |
| Dataset clinico estructurado | IDEXX + DAP, artefactos de datos | Cumplido |
| Modelo multilabel | PR-AUC macro, politica de etiquetas | Cumplido con limitaciones |
| Portal ciudadano | Frontend, historial, chat, biblioteca | Cumplido |
| Vigilancia comunitaria | Reporte y mapas agregados | Cumplido como exploratorio |
| Capa conversacional | RAG + guardrails | Cumplido |

### 7.3 Limitaciones

Incluir:

- Solo caninos.
- Dependencia de formato y calidad de hemogramas.
- Validacion clinica con dos evaluadores, pero aun limitada territorialmente.
- DAP no tiene etiquetas compatibles.
- Algunas etiquetas tienen bajo soporte o mayor ambiguedad clinica.
- Vigilancia poblacional no equivale a prevalencia epidemiologica.
- LLM no diagnostica ni recomienda tratamientos.

### 7.4 Resultados inesperados

- La validacion clinica mostro que la discrepancia entre medicos es relevante.
- Leucograma de estres tuvo tendencia a sobredeteccion.
- Policitemia tuvo alta especificidad pero sensibilidad menor.
- Agregados plaquetarios funciono mejor como regla deterministica que como modelo.

### 7.5 Recomendaciones

- Ampliar validacion con mas clinicas y mas evaluadores.
- Recalibrar etiquetas con mayor desacuerdo clinico.
- Mejorar extraccion de reticulocitos y morfologia.
- Separar modo ciudadano y modo veterinario.
- Mantener auditoria de artefactos, hashes y versionado.
- Convertir vigilancia poblacional en modulo epidemiologico solo con protocolos formales.

### 7.6 Sostenibilidad

- Despliegue Docker.
- PostgreSQL/Alembic.
- Corpus RAG versionado.
- CI/CD.
- Backups de modelos y datos anonimizados.



---

## Estado 11/7/2026 (revisión sobre `.docx (4)`)

> Bloque nuevo del 11/7/2026. Todo lo de arriba es el plan original; esto es el estado verificado hoy.

**BLOQUEANTE — CAPÍTULO VACÍO.** En el `.docx (4)` el encabezado "7. Capítulo VII" (P1994) va directo a Referencias (P2004); los párrafos P1995–P2003 están vacíos. **Redactar completo** con la estructura de este README (7.1–7.6). Es el mayor faltante del documento.
**Insumos listos para redactar:** tabla de objetivos (7.2) con evidencia ya disponible; limitaciones (7.3) incluyendo la del alcance del chat y los 14 FAIL de política; resultados inesperados (7.4) con la discrepancia interevaluador y el hallazgo de seguridad del LLM antes/después (evaluación del compañero, `tools/llm_cbc_eval/`).

**Limitaciones y trabajo futuro del LLM (borrador listo `cambios_2026-07-11/capitulo_vii_7.3_limitaciones/7.3_limitaciones.md`):**
- La validación de **exactitud de contenido con los dos veterinarios** (rúbrica de 30 preguntas) es de carácter piloto; **sus datos reales se incorporan a futuro cuando ambos evaluadores completen la rúbrica** — declararlo explícitamente como trabajo pendiente.
- Declarar como limitación el número de evaluadores (2, frente a 4–7 recomendados por la literatura QUEST) y el tamaño de muestra (n=30 vs. ≥100); recomendar ampliarlos.
- Incluir la evaluación de seguridad/alcance del compañero como evidencia complementaria ya disponible.

**Usabilidad — insumos para 7.2, 7.3, 7.4 y 7.5 (nuevo, 12/7/2026; ver Cap. VI 6.7):**
- **7.2 Objetivos:** la encuesta de usabilidad (n = 44, índice 84/100, 81.6 % favorable) es evidencia de cumplimiento del objetivo de comprensibilidad/experiencia para usuarios legos (77 % nunca vio un hemograma).
- **7.3 Limitaciones:** declarar que es **usabilidad percibida** con muestra de conveniencia (n = 44) e instrumento propio (no SUS estandarizado, sin medición cronometrada de tareas ni tasa de error observada).
- **7.4 Resultados inesperados:** los usuarios pidieron funciones que confirman decisiones o limitaciones del sistema (velocidad/memoria del chat = latencia en CPU ya documentada; dudas sobre si las fuentes del chat son reales, que la validación veterinaria confirmó reales).
- **7.5 Recomendaciones (hoja de ruta priorizada por menciones):** acelerar y dar memoria al chat; leyenda de colores fija y rangos normales junto a los valores; compartir por WhatsApp/correo; modo de alto contraste y menos texto (accesibilidad); **arreglar el tour de bienvenida (no arrancaba)** y añadir un mini-tutorial; aclarar el propósito del mapa/zona y la diferencia de contexto del chat; glosario para unidades (µL, fL) y jerga (in vitro/in vivo).
