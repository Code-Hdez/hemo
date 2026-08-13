# Anexos — estado frente al `.docx (12)`

**Actualización 12/7/2026.** El docx (12) **ya incorporó los anexos A–D** (con sus tablas), pero
con una organización distinta a la propuesta original de esta carpeta. Estado real:

| Anexo (en el docx 12) | Título | Estado | Corresponde a |
| --- | --- | --- | --- |
| **A** | Matriz de riesgos actualizada (Tablas A.1–A.2) | ✅ en el docx | — |
| **B** | Evidencia de validación clínica (Tablas B.1–B.6) | ✅ en el docx | — (nuevo, lo armó el docx) |
| **C** | Evidencia de validación del asistente LLM/RAG (Tablas C.1–C.8) | ✅ en el docx | `anexo_C_evidencia_validacion_asistente.md` (fuente/base) |
| **D** | Instrumento y resultados de usabilidad (Tablas D.1–D.3) | ✅ en el docx | `anexo_D_instrumento_usabilidad.md` (fuente/base) |

> Es decir: los anexos C y D de este directorio **ya están reflejados** en el docx (que además
> los amplió). Se conservan aquí como fuente/trazabilidad de los datos (`outputs/*.csv`).

## ⚠️ Lo que FALTA y el guía EXIGE: Manual de usuario

El guía EICT (pág. 12) obliga a que **el producto final contenga un manual de usuario**, y **no
está en el docx (12)** (ni en el cuerpo ni en los anexos A–D). Es el único requisito de anexo/
producto que sigue sin cumplirse.

- Borrador listo: **`anexo_B_manual_usuario.md`** (en esta carpeta).
- Dónde colocarlo: como **Anexo E** (o dentro del Capítulo V como "Manual de usuario"). Ya no puede
  ser "Anexo B" porque ese lugar lo ocupa la validación clínica en el docx.

## Outputs (`outputs/`)

Se conservan como respaldo de datos de los anexos C y D:
- `evidencia_chat_por_categoria.csv` — respalda Tabla C.3.
- `usabilidad_por_item.csv`, `usabilidad_por_dimension.csv` — respaldan Tablas D.2 y D.3.
