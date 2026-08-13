# Aceptación real del chat con Ollama/Qwen

Esta suite es opcional porque necesita un runtime Ollama y el modelo Qwen local.
No utiliza un cliente LLM falso. Ejecuta el `SendChatMessageUseCase` activo con
los prompts, clasificación, selección de contexto, validación, reparación y
persistencia conversacional SQLAlchemy reales.

Los datos del paciente son sintéticos y se crean en una base SQLite temporal de
pytest. El recuperador entrega un documento veterinario controlado para probar
de forma reproducible el contrato RAG, incluida su atribución. La prueba no lee
ni modifica usuarios o hemogramas reales.

## Requisitos

- Ollama accesible desde el proceso de pytest. Para una instalación nativa suele
  ser `http://127.0.0.1:11434`; el Compose de HemoVet mantiene Ollama en su red
  interna y se debe usar una URL alcanzable de esa red.
- Modelo `qwen3:4b-instruct-2507-q4_K_M` instalado.
- Entorno Python del backend disponible.

## Ejecución

Desde la raíz del repositorio:

```bash
RUN_OLLAMA_ACCEPTANCE=1 \
  OLLAMA_ACCEPTANCE_REPETITIONS=5 \
  OLLAMA_ACCEPTANCE_BASE_URL=http://127.0.0.1:11434 \
  OLLAMA_ACCEPTANCE_MODEL=qwen3:4b-instruct-2507-q4_K_M \
  PYTHONPATH=backend .venv/bin/pytest -q -s \
  backend/tests/llm_chat/test_ollama_qwen_acceptance.py
```

En Linux, si Ollama fue iniciado con el Compose del proyecto y no se publicó su
puerto al host, se puede resolver la URL de la red interna antes de ejecutar:

```bash
OLLAMA_CONTAINER_ID="$(docker compose ps -q ollama)"
OLLAMA_CONTAINER_IP="$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$OLLAMA_CONTAINER_ID")"
RUN_OLLAMA_ACCEPTANCE=1 \
  OLLAMA_ACCEPTANCE_REPETITIONS=5 \
  OLLAMA_ACCEPTANCE_BASE_URL="http://${OLLAMA_CONTAINER_IP}:11434" \
  OLLAMA_ACCEPTANCE_MODEL=qwen3:4b-instruct-2507-q4_K_M \
  PYTHONPATH=backend .venv/bin/pytest -q -s \
  backend/tests/llm_chat/test_ollama_qwen_acceptance.py
```

Sin `RUN_OLLAMA_ACCEPTANCE=1`, pytest recopila el archivo y lo omite de forma
explícita. Si se habilita la suite pero Ollama o el modelo no están disponibles,
la prueba falla: no informa un falso resultado aprobado.

Variables opcionales:

| Variable | Predeterminado | Propósito |
| --- | --- | --- |
| `OLLAMA_ACCEPTANCE_CONTEXT` | `4096` | Contexto operativo |
| `OLLAMA_ACCEPTANCE_MAX_TOKENS` | `384` | Máximo de salida |
| `OLLAMA_ACCEPTANCE_TEMPERATURE` | `0.1` | Temperatura |
| `OLLAMA_ACCEPTANCE_TIMEOUT` | `90` | Timeout por solicitud al proveedor |
| `OLLAMA_ACCEPTANCE_KEEP_ALIVE` | `10m` | Residencia solicitada a Ollama |
| `OLLAMA_ACCEPTANCE_REPETITIONS` | `1` | Repeticiones completas; usar `5` como evidencia de release |

## Cobertura e invariantes

La suite cubre:

- chat general con evidencia RAG y fuente visible;
- fixture longitudinal de 24 parámetros por estudio y conservación de códigos
  diferentes para `NEU` absoluto, `NEU_PCT`, `LYM`/`LYM_PCT` y MPV;
- valor directo de WBC en el hemograma seleccionado;
- seguimiento que conserva el parámetro y el análisis;
- explicación prudente de un patrón hematológico del análisis seleccionado;
- parámetro ausente (células en banda) sin inventar un valor;
- preguntas contextualizadas para el veterinario sin falsos
  `absent_parameter_*`;
- modo histórico disponible ante una intención general;
- transición temporal WBC bajo → alto con ambos estudios y fechas;
- rechazo generativo de inyección, diagnóstico definitivo y dosis;
- persistencia terminal de cada turno (`completed` para solicitudes permitidas
  y `refused` para el caso de seguridad) y aislamiento de las tres
  conversaciones por contexto.

Las aserciones no comparan una respuesta completa literal. Verifican hechos,
unidades, estados, dimensión temporal, seguridad, atribución, identidad del
contexto y terminación. Al finalizar, pytest imprime un objeto
`OLLAMA_ACCEPTANCE_REPORT` con modelo, dispositivo, latencias, intentos de
generación y resultado por caso, sin volcar prompts ni respuestas clínicas.
