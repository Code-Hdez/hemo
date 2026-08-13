# 04 - Capítulo II - Solución propuesta (pasada de agosto)

## Bien: la contradicción de julio (38 vs 43 características) está resuelta

El documento actual dice consistentemente **43 características** en todas las
apariciones de este capítulo (líneas 429, 791, 799, 835). El bloqueante de
julio ya no aplica.

## Tres errores factuales nuevos, verificados contra código en vivo

### 1. Orden de la cadena de extracción invertido

Línea 793: *"El flujo de extracción principal está implementado mediante
OpenRouter Gemma; como alternativas implementada tenemos OpenRouter Nemotron,
Google Gemini como solución de respaldo remota y una solución de respaldo
local"* — es decir, dice que Gemma es el método principal y Gemini es un
respaldo.

El código real (`backend/app/modules/gemini_extraction/service.py:31-66`,
función `build_default_attempts`) construye la cadena en este orden exacto:
**1. Gemini, 2. OpenRouter Gemma, 3. OpenRouter Nemotron, 4. fallback local**
— Gemini va primero, no al final. Corregir el orden en el texto.

### 2. Ruta del endpoint de demo incorrecta

Línea 1003 (sección 2.6.3): *"el portal invoca el endpoint de análisis
hematológico versionado, **POST /api/v1/hematology/analyze**"*.

Verificado en `backend/app/modules/hematology/router.py:15,44` — el router se
declara `APIRouter(tags=["Hematology"])` **sin prefijo**, y se monta
directamente bajo `/api/v1` (`backend/app/api/v1/api.py:21`). La ruta real es
**`POST /api/v1/analyze`** (y `/api/v1/analyze/confirmed`, `/api/v1/extract`)
— sin el segmento `/hematology`. Los endpoints de chat citados en la misma
sección (`POST /api/v1/chat`, `POST /api/v1/chat/stream`) sí son correctos
(verificado en `llm_chat/api/router.py:60,484,580`).

### 3. LLM del stack de software desactualizado

Tabla 5 (línea 971): *"Ollama + Llama 3-2B | Open-source (Apache 2.0)"*.
Mismo problema que en Cap I — producción corre `qwen3:4b-instruct-2507-q4_K_M`,
no Llama 3.2. Ver `03_capitulo_i_marco_teorico/README.md` para la evidencia
completa (SSH en vivo, 2026-08-02).

## Pendiente sin verificar en esta pasada: v3 vs v4

Línea 791 dice *"El núcleo analítico consiste en un modelo v3"* — pero
Capítulo V (5.2) y Capítulo VI (6.1.3, 6.3.3) documentan que el modelo se
reentrenó a **v4** después de la validación clínica (S4, retiene 7 etiquetas,
mejoras en QC_REQUIERE_FROTIS y PATRON_POLICITEMIA). Este capítulo nunca
menciona esa evolución. Ver `05_capitulo_iii_metodologia/README.md` para el
mismo hallazgo con más detalle — decidir si conviene mencionar v4 aquí
también o dejarlo solo como referencia hacia adelante ("ver Cap. VI").

## Evidencia

Verificación de código citada arriba corrida directamente sobre el repo
(`backend/app/modules/gemini_extraction/service.py`,
`backend/app/modules/hematology/router.py`, `backend/app/api/v1/api.py`) el
2026-08-02. No se copiaron archivos — referenciar las rutas indicadas.
