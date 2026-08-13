# Capítulo IV — TEXTO ACTUAL, ÍNTEGRO Y VERBATIM

> Extraído de `P1 ICC 1910 — … (4).docx` el 12 de agosto de 2026. Es el texto que hay que
> modificar. Se han desescapado los artefactos de conversión y las imágenes se han sustituido por
> marcadores `[FIGURA imageNN]`; los pies de figura se conservan tal cual.
>
> **No se ha alterado ninguna palabra del contenido.** Los errores y las cifras desactualizadas que
> contiene son deliberados: son precisamente los que hay que corregir.

---

# **Capítulo IV - Análisis y Diseño** 

Este capítulo presenta el análisis funcional y el diseño arquitectónico de HemoVet basados en el sistema final desarrollado. Su objetivo es esbozar la estructura de la plataforma, los actores implicados, los casos de uso que se abordan, la distribución de responsabilidades internas y las decisiones de diseño que permiten la integración de la clasificación hematológica, la extracción asistida, la persistencia, la vigilancia poblacional y las explicaciones conversacionales controladas.

HemoVet se diseñó como una plataforma modular, en lugar de una arquitectura monolítica o una arquitectura compuesta por tres servicios simples. La API funcional se publica en /api/v1, mientras que las comprobaciones de estado operativo no se encuentran en /api/v1. El backend aloja dominios independientes para la autenticación, los usuarios, las mascotas, el historial, la hematología, la inferencia, la extracción, los archivos, la vigilancia poblacional, los mapas, el chat LLM/RAG y el panel técnico. Esta separación permite mantener, probar y ampliar cada dominio sin necesidad de modificar todo el sistema.

El análisis y el diseño mencionados en este capítulo se circunscriben exclusivamente al ámbito del proyecto desde el punto de vista académico y funcional. El sistema no tiene fines diagnósticos, ni terapéuticos, ni indicativos, ni sustituye el diagnóstico o el tratamiento de un veterinario. Está diseñado para contribuir a la difusión de conocimientos entre el público sobre los hemogramas completos caninos y para recordarles las pautas de seguridad y la importancia de derivar al profesional adecuado.

## **4.1. Análisis del sistema** 

El análisis del sistema se llevó a cabo siguiendo los siguientes pasos: creación de una cuenta de propietario, carga de un hemograma, visualización de todos los valores extraídos del hemograma, activación del análisis hematológico, consulta del resultado y, si fuera necesario, comunicación con el asistente conversacional. A partir de este flujo de trabajo, se identificaron los actores, los casos de uso, los requisitos funcionales, los requisitos no funcionales y las restricciones de alcance clínico.

### **4.1.1. Actores del sistema** 

La Tabla 4.1 resume los actores identificados durante el análisis del sistema.

| Actor | Descripción | Responsabilidades dentro del sistema |
| :---: | :---: | :---: |
| Propietario | Usuario principal de la plataforma. | Gestiona mascotas, carga hemogramas, revisa valores, consulta resultados, usa el asistente y revisa historial. |
| Administrador técnico | Usuario con permisos de operación y supervisión. | Consulta métricas, estado del sistema, vigilancia agregada y evidencias técnicas. |
| Servicios de extracción | Servicios remotos o locales usados por el backend. | Apoyan la extracción de valores desde PDF, CSV o imagen mediante proveedores remotos y fallback local. |
| Servicios RAG/LLM | Componentes de recuperación semántica y generación controlada. | Recuperan fragmentos aprobados, generan respuestas educativas y aplican validación de salida. |

*Tabla 4.1. Actores del sistema HemoVet.*

### **4.1.2. Casos de uso principales** 

Los casos de uso se definieron para cubrir el flujo completo del propietario y las funciones de supervisión técnica. La Figura 4.1 sintetiza la interacción entre actores y funcionalidades. El propietario concentra los casos de uso ciudadanos; el administrador técnico accede a métricas y operación; los servicios de extracción y RAG actúan como componentes técnicos invocados por el backend, no como usuarios finales.

[FIGURA image9]

*Figura 4.1. Diagrama de casos de uso actualizado de HemoVet.*

| Código | Caso de uso | Actor principal | Resultado esperado |
| :---: | :---: | :---: | :---: |
| CU-01 | Registrarse e iniciar sesión | Propietario | Sesión autenticada mediante cookie HttpOnly o token Bearer para clientes API. |
| CU-02 | Gestionar mascotas | Propietario | Creación, consulta y actualización de mascotas asociadas a la cuenta. |
| CU-03 | Cargar hemograma | Propietario | Archivo recibido y asociado al usuario para extracción y análisis. |
| CU-04 | Revisar extracción | Propietario | Valores extraídos presentados para confirmación o corrección antes del análisis. |
| CU-05 | Ejecutar análisis hematológico | Propietario | Predicciones, reglas determinísticas y hallazgos almacenados en el sistema. |
| CU-06 | Consultar resultado | Propietario | Visualización de patrones activos, probabilidades, advertencias y explicación orientativa. |
| CU-07 | Consultar asistente | Propietario | Respuesta educativa con guardrails, fuentes RAG y advertencia de no sustitución clínica. |
| CU-08 | Consultar historial por mascota | Propietario | Listado cronológico de análisis asociados a una mascota. |
| CU-09 | Revisar vigilancia comunitaria | Propietario/Admin | Mapa o resumen agregado sin interpretación de prevalencia real ni diagnóstico confirmado. |
| CU-10 | Consultar biblioteca/glosario | Propietario | Acceso a definiciones y materiales educativos aprobados. |
| CU-11 | Consultar panel técnico | Administrador técnico | Revisión de métricas, salud de servicios y evidencias de operación. |

*Tabla 4.2. Casos de uso principales del sistema.*

### **4.1.3. Requerimientos funcionales** 

Los requisitos funcionales se desarrollaron basándose en los objetivos específicos del proyecto. Cada requisito se asoció a una capacidad observable del sistema, para evitar la ambigüedad en los objetivos. La tabla 4.3 muestra los requisitos funcionales incluidos en el diseño final.

| Código | Requerimiento funcional | Descripción |
| :---: | :---: | :---: |
| RF-01 | Autenticación | El sistema debe permitir registro, inicio de sesión, validación de sesión y cierre de sesión. |
| RF-02 | Gestión de mascotas | El sistema debe asociar mascotas a usuarios y controlar la pertenencia de cada recurso. |
| RF-03 | Carga de hemogramas | El sistema debe recibir archivos PDF, CSV o imágenes para procesamiento hematológico. |
| RF-04 | Extracción asistida | El sistema debe extraer valores hematológicos mediante proveedores remotos y fallback local. |
| RF-05 | Revisión de valores | El usuario debe poder verificar los valores extraídos antes de ejecutar el análisis. |
| RF-06 | Análisis hematológico | El backend debe construir características, ejecutar el modelo XGBoost v3 y aplicar umbrales congelados. |
| RF-07 | Reglas determinísticas | El sistema debe aplicar reglas para etiquetas no resueltas por modelo y para condiciones de control de calidad. |
| RF-08 | Persistencia | El sistema debe almacenar análisis, valores, predicciones, mensajes y eventos asociados. |
| RF-09 | Chat LLM/RAG | El sistema debe responder preguntas educativas con recuperación semántica y validación de salida. |
| RF-10 | Vigilancia agregada | El sistema debe visualizar patrones agregados sin presentarlos como prevalencia real. |
| RF-11 | Panel técnico | El sistema debe exponer métricas y estados para administración y QA. |

*Tabla 4.3. Requerimientos funcionales del sistema.*

### **4.1.4. Requerimientos no funcionales** 

Los requisitos no funcionales abarcanabarcaban la seguridad, la privacidad, la reproducibilidad, la trazabilidad y la facilidad de mantenimiento. Estos factores son tan cruciales para un sistema de orientación hematológica como lo son los modelos, ya que un resultado correcto puede resultar perjudicial si no se ajusta al ámbito del sistema o si no está controlado.

| Código | Requerimiento no funcional | Criterio de diseño |
| :---: | :---: | :---: |
| RNF-01 | Seguridad | Uso de cookie HttpOnly para navegador y Bearer JWT para clientes API. |
| RNF-02 | Privacidad | No incluir datos identificables innecesarios en prompts ni vectores de entrenamiento. |
| RNF-03 | Reproducibilidad | Despliegue mediante Docker Compose, migraciones Alembic y artefactos versionados. |
| RNF-04 | Mantenibilidad | Separación Router, Schema, Service, Repository y Model en el backend. |
| RNF-05 | Trazabilidad | Registro de modelo, umbrales, fuentes RAG, mensajes, latencia y acciones de seguridad. |
| RNF-06 | Disponibilidad operativa | Healthchecks separados para backend, RAG, Chroma, Ollama y base de datos. |
| RNF-07 | Control de alcance clínico | Guardrails para diagnóstico definitivo, medicamentos, tratamientos, dosis y urgencias. |
| RNF-08 | Extensibilidad | API versionada bajo /api/v1 para permitir evolución futura sin romper clientes existentes. |

*Tabla 4.4. Requerimientos no funcionales del sistema.*

### **4.1.5. Restricciones de alcance clínico y ético** 

En el diseño del sistema solo se incluyó la interpretación inicial del hemograma completo de un perro. No se incluyeron diagnósticos definitivos, ni tratamientos, medicaciones, dosis, pronósticos o decisiones clínicas de emergencia automatizadas. Si la consulta de un usuario requiere este tipo de respuesta, el sistema debe impedir que el usuario interactúe con el modelo de IA o guiarlo hacia una respuesta no perjudicial, como “Es hora de ir al veterinario”.

También se estableció una restricción explícita sobre la vigilancia comunitaria. Los eventos agregados son únicamente patrones de eventos observados en los registros subidos a la plataforma y no representan prevalencia, incidencia epidemiológica ni diagnósticos confirmados. En consecuencia, la interfaz debe proporcionar avisos y advertencias sobre las interpretaciones que deben evitarse para prevenir interpretaciones erróneas.

## **4.2. Diseño del sistema** 

El diseño de HemoVet es modular y se basa en la separación de responsabilidades: el frontend se encarga de la interacción con el usuario; el backend, de los contratos, las reglas, las transacciones, la inferencia y la seguridad; se utiliza PostgreSQL para almacenar entidades persistentes; ChromaDB, para almacenar los embeddings del corpus curado; y Ollama, para ejecutar el modelo de lenguaje, cargando los artefactos de aprendizaje automático en el backend para la inferencia local.

La evolución del sistema no requiere una modificación brusca de la interfaz, ya que la comunicación se basa en contratos HTTP versionados. El diseño garantiza que el frontend no ejecute reglas clínicas ni almacene tokens confidenciales en JavaScript en producción.

### **4.2.1. Diseño modular del backend** 

El backend está diseñado basándose en la separación en capas. Cuando procede, cada uno de los dominios contiene un enrutador, esquemas, servicios y repositorios. El enrutador representa el contrato HTTP; los esquemas son la estructura de entrada/salida definida por Pydantic; los servicios son donde se centralizan las reglas de negocio y las transacciones; los repositorios sirven para encapsular consultas de SQLAlchemy; y los modelos representan la persistencia del dominio.

Esta organización evita que la API dependa directamente de los modelos de persistencia o de las consultas SQL. También permite realizar pruebas unitarias, ya que las reglas se prueban a nivel de servicio, sin necesidad de iniciar la plataforma. Los módulos principales y sus dependencias técnicas se muestran en la figura 4.2.

[FIGURA image10]

*Figura 4.2. Diagrama de componentes backend y servicios asociados.*

| Módulo | Responsabilidad principal | Datos o servicios asociados |
| :---: | :---: | :---: |
| auth | Inicio de sesión, emisión de sesión y control de acceso. | Cookie HttpOnly, JWT, validación de usuario. |
| users | Gestión de usuarios y roles. | users.role como fuente de verdad de autorización. |
| pets | Registro y consulta de mascotas. | Mascotas asociadas a usuarios. |
| pet_history | Consulta cronológica de análisis por mascota. | Historial de hemogramas y resultados. |
| hematology | Orquestación del análisis hematológico. | Valores CBC, análisis, resultados y revisión. |
| ml | Carga de artefactos y ejecución de inferencia. | XGBoost v3, calibradores, umbrales y medianas. |
| gemini_extraction | Extracción asistida con proveedores remotos. | OpenRouter, Gemini y normalización de salida. |
| files | Recepción y gestión de archivos. | PDF, CSV, imágenes, checksums y metadatos. |
| llm_chat | Chat educativo con RAG y guardrails. | ChromaDB, FastEmbed, Ollama, mensajes y fuentes. |
| population_surveillance | Agregación de hallazgos orientativos. | Eventos agregados y tasas internas. |
| maps | Representación geográfica agregada. | Zonas, mapas y visualización comunitaria. |
| dashboard | Panel técnico y métricas operativas. | Estados, QA, métricas y healthchecks. |

*Tabla 4.5. Módulos backend y responsabilidades de diseño.*

### **4.2.2. Diseño del flujo de análisis hematológico** 

El flujo del análisis hematológico comienza con la carga del archivo y finaliza con la entrega de los resultados preliminares. El sistema comprueba la sesión, la propiedad de los recursos, el formato del archivo, la extracción de valores, la normalización y la construcción de características antes de ejecutar el modelo. Esta secuencia no permite realizar ninguna inferencia a partir de entradas incompletas o no verificadas.

Para realizar las inferencias se utilizan el modelo XGBoost v3 y los umbrales fijos. A continuación, se aplican a las etiquetas las reglas que el modelo no puede resolver, al igual que las reglas relativas a las condiciones de control de calidad. De este modo, también se conservan los valores, las probabilidades, las etiquetas activas, la versión del modelo y los metadatos con fines de auditoría. Este flujo de trabajo se resume en la figura 4.3.

[FIGURA image11] 

*Figura 4.3. Diseño del flujo de análisis hematológico*

### 

### **4.2.3. Diseño de persistencia y modelo de datos** 

El modelo de datos se creó para capturar la relación entre el usuario, la mascota, el archivo, un análisis, los valores hematológicos, las predicciones, una conversación y las fuentes RAG. Esta trazabilidad permitirá vincular la respuesta de un asistente a un análisis específico, siempre que no se facilite información identificable innecesaria en la solicitud.

La persistencia se basa en migraciones de Postgres y Alembic. Los modelos para SQLAlchemy forman parte del módulo que contiene los datos y están registrados para una migración centralizada. El modelo lógico de datos utilizado para el diseño se ilustra en la figura 4.4.

[FIGURA image12]

*Figura 4.4. Modelo conceptual de persistencia de HemoVet.*

### **4.2.4. Diseño del módulo LLM/RAG** 

La consulta pasa primero por políticas determinísticas de seguridad. Si está permitida, se clasifica la intención y se selecciona el contexto clínico autorizado del análisis o historial correspondiente. El sistema recupera fuentes del corpus RAG, incorpora memoria conversacional y construye el contexto del modelo. La respuesta generada se valida antes de persistirse y mostrarse con sus fuentes. Este diseño impide que el modelo sustituya la salida del clasificador o mezcle información de hemogramas distintos.

[FIGURA image13]

*Figura 4.5. Pipeline completo del módulo LLM/RAG.*

### **4.2.5. Diseño de despliegue** 

La implementación se realizó con Docker Compose. En fase de desarrollo, el frontend y el backend están disponibles en la red local, y en producción se integra un proxy que incluye terminación HTTPS. La topología de producción reenvía todo el tráfico /api/v1/* al backend y utiliza una configuración especial para el comportamiento de streaming de SSE, conservando las cookies y los encabezados de autorización, y desactivando el almacenamiento en búfer si es necesario.

El arranque del sistema considera dependencias estrictas: PostgreSQL y ChromaDB deben estar saludables, la ingesta RAG debe completarse con al menos un chunk aprobado, el modelo de Ollama debe estar disponible y el backend debe ejecutar migraciones antes de iniciar. La Figura 4.5 muestra la topología lógica de despliegue.

[FIGURA image14] 

*Figura 4.6. Estado de despliegue verificado en Google Cloud.*

### **4.2.6. Contratos API versionados** 

En cuanto a la API funcional, se publica en /api/v1. Esta elección ayuda a distinguir los endpoints de negocio de las comprobaciones de estado operativas, lo que permite mantener las versiones de los contratos sin afectar a la monitorización. El resumen de los principales grupos de endpoints utilizados por el sistema se muestra en la siguiente tabla (Tabla 4.6). Si es probable que la ruta real cambie debido a una refactorización interna, el contrato se mantiene a nivel de grupo funcional en /api/v1.

| Grupo API | Ruta base o endpoint | Propósito |
| :---: | :---: | :---: |
| Autenticación | /api/v1/auth/* | Registro, login, sesión actual y cierre de sesión. |
| Usuarios | /api/v1/users/* | Consulta y administración de usuarios según permisos. |
| Mascotas | /api/v1/pets/* | Gestión de mascotas y asociación con el propietario. |
| Historial | /api/v1/pet-history/* | Consulta de análisis previos por mascota. |
| Hematología | /api/v1/hematology/* | Carga, revisión, análisis y consulta de resultados hematológicos. |
| Extracción | /api/v1/gemini-extraction/* o módulo equivalente | Extracción asistida de valores desde documentos. |
| Vigilancia | /api/v1/population-surveillance/* | Consulta de información agregada y no diagnóstica. |
| Mapas | /api/v1/maps/* | Visualización geográfica agregada. |
| Chat | POST /api/v1/chat | Respuesta completa del asistente educativo. |
| Chat streaming | POST /api/v1/chat/stream | Respuesta validada mediante SSE. |
| Historial de chat | GET /api/v1/chat/conversations/{id}/messages | Consulta paginada de mensajes propios. |
| Salud chat | GET /api/v1/chat/health | Healthcheck sanitizado de Chroma, Ollama, embeddings y RAG. |
| Healthchecks | /health* | Verificación operacional fuera del prefijo funcional /api/v1. |

*Tabla 4.6. Contratos API versionados por grupo funcional.*

### **4.2.7. Seguridad, autenticación y privacidad** 

El diseño se basa en el hecho de que se utiliza una cookie HttpOnly para proporcionar autenticación a las solicitudes del navegador, y en que esta puede utilizarse con JWT de tipo Bearer para los clientes de la API. El frontend debe enviar las credenciales y no debe almacenar el JWT en JavaScript en el entorno de producción. La autorización viene definida por el rol y la titularidad de las mascotas, los análisis y las conversaciones.

Las variables de entorno se utilizan para almacenar secretos como DATABASE_URL, SECRET_KEY y claves de proveedores externos, y nunca están sometidas a control de versiones. En las pruebas, solo son obligatorias las variables correspondientes a los componentes utilizados. Las comprobaciones de estado no deben revelar secretos ni información confidencial. En el módulo de conversación, el mensaje solo contiene información clínica relevante y no incluye el nombre ni la dirección de la mascota o del propietario, ni otros identificadores irrelevantes.

## **4.3. Síntesis del diseño propuesto** 

El diseño final de HemoVet combina los diversos elementos del análisis hematológico, las reglas deterministas, la persistencia, la visualización, la vigilancia agregada y las explicaciones conversacionales en una arquitectura modular. La separación entre entrenamiento e inferencia, entre el backend y el frontend, junto con la integración controlada de LLM y RAG, permite controlar el alcance del sistema clínico y garantizar la trazabilidad técnica.

La arquitectura propuesta logra el objetivo de disponer de una herramienta de orientación hematológica orientada a los ciudadanos, sin sustituir al veterinario. El diseño también sentará las bases para futuras ampliaciones, entre las que se incluyen la integración con el sistema de información de laboratorio (LIS), una mejor geocodificación, la ampliación del corpus RAG, el análisis longitudinal automatizado y nuevas validaciones clínicas.
