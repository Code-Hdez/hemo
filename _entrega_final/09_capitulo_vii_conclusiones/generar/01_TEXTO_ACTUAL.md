# Capítulo VII — TEXTO ACTUAL, ÍNTEGRO Y VERBATIM

> Extraído de `P1 ICC 1910 — … (4).docx` el 12 de agosto de 2026. Es el texto que hay que
> modificar. Se han desescapado los artefactos de conversión y las imágenes se han sustituido por
> marcadores `[FIGURA imageNN]`; los pies de figura se conservan tal cual.
>
> **No se ha alterado ninguna palabra del contenido.** Los errores y las cifras desactualizadas que
> contiene son deliberados: son precisamente los que hay que corregir.

---

# **Capítulo VII - Conclusiones y recomendaciones** 

## **7.1. Conclusiones** 

Se alcanzó el objetivo general y el proyecto dio lugar a la creación de HemoVet, una plataforma web orientada al ciudadano que permite integrar la clasificación multietiqueta de patrones hematológicos a partir de hemogramas completos caninos, una capa de conversación y medidas de seguridad, y un panel de orientación con historial y vigilancia comunitaria. El sistema identifica patrones en la información hematológica de interés, comunica los resultados en un lenguaje comprensible para el propietario de la mascota, permite el control de calidad de la lectura, permite la visualización de la información tanto a nivel individual como comunitario y, como condición transversal, los resultados del sistema no deben sustituir el criterio del veterinario.

La conclusión final del proyecto es que tres niveles de responsabilidad (el entrenamiento del modelo, la implementación de la inferencia del modelo y la comunicación con el usuario) son esenciales para convertir la interpretación de los hemogramas completos caninos, basada en orientaciones, en un flujo de trabajo computacional más formal. El motor de clasificación procesa valores tabulares y artefactos congelados; el backend se encarga de las reglas determinísticas, la validación de entradas y la persistencia; y el módulo LLM/RAG proporciona explicaciones de los resultados previamente estructurados, pero no formula afirmaciones diagnósticas ni terapéuticas. Esta separación permitió establecer una trazabilidad técnica y unos límites clínicos explícitos para el sistema.

Los resultados obtenidos se utilizan para evaluar el proyecto desde cuatro perspectivas: técnica, clínica, conversacional y de usabilidad.. Desde el punto de vista técnico, el motor de clasificación obtuvo muy buenos resultados en el conjunto de prueba, con un PR-AUC macro de 0.9529, un F1 macro de 0.8727 y un recall macro de 0.9205. Una validación clínica del modelo (dos veterinarios, 509 casos evaluables) indicó que el modelo tiene una precisión similar a la de la concordancia entre evaluadores y presenta un kappa de 0.629 con el veterinario 1, en comparación con un kappa de 0.684 entre los dos veterinarios. El módulo LLM/RAG se probó utilizando el flujo de trabajo real y con la participación de dos veterinarios; en un conjunto de 30 respuestas clínicamente seguras obtenidas en ambas pruebas, el 83.3 % de las respuestas fueron correctas o parcialmente correctas, y no se detectaron alucinaciones en el conjunto de prueba.

También se ha constatado que HemoVet resuelve con éxito el problema de comunicación identificado en el proyecto. Se llevó a cabo una validación de la usabilidad con 44 usuarios, en su mayoría no especializados, que arrojó un índice de usabilidad de 84/100, un 81,6 % de respuestas positivas y un 0 % de respuestas negativas. El resultado sugiere que la interfaz y el lenguaje utilizados facilitan que los usuarios no clínicos interpreten el flujo de trabajo como comprensible y beneficioso para su preparación de cara a una consulta con un veterinario.

En general, el sistema está listo para ser presentado y utilizado con restricciones. Esto no debe considerarse como una certificación clínica ni una autorización para el diagnóstico clínico, sino más bien como una prueba de que el prototipo funcional ha alcanzado la madurez suficiente para pasar a la siguiente fase de validación clínica ampliada, optimización del producto y despliegue supervisado.

## **7.2. Resultados de los objetivos planteados** 

La evaluación del cumplimiento de los objetivos se realizó comparando cada objetivo específico con las pruebas obtenidas durante el desarrollo, la validación técnica, la validación clínica, la evaluación conversacional y la validación de usabilidad. Esta relación se resume en la Tabla 7.1.

| Objetivo específico | Evidencia principal | Estado |
| :---- | :---- | :---- |
| OE1. Conformar un conjunto de datos clínico estructurado a partir de registros hematológicos caninos de clínicas locales y del Dog Aging Project, sometido a limpieza, imputación y estandarización. | Corpus IDEXX curado, cohorte externa DAP de 1,301 registros, 43 características hematológicas y artefactos de datos versionados. | Cumplido |
| OE2. Construir un modelo de aprendizaje automático de clasificación multietiqueta capaz de predecir anomalías hematológicas específicas a partir de valores tabulares del hemograma. | Modelo XGBoost multilabel con siete etiquetas oficiales, PR-AUC macro de 0.9529, F1 macro de 0.8727, recall macro de 0.9205 y validación clínica con kappa de 0.629 frente al Veterinario 1. | Cumplido con limitaciones |
| OE3. Desarrollar un portal web ciudadano que consuma el motor de clasificación y presente resultados comprensibles, historial y orientación explícita hacia consulta veterinaria. | Aplicación Web con resumen, carga de hemograma, revisión de valores, resultado interpretativo, historial, biblioteca, chat y validación de usabilidad con n \= 44 e índice 84/100. | Cumplido |
| OE4. Realizar un módulo de vigilancia comunitaria sobre zonas agregadas, con resguardo de privacidad y advertencias metodológicas. | Módulo de vigilancia con señales agregadas, reporte poblacional funcional y advertencias de que no representa prevalencia ni diagnóstico confirmado. | Cumplido como exploratorio |
| OE5. Implementar una capa de explicación conversacional basada en un modelo de lenguaje con guardrails, sin emitir diagnósticos, tratamientos ni dosis. | Asistente LLM/RAG con corpus curado, guardrails, seguridad 30/30, exactitud correcta o parcial de 83.3 %, concordancia veterinaria de kappa 0.841 y reducción de prompt injection de 61 a 1 fallo tras refuerzo. | Cumplido |

*Tabla 7.1. Cumplimiento de los objetivos específicos y evidencia de respaldo.*

Se considera que se han cumplido los cinco objetivos específicos. El OE2 se declara alcanzado con limitaciones, ya que algunas etiquetas presentan menor certeza debido a un respaldo limitado o a una mayor ambigüedad clínica, especialmente en el caso del patrón de anemia regenerativa.

## **7.3. Limitaciones** 

El proyecto presenta algunas limitaciones que deben tenerse en cuenta para evitar una interpretación errónea de los resultados del mismo. Los aspectos limitados de estos sistemas no los hacen inútiles como sistemas de orientación, pero delimitan el alcance técnico, clínico y operativo de los mismos.

La primera limitación es que el sistema se restringe a la especie canina. La información, las reglas, los intervalos de referencia, las etiquetas y las validaciones se han creado para perros. Por lo tanto, el sistema no puede aplicarse a gatos, caballos, personas ni a ninguna otra especie sin un nuevo proceso de recopilación de datos, etiquetado, entrenamiento y validación.

En segundo lugar, la calidad y la exhaustividad del hemograma completo de entrada son fundamentales para HemoVet. Para la extracción y la clasificación se utilizan valores tabulares, por lo que la inferencia podría verse afectada por una transcripción incorrecta de un valor, una conversión errónea de una unidad, un formato PDF no compatible o un error de lectura. Por ello, los valores obtenidos deben ser revisados por una persona antes de obtener el resultado.

En tercer lugar, algunas etiquetas carecen de respaldo estadístico. Se registraron seis casos positivos en el conjunto de prueba para la etiqueta anemia regenerativa. Se añadió a la lista de resultados oficiales con bajo respaldo debido a su importancia clínica; sin embargo, debería indicarse como un resultado exploratorio y no como un resultado convergente. Es necesario reducir esta restricción añadiendo más casos de anemia regenerativa clínicamente probados.

En cuarto lugar, las etiquetas del Dog Aging Project no eran compatibles con el esquema de HemoVet. Como resultado, se pudieron analizar las tasas de activación para esta cohorte, al igual que la consistencia biológica, pero no fue posible calcular el F1, el PR-AUC ni otras métricas supervisadas para esta fuente. La validación externa debe interpretarse como una prueba de comportamiento fuera del dominio y no como una prueba diagnóstica supervisada.

En quinto lugar, la validación clínica se llevó a cabo en un entorno local por parte de dos veterinarios. El número de evaluadores y el número de casos evaluados no es lo suficientemente amplio, y los casos no proceden de una población lo suficientemente amplia como para que los resultados de este estudio sean generalizables. Además, la concordancia entre evaluadores no fue del 100 %, lo que demuestra que el juicio clínico humano también puede variar y que, en futuras validaciones, debería aumentarse el número de clínicas, evaluadores y protocolos ciegos.

En sexto lugar, el módulo conversacional se ha sometido a una validación piloto. Para la evaluación veterinaria del asistente se utilizaron dos evaluadores y 30 preguntas sobre hematología canina. Los resultados fueron positivos en cuanto a la seguridad y la ausencia de preguntas capciosas, aunque es importante contar con un conjunto más amplio de preguntas, evaluadores y una comparación con las respuestas escritas por veterinarios para tener mayor confianza en la validez clínica.

Por último, la validación de la usabilidad se llevó a cabo en lo que respecta a la percepción y se trató de una muestra de conveniencia. El instrumento permitió medir la claridad, la utilidad y la comprensión percibidas, pero no incluyó mediciones de tareas cronometradas, tasas de error observadas ni comparaciones con otro sistema. En consecuencia, el índice de usabilidad debe considerarse como un indicio de aceptación inicial y no como un certificado formal de la experiencia del usuario.

## **7.4. Resultados inesperados o no planificados** 

A medida que el sistema se desarrollaba y validaba, se descubrió que se producían algunos acontecimientos inesperados que aportaban información para la evolución del sistema. El primero fue la gran variabilidad de las opiniones de los veterinarios. El valor kappa entre evaluadores de 0.684 mostró que las discrepancias entre el modelo y los evaluadores no significan necesariamente que haya un error en el algoritmo, sino más bien que existen diferencias legítimas en la interpretación hematológica. Este hallazgo debía validarse clínicamente para interpretarse como una comparación con el juicio variable humano y no como una única verdad absoluta.

El segundo hallazgo fue que se detectaban en exceso los leucogramas de estrés. El modelo tendía a activar esta etiqueta cuando el evaluador humano no lo hacía, lo que daba lugar a falsos positivos. Esto puede considerarse una respuesta de alta sensibilidad ante configuraciones compatibles con el estrés, pero debe equilibrarse al hablar con los propietarios para evitar alarmas innecesarias.

El tercer hallazgo fue que la etiqueta de policitemia resultó ser conservadora en comparación con el juicio clínico. Sin embargo, la etiqueta presentó mayor especificidad que sensibilidad en la validación clínica, lo que significa que el modelo pasó por alto algunos casos positivos identificados por el evaluador. Esta situación debe corregirse mediante la recalibración de los umbrales y el aumento del número de casos positivos.

El cuarto hallazgo fue que algunos de los controles de calidad resultaban más eficaces cuando se aplicaban como reglas deterministas en lugar de como resultados estadísticos. En el caso de los agregados plaquetarios, algunos de estos eventos resultaban más fiables cuando se resolvían mediante reglas explícitas, debido a su asociación directa con las condiciones de medición o con artefactos de laboratorio. Esto subraya la necesidad de combinar el aprendizaje automático con una lógica clínica adecuada que pueda verificarse.

El quinto hallazgo procedió de la evaluación de la usabilidad. Los usuarios deseaban agilizar el chat y facilitar la memoria conversacional, en consonancia con las limitaciones ya observadas por el equipo. También surgieron cuestiones sobre la autenticidad de las fuentes mencionadas por el asistente, y se señaló que, si bien el sistema RAG recupera documentos válidos, la interfaz debería comunicar mejor la trazabilidad de las fuentes y su papel en la respuesta.

## **7.5. Recomendaciones** 

Desde un punto de vista clínico, se sugiere que la validación se amplíe a más veterinarios, clínicas veterinarias y casos. Las etiquetas que muestran un mayor desacuerdo clínico (leucograma de estrés, hemólisis/MCHC, policitemia, anemia regenerativa) deberían revisarse con protocolos de consenso basados en casos confirmados. También se recomienda utilizar un diseño de evaluación por pares y a ciegas, en el que se evalúen los resultados del sistema y la interpretación humana sin ningún sesgo de orden ni conocimiento previo.

El corpus debería ampliarse con casos positivos de las clases menos frecuentes de anemia no regenerativa, anemia regenerativa y policitemia, para mejorar el motor de clasificación. Deberían mantenerse los intervalos de confianza de bootstrap, la comprobación del soporte estadístico de cada etiqueta y la fijación de los umbrales antes de la evaluación final. El modelo de la nueva versión debe generar los manifiestos, los hash de los artefactos y los informes de comparación con la versión anterior.

Se sugiere que el número de preguntas de evaluación se incremente también hasta un mínimo de 100, que participen más evaluadores y que se añadan los criterios de evaluación de seguridad, precisión, idoneidad de las citas y utilidad para los usuarios. Asimismo, se sugiere que se mejore la presentación de las fuentes en la interfaz para dejar claro a los propietarios que las respuestas son generadas por el modelo a partir de documentos seleccionados y bajo restricciones de seguridad.

Deberían considerarse para su implementación las siguientes mejoras en la experiencia del usuario, identificadas durante la encuesta, con el fin de que la aplicación resulte más fácil de usar: 1\) aumentar la velocidad del chat, 2\) añadir una memoria conversacional controlada, 3\) fijar la leyenda de colores en su lugar, 4\) añadir rangos normales a los valores, 5\) añadir una función de exportación a través de WhatsApp o correo electrónico, 6\) añadir un modo de alto contraste, 7\) mejorar el recorrido de bienvenida, 8\) ampliar el glosario de unidades y términos técnicos.

Por último, en el contexto de futuros proyectos derivados, se sugiere investigar dos usos alternativos: un modo de uso para ciudadanos, destinado a la explicación, la orientación y la redacción de preguntas para la consulta, y un modo veterinario con contenido más técnico, trazabilidad de variables y revisión profesional. Dicha separación garantizaría la seguridad de los usuarios no expertos, al tiempo que maximizaría el valor de este sistema para los usuarios clínicos.

## **7.6. Puesta en funcionamiento e implementación de la plataforma** 

HemoVet no se limitó a ser un prototipo conceptual. Se desarrolló como un sistema funcional y operativo, en un entorno de producción controlado y con servicios independientes y una implementación reproducible. La arquitectura se ha implementado mediante contenedores Docker que ejecutan el backend de FastAPI, la base de datos PostgreSQL, el índice vectorial ChromaDB, el servidor de modelos de lenguaje Ollama y el frontend web basado en React.

La API funcional se encuentra en /api/v1 y las comprobaciones de estado operativas se mantienen por separado para facilitar la supervisión y el diagnóstico de problemas técnicos. El backend utiliza artefactos de modelos que ya han sido entrenados y congelados, aplica reglas deterministas, valida los datos de entrada, almacena los resultados y proporciona los servicios necesarios para llevar a cabo análisis hematológicos, datos de mascotas, historial, seguimiento y chat.

Se ha probado de principio a fin todo el flujo de trabajo operativo. Los usuarios pueden registrarse, iniciar sesión o continuar como invitados, cargar un hemograma completo, ejecutar la extracción automática de valores, comprobar los datos detectados, confirmar el análisis, ver el resultado orientativo, consultar el historial, utilizar el asistente de conversación, consultar la biblioteca y ver la vigilancia agregada. Un control crítico para minimizar los errores de extracción es la revisión humana obligatoria previa al análisis.

El estado del sistema quedó registrado como listo para producción con limitaciones. Esta condición significa que la plataforma está operativa y lista para su despliegue y demostración de uso controlado, tal y como se indica en este capítulo. Las pruebas técnicas de la preparación operativa incluyen: 25 pruebas superadas en el backend, una latencia media de inferencia de 28.73 ms y la validación funcional de los mecanismos de seguridad. La limitación más relevante en términos de funcionamiento está relacionada con la generación conversacional, ya que el modelo de lenguaje se ejecuta sin aceleración GPU, lo que da lugar a tiempos de respuesta más lentos en el chat.

La implementación debe realizarse de forma gradual. El primer paso consiste en realizar una demostración en el ámbito académico y llevar a cabo pruebas bajo supervisión. Una segunda fase debería incluir la supervisión de errores, el registro de eventos, la revisión de las conversaciones y los comentarios de los usuarios. Una tercera fase, previa a la ampliación del uso clínico, debe incluir la validación multicéntrica, acuerdos formales con las clínicas, consideraciones sobre la privacidad y la aprobación institucional de la gestión de datos.

## **7.7. Sostenibilidad de la plataforma** 

La reproducibilidad, el mantenimiento y la evolución controlada son las decisiones arquitectónicas que permiten la sostenibilidad técnica de HemoVet. Docker permite que los distintos servicios se ejecuten de forma coherente en diferentes entornos, PostgreSQL proporciona persistencia y Alembic se encarga de la gestión de la migración. Además, el uso de una API versionada minimiza el riesgo de fallos si se añaden nuevas funciones.

La parte de IA también se diseñó para ser duradera. Los artefactos del modelo, las columnas de entrada, las medianas de imputación, los umbrales, los calibradores y la política de etiquetado están documentados en el contrato operativo del sistema. Todas las actualizaciones futuras deben generarse con nuevos manifiestos, compararse con la versión anterior y validarse técnicamente antes de su implementación.

Es importante que el módulo conversacional sea sostenible, lo que requiere una curación continua del corpus RAG. La base de conocimientos debe plasmarse en documentos versionados y ser revisada y aprobada antes de su incorporación. La indexación fuera de línea garantizará que los documentos no validados no se incluyan en el flujo de trabajo de respuestas, y la supervisión de las fuentes permitirá identificar qué fragmentos respaldan cada resultado generado.

Para la sostenibilidad operativa, son necesarias copias de seguridad, la supervisión del estado del servicio, las actualizaciones de dependencias, la revisión de las advertencias técnicas y la automatización de las pruebas. Las alertas que aparecen durante las pruebas no suponen un obstáculo para un uso controlado, pero deben tenerse en cuenta para evitar la deuda técnica, especialmente en lo que respecta a las dependencias, el manejo de fechas y la compatibilidad futura.

Para lograr la sostenibilidad clínica, es esencial mantener la advertencia de que el sistema no sustituye la evaluación ni el criterio veterinario, seguir validando el sistema con casos reales y evitar que se mezclen las orientaciones y el diagnóstico. Cuando el sistema se utilice en clínicas o sea accesible para usuarios externos, deben crearse protocolos que abarquen todos los aspectos relacionados con el consentimiento, la anonimización, la gestión del acceso, el almacenamiento de datos y las evaluaciones periódicas del rendimiento.

Por último, HemoVet ofrece una plataforma sostenible para el desarrollo continuo hacia una plataforma de orientación hematológica más madura si continúa creciendo, respaldada por la validación clínica, el soporte técnico, las actualizaciones del corpus conversacional y una gobernanza responsable de los datos.
