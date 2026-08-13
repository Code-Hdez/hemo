Prompt para implementar la etapa 3

Se te pide implementar exclusivamente la etapa número 3 de la corrección del módulo de chat LLM de HemoVet. Esta es una tarea de implementación real sobre el repositorio: no debes entregar otro plan, limitarte a recomendaciones, describir cambios hipotéticos ni sustituir la implementación con pseudocódigo. Debes inspeccionar la línea base actual, modificar el código de producción necesario y dejar cerrada esta etapa dentro de su alcance exacto.

Antes de modificar cualquier archivo, debes localizar y leer íntegramente, de principio a fin y sin limitarte a resúmenes, fragmentos, encabezados o búsquedas puntuales, los cuatro documentos obligatorios que estarán en la raíz del proyecto:

plan_1.md

plan_2.md

contexto_1.md

contexto_2.md

También debes leer completos, antes de editar, los antecedentes de ejecución que se te entregarán:

informe_etapa_1.md

informe_etapa_2.md

prompt_etapa_1.md

prompt_etapa_2.md

Los dos informes y el estado real del repositorio constituyen la línea base de esta etapa. Debes conservar los cambios correctos ya implementados, trabajar sobre ellos y evitar repetirlos, reemplazarlos con implementaciones paralelas o revertirlos. Si algún informe no coincide con el código actual, inspecciona el repositorio y toma el código real como autoridad, pero registra la discrepancia en la entrega final. No supongas que una tarea está terminada solamente porque el informe la menciona: verifica estáticamente sus contratos y puntos de integración antes de depender de ella.

Los cuatro documentos principales pertenecen al mismo proyecto y deben interpretarse juntos. contexto_1.md y contexto_2.md explican los defectos, riesgos e invariantes arquitectónicos; plan_1.md y plan_2.md presentan dos numeraciones parcialmente diferentes de una misma migración. Los prompts e informes anteriores muestran cómo se reconciliaron esas numeraciones y qué se implementó realmente. No debes escoger uno de los planes e ignorar el otro.

Línea base que debe preservarse

La etapa 1 dejó configuraciones tipadas, contratos canónicos de ResponsePlan, parámetros efectivos de generación, representación decimal correcta y persistencia atómica mediante complete_turn(). La etapa 2 integró el ResponsePlan, desacopló el RAG como permiso para responder, corrigió la disponibilidad degradable y creó el ContextBundle autorizado para los tres modos.

Debes reutilizar esas piezas. En particular:

No vuelvas a crear ResponsePlan, RetrievalPolicy, RetrievalStatus, KnowledgeMode, ContextBundle ni otra familia equivalente de tipos.

No restaures use_rag como gate de respuesta ni vuelvas a hacer que chat_ready dependa del RAG.

Conserva la corrección de números como 150, la validación previa a persistencia y el conflicto CAS tipado.

Extiende la propiedad conversacional de ContextBundle y la ruta activa que compone el turno; no construyas un sistema de memoria paralelo.

Mantén PostgreSQL como única autoridad para hechos concretos de la mascota. La memoria nunca puede sustituir la recarga clínica realizada en cada turno.

Alcance unificado de esta etapa 3

La numeración de los planes se solapa: plan_2.md llama “etapa 3” a parte del ContextBundle, pero ese bloque ya fue incorporado y cerrado en la etapa 2 unificada, según informe_etapa_2.md. Por tanto, para esta ejecución la etapa 3 unificada corresponde a:

Corrección de la memoria y del contexto conversacional, descrita como etapa 3 en plan_1.md.

Memoria y persistencia conversacional reales, descrita como etapa 5 en plan_2.md.

No repitas el trabajo de contexto clínico de la etapa 2 y no avances al routing/seguridad, contrato generativo o etapas posteriores. La meta de esta etapa es que la conversación conserve continuidad real y segura, sin convertir el transcript en evidencia clínica ni mezclar usuarios, mascotas, análisis o temas.

A. Memoria disponible en todos los turnos

Elimina la dependencia de expresiones regulares para decidir si el modelo puede recordar. La ruta canónica debe proporcionar memoria conversacional en todos los turnos autorizados, no solo cuando una frase empiece por “¿y eso?”, cuando el clasificador marque FOLLOW_UP o cuando se solicite explícitamente historial.

Como mínimo, el contexto conversacional disponible debe incluir:

El último intercambio válido entre usuario y asistente.

Una ventana reciente configurable, utilizando la configuración tipada creada en la etapa 1 y sin introducir nuevos límites mágicos.

Un resumen estructurado de la conversación anterior cuando exista.

Tema activo.

Parámetro o analito activo.

Estudio o análisis activo.

Preferencia de estilo o nivel de explicación.

Estado de seguridad e insistencia.

La ventana reciente deberá seguir el rango y el presupuesto configurables descritos en los planes —normalmente de 8 a 12 turnos cuando la configuración y el contexto lo permitan—, pero esta etapa no debe reconstruir todavía el planificador final de tokens. Debes hacer que la memoria completa autorizada llegue al ContextBundle y al camino real de composición existente; no basta con almacenarla en una dataclass que el prompt nunca utiliza.

Preguntas como “¿Eso es preocupante?”, “¿Y el anterior?”, “Explícamelo más sencillo”, “Pero entonces, ¿por qué?” o “¿Qué pasa con las plaquetas?” deben disponer siempre del diálogo y de las entidades activas necesarias para que el LLM resuelva la referencia de forma semántica. Los regex pueden conservarse únicamente como señales deterministas de alta confianza o ayudas de extracción; nunca deben ser el interruptor que elimina toda la memoria.

No persistas errores técnicos como mensajes del asistente y no incluyas en la ventana respuestas que nunca superaron validación o no se confirmaron en PostgreSQL.

B. Separación entre conversación y contexto clínico

Separa explícitamente la evolución del diálogo de la evolución de los datos clínicos. Deben existir conceptos distintos y coherentes equivalentes a:

conversation_revision

clinical_context_revision o clinical_data_revision

Un nuevo hemograma, un cambio de perfil o una actualización clínica debe modificar la revisión y el fingerprint clínicos, pero no borrar, ocultar, reiniciar ni volver inaccesible el transcript anterior de la misma conversación autorizada. A la vez, la conversación previa no debe congelar datos clínicos obsoletos: los hechos clínicos se recargan desde PostgreSQL en cada turno y sustituyen la información clínica anterior para efectos de factualidad.

El fingerprint clínico canónico debe considerar, según el alcance disponible:

Perfil autorizado.

Análisis y parámetros.

Resultados ML estructurados.

Hallazgos autorizados.

Calidad y confianza.

Laboratorio, analizador y procedencia.

Revisión del contexto.

No uses textos narrativos del formatter, resúmenes del LLM ni afirmaciones del transcript como entrada factual del fingerprint. No conviertas un resumen conversacional en ClinicalFact, no lo autorices para claims y no permitas que reemplace IDs, cifras, unidades o procedencia de PostgreSQL.

Los resúmenes sirven únicamente para continuidad lingüística. Deben estar tipados o estructurados de manera que distingan tema, entidades activas, preferencias y estado conversacional de cualquier dato clínico. Si un resumen menciona un valor médico, ese texto sigue sin ser evidencia y debe revalidarse contra el ContextBundle clínico actual antes de poder utilizarse en una respuesta.

C. Persistencia y ciclo de vida de las conversaciones

Corrige la persistencia conversacional sin debilitar propiedad, idempotencia ni concurrencia:

El transcript completo debe permanecer en PostgreSQL.

Una conversación no puede eliminarse simplemente por superar una hora de antigüedad.

El TTL debe aplicarse a leases, bloqueos, idempotencia o recursos temporales que realmente lo requieran, no al transcript ni a los mensajes persistidos.

Abrir o consultar una conversación no debe ejecutar una limpieza global que elimine conversaciones de otros usuarios.

El navegador, pestaña o identificador de sesión del cliente no puede ser la frontera de propiedad. La autoridad es el usuario autenticado junto con el alcance autorizado de la conversación.

Debes evitar la mezcla entre conversación general sin mascota, conversación general con mascota, hemograma seleccionado e historial; tampoco deben mezclarse mascotas o análisis diferentes.

Conserva la semántica atómica y el conflicto tipado de complete_turn() implementados en la etapa 1. Si necesitas adaptar la persistencia para las revisiones separadas, no reintroduzcas retornos silenciosos ni éxitos locales no confirmados.

Mantén la representación exacta de números clínicos; no vuelvas a pasar valores por conversiones que transformen 150 en 15 o alteren decimales.

Debes resolver de manera explícita y uniforme la continuidad cuando falta conversation_id. Para conciliar ambos planes:

Un conversation_id suministrado es la referencia autoritativa para continuar esa conversación concreta y debe validarse por usuario y alcance.

Si no se suministra, no debes asociar una conversación basándote únicamente en navegador o sesión. Recupera automáticamente la conversación más reciente solo cuando exista una única conversación compatible del mismo usuario y del mismo alcance clínico —modo, mascota y análisis cuando apliquen— y esa conducta sea compatible con el contrato público vigente; si la resolución es ambigua, inicia una nueva conversación en lugar de adivinar.

La API debe devolver o conservar el identificador resuelto para que los turnos siguientes puedan continuar de forma explícita.

Nunca recuperes una conversación de otro usuario, otra mascota, otro análisis o un alcance incompatible.

No modifiques el frontend para compensar esta lógica; el alcance sigue siendo el backend LLM y sus adaptadores directos.

D. Estado conversacional de insistencia

Implementa y persiste un estado estructurado de seguridad conversacional equivalente a:

{
  "blocked_action": "medication_request",
  "blocked_action_count": 2,
  "last_safety_level": "referral_required",
  "last_boundary_explained": true
}

Este estado debe pertenecer a la conversación autorizada, actualizarse de manera atómica y estar disponible para el ResponsePlan y las etapas posteriores. Debe distinguir una insistencia real de una pregunta nueva o educativa, y debe reiniciarse o cambiar de acción con reglas explícitas para no acumular falsos positivos indefinidamente.

En esta etapa solo se construye y conecta la memoria de insistencia. No rehagas todavía el clasificador de seguridad, no amplíes la taxonomía de routing y no redactes respuestas, rechazos o derivaciones nuevas. El estado es información determinista interna; cualquier prosa visible seguirá correspondiendo a la etapa generativa posterior.

Límites estrictos

Trabaja únicamente en backend/app/modules/llm_chat/** y en los puntos directos de persistencia, API o configuración del LLM estrictamente necesarios para esta etapa. No modifiques frontend, entrenamiento ML, extracción, formatter hematológico, modelos generales de negocio ni datos aguas arriba. Los defectos externos deben registrarse como dependencias, no corregirse fuera de alcance.

No avances a:

La nueva taxonomía completa de routing y seguridad.

La eliminación total de respuestas hardcodeadas o del origen determinista temporal.

El nuevo envelope generativo, claims, validación y regeneración.

La unificación definitiva de prompts y el presupuesto con tokenizer real.

El RAG multilingüe, reranker o cambios de ingesta.

El cambio de modelo o ampliación de contexto.

Streaming, observabilidad final o limpieza del monolito.

Puedes realizar los ajustes mínimos de integración necesarios para que la memoria llegue al flujo activo, pero no utilices esta etapa como excusa para implementar funcionalidades posteriores.

Queda totalmente prohibido crear, modificar, borrar, regenerar, leer como especificación o ejecutar tests. No toques tests/, no actualices fixtures o snapshots, no ejecutes suites y no hagas búsquedas amplias que incluyan la carpeta de tests. Excluye explícitamente tests/ de las búsquedas de código. Tampoco crees scripts ad hoc cuyo propósito sea probar comportamiento como sustituto de una suite. El cierre se realizará mediante revisión estática del diff, análisis de contratos, imports y tipos, parseo o compilación estática de los archivos de producción afectados y búsquedas dirigidas exclusivamente sobre código de producción. No levantes servicios, bases de datos, Chroma, FastAPI u Ollama.

No alteres cambios ajenos del workspace, no limpies el repositorio de forma destructiva y no realices commit, push, merge o rebase salvo autorización explícita.

Forma de trabajo y condición de cierre

Antes de editar, inspecciona la ruta canónica desde la API hasta SendChatMessageUseCase, el repositorio de conversaciones, los modelos de persistencia, ConversationMemory, ContextBundle, el constructor creado en la etapa 2 y todos sus consumidores reales. Localiza específicamente dónde se descartan mensajes, resumen y estado; dónde se cambia la revisión clínica; dónde se aplican expiración y limpieza; cómo se resuelve conversation_id; y cómo se confirma complete_turn().

Después implementa la solución en el código de producción, conectándola a la única ruta activa. No dejes contratos huérfanos, dos repositorios de memoria, rutas paralelas, TODOs que sustituyan la implementación, migraciones incompletas ni compatibilidad silenciosa que conserve el comportamiento defectuoso.

La etapa quedará cerrada cuando, por inspección estática, pueda demostrarse que:

La memoria reciente autorizada está disponible en todos los turnos, no solo en seguimientos detectados por regex.

El último intercambio, la ventana, el resumen y las entidades activas llegan al camino real de composición.

La memoria no funciona como evidencia clínica y los datos clínicos se recargan desde PostgreSQL.

La revisión conversacional está separada de la revisión clínica.

Un cambio clínico no borra ni oculta el diálogo.

No existe expiración destructiva de transcripts ni limpieza global durante una consulta normal.

La propiedad depende del usuario y del alcance, no del navegador.

La resolución sin conversation_id es determinista y no mezcla contextos.

El estado de insistencia se persiste y queda disponible sin generar prosa visible.

La atomicidad de complete_turn() y la exactitud numérica permanecen intactas.

Al terminar, detente: no comiences la etapa 4. Entrega un informe final preciso que incluya:

Qué encontraste de las etapas 1 y 2 y cómo lo reutilizaste.

Qué archivos de producción modificaste o creaste.

Cómo llega la memoria a todos los turnos y al ContextBundle/prompt activo.

Cómo separaste las revisiones conversacional y clínica.

Cómo quedó la persistencia, propiedad, expiración y resolución de conversaciones.

Cómo funciona el estado de insistencia y cuáles son sus límites actuales.

Qué validaciones estáticas realizaste y su resultado.

Qué dependencias o riesgos quedan para etapas posteriores.

Confirmación explícita de que no creaste, modificaste, leíste como especificación ni ejecutaste tests, que no levantaste servicios y que no implementaste etapas posteriores.

Esta tarea es crítica para la continuidad segura del chat. Debe ejecutarse de manera profesional, detallada, exhaustiva y coherente con los cuatro documentos obligatorios, los prompts anteriores, los informes de las etapas 1 y 2 y el estado real del repositorio, concentrándose solamente en la etapa 3 unificada definida aquí.