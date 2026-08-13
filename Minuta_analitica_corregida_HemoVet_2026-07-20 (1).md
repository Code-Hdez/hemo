# Minuta analítica corregida — Reunión de seguimiento de HemoVet

**Fecha:** 20 de julio de 2026  
**Duración:** 55 minutos  
**Participantes:** Lisibonny Eustina Beato, Edwin Andrés Balbuena Bisonó y Carlos David Hernández Collado  
**Tipo de documento:** Minuta de análisis técnico, no transcripción literal  
**Fuente:** Transcripción de la reunión “General-20260720_100233”

> **Nota de precisión:** La transcripción automática contiene palabras incompletas y errores de reconocimiento. Las preguntas y respuestas se presentan con correcciones mínimas de puntuación y ortografía, sin alterar su sentido. Cuando una intervención no puede reconstruirse con seguridad, se indica expresamente.

---

# 1. Corrección conceptual necesaria

En la reunión se trataron **dos tipos de preguntas diferentes**, que no deben mezclarse:

1. **Preguntas generadas por la aplicación para preparar una consulta veterinaria.**  
   Ejemplo: preguntas sugeridas al propietario después de analizar el hemograma.

2. **Preguntas que una persona escribe directamente al asistente conversacional.**  
   Ejemplo: “¿Qué puedes observar sobre mi perro en los últimos hemogramas que analizaste?”.

El problema más grave evidenciado en la demostración corresponde al **segundo tipo**: la profesora realizó preguntas al asistente y este respondió de manera incompleta, incoherente o contradictoria con las clasificaciones mostradas por la aplicación.

También debe utilizarse la terminología técnica correcta:

- El **modelo de Machine Learning (ML)** clasifica los datos tabulares y genera una etiqueta o patrón.
- El **modelo de lenguaje (LLM)** recibe preguntas y genera respuestas conversacionales.
- La falla observada se encuentra principalmente en la **integración ML–LLM**, porque el asistente no parece utilizar de manera confiable la etiqueta producida por el clasificador.

Por tanto, no conviene escribir que “el ML responde preguntas”. Académicamente debe indicarse que **el usuario consulta al asistente conversacional y este debe explicar los resultados generados por el modelo de clasificación**.

---

# 2. Resumen ejecutivo y opinión general

La reunión no demostró solamente que “faltan mejoras” en el asistente. Demostró una falla de arquitectura funcional: **la respuesta conversacional no está subordinada de manera clara al resultado del clasificador**.

La profesora realizó preguntas normales, no adversariales, sobre tres hemogramas previamente cargados. En pocos minutos se observaron los siguientes problemas:

- El asistente se concentró en valores aislados y no en el resultado integral del modelo.
- Indicó o sugirió alteraciones en tres hemogramas cuando la interfaz mostraba patrones en solo dos.
- No pudo listar correctamente los patrones por hemograma.
- Afirmó que no tenía las fechas disponibles.
- No respondió de forma directa a preguntas sobre condiciones o diagnósticos.
- Generó una recomendación clínica genérica que podía interpretarse como alarma, aunque el modelo principal no había detectado uno de los patrones contemplados.
- Perdió el contexto conversacional al cambiar de modo o recargar la página.

**Opinión técnica:** cambiar a un LLM más grande puede mejorar redacción, seguimiento de instrucciones y capacidad de contexto, pero no corregirá por sí solo estas fallas. El problema central parece ser el **contenido y la estructura del contexto enviado al LLM**, así como la ausencia de reglas claras para resolver contradicciones entre valores crudos, etiquetas del clasificador y respuestas generadas.

---

# 3. Preguntas realizadas al asistente y respuestas observadas

## Caso 1 — Consulta general sobre el historial

### Pregunta realizada

> **“¿Qué puedes observar sobre mi perro en los últimos hemogramas que analizaste?”**

### Respuesta del asistente leída durante la reunión

> “Se observa una disminución significativa en el valor de hemoglobina. Este cambio puede ser compatible con una reducción en la capacidad del perro para transportar oxígeno, aunque no confirma una enfermedad específica. Recomiendo que se evalúe este hallazgo con un veterinario para determinar su causa y significado clínico en el contexto general de salud del perro.”

### Análisis

La respuesta es lingüísticamente adecuada y contiene una advertencia prudente, pero **no responde completamente a la solicitud**.

La pregunta pide una observación general sobre **varios hemogramas históricos**. Por tanto, la respuesta debió incluir:

- cuántos hemogramas fueron analizados;
- sus fechas;
- los patrones detectados en cada uno;
- los cambios entre el primero, el segundo y el tercero;
- si existe mejoría, estabilidad o empeoramiento;
- cuáles datos sustentan esa conclusión.

En cambio, el asistente seleccionó un único hallazgo —la disminución de hemoglobina— y produjo una explicación clínica general. Esto sugiere que tiene acceso parcial a los valores, pero no utiliza o no prioriza correctamente la estructura histórica completa.

### Clasificación del problema

- **Tipo:** respuesta incompleta y pérdida de intención.
- **Gravedad:** alta.
- **Posible causa:** contexto histórico no estructurado, prompt ambiguo o recuperación parcial de datos.
- **No constituye por sí sola una alucinación**, siempre que la disminución de hemoglobina existiera realmente. El problema es que no responde a todo lo solicitado.

---

## Caso 2 — Determinación de si los tres hemogramas mostraban una condición similar

### Pregunta reconstruida

La transcripción presenta interrupciones en esta parte. El sentido de la consulta fue verificar si en los **tres hemogramas** se había observado o diagnosticado una condición semejante.

### Respuesta o afirmación atribuida al asistente

La profesora leyó una respuesta que sugería que los hallazgos de los tres hemogramas eran compatibles con un patrón inflamatorio o de estrés. Inmediatamente aclaró que, según la interfaz, **solo dos hemogramas tenían patrones**, mientras que en uno no se había detectado ninguno.

### Comentario realizado durante la reunión

Edwin indicó:

> “Posiblemente que ya ha alucinado.”

### Análisis

Este es uno de los hallazgos más graves. Si el sistema tenía tres registros y la salida del clasificador indicaba:

- dos con patrón detectado;
- uno sin patrón detectado;

el asistente no podía responder como si los tres compartieran la misma condición.

Esto demuestra una de estas posibilidades:

1. La etiqueta de cada hemograma no estaba incluida en el contexto.
2. Las etiquetas sí estaban presentes, pero no se distinguían claramente por registro.
3. El LLM mezcló valores de diferentes hemogramas.
4. El asistente infería por su cuenta a partir de valores crudos y sustituía la salida del clasificador.
5. El historial enviado no preservaba correctamente identidad, fecha y resultado de cada análisis.

### Clasificación del problema

- **Tipo:** contradicción factual o alucinación contextual.
- **Gravedad:** crítica.
- **Impacto:** invalida la confianza en la función de comparación histórica.
- **Acción inmediata:** crear un caso de prueba exacto con tres hemogramas y verificar la respuesta esperada antes de continuar con otras mejoras.

---

## Caso 3 — Solicitud de listar patrones por hemograma

### Pregunta realizada

La formulación buscaba que el asistente listara **los patrones detectados en cada uno de los tres hemogramas**.

Una versión normalizada sería:

> **“Lista los patrones detectados en cada uno de los tres hemogramas.”**

### Respuesta del asistente leída en la reunión

> “No se proporcionan fechas específicas para cada estudio. Los hechos clínicos autorizados se registran tres con valores de hemoglobina, hematocrito y eosinófilos. Pero las fechas exactas no están disponibles en este turno. Por lo tanto, no se pueden listar los patrones por fecha. Se recomienda que un veterinario interprete los cambios junto con la condición clínica.”

### Análisis

La respuesta falla en varios niveles:

1. **No realiza la tarea solicitada.**  
   Se pidieron patrones y devolvió valores hematológicos generales.

2. **Declara que no dispone de las fechas.**  
   La aplicación sí manejaba fechas de los hemogramas, aunque la presentación visual era confusa. Esto indica que el asistente no recibió las fechas o no pudo recuperarlas.

3. **Sustituye una respuesta factual por una advertencia genérica.**  
   “Consulte a un veterinario” no resuelve la pregunta.

4. **Introduce una expresión confusa:** “hechos clínicos autorizados”.  
   Esto parece provenir del prompt o de una traducción defectuosa del esquema de contexto.

5. **No identifica los registros individualmente.**  
   Debió responder con una tabla o lista: fecha, patrón, nivel de confianza y observación.

### Clasificación del problema

- **Tipo:** incumplimiento de instrucción y contexto insuficiente.
- **Gravedad:** crítica.
- **Posible causa principal:** las fechas, etiquetas e identificadores no forman parte de un objeto estructurado y verificable enviado al LLM.

---

## Caso 4 — Solicitud de condiciones detectadas en cada análisis

### Pregunta realizada

> **“Dime las condiciones detectadas en cada uno.”**

### Resultado observado

La respuesta completa no quedó registrada de forma clara en la transcripción. Durante la espera, Carlos expresó:

> “Déjame ver qué pasó en el servidor.”

Posteriormente, la profesora cambió al análisis de un hemograma individual.

### Análisis

No debe inventarse una respuesta que no aparece en la fuente. Lo que sí puede afirmarse es que la consulta no produjo una respuesta útil durante la demostración.

Este caso debe registrarse como:

- posible bloqueo;
- demora;
- error del servidor;
- pérdida de contexto;
- o fallo de generación.

No debe mezclarse con una alucinación, porque aquí el problema observado fue la **ausencia de una respuesta verificable**.

### Clasificación del problema

- **Tipo:** fallo de disponibilidad o ejecución.
- **Gravedad:** alta.
- **Acción:** registrar logs, tiempo de respuesta, error del backend, estado del modelo y tamaño del contexto.

---

## Caso 5 — Consulta sobre un hemograma sin patrón detectado

### Pregunta realizada

> **“¿En este hemograma ves algún problema con mi perro?”**

### Respuesta del asistente observada

La parte claramente registrada indica:

> “Se recomienda una valoración veterinaria completa con los signos clínicos y antecedentes del perro para interpretar estos resultados.”

La profesora señaló que el asistente estaba observando valores fuera de rango, pero no parecía reconocer que el resultado mostrado por el sistema no contenía un patrón específico.

### Análisis

Aquí debe realizarse una distinción clínica y técnica importante:

- **“No se detectó uno de los patrones clasificados por el modelo”** no significa necesariamente que todos los parámetros estén normales.
- Puede haber valores fuera de rango sin que se cumpla la combinación necesaria para una etiqueta determinada.
- Sin embargo, el asistente debe explicar esa diferencia con claridad.

Una respuesta correcta habría sido similar a:

> “El modelo no detectó ninguno de los patrones hematológicos específicos contemplados por el sistema en este análisis. No obstante, existen valores fuera de rango que deben interpretarse junto con los signos clínicos y antecedentes por un veterinario.”

La respuesta observada fue demasiado genérica y dejó la impresión de que existía un problema que contradecía el resultado principal. La falla no consiste en recomendar valoración veterinaria; esa recomendación es prudente. La falla consiste en **no mencionar primero el resultado del clasificador y no explicar la diferencia entre valores alterados y patrón clasificado**.

### Clasificación del problema

- **Tipo:** comunicación clínica ambigua y falta de anclaje al modelo.
- **Gravedad:** crítica.
- **Riesgo:** alarma innecesaria y pérdida de confianza.

---

## Caso 6 — Pregunta directa sobre el diagnóstico

### Pregunta realizada

> **“¿Cuál es el diagnóstico?”**  
> **“¿Cuáles diagnósticos ves en este hemograma?”**

### Respuesta registrada

La transcripción no contiene una respuesta completa y confiable del asistente después de esta pregunta. La profesora concluyó que, si la etiqueta diagnóstica o el patrón calculado se estuviera pasando correctamente, el asistente debería poder recuperarlo de inmediato.

### Análisis

No debe atribuirse una respuesta inexistente al sistema. El hallazgo verificable es que **la sesión no permitió demostrar que el LLM recibía y utilizaba la etiqueta del modelo de clasificación**.

También debe corregirse el término “diagnóstico” en la interfaz y en el prompt. Como el sistema es de apoyo, conviene utilizar:

- “patrón detectado”;
- “clasificación sugerida”;
- “hallazgo compatible con”;
- “resultado del modelo”.

El LLM no debe presentar una enfermedad como diagnóstico definitivo.

### Clasificación del problema

- **Tipo:** función no demostrada.
- **Gravedad:** crítica.
- **Implicación académica:** el objetivo relacionado con explicación de resultados solo puede considerarse parcialmente cumplido.

---

# 4. Problema adicional: preguntas generadas para la consulta veterinaria

Este hallazgo es diferente de las preguntas realizadas al asistente, pero también apareció en la reunión.

La aplicación generó preguntas como:

> “¿El perro presenta signos de pérdida de sangre o hemorragia reciente?”

y

> “¿Se han realizado otros estudios...?”

La profesora cuestionó que estas fueran preguntas que el propietario le haría al veterinario. En realidad, parecen preguntas que el veterinario le haría al propietario o datos que el propietario debería conocer antes de la consulta.

## Opinión

La función no debe eliminarse, pero sí debe rediseñarse. Se recomienda separar el contenido en tres bloques:

### Preguntas que el propietario puede hacer al veterinario

- “¿Qué causas podrían explicar la disminución de hemoglobina?”
- “¿Es necesario repetir el hemograma?”
- “¿Qué pruebas complementarias recomienda?”
- “¿Qué signos debo vigilar en casa?”

### Información que el propietario debe preparar

- presencia de sangrado;
- cambios en apetito o actividad;
- tratamientos recientes;
- estudios anteriores;
- fecha de inicio de síntomas.

### Preguntas que podría realizar el veterinario

- “¿Ha observado pérdida de sangre?”
- “¿Se han realizado pruebas complementarias?”
- “¿El paciente recibe medicamentos?”

La aplicación debe indicar claramente quién formula cada pregunta y a quién va dirigida.

---

# 5. Diagnóstico técnico de la integración ML–LLM

## 5.1 El problema no es solo el tamaño del modelo

La nueva máquina con aproximadamente 24 GB de VRAM redujo el tiempo de respuesta de cerca de un minuto a unos siete segundos. Esto es un avance importante de infraestructura.

No obstante, la velocidad no garantiza calidad. Un modelo más grande puede producir respuestas más fluidas, pero también puede generar contradicciones más convincentes si recibe contexto incompleto.

## 5.2 El clasificador debe ser la fuente de verdad

El flujo correcto debe ser:

```text
Hemograma
   ↓
Validación y preprocesamiento
   ↓
Modelo de clasificación ML
   ↓
Resultado estructurado y versionado
   ↓
LLM explicador
   ↓
Respuesta al usuario
```

El LLM no debe sustituir al clasificador ni recalcular libremente el patrón a partir de valores aislados.

## 5.3 Contexto estructurado recomendado

Cada hemograma enviado al asistente debe incluir, como mínimo:

```json
{
  "hemogram_id": "CBC-003",
  "sample_date": "2026-06-20",
  "uploaded_at": "2026-07-20T14:15:00-04:00",
  "model_version": "rf-1.4.0",
  "detected_pattern": null,
  "classification_status": "NO_TARGET_PATTERN_DETECTED",
  "probabilities": {
    "inflammatory_pattern": 0.18,
    "stress_leukogram": 0.11
  },
  "out_of_range_values": [
    {
      "parameter": "HGB",
      "value": 11.2,
      "unit": "g/dL",
      "flag": "LOW"
    }
  ],
  "authorized_interpretation": "No se detectó uno de los patrones objetivo del sistema."
}
```

Para un historial, debe enviarse un arreglo ordenado y no un bloque de texto libre.

## 5.4 Regla de respuesta obligatoria

El prompt del sistema debe imponer este orden:

1. Mencionar el resultado del clasificador.
2. Distinguir patrón clasificado de valores fuera de rango.
3. Explicar el hallazgo sin introducir diagnósticos nuevos.
4. Indicar límites y recomendar evaluación veterinaria.
5. Declarar explícitamente cuando falta información.
6. No afirmar que varios hemogramas comparten un patrón si la etiqueta no coincide.

---

# 6. Matriz analítica de los casos observados

| Caso | Pregunta | Resultado observado | Falla principal | Severidad |
|---|---|---|---|---|
| 1 | ¿Qué puedes observar sobre mi perro en los últimos hemogramas? | Se enfocó en disminución de hemoglobina. | Respuesta parcial; no compara todo el historial. | Alta |
| 2 | ¿Los tres hemogramas presentan una condición similar? | Sugirió un patrón similar en los tres. | Contradicción con la interfaz; posible alucinación. | Crítica |
| 3 | Lista los patrones en cada hemograma. | Dijo no disponer de fechas y habló de valores. | No cumple la instrucción; contexto incompleto. | Crítica |
| 4 | Dime las condiciones detectadas en cada uno. | No se obtuvo respuesta verificable. | Error, bloqueo o fallo del servidor. | Alta |
| 5 | ¿En este hemograma ves algún problema? | Dio advertencia genérica sin anclarse a la etiqueta. | Ambigüedad y alarma potencial. | Crítica |
| 6 | ¿Cuál es el diagnóstico o patrón? | No quedó una respuesta confiable registrada. | No se demostró acceso a la salida del clasificador. | Crítica |

---

# 7. Comentario crítico como asesor

La principal debilidad actual no es estética ni de usabilidad. Es una **incoherencia entre dos fuentes de decisión dentro de la misma plataforma**.

Un jurado podría formular inmediatamente estas preguntas:

1. ¿Cuál componente tiene autoridad: el clasificador o el LLM?
2. ¿Qué ocurre cuando el LLM contradice la etiqueta?
3. ¿Cómo se evita que el asistente interprete valores aislados como una enfermedad?
4. ¿Qué pruebas demuestran concordancia entre ambos componentes?
5. ¿Cómo se mide una alucinación?
6. ¿Qué versión del modelo produjo cada resultado?
7. ¿Cómo se reproducen las respuestas obtenidas?
8. ¿Qué información recibe exactamente el asistente?
9. ¿Cómo se protege al usuario frente a una respuesta alarmista?
10. ¿Por qué se denomina diagnóstico a una clasificación sugerida?

Actualmente, la defensa de estas preguntas sería débil si solo se responde que se consiguió una máquina más potente o un modelo más grande.

La solución debe demostrarse con evidencia experimental.

---

# 8. Plan de acción corregido

## Prioridad P0 — Coherencia del sistema

| ID | Tarea | Criterio de aceptación |
|---|---|---|
| P0-01 | Inspeccionar y documentar el payload exacto enviado al LLM. | Se evidencia que contiene fecha, identificador, etiqueta, probabilidades y valores. |
| P0-02 | Hacer que la salida del clasificador sea la fuente principal de verdad. | Ninguna respuesta contradice la clasificación almacenada. |
| P0-03 | Separar “sin patrón objetivo” de “todos los valores normales”. | El asistente explica correctamente ambos conceptos. |
| P0-04 | Crear pruebas automatizadas con las preguntas de esta reunión. | Las seis consultas tienen una respuesta esperada y una prueba reproducible. |
| P0-05 | Prohibir diagnósticos no presentes en la salida autorizada. | El LLM no introduce enfermedades o patrones nuevos. |
| P0-06 | Verificar la relación uno a uno entre hemograma, fecha y etiqueta. | El asistente lista correctamente cada registro histórico. |

## Prioridad P1 — Historial y conversación

| ID | Tarea | Criterio de aceptación |
|---|---|---|
| P1-01 | Enviar el historial como arreglo cronológico estructurado. | Puede identificar primero, último y evolución. |
| P1-02 | Mostrar fecha de muestra y fecha de carga. | Ambas son visibles y llegan al LLM. |
| P1-03 | Mantener el contexto al cambiar de modo o mascota. | La política de persistencia queda definida y probada. |
| P1-04 | Manejar fallos del servidor con mensajes claros. | No se muestra una respuesta incompleta como si fuera válida. |

## Prioridad P2 — Validación externa

| ID | Tarea | Criterio de aceptación |
|---|---|---|
| P2-01 | Invitar usuarios externos a formular preguntas libres. | Se registra cada pregunta, respuesta y evaluación. |
| P2-02 | Validar respuestas con veterinarios. | Se mide corrección, claridad, utilidad y riesgo. |
| P2-03 | Crear una prueba de contradicción ML–LLM. | Se calcula la tasa de concordancia. |
| P2-04 | Evaluar el modelo nuevo contra el actual. | Se comparan calidad, latencia y alucinaciones, no solo VRAM. |

## Prioridad P3 — Documentación

| ID | Tarea | Criterio de aceptación |
|---|---|---|
| P3-01 | Documentar estos casos como resultados de prueba. | Se presentan entradas, respuestas, fallos y correcciones. |
| P3-02 | No declarar cumplimiento total del objetivo conversacional. | Se utiliza “cumplimiento parcial” hasta validar. |
| P3-03 | Actualizar conclusiones después de repetir las pruebas. | Las afirmaciones se sustentan en métricas. |
| P3-04 | Diferenciar ML, LLM, API y módulo de vigilancia. | La arquitectura se describe sin mezclar responsabilidades. |

---

# 9. Métricas que deben reportarse

## Concordancia con el clasificador

```text
Concordancia = respuestas consistentes con la etiqueta / total de respuestas evaluadas
```

## Tasa de contradicción

```text
Contradicción = respuestas que contradicen la salida del ML / total de respuestas
```

## Tasa de alucinación contextual

```text
Alucinación = respuestas que inventan patrones, fechas o diagnósticos / total de respuestas
```

## Cumplimiento de la instrucción

Evaluar si la respuesta:

- contesta la pregunta;
- utiliza todos los hemogramas solicitados;
- identifica fechas;
- diferencia valores de patrones;
- mantiene el contexto;
- evita afirmaciones no sustentadas.

## Latencia

Reportar:

- promedio;
- mediana;
- percentil 95;
- respuesta en frío;
- respuesta con modelo precalentado.

---

# 10. Estado real del objetivo conversacional

A partir de la demostración, el objetivo no puede considerarse completamente logrado.

## Capacidades demostradas

- El asistente recibe preguntas en lenguaje natural.
- Puede explicar valores hematológicos.
- Produce respuestas más rápidas con la nueva infraestructura.
- Puede acceder al menos a parte de los datos del hemograma.

## Capacidades no demostradas o fallidas

- Coherencia con la etiqueta del clasificador.
- Comparación fiable de varios hemogramas.
- Identificación correcta de patrones por fecha.
- Continuidad de contexto entre modos.
- Respuesta directa sobre la clasificación sugerida.
- Ausencia de alucinaciones.
- Validación externa suficiente.

## Dictamen

**Cumplimiento parcial y todavía no aceptable para defensa**, tal como se reconoció durante la reunión.

---

# 11. Decisiones de la reunión

1. No se recomendó realizar la defensa ordinaria inmediata.
2. Se propuso acogerse al estado de incompleto.
3. La fecha tentativa de presentación sería la semana del 24 de agosto de 2026.
4. La prioridad debe ser corregir la funcionalidad vinculada con los objetivos.
5. La parte conversacional fue identificada como el componente más débil.
6. Se deben organizar pruebas con personas externas.
7. El documento y el blog no deben priorizarse sobre la corrección funcional inmediata.
8. El equipo debía confirmar su decisión definitiva antes de las 4:00 p. m. del día de la reunión.

---

# 12. Conclusión analítica

La reunión produjo evidencia útil porque las preguntas realizadas fueron simples y realistas. No fue necesario utilizar ataques complejos para detectar inconsistencias. Esto demuestra que el problema no se limita a casos extremos; afecta el uso normal del asistente.

El próximo avance no debe describirse únicamente como “se cambió el modelo” o “se aumentó la VRAM”. Debe demostrarse que:

- el LLM recibe la salida exacta del clasificador;
- las respuestas conservan la identidad de cada hemograma;
- las fechas están disponibles;
- no se inventan condiciones;
- se responde directamente a la pregunta;
- la interpretación es coherente con la interfaz;
- y las pruebas externas confirman la mejora.

Ese conjunto de evidencias permitiría afirmar, de manera académicamente defendible, que el asistente funciona como una capa de explicación del sistema de clasificación y no como un generador independiente de conclusiones clínicas.
