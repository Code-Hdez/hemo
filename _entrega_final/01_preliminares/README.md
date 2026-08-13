# 01 · Preliminares — portada, índices, resumen y abstract

> **Trabajar este bloque AL FINAL.** Todo lo que hay aquí depende de las secciones que aún se van
> a insertar (§6.6, §6.9, §3.11, §5.9, §5.10, §1.1.3.7, Anexo E). Regenerarlo antes de aplicar
> esos cambios es trabajo que hay que repetir.

Acciones: `A-PRE-01` … `A-PRE-08` en `../00_guia_general/MATRIZ_HALLAZGOS.csv`.

---

## A-PRE-05 · 🔴 Agradecimientos y dedicatorias vacíos

Los cuatro encabezados existen (`Agradecimientos – Carlos David Hernández Collado`,
`Agradecimientos – Edwin Andrés Balbuena Bisonó`, y las dos dedicatorias) **con el cuerpo
completamente vacío**. Es lo primero que ve el comité al abrir el empastado.

El manual los marca como opcionales, pero **si el encabezado está, el cuerpo tiene que estar**.
Una página por estudiante, paginada en romanos.

---

## A-PRE-02 · 🔴 La Lista de Tablas no cuadra con el cuerpo

| Lista de Tablas dice | El cuerpo tiene | Problema |
| :--- | :--- | :--- |
| Tabla 6.13 — Rendimiento de inferencia y pruebas backend | Tabla 6.13 ✅ | ok |
| **Tabla 6.14 — Señales del reporte de vigilancia poblacional** | **no existe** | la sección 6.6 desapareció |
| Tabla 6.15 — Usabilidad percibida por dimensión, n = 44 | numerada como **Tabla 6.14** | desfase de uno |

Al insertar §6.6 y §6.9 la serie completa se reordena. **Numeración final propuesta del
Capítulo VI:**

| Nº | Título | Origen |
| :--- | :--- | :--- |
| 6.1 – 6.8 | (sin cambios) | actuales |
| 6.9 | Veces que el asistente cruzó cada límite de seguridad | actual 6.9 |
| 6.10 | Resultados de ámbito y seguridad sobre el *pipeline* real | actual 6.10 |
| 6.11 | Evaluación de exactitud clínica por dos veterinarios | actual 6.11 |
| 6.12 | Concordancia interevaluador de la rúbrica de exactitud | actual 6.12 |
| 6.13 | Resultados de rendimiento de inferencia y pruebas backend | actual 6.13 |
| **6.14** | **Señales del reporte de vigilancia poblacional** | **§6.6 reinsertada** |
| **6.15** | Usabilidad percibida por dimensión, n = 44 | actual 6.14 → renumerar |
| **6.16** | Identidad sellada del runtime conversacional medido | **§6.9 nueva** |
| **6.17** | Caracterización física del decodificado sobre A100 | **§6.9 nueva** |
| **6.18** | Réplica estricta pareada L4 → A100 | **§6.9 nueva** |
| **6.19** | Turnos sin respuesta por corrida, con IC de Wilson | **§6.9 nueva** |
| **6.20** | Tablero de las diez hipótesis pre-registradas | **§6.9 nueva** |

Y en el Capítulo V, si se aceptan §5.9 y §5.10: **Tabla 5.10** (contratos y artefactos de
release) y **Tabla 5.11** (cambios de las rondas 4-6 del asistente).

---

## A-PRE-03 · Lista de Figuras — entradas nuevas

Añadir, tras la actual Figura 6.29:

| Nº | Título | Fichero fuente (vectorial) |
| :--- | :--- | :--- |
| Figura 6.30 | Composición del corpus de evidencia previa auditado | `fig_A2_corpus_evidencia.pdf` |
| Figura 6.31 | Reconstrucción del protocolo del 7 de agosto: semáforo de las quince preguntas | `fig_A4_semaforo_protocolo.pdf` |
| Figura 6.32 | Verificación de identidad de modelo en cada respuesta | `fig_B3_identidad_por_respuesta.pdf` |
| Figura 6.33 | Techos de decodificación y rendimiento medido | `fig_C1_techos_decode.pdf` |
| Figura 6.34 | Distribución del tiempo por token de salida (TPOT) | `fig_C2_tpot_distribucion.pdf` |
| Figura 6.35 | Lo predicho frente a lo medido: la sobrecarga de gramática | `fig_C6_gramatica_predicho_medido.pdf` |
| Figura 6.36 | Latencia por caso: L4 → A100 | `fig_E1_slopegraph_pareado.pdf` |
| Figura 6.37 | Distribución de las diferencias pareadas | `fig_E2_diferencias_pareadas.pdf` |
| Figura 6.38 | Naturaleza de los fallos: dos fenómenos distintos | `fig_E5_clases_fallo.pdf` |
| Figura 6.39 | Tasa de alucinación numérica y su intervalo de confianza | `fig_D7_alucinacion_wilson.pdf` |
| Figura 6.40 | Tablero de las diez hipótesis pre-registradas | `fig_F1_tablero_hipotesis.pdf` |
| Figura 6.41 | Potencia del diseño | `fig_F4_potencia.pdf` |

Todas están en `06_analisis/figuras/` en PDF, SVG y PNG, con SHA-256 en `MANIFIESTO.json`, y con
su versión en escala de grises en `06_analisis/grises/` para verificar el empastado.
Las copias listas para insertar están en
`../08_capitulo_vi_resultados/6.9_recaracterizacion_a100/figuras/`.

---

## A-PRE-04 · Lista de Anexos

Añadir la quinta fila:

| Anexo | Título | Contenido principal |
| :--- | :--- | :--- |
| Anexo E | Evidencia de la campaña de recaracterización del runtime conversacional | Pre-registro firmado con su hash, tablero de hipótesis, procedencia SHA-256 de cada artefacto, manifiesto de las 36 figuras y 37 tablas, y las aserciones de verificación con la que falla declarada. |

---

## A-PRE-06 / A-PRE-07 · 🔴 Resumen ejecutivo y Abstract

El resumen actual describe el módulo conversacional en una sola frase genérica: *«El módulo
conversacional se evaluó en el flujo de trabajo real utilizando baterías de pruebas de
seguridad, robustez, memoria, coherencia de las fuentes y revisión veterinaria.»* No da una sola
cifra, y omite el resultado con mayor peso metodológico del proyecto.

El manual sugiere entre 250 y 400 palabras y pide que incluya «los resultados más importantes».
**Extensión medida:** el resumen tiene **354 palabras** y el *abstract* **313**. La sustitución
propuesta alarga el resumen unas 90 palabras, con lo que quedaría en ~445 y **se pasaría del
máximo**. Para no desbordar, recortar en compensación el párrafo 4 (validación externa y clínica),
que hoy repite cifras que el párrafo 3 ya introduce. Volver a contar tras el cambio.

### Sustituir el párrafo 5 del Resumen ejecutivo

> **Texto actual:**
> «El módulo conversacional se evaluó en el flujo de trabajo real utilizando baterías de pruebas
> de seguridad, robustez, memoria, coherencia de las fuentes y revisión veterinaria. En general,
> HemoVet demuestra la viabilidad técnica de combinar la clasificación hematológica
> automatizada, la explicación controlada y la visualización responsable para los ciudadanos.»

> **Texto propuesto:**
> «El módulo conversacional se evaluó sobre el flujo de trabajo real mediante baterías de
> seguridad, robustez ortográfica, memoria multiturno, coherencia de fuentes y una rúbrica
> veterinaria ciega; las treinta respuestas evaluadas fueron consideradas clínicamente seguras
> por ambos evaluadores y no se detectaron alucinaciones en la muestra. En agosto de 2026 el
> runtime conversacional se migró a una unidad de procesamiento gráfico NVIDIA A100, y el cambio
> se caracterizó mediante una campaña de medición con diez hipótesis registradas antes de medir:
> la latencia mediana por turno se redujo un 60,6 % (de 54,4 s a 21,4 s; prueba de Wilcoxon
> pareada por caso, n = 64) y la proporción de turnos sin respuesta bajó de 24,3 % a 8,6 %
> (McNemar exacto, p = 0,035), si bien el análisis de identificadores de fallo muestra que
> ambos conjuntos de fallos corresponden a fenómenos distintos y no a la corrección de los
> mismos errores. En conjunto, HemoVet demuestra la viabilidad técnica de combinar la
> clasificación hematológica automatizada, la explicación controlada y la visualización
> responsable para los ciudadanos.»

### Abstract — traducción del mismo párrafo

> «The conversational module was evaluated on the real pipeline through batteries covering
> safety, spelling robustness, multi-turn memory, source consistency and a blinded veterinary
> rubric; both raters judged all thirty evaluated answers to be clinically safe, and no
> hallucinations were observed in the sample. In August 2026 the conversational runtime was
> migrated to an NVIDIA A100 graphics processing unit, and the change was characterised through
> a measurement campaign with ten hypotheses registered before measuring: the median per-turn
> latency dropped by 60.6 % (from 54.4 s to 21.4 s; Wilcoxon signed-rank test paired by case,
> n = 64) and the share of unanswered turns fell from 24.3 % to 8.6 % (exact McNemar test,
> p = 0.035), although the failure-identifier analysis shows that both failure sets correspond
> to distinct phenomena rather than to the correction of the same errors. Overall, HemoVet
> demonstrates the technical feasibility of combining automated hematological classification,
> controlled explanation and responsible citizen-facing visualisation.»

### Además, en el párrafo 2 de ambos

Donde dice «una capa conversacional LLM/RAG con límites de seguridad clínica», el sistema real ya
no es solo eso: hoy incorpora una **puerta de contenido** que invalida la respuesta que solo
deriva, y un **completado determinista desde la base de datos** para lo que el sistema ya sabe.
Sugerencia mínima: «…una capa conversacional LLM/RAG con límites de seguridad clínica y
completado determinista de los datos ya registrados».

---

## A-PRE-01 · Tabla de contenido

Regenerar al final. Verificar que aparecen, con página:

- `6.6. Resultados de la vigilancia poblacional`
- `6.9. Recaracterización del runtime conversacional sobre A100` (y sus subsecciones)
- `3.11. Metodología de recaracterización y pre-registro de hipótesis`
- `5.9. Cadena de release y contrato de runtime GPU`
- `5.10. Evolución del asistente: rondas 4 a 6`
- `1.1.3.7. Rendimiento de inferencia de modelos de lenguaje`
- `Anexo E`

---

## A-PRE-08 · Numeración mixta de tablas

El Capítulo II usa `Tabla 1`…`Tabla 6`; el resto usa `Tabla N.M`. El manual pide numeración
consecutiva por categoría. **Recomendación:** renumerar las seis del Capítulo II a
`Tabla 2.1`…`Tabla 2.6` y actualizar la Lista de Tablas y las referencias del cuerpo. Es un
cambio mecánico de bajo riesgo que elimina una observación segura del comité.

Lo mismo aplica a `Figura 1`, `Figura 2`, `Figura 3` → `Figura 2.1`, `Figura 2.2`, `Figura 2.3`.

---

## Checklist de cierre de este bloque

- [ ] Agradecimientos redactados (×2).
- [ ] Dedicatorias redactadas (×2).
- [ ] Resumen ejecutivo actualizado y dentro de 250–400 palabras.
- [ ] Abstract equivalente.
- [ ] Lista de Tablas renumerada y con páginas.
- [ ] Lista de Figuras con las 12 entradas nuevas y con páginas.
- [ ] Lista de Anexos con el Anexo E.
- [ ] TOC regenerado con páginas.
- [ ] Numeración de tablas y figuras del Capítulo II unificada.
- [ ] Portada verificada contra el Anexo 1 del manual (título, integrantes con ID, asesor).
