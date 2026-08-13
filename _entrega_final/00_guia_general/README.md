# 00 · Guía general — Conformidad con el manual EICT

Referencia: *Manual para la realización del Informe final de proyecto*, Escuela de Ingeniería
en Computación y Telecomunicaciones, PUCMM, **Rev. Septiembre 2025**
(`manual_eict/2.Informe final de proyecto EICT - Rev. Sept. 2025 (1).pdf`, 21 páginas).

---

## 1. Estructura exigida vs. estructura actual

| # | Exige el manual (p. 3, «Contenido y Estructura») | En el documento (4) | Estado |
| :---: | :--- | :--- | :---: |
| 1 | Portada / hoja de presentación general (Anexo 1) | Presente | ✅ |
| 2 | Tabla de contenido | Presente, **sin números de página** | ⚠️ |
| 3 | Lista de Tablas | Presente, **sin páginas y desincronizada del cuerpo** | ⚠️ |
| 4 | Lista de Figuras | Presente, **sin páginas** | ⚠️ |
| 5 | Lista de Anexos | Presente (A–D) | ⚠️ falta E |
| 6 | Agradecimientos (opcional, una página por estudiante) | Encabezados presentes, **cuerpo vacío** | 🔴 |
| 7 | Dedicatoria (opcional, una página por estudiante) | Encabezados presentes, **cuerpo vacío** | 🔴 |
| 8 | Resumen ejecutivo en español **y** en inglés | Ambos presentes | ✅ |
| 9 | Desarrollo de los contenidos | Capítulos I–VII presentes | ⚠️ |
| 10 | Anexos | A, B, C, D | ⚠️ falta E |
| — | **Manual de usuario** (exigido textualmente en el Cap. V) | **No existe** | 🔴 |
| — | Código en el servidor de control de versiones de la EICT (Anexo II) | Repo GitHub `xPshycho/hemogramas-proyectoICC` | ⚠️ verificar |

Los capítulos exigidos (Introducción → Cap. I Marco teórico → Cap. II Solución propuesta →
Cap. III Metodología → Cap. IV Análisis y diseño → Cap. V Desarrollo → Cap. VI Análisis de
resultados → Cap. VII Conclusiones → Referencias → Anexos) **están todos presentes y en el
orden correcto**. El problema no es estructural: es de contenido desactualizado y de dos
secciones perdidas dentro del Capítulo VI.

---

## 2. Lo que el manual pide y el documento cumple a medias

### 2.1 «Metodología del componente de tecnología emergente» (p. 10)

El manual dedica una sección entera a esto y pide, textualmente, cuatro cosas para el
componente emergente: **selección del clasificador justificada**, **selección o construcción del
banco de datos justificada**, **justificación del método de entrenamiento** (validación cruzada,
bootstrapping) y **presentación exhaustiva de las métricas de calidad contrastadas con la
literatura**.

- Para el **motor ML**: cumplido en §3.3–§3.5 y §6.1. ✅
- Para el **componente LLM/RAG**: cumplido a medias. §3.7 describe las baterías, pero **no
  describe el diseño experimental de la campaña de agosto**, que es donde el proyecto realmente
  contrasta lo medido contra la literatura (la ablación de gramática refuta un valor publicado
  por un factor de ~44×). Ese contraste es exactamente lo que el manual pide y hoy no está.
  → acción **N3** (§3.11 nueva), detallada en `../05_capitulo_iii_metodologia/README.md`.

### 2.2 «Capítulo VI — Análisis de los resultados» (p. 13)

> «en este apartado **no se incluyen conclusiones ni sugerencias**… se limita a describir los
> hallazgos… mediante tablas, cuadros, gráficas, dibujos, diagramas, mapas y figuras».

- El Capítulo VI actual respeta esta separación razonablemente. ✅
- Pero §6.4.2 incluye una frase de gestión («hallazgo que se entrega al equipo de desarrollo»)
  que pertenece al Capítulo VII. Menor, pero es el tipo de detalle que un comité marca.
- La regla favorece la incorporación de §6.9: la campaña produce **36 figuras y 37 tablas ya
  generadas**, que es literalmente el formato que el manual prefiere.

### 2.3 «Capítulo VII — Conclusiones y recomendaciones» (p. 13)

El manual enumera siete sub-ítems: Conclusión · Resultados de los objetivos planteados ·
Limitaciones · Resultados inesperados o no planificados · Recomendaciones · Puesta en
funcionamiento · Sostenibilidad. **El documento tiene los siete, en ese orden.** ✅
El trabajo pendiente aquí es de contenido, no de estructura.

### 2.4 «Capítulo V — Desarrollo» (p. 12)

El manual lista lo que debe tener el producto final: estéticamente aceptable · rotulado ·
**contener un manual de usuario** · información útil y legible · cerrar los procesos operativos ·
adecuada calibración · **diseñar un caso de prueba, probar, medir y poner los resultados**.

- Caso de prueba diseñado, probado y medido: ✅ (§2.6.2, §5.7, demostración E2E de 4 casos).
- **Manual de usuario: ausente.** Es un requisito explícito. → acción **N7**.

---

## 3. Checklist de formato (pendiente de aplicar sobre el `.docx`)

Ver `CHECKLIST_FORMATO.md`. Resumen de lo que el manual fija (p. 3) y hay que verificar antes de
imprimir:

- Tipografía Courier / Courier New / Times New Roman / Bookman Old Style.
- Interlineado 1,5. Cuerpo 12 pt, subtítulos 13 pt, títulos 14 pt. Texto justificado.
- Márgenes: superior 2,54 cm · inferior 3,17 cm · izquierdo 3,81 cm · derecho 2,54 cm.
- Paginación arábiga inferior derecha; romanos en presentación, portadillas, dedicatorias y
  agradecimientos.
- **Citación IEEE.** Palabras en otro idioma en cursiva.
- Tablas, imágenes y fórmulas numeradas **por categoría independiente** y listadas cada una en
  su índice.
- Solo **cuatro niveles de título**: nivel 1 en mayúsculas y centrado; nivel 2 alineado a la
  izquierda con mayúscula inicial en palabras principales; nivel 3 alineado a la izquierda con
  mayúscula solo en la primera palabra.
- Entrega física: negro sobre bond 20 blanco, **empastado azul marino con letras doradas**,
  lomo con título y año.

> ⚠️ **Tensión detectada en el propio manual.** En «Referencias bibliográficas» (p. 14) pide
> que estén «ordenadas alfabéticamente», pero también exige **formato IEEE**, que numera por
> orden de aparición. El documento usa IEEE numérico, que es lo consistente con la exigencia de
> formato y con el uso de `[n]` en el cuerpo. **Recomendación: mantener IEEE numérico** y, si el
> asesor lo pide, añadir un índice alfabético de autores como apéndice. No reordenar
> alfabéticamente una lista numérica: rompería todas las citas del cuerpo.

---

## 4. Estado del sistema real (contra el que se contrasta el documento)

Verificado el 12 de agosto de 2026 sobre la rama `main`, commit `f9deedb`.

| Componente | Estado real | ¿Lo dice el documento? |
| :--- | :--- | :---: |
| API versionada `/api/v1` + `/health*` | 12 módulos, **40 rutas** declaradas | ✅ |
| Backend FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic | **15 migraciones** | ✅ |
| Frontend | **`frontend_4/` es la única implementación activa** (95 ficheros versionados); `frontend/` ya no está en control de versiones | ✅ |
| Modelo ML | XGBoost multilabel v4, 7 etiquetas oficiales + 2 por regla + 1 excluida | ✅ |
| Corpus RAG | **1 252 documentos Markdown** en `knowledge_base/`, ingesta offline | ⚠️ sin cifra en el doc |
| Runtime LLM | **`qwen3.6:27b-q4_K_M` sobre A100-SXM4-40GB spot** | 🔴 dice Qwen3 4B sobre CPU |
| Cadena de release | Contratos `hemovet.release/v1` y `hemovet.gpu-startup/v1`, manifiestos firmados, rollback validado, fail-closed | 🔴 ausente |
| Pruebas backend | **35 archivos** de test | 🔴 dice «25 passed» |
| Campaña de recaracterización | 36 figuras + 9 paneles de ausencia + 37 tablas, 10 hipótesis pre-registradas | 🔴 ausente |

---

## 5. Documentos de esta guía

| Documento | Para qué |
| :--- | :--- |
| [`COMO_PRESENTAR_LA_EVIDENCIA.md`](COMO_PRESENTAR_LA_EVIDENCIA.md) | **Qué formato va al documento y cuál no.** Un JSON no es material de tesis: se convierte a tabla numerada. Incluye las convenciones de tablas, figuras, compendios y números |
| [`CATALOGO_DE_FIGURAS_E_IMAGENES.md`](CATALOGO_DE_FIGURAS_E_IMAGENES.md) | **Las 47 figuras que hay y las que faltan.** Ninguna muestra el producto funcionando: catálogo de 11 capturas a producir, con especificaciones |
| [`CHECKLIST_FORMATO.md`](CHECKLIST_FORMATO.md) | Tipografía, márgenes, paginación, IEEE, empastado |
| [`MATRIZ_HALLAZGOS.csv`](MATRIZ_HALLAZGOS.csv) | Los 61 hallazgos con id, severidad, acción y evidencia |

## 6. Cómo usar esta carpeta

1. Abrir `MATRIZ_HALLAZGOS.csv` y filtrar por `severidad = P0`.
2. Ir al `README.md` del capítulo correspondiente: cada hallazgo tiene un **identificador de
   acción** (`A-VI-03`, `A-V-01`, …), la **localización exacta** en el documento, el **texto
   actual**, el **texto de reemplazo** y el **artefacto** que lo respalda.
3. Aplicar sobre el `.docx (4)`, que es la versión vigente.
4. Marcar la acción como aplicada en la matriz.
5. Al terminar, ejecutar el cierre de `../01_preliminares/README.md` (TOC, listas, paginación).
