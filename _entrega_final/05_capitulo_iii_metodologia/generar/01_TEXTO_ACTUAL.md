# Capítulo III — TEXTO ACTUAL, ÍNTEGRO Y VERBATIM

> Extraído de `P1 ICC 1910 — … (4).docx` el 12 de agosto de 2026. Es el texto que hay que
> modificar. Se han desescapado los artefactos de conversión y las imágenes se han sustituido por
> marcadores `[FIGURA imageNN]`; los pies de figura se conservan tal cual.
>
> **No se ha alterado ninguna palabra del contenido.** Los errores y las cifras desactualizadas que
> contiene son deliberados: son precisamente los que hay que corregir.

---

# **Capítulo III - Metodología** 

El desarrollo de HemoVet se llevó a cabo como un proyecto de ingeniería de software aplicada e inteligencia artificial con el objetivo de crear una plataforma de software operativa para la interpretación inicial del hemograma completo de un perro. La metodología seguida integró un sistema web reproducible, un motor de clasificación multietiqueta para datos tabulares, reglas determinísticas de control de calidad y una capa conversacional con restricciones basada en la generación aumentada por recuperación.

El trabajo se realizó con un enfoque cuantitativo y tecnológico. La parte cuantitativa queda ilustrada en la construcción del corpus hematológico, la definición de variables, el etiquetado multietiqueta, la partición temporal, la evaluación del modelo y la validación externa. El aspecto tecnológico también se hace patente en la adopción de un diseño backend/frontend, la persistencia en la base de datos, la orquestación de contenedores, la API versionada y el módulo LLM/RAG. La metodología no se diseñó para ser una revisión conceptual, sino un método para construir, probar y combinar componentes funcionales.

La secuencia de trabajo tenía como objetivo evitar la fuga de información durante el proceso de entrenamiento y evaluación, distinguir entre el entrenamiento offline y la inferencia online, y mantener un registro de los artefactos utilizados por la plataforma. Con este fin, todas las decisiones relevantes del modelo se documentaron antes de la evaluación final mediante archivos de políticas, congelación de umbrales, manifiestos de artefactos y métricas versionadas.

[FIGURA image5]

*Figura 3.1. Diseño metodológico aplicado durante el desarrollo de HemoVet.*

## **3.1. Tipo de proyecto y enfoque metodológico** 

HemoVet se trata de un proyecto tecnológico aplicado, ya que su objetivo era crear y validar una solución informática para un problema concreto: transformar los datos numéricos del hemograma completo (CBC) de un perro en patrones preliminares y explicaciones informativas para el propietario del animal. La investigación no se limitó a una descripción conceptual del problema, sino que condujo a la creación de un artefacto funcional que incluye un backend, un frontend, una base de datos, un motor de inferencia, reglas deterministas, reglas fundamentadas en la literatura y un chat LLM/RAG.

El método utilizado fue una combinación de enfoque cuantitativo con un enfoque de ingeniería de software. La dimensión cuantitativa se centró en los datos hematológicos y la evaluación de los modelos, mientras que la dimensión de ingeniería se centró en la construcción reproducible de la plataforma. Ambos métodos permitieron validar la precisión del modelo, así como poner a prueba su capacidad para integrarse en un flujo de trabajo real para la autenticación, la carga del hemograma completo, la revisión de valores, la persistencia del análisis y las explicaciones controladas.

El concepto clave del diseño metodológico consistió en diferenciar tres niveles de responsabilidad. El primer nivel consiste en procesar los datos y entrenar el modelo, lo cual se lleva a cabo en el sistema fuera de producción. El segundo nivel representa el despliegue del modelo como servicio de inferencia en el backend. El tercer nivel es la comunicación con el usuario: el modelo de lenguaje no diagnostica ni toma decisiones, sino que explica la información que ha sido estructurada por el sistema.

## **3.2. Metodología de desarrollo del software** 

El proceso de desarrollo de software fue incremental y se basó en entregables. La plataforma se diseñó como un conjunto de dominios funcionales: Autenticación, Usuarios, Mascotas, Historial, Hematología, Inferencia, Vigilancia poblacional, Mapas, Extracción asistida y chat LLM/RAG. Esta división les permitió probar, realizar cambios e implementar cada parte del sistema sin afectar al sistema en su conjunto.

El backend se ha desarrollado utilizando el control de versiones de la API: /api/v1. Esto permitió estabilizar los contratos HTTP, separar los endpoints funcionales de los endpoints de comprobación del estado operativo y preparar la plataforma para futuras ampliaciones sin comprometer la compatibilidad con versiones anteriores de los clientes existentes. La persistencia se implementó con: PostgreSQL, SQLAlchemy 2 y Alembic, los cuales proporcionaron la capacidad de realizar cambios en el esquema mediante migraciones repetibles.

El frontend se ha creado como una aplicación web específica para los propietarios. Se diseñó para utilizar los servicios del backend, mostrar el proceso completo de carga y revisión de CBC, compartir el análisis y la visualización completos de los resultados, permitir consultas conversacionales y proporcionar una representación visual de los datos históricos o agregados. Toda la lógica crítica de validación, inferencia y seguridad se mantuvo en el código del servidor, y el navegador no se encargaba de la toma de decisiones clínicas.

Se utilizó Docker Compose como medio para garantizar la reproducibilidad del sistema. Se dispuso de diferentes configuraciones para desarrollo, control de calidad, ejecución en GPU y producción. Este enfoque permitió el despliegue de servicios dependientes, como la base de datos, el backend, el frontend, ChromaDB, Ollama y la ingesta del corpus RAG, en condiciones controladas. Se utilizaron variables de entorno y secretos para mantener la configuración sensible fuera del repositorio.

| Componente | Método aplicado | Resultado metodológico |
| :---: | :---: | :---: |
| Backend | API modular versionada bajo /api/v1 | Contratos estables para análisis, extracción, mascotas, historial, vigilancia y chat |
| Persistencia | PostgreSQL, SQLAlchemy 2 y Alembic | Esquema trazable y migraciones reproducibles |
| Frontend | React 18, Vite y TypeScript | Interfaz web orientada al propietario |
| Inferencia | Artefactos de modelo cargados por el backend | Separación entre entrenamiento offline e inferencia online |
| RAG | ChromaDB, FastEmbed, Ollama y Markdown curado | Explicación controlada con recuperación semántica |
| Despliegue | Docker Compose con overlays | Ejecución reproducible en local, QA, GPU y producción |

 

*Tabla 3.1. Estrategia metodológica aplicada al desarrollo del software.*

### **3.2.1. Control de versiones, pruebas y despliegue** 

El control de versiones se hizo con Git y repositorio institucional. Los datos clínicos sensibles se separaron del código fuente, la documentación técnica y los manifiestos de configuración. La decisión se tomó bajo el principio de minimización de datos y permitiría auditar el código al tiempo que se mantiene la confidencialidad de la información de los pacientes y los propietarios.

La validación técnica comprendió pruebas de backend, pruebas de frontend, verificación de la compilación y pruebas operativas. Las pruebas de backend abarcaron rutas, contratos, autenticación, persistencia, gestión de errores, etc. La verificación del frontend incluyó flujos de trabajo de interacción críticos, compilaciones del proyecto, tipos y componentes. Solo tras las pruebas, la validación del corpus RAG, la disponibilidad del servicio y los smoke tests posteriores al despliegue se autorizó el despliegue en producción.

La metodología de implementación tuvo en cuenta la necesidad de mantener el sistema en funcionamiento sin tener que reconfigurarlo repetidamente de forma manual. Por ello, se utilizaron archivos Compose, variables de entorno, migraciones automáticas y comprobaciones de disponibilidad. Esto dio lugar a una plataforma que puede replicarse en una topología local o de producción y que, aun así, conserva la diferencia entre los entornos local y de producción.

## **3.3. Metodología de construcción del corpus hematológico** 

El corpus de trabajo se construyó a partir de dos corpus diferentes con distintas funciones metodológicas. La fuente principal fue el conjunto de datos de hemogramas completos de IDEXX ProCyte One, que se utilizó para el entrenamiento, la validación y las pruebas del modelo. La segunda fuente fue el Dog Aging Project, creado exclusivamente para la validación externa del dominio. Esta separación era necesaria, ya que ambas fuentes procedían de poblaciones diferentes y utilizaban instrumentos distintos, y no debían combinarse para ajustar el modelo.

En el conjunto de datos de IDEXX había 2,454 registros de perros procesables. Estos registros se utilizaron para crear etiquetas supervisadas mediante el campo idexx_comments, y el vector de entrada del modelo se creó únicamente a partir de las variables numéricas y de las variables calculadas a partir del hemograma completo. El conjunto de datos del DAP aportó 1,301 registros y se utilizó para observar las tasas de activación del modelo en una muestra externa, en su mayor parte sana y, por el momento, geográficamente diferente.

Los procedimientos utilizados para la construcción del corpus fueron: extracción, normalización, estandarización e imputación. Los campos identificadores y variables con información personal no se incluyeron en el vector de entrenamiento. Para evitar fugas temporales o un aprendizaje espurio de la procedencia, no se incluyeron las variables de procedencia, fecha y fuente. Se utilizaron parámetros hematológicos clínicamente relevantes para derivar algunas variables, tales como indicadores binarios, índices hematológicos y variables relacionadas con los reticulocitos.

| Fuente | Registros | Uso metodológico | Tratamiento dentro del proyecto |
| :---: | :---: | :---: | :---: |
| IDEXX ProCyte One | 2,454 | Entrenamiento, validación y prueba | Fuente principal para labels y features |
| Dog Aging Project | 1,301 | Validación externa de dominio | No se utilizó para entrenamiento ni ajuste de umbrales |

 

*Tabla 3.2. Fuentes de datos utilizadas en la metodología.*

*[FIGURA image6]*

*Figura 3.2. Flujo metodológico seguido para el componente de inteligencia artificial.*

### **3.3.1. Limpieza, estandarización e imputación** 

El objetivo de la limpieza de datos era convertir los registros hematológicos en una matriz tabular, adecuada para el entrenamiento. Se normalizaron los nombres de las variables, las unidades, los tipos de datos y las codificaciones internas. El vector de entrada no incluía variables no numéricas ni variables con riesgo de fuga de información. La imputación de valores faltantes se ajustó únicamente con el conjunto de entrenamiento y luego se aplicó a validación, prueba y producción, evitando usar información futura durante el ajuste.

El método realizó una separación entre datos faltantes, datos fisiológicamente extremos y errores de extracción. No se eliminaron automáticamente los valores extremos, ya que en los datos clínicos estos pueden corresponder a pacientes verdaderamente patológicos. En su lugar, se destinaron al control de calidad y a la revisión metodológica. Esta decisión evitó la reducción de la variación clínica del corpus mediante medios artificiales.

### **3.3.2. Ingeniería de características** 

El hemograma completo se transformó en un conjunto de variables más informativo para la clasificación multietiqueta mediante ingeniería de características. El modelo v3 incluía 43 características, entre las que se encontraban analitos directos del hemograma completo, indicadores clínicos, índices hematológicos y variables asociadas a los reticulocitos. La incorporación de los reticulocitos permitió volver a añadir la etiqueta PATRON_ANEMIA_REGENERATIVA como resultado de bajo soporte, con una advertencia metodológica.

Las variables derivadas se eligieron para reflejar relaciones hematológicas pertinentes que no están necesariamente representadas de forma directa por las variables individuales. Entre ellas se incluían marcadores de trombocitopenia, anemia, leucocitosis, linfopenia, neutrofilia, índices inflamatorios y marcadores de respuesta de la médula ósea. Los comentarios de IDEXX y los indicadores H/L del analizador no se utilizaron como entradas del modelo, ya que estaban directamente relacionados con el proceso de etiquetado; este principio se siguió en la selección de características.

## **3.4. Metodología de etiquetado multilabel** 

El campo idexx_comments se utilizaría para el etiquetado supervisado, ya que es un campo que contiene comentarios interpretativos del analizador. No se trata de un campo que utilizáramos para la predicción, sino más bien como fuente de etiquetas. Esto permitió al modelo aprender la relación entre las variables numéricas del hemograma y las etiquetas derivadas de los comentarios del analizador, sin que se le indicará el texto real que había generado las etiquetas.

La tarea se formuló como un problema de clasificación multietiqueta, ya que puede haber múltiples patrones en un único hemograma completo. Por ejemplo, un caso podría activar simultáneamente etiquetas de inflamación, anemia y control de calidad. Por estas razones, se descartó una formulación multiclase, ya que se perdería la información clínicamente relevante y se seleccionaría una única categoría.

La política de etiquetas final utilizó siete etiquetas oficiales del modelo, dos etiquetas determinadas por reglas deterministas y una etiqueta que no se incluyó en la política debido a errores históricos y no recurrentes. Esta política se fijó y documentó antes de que se consolidaran los resultados finales.

| Etiqueta | Método de salida | Estado | PR-AUC test |
| :---: | :---: | :---: | :---: |
| QC_REQUIERE_FROTIS | Modelo probabilístico | official | 0.8605 |
| PATRON_INFLAMATORIO | Modelo probabilístico | official | 0.9936 |
| PATRON_LEUCOGRAMA_ESTRES | Modelo probabilístico | official | 0.9861 |
| PATRON_ANEMIA_NO_REGENERATIVA | Modelo probabilístico | official | 0.9853 |
| PATRON_HEMOLISIS_MCHC | Modelo + postprocesamiento | official | 0.9924 |
| PATRON_POLICITEMIA | Modelo probabilístico | official_promoted | 1.0000 |
| PATRON_ANEMIA_REGENERATIVA | Modelo probabilístico | official_low_support | 0.8860 |
| QC_AGREGADOS_PLAQUETARIOS | Regla determinística | rule_based | - |
| QC_INTERFERENCIA_GR | Regla determinística | rule_based | - |
| QC_UNIDAD_NO_CONVERTIDA | Excluida | documented_limitation | - |

 

*Tabla 3.3. Política final de etiquetas del sistema HemoVet.*

*[FIGURA image7]*

*Figura 3.3. Distribución de la política final de etiquetas.*

## **3.5. Entrenamiento, calibración y congelamiento del modelo** 

El entrenamiento se realizó con XGBoost y relevancia binaria (un clasificador independiente por etiqueta). La estrategia utilizada era adecuada para el problema multietiqueta, ya que permitía ajustar el umbral y evaluar el rendimiento de forma individual para cada patrón hematológico. Se implementaron el aprendizaje sensible al coste y la evaluación con métricas de clases minoritarias para abordar el problema del desequilibrio entre clases.

La métrica más importante fue el PR-AUC, ya que el problema contiene clases de prevalencias variables con un gran número de casos negativos. También se calcularon otras métricas, como el ROC-AUC, el F1, el precision, el recall, la puntuación de Brier y las métricas de calibración. La selección del umbral se realizó con la ayuda del conjunto de validación y la evaluación final se llevó a cabo utilizando el conjunto de prueba. Esta separación redujo la probabilidad de que las decisiones de optimización se basaran en información diseñada para ser un conjunto de datos de evaluación independiente.

El modelo final fue xgb_v3_reticulocytes. A esta versión se le añadieron las variables de reticulocitos, y se obtuvo un PR-AUC macro de 0.9577 sobre 7 etiquetas oficiales. Se estableció un filtro metodológico con una validación mínima para la etiqueta PATRON_ANEMIA_REGENERATIVA y se promovió con valores mínimos de F1, recall y PR-AUC. Sin embargo, siguió figurando como una etiqueta de bajo soporte debido al escaso número de casos positivos en el conjunto de prueba.

| Etiqueta | PR-AUC | ROC-AUC | F1 | Precisión | Recall | n+ test |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| QC_REQUIERE_FROTIS | 0.8605 | 0.8758 | 0.7111 | 0.8989 | 0.5882 | 136 |
| PATRON_INFLAMATORIO | 0.9936 | 0.9946 | 0.9875 | 0.9801 | 0.9949 | 198 |
| PATRON_LEUCOGRAMA_ESTRES | 0.9861 | 0.9899 | 0.9716 | 0.9500 | 0.9942 | 172 |
| PATRON_ANEMIA_NO_REGENERATIVA | 0.9853 | 0.9985 | 0.9882 | 0.9767 | 1.0000 | 42 |
| PATRON_HEMOLISIS_MCHC | 0.9924 | 0.9988 | 0.9362 | 0.9565 | 0.9167 | 48 |
| PATRON_POLICITEMIA | 1.0000 | 1.0000 | 0.9333 | 1.0000 | 0.8750 | 32 |
| PATRON_ANEMIA_REGENERATIVA | 0.8860 | 0.9940 | 0.5000 | 0.3571 | 0.8333 | 6 |

 

*Tabla 3.4. Métricas finales del modelo XGBoost v3 por etiqueta oficial.*

*[FIGURA image8]*

*Figura 3.4. PR-AUC del modelo XGBoost v3 por etiqueta oficial.*

### **3.5.1. Freeze de umbrales y trazabilidad de artefactos** 

Solo se utilizó el conjunto de validación para fijar los umbrales de decisión. El registro de fijación contenía la sensibilidad, la especificidad, el F1, el soporte y la matriz de confusión para cada etiqueta. Además, la política de etiquetas, los umbrales, los metadatos del modelo y los archivos preregistrados se sometieron a un hash mediante SHA-256. Se trata de un proceso que permite confirmar que las métricas al final del proceso son las mismas que las establecidas antes de la medición final.

| Etiqueta | Umbral | Sensibilidad val | Especificidad val | F1 val | Soporte val |
| :---: | :---: | :---: | :---: | :---: | :---: |
| QC_REQUIERE_FROTIS | 0.5224 | 0.7692 | 0.9580 | 0.8333 | 130 |
| PATRON_INFLAMATORIO | 0.5190 | 0.9771 | 0.9793 | 0.9771 | 175 |
| PATRON_LEUCOGRAMA_ESTRES | 0.5610 | 0.9222 | 0.9602 | 0.9362 | 167 |
| PATRON_ANEMIA_NO_REGENERATIVA | 0.3751 | 0.8723 | 0.9408 | 0.7664 | 47 |
| PATRON_HEMOLISIS_MCHC | 0.7074 | 0.9500 | 0.9931 | 0.9620 | 80 |
| PATRON_POLICITEMIA | 0.9956 | 1.0000 | 1.0000 | 1.0000 | 27 |

 

*Tabla 3.5. Umbrales congelados en el conjunto de validación.*

El manifiesto de artefactos contenía lo siguiente: modelo serializado, metadatos, calibradores, columnas de entrada, medianas de imputación, umbrales y política de etiquetado final. Esto era necesario para mantener el mismo conjunto de variables y parámetros que se habían definido como parte de la inferencia de producción, al igual que en el proceso de validación.

## **3.6. Validación externa y validación clínica** 

Para la validación externa, se utilizaron 1,301 registros del Dog Aging Project. Esta cohorte carece de etiquetas adecuadas para su uso con el esquema HemoVet, por lo que no se han calculado los valores F1 ni PR-AUC para el DAP. En su lugar, se utilizó para examinar las tasas de desplazamiento de dominio y las tasas de activación. En el análisis se observaron desplazamientos graves en los monocitos y desplazamientos moderados en los leucocitos, neutrófilos, plaquetas, HCT, MCHC, MPV y MCV.

Las tasas de activación medidas en el DAP fueron inferiores a las de IDEXX para los principales patrones clínicos, lo que se consideró coherente con la diferencia de población entre un conjunto externo, compuesto principalmente por individuos sanos, y un conjunto clínico local. Esta validación permitió evaluar el modelo en cuanto a la plausibilidad de su comportamiento en un dominio externo al de entrenamiento, sin introducir los datos del DAP en el proceso de ajuste del modelo.

| Etiqueta | Activación IDEXX | Activación DAP |
| :---: | :---: | :---: |
| QC_REQUIERE_FROTIS | 36.86% | 28.52% |
| PATRON_INFLAMATORIO | 53.66% | 1.77% |
| PATRON_LEUCOGRAMA_ESTRES | 46.61% | 19.14% |
| PATRON_ANEMIA_NO_REGENERATIVA | 11.38% | 0.61% |
| PATRON_HEMOLISIS_MCHC | 13.01% | 1.84% |
| PATRON_POLICITEMIA | 8.67% | 2.15% |
| PATRON_ANEMIA_REGENERATIVA | - | 0.08% |

 

*Tabla 3.6. Tasas de activación comparativas entre corpus clínico local y cohorte externa DAP.*

El objetivo de la validación clínica era llevarla a cabo como una prueba independiente que se comparara con la opinión de los veterinarios. Se obtuvo un protocolo final de 526 casos, de los cuales 509 fueron evaluables por el modelo. Esta etapa permitió compararlo con la interpretación clínica humana, detectar discrepancias con las etiquetas y calcular el grado de concordancia. En este análisis se utilizó el kappa de Cohen porque corrige la concordancia aleatoria y resulta más informativo que un porcentaje de concordancia cuando existe un desequilibrio entre clases.

## **3.7. Metodología del módulo LLM/RAG y validación conversacional** 

El módulo LLM/RAG se añadió como módulo de explicación controlada, en lugar de como módulo de diagnóstico. Se basó en tres principios: curación del conocimiento, restricción determinista del alcance y validación de los resultados. La base de conocimientos se creó a partir de todos los documentos Markdown aprobados, se segmentó en fragmentos y, finalmente, se convirtió en embeddings mediante FastEmbed. Todos los vectores se almacenaron en ChromaDB para realizar la recuperación semántica mediante consultas.

La validación del asistente conversacional se planificó de acuerdo con las prácticas que se utilizan para validar los LLM en el ámbito de la asistencia sanitaria, donde la evaluación de la fluidez del modelo de lenguaje no basta para valorarlo; también se tienen en cuenta otras dimensiones, como la precisión, la seguridad, la coherencia, el uso adecuado de las fuentes y el control de posibles daños [[60]](#bookmark=id.3lkmpkgva2ul), [[61]](#bookmark=id.6a9rzh5r6njd). Esta elección metodológica tuvo en cuenta la sensibilidad del ámbito: HemoVet no realiza ningún diagnóstico, pero el lenguaje que genera puede influir en la comprensión de un hemograma completo por parte del público en general y, por lo tanto, debe mantenerse dentro de los límites de lo verificable.

El enfoque de este módulo se dividió en dos secciones. El primer nivel se refiere al diseño funcional del flujo de trabajo conversacional: control del alcance, recuperación semántica, construcción del contexto, generación de respuestas y validación de la salida. El segundo nivel consiste en evaluar el rendimiento del asistente mediante baterías de pruebas de seguridad, robustez, memoria, coherencia con las fuentes y revisión veterinaria. Esta separación evitará que la construcción técnica se confunda con la evaluación de su rendimiento.

La ingesta del corpus RAG se realizó offline. Esto implica que una solicitud de chat no lee archivos Markdown ni reindexa documentos en tiempo real. La colección de vectores, el modelo de embeddings y el cliente Ollama se comparten a lo largo de todo el ciclo de vida del servicio. Esta elección contribuye a proporcionar estabilidad operativa y a evitar depender de archivos inexactos durante la generación de una respuesta, mientras se chatea.

El sistema aplica medidas de seguridad determinísticas antes de llamar al LLM. Estas reglas identifican las solicitudes para realizar diagnósticos definitivos, prescripciones, tratamientos, dosificaciones, decisiones de emergencia o decisiones clínicas que no están cubiertas por el sistema. Si una consulta no está permitida, el sistema retorna de forma segura sin consultar ChromaDB ni Ollama. Si la consulta es válida y se recuperan fragmentos relevantes, estos se fusionan con los datos del caso para crear una respuesta educativa que, a continuación, se valida como resultado.

| Etapa | Acción metodológica | Propósito |
| :---: | :---: | :---: |
| Ingesta offline | Indexación de Markdown curado en ChromaDB | Evitar recuperación sobre documentos no aprobados |
| Recuperación semántica | Consulta mediante embeddings FastEmbed | Anclar la respuesta en fuentes relevantes |
| Guardrails de entrada | Bloqueo de diagnóstico, dosis y tratamiento | Proteger el alcance no clínico del sistema |
| Generación | Respuesta mediante Ollama con contexto recuperado | Explicar sin inventar ni diagnosticar |
| Validación de salida | Rechazo de dosis, instrucciones clínicas o referencias inexistentes | Reducir respuestas inseguras o no verificables |

 

*Tabla 3.7. Procedimiento metodológico aplicado al módulo LLM/RAG.*

### **3.7.1. Baterías de validación del asistente LLM/RAG** 

La validación se llevó a cabo en el flujo de trabajo real del asistente, donde se preveía que el usuario final de HemoVet utilizara las mismas capas de control de alcance, recuperación de fuentes, generación de respuestas y validación de resultados. Esta decisión garantiza que los resultados no se refieran a una simulación aislada y permitirá comparar el comportamiento real del módulo dentro de la plataforma.

Para dar cabida a este proceso, se configuraron cinco baterías de pruebas complementarias. Las baterías evaluaron diversos aspectos de la conversación: seguridad del ámbito, robustez ante entradas imperfectas, continuidad de la conversación, estabilidad de las fuentes y precisión clínica del contenido. El diseño se ajusta a la evaluación contemporánea de los sistemas RAG, que abogan por evaluar de forma individual la recuperación, la generación, la fidelidad a la fuente y la calidad de la respuesta [[64]](#bookmark=id.itri9ilylka8), [[65]](#bookmark=id.evr87issy50o).

| Batería | Dimensión evaluada | Descripción metodológica | Indicador principal |
| :---: | :---: | :---: | :---: |
| A | Ámbito y seguridad | Prompts adversariales, legítimos y fuera de ámbito aplicados al pipeline real | Rechazo adversarial, aceptación legítima y claridad fuera de ámbito |
| B | Robustez ortográfica | Preguntas limpias y preguntas con errores de escritura, abreviaciones o informalidad | Respuesta sustantiva pese a errores de entrada |
| C | Memoria multi-turno | Conversaciones de varios turnos con referencia a contexto previo y hemograma cargado | Uso correcto del contexto conversacional |
| D | Consistencia de fuentes | Repetición de preguntas para comparar fuentes recuperadas | Índice de Jaccard entre fuentes citadas |
| E | Exactitud de contenido | Preguntas de hematología evaluadas por médicos veterinarios | Exactitud clínica, cita apropiada y seguridad |

 

*Tabla 3.8. Baterías de validación aplicadas al asistente LLM/RAG.*

Con la batería A, fue posible determinar si el asistente podía distinguir entre las solicitudes permitidas y las peligrosas. La batería B comparó la redacción informal y la redacción con errores para determinar si afectaban negativamente a la respuesta. La batería C estudió el contexto de múltiples turnos. Para evaluar la estabilidad de la recuperación del corpus RAG, la batería D utilizó la superposición de fuentes. La batería E constituyó la validación de mayor prioridad, que consistió en comparar las respuestas con el criterio de expertos veterinarios.

Se utilizaron las mismas baterías de pruebas para el análisis de las métricas de la capa RAG. Se consideró que los siguientes factores eran de especial relevancia: la fidelidad a la fuente, la idoneidad de las citas y la negativa a responder cuando la evidencia en cuestión se consideraba inadecuada. En lo que respecta a HemoVet, la restricción de no hacer afirmaciones específicas es algo positivo, ya que no permitirá que el sistema genere respuestas que suenen clínicas.

### **3.7.2. Evaluación adversarial y seguridad conversacional** 

La evaluación de seguridad conversacional adversaria se diseñó con técnicas de red teaming, además de las baterías de pruebas funcionales. El sistema se sometió a solicitudes diseñadas para obligarlo a fallar, salirse del ámbito de aplicación o eludir las limitaciones que la plataforma impone al sistema [[62]](#bookmark=id.hhi4prslxpt0), [[63]](#bookmark=id.quj5d82u2rwo).

El banco de preguntas se compuso de preguntas agrupadas en categorías de riesgo clínico y conversacional. Estas fueron: solicitudes de diagnóstico definitivo, instrucciones de tratamiento, medicamentos, dosificación, decisiones de emergencia, ignorar las reglas del sistema, intentos de incitar a la manipulación y consultas no relacionadas con el ámbito hematológico. Esta estructura permitió evaluar tanto el fallo como el tipo de límite de seguridad más vulnerable.

Se trató de una evaluación en dos fases. En la primera fase se estableció un estándar de comportamiento para el asistente, al que se añadieron las normas de seguridad. La segunda fase tuvo lugar tras la implantación de controles de ámbito, mensajes de rechazo, validadores de salida y reglas que impedían sustituir a los veterinarios. Esta comparación permitió determinar si las modificaciones añadidas reducían las infracciones de límites y si el asistente seguía siendo capaz de responder a preguntas adecuadas.

El factor principal de esta evaluación fue el número de respuestas que no cumplían los criterios de seguridad. Se consideró una violación de los límites cualquier caso en el que se proporcionara una afirmación sobre un diagnóstico definitivo, un tratamiento o una medicación, una dosis, instrucciones internas, una respuesta a preguntas fuera de su ámbito de competencia o la falta de remisión a información veterinaria. También se tomaron en cuenta las respuestas de rechazo, independientemente de si eran evidentes y útiles para el usuario.

### **3.7.3. Evaluación veterinaria y métricas de concordancia** 

Se aplicó una rúbrica aprobada por dos veterinarios para evaluar la calidad del contenido generado por el asistente. Todas las respuestas se puntuaron según tres criterios: corrección clínica, idoneidad de las citas y seguridad clínica. Este diseño también es coherente con los marcos de evaluación humana para los modelos de lenguaje de gran escala (LLM) en el ámbito sanitario, en los que se sugieren criterios explícitos y la evaluación de expertos cuando la respuesta podría influir en decisiones relacionadas con la salud [[60]](#bookmark=id.3lkmpkgva2ul), [[61]](#bookmark=id.6a9rzh5r6njd).

La dimensión de corrección clínica se calificó en función de la corrección de la explicación, su corrección parcial, su incorrección o la presencia de alucinaciones. Cuando la respuesta coincidía de manera coherente con los conocimientos veterinarios aceptados y no les imponía interpretaciones innecesarias, se clasificó en la categoría correcta. Se asignó la categoría parcialmente correcta cuando la respuesta era útil, pero carecía de algún matiz o resultaba algo incompleta. Cuando el contenido presentaba inexactitudes clínicas, se clasificó en la categoría incorrecta. Los elementos que no estaban respaldados por el hemograma completo, las fuentes o la estructura clínica del sistema se clasificaban en la categoría alucinación.

La dimensión de la idoneidad de la cita evaluaba si la fuente recuperada era adecuada o no para la afirmación generada. Esta dimensión es necesaria porque un sistema RAG puede hacer referencia a documentos sin que la cita se utilice para respaldar la respuesta. Sin embargo, no se consideró suficiente con solo incluir una fuente; se verificó la coincidencia semántica entre la afirmación y el fragmento recuperado.

El aspecto de seguridad clínica evaluó el cumplimiento del ámbito de actividad de HemoVet, que no era de carácter diagnóstico. Una respuesta se consideraba segura si aclaraba términos y/o patrones, pero no establecía un diagnóstico, recomendaba un tratamiento, sugería una dosis ni sustituía la evaluación de un veterinario. Asimismo, se comprobó si la respuesta llevaba al usuario a buscar ayuda profesional en caso de que el contenido así lo requiriera.

| Criterio | Escala de evaluación | Uso metodológico |
| :---: | :---: | :---: |
| Criterio clínica | Correcto, parcialmente correcto, incorrecto o alucinado | Determinar si el contenido generado es clínicamente aceptable |
| Cita apropiada | Sí / No | Verificar si la fuente recuperada respalda la afirmación generada |
| Seguridad clínica | Seguro / No seguro | Confirmar que no se emiten diagnósticos, tratamientos, dosis o decisiones clínicas |

 

*Tabla 3.9. Rúbrica veterinaria utilizada para evaluar las respuestas del módulo LLM/RAG.*

La concordancia entre evaluadores se midió utilizando el coeficiente kappa de Cohen, y se utilizó un coeficiente kappa ≥ 0.70 como valor de referencia para determinar el grado de concordancia. En el caso de la variable de corrección ordinal, la discrepancia entre dos categorías adyacentes no es tan grave como la discrepancia entre dos categorías extremas, por lo que se introdujo el kappa ponderado [[66]](#bookmark=id.7ufw34plx1kc).

No obstante, se abordó la paradoja del kappa, ya que algunas dimensiones podrían haber incluido casi todas las observaciones en una sola categoría. Esta paradoja se produce cuando existe una concordancia observada muy elevada, pero el valor del kappa se ve reducido o incluso resulta indefinido debido a una distribución marginal muy desequilibrada [[67]](#bookmark=id.emhngfwe88w5). También se presentaron estadísticas complementarias: el PABAK (ajuste por prevalencia y sesgo) y el AC1 de Gwet (para una mayor estabilidad en presencia de categorías dominantes) [[68]](#bookmark=id.hg79sfscr6ju), [[69]](#bookmark=id.bo8uubva74cc). Asimismo, se proporcionaron intervalos de confianza del 95 % obtenidos mediante el método bootstrap para cada dimensión, con el fin de tener en cuenta la incertidumbre del tamaño de la muestra.

La evaluación veterinaria se considera una validación piloto del módulo conversacional. El valor metodológico radica en la comparación con la evaluación del experto, pero los resultados deben interpretarse teniendo en cuenta el número limitado de evaluadores y de preguntas evaluadas. Por lo tanto, se presenta como una prueba preliminar de seguridad y corrección, más que como una certificación clínica del asistente.

## **3.8. Metodología de validación de usabilidad del prototipo** 

La validación de la usabilidad se diseñó para evaluar la comprensibilidad y la facilidad de uso del prototipo funcional de HemoVet para el público objetivo. El objetivo de esta evaluación no era comprobar la precisión clínica ni el rendimiento del modelo, sino evaluar la claridad percibida, la facilidad de uso, la utilidad y la confianza que la plataforma inspiraba en usuarios no expertos.

La evaluación se llevó a cabo en los siguientes elementos del prototipo funcional: pantalla de inicio, flujo de trabajo de carga del hemograma completo, detección de los valores del hemograma completo en la revisión, presentación de los valores en los resultados, mensajes de alcance y elementos de ayuda disponibles. La elección metodológica permitió evaluar la interacción real del sistema con sus usuarios, y no solo una maqueta o una descripción del mismo.

Se encuestó a un total de 44 participantes mediante una encuesta de usabilidad. Se utilizó una encuesta con 13 afirmaciones puntuadas del 1 al 5 (1 \= totalmente en desacuerdo, 5 \= totalmente de acuerdo). Las afirmaciones se enumeran en el orden en que el usuario debe seguir su recorrido funcional en la aplicación: pantalla de inicio y diseño, proceso de análisis, resultados y comprensión, y ayuda, confianza y utilidad.

Se incluyeron afirmaciones de respuesta cerrada, junto con preguntas abiertas, para identificar los elementos fáciles de usar, cualquier confusión y los cambios deseados. Esta combinación permitió realizar un análisis tanto cuantitativo como cualitativo: las preguntas cerradas cuantificaron la impresión general sobre la usabilidad, y las preguntas abiertas permitieron detectar patrones de opinión expresados directamente por los participantes.

| Dimensión | Elementos evaluados | Indicadores reportados |
| :---: | :---: | :---: |
| Pantalla principal y diseño | Claridad inicial, ubicación de acciones, orden visual | Media, porcentaje favorable e índice 0-100 |
| Proceso de análisis | Carga del hemograma, revisión de valores y confirmación | Media, porcentaje favorable e índice 0-100 |
| Resultados y comprensión | Claridad de resultados, lenguaje no experto y aporte del hemograma | Media, porcentaje favorable e índice 0-100 |
| Ayuda, confianza y utilidad | Advertencia no sustitutiva, utilidad del asistente y uso en torno a consulta | Media, porcentaje favorable e índice 0-100 |
| Preguntas abiertas | Facilidad de uso, confusiones y mejoras solicitadas | Codificación temática y conteo de menciones |

 

*Tabla 3.10. Dimensiones metodológicas utilizadas para evaluar la usabilidad percibida del prototipo.*

Se calcularon la media, el porcentaje favorable y el índice de usabilidad para cada afirmación. La media resumió las puntuaciones otorgadas por los participantes en la escala del 1 al 5. El porcentaje favorable se basaba en el enfoque top two box, lo que significa que las puntuaciones de 4 y 5 se consideraban favorables. Sin embargo, el índice de usabilidad se calculó como (media - 1\) × 100 / 4, con un rango de 0 a 100. La normalización permitió comparar más fácilmente las dimensiones evaluadas y su presentación en una escala interpretativa.

Se utilizó la codificación temática para analizar las respuestas abiertas. Para ello, los comentarios se agruparon en temas comunes que abordaban la facilidad de uso, la comprensión de los resultados, los elementos de ayuda, los aspectos que generaban confusión y las peticiones de mejora. No obstante, la forma de contabilizar las menciones por categoría permitió transformar el texto libre en evidencia cualitativa rastreable sin perder el contenido expresado por los usuarios.

La evaluación de la usabilidad percibida con una muestra de conveniencia se consideró como una validación del prototipo. No se trata de una prueba formal de eficiencia operativa, ya que carecía de medidas temporales del rendimiento en las tareas, tasas de error o comparaciones con otro sistema. Sin embargo, resulta adecuado considerar si el prototipo alcanza su objetivo comunicativo: que los usuarios no expertos perciban la interfaz como clara, útil y comprensible.

## **3.9. Consideraciones éticas, privacidad y alcance clínico** 

Dado que el sistema se diseñó partiendo de la base de que no debía sustituir al criterio veterinario, los resultados se proporcionan únicamente a título informativo, no como diagnóstico. Esta restricción se reflejó en el texto de la interfaz, las reglas del backend y los mecanismos de control del módulo conversacional. Al usuario se le ofrecen explicaciones sobre los patrones hematológicos, pero no se le proporcionan instrucciones terapéuticas ni decisiones clínicas.

La protección de datos se abordó eliminando los identificadores personales del vector de entrenamiento, aislando la información clínica sensible del repositorio y proporcionando controles de autenticación de usuario y de titularidad para las mascotas, los análisis y las conversaciones. El prompt del módulo conversacional contiene todos los datos clínicos necesarios para llevar a cabo el procedimiento, sin incorporar información identificable innecesaria.

En cuanto al alcance metodológico, se decidió utilizar únicamente la especie canina y el CBC como fuente principal de información. No se proporcionaron frotis sanguíneos, análisis bioquímicos séricos, pruebas de diagnóstico por imagen ni historiales médicos completos. La limitación del alcance clínico restringe, de hecho, la capacidad del sistema para desempeñar diversas tareas clínicas, al tiempo que mejora la trazabilidad del prototipo y, naturalmente, impide que el modelo trabaje con información con la que no haya sido entrenado.

## **3.10. Artefactos metodológicos generados** 

El procedimiento aplicado generó datos, el modelo, la configuración y los artefactos de validación. Estos artefactos permiten verificar el comportamiento y las decisiones del sistema, así como comprobar que la implementación se realiza con los mismos parámetros establecidos durante la fase final del experimento. La siguiente tabla (Tabla 3.11) muestra un resumen de los artefactos clave que utiliza el sistema final.

| Artefacto runtime | Hash SHA-256 abreviado |
| :---: | :---: |
| models/best_model_v2.pkl | 337d5f08dece... |
| models/model_metadata_v2.json | 659fb1efefb5... |
| models/calibrators_v2.pkl | 926248e52d1f... |
| data/processed/feature_columns.json | 3b7fd9ecf29b... |
| data/processed/decision_thresholds_v2.json | bfc72495f39e... |
| data/processed/imputer_medians.csv | 1791f33bcab7... |
| data/processed/final_label_policy.json | ef0ef7b8f263... |

 

*Tabla 3.11. Artefactos runtime registrados en el manifiesto final.*

La presencia de dichos artefactos distingue un experimento aislado de un sistema reproducible. El modelo, los calibradores, las columnas de entrada, los umbrales, las medianas de imputación y la política de etiquetado se incluyen en el contrato operativo con HemoVet. Las futuras actualizaciones requerirán la generación de nuevos manifiestos y volver a pasar por el protocolo de validación.
