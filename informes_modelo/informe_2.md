Investigación terminada. El hallazgo central cambia el diagnóstico inicial: **HemoVet sí utiliza salida estructurada**. Envía un JSON Schema a Ollama mediante `format`, obliga al modelo a generar `claims`, IDs, evidencias y siete indicadores de seguridad, y luego devuelve otro JSON público mediante `ChatResponse`. [Sobre estructurado](https://github.com/Code-Hdez/hemo/blob/50954156d945ebea32d4f65c64e843f1bb734419/backend/app/modules/llm_chat/application/services/structured_response.py#L103-L263), [contrato público](https://github.com/Code-Hdez/hemo/blob/50954156d945ebea32d4f65c64e843f1bb734419/backend/app/modules/llm_chat/api/schemas.py#L164-L241).

La recomendación concreta es:

* **Salida del modelo:** Markdown/texto natural en español.
* **Validación:** determinista en el backend sobre la respuesta completa.
* **Salida para frontend:** conservar el JSON tipado actual con `answer`, fuentes, hechos, métricas y estado.
* **Generación:** exactamente una llamada a Ollama.
* **Fallo:** error terminal tipado, sin regenerar ni persistir una respuesta inválida.

Si se exige JSON también entre Ollama y el backend, la segunda opción es un esquema mínimo con un único campo `answer_markdown`. No recomiendo conservar el envelope actual ni cambiarlo por YAML/XML.

La evidencia más fuerte:

* 45 turnos A100.
* 10 reparaciones: **22,2 %**.
* En historial: 7/15 reparaciones, **46,7 %**.
* Mediana sin reparación: **16,3 s**.
* Mediana con reparación: **44,05 s**.
* Solo 2/10 reparaciones fueron por JSON/schema; las otras 8 fueron por metadatos semánticos como `fact_id`, atribución, contenido insuficiente o clasificación de claims.

Por tanto, establecer simplemente `CHAT_MAX_GENERATION_ATTEMPTS=1` dejaría aproximadamente 10/45 turnos actuales fallando. Primero debe simplificarse el contrato.

También confirmé que el techo real no es dos intentos: el código puede ejecutar generación principal, reparación, generación reconducida y último recurso —hasta cuatro respuestas—, además del posible reintento HTTP. [Flujo completo](https://github.com/Code-Hdez/hemo/blob/50954156d945ebea32d4f65c64e843f1bb734419/backend/app/modules/llm_chat/application/use_cases/send_chat_message.py#L1669-L2005). HTTPX además repite conexiones cuando `retries=1`. [Documentación de HTTPX](https://www.python-httpx.org/advanced/transports/).

Socratic Tutor aporta una idea útil: decidir ALLOW/STEER antes de generar. Pero no debe copiarse literalmente, porque utiliza un modelo estructurado para la guardia y otro para responder; es decir, normalmente son dos llamadas. [Guardia](https://github.com/cristiandlahoz/socratic-tutor/blob/29b8c224940c6c200a3f4182fb1c4b9a2fcb1ebb/src/main/java/com/wornux/ai/guard/GuardClassifierService.java#L68-L137), [respuesta principal](https://github.com/cristiandlahoz/socratic-tutor/blob/29b8c224940c6c200a3f4182fb1c4b9a2fcb1ebb/src/main/java/com/wornux/services/chat/ChatService.java#L56-L103).

La documentación y la literatura confirman que Structured Outputs garantiza la forma, no la exactitud de los valores ni la corrección médica. [Ollama](https://docs.ollama.com/capabilities/structured-outputs), [JSONSchemaBench](https://arxiv.org/html/2501.10868v3), [estudio sobre restricciones de formato](https://arxiv.org/html/2408.02442v1).

El informe incluye arquitectura propuesta, inventario exacto de código/configuración que retirar, contrato de error, plan de latencia 10–15 segundos, criterios de aceptación y una ablación A/B/C:

[Descargar el informe técnico completo](sandbox:/workspace/scratch/954761334f9b/INFORME_FORMATO_SALIDA_Y_GENERACION_UNICA_HEMOVET_2026-08-12.md)
