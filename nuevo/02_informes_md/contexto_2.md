Terminé la auditoría estática del backend completo en main, fijado en el commit b9ddd75. Revisé 177 archivos Python —aproximadamente 46,600 líneas— además de prompts, configuración, despliegue,
  documentación y pruebas existentes como especificaciones, sin ejecutarlas.

  No ejecuté tests, compilaciones ni servicios. Tampoco modifiqué archivos ni toqué los cambios actuales del workspace.

  ## Conclusión

  El chat de main no cumple todavía los requisitos definidos. No es principalmente un problema del modelo Qwen: el backend impide que el modelo responda libremente mediante varias capas simultáneas:

  1. El RAG funciona como permiso obligatorio.
  2. El router solo comprende bien hematología canina.
  3. En hemograma seleccionado e historial, el contrato permite repetir valores, pero prácticamente prohíbe explicarlos.
  4. Gran parte de la información existente en PostgreSQL nunca llega al modelo.
  5. La memoria se descarta en la mayoría de los turnos.
  6. Variables del .env son limitadas o sustituidas por constantes posteriores.
  7. Existen varias respuestas visibles generadas por código.
  8. Los validadores bilingües rechazan traducciones y paráfrasis correctas.
  9. Hay defectos de integridad en los datos que alimentan al chat.

  Cambiar de 4B a 9B o aumentar el contexto no corregirá ninguno de estos bloqueos.

  ## Estado real de los tres modos

   Modo                      Lo que recibe actualmente                                       Problema principal
  ━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   General                   Pregunta, reglas, RAG y memoria solo en algunos seguimientos    La API prohíbe pet_id; sin RAG puede abstenerse; preguntas veterinarias fuera de CBC se rechazan
  ────────────────────────  ──────────────────────────────────────────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
   Hemograma seleccionado    Perfil parcial y un análisis                                    El contrato reduce la respuesta a valores literales y elimina la posibilidad de combinar esos datos con
                                                                                             explicaciones RAG
  ────────────────────────  ──────────────────────────────────────────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
   Historial                 Perfil parcial y varios análisis                                El formato compacto pierde hallazgos ML, observaciones y calidad; la comparación se reduce a pocos parámetros y
                                                                                             afirmaciones

  ## Fallos críticos que deben resolverse primero

  ### 1. El RAG es obligatorio globalmente

  RAG_ENABLED=1 termina significando que el chat completo requiere RAG:

  - backend/app/modules/llm_chat/infrastructure/composition.py:328
  - backend/app/core/availability.py:142

  Si ChromaDB o el índice no están disponibles, chat_ready queda falso. Esto puede impedir hasta saludos, explicaciones generales y límites de seguridad.

  Cuando la recuperación devuelve cero documentos, una pregunta general termina como INSUFFICIENT_EVIDENCE:

  - backend/app/modules/llm_chat/application/use_cases/send_chat_message.py:1049

  Incluso después de una generación válida, todavía existe lógica que vuelve a marcar la respuesta como evidencia insuficiente si la política original contenía use_rag=True.

  Debe sustituirse el booleano use_rag por decisiones independientes:

  retrieval_policy = NONE | OPTIONAL | REQUIRED
  retrieval_status = NOT_NEEDED | HIT | NO_MATCH | UNAVAILABLE
  knowledge_mode = PARAMETRIC | RAG_AUGMENTED | DATABASE_GROUNDED

  NO_MATCH nunca debe equivaler automáticamente a allow_answer=False.

  ### 2. No todas las respuestas visibles son generadas

  Continúan existiendo textos clínicos y de seguridad escritos directamente en Python:

  - Diagnóstico.
  - Dosis.
  - Medicamentos.
  - Tratamiento.
  - Emergencias.
  - Prompt injection.
  - Fuera de ámbito.
  - Falta de evidencia.
  - Requerimiento de hemograma.

  Están en backend/app/modules/llm_chat/application/use_cases/send_chat_message.py:4577.

  También se agrega por código:

  > Conviene revisar estos resultados con un profesional veterinario.

  en backend/app/modules/llm_chat/application/use_cases/send_chat_message.py:3433.

  Y se reemplazan respuestas generadas por oraciones canónicas como:

  > El valor de WBC del 03/08/2026 es…

  en backend/app/modules/llm_chat/application/use_cases/send_chat_message.py:3551.

  Esto contradice directamente el requisito de que toda respuesta visible sea generada.

  La arquitectura correcta es:

  Reglas internas deterministas
          ↓
  Plan de respuesta
          ↓
  Generación LLM obligatoria
          ↓
  Validación
          ↓
  Regeneración si incumple
          ↓
  Respuesta generada

  La única excepción debe ser un error técnico de la interfaz cuando el proveedor no pueda generar nada válido.

  ### 3. Hemograma seleccionado e historial no pueden explicarse correctamente

  Cuando existen hechos clínicos, patient_supported domina sobre las fuentes documentales. El esquema permite solo PATIENT_FACT y excluye los claims basados en RAG:

  - backend/app/modules/llm_chat/application/use_cases/send_chat_message.py:2261
  - backend/app/modules/llm_chat/application/use_cases/send_chat_message.py:2371

  Además, el modelo debe seleccionar frases exactas proyectadas por el backend, sin interpretación:

  - backend/app/modules/llm_chat/application/services/structured_response.py:566

  Consecuencia práctica:

  Dato PostgreSQL: WBC = 18.2
  RAG: explicación de leucocitosis
  Modelo: debería explicar el valor
  Contrato actual: solo puede repetir “El valor de WBC es 18.2...”

  Esto explica por qué el modo seleccionado “ve” algunos datos, pero parece no entenderlos.

  El contrato debe permitir simultáneamente:

  - PATIENT_FACT: valores exactos de PostgreSQL.
  - DOCUMENTARY_EXPLANATION: explicación respaldada por fuentes.
  - GENERAL_EDUCATION: conocimiento paramétrico prudente.
  - SAFETY_BOUNDARY: límites médicos generados.

  ### 4. El perfil de la mascota llega incompleto

  PostgreSQL contiene más información de la que el chat utiliza. El modelo de mascota conserva peso, notas y residencia:

  - backend/app/modules/pets/models.py:19

  Pero PatientContext solo contiene:

  - ID.
  - Nombre.
  - Especie.
  - Raza.
  - Sexo.
  - Edad.

  Véase backend/app/modules/llm_chat/domain/clinical.py:51 y el mapeo SQL en backend/app/modules/llm_chat/infrastructure/persistence/sqlalchemy_repositories.py:1861.

  Se pierden:

  - Peso.
  - Notas.
  - Ciudad o residencia.
  - Información clínica adicional disponible.
  - Fecha de nacimiento precisa; la edad se calcula solo restando años.

  En modo general, el problema es mayor: la API prohíbe enviar pet_id:

  - backend/app/modules/llm_chat/api/schemas.py:57

  Por tanto, actualmente es imposible implementar correctamente un chat general “sobre tu mascota”.

  ### 5. Los hallazgos ML existen, pero no son hechos autorizados utilizables

  Los estudios pueden contener:

  - Resultado del clasificador.
  - Observaciones.
  - Calidad.
  - Parámetros extraídos.
  - Valores calculados.

  El prompt completo puede incluir parte de ello, pero authorized_facts está construido principalmente con valores de laboratorio. Los contratos estructurados no permiten al modelo afirmar de forma natural
  los hallazgos ML.

  En historial, el formato compacto elimina precisamente clasificador, observaciones y calidad:

  - backend/app/modules/llm_chat/domain/clinical.py:237

  Debe existir una separación clara:

  LAB_FACT
  ML_FINDING
  QUALITY_FINDING
  PET_PROFILE_FACT
  DOCUMENTARY_EVIDENCE

  Cada dato necesita ID, procedencia, fecha y reglas propias de validación.

  ### 6. La memoria se elimina en casi todos los mensajes

  El seguimiento solo se reconoce con un grupo estrecho de expresiones colocadas al inicio del mensaje:

  - backend/app/modules/llm_chat/application/services/conversation_memory.py:45

  Luego, si el mensaje no fue clasificado como seguimiento o solicitud explícita de historial, se eliminan:

  - Mensajes anteriores.
  - Resumen.
  - Estado conversacional.

  Esto ocurre en backend/app/modules/llm_chat/application/use_cases/send_chat_message.py:2092.

  Por eso pueden fallar preguntas como:

  - “¿Eso es preocupante?”
  - “¿Y el anterior?”
  - “Explícamelo más sencillo.”
  - “Pero entonces, ¿por qué?”
  - “¿Y qué pasa con las plaquetas?”

  Además, existe un error concreto al serializar números en memoria: se eliminan ceros finales incluso en enteros. Valores como 150 pueden convertirse en 15, y 500 en 5:

  - backend/app/modules/llm_chat/application/services/conversation_memory.py:329

  Este es un defecto crítico de integridad clínica.

  ### 7. Las conversaciones no son realmente persistentes

  Aunque se guardan en PostgreSQL:

  - Expiran después de una hora.
  - El acceso a una conversación elimina todas las sesiones expiradas globalmente.
  - El borrado se propaga a turnos, mensajes y eventos RAG.
  - Cuando el frontend no manda conversation_id, el caso de uso fuerza una conversación nueva en lugar de restaurar la anterior.
  - La asociación con navegador dificulta continuar desde otra pestaña o dispositivo.

  También existe una condición de carrera: complete_turn() puede retornar silenciosamente si el turno ya no está en el estado esperado, mientras el caso de uso devuelve al usuario la respuesta local como si
  hubiera sido persistida:

  - backend/app/modules/llm_chat/infrastructure/persistence/sqlalchemy_repositories.py:864

  ## Variables del .env ignoradas o sustituidas

  El .env sí se carga. El problema es la precedencia posterior.

   Configuración                                    Comportamiento real
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   OLLAMA_CONTEXT_LENGTH                            Los perfiles vuelven a limitarlo a 4096
  ───────────────────────────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────────
   OLLAMA_NUM_PREDICT                               El perfil fija 512; el wrapper estructurado obliga un mínimo de 512 aunque .env diga 384
  ───────────────────────────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────────
   Contexto conversacional                          Se vuelve a recortar a 3072
  ───────────────────────────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────────
   RAG_FETCH_K, RAG_TOP_K, RAG_MAX_CONTEXT_CHARS    Los perfiles imponen otros valores
  ───────────────────────────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────────
   CHAT_HISTORY_LIMIT=0                             La memoria obliga al menos un elemento
  ───────────────────────────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────────
   options.thinking de la API                       Se recibe, pero el comando fuerza False
  ───────────────────────────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────────
   OLLAMA_TIMEOUT_SECONDS                           No gobierna el timeout canónico
  ───────────────────────────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────────
   max_per_source                                   Está fijado a 2 en composición

  Los límites principales están en:

  - backend/app/modules/llm_chat/application/services/chat_profile_policy.py:34
  - backend/app/modules/llm_chat/application/use_cases/send_chat_message.py:2111
  - backend/app/modules/llm_chat/application/use_cases/send_chat_message.py:2394

  El contrato de despliegue vuelve a fijar modelo, digest, cuantización, contexto 4096 y salida 384. Por eso cambiar solamente .env o crear un Modelfile no cambia toda la aplicación.

  También hay lectores directos de os.getenv() fuera de Settings. Pydantic puede leer .env sin poblar os.environ, por lo que dos partes de la misma aplicación pueden obtener configuraciones distintas.

  ## Errores de clasificación y seguridad

  Las reglas actuales generan falsos positivos importantes.

  ### “Cuántos” puede interpretarse como dosis

  El patrón de dosis contiene una coincidencia para cuánto/cuántos sin exigir medicamento o unidad:

  - backend/app/modules/llm_chat/domain/safety_policy.py:67

  Preguntas válidas como:

  > ¿Cuántos tipos de leucocitos hay?

  pueden terminar como solicitud de dosis.

  ### Preguntas educativas pueden convertirse en diagnóstico

  La detección de diagnóstico ocurre antes que la intención educativa. Términos como “anemia” pueden hacer que:

  > ¿Qué es la anemia?

  se clasifique como solicitud diagnóstica.

  ### El fallback es exclusivamente hematológico

  Si no aparecen términos CBC o parámetros conocidos, el clasificador cae en OUT_OF_DOMAIN:

  - backend/app/modules/llm_chat/application/services/intent_classifier.py:399

  Esto impide que el producto sea un asistente veterinario general.

  ### El fallback paramétrico deseado se considera prompt injection

  Expresiones como:

  - “Usa tu conocimiento general.”
  - “Responde sin fuentes.”
  - “No uses el RAG.”

  aparecen dentro de patrones de manipulación:

  - backend/app/modules/llm_chat/domain/safety_policy.py:33

  ### No existe detección real de insistencia

  La seguridad solo recibe el mensaje actual. No conoce:

  - Qué acción se bloqueó anteriormente.
  - Cuántas veces insistió el usuario.
  - Qué límite explicó el asistente.
  - Si la petición actual reformula la anterior.

  Se necesita estado como:

  {
    "blocked_action": "medication_request",
    "blocked_action_count": 2,
    "last_safety_level": "referral_required"
  }

  ## Español y fuentes en otros idiomas

  El sistema intenta responder en español mediante prompts y un validador, pero no lo garantiza correctamente.

  Problemas:

  1. La detección de inglés consiste en contar palabras funcionales inglesas consecutivas y un porcentaje aproximado.
  2. No existe un campo obligatorio response_language="es".
  3. El texto chino/japonés/coreano se rechaza directamente.
  4. La recuperación tokeniza principalmente [a-z0-9], perdiendo otros alfabetos.
  5. Los equivalentes están hardcodeados para unos pocos términos español-inglés.
  6. El metadato language del documento se guarda, pero no se utiliza para buscar o rerankear.
  7. El grounding exige alrededor de 60% de coincidencia léxica entre la respuesta española y la oración original, incluso si la fuente está en inglés:
      - backend/app/modules/llm_chat/application/services/structured_response.py:905

  8. La reparación obliga a reutilizar oraciones casi literales de la fuente.

  Por tanto, el sistema puede recuperar correctamente una fuente inglesa y luego rechazar una explicación española correcta.

  La solución necesita:

  - Recuperación semántica independiente del idioma.
  - Expansión de consulta español/inglés.
  - response_language="es" en el contrato.
  - Detector de idioma real.
  - Una regeneración si la salida no es española.
  - Validación semántica cross-lingual, no porcentaje de palabras.
  - Conservar la cita y el fragmento en su idioma original.
  - No traducir ni alterar cifras, unidades o nombres de fuentes.

  ## Problemas adicionales del RAG

  La base ya tiene recuperación densa, BM25 y RRF, pero encontré estas limitaciones:

  - El reranker configurado es NoopReranker.
  - El caso de uso nunca envía las variantes de consulta que el recuperador ya admite.
  - Hay dominios renal, hepático, endocrino, neurológico, reproductivo e inflamatorio excluidos mediante listas hardcodeadas.
  - citation_allowed=False elimina el documento incluso como contexto interno; se confunde permiso de citar con permiso de utilizar.
  - Los filtros de especie, estado y dominio están duplicados y hardcodeados en Chroma y BM25.
  - Si falla dense o BM25, asyncio.gather() aborta toda la recuperación; no existe degradación a uno solo.
  - BM25 normaliza siempre su mejor resultado a 1, haciendo que los umbrales de relevancia pierdan significado.
  - Los IDs de chunks anterior y siguiente se guardan, pero nunca se expanden.
  - El catálogo mostrado al modelo procede del manifiesto completo, no necesariamente de lo realmente indexado.
  - Un Markdown mal formado, ilegible o demasiado grande puede abortar la ingesta completa.
  - bool("false") se interpreta como True al leer ciertos metadatos del catálogo.
  - Cualquier cambio de revisión global modifica los hashes y puede forzar la reindexación completa.
  - El corte de oraciones está preparado principalmente para puntuación y mayúsculas latinas.
  - Los documentos de múltiples especies pueden quedar fuera si el metadato no coincide exactamente.

  Archivos centrales:

  - backend/app/modules/llm_chat/infrastructure/rag/retrieval_service.py:185
  - backend/app/modules/llm_chat/infrastructure/rag/bm25_store.py:87
  - backend/app/modules/llm_chat/infrastructure/rag/chroma_store.py:130
  - backend/app/modules/llm_chat/infrastructure/rag/source_catalog.py:121
  - backend/app/modules/llm_chat/infrastructure/rag/markdown_loader.py:112

  ## Defectos en datos que alimentan al chat

  Estos deben corregirse antes de confiar en cualquier explicación generada.

  ### IDs de análisis de solo ocho caracteres

  Los análisis utilizan un prefijo UUID de ocho caracteres:

  - backend/app/modules/hematology/service.py:284

  Luego se usa session.merge(). Una colisión podría actualizar o sobrescribir un análisis existente y sus parámetros. Debe usarse un UUID completo y una inserción que falle ante colisiones.

  ### Se pierde la fecha real de subida

  El formateador produce _uploaded_at, pero AnalysisResult no declara ese campo y Pydantic lo descarta. Finalmente:

  - created_at termina siendo la fecha de la muestra.
  - performed_at recibe la misma fecha.
  - La fecha real de carga desaparece.

  Esto afecta el orden histórico y comparaciones temporales.

  ### Posible afirmación falsa de normalidad

  Cuando el clasificador ML no activa uno de sus patrones objetivo, el formateador puede guardar:

  > Los valores analizados se encuentran dentro de los rangos de referencia.

  Eso no demuestra que todos los parámetros estén normales; solo indica que no se activó una etiqueta específica:

  - backend/app/modules/hematology/formatter.py:255

  ### Rangos y umbrales críticos hardcodeados

  Los rangos y la regla de “crítico” de ±30% están escritos en Python:

  - backend/app/modules/hematology/formatter.py:86

  No están versionados por laboratorio, analizador, especie, edad o catálogo clínico.

  ### Lectura de archivos sin límite efectivo

  Las rutas de extracción y análisis ejecutan await file.read() sin aplicar HEMOGRAM_FILE_MAX_BYTES:

  - backend/app/modules/hematology/router.py:18

  Un archivo grande puede consumir memoria innecesariamente.

  ### El modo de extracción solicitado se ignora parcialmente

  La API acepta auto, gemini y local, pero la validación normaliza todos los modos válidos a auto. El procesamiento y los metadatos pueden no reflejar lo solicitado.

  ## Streaming y contrato API

  El endpoint utiliza SSE, pero no transmite tokens visibles durante la generación. ValidatedStreamingResponse acumula todo, valida al final y emite una sola delta:

  - backend/app/modules/llm_chat/application/services/streaming_response.py:17

  Otros defectos:

  - Puede haber dos generaciones secuenciales: generación y reparación.
  - Todo se mantiene en buffer.
  - El usuario solo ve estados intermedios.
  - La delta puede contener texto sanitizado, mientras done contiene otra versión.
  - La ruta API acepta thinking, pero siempre construye el comando con thinking=False.
  - response_origin permite únicamente llm, safety_fallback y legacy_deterministic, pero el caso de uso produce deterministic_safety_boundary. Esto puede provocar validación de respuesta y error 500:
      - backend/app/modules/llm_chat/api/schemas.py:110

  ## Presupuesto de contexto

  El contexto efectivo actual sigue siendo aproximadamente:

  3,200 tokens de entrada
  + 512 de salida estructurada
  + 256 de reserva
  ≈ 4,096 tokens

  Además:

  - Las fuentes se recortan por caracteres y pueden quedar cortadas a mitad de tabla u oración.
  - Después se eliminan resumen, historial y estado.
  - El contexto clínico y la política son considerados inmutables.
  - El enorme JSON Schema estructurado se agrega tarde.
  - El presupuesto puede cumplirse antes del esquema y excederse después, terminando en 503.
  - Si no existe tokenizer exacto, se estiman tokens mediante bytes/3.
  - Otra parte usa caracteres/4.
  - El selector limita hechos clínicos por una fórmula heurística, no por coste real de tokens.

  Aumentar num_ctx no soluciona esta composición. Primero debe existir un único planificador de presupuesto.

  ## Código legado y documentación contradictoria

  La ruta canónica es:

  application.py
  → api/v1
  → llm_chat/api/router.py
  → SendChatMessageUseCase

  Existen implementaciones antiguas paralelas como service.py, local_model.py, context.py, knowledge_base.py y kb_ingest.py. No alimentan la ruta principal, pero contienen más:

  - Respuestas fijas.
  - Lecturas directas de entorno.
  - Reglas duplicadas.
  - Modelos RAG antiguos.

  Esto aumenta la posibilidad de corregir el archivo equivocado.

  La documentación afirma que todo el texto visible proviene del LLM, pero el código continúa teniendo fallbacks y anexos deterministas:

  - backend/docs/llm-production-hardening-report.md:109
  - backend/docs/llm-rag.md:8

  Las pruebas existentes también fijan como comportamiento esperado:

  - Seguridad sin invocar al LLM.
  - Mensaje fijo de evidencia insuficiente.
  - RAG necesario para disponibilidad.
  - Límites 512/4096.

  No ejecuté esas pruebas; las leí como parte del contrato existente. Tendrán que cambiar junto con la implementación porque actualmente protegen el comportamiento que se desea eliminar.

  ## Aspectos correctos que conviene preservar

  No todo está mal. Estas bases son valiosas:

  - Validación de propiedad de mascota y análisis.
  - Contextos clínicos tipados.
  - Snapshots de extracción.
  - Parámetros normalizados.
  - Idempotencia de turnos.
  - Arrendamiento de generaciones concurrentes.
  - Fingerprints del corpus.
  - Metadatos de fuentes.
  - Recuperación híbrida dense + BM25 + RRF.
  - Validadores de cifras, unidades, fuentes y seguridad.
  - Reconsulta de PostgreSQL como autoridad clínica.

  Deben conservarse como controles internos, sin convertirlos en textos visibles ni permisos absolutos para responder.

  ## Orden de corrección recomendado

  No empezaría aún por cambiar el modelo ni por ampliar a 128K.

  1. Corregir integridad de datos:
      - UUID completo.
      - Fechas de muestra y subida separadas.
      - Error 150 → 15.
      - Falsa afirmación de normalidad.
      - Límite real de archivos.
      - Modo de extracción.

  2. Crear ResponsePlan y RetrievalPolicy:
      - RAG opcional por defecto.
      - Fallback paramétrico para educación veterinaria.
      - PostgreSQL como autoridad para datos concretos.
      - Fuentes obligatorias solo cuando la petición realmente lo exija.

  3. Eliminar toda prosa visible hardcodeada:
      - Seguridad.
      - Emergencias.
      - Rechazos.
      - Derivaciones.
      - Evidencia insuficiente.
      - Frases canónicas de valores.

  4. Rehacer los contratos generativos:
      - Contratos pequeños por riesgo.
      - Datos clínicos y evidencia documental simultáneos.
      - Sin enumeraciones de oraciones exactas.
      - Validación y regeneración.
      - Error técnico si ninguna generación válida es posible.

  5. Completar el contexto:
      - Permitir pet_id opcional en chat general.
      - Perfil completo autorizado.
      - Hallazgos ML y calidad.
      - Hemograma seleccionado.
      - Historial comparable.
      - Último turno y estado conversacional siempre.
      - No enviar “toda la BD”; seleccionar toda la información relevante para la pregunta.

  6. Centralizar configuración:
      - Settings como única fuente.
      - Perfiles configurables.
      - Eliminar 512, 4096, 3072 y presupuestos RAG hardcodeados.
      - Registrar los valores efectivos enviados al proveedor.

  7. Corregir español y RAG multilingüe:
      - Enrutamiento cross-lingual.
      - Variantes español/inglés.
      - Grounding semántico.
      - Detector real de idioma.
      - Reranker multilingüe.
      - Degradación dense/BM25 independiente.
      - Separar uso documental de permiso de cita.

  8. Corregir memoria, persistencia y streaming.
  9. Dividir send_chat_message.py, que actualmente concentra unas 5,762 líneas, en:
      - Coordinador.
      - Planificador de recuperación.
      - Constructor de contexto.
      - Generador.
      - Validador.
      - Persistencia.

  El primer cambio funcional debe ser eliminar la equivalencia:

  sin RAG = sin respuesta

  pero debe hacerse junto con los contratos clínicos, porque actualmente permitir el fallback paramétrico sin corregir esos contratos seguiría dejando rotos los modos seleccionado e historial.

  En esta fase la revisión fue exclusivamente estática, sin pruebas ni modificaciones. Los números de línea corresponden al main auditado en b9ddd75; el workspace actual puede mostrar diferencias porque
  está en otra rama.