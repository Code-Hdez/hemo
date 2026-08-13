# Capítulo II — TEXTO ACTUAL, ÍNTEGRO Y VERBATIM

> Extraído de `P1 ICC 1910 — … (4).docx` el 12 de agosto de 2026. Es el texto que hay que
> modificar. Se han desescapado los artefactos de conversión y las imágenes se han sustituido por
> marcadores `[FIGURA imageNN]`; los pies de figura se conservan tal cual.
>
> **No se ha alterado ninguna palabra del contenido.** Los errores y las cifras desactualizadas que
> contiene son deliberados: son precisamente los que hay que corregir.

---

# **Capítulo II - Solución propuesta** 

En este capítulo se describe la solución propuesta para el problema identificado en el capítulo anterior en relación con la comprensión por parte de los ciudadanos del hemograma completo canino. Se presenta una descripción general del proyecto, sus entregables principales, el proceso de desarrollo del proyecto, el calendario del proyecto, la estrategia de gestión de riesgos, el presupuesto del proyecto y la forma en que se presentará la plataforma. Estas secciones se combinan para poder definir de antemano los límites técnicos, metodológicos y operativos del sistema HemoVet y, a continuación, se procede a la realización detallada del mismo.

## **2.1. Definición del Proyecto** 

El proyecto consiste en el diseño e implementación de la Plataforma HemoVet: un sistema de interpretación hematológica inteligente para la especie canina, cuyo público objetivo son los propietarios de mascotas. El sistema permite a los usuarios cargar el PDF del hemograma completo (CBC), clasifica automáticamente los patrones hematológicos presentes y genera explicaciones en un lenguaje no técnico sin emitir diagnósticos clínicos. Esta solución responde a la falta de herramientas tecnológicas que permitan convertir los datos numéricos del hemograma completo canino en un formato fácilmente accesible para personas sin formación clínica específica.

Se ha implementado como una aplicación web modular con una API versionada /api/v1. Su arquitectura está diseñada para separar las responsabilidades de autenticación, usuarios, mascotas, historial hematológico, inferencia de aprendizaje automático, vigilancia poblacional, mapas, extracción asistida y chat LLM/RAG. Esta estructura permite mantener, probar y actualizar cada dominio funcional de forma independiente.

El núcleo analítico consiste en un modelo de clasificación multietiqueta basado en XGBoost que utiliza un conjunto final de 43 características hematológicas. El sistema produce siete etiquetas oficiales mediante el modelo probabilístico, dos etiquetas mediante reglas determinísticas y mantiene una etiqueta fuera del alcance final por limitaciones documentadas. La evolución y validación de las versiones v3 y v4 se describen en los Capítulos III, V y VI.

La capa de extracción procesa archivos PDF, CSV e imágenes mediante una cadena de intentos. El primer intento utiliza Google Gemini; si no se obtiene una salida válida, se intenta OpenRouter Gemma, seguido de OpenRouter Nemotron. Cuando los servicios remotos no producen un resultado aceptable, se utiliza un respaldo local basado en herramientas de extracción tabular y OCR. Los valores extraídos se presentan al usuario para revisión antes de la clasificación.

La capa conversacional utiliza una base de conocimiento curada, recuperación semántica y un modelo Qwen3 4B servido mediante Ollama. Antes de generar una respuesta, el sistema aplica políticas determinísticas de seguridad y selecciona únicamente el contexto clínico autorizado. La salida se valida antes de presentarse y se conserva junto con las fuentes utilizadas.

### **2.1.1. Justificación metodológica de características y orígenes de datos** 

Las características utilizadas para la clasificación de patrones son 43 características hematológicas, que consisten en analitos directos del hemograma completo (CBC), características derivadas tras la ingeniería de características, indicadores clínicos, ratios hematológicos y características asociadas a los reticulocitos. El objetivo era incorporar información adicional sobre los patrones eritroides y seguir incluyendo el PATRON_ANEMIA_REGENERATIVA como resultado oficial con bajo soporte.

Las etiquetas de entrenamiento se basan en el campo idexx_comments: se trata del texto explicativo generado a partir de la propia lógica interpretativa de ProCyteOne. Este campo NO se utilizó en el modelo, sino que se empleó para el etiquetado supervisado. El sistema aprende la relación entre el valor numérico del hemograma completo y el patrón interpretativo que obtiene del analizador, pero no tiene que leer directamente el texto que dio lugar a las etiquetas, ni sufre fugas de datos.

Para garantizar la solidez estadística y técnica, el proceso trabaja con dos fuentes de información con funciones metodológicamente distintas. La fuente principal consiste en 2,454 hemogramas completos caninos extraídos del analizador IDEXX ProCyte One en dos clínicas de Santiago de los Caballeros (noviembre de 2022 – febrero de 2026), utilizados para el entrenamiento supervisado. Por otro lado, la fuente de validación externa comprende 1,301 registros del *Dog Aging Project* (EE. UU., cohorte sana), los cuales son utilizados exclusivamente para la validación del desplazamiento de dominio (*domain shift*) sin influir en ninguna decisión de diseño o ajuste del modelo.

## **2.2. Productos del Proyecto** 

Los productos del proyecto son los resultados funcionales, técnicos y documentales que se materializan como parte de la solución propuesta. Esta sección define el alcance del MVP, los requisitos mínimos para que el motor de clasificación se considere aceptado y la estructura de los artefactos creados a lo largo del proceso de trabajo. De este modo, se establece un vínculo directo entre el objetivo del proyecto, las funcionalidades implementadas en el mismo y los resultados que pueden verificarse.

### **2.2.1. Delimitación funcional y criterios de aceptación**

Las funcionalidades del sistema son: (i) clasificación de patrones hematológicos multilabel a partir de valores tabulares CBC; (ii) extracción de valores desde distintos tipos de archivos para el CBC mediante análisis sintáctico; (iii) creación de un informe estructurado con patrones activos, probabilidades y variables influyentes; (iv) explicación en lenguaje natural utilizando LLM+RAG con guardrails de seguridad; y (v) visualización cronológica (sin análisis automatizado de tendencias) de hemogramas previos por paciente.

Quedan explícitamente excluidos del alcance: el procesamiento de imágenes de frotis sanguíneos, la integración con sistemas LIS de terceros, la compatibilidad con especies distintas de la canina y la provisión de diagnósticos clínicos.

Los criterios de aceptación del Motor ML son los umbrales mínimos de PR-AUC por etiqueta verificados sobre el conjunto de validación antes de avanzar al despliegue:

| Etiqueta | PR-AUC mínimo |
| :---: | :---: |
| PATRON_INFLAMATORIO | ≥ 0.80 |
| PATRON_LEUCOGRAMA_ESTRES | ≥ 0.80 |
| QC_REQUIERE_FROTIS | ≥ 0.75 |
| PATRON_ANEMIA_NO_REGENERATIVA | ≥ 0.70 |
| PATRON_HEMOLISIS_MCHC | ≥ 0.70 |
| PATRON_POLICITEMIA | ≥ 0.60 |

*Tabla 1. Criterios mínimos de aceptación del Motor ML por etiqueta.*

### **2.2.2. Pipeline de desarrollo y entregables**

El pipeline de desarrollo se ejecutó como una secuencia de ocho notebooks Jupyter (NB01–NB08) con entradas y salidas claramente definidas. La siguiente tabla sintetiza los artefactos producidos por cada fase; la descripción completa de su implementación técnica se documenta en el Capítulo 3.

| Fase | Notebook | Artefacto principal | Sección Cap. 3 |
| :---: | :---: | :---: | :---: |
| Ingesta y QC | NB01–NB02 | Dataset unificado 3,755 registros | 3.1 |
| Ingeniería de características | NB03 | Feature set canónico ampliado de 38 a 43 características hematológicas, incluyendo variables asociadas a reticulocitos  | 3.2 |
| Etiquetado multilabel | NB04 | Labels supervisadas + partición temporal | 3.3 |
| Modelado supervisado | NB05–NB05b | Motor ML + política de etiquetas v1.1.0 | 3.4 |
| Validación externa | NB06 | Análisis de domain shift IDEXX↔DAP | 3.5 |
| API REST | NB07 | Servicio FastAPI modular con endpoints versionados bajo `/api/v1`, incluyendo análisis hematológico, extracción asistida, autenticación, gestión de mascotas, historial, vigilancia poblacional, mapas, chat LLM/RAG y healthchecks operacionales. | 3.6 |
| Portal web + LLM/RAG | NB08 | Aplicación React 18 + Vite + TypeScript integrada con ChromaDB, FastEmbed y Ollama para consulta conversacional basada en RAG. | 3.7 |

*Tabla 2. Mapa de artefactos del pipeline HemoVet por fase de desarrollo.*

*[FIGURA image3]*   

*Figura 2.  Flujo funcional desde carga y extracción hasta clasificación y consulta conversacional.*

## **2.3. Cronograma del Proyecto**

El plan del proyecto se organizó con un enfoque incremental centrado en entregables, alineado con la guía institucional. Las tareas se agrupan por frentes de trabajo: (i) inicio y gestión (kick-off, repositorio y acuerdos); (ii) gobernanza de datos (diccionario de datos, guía de etiquetado y validación metodológica); (iii) adquisición y curación del dataset de entrenamiento IDEXX y preparación de la cohorte de validación externa DAP (captura/ingesta, control de calidad, limpieza e imputación); (iv) modelado (feature engineering, baselines, balanceo de clases, entrenamiento con Random Forest/XGBoost y optimización); (v) implementación de la capa de servicio (API REST, portal web, módulo LLM/RAG); y (vi) entregables académicos (revisión del informe y presentación).

Las dependencias y la ruta crítica se especifican explícitamente: el modelado depende de la disponibilidad del dataset curado y un esquema de etiquetado clínico uniforme; por tanto, la gobernanza de datos y el pipeline de preprocesamiento se planificaron con antelación. Se incorporaron márgenes de contingencia en relación con el calendario académico.

[FIGURA image4]

*Figura 3. Calendario de Jira - Periodo: Enero - Abril*

La Tabla 3 consolida las actividades del cronograma organizadas por frente de trabajo, con sus fechas de inicio y finalización y el estado de avance correspondiente:

| Código | Actividad | Inicio | Finalización | Estado |
| :---: | :---: | :---: | :---: | :---: |
| CH-34 | Presentación preliminar del anteproyecto ante el jurado evaluador, recepción de observaciones y determinación de las correcciones necesarias | — | — | Completada |
| **CH-36 Alineación post-jurado, cronograma y alcance validado (11 may. 2026 – 18 may. 2026\)** |  |  |  |  |
| CH-46 | Corrección de las secciones del informe que únicamente contenían títulos, numeraciones o información incompleta | 11 may. 2026 | 18 may. 2026 | Completada |
| CH-44 | Actualización del cronograma general del proyecto y vinculación del documento de trabajo utilizado por el equipo | 11 may. 2026 | 18 may. 2026 | Completada |
| CH-45 | Validación con la asesora del formato oficial que debía utilizarse antes de realizar las modificaciones del informe | 11 may. 2026 | 15 may. 2026 | Completada |
| CH-47 | Elaboración de una matriz con las observaciones realizadas por el jurado y las respuestas o correcciones planificadas | 11 may. 2026 | 18 may. 2026 | Completada |
| CH-48 | Alineación de los objetivos y requerimientos del proyecto con el modelo de machine learning, el LLM, el portal web y el dashboard | 13 may. 2026 | 22 may. 2026 | Completada |
| **CH-37 - Datos locales, etiquetado y validación clínica (11 may. 2026 – 29 jun. 2026\)** |  |  |  |  |
| CH-49 | Contacto con Brunilda para solicitar la información de contacto directo de la veterinaria colaboradora | 11 may. 2026 | 16 may. 2026 | Completada |
| CH-51 | Auditoría del dataset disponible para identificar etiquetas con pocos casos, bajo soporte o resultados deficientes | 11 may. 2026 | 20 may. 2026 | Completada |
| CH-50 | Preparación del documento explicativo para la veterinaria y organización de la solicitud de hemogramas y datos clínicos | 13 may. 2026 | 18 may. 2026 | Completada |
| CH-52 | Búsqueda y recopilación de hemogramas locales para fortalecer las dos etiquetas clínicas consideradas críticas | 18 may. 2026 | 15 jun. 2026 | Completada |
| CH-53 | Limpieza, organización y preparación de la primera versión del dataset destinado al Prototipo 1 | 20 may. 2026 | 29 may. 2026 | Completada |
| CH-54 | Evaluación de nuevas etiquetas clínicas que podían incorporarse sin aumentar excesivamente el alcance del proyecto | 20 may. 2026 | 05 jun. 2026 | Completada |
| CH-55 | Preparación de las versiones 2 y 3 del dataset y actualización de la guía utilizada para el etiquetado clínico | 02 jun. 2026 | 22 jun. 2026 | Completada |
| CH-56 | Revisión clínica preliminar de las predicciones realizadas por el modelo para comprobar su coherencia y utilidad | 17 jun. 2026 | 29 jun. 2026 | Completada |
| **CH-38 - Modelo de machine learning, métricas y explicabilidad (11 may. 2026 – 06 jul. 2026\)** |  |  |  |  |
| CH-57 | Reproducción del modelo baseline y revisión de las métricas obtenidas para cada una de las etiquetas clínicas | 11 may. 2026 | 25 may. 2026 | Completada |
| CH-58 | Entrenamiento de la primera versión del modelo de machine learning utilizando el dataset curado inicialmente | 20 may. 2026 | 01 jun. 2026 | Completada |
| CH-59 | Preparación de las métricas, resultados y demás evidencias del modelo requeridas para la presentación del Prototipo 1 | 29 may. 2026 | 01 jun. 2026 | Completada |
| CH-60 | Entrenamiento de la segunda versión del modelo con los nuevos datos y calibración de los umbrales de clasificación | 02 jun. 2026 | 19 jun. 2026 | Completada |
| CH-61 | Validación de la segunda versión del modelo de machine learning para su incorporación en el Prototipo 2 | 15 jun. 2026 | 22 jun. 2026 | Completada |
| CH-62 | Generación de explicaciones mediante SHAP para mostrar la influencia de cada variable en las predicciones realizadas | 15 jun. 2026 | 29 jun. 2026 | Completada |
| CH-63 | Entrenamiento y evaluación de la tercera versión del modelo, seleccionada como versión final del proyecto | 23 jun. 2026 | 06 jul. 2026 | Completada |
| CH-64 | Congelamiento, almacenamiento y control de versiones de los archivos y artefactos correspondientes al modelo final | 01 jul. 2026 | 06 jul. 2026 | Completada |
| CH-39 | Portal web, API, dashboard y LLM Desarrollo e integración del portal web para introducir los datos del hemograma, conexión con el modelo mediante una API, presentación de resultados en el dashboard e incorporación del LLM para generar explicaciones comprensibles | 18 may. 2026 | 06 jul. 2026 | Completado |
| CH-40 | Entregas de prototipo y evidencias. Preparación y presentación de las versiones funcionales del prototipo, acompañadas de capturas, métricas, pruebas y evidencias del funcionamiento de los componentes desarrollados | 11 may. 2026 | 06 jul. 2026 | Pendiente |
| CH-41 | Informe del proyecto. Corrección, ampliación y consolidación del informe final, incluyendo la metodología, el desarrollo del sistema, los resultados obtenidos, las validaciones, las conclusiones y las observaciones del jurado | 11 may. 2026 | 20 jul. 2026 | Pendiente |
| CH-42 | Artículo científico y de divulgación. Redacción de un artículo científico y una versión de divulgación que presenten el problema investigado, la metodología aplicada, los resultados alcanzados y los principales aportes de HemoVet | 25 may. 2026 | 20 jul. 2026 | Pendiente |
| CH-43 | Defensa ante el jurado y cierre del proyecto. Preparación de la presentación final, organización de las evidencias, ensayo de la exposición, defensa ante el jurado, aplicación de las correcciones finales y cierre documental del proyecto | 20 jul. 2026 | 04 ago. 2026 | Pendiente |

*Tabla 3. Cronograma del proyecto HemoVet organizado por frente de trabajo (epics de Jira) y tareas asociadas.*

## **2.4. Plan de Gestión de Riesgos**

Se denomina riesgo a cualquier acontecimiento o situación incierta que pueda tener un efecto adverso en el cumplimiento del objetivo general y los entregables del proyecto, ya sea en términos de alcance, plazos, rendimiento técnico, validez clínica, normas éticas/privacidad o sostenibilidad operativa. El Plan de Gestión de Riesgos tiene por objeto crear un marco sistemático para: (i) identificar y documentar los riesgos; (ii) evaluarlos basándose en criterios homogéneos; (iii) clasificar los riesgos en función de su exposición; y (iv) garantizar seguimiento ajustado al cronograma. Este plan aborda los riesgos relacionados con:

* Datos: acceso, disponibilidad, integridad, sesgo, estandarización de unidades, trazabilidad, anonimización y control de calidad.

* Modelado: rendimiento, desequilibrio, sobreajuste, fuga de información, reproducibilidad y estimación del modelo final.

* XAI e informes: SHAP/alternativas técnicas, interpretabilidad clínica e informes coherentes.

* Implementación: resiliencia de la API, verificación de entradas, tolerancia a fallos, latencia y coherencia.

* Validación: planificación/ejecución de UAT, recursos expertos y especificaciones de aceptación.

* Gestión: limitaciones de recursos y calendario, coordinación de equipos, dependencias críticas y control de cambios.

El plan no aborda riesgos clínicos de prescripción o tratamiento, dado que la herramienta se considera un apoyo y no sustituye las decisiones clínicas.

**Gobernanza y responsables**

La gobernanza se estructura en tres roles: el Responsable del Riesgo (Risk Owner), que se encarga de conocer el riesgo y desarrollar medidas preventivas; el Monitor de Riesgos (Risk Monitor), puesto de coordinación que prioriza la recopilación de evidencia y garantiza la ejecución; y el Responsable de la Decisión (Decision Owner), función o autoridad que aprueba cambios significativos. La periodicidad de revisión es semanal en proximidad a hitos sensibles y quincenal en períodos ordinarios.

**Criterios de evaluación y priorización**

El análisis se realiza por categorías (Técnicos TR, Gestión MR, Externos ER, Éticos/Legales E-LR) con escalas numéricas de probabilidad (0.90–0.10) y severidad (0.80–0.05). La exposición se calcula como E \= P × I. Los umbrales de clasificación son: Alto (E ≥ 0.50), Medio (0.30 < E < 0.50) y Bajo (E ≤ 0.30).

Los artefactos del plan son: (i) Registro/Matriz de Riesgos (Anexo Tabla 16); (ii) Plan de Respuesta y Contingencia (Anexo Tabla 17); (iii) Señales de alerta y desencadenantes operativos; y (iv) Registro de revisión de riesgos con estados (abierto/mitigado/materializado/cerrado).

### **2.4.1. Enfoque metodológico para la evaluación de riesgos**

El enfoque se concibió como un ciclo continuo y verificable, implementando mecanismos de detección temprana (indicadores anticipados). La identificación se realiza mediante: revisión de dependencias críticas del cronograma, análisis del ciclo de vida del aprendizaje automático, revisión de restricciones y sesiones de trabajo internas por cada fase del pipeline. El análisis cualitativo determina probabilidad e impacto, interpretado en dimensiones de tiempo, calidad técnica, calidad clínica y ética/privacidad. El análisis cuantitativo (P × I) permite priorizar: riesgos altos requieren respuesta planificada con revisión semanal; medios, mitigación planificada; bajos, seguimiento proporcional.

En el contexto de este proyecto, el panel de control no es un panel de métricas en sí mismo, sino más bien la interfaz estructurada del portal ciudadano que reúne cuatro experiencias principales: comprender lo que está sucediendo en el CBC actual, la vista cronológica de la mascota, la vigilancia comunitaria basada en el CBC registrado y la consulta explicativa mediante el uso del LLM. Los parámetros metodológicos del modelo se dejan en manos de un panel técnico independiente y no son clave para la navegación del usuario.

El módulo de vigilancia comunitaria presenta, en un área cartografiada, zonas agregadas y el número de hallazgos indicativos detectados en el sistema, con protección de la privacidad. Su objetivo es facilitar una lectura exploratoria a nivel poblacional del comportamiento observado en los registros disponibles y no constituye un diagnóstico ni una indicación de incidencia, ni un fiel reflejo de la prevalencia de la enfermedad en los perros. La interfaz incluye una leyenda interpretativa que se muestra de forma permanente y una tabla de texto equivalente al mapa a la que se puede acceder fácilmente.

### **2.4.2. ¿Cómo manejará sus riesgos?** 

La gestión se implementa mediante cuatro estrategias complementarias:

* **Evitar:** Congelar permanentemente el MVP en especie, tipo de datos y artefactos comprometidos; formalizar solicitudes adicionales como versiones futuras.

* **Mitigar:** Comprobaciones automáticas de calidad de datos, políticas de estandarización, verificación de fugas y duplicados, balanceo de clases, pruebas unitarias e integración de la API.

* **Aceptar:** Aplicable a riesgos bajos o medios cuando el costo de mitigación es desproporcionado, manteniendo desencadenantes y planes de contingencia activos.

* **Mitigar mediante apoyo externo:** Cuando la gestión requiera asistencia externa (revisión ética, UAT, asesoramiento clínico), sin transferir la responsabilidad del equipo.

## **2.5. Presupuesto** 

El presupuesto del proyecto representa una estimación de los recursos necesarios para finalizar el prototipo funcional de HemoVet en el plazo académico establecido. Se sistematiza en cinco categorías: hardware, software/licencias, datos, recursos humanos y costos operativos de despliegue. Los componentes tecnológicos se describen en dólares estadounidenses (USD).

### **2.5.1. Hardware** 

El desarrollo y la demostración emplean equipos locales y recursos de Google Cloud. 

| Ítem | Especificación | Costo estimado (USD) | Observación |
| :---: | :---: | :---: | :---: |
| Laptop principal (existente) | RTX 4050 6 GB VRAM, 16 GB RAM, SSD 512 GB | 0.0 | Propiedad del equipo investigador |
| Laptop respaldo (existente) | CPU 8 núcleos, 16 GB RAM, sin GPU dedicada | 0.0 | Propiedad del equipo investigador |
| Almacenamiento en la nube 5 TB | Backup de datasets y modelos | 0.0 | En manos de ambos investigadores por paquete estudiantil de Google |
| VPS (Virtual Private Server) para hosting | - | Depende de los recursos a solicitar. | Los investigadores cuentan con al menos 200 créditos en plataformas que ofrecen los servicios. Como alternativa, los investigadores disponen de acceso autorizado a un VPS facilitado por la empresa en la que labora uno de ellos. |
| Subtotal hardware |  | 0.0 |  |

*Tabla 4. Estimación de costos de hardware del proyecto HemoVet.*

### **2.5.2. Software y licencias** 

Toda la pila tecnológica del proyecto es de código abierto o gratuita. No se han adquirido licencias de software comercial.

| Componente | Versión / fuente | Costo (USD) |
| :---: | :---: | :---: |
| Python 3.11 + librerías ML (scikit-learn, XGBoost, shap, pdfplumber, pandas) | Open-source (PyPI) | 0.0 |
| FastAPI + Uvicorn + Nginx | Open-source (MIT) | 0.0 |
| React 18 + TypeScript + Vite + Tailwind CSS | Open-source (MIT) | 0.0 |
| Módulo RAG (retrieval léxico + corpus local) | ChromaDB + FastEmbed + Ollama + corpus Markdown curado | 0.0 |
| Ollama + Qwen3 4B cuantizado | Open-source (Apache 2.0) | 0.0 |
| Docker + docker-compose | Open-source (Apache 2.0) | 0.0 |
| PostgreSQL 16 | Open-source (PostgreSQL License) | 0.0 |
| Git + GitHub (repositorio privado) | Gratuito (plan educativo) | 0.0 |
| Jupyter Lab / VS Code | Open-source | 0.0 |
| Subtotal software y licencias |  | 0.00 USD |

*Tabla 5. Estimación de costos de software del proyecto HemoVet.*

## **2.6. Definición de la Demostración**

La demostración del proyecto tiene como objetivo ilustrar cómo funciona HemoVet en una situación controlada y verificable. Se definen el entorno de ejecución, los casos de prueba prevalidados y el flujo que seguirá el usuario desde la carga del hemograma completo hasta la creación del informe y la interacción con la capa conversacional. Esta sección permite comprobar que la solución no solo es técnicamente madura, sino que también es posible ejecutarla de forma repetible, tomando como referencia los criterios de éxito acordados.

### **2.6.1. Entorno de ejecución**

La demostración se realizará en una sala de presentación con conexión estable a internet, proyector y equipo de respaldo. La interfaz será accedida desde un navegador web y el sistema principal se ejecutará en la VM hemovet-prod de Google Cloud, donde operan el proxy web, el frontend, el backend, PostgreSQL, ChromaDB y Ollama sobre CPU. Se conservará una copia local de los casos de prueba y un procedimiento de contingencia para reiniciar los servicios. La VM hemovet-llm-gpu no se presentará como parte del entorno operativo mientras permanezca apagada y desconectada del despliegue automatizado.

### **2.6.2 Casos de prueba prevalidados**

Los casos de prueba se seleccionan para abarcar escenarios hematológicos relevantes, con el fin de validar el comportamiento del motor de clasificación, las reglas determinísticas y la generación de explicaciones para los ciudadanos. Para cada caso se definieron un perfil esperado, etiquetas de destino y un objetivo de verificación específico, lo que proporciona un amplio espectro de patrones clínicos y casos de control de calidad.

| Caso | Perfil hematológico | Etiquetas esperadas | Propósito |
| :---: | :---: | :---: | :---: |
| A | Trombocitopenia severa (PLT 18), linfopenia, neutrofilia | QC_REQUIERE_FROTIS, PATRON_INFLAMATORIO | Discriminación QC + inflamatorio |
| B | Leucograma de estrés clásico: neutrofilia + linfopenia + eosinopenia | PATRON_LEUCOGRAMA_ESTRES | Patrón compuesto sin alerta QC |
| C | Anemia (HCT 28%, HGB 9.2), normocítica normocrómica | PATRON_ANEMIA_NO_REGENERATIVA | Clasificación de anemia |
| D | MCHC 53 g/dL (artefacto), agregados plaquetarios | QC_AGREGADOS (Módulo 2); HEMOLISIS_MCHC suprimida | Regla artefacto + Módulo 2 |

*Tabla 6. Casos de prueba prevalidados para la demostración de HemoVet.*

### **2.6.3. Flujo y criterios de éxito**

La demostración se realiza de forma secuencial: (1) se sube el PDF al portal a través de DropZone; (2) el portal invoca el endpoint de análisis hematológico versionado, POST /api/v1/hematology/analyze, que lleva a cabo la extracción, la validación de entradas, la construcción de características, la inferencia con XGBoost, las reglas determinísticas y la persistencia del resultado; (3) visualización del informe con patrones, probabilidades, valores clave del hemograma completo y derivación veterinaria; (4) consulta al módulo conversacional mediante POST /api/v1/chat o POST /api/v1/chat/stream, con verificación previa de los límites de seguridad determinísticos y validación de la salida; (5) comparación con el comentario original de IDEXX. Duración aproximada: entre 15 y 20 minutos para los cuatro casos.

El rendimiento se considera exitoso si: los cuatro casos producen las etiquetas esperadas sin error; la regla MCHC se activa en el Caso D; el LLM rechaza la solicitud adversaria; la latencia de respuesta por caso es inferior a 10 segundos; y no se exponen identificadores reales de pacientes.
