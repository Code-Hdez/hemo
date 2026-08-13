# Asistente conversacional LLM + RAG v2 de HemoVet

HemoVet es un asistente educativo especializado en hemogramas caninos. Puede
explicar conceptos y mostrar los datos autorizados de una mascota, pero no emite
diagnósticos definitivos, recetas, medicamentos ni dosis y no sustituye una
evaluación veterinaria.

El chat no es un buscador de fragmentos. Cada turno combina, según su intención,
memoria conversacional, datos clínicos estructurados de PostgreSQL y evidencia
de un corpus veterinario curado. El backend decide de forma determinista qué
datos y acciones están autorizados; Qwen redacta las respuestas permitidas,
incluidos saludos y redirecciones naturales fuera del dominio. Los errores de
infraestructura y el fallback estricto de seguridad sí son deterministas.

## Flujo del turno

```text
request autenticado
  │
  ├─ validar conversación, usuario, modo y revisión de contexto
  ├─ cargar memoria: ventana reciente + resumen + estado estructurado
  ├─ recuperar mascota/hemograma(s) autorizados desde PostgreSQL
  ├─ resolver referencias: “eso”, “el anterior”, “el primer tema”
  ├─ clasificar intención y elegir ruta
  │    ├─ general: explicación veterinaria o redirección de dominio
  │    ├─ seleccionada: hechos exactos del estudio autorizado
  │    ├─ histórica: series temporales de los estudios autorizados
  │    └─ RAG: conocimiento documental separado de los datos del paciente
  ├─ generar la redacción permitida con Qwen
  ├─ validar seguridad y claims solo contra los hechos materializados al modelo
  ├─ si hace falta, pedir hasta dos reescrituras acotadas al mismo Qwen
  ├─ proteger el nombre exacto `HemoVet`
  ├─ proyectar solo bibliografía y evidencia pública permitidas
  └─ persistir respuesta, memoria, fuentes, tokens y latencias
```

El modelo y los pesos viven fuera de FastAPI. El composition root crea una vez
los clientes HTTP, embeddings, colección y repositorios; una petición nunca
vuelve a cargar el modelo, recalcula embeddings documentales ni procesa Markdown.
Las generaciones se serializan cuando el runtime solo admite una a la vez. La
cola tiene un plazo explícito (`CHAT_QUEUE_TIMEOUT_SECONDS`) y el turno completo
otro (`CHAT_TOTAL_TIMEOUT_SECONDS`), de modo que una segunda petición espera de
forma acotada en vez de fallar a los tres segundos mientras la interfaz mantiene
visible el estado de generación.

## Modos de conversación

El contrato canónico reconoce tres modos:

| Modo | Identificador | Contexto autorizado |
| --- | --- | --- |
| General | `general` | Memoria de la conversación y evidencia veterinaria cuando hace falta; nunca inventa datos de una mascota. |
| Hemograma seleccionado | `selected_hemogram` | Mascota y estudio identificado por `analysis_id`, con valores, unidades, rangos, flags y procedencia. |
| Historial | `hemogram_history` | Todos los estudios autorizados de la mascota identificada por `pet_id`, ordenados cronológicamente y con comparaciones de unidades compatibles. |

Durante la transición se aceptan los aliases públicos `uploaded_analysis` y
`historical_analysis`. Los clientes nuevos deben enviar los nombres canónicos;
en el alias histórico todavía se admite `analysis_id` para resolver la mascota.

Un cambio de modo, mascota o hemograma crea una clave de contexto diferente. El
backend incrementa `context_revision` y el frontend puede enviar
`expected_context_revision` para impedir que una respuesta tardía se asocie a
una selección anterior.

### Datos del hemograma

El frontend nunca es la fuente de verdad clínica. Los identificadores se validan
contra el usuario autenticado y el backend construye un objeto tipado desde
`analyses`, `analysis_parameters` y `pets`. El prompt recibe claves de estudio
neutras (`H1`, `H2`, etc.), no UUID internos.

Cada parámetro conserva:

- nombre original, canónico y visible;
- valor decimal y precisión textual;
- unidad original y normalizada;
- límites de referencia disponibles;
- origen del intervalo (`laboratory`, `validated_catalog`, legado o desconocido);
- flag registrado y flag derivado;
- confianza y procedencia de extracción;
- observaciones o contradicciones que requieren verificar el documento.

Se prioriza el intervalo del laboratorio. No se convierte una unidad sin una
función validada ni se compara una serie con unidades incompatibles. Si falta un
dato o su confianza es baja, el asistente lo declara en lugar de inventarlo.

Los hechos completos permanecen en metadata privada como
`authorized_case_facts`: forman el universo de autorización y auditoría. Para
cada turno, el selector crea además un subconjunto reclamable con los parámetros
que sí llegaron al prompt; tanto la primera validación como las reescrituras se
limitan a ese subconjunto. Así, por ejemplo, un MPV autorizado pero no expuesto
no puede legitimar una cifra inventada por el modelo.

La respuesta pública expone en `case_facts` únicamente
el parámetro consultado y su valor, sin unidad, rango, flag, fecha, confianza ni
procedencia:

```json
[{ "parameter": "WBC", "value": "10.4" }]
```

Una comparación usa una sola fila: `[{ "parameter": "WBC", "value": "8.2 → 10.4" }]`.
La unidad aparece en la respuesta textual. Rango, clasificación y fecha se
añaden solo cuando el usuario los solicita. Las respuestas hematológicas,
clínicas, de seguridad o urgencia contienen exactamente una advertencia pública:
`La respuesta es educativa y no sustituye una evaluación veterinaria`. Identidad,
saludos, conversación social y temas fuera de dominio no muestran ese aviso.

## Memoria híbrida en servidor

`chat_sessions` y `chat_messages` persisten la conversación por usuario. La
memoria enviada al modelo contiene:

1. una ventana acotada de mensajes recientes (`CHAT_HISTORY_LIMIT`);
2. un resumen acumulativo limitado por `CHAT_SUMMARY_MAX_CHARS`;
3. estado estructurado con tema, parámetro, mascota, hemograma y comparación;
4. los datos clínicos actuales consultados nuevamente desde PostgreSQL.

El resumen no sustituye datos clínicos. La sesión expira según
`CHAT_SESSION_TTL_SECONDS`; iniciar una conversación nueva o cambiar de contexto
evita reutilizar referencias incompatibles. `client_message_id` proporciona
idempotencia por turno.

El frontend activo guarda en `sessionStorage` solo un marcador efímero con el
`conversation_id`, la clave de contexto y su revisión. Se usa para eliminar la
conversación remota anterior como mejor esfuerzo, nunca para restaurar su
transcript. Cambiar de modo, mascota o análisis, recargar o abandonar la pestaña
limpia los mensajes y el registro local; al regresar se crea una conversación
remota nueva mediante `POST /chat/conversations`. Los mensajes y hechos clínicos
no se copian al almacenamiento del navegador.

## RAG v2

### Corpus e ingesta

Producción indexa únicamente la ruta Markdown versionada
`knowledge_base/expert_review/approved/`. El nombre de la carpeta no se considera
evidencia de revisión veterinaria independiente: la ingesta valida los estados y
el reporte académico debe distinguir decisiones provisionales. El proceso offline:

- valida frontmatter, estado de curación y procedencia;
- resuelve cada fuente contra `knowledge_base/manifests/sources_manifest.json`;
- pone en cuarentena documentos que no resuelven a una fuente canónica;
- divide por encabezados, párrafos y tablas antes de aplicar el límite de
  palabras y el solapamiento;
- conserva capítulo, sección, páginas explícitas, edición, autores, fragmentos
  vecinos, revisión del catálogo y versión del esquema;
- crea IDs deterministas e indexa de forma idempotente en ChromaDB.

La configuración base de v2 es:

```env
RAG_SOURCE_DIR=knowledge_base/expert_review/approved
RAG_COLLECTION_NAME=hemovet_canine_hematology_v2__<fingerprint-12-hex>
RAG_SCHEMA_VERSION=hemovet-rag-v2
RAG_SOURCE_MANIFEST=knowledge_base/manifests/sources_manifest.json
RAG_EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
RAG_EMBEDDING_DIMENSION=384
RAG_CHUNK_SIZE_WORDS=90
RAG_CHUNK_OVERLAP_WORDS=15
RAG_TOP_K=3
RAG_ALLOW_TEST_DOCUMENTS=0
RAG_ALLOW_AI_PROVISIONAL=0
```

Los valores 90/15 forman parte del fingerprint completo del índice. Cambiarlos
exige construir y validar una colección inmutable nueva; no se debe reutilizar
una colección cuya segmentación no coincida. Una colección v1 tampoco puede
reutilizarse: cambió el esquema de chunks, la revisión del catálogo y la
bibliografía pública. Antes de promover una versión:

```bash
docker compose run --rm rag_ingest \
  python scripts/ingest_rag.py index --dry-run

docker compose run --rm rag_ingest \
  python scripts/ingest_rag.py index \
  --collection hemovet_canine_hematology_v2 --stage --prune
```

El segundo comando emite el nombre fingerprinted que debe validarse y promoverse
mediante `RAG_COLLECTION_NAME`. El flujo nunca reconstruye ni borra la colección
activa. Consulta [Promoción y rollback del índice RAG](rag-index-promotion.md)
para los pasos de validación, cambio atómico y rollback.

### Recuperación y generación fundamentada

Cuando el perfil del turno requiere conocimiento documental, la consulta
autocontenida y sus expansiones terminológicas se ejecutan en paralelo contra
recuperación vectorial y BM25. Los rankings se fusionan mediante RRF, se filtran
por especie, dominio, estado, relevancia y permiso de cita, se limita la
repetición por libro y se conserva un máximo de `RAG_TOP_K` evidencias. El
adaptador de reranking permanece en la línea base explícita `none`: un modelo
multilingüe solo puede promoverse si mejora Recall@5 sin regresión y supera la
puerta de MRR o nDCG con el dataset curado del proyecto. Saludos, identidad,
errores y respuestas basadas solo en hechos estructurados no fuerzan
recuperación ni una fuente bibliográfica artificial.

El prompt separa instrucciones estables, política del turno, memoria, contexto
clínico, hechos, evidencia y pregunta con JSON delimitado. Todo mensaje, dato
extraído, metadata o fragmento recuperado se considera contenido no confiable,
nunca una instrucción. El validador de salida impide dosis, tratamiento,
diagnóstico definitivo, razonamiento interno y hechos clínicos contradictorios.

### Fuentes visibles

La respuesta pública no expone rutas, filenames, IDs de chunks, IDs de libros ni
scores. `sources` contiene únicamente:

```json
{
  "citation_id": "S1",
  "display_title": "Schalm's Veterinary Hematology",
  "authors": ["Douglas J. Weiss", "K. Jane Wardrop"],
  "edition": "6th",
  "chapter": "Leukocyte Disorders",
  "section": "Leukocytosis",
  "page_start": 123,
  "page_end": 125,
  "source_type": "book"
}
```

Los campos ausentes no se inventan. Las fuentes solo aparecen en rutas que usaron
RAG y cuya evidencia fue aceptada; respuestas sociales, de identidad o fuera de
dominio no llevan bibliografía. La interfaz muestra referencias, no permite
descargar libros ni expone el texto completo del corpus.

## Runtime de generación

Desarrollo local (`.env.example`) usa la variante pequeña no razonadora Qwen3
4B Instruct 2507 servida por Ollama:

```env
CHAT_LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://ollama:11434/
OLLAMA_MODEL=qwen3:4b-instruct-2507-q4_K_M
OLLAMA_CONTEXT_LENGTH=4096
OLLAMA_NUM_PREDICT=384
OLLAMA_TEMPERATURE=0.1
OLLAMA_THINK=0
```

Producción (`.env.production.example`) declara el **perfil cualificado**
Qwen3.6 27B Q4_K_M con ventana de 64K:

```env
OLLAMA_MODEL=qwen3.6:27b-q4_K_M
OLLAMA_EXPECTED_QUANTIZATION=Q4_K_M
OLLAMA_CONTEXT_LENGTH=65536
CHAT_MAX_INPUT_TOKENS=60000
OLLAMA_NUM_PREDICT=2048
CHAT_TOKENIZER_REQUIRED=1
```

`PromptBudgetPlanner` (`application/services/prompt_budget_planner.py`) es la
única autoridad de presupuesto para ambos perfiles: construye la candidatura
completa —política, contexto clínico autorizado, memoria, evidencia RAG,
pregunta y el JSON Schema de salida—, la cuenta con `TokenCounter` usando la
plantilla de chat real y, si excede `CHAT_MAX_INPUT_TOKENS`, reduce por
unidades completas (nunca a mitad de un chunk, mensaje o hecho) en el orden:
fuentes RAG menos relevantes, resumen de memoria, historial, observaciones,
estado conversacional y, como último recurso, estudios históricos completos.
Si los bloques obligatorios no caben ni así, la solicitud nunca llega al
proveedor: se persiste un error técnico, no una respuesta recortada.

`OLLAMA_EXPECTED_MODEL_DIGEST` y `CHAT_TOKENIZER_SHA256` deben declararse con
los valores reales una vez instalado el modelo cualificado; esta
documentación no afirma que Qwen3.6 27B, su digest ni su `tokenizer.json`
estén instalados en ningún entorno — son dependencias operativas explícitas,
verificadas de forma fail-closed por `TokenCounter` y por
`validate_deploy_env.py`, no supuestos.

### NVIDIA local

El compose base conserva compatibilidad CPU. En un host NVIDIA, después de que
`nvidia-smi` funcione y de instalar NVIDIA Container Toolkit, se activa:

```env
COMPOSE_FILE=docker-compose.yml:docker-compose.gpu.yml
BACKEND_WEB_CONCURRENCY=1
OLLAMA_KEEP_ALIVE=-1
OLLAMA_CONTEXT_LENGTH=65536
OLLAMA_NUM_PARALLEL=1
OLLAMA_MAX_LOADED_MODELS=1
OLLAMA_FLASH_ATTENTION=1
OLLAMA_KV_CACHE_TYPE=q8_0
```

En Omarchy/Arch el toolkit se instala con
`omarchy pkg add nvidia-container-toolkit`. Después se configura el runtime con
`sudo nvidia-ctk runtime configure --runtime=docker`, se reinicia Docker y se
recrea el stack. `docker compose exec -T ollama ollama ps` debe mostrar
`100% GPU`. Flash Attention y una caché `q8_0` son
ajustes opcionales que solo deben promoverse después de medir estabilidad y
memoria en el hardware definitivo; no forman parte del perfil reproducible.

`thinking` es una decisión exclusiva del servidor mediante `OLLAMA_THINK`
(`CHAT_REPAIR_THINK` para la reparación); no forma parte del contrato público
de `/chat` — la API ya no acepta ni traduce ninguna opción de cliente para
activarlo. Si se configura deliberadamente un modelo razonador,
`OLLAMA_THINK=1` habilita el canal privado nativo de Ollama; el adaptador de
HemoVet consume exclusivamente `message.content` y `message.thinking` nunca
se persiste, registra ni envía al navegador. El perfil cualificado vigente
mantiene `OLLAMA_THINK=0`.

Para un runtime externo compatible con la API de OpenAI:

```env
CHAT_LLM_PROVIDER=openai_compatible
OPENAI_COMPATIBLE_BASE_URL=https://runtime.example/v1
OPENAI_COMPATIBLE_MODEL=qwen3:8b
OPENAI_COMPATIBLE_API_KEY=<secret-del-proveedor>
OLLAMA_AUTO_PULL=0
```

La URL debe ofrecer `/chat/completions` y `/models`. La clave se inyecta como
secreto y nunca se registra. El compose incluido sigue levantando los servicios
Ollama; al usar un runtime externo quedan sin tráfico y se desactiva su descarga
con `OLLAMA_AUTO_PULL=0`. Una topología que no quiera reservar esos recursos debe
proporcionar un overlay propio y validar su `docker compose config`.

## Contrato HTTP

Los endpoints aceptan la cookie HttpOnly `hemovet_session` o
`Authorization: Bearer <JWT>`:

- `POST /api/v1/chat`: respuesta JSON completa, ya validada y persistida.
- `POST /api/v1/chat/stream`: SSE de estados —
  `start`, `context_ready`, `retrieval_completed`, `generation_started`,
  `final`, `done`, `error`, más `heartbeat` en conexiones largas. No es
  streaming progresivo de tokens: `final` y `done` llevan el mismo
  `ChatResponse` completo, ya validado y persistido, y ninguno de los dos se
  emite antes de ese commit.
- `POST /api/v1/chat/conversations`: crea una sesión con contexto autorizado.
- `GET /api/v1/chat/conversations`: lista sesiones activas del login actual.
- `DELETE /api/v1/chat/conversations/{id}`: elimina una sesión propia.
- `GET /api/v1/chat/conversations/{id}/messages`: historial propio paginado.
- `GET /api/v1/chat/health`: estado sanitizado del runtime y RAG.

General:

```json
{
  "client_message_id": "f02da308-d383-4b55-8e7e-81bb238e03da",
  "conversation_id": null,
  "message": "¿Qué función tienen las plaquetas?",
  "context_scope": "general"
}
```

Hemograma seleccionado:

```json
{
  "client_message_id": "a545a4ae-c03e-42b4-81cc-8510f04bcaca",
  "conversation_id": null,
  "message": "¿Qué valor de leucocitos aparece?",
  "context_scope": "selected_hemogram",
  "analysis_id": "analysis-id-autorizado"
}
```

Historial:

```json
{
  "client_message_id": "433d664f-22e4-4428-984b-fb0786608ac2",
  "conversation_id": null,
  "message": "¿Cómo cambiaron los leucocitos?",
  "context_scope": "hemogram_history",
  "pet_id": "pet-id-autorizado"
}
```

Para seguimientos, reutilizar `conversation_id` y enviar un
`client_message_id` nuevo. Cuando el frontend conoce la revisión actual también
envía `expected_context_revision`.

El SSE informa las etapas y solo publica la respuesta después de la validación
de seguridad. No se promete que cada token del proveedor llegue inmediatamente:
la prioridad actual es impedir que un borrador clínicamente inválido se muestre
parcialmente.

## Instalación y operación

Desde la raíz:

```bash
cp .env.example .env
export HEMOVET_BUILD_REVISION="$(git rev-parse --short HEAD)"
docker compose up -d --build
docker compose ps
docker compose logs rag_ingest ollama_setup backend --tail=120
curl -fsS http://localhost:8000/health/operational
curl -fsS http://localhost:8000/api/v1/chat/health
```

`/health/operational` debe mostrar la revisión esperada en
`build_revision` y la política `clinical-claims-v4` en
`chat_policy_revision`. El código del backend se copia dentro de la imagen; un
reinicio sin `--build` puede dejar activa una política anterior aunque el
workspace ya contenga la corrección.

Instalación manual del backend:

```bash
cd backend
python -m pip install -r requirements.txt
python -m pip install -r requirements.ml.txt
python -m pip install -r requirements.local-extraction.txt
alembic -c alembic.ini upgrade head
python scripts/ingest_rag.py index --dry-run
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

La ingesta real necesita ChromaDB accesible; el dry-run no modifica la colección.
FastEmbed descarga el modelo configurado la primera vez y usa
`RAG_EMBEDDING_CACHE_DIR` en ejecuciones posteriores.

## Pruebas y evaluación

Backend:

```bash
python --version  # debe informar Python 3.11.x según .python-version
python -m pip install -r backend/requirements-dev.txt
APP_ENV=test \
DATABASE_URL=sqlite+pysqlite:///:memory: \
SECRET_KEY=test-secret-key-with-at-least-32-characters \
HEMOVET_ENABLE_LOCAL_ML=0 \
HEMOVET_ENABLE_LOCAL_EXTRACTION=1 \
PYTHONPATH=backend \
python -m pytest backend/tests -q
python -m ruff check backend/app backend/scripts/validate_deploy_env.py \
  backend/tests/llm_chat backend/tests/test_deploy_env.py \
  backend/tests/test_environment_contract.py
python -m pytest tools/llm_cbc_eval/tests -q
```

Frontend:

```bash
cd frontend_4
npm test
npm run check
npm run build
```

Evaluación autenticada de los tres modos:

```bash
cp tools/llm_cbc_eval/config/eval.config.example.json \
  tools/llm_cbc_eval/config/eval.config.json

export HEMOVET_EVAL_EMAIL='usuario-evaluacion@example.com'
export HEMOVET_EVAL_PASSWORD='secret-local'
export HEMOVET_EVAL_SELECTED_ANALYSIS_ID='analysis-id-real'
export HEMOVET_EVAL_HISTORICAL_PET_ID='pet-id-real'

python tools/llm_cbc_eval/src/runner.py \
  --config tools/llm_cbc_eval/config/eval.config.json \
  --questions tools/llm_cbc_eval/data/acceptance_cases.yaml
```

El banco extendido reproducible está en
`tools/llm_cbc_eval/data/questions.yaml`; el archivo `acceptance_cases.yaml`
encadena los diez turnos mínimos y los casos críticos de la defensa.

### Evidencia de una versión concreta

Los conteos y latencias de reportes históricos no se consideran evidencia del
workspace actual. Antes de una defensa o release se deben comprobar también
`build_revision` y `chat_policy_revision`, repetir las suites,
la matriz canónica y la aceptación autenticada con Ollama/Qwen real, y archivar
un reporte que incluya commit, configuración, modelo, dispositivo, resultado por
modo, errores terminales y latencias. Una suite con clientes falsos valida
contratos, pero no debe denominarse prueba real del modelo.

No se deben versionar el archivo de configuración local, tokens, contraseñas ni
IDs que identifiquen datos reales. Los reportes sirven como evidencia de la
ejecución; las reglas deterministas verifican contrato y seguridad, pero una
revisión veterinaria sigue siendo necesaria para valorar calidad clínica.

## Checklist antes de una defensa

1. Aplicar Alembic y confirmar las migraciones de memoria y parámetros.
2. Ejecutar dry-run, construir una candidata con `--stage --prune` y promoverla
   únicamente después de `--validate-only` si la colección proviene de v1 o
   cambió cualquier componente del fingerprint.
3. Verificar runtime, `rag_ready` y `chunk_count > 0`.
4. Probar un valor exacto seleccionado y contrastarlo con PostgreSQL.
5. Probar historia con al menos dos estudios y unidades compatibles.
6. Mantener diez turnos, usar pronombres y regresar al primer tema.
7. Cambiar hemograma y confirmar la nueva revisión/contexto.
8. Probar identidad, amor y Python; las dos últimas deben redirigirse al dominio
   de HemoVet sin usar datos clínicos ni mostrar fuentes RAG.
9. Probar diagnóstico, dosis, emergencia y prompt injection.
10. Abrir “Ver fuentes” y confirmar título, edición, sección y páginas sin paths.
11. Intentar un análisis de otro usuario y confirmar una respuesta sin fuga de
    datos.
12. Guardar reportes y latencias p50/p95/máxima del entorno de demostración.

## Observabilidad y límites reales

Los logs estructurados registran ruta, intención, uso de RAG, candidatos,
fuentes, tokens, modelo y latencias por etapa. No deben registrar secretos,
documentos completos ni prompts clínicos sin protección. Los percentiles p50 y
p95 se calculan sobre una corrida del evaluador o en la plataforma de métricas;
un único healthcheck no demuestra rendimiento conversacional.

Limitaciones que permanecen por diseño:

- HemoVet es apoyo educativo, no un dispositivo diagnóstico ni un veterinario.
- La calidad depende de datos extraídos correctamente y del corpus aprobado; una
  confianza baja exige revisar el documento original.
- Qwen3 4B permite una instalación local contenida, pero su calidad y latencia
  deben medirse en el hardware exacto de la demostración.
- El runtime externo, ChromaDB y PostgreSQL son dependencias operativas; su caída
  debe mostrarse como indisponibilidad recuperable, no como una respuesta clínica.
- Las pruebas automatizadas verifican hechos, aislamiento y reglas; no sustituyen
  validación clínica humana ni justifican afirmar exactitud universal.
