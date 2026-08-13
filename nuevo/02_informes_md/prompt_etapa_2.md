Prompt para implementar la etapa 2

Se te pide implementar exclusivamente la etapa número 2 de la corrección del módulo de chat LLM de HemoVet. Esta es una tarea de implementación real sobre el repositorio: no debes limitarte a proponer otro plan, describir cambios posibles ni entregar pseudocódigo. Debes inspeccionar el estado actual, modificar el código de producción necesario y dejar esta etapa cerrada dentro de su alcance.

Antes de realizar cualquier cambio, debes localizar y leer íntegramente, de principio a fin y sin limitarte a resúmenes, fragmentos o búsquedas puntuales, los siguientes cuatro archivos que estarán en la raíz del proyecto:

plan_1.md

plan_2.md

contexto_1.md

contexto_2.md

También se te entregará el resultado completo de la etapa 1, ya sea como un archivo, un informe, un diff y/o cambios ya aplicados en el repositorio. Debes leerlo e inspeccionarlo por completo antes de editar nada. El resultado de la etapa 1 y el estado real del código constituyen la línea base sobre la cual trabajarás: conserva los cambios correctos ya implementados, no los repitas, no los sustituyas por implementaciones paralelas y no reviertas trabajo previo. Si el informe de la etapa 1 y el repositorio no coinciden, verifica el código y toma el estado real del repositorio como autoridad, dejando constancia de cualquier discrepancia relevante.

Los cuatro documentos pertenecen al mismo proyecto y deben interpretarse de forma conjunta. contexto_1.md y contexto_2.md contienen la auditoría, los defectos detectados, las restricciones y las razones arquitectónicas. plan_1.md y plan_2.md contienen dos formulaciones complementarias del plan de corrección. Debes unificarlas de manera coherente, resolver diferencias de nombres sin crear contratos duplicados y aplicar sus invariantes comunes. No leas ningún archivo superficialmente y no ejecutes cambios basándote únicamente en el título de una sección.

Alcance unificado de esta etapa 2

Los dos planes numeran algunos trabajos de forma diferente. Para esta ejecución, la etapa 2 unificada comprende únicamente los siguientes dos bloques, construidos sobre lo que ya dejó listo la etapa 1:

Integración real de ResponsePlan y desacoplamiento completo del RAG como permiso para responder, correspondiente a la etapa 2 de plan_2.md y a los contratos fundacionales definidos en plan_1.md.

Construcción del ContextBundle completo, autorizado y trazable para los tres modos del chat, correspondiente a la etapa 2 de plan_1.md y a la descripción equivalente de contexto contenida en plan_2.md.

Si la etapa 1 ya creó enums, dataclasses, settings u otros contratos relacionados, debes reutilizarlos y completar su integración; no crees otra versión con nombres casi iguales. Cuando los planes utilicen nombres distintos —por ejemplo, REQUIRED frente a REQUIRED_FOR_CITATIONS, USED frente a HIT o DATABASE frente a DATABASE_GROUNDED— conserva un único vocabulario canónico compatible con la implementación de la etapa 1 y garantiza la semántica exigida por ambos planes. Evita adaptadores o aliases innecesarios que perpetúen dos modelos conceptuales.

A. ResponsePlan y RAG degradable

La ruta activa debe dejar de interpretar use_rag como una decisión simultánea sobre recuperación, conocimiento, seguridad y permiso para contestar. Integra el ResponsePlan canónico de la etapa 1 en el flujo real del chat y separa, como mínimo, la política de recuperación, el estado de recuperación y el modo o los modos de conocimiento permitidos.

El comportamiento resultante debe cumplir estos invariantes:

NO_MATCH o UNAVAILABLE son estados técnicos de recuperación, no una prohibición automática de responder.

La ausencia, desactivación o caída de Chroma/RAG no convierte por sí sola una consulta en INSUFFICIENT_EVIDENCE, no apaga el chat y no bloquea respuestas basadas en PostgreSQL o conocimiento paramétrico permitido.

PostgreSQL es soporte factual suficiente para datos concretos y autorizados de la mascota.

El conocimiento paramétrico puede utilizarse para educación veterinaria segura cuando el plan lo autorice.

El RAG puede enriquecer una respuesta, pero solo será obligatorio cuando la petición requiera explícitamente fuentes o citas, según el contrato canónico adoptado.

Si se solicitan fuentes y no están disponibles, el sistema no inventará referencias; la situación se trasladará al plan y al flujo generativo de forma transparente.

chat_ready dependerá del módulo y del proveedor; rag_ready será un estado independiente y degradable.

OUT_OF_DOMAIN continuará siendo una intención o alcance interno, no una respuesta visible prefabricada.

Ningún router, clasificador o coordinador nuevo devolverá prosa visible. Las decisiones deterministas producen planes, metadatos y restricciones.

Elimina o adapta únicamente las bifurcaciones activas necesarias para hacer efectivo este desacoplamiento. No dejes el contrato nuevo sin uso mientras la ruta canónica continúa gobernada por el booleano anterior.

B. ContextBundle completo y trazable

Implementa un único constructor de contexto que cargue desde PostgreSQL toda la información autorizada necesaria para el alcance del turno antes de cualquier compactación posterior. Debe existir una representación tipada equivalente al ContextBundle descrito en los planes, con perfil de la mascota, estudio seleccionado, historial, resultados y hallazgos ML, calidad y procedencia, conversación disponible, evidencia RAG opcional, revisión del contexto y registro explícito de hechos omitidos cuando corresponda.

Cada hecho clínico utilizable debe tener un identificador estable interno, tipo, valor, unidad cuando aplique, estudio y fecha cuando apliquen, procedencia y confianza cuando exista. Los IDs internos son para trazabilidad y validación; no deben exponerse como texto visible al usuario.

Debes cubrir los tres modos:

General sin pet_id: conversación veterinaria general, sin datos personales.

General con pet_id opcional: validar propiedad y cargar únicamente el perfil autorizado necesario; analysis_id permanece prohibido en este modo. Incluir los campos consentidos y disponibles señalados por los planes, sin enviar coordenadas exactas.

Hemograma seleccionado: cargar el perfil autorizado, todos los parámetros persistidos del análisis con valores, unidades, referencias y estados disponibles, fechas, laboratorio, analizador, ML estructurado, hallazgos, calidad, confianza, procedencia y revisión. La priorización puede ordenar los hechos, pero no eliminar arbitrariamente información solicitada; si el usuario pide todos los valores, deben quedar disponibles todos los valores existentes.

Historial: conservar por estudio fechas clínicas y de carga disponibles, parámetros, unidades, referencias, ML, hallazgos, calidad, laboratorio, analizador, procedencia y comparabilidad. Un cambio de laboratorio, rango o analizador debe generar metadatos de comparabilidad, no ocultar los valores exactos.

No conviertas narrativas libres del formatter en hechos clínicos autorizados, no interpretes la ausencia de una etiqueta ML como normalidad, no inventes parámetros ausentes de PostgreSQL y marca de forma trazable cualquier dato heredado o recuperado desde un snapshot autorizado. Respeta en todo momento la propiedad del usuario y evita mezclar mascotas, análisis o conversaciones.

El ContextBundle debe representar lo autorizado antes de que una etapa posterior aplique el presupuesto final del prompt. En esta etapa puedes crear las interfaces y puntos de integración necesarios, pero no debes adelantar la reconstrucción completa del PromptBudgetPlanner, el tokenizer definitivo, el nuevo envelope generativo ni la regeneración, salvo ajustes mínimos indispensables para que los contratos de esta etapa estén conectados y el código sea coherente.

Límites estrictos

Trabaja solamente en el módulo LLM y sus puntos directos de integración especificados en los planes. No modifiques frontend, entrenamiento ML, extracción o formatter hematológico, otros módulos de negocio ni datos aguas arriba. Los defectos externos descubiertos en las auditorías deben quedar documentados como dependencias cuando afecten esta etapa, no corregirse fuera del alcance autorizado.

No avances a las etapas dedicadas a la reforma completa de memoria, routing y seguridad, contrato generativo, eliminación total de prosa legacy, RAG multilingüe, presupuesto final de prompts, cambio de modelo, streaming, observabilidad o limpieza definitiva del monolito. Tampoco cambies el modelo ni amplíes el contexto por iniciativa propia.

Queda totalmente prohibido crear, modificar, borrar, regenerar o ejecutar tests. No toques tests/, no actualices fixtures o snapshots de prueba y no ejecutes suites de tests ni comandos que las recolecten. El cierre de esta etapa se hará mediante inspección estática del código, revisión del diff, comprobación de contratos, imports, tipos e invariantes, sin usar los tests como tarea paralela. No alteres cambios ajenos existentes en el workspace y no uses operaciones destructivas para limpiar el repositorio.

Forma de trabajo y entrega

Primero inspecciona la ruta canónica real desde la API hasta el proveedor, los componentes creados en la etapa 1 y todos los consumidores de los contratos que vayas a cambiar. Luego implementa la solución completa de esta etapa en el código de producción. No dejes una segunda ruta paralela, contratos huérfanos, imports rotos, TODOs que sustituyan la implementación ni compatibilidad silenciosa que mantenga activo el comportamiento defectuoso.

Al terminar, detente: no comiences la etapa 3. Entrega un informe final preciso que incluya:

Qué parte de la etapa 1 encontraste y cómo la reutilizaste.

Qué archivos de producción modificaste.

Cómo quedó integrado ResponsePlan y cómo se desacopló el RAG.

Cómo se construye y qué contiene el ContextBundle en cada modo.

Qué invariantes y contratos verificaste estáticamente.

Qué dependencias externas o riesgos quedan pendientes para etapas posteriores.

Confirmación explícita de que no creaste, modificaste ni ejecutaste tests y de que no implementaste etapas posteriores.

Esta tarea es una parte crítica del proyecto. Debe ejecutarse de manera profesional, exhaustiva y coherente con los cuatro documentos y con el resultado real de la etapa 1, concentrándose únicamente en la etapa 2 unificada aquí definida.