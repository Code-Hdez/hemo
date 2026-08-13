# 10 - Referencias y anexos

## Referencias

Revisar que toda referencia este en formato IEEE. Priorizar:

- Articulos revisados por pares.
- Manuales tecnicos oficiales.
- Libros de hematologia veterinaria.
- Documentacion tecnica solo cuando respalde implementacion.

## Anexos recomendados

### Anexo A - Matriz de riesgos

Ya existe en el documento, pero debe actualizarse si se agregan riesgos de produccion, RAG, validacion clinica y despliegue.

### Anexo B - Manual de usuario

Agregar:

- Registro/login.
- Registrar mascota.
- Cargar hemograma.
- Revisar extraccion.
- Leer resultado.
- Usar chat.
- Consultar historial.
- Consultar vigilancia.
- Descargar/copiar resumen para veterinario.

### Anexo C - Evidencia de validacion clinica

Incluir tablas resumidas y referenciar CSV:

- `evidencia/resumen_validacion.json`
- `evidencia/comparacion_larga.csv`
- `evidencia/respuesta_clinica_s2.csv`
- `evidencia/respuesta_medico2_s2.csv`
- `evidencia/respuesta_modelo_s2.csv`
- equivalentes S3/S4.

### Anexo D - Evidencia de trazabilidad del modelo

Incluir:

- `evidencia/artifact_manifest_v3.json`
- `evidencia/final_label_policy.json`
- `evidencia/gate_policy_freeze_v3.json`
- `evidencia/thesis_defense_dossier_v3.json`

### Anexo E - Figuras extendidas

Usar las imagenes copiadas en `imagenes/`.



---

## Estado 11/7/2026 (revisión sobre `.docx (4)`)

> Bloque nuevo del 11/7/2026. Todo lo de arriba es el plan original; esto es el estado verificado hoy.

**Estado:** Referencias presentes (P2004–P2078, formato IEEE) y Anexos presentes (P2079+).
**Pendiente:**
- Anexo B (Manual de usuario): falta redactar (registro, carga de hemograma, chat, historial, vigilancia).
- Anexo A (Matriz de riesgos): actualizar con riesgos de producción/RAG/despliegue.
- Nuevo anexo sugerido: evidencia de la validación del asistente LLM. Dos partes:
  - **Seguridad y alcance (trabajo del compañero, `tools/llm_cbc_eval/`):** tablas por categoría de las dos rondas + evidencia cruda en `results/`.
  - **Baterías formales A–D (`validacion_llm/resultados/`):** CSV con las cifras reales del sistema corridas en la VM (ámbito/seguridad, robustez, memoria, consistencia).
  - **Exactitud de contenido (rúbrica de 2 veterinarios):** **a futuro** — se anexan los datos reales cuando ambos evaluadores completen `rubrica_contenido_llm.csv` (guía en `GUIA_PARA_VETERINARIOS.md`); incluir kappa de Cohen.
- Nueva referencia bibliográfica de respaldo metodológico (QUEST, Med-PaLM, red-teaming, RAG) en `cambios_2026-07-11/capitulo_iii_3.7_metodologia/METODOLOGIA_VALIDACION_LLM_LITERATURA.md`.
