# Análisis de duplicación: Anexos B/C/D vs. Capítulo VI

> **12/7/2026, sobre el `.docx (12)`.** El guía EICT pide que las tablas "enriquezcan el texto en
> lugar de duplicarlo". Los Anexos B, C y D respaldan sus secciones del Cap. VI (6.3, 6.4, 6.7),
> pero varias de sus tablas **repiten** las que ya están en el cuerpo. Aquí está qué duplica, qué
> es único y qué recortar.
>
> Criterio: **DUPLICA** = misma información que una tabla del Cap. VI → quitar del anexo y dejar un
> "(ver Tabla 6.X)". **ÚNICO** = trazabilidad/inventario que no está en el cuerpo → mantener.
> **AMPLÍA** = versión más granular (por caso/ítem) de algo resumido en el cuerpo → mantener, es
> el valor legítimo de un anexo.

## Anexo B — Validación clínica (respalda 6.3)

| Tabla anexo | Contenido | Equivalente en cuerpo | Veredicto | Acción |
|---|---|---|---|---|
| B.1 | Resumen general de la validación clínica | **Tabla 6.7** (Resumen global) | 🔴 DUPLICA | Quitar → "(ver Tabla 6.7)" |
| B.2 | Desglose semanal | **Tabla 6.6** (Distribución semanal) | 🔴 DUPLICA | Quitar → "(ver Tabla 6.6)" |
| B.3 | Inventario de CSV oficiales | — | 🟢 ÚNICO | Mantener (trazabilidad) |
| B.4 | Positivos y acuerdos M1/M2/modelo | — (el cuerpo solo da κ macro) | 🟡 AMPLÍA | Mantener |
| B.5 | Métricas del modelo vs. Médico 1 | **Tabla 6.8** (Modelo vs. Médico 1) | 🔴 DUPLICA | Quitar → "(ver Tabla 6.8)" |
| B.6 | Resumen de manifiestos de trazabilidad | — | 🟢 ÚNICO | Mantener (trazabilidad) |

**Anexo B: 3 de 6 tablas duplican el cuerpo (B.1, B.2, B.5).**

## Anexo C — Asistente LLM/RAG (respalda 6.4)

| Tabla anexo | Contenido | Equivalente en cuerpo | Veredicto | Acción |
|---|---|---|---|---|
| C.1 | Inventario de archivos oficiales | — | 🟢 ÚNICO | Mantener (trazabilidad) |
| C.2 | Resumen del comportamiento sobre el pipeline | **Tabla 6.10** (Ámbito y seguridad) | 🔴 DUPLICA | Quitar → "(ver Tabla 6.10)" |
| C.3 | Fallos por categoría, red-teaming 2 rondas | Tabla 6.9 (solo los 4 límites) | 🟡 AMPLÍA | Mantener (detalle por categoría) |
| C.4 | Batería A por categoría y tipo de mensaje | Tabla 6.10 (resumen) | 🟡 AMPLÍA | Mantener (granular) |
| C.5 | Síntesis de baterías A–E | Secciones 6.4.2–6.4.5 | 🔴 DUPLICA | Quitar o condensar a 1 fila remitiendo a 6.4 |
| C.6 | Consistencia de fuentes por caso | 6.4.4 (solo Jaccard medio 0.84) | 🟡 AMPLÍA | Mantener (por caso) |
| C.7 | Resumen de la evaluación veterinaria | **Tabla 6.11** (Exactitud por 2 vets) | 🔴 DUPLICA | Quitar → "(ver Tabla 6.11)" |
| C.8 | Concordancia interevaluador | **Tabla 6.12** (Concordancia) | 🔴 DUPLICA | Quitar → "(ver Tabla 6.12)" |

**Anexo C: 4 de 8 tablas duplican el cuerpo (C.2, C.5, C.7, C.8).**

## Anexo D — Usabilidad (respalda 6.7)

| Tabla anexo | Contenido | Equivalente en cuerpo | Veredicto | Acción |
|---|---|---|---|---|
| D.1 | Estructura del instrumento (cuestionario) | — | 🟢 ÚNICO | Mantener (el instrumento) |
| D.2 | Resultados por dimensión | **Tabla 6.15** (Usabilidad por dimensión) | 🔴 DUPLICA | Quitar → "(ver Tabla 6.15)" |
| D.3 | Resultados por ítem Likert | Figura 6.25 (media por ítem) | 🟡 AMPLÍA | Mantener (tabla por ítem, la figura no da los números exactos) |

**Anexo D: 1 de 3 tablas duplica el cuerpo (D.2).**

## Resumen y recomendación

- **8 tablas de los anexos duplican tablas del Cap. VI**: B.1, B.2, B.5, C.2, C.5, C.7, C.8, D.2.
- **Recomendación:** quitarlas de los anexos y dejar en su lugar una línea "(ver Tabla 6.X en la
  sección correspondiente)". Con eso los anexos quedan como lo que deben ser —**trazabilidad,
  inventarios y datos granulares por caso/ítem**— sin repetir los resultados ya presentados.
- **Se mantienen 11 tablas** (las 🟢 ÚNICO y 🟡 AMPLÍA), que sí aportan valor de anexo.
- **Efecto:** reduce ~8 tablas y varias páginas, y elimina el reparo del guía sobre duplicación,
  sin perder ninguna evidencia (los datos crudos siguen en `validacion_*/resultados/` y en los
  outputs de `anexos/outputs/`).

### Alternativa mínima (si no se quiere tocar la estructura de anexos)
Dejar los anexos como están, pero **añadir al inicio de cada anexo una nota**: "Las tablas de
resumen de este anexo reproducen, para consulta consolidada, las tablas 6.6–6.15 del Capítulo VI;
las tablas de inventario y detalle por caso son evidencia adicional." Esto no acorta, pero
justifica explícitamente la repetición ante el evaluador.
