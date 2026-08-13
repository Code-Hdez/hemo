# 7. Capítulo VII · Conclusiones y recomendaciones — CAPÍTULO COMPLETO (borrador para pegar)

> **Qué es este archivo (12/7/2026).** Redacta **desde cero el Capítulo VII entero**, que en
> el `.docx (7)` está VACÍO (solo existe el encabezado, párrafo 702, y salta a Referencias).
> Sigue la estructura pedida en `09_capitulo_vii_conclusiones/README.md` y la guía general
> (Cap. VII cierra objetivos, limitaciones y recomendaciones). **Es texto** (los resultados y
> figuras están en el Cap. VI y aquí solo se referencian); la única tabla es la 7.1 de
> cumplimiento de objetivos. Integra el material de `capitulo_vii_7.3_limitaciones/`.
> Cifras tomadas de las tres validaciones ya cerradas (Cap. VI): modelo, LLM/RAG y usabilidad.

---

# 7. Capítulo VII · Conclusiones y recomendaciones

## 7.1. Conclusiones

El proyecto cumplió su objetivo general: se desarrolló **HemoVet**, una plataforma web
orientada al ciudadano que integra la clasificación multilabel de patrones hematológicos del
hemograma completo canino mediante aprendizaje automático, una capa conversacional con
*guardrails* y un panel de orientación con historial y vigilancia comunitaria. El sistema
identifica patrones hematológicos de interés, comunica sus resultados en lenguaje comprensible
para el propietario, apoya el control de calidad de la lectura y habilita la visualización
individual y comunitaria de los hemogramas registrados, manteniendo en todo momento la
advertencia explícita de que **no sustituye el criterio de un médico veterinario**.

La conclusión de fondo, más allá de las cifras detalladas en el Capítulo VI, es que las cuatro
vías de evaluación convergen en un mismo mensaje. El motor de clasificación demostró un
desempeño técnico sólido y coherente con la interpretación hematológica esperada, aunque su
lectura debe hacerse por etiqueta y con cautela en las clases de bajo soporte. La validación
clínica con dos médicos veterinarios enseñó una lección metodológica central: el modelo se
aproxima al criterio profesional en un grado comparable a la propia variabilidad entre expertos,
por lo que su papel adecuado es el de **herramienta de orientación y control de calidad, no de
diagnóstico autónomo**. El asistente conversacional resultó clínicamente seguro y
mayoritariamente exacto según el juicio veterinario, lo que valida el diseño de sus *guardrails*.
Y la validación de usabilidad confirmó, con usuarios en su mayoría legos, que el objetivo más
delicado del proyecto —comunicar información hematológica compleja en lenguaje comprensible— se
logró en la práctica.

En conjunto, HemoVet se encuentra **listo para demostración y uso controlado con limitaciones**.
El proyecto demuestra la viabilidad de una herramienta ciudadana de orientación hematológica que
combina rigor técnico, resguardo de seguridad clínica y una experiencia de usuario accesible, sin
invadir el terreno del diagnóstico profesional. Las cifras que respaldan cada una de estas
afirmaciones se resumen en la sección 7.2 y se desarrollan en el Capítulo VI.

## 7.2. Resultados de los objetivos planteados

La Tabla 7.1 resume el grado de cumplimiento de cada objetivo específico y la evidencia que lo
respalda, generada durante el desarrollo y la validación del sistema.

| Objetivo específico | Evidencia principal | Estado |
| :---- | :---- | :---- |
| **OE1.** Conformar un conjunto de datos clínico estructurado (clínicas locales + Dog Aging Project), con limpieza, imputación y estandarización. | Corpus IDEXX curado y cohorte externa DAP (1 301 registros); 43 características hematológicas; artefactos de datos versionados. | Cumplido |
| **OE2.** Construir un modelo de clasificación multietiqueta de anomalías hematológicas. | Modelo XGBoost multilabel con 7 etiquetas oficiales; PR-AUC macro 0.9529, F1 macro 0.8727, recall macro 0.9205; validación clínica (kappa 0.629, F1 0.704 frente al Médico 1). | Cumplido con limitaciones |
| **OE3.** Desarrollar un portal web ciudadano (resumen, resultado explicativo, evolución longitudinal, lenguaje comprensible e indicación de cuándo consultar). | Frontend React con resumen, resultado, historial, chat, biblioteca y vigilancia; validación de usabilidad (n = 44, índice 84/100, 81.6 % favorable). | Cumplido |
| **OE4.** Realizar un módulo de vigilancia comunitaria sobre zonas agregadas, con privacidad y advertencias metodológicas. | Módulo de vigilancia con señales agregadas por zona, umbral mínimo de agregación y advertencias explícitas; reporte poblacional funcional. | Cumplido como exploratorio |
| **OE5.** Implementar una capa conversacional con *guardrails* que explique sin emitir diagnósticos, tratamientos ni dosis. | Asistente LLM/RAG con corpus veterinario local; seguridad 30/30, exactitud 83.3 %, concordancia veterinaria κ 0.841; resistencia a *prompt injection* mejorada de 61 a 1 fallo tras el refuerzo. | Cumplido |

*Tabla 7.1. Cumplimiento de los objetivos específicos y evidencia de respaldo.*

Los cinco objetivos específicos se cumplieron. OE2 se declara "cumplido con limitaciones" porque
algunas etiquetas de bajo soporte o de mayor ambigüedad clínica —en particular
PATRON_ANEMIA_REGENERATIVA— conservan intervalos amplios y se mantienen como resultado
exploratorio. OE4 se declara "cumplido como exploratorio" por las limitaciones de geocodificación
descritas en el Capítulo VI.

## 7.3. Limitaciones

El alcance y la interpretación de los resultados están sujetos a las siguientes limitaciones,
que se declaran de forma explícita:

**Del sistema y el modelo:**

- **Especie única.** El sistema se limita a hemogramas caninos; no es aplicable a otras especies
  sin un nuevo proceso de datos, etiquetado y validación.
- **Dependencia del formato y la calidad del hemograma.** La extracción y la clasificación
  dependen de la calidad del documento de origen; un valor mal transcrito o un formato no
  contemplado pueden alterar la lectura, por lo que la revisión humana de los valores es
  obligatoria.
- **Etiquetas de bajo soporte.** Algunas etiquetas presentan pocos casos positivos (p. ej.
  PATRON_ANEMIA_REGENERATIVA, con 6 casos en el conjunto de prueba), lo que amplía la
  incertidumbre y obliga a tratarlas como exploratorias.
- **Validación externa sin etiquetas compatibles.** La cohorte del Dog Aging Project no contiene
  etiquetas del esquema de HemoVet, por lo que solo permitió analizar coherencia biológica y
  desplazamiento de dominio, no medir F1 ni PR-AUC.
- **Validación clínica acotada territorialmente.** Se realizó con dos evaluadores veterinarios y
  casos de un entorno local; la concordancia interevaluador no perfecta (kappa 0.684) muestra que
  el propio criterio humano varía, lo que exige ampliar la validación con más clínicas y
  evaluadores.
- **Vigilancia poblacional no epidemiológica.** El módulo de vigilancia refleja los hemogramas
  registrados en la plataforma, no la prevalencia o incidencia reales; la geocodificación
  limitada y la concentración territorial impiden inferencias poblacionales robustas.

**Del asistente conversacional (LLM/RAG):**

- **Validación de exactitud de carácter piloto.** La rúbrica de contenido fue evaluada por dos
  veterinarios sobre 30 preguntas (concordancia κ = 0.841); la literatura recomienda entre cuatro
  y siete evaluadores y muestras de ≥100 ítems para uso clínico. Se declara como validación piloto.
- **Alcance del chat como decisión abierta.** Los fallos residuales de la categoría de
  "diagnóstico directo" no son respuestas inseguras, sino una decisión de diseño pendiente sobre
  dónde termina la orientación educativa y empieza el diagnóstico.
- **Latencia en CPU.** La generación se ejecuta sin acelerador gráfico, lo que produce tiempos de
  respuesta altos y algún tiempo de espera agotado; es una limitación de infraestructura, no de
  diseño.

**De la validación de usabilidad:**

- **Usabilidad percibida y muestra de conveniencia.** La encuesta (n = 44) mide percepción con un
  instrumento propio, no un cuestionario SUS estandarizado, y no incluye medición cronometrada de
  tareas ni tasa de error observada; el índice 0–100 es una normalización de las medias Likert.

## 7.4. Resultados inesperados o no planificados

Durante la validación surgieron hallazgos que no se anticiparon en el diseño inicial y que
resultan metodológicamente relevantes:

- **La discrepancia entre médicos es sustantiva.** La concordancia interevaluador (kappa 0.684)
  reveló que parte de las diferencias modelo–clínico no son errores del modelo, sino reflejo de la
  variabilidad legítima del criterio hematológico humano. Este hallazgo obligó a reinterpretar
  toda la validación clínica como una comparación con un "techo humano" imperfecto, no con una
  verdad absoluta.
- **Sobredetección del leucograma de estrés.** El modelo tendió a asignar este patrón en casos
  donde el evaluador no lo hizo, produciendo falsos positivos; es una señal de sensibilidad alta
  que conviene comunicar como orientación, no como diagnóstico.
- **Policitemia conservadora.** Esta etiqueta mostró especificidad muy alta pero sensibilidad
  menor frente al criterio clínico, es decir, una tendencia del modelo a ser conservador y omitir
  algunos casos (falsos negativos).
- **Los agregados plaquetarios funcionan mejor como regla determinista.** El control de calidad de
  agregados plaquetarios resultó más fiable implementado como regla determinista que como salida
  del modelo, lo que llevó a mantenerlo fuera del clasificador estadístico.
- **Los usuarios validaron indirectamente decisiones del sistema.** En la encuesta de usabilidad,
  varias mejoras solicitadas (mayor velocidad y memoria del chat) confirmaron limitaciones ya
  conocidas, y la duda de algunos usuarios sobre si las fuentes citadas por el asistente eran
  reales resultó ser infundada: la validación veterinaria confirmó que las fuentes son reales y
  pertinentes.

## 7.5. Recomendaciones

A partir de las limitaciones y los hallazgos, se proponen las siguientes líneas de trabajo futuro:

**Sobre la validación:**

- Ampliar la validación clínica con más clínicas, más casos y entre cuatro y siete evaluadores;
  ampliar la rúbrica de contenido del asistente a ≥100 preguntas.
- Recalibrar las etiquetas con mayor desacuerdo clínico (leucograma de estrés, policitemia,
  hemólisis/MCHC) y reforzar el soporte de las etiquetas exploratorias.
- Incorporar un diseño pareado ciego que compare las respuestas del asistente con respuestas
  redactadas por veterinarios.

**Sobre el producto:**

- Mejorar la extracción de reticulocitos y de morfología para robustecer las etiquetas eritroides.
- Separar un **modo ciudadano** y un **modo veterinario**, con distinto nivel de detalle y alcance.
- Optimizar la latencia del asistente (GPU o modelo más eficiente) y dar al chat memoria
  conversacional y mayor velocidad, las dos mejoras más solicitadas por los usuarios.
- Atender las mejoras de usabilidad priorizadas: leyenda de colores fija y rangos normales junto a
  los valores, exportación del resultado por WhatsApp o correo, modo de alto contraste, corrección
  del *tour* de bienvenida (que no se iniciaba) y un glosario para unidades y tecnicismos.

**Sobre la vigilancia:**

- Convertir la vigilancia poblacional en un módulo epidemiológico solo bajo protocolos formales,
  con geocodificación efectiva, umbrales de privacidad revisados y cobertura territorial ampliada.

## 7.6. Puesta en funcionamiento e implementación de la plataforma

HemoVet no quedó como un prototipo de laboratorio, sino como una plataforma **desplegada y
operativa en un entorno de producción controlado**. El sistema se ejecuta sobre una máquina
virtual de despliegue (`hemovet-prod`) mediante una arquitectura **contenerizada con Docker**,
que orquesta de forma conjunta el backend (FastAPI servido con Uvicorn, con la API versionada en
`/api/v1`), la base de datos PostgreSQL, el índice vectorial ChromaDB, el servidor de modelo de
lenguaje Ollama, el frontend web en React y un *reverse proxy* Caddy como punto de entrada. Esta
separación en servicios permite reproducir el entorno completo entre máquinas con un único comando
de orquestación, a partir de una configuración base y una superposición específica de producción.

La puesta en funcionamiento está **automatizada mediante integración y despliegue continuos**:
cada cambio incorporado a la rama principal dispara una canalización que valida la configuración,
construye las imágenes y despliega la nueva versión al servidor productivo por SSH, con manejo de
errores y registro sanitizado por servicio. Esto reduce la intervención manual y hace repetible la
operación de la plataforma.

El estado final del sistema quedó registrado como **listo para producción con limitaciones**
(READY_FOR_PRODUCTION_WITH_LIMITATIONS), condición que indica que la plataforma es funcional y
desplegable para escenarios controlados y de demostración, con las limitaciones documentadas en
la sección 7.3. El flujo operativo completo fue verificado de extremo a extremo: registro y
autenticación del usuario (con modo invitado disponible), carga del hemograma, extracción
automática de valores, **revisión humana obligatoria**, clasificación por el modelo,
presentación del resultado orientativo, y acceso al historial, al asistente conversacional, a la
biblioteca y al módulo de vigilancia.

La preparación operativa se sustenta en evidencia técnica: la batería de pruebas del backend se
ejecuta sin fallos (25 pruebas superadas) y el motor de inferencia responde con una latencia
media de 28.73 ms, muy por debajo del umbral interactivo. La única restricción operativa
relevante en el despliegue actual es que el modelo de lenguaje se ejecuta **sobre CPU, sin
acelerador gráfico**, lo que eleva el tiempo de respuesta del asistente conversacional; el resto
del sistema opera en tiempos adecuados para uso interactivo. La incorporación de una GPU o de un
modelo más eficiente, señalada en las recomendaciones, resolvería esta restricción sin cambios de
arquitectura.

## 7.7. Sostenibilidad de la plataforma

La continuidad técnica de HemoVet se apoya en decisiones de arquitectura orientadas a la
reproducibilidad y el mantenimiento:

- **Despliegue contenerizado con Docker**, que reproduce el entorno completo (backend, base de
  datos, Chroma y Ollama) de forma consistente entre máquinas.
- **Persistencia con PostgreSQL y migraciones versionadas con Alembic**, que permiten evolucionar
  el esquema de datos sin pérdida ni intervención manual.
- **Corpus RAG versionado** e ingesta offline de Markdown curado, de modo que la base de
  conocimiento del asistente sea auditable y actualizable.
- **Integración y despliegue continuos (CI/CD)** y una batería de pruebas de backend, que protegen
  contra regresiones al incorporar cambios.
- **Auditoría de artefactos del modelo** —hashes, congelamiento de umbrales y manifiestos de
  versión— que garantizan la trazabilidad de cada versión desplegada.
- **Copias de seguridad de modelos y de datos anonimizados**, que preservan la evidencia y
  permiten recuperar estados previos.

Estas prácticas hacen que el sistema sea mantenible y extensible por un equipo distinto al que lo
construyó, condición necesaria para que HemoVet trascienda el ámbito del proyecto de grado y pueda
evolucionar hacia un servicio sostenido.
