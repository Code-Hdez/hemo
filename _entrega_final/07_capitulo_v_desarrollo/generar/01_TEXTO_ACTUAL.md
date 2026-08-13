# Capítulo V — TEXTO ACTUAL, ÍNTEGRO Y VERBATIM

> Extraído de `P1 ICC 1910 — … (4).docx` el 12 de agosto de 2026. Es el texto que hay que
> modificar. Se han desescapado los artefactos de conversión y las imágenes se han sustituido por
> marcadores `[FIGURA imageNN]`; los pies de figura se conservan tal cual.
>
> **No se ha alterado ninguna palabra del contenido.** Las cifras erróneas que contiene son
> deliberadas: son precisamente las que hay que corregir.

---

# **Capítulo V - Desarrollo del proyecto** 

En este capítulo se describe la construcción técnica de HemoVet, cuyo diseño se presentó en el capítulo anterior. Se presta especial atención a los componentes concretos que se implementaron, los artefactos que se crearon, las integraciones que se llevaron a cabo y las verificaciones técnicas que se utilizaron para convertir la propuesta en una plataforma operativa. El análisis detallado de los resultados experimentales, la interpretación de las métricas y la discusión sobre el rendimiento se dejan para el capítulo VI.

El desarrollo se llevó a cabo con el objetivo de crear un sistema integrado de ingeniería de software e inteligencia artificial. La solución final incluye un flujo de datos hematológicos, un motor de clasificación multietiqueta, reglas deterministas, una API REST modular, una interfaz web para propietarios, un módulo LLM/RAG con medidas de seguridad, una capa de vigilancia poblacional y una estrategia de despliegue reproducible mediante contenedores.

Durante la construcción, se mantuvo una separación estricta entre el entrenamiento y la inferencia. El entrenamiento, la calibración, la fijación de umbrales y la generación de artefactos se llevaron a cabo al margen del entorno de producción. El backend utiliza los artefactos para realizar la inferencia, almacenar los resultados y ofrecer servicios disponibles a través de contratos HTTP versionados. De este modo, el modelo puede actualizarse sin modificar la API ni la interfaz de usuario.

## **5.1. Construcción del pipeline de datos** 

El trabajo inicial consistió en el desarrollo del flujo de trabajo de datos para convertir un hemograma completo canino (CBC) a un formato tabular que pudiera procesarse automáticamente. El proceso está diseñado para procesar registros de entrenamiento, preparar datos de validación externos y mantener la trazabilidad entre cada archivo fuente, la información extraída de él y los artefactos creados.

La fuente clínica principal fue IDEXX ProCyte One, con hemogramas completos. Se utilizaron los siguientes registros para crear el corpus supervisado, ya que incluyen mediciones hematológicas numéricas y comentarios interpretativos del analizador. El Dog Aging Project se convirtió en una fuente externa para validar las respuestas fuera del dominio local; no se utilizó para el entrenamiento ni para el ajuste de umbrales.

En el proceso se extrajeron las variables, se normalizaron, se estandarizaron los nombres de sus campos, se convirtió su formato, se sometieron a control de calidad, se imputaron los datos faltantes y se eliminaron las variables que pudieran filtrar información. No se utilizaron como entrada en el modelo variables identificables del propietario, la mascota o la clínica. Del mismo modo, se omitió el campo de comentarios del analizador como característica predictiva, ya que su finalidad era la etiquetación.

| Actividad desarrollada | Descripción técnica | Artefacto generado |
| :---: | :---: | :---: |
| Extracción de hemogramas | Procesamiento de reportes CBC y normalización de parámetros hematológicos. | Dataset clínico IDEXX estructurado. |
| Integración externa | Mapeo del Dog Aging Project a un esquema compatible con el corpus local. | Cohorte DAP para validación externa. |
| Control de calidad | Identificación de campos faltantes, valores extremos y registros con inconsistencias. | Reportes de QA y flags de extracción. |
| Imputación | Cálculo de medianas sobre el conjunto de entrenamiento y aplicación consistente al resto de particiones. | Archivo de medianas de imputación. |
| Trazabilidad | Preservación de columnas, políticas y hashes de artefactos para reproducibilidad. | Manifiestos de artefactos y políticas de labels. |

*Tabla 5.1. Actividades principales desarrolladas en el pipeline de datos.*

El diseño del proceso permitió separar los datos para el aprendizaje supervisado de los datos para la validación de la generalización. Esta elección ayudó a que el modelo no aprendiera patrones específicos de la cohorte del DAP y a utilizar dicha cohorte como control externo para observar el desplazamiento de dominio.

## **5.2. Desarrollo del motor de aprendizaje automático** 

Se creó un motor de aprendizaje automático de clasificación multietiqueta utilizando XGBoost. Se requirieron varias etiquetas porque un hemograma completo puede dar lugar a múltiples patrones hematológicos: inflamación, leucograma de estrés, anemia o alerta de control de calidad. Se descartó un modelo multiclase, ya que habría obligado al sistema a elegir una de las categorías y se habría perdido la información clínicamente relevante.

La versión final del sistema se documentó como versión lógica 4.0.0 y cuenta con siete etiquetas oficiales. Algunos artefactos de tiempo de ejecución dejaron nombres de versiones antiguas, como best_model_v2.pkl o decision_thresholds_v2.json, pero el estado final del sistema incluye explícitamente la política de umbrales, la versión lógica y las restricciones de implementación.

El conjunto de características incluía analitos del hemograma completo, así como indicadores clínicos, índices hematológicos y variables relacionadas con los reticulocitos. Se incluyó la etiqueta PATRON_ANEMIA_REGENERATIVA porque solo había seis casos positivos en el conjunto de prueba; por ello se consideró un resultado exploratorio con escaso respaldo. Esta condición se dejó sin modificar para evitar una interpretación excesiva de dicho resultado.

| Elemento | Decisión de desarrollo | Resultado |
| :---: | :---: | :---: |
| Algoritmo principal | XGBoost multilabel con relevancia binaria. | Un clasificador por etiqueta oficial. |
| Métrica operativa | PR-AUC, F1, recall, Brier Score y calibración. | Evaluación por etiqueta y métrica macro. |
| Umbrales | Selección sobre validación y congelamiento para runtime. | Archivo de umbrales persistido. |
| Reglas determinísticas | Aplicación de reglas para condiciones no confiables o no aprendibles. | Etiquetas rule-based y supresión de artefactos. |
| Trazabilidad | Registro de estado final, manifiestos y limitaciones. | Sistema marcado como listo con limitaciones. |

*Tabla 5.2. Decisiones de desarrollo aplicadas al motor de aprendizaje automático.*

| Tipo de salida | Etiquetas o condiciones | Mecanismo |
| :---: | :---: | :---: |
| Etiquetas oficiales de modelo | QC_REQUIERE_FROTIS; PATRON_INFLAMATORIO; PATRON_LEUCOGRAMA_ESTRES; PATRON_ANEMIA_NO_REGENERATIVA; PATRON_HEMOLISIS_MCHC; PATRON_POLICITEMIA; PATRON_ANEMIA_REGENERATIVA. | Inferencia XGBoost calibrada. |
| Etiquetas por regla | QC_AGREGADOS_PLAQUETARIOS; QC_INTERFERENCIA_GR. | Reglas determinísticas y condiciones explícitas. |
| Etiqueta excluida | QC_UNIDAD_NO_CONVERTIDA. | Limitación documentada. |
| Política de bajo soporte | PATRON_ANEMIA_REGENERATIVA. | Salida exploratoria por bajo número de positivos en prueba. |

Tabla 5.3. Política de salidas implementada en el sistema final.

 

[FIGURA image15]

Figura 5.1. Salida gráfica generada durante la verificación del motor de clasificación. El análisis comparativo de estas métricas se desarrolla en el Capítulo VI.

 

[FIGURA image16]

Figura 5.2. Curvas Precision-Recall generadas como artefacto de evaluación del desarrollo del modelo. La interpretación detallada se reserva para el análisis de resultados.

 

[FIGURA image17]

Figura 5.3. Visualización de la política de etiquetas utilizada durante la consolidación del sistema. La política final queda formalizada en la Tabla 5.3.

También se añadieron reglas determinísticas en los casos en los que el modelado probabilístico no resultaba el mejor enfoque. Un ejemplo de ello es que las afecciones con un patrón de PATRON_HEMOLISIS_MCHC se suprimen cuando el valor de MCHC indica que se trata de un artefacto analítico, por lo que estas afecciones no aparecen como patrones.

[FIGURA image18]

*Figura 5.4. Salida SHAP generada para auditar importancia global de características por etiqueta durante el desarrollo del motor.*

 

*[FIGURA image19]*

*Figura 5.5. Salida de comparación de tasas de activación entre IDEXX y DAP como verificación de comportamiento fuera del dominio de entrenamiento.*

 

## **5.3. Desarrollo del backend** 

El backend está escrito con FastAPI y Pydantic v2, y cuenta con una arquitectura modular basada en dominios. La API funcional solo estuvo presente en /api/v1, mientras que los endpoints de verificación operativa se mantuvieron en un espacio independiente en /health\*. Esto permitió diferenciar entre los contratos de usuario, los servicios internos y las comprobaciones de disponibilidad.

La estructura interna del backend se organizó en módulos dentro de app/modules. Las rutas, los esquemas, los servicios, los repositorios y los modelos de persistencia (cuando procede) están disponibles en cada dominio. La configuración transversal, la seguridad, las sesiones y las dependencias se trasladaron a app/core, app/db y app/dependencies, respectivamente, junto con las excepciones. Esta organización ayuda a evitar que la lógica de negocio se concentre en un único archivo y facilita la realización de pruebas unitarias por componente.

| Módulo backend | Responsabilidad implementada |
| :---: | :---: |
| auth | Registro, inicio de sesión, emisión de sesión y validación de identidad. |
| users | Gestión de usuarios y roles. |
| pets | Gestión de mascotas asociadas al propietario. |
| pet_history | Consulta de historial de análisis por mascota. |
| hematology | Carga, revisión, análisis y persistencia de hemogramas. |
| ml | Carga de artefactos, construcción de features e inferencia. |
| population_surveillance | Agregación poblacional y señales de vigilancia. |
| maps | Servicios asociados a visualización geográfica agregada. |
| llm_chat | Consulta conversacional, RAG, guardrails y streaming SSE. |
| gemini_extraction | Extracción asistida con modelos externos cuando aplica. |
| files | Manejo de archivos subidos y artefactos asociados. |
| dashboard | Métricas técnicas y vistas administrativas. |

*Tabla 5.4. Módulos del backend implementados por dominio funcional.*

Para implementar la persistencia se utilizaron PostgreSQL, SQLAlchemy 2 y Alembic. Los modelos de SQLAlchemy se crean en el módulo que contiene los datos y se añaden a la base compartida de la aplicación para las migraciones. El DDL no se ejecuta al iniciar la aplicación, sino que los cambios en la estructura se aplican mediante migraciones controladas.

En producción, la autenticación en el navegador se realiza mediante una cookie denominada hemovet_session, que es una cookie HttpOnly, lo que significa que el token de sesión no se puede leer directamente mediante JavaScript. Los clientes de la API siguen admitiendo el esquema Authorization: Bearer. Este enfoque dual ayuda a diferenciar el uso a través del navegador y a través de la API programática.

| Capa interna | Implementación | Función |
| :---: | :---: | :---: |
| Router | FastAPI APIRouter | Define contratos HTTP y dependencias. |
| Schema | Pydantic v2 | Valida request/response. |
| Service | Servicios de dominio | Orquesta reglas, transacciones e integración. |
| Repository | SQLAlchemy | Centraliza consultas y persistencia. |
| Model | SQLAlchemy ORM | Define estructura persistente. |
| Cliente externo | Gemini, OpenRouter, Ollama o ChromaDB | Integra servicios técnicos externos o locales. |

*Tabla 5.5. Patrón de responsabilidades aplicado dentro del backend.*

## **5.4. Desarrollo del frontend** 

El frontend está construido con React 18, Vite y TypeScript. La interfaz está orientada al propietario y hace hincapié en el flujo de trabajo de comprensión del hemograma completo sin presentar la plataforma como un sistema de diagnóstico. El frontend llama a la API versionada y el backend ejecuta los procesos críticos de las decisiones críticas de extracción, inferencia, persistencia, autenticación y control de ámbito.

La aplicación incluye pantallas para registrarse e iniciar sesión, gestionar mascotas, cargar hemogramas completos, revisar hemogramas para su análisis, visualizar resultados, consultar el historial específico de cada mascota, plantear preguntas al sistema, acceder a una biblioteca o glosario, visualizar datos agregados de vigilancia comunitaria y acceder a métricas técnicas y administrativas. En conjunto, estas pantallas acompañan al propietario durante el proceso y facilitan la preparación de preguntas para la consulta veterinaria.

| Vista o funcionalidad | Propósito dentro de la plataforma |
| :---: | :---: |
| Resumen personal | Presenta una visión inicial de mascotas, análisis recientes y accesos rápidos. |
| Carga y revisión de hemograma | Permite subir archivos, verificar valores extraídos y corregir antes del análisis. |
| Resultado actual | Muestra patrones activos, probabilidades, valores relevantes y advertencias de alcance. |
| Historial/evolución | Permite consultar análisis previos asociados a una mascota. |
| Chat | Explica valores y patrones mediante el módulo LLM/RAG controlado. |
| Biblioteca/glosario | Ofrece definiciones y material educativo relacionado con hematología canina. |
| Vigilancia comunitaria | Muestra información agregada sin presentarla como prevalencia real o diagnóstico confirmado. |
| Panel técnico/admin | Permite revisar métricas operativas y estado de componentes. |

*Tabla 5.6. Funcionalidades principales implementadas en el frontend.*

En el frontend, las credenciales se incluyen en las solicitudes para mantener la sesión del navegador mediante una cookie HttpOnly. Para el chat en tiempo real, la interfaz consume eventos SSE procedentes del backend y mantiene el control de la sesión, así como las validaciones de seguridad del lado del servidor.

## **5.5. Desarrollo del módulo LLM/RAG** 

El módulo LLM/RAG no se diseñó como un motor de diagnóstico, sino más bien como una capa explicativa con fines educativos. Se utiliza para proporcionar respuestas a consultas sobre valores hematológicos, términos y patrones dentro del ámbito permitido por el sistema. En este sentido, el módulo se diseñó con una arquitectura en capas en app/modules/llm_chat, donde se separan la API, la aplicación, el dominio, la infraestructura, los prompts y la composición de clientes reutilizables.

La base de conocimientos se ha creado a partir de documentos Markdown seleccionados y aprobados. La ingesta se realiza sin conexión: los documentos Markdown no se leen a partir de una solicitud de chat, los archivos no se dividen y el corpus no se reindexa. FastAPI reutiliza la colección ChromaDB, el modelo de embeddings FastEmbed y el cliente HTTP para Ollama durante la ejecución. De este modo, cuando no hay corpus o hay fragmentos que no son útiles, no se lleva a cabo el despliegue, lo que reduce la variabilidad en producción.

El flujo de trabajo de consultas era capaz de realizar la validación de la autenticación, la verificación de la pertenencia del análisis, la clasificación determinista del ámbito, la recuperación semántica, la construcción de un prompt que incluyera hechos y fuentes, la generación con Ollama y la validación de la salida. Si una consulta busca un diagnóstico definitivo, un tratamiento, dosis, medicamentos, decisiones de emergencia, etc., entonces se genera la respuesta más segura sin utilizar ChromaDB ni Ollama.

| Etapa implementada | Descripción |
| :---: | :---: |
| Ingesta offline | Indexación de documentos Markdown aprobados en ChromaDB. |
| Embeddings | Transformación semántica de fragmentos mediante FastEmbed. |
| Recuperación | Búsqueda de candidatos relevantes por similitud semántica. |
| Guardrails de entrada | Clasificación de consultas fuera de alcance antes de invocar el LLM. |
| Generación | Uso de Ollama mediante API compatible con OpenAI. |
| Validación de salida | Rechazo de dosis, instrucciones clínicas, diagnósticos definitivos y referencias inexistentes. |
| Persistencia | Registro de pregunta, respuesta, fuentes, latencia y uso de tokens. |

*Tabla 5.7. Componentes desarrollados para el módulo LLM/RAG.*

El endpoint POST /api/v1/chat devuelve una respuesta JSON completa, pero POST /api/v1/chat/stream envía eventos de estado, fragmentos de respuesta, fuentes y el evento de cierre como eventos enviados por el servidor (Server-Sent Events). La salida se produce tras la validación, incluso durante la transmisión en tiempo real; la política de seguridad permanece intacta.

Aunque el módulo conversacional se sometió inicialmente a pruebas preliminares de alcance funcional, la evaluación final del asistente no se limitó a estas pruebas iniciales. La validación completa del módulo LLM/RAG se dejó para el capítulo VI, donde se analizan los comportamientos del proceso real mediante una serie de pruebas de seguridad, robustez frente a errores ortográficos, memoria a lo largo de múltiples turnos, coherencia de las fuentes y una evaluación veterinaria.

Por lo tanto, el diseño técnico del módulo queda reflejado en el proceso de desarrollo: control del alcance mediante barreras determinísticas, recuperación semántica a partir de un corpus seleccionado, generación mediante un modelo de lenguaje y validación de la salida. Los resultados de los experimentos con el asistente se resumen en la sección 6.4.

## **5.6. Desarrollo del módulo de vigilancia poblacional** 

El módulo de vigilancia poblacional se ha creado como una amalgama de las señales detectadas en los hemogramas completos registrados en la población. Su objetivo es ofrecer una perspectiva exploratoria del patrón de los análisis, la frecuencia de los hallazgos preliminares y las señales temporales, y no necesariamente una prevalencia real o un diagnóstico confirmado en la población de perros.

Las siguientes funciones formaban parte de la estructura del módulo: agregación de resultados, controles de privacidad, generación de informes y advertencias metodológicas. El sistema no proporciona ningún dato individual ni realiza inferencias sobre los datos clínicos de ninguna mascota en concreto a partir de la visualización de la vista poblacional. En la interfaz, la vigilancia va acompañada de avisos que especifican que los datos son exploratorios y preliminares.

| Control de vigilancia | Resultado en el reporte v3 | Interpretación de desarrollo |
| :---: | :---: | :---: |
| feature_parity | pass | La paridad de características fue verificada. |
| leakage_audit | pass | No se detectó fuga básica según el gate aplicado. |
| manifest_integrity | pass | Los artefactos requeridos estuvieron disponibles. |
| policy_freeze | pass | La política de etiquetas se mantuvo congelada. |
| drift_basic | pass | La verificación básica de deriva fue aprobada. |

*Tabla 5.8. Gates técnicos aplicados al módulo de vigilancia poblacional.*

El informe de vigilancia poblacional se basa en una cohorte de 200 registros correspondientes a un periodo de 30 días. El estado general era de advertencia, con tres señales en estado aprobado, dos en estado advertencia y ninguna señal en estado fallo. Las advertencias se debían a la falta de geocodificación y al hecho de que la mayoría de los registros se encontraban en una ubicación desconocida, por lo que el módulo funcionaba correctamente, pero con una clara restricción geográfica.

## **5.7. Pruebas, despliegue y verificación técnica** 

El último paso del desarrollo fue la verificación de la capacidad de los componentes creados para funcionar como un sistema completo. Esto se logró mediante pruebas automatizadas, una prueba de rendimiento de inferencia, la ejecución de casos de demostración, la validación de medidas de seguridad, la verificación del estado del sistema y una estrategia de despliegue reproducible mediante contenedores..

Para el despliegue se utilizaron topologías independientes para desarrollo, control de calidad, GPU y producción. Los servicios se pueden iniciar con el comando `docker compose up --build` en el entorno de desarrollo. En producción, el sistema incluirá un overlay de Docker Compose con Caddy para la terminación TLS y redirigirá `/api/v1/\*` al backend. Las migraciones son migraciones de Alembic que se ejecutan en el punto de entrada del backend, y el despliegue requiere un corpus RAG válido antes de atender el tráfico.

| Evidencia técnica | Resultado registrado | Uso dentro del desarrollo |
| :---: | :---: | :---: |
| Pruebas backend | 25 passed, 114 warnings in 1.45s | Verificación automatizada de rutas, servicios y RAG. |
| Benchmark de inferencia | p50=27.93 ms; p95=33.9 ms; n=1000 | Medición in-process del predictor ML. |
| Guardrails LLM/RAG | 50/50 adversariales rechazados; 20/20 legítimos aceptados | Validación de alcance conversacional. |
| Demostración E2E | 4 casos ejecutados con estado success | Verificación del flujo de predicción y reglas. |
| Estado final del sistema | READY_FOR_PRODUCTION_WITH_LIMITATIONS | Cierre técnico con limitaciones explícitas. |

*Tabla 5.9. Evidencias técnicas de verificación del sistema desarrollado.*

Se validaron previamente cuatro casos en la ejecución de extremo a extremo. En los escenarios A y B se observaron más etiquetas debido a la naturaleza multietiqueta del clasificador. Esto confirma que la verificación funcional no debe considerarse una validación clínica, sino un medio para probar el flujo del proceso de trabajo.

Se utilizaron 1,000 solicitudes y 50 iteraciones de calentamiento para ejecutar la prueba de rendimiento del motor de inferencia. La medición se llevó a cabo sin HTTP, autenticación, base de datos ni RAG, y corresponde a la latencia interna del predictor. El valor mediano fue de 27.93 ms y el valor del percentil 95 fue de 33.9 ms; ambos se consideran valores interactivos dentro de la aplicación web.

El estado técnico del sistema se clasificó como READY_FOR_PRODUCTION_WITH_LIMITATIONS. Esta clasificación significa que el sistema puede instalarse y utilizarse dentro de las limitaciones indicadas, pero no excluye la necesidad de supervisar la deriva, aumentar los datos y evaluar las etiquetas con escaso soporte en versiones posteriores.

## **5.8. Síntesis del desarrollo implementado** 

El proceso de desarrollo dio como resultado HemoVet, una plataforma web modular compuesta por el procesamiento del hemograma completo, la inferencia multietiqueta, reglas deterministas, persistencia, consultas conversacionales, vigilancia poblacional y despliegue reproducible. El desarrollo se centró en la trazabilidad de los artefactos, la separación entre entrenamiento e inferencia, la seguridad de las sesiones, el control del ámbito clínico y la validación técnica automatizada.

El capítulo demuestra que existe un producto operativo, que utiliza componentes verificables y evidencia técnica. En el capítulo VI se analiza el comportamiento del sistema, no solo su construcción, y se presentan los resultados junto con un análisis del rendimiento del modelo, la interpretación de las curvas, la discusión de los errores, la validación clínica de los resultados y una evaluación crítica.

