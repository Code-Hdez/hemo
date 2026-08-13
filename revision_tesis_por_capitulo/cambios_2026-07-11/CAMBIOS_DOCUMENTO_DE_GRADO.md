# Cambios a realizar en el documento de grado — 11/7/2026

Lista consolidada de todo lo que hay que **cambiar** o **agregar** al documento,
verificado sobre la versión vigente **`.docx (4)`**. El `.md (1)` es una exportación
más antigua (le falta el Capítulo VII); trabajar sobre el `.docx`.

Los números de párrafo (P###) son la ubicación aproximada en el `.docx` para
encontrar el texto rápido.

---

## 📋 Revisión contra el guía institucional EICT (Rev. Sept. 2025) — 12/7/2026

Verificado sobre el **`.docx (9)`** (versión vigente). Guía: `2.Informe final de proyecto EICT - Rev. Sept. 2025.pdf`.

**✅ Cumple:** Resumen ejecutivo (336 pal., dentro de 250–400) + Abstract inglés (327 pal.);
Introducción con sus 4 sub-secciones; Objetivos (general + específicos); Justificación;
Limitaciones; Cap. I–VII presentes con su estructura; Referencias en **formato IEEE**; anexo de
matriz de riesgos presente; Cap. VII con los 7 sub-ítems.

**❌ Falta (el guía lo pide):**
- **Lista de Tablas / Lista de Figuras / Lista de Anexos** en preliminares (el guía: "si aplica";
  aplican con 53 tablas y 47 figuras). → listo en `preliminares_listas/`.
- **Manual de usuario:** el guía lo EXIGE (pág. 12: "El producto final debe… Contener un manual
  de usuario") y **no está en el documento**. → listo en `anexos/anexo_B_manual_usuario.md`.
- Anexos B/C/D por colocar.

**⚠️ A corregir:**
- **Numeración de tablas/figuras inconsistente.** El guía pide numeración "consecutiva, cada
  categoría de forma independiente". El doc mezcla esquemas: Cap. II usa 1–6 / Fig. 1–3 sin
  prefijo, el resto usa `cap.n` (3.1, 6.15…) y los anexos usan 16/17. Unificar.
- **6.8 "Síntesis crítica" incluye conclusiones.** El guía (pág. 13): en el Cap. VI "no se
  incluyen conclusiones ni sugerencias". La frase "…HemoVet se encuentra listo para demostración
  y uso controlado con limitaciones, siempre que se mantenga la advertencia…" es una conclusión
  (y se repite en 7.1). Reformular 6.8 a solo hallazgos.
- **Fuente tipográfica:** el guía exige Times New Roman, Courier, Courier New o Bookman Old Style;
  interlineado 1.5; tamaños 12/13/14; texto justificado; palabras en otro idioma en cursiva.
  Verificar en Word (el default de los runs es heredado; confirmar que no sea Calibri u otra).
- "50/50" en Cap. V (P524) y "38 vs 43" (P219) — ver abajo.

**Proceso (no es contenido del documento):** el guía (Anexo II) exige **ceder/compartir el código
al repositorio de la Escuela** (github.com/eict-pucmm) y completar el formulario oficial.

---

## 🔴 Bloqueantes (sin esto no se puede entregar)

- [x] **Redactar el Capítulo VII completo (Conclusiones y recomendaciones).**
  ✅ REDACTADO (12/7/2026) en `capitulo_vii_COMPLETO/7_capitulo_vii_COMPLETO.md` (7.1–7.6,
  solo texto + Tabla 7.1 de objetivos). Falta **pegarlo** en el `.docx (7)`, donde el
  Capítulo VII sigue vacío (encabezado en párrafo 702, salta a Referencias).

- [ ] **Reemplazar la sección 6.4 (resultados del LLM).** Las cifras "50 de 50 / 20 de
  20" (P1916 y Tabla 6.9 en P1931) son inválidas: venían de una prueba que no ejercía
  el asistente real. Sustituir por el texto y figuras de
  `cambios_2026-07-11/capitulo_vi_6.4_resultados_llm/6.4_resultados_llm.md`, que ya consolida las seis
  subsecciones (6.4.1–6.4.6), **incluida la exactitud de contenido con los dos veterinarios
  ya COMPLETA** (Tablas 6.11 y 6.12, figuras `cambios_2026-07-11/capitulo_vi_6.4_resultados_llm/6.4.5_*.png`).

- [ ] **Quitar el mismo "50 de 50" del Capítulo V** (P1432). Aparece también aquí, no
  solo en 6.4. Borrarlo o reemplazarlo por una frase que remita a los resultados del
  Capítulo VI.

- [x] **Correr la validación de contenido con los 2 veterinarios** (`validacion_llm/`).
  ✅ HECHO: ambos veterinarios completaron la rúbrica (`evaluador_1.csv`,
  `evaluador_2.csv`); resultados en la subsección **6.4.4** (Tablas 6.10 y 6.11) y en
  `notebooks/validacion/14_validacion_llm_exactitud.ipynb`. Hallazgos: 30/30 seguras,
  83.3 % correctas/parciales, 0 alucinadas, κ = 0.841. Era la prioridad de la asesora.

---

## 🟠 Correcciones de consistencia

- [ ] **Corregir la contradicción de "número de características" en el Capítulo II.**
  El documento dice **43 características** en P322 y P734, pero **38** en P326. El valor
  correcto es **43** (modelo v3 con variables de reticulocitos). Cambiar el "38" de P326
  a 43 y ajustar el desglose (el "20 directos + 18 derivadas = 38" ya no cuadra;
  recalcular el desglose real).

- [ ] **Verificar que el "43" quede uniforme** en todo el documento (Cap. II, Cap. III
  P734, y donde se mencione el feature set).

- [ ] **Revisar el Resumen ejecutivo (P129)** para que no contradiga las cifras finales
  una vez cerrados el Cap. VII y la 6.4.

---

## 🟢 Contenido a agregar

- [ ] **Preliminares:** agregar Lista de tablas, Lista de figuras y Lista de anexos
  después de la tabla de contenido. Renumerar tablas y figuras incluyendo las nuevas
  del LLM (6.4).

- [ ] **Capítulo III (Metodología), sección 3.7:** agregar cómo se evaluó la seguridad
  del asistente (banco de 770 preguntas por categoría de riesgo, endpoint real, dos
  rondas). Hoy solo describe el pipeline, no el método de evaluación.

- [ ] **Anexo B — Manual de usuario:** redactar (registro/login, registrar mascota,
  cargar hemograma, revisar extracción, leer resultado, usar el chat, historial,
  vigilancia, descargar resumen para el veterinario).

- [ ] **Anexo A — Matriz de riesgos:** actualizar con riesgos de producción, RAG,
  validación clínica y despliegue.

- [ ] **Anexo nuevo (evidencia del chat):** tablas por categoría de las dos rondas y
  referencia a la evidencia en `tools/llm_cbc_eval/results/`.

- [ ] **Capítulo VI — agregar sección 6.7 (Validación de usabilidad).** Redacción lista en
  `cambios_2026-07-11/capitulo_vi_6.7_usabilidad/6.7_usabilidad.md` (n=44, índice 84/100, 81.6 % favorable).
  Notebook `notebooks/validacion/16_validacion_usabilidad.ipynb`; figuras `cambios_2026-07-11/capitulo_vi_6.7_usabilidad/6.7_usab_*.png`.
  En 3.x agregar la metodología de la encuesta; en 7.5 las recomendaciones priorizadas.

---

## Estado por capítulo (referencia rápida)

| Capítulo | Estado | Acción |
|---|---|---|
| Preliminares | Casi listo | Agregar listas de tablas/figuras/anexos |
| Introducción / Objetivos / Justif. / Limitaciones | ✅ Alineado | Revisar coherencia final |
| I — Marco teórico | ✅ Alineado | Sin cambios de fondo |
| II — Solución propuesta | ⚠️ Contradicción | Corregir 43 vs 38 características |
| III — Metodología | 📝 Borrador listo | Pegar 3.7/3.8 (`cambios_2026-07-11/capitulo_iii_3.7_metodologia/`) |
| IV — Análisis y diseño | ✅ Alineado | Verificar contratos `/api/v1` |
| V — Desarrollo | ⚠️ Dato inválido | Quitar el "50 de 50" (P1432) |
| VI — Resultados | 📝 Borrador listo | Pegar 6.4 (consolidada) y 6.7 (usabilidad) |
| VII — Conclusiones | 📝 Borrador listo | Pegar `capitulo_vii_COMPLETO/` (docx sigue vacío) |
| Referencias | ✅ Presente | Verificar formato IEEE |
| Anexos | Incompleto | Agregar Manual de usuario y actualizar matriz de riesgos |

---

## Insumos ya generados que apoyan estos cambios

Todos los borradores y sus figuras/outputs están en `cambios_2026-07-11/`, en una subcarpeta
por capítulo/sección (ver `INVENTARIO_FIGURAS.md`). Resumen:

- `capitulo_iii_3.7_metodologia/` — 3.7 (LLM) + 3.8 (usabilidad) + respaldo bibliográfico.
- `capitulo_vi_6.4_resultados_llm/` — 6.4 completa (6.4.1–6.4.6) + 9 figuras. Notebooks 13/14/15.
- `capitulo_vi_6.7_usabilidad/` — 6.7 + 6 figuras + 2 CSV. Notebook 16.
- `capitulo_vii_7.3_limitaciones/` — 7.3 y 7.5 (LLM + usabilidad).
- `capitulo_v_descripcion_ui_ux/` — descripción de UI/UX de la app.

Datos fuente: `validacion_llm/resultados/evaluador_{1,2}.csv`,
`Respuestas - Validación HemoVet.xlsx`. Evidencia cruda del chat: `tools/llm_cbc_eval/results/`.
