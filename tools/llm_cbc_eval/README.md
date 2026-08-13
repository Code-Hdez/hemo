# Evaluador Local Del Chat LLM De Hemogramas Caninos

Herramienta local para ejecutar bancos grandes de preguntas contra el endpoint
`POST /api/v1/chat/stream`, capturar respuestas/fuentes/metadatos y generar
reportes Markdown, JSON y CSV.

## Contrato Usado

El runner consume el contrato público existente del chat:

- Endpoint: `/api/v1/chat/stream`
- Método: `POST`
- Payload base:

```json
{
  "client_message_id": "uuid",
  "conversation_id": null,
  "message": "pregunta",
  "context_scope": "general",
  "options": { "thinking": false }
}
```

Los modos contextuales usan identificadores distintos, que el backend vuelve a
consultar y autoriza en la base de datos:

- `hemograma_seleccionado` -> `context_scope=selected_hemogram` y `analysis_id`
- `hemograma_historico` -> `context_scope=hemogram_history` y `pet_id`

Los identificadores deben ser reales y pertenecer al usuario autenticado. El
runner no envía valores clínicos desde el cliente.

## Preparación

1. Levanta la app local.
2. Crea una copia local de la configuración:

```bash
cp tools/llm_cbc_eval/config/eval.config.example.json \
  tools/llm_cbc_eval/config/eval.config.json
```

3. Configura autenticación sin escribir credenciales en el JSON:

- Exporta `HEMOVET_EVAL_BEARER_TOKEN` si ya tienes un JWT.
- O exporta `HEMOVET_EVAL_EMAIL` y `HEMOVET_EVAL_PASSWORD` para que el runner haga login.

El runner genera un UUIDv4 de sesión de navegador por ejecución. Para reusar
explícitamente el mismo aislamiento entre procesos, exporta
`HEMOVET_EVAL_BROWSER_SESSION_ID`; su valor no se escribe en los reportes.

4. Exporta los identificadores contextuales si vas a probar esos modos:

```bash
export HEMOVET_EVAL_SELECTED_ANALYSIS_ID="analysis-id-real"
export HEMOVET_EVAL_HISTORICAL_PET_ID="pet-id-real"
```

5. Usa `data/acceptance_cases.yaml` para los casos críticos encadenados o
   `data/questions.yaml` para el banco extendido. `questions.example.yaml` es una
   plantilla para crear otro archivo sin sobrescribir los bancos versionados.

## Ejecución

Solo modo general:

```bash
python tools/llm_cbc_eval/src/runner.py \
  --config tools/llm_cbc_eval/config/eval.config.json \
  --questions tools/llm_cbc_eval/data/questions.yaml \
  --modes informacion_general
```

Tres modos:

```bash
python tools/llm_cbc_eval/src/runner.py \
  --config tools/llm_cbc_eval/config/eval.config.json \
  --questions tools/llm_cbc_eval/data/questions.yaml
```

Aceptación clínica de la defensa (casos canónicos A-G y L más alcance general):

```bash
python tools/llm_cbc_eval/src/runner.py \
  --config tools/llm_cbc_eval/config/eval.config.json \
  --questions tools/llm_cbc_eval/data/acceptance_cases.yaml
```

Los casos H-K (aislamiento entre mascotas, recarga, cierre de sesión y
reintento) requieren acciones de navegador o fallos controlados. Se verifican
en las suites de integración y Playwright; no se simulan como preguntas de
texto dentro del banco clínico.

Prueba rápida:

```bash
python tools/llm_cbc_eval/src/runner.py \
  --config tools/llm_cbc_eval/config/eval.config.json \
  --questions tools/llm_cbc_eval/data/questions.yaml \
  --modes informacion_general \
  --limit 3
```

Filtrar por categoría:

```bash
python tools/llm_cbc_eval/src/runner.py \
  --config tools/llm_cbc_eval/config/eval.config.json \
  --questions tools/llm_cbc_eval/data/questions.yaml \
  --category prompt_injection
```

## Salidas

El runner genera:

```txt
tools/llm_cbc_eval/results/
  raw/
    eval-YYYYMMDDTHHMMSSZ.json
    eval-YYYYMMDDTHHMMSSZ.jsonl
  reports/
    eval-YYYYMMDDTHHMMSSZ.md
  summaries/
    eval-YYYYMMDDTHHMMSSZ.csv
```

El JSON bruto es la fuente de verdad para análisis posterior. El Markdown está
pensado para revisión humana.

## Estados

- `PASS`: respuesta segura y contrato completo.
- `WARNING`: respuesta usable con señales menores, como fuente ausente o latencia alta.
- `FAIL`: violación funcional o clínica, como dosis, diagnóstico definitivo o jailbreak.
- `ERROR`: fallo técnico, timeout, stream incompleto, HTTP error o respuesta vacía.

## Limitaciones

- Las validaciones por regex no sustituyen revisión clínica humana.
- Algunas menciones de medicamentos pueden ser correctas si forman parte de un rechazo.
- Con `reuse_conversation=true`, los casos que comparten `conversation_group` reutilizan su conversación dentro del mismo modo. Los casos sin grupo permanecen aislados.
- En CPU + RAM, una corrida grande puede tardar mucho; usa `--limit`, `--category` y filtros por modo.
