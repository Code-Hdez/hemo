# Hechos verificados — la única fuente de datos para los preliminares

> Toda cifra debe salir de aquí, **y toda cifra tiene que estar además en el cuerpo del
> documento**: el resumen sintetiza, no aporta.
>
> **[MEDIDO]** leído de un artefacto · **[DERIVADO]** calculado a partir de artefactos ·
> **[PENDIENTE]** no disponible: usar marcador, **nunca** estimar.
>
> Verificado el 12 de agosto de 2026 sobre la rama `main`, commit `f9deedb`.

---

## 1 · El resumen ejecutivo 🔴

### El párrafo que hay que sustituir

> **Texto actual, párrafo 5:** «El módulo conversacional se evaluó en el flujo de trabajo real
> utilizando baterías de pruebas de seguridad, robustez, memoria, coherencia de las fuentes y
> revisión veterinaria. En general, HemoVet demuestra la viabilidad técnica de combinar la
> clasificación hematológica automatizada, la explicación controlada y la visualización
> responsable para los ciudadanos.»

No da una sola cifra, y omite el resultado con mayor peso metodológico del proyecto.

> **Texto propuesto:**
>
> «El módulo conversacional se evaluó sobre el flujo de trabajo real mediante baterías de
> seguridad, robustez ortográfica, memoria multiturno, coherencia de fuentes y una rúbrica
> veterinaria ciega; las treinta respuestas evaluadas fueron consideradas clínicamente seguras
> por ambos evaluadores y no se detectaron alucinaciones en la muestra. En agosto de 2026 el
> *runtime* conversacional se migró a una unidad de procesamiento gráfico NVIDIA A100, y el cambio
> se caracterizó mediante una campaña de medición con diez hipótesis registradas antes de medir:
> la latencia mediana por turno se redujo un 60,6 % (de 54,4 s a 21,4 s; prueba de Wilcoxon
> pareada por caso, n = 64) y la proporción de turnos sin respuesta bajó de 24,3 % a 8,6 %
> (McNemar exacto, p = 0,035), si bien el análisis de identificadores de fallo muestra que ambos
> conjuntos de fallos corresponden a fenómenos distintos y no a la corrección de los mismos
> errores. En conjunto, HemoVet demuestra la viabilidad técnica de combinar la clasificación
> hematológica automatizada, la explicación controlada y la visualización responsable para los
> ciudadanos.»

### La aritmética que hay que resolver 🔴

| Elemento | Palabras |
| :--- | ---: |
| Resumen actual | **354** [MEDIDO] |
| *Abstract* actual | **313** [MEDIDO] |
| Máximo que sugiere el manual | **400** |
| Párrafo actual (el que sale) | ~55 |
| Párrafo propuesto (el que entra) | ~145 |
| **Resultado si solo se sustituye** | **~445** 🔴 |

**Hay que recortar unas 50 palabras en compensación.** El candidato es **el párrafo 4** —validación
externa y clínica—, que hoy repite cifras que el párrafo 3 ya introduce.

**Cuenta las palabras del resultado y decláralo.** Es el único límite duro de este encargo.

### El abstract — traducción del mismo párrafo

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

> ⚠️ **Ojo con los decimales.** El resumen en español lleva **coma** decimal (`60,6 %`); el
> *abstract* en inglés lleva **punto** (`60.6 %`). Es correcto que difieran, y es un detalle que se
> corrige mal con frecuencia.

**El recorte compensatorio hay que aplicarlo también al *abstract***, en el párrafo equivalente.

### Además, en el párrafo 2 de ambos

Donde dice «una capa conversacional LLM/RAG con límites de seguridad clínica», el sistema real ya
no es solo eso: hoy incorpora una **puerta de contenido** que invalida la respuesta que solo
deriva, y un **completado determinista desde la base de datos** para lo que el sistema ya sabe.

> **Sugerencia mínima:** «…una capa conversacional LLM/RAG con límites de seguridad clínica y
> completado determinista de los datos ya registrados».

En inglés: «…with clinical safety limits and deterministic completion of already recorded data».

---

## 2 · Lista de Tablas — la numeración final 🔴

### Lo que no cuadra hoy

| La Lista de Tablas dice | El cuerpo tiene | Problema |
| :--- | :--- | :--- |
| Tabla 6.13 — Rendimiento de inferencia y pruebas backend | Tabla 6.13 ✅ | correcto |
| **Tabla 6.14 — Señales del reporte de vigilancia poblacional** | **no existe** | la sección §6.6 no está escrita |
| Tabla 6.15 — Usabilidad percibida por dimensión, n = 44 | numerada como **Tabla 6.14** | desfase de uno |

### La numeración final del Capítulo VI, tras insertar §6.6 y §6.8

| Nº | Título | Origen |
| :--- | :--- | :--- |
| 6.1 – 6.13 | *(sin cambios)* | actuales |
| **6.14** | Compuertas técnicas del módulo de vigilancia poblacional | **§6.6 nueva** |
| **6.15** | Señales del reporte de vigilancia poblacional | **§6.6 nueva** |
| **6.16** | Usabilidad percibida por dimensión, n = 44 | actual 6.14 → **se corre** |
| **6.17 – 6.23** | Siete tablas de la recaracterización del *runtime* | **§6.8 nueva** |

> 🔴 **Corrección de una inconsistencia del material de partida.** La versión anterior de este
> mapa asignaba a §6.6 **una sola** tabla (6.14), dejaba usabilidad en 6.15 y daba a §6.8 el rango
> 6.16–6.20. **Es incorrecto:** §6.6 aporta **dos** tablas numeradas y §6.8 aporta **siete**. La
> numeración válida es la de arriba, y es la que usan los textos ya redactados de esas dos
> secciones.

### Capítulo V

Si se aceptan §5.9 y §5.10: **Tabla 5.10** (contratos y artefactos de la cadena de versiones
desplegables) y **Tabla 5.11** (cambios de las rondas 4 a 6 del asistente). El paquete del Capítulo
V contempla además una **Tabla 5.12**; verifícalo contra lo que ese capítulo haya devuelto.

### Capítulo II

Las seis tablas del Capítulo II usan hoy numeración suelta (`Tabla 1` … `Tabla 6`) mientras el
resto del documento usa `Tabla N.M`. **Renumeradas a `Tabla 2.1` … `Tabla 2.6`**, más las que
añadan las subsecciones nuevas de presupuesto (2.7, 2.8 y quizá 2.9).

Lo mismo con las figuras: `Figura 1`, `Figura 2`, `Figura 3` → `Figura 2.1`, `Figura 2.2`,
`Figura 2.3`.

### Capítulos III y I

- **Tabla 3.12** — Identidad sellada del *runtime* bajo el que se midió (§3.11 nueva).
- El Capítulo I no añade tablas.

---

## 3 · Lista de Figuras — las doce entradas nuevas

Van **después de la actual Figura 6.29**. Las figuras 6.1 a 6.29 conservan su número.

| Nº | Título |
| :--- | :--- |
| Figura 6.30 | Composición del corpus de evidencia previa auditado |
| Figura 6.31 | Reconstrucción del protocolo anterior: semáforo de las quince preguntas |
| Figura 6.32 | Verificación de identidad de modelo en cada respuesta |
| Figura 6.33 | Techos de decodificación y rendimiento medido |
| Figura 6.34 | Distribución del tiempo por token de salida |
| Figura 6.35 | Lo predicho frente a lo medido: la sobrecarga de gramática |
| Figura 6.36 | Latencia por caso entre ambas configuraciones |
| Figura 6.37 | Distribución de las diferencias pareadas |
| Figura 6.38 | Naturaleza de los fallos: dos fenómenos distintos |
| Figura 6.39 | Tasa de alucinación numérica y su intervalo de confianza |
| Figura 6.40 | Tablero de las diez hipótesis pre-registradas |
| Figura 6.41 | Potencia del diseño |

**Y una más, del Capítulo IV:** `Figura 4.7 — Diagrama de despliegue de HemoVet`, si ese capítulo
la incorporó. **Verifícalo** antes de añadirla: puede seguir pendiente de dibujar.

### Una corrección de título en el Capítulo IV

La Lista de Figuras, el pie del cuerpo y la referencia cruzada dan **tres títulos distintos** para
la misma figura de despliegue. **Título unificado: *Diagrama de despliegue lógico de HemoVet*.**

---

## 4 · Lista de Anexos — la quinta fila

| Anexo | Título | Contenido principal |
| :--- | :--- | :--- |
| Anexo E | Evidencia de la campaña de recaracterización del *runtime* conversacional | Pre-registro firmado con su compendio, tablero de las diez hipótesis, procedencia criptográfica de cada artefacto fuente, manifiesto de figuras y tablas, registro de verificación con la aserción que falla declarada, y paneles de ausencia. |

Los anexos A a D conservan sus filas actuales sin cambios.

---

## 5 · Tabla de Contenido — las siete entradas a verificar

**No la produces:** Word la regenera desde los estilos de título. Lo que produces es la lista de lo
que debe aparecer en ella, para que quien la regenere lo verifique:

- `1.1.3.7. Rendimiento de inferencia de modelos de lenguaje`
- `3.11. Metodología de recaracterización y pre-registro de hipótesis`
- `5.9. Cadena de release y contrato de runtime`
- `5.10. Evolución del asistente: rondas 4 a 6`
- `6.6. Resultados de la vigilancia poblacional`
- `6.8. Recaracterización del runtime conversacional` *(y sus subsecciones 6.8.1 a 6.8.8)*
- `Anexo E. Evidencia de la campaña de recaracterización del runtime conversacional`

**Todas con su número de página.** Si alguna no aparece, el estilo de título no se aplicó al
insertarla en Word.

---

## 6 · La portada — verificación, no reescritura

La portada existe y está completa. **No se reescribe.** Lo único que hay que hacer es verificarla
contra el anexo de formato del manual:

| Elemento | Estado |
| :--- | :---: |
| Nombre de la universidad y la facultad | ✅ presente |
| Escuela | ✅ presente |
| Logotipo institucional | ✅ presente |
| Título del proyecto | ✅ presente |
| Fórmula de presentación del requisito | ✅ presente |
| Integrantes con su identificador | ✅ dos, con matrícula |
| Asesora, con su cargo | ✅ presente |
| Ciudad, país y fecha | ✅ presente |

**Si el manual exige algún elemento adicional, anótalo como pendiente. No lo inventes.**

---

## 7 · Los agradecimientos y las dedicatorias 🔴

**Los cuatro encabezados existen con el cuerpo completamente vacío:**

- Agradecimientos – Carlos David Hernández Collado
- Agradecimientos – Edwin Andrés Balbuena Bisonó
- Dedicatoria – Carlos David Hernández Collado
- Dedicatoria – Edwin Andrés Balbuena Bisonó

El manual los marca como **opcionales**, pero **si el encabezado está, el cuerpo tiene que estar**.
Un encabezado con la página en blanco es peor que no tenerlo. Una página por estudiante, paginada
en números romanos.

> 🔴 **Estos textos no los escribe el LLM.** Son textos personales de dos personas concretas, sobre
> su familia, sus profesores y su propio recorrido. Un agradecimiento generado se nota
> inmediatamente, y es de las pocas partes de la tesis donde eso ocurre.
>
> **Lo que sí se produce es un guion de estructura**, en `04_GUION_SECCIONES_NUEVAS.md`. Nada más.
> Ni un párrafo de ejemplo con contenido personal inventado.

---

## 8 · Cifras del cuerpo que el resumen puede citar

Solo estas, y solo porque el cuerpo las reporta.

| Cifra | Valor | Sección | Marca |
| :--- | ---: | :--- | :---: |
| Respuestas evaluadas clínicamente seguras | 30 de 30 | §6.4.5 | MEDIDO |
| Alucinaciones detectadas en la muestra | 0 | §6.4.5 | MEDIDO |
| Latencia mediana por turno, antes → después | 54,4 s → 21,4 s | §6.8 | MEDIDO |
| Reducción de la latencia mediana | 60,6 % | §6.8 | DERIVADO |
| Casos pareados | n = 64 | §6.8 | MEDIDO |
| Turnos sin respuesta, antes → después | 24,3 % → 8,6 % | §6.8 | MEDIDO |
| Contraste de esa proporción | McNemar exacto, p = 0,035 | §6.8 | MEDIDO |
| Hipótesis registradas antes de medir | 10 | §3.11 y §6.8 | MEDIDO |
| Registros del Dog Aging Project | 1 301 | §6.2 | MEDIDO |
| Características finales del modelo | 43 | §6.1 | MEDIDO |

> ⚠️ El resumen actual escribe `1,301 registros` con **coma de millar inglesa**. En español es
> `1 301`. Corrígelo al pasar por el párrafo.

---

## 9 · Lo que NO debe aparecer

| Prohibido | Por qué |
| :--- | :--- |
| Cualquier cifra que no esté en el cuerpo | El resumen sintetiza, no aporta |
| Citas bibliográficas en el resumen o el *abstract* | No las llevan |
| Un resumen de más de 400 palabras | Límite duro del manual |
| Texto de agradecimiento o dedicatoria redactado | Lo escriben los estudiantes |
| Números de página inventados | Si no los tienes, deja la celda vacía |
| La Tabla de Contenido completa | Word la regenera |
