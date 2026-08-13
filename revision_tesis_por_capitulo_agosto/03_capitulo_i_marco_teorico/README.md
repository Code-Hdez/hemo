# 03 - Capítulo I - Marco teórico (pasada de agosto)

## Estado verificado: mayormente resuelto, un error factual heredado

Julio pidió agregar Cohen's kappa al glosario y reforzar la explicación de
validación clínica. Ambos **ya están**: la entrada "Cohen's kappa" existe
(línea 713), y 1.1.2 explica con detalle por qué se necesita validación
externa con veterinarios (variabilidad interobservador, kappa como medida
adecuada). El ciclo operativo del LLM/RAG (1.1.3.6, líneas 623-631) describe
correctamente las 5 etapas: filtros determinísticos → recuperación semántica
→ contexto controlado → generación → validación de salida — consistente con
el pipeline real verificado en `06_capitulo_iv_analisis_diseno/`.

## Error factual: modelo LLM incorrecto (mismo problema que en Cap II)

El glosario define dos veces (líneas 721 y 737) **"Llama 3-2B"** como el LLM
principal de HemoVet:

- *"LLM (Large Language Model)... Como modelo principal en HemoVet: Llama 3-2B"*
- *"Ollama: ... En el caso de Llama 3-2B, se utiliza en HemoVet para garantizar
  la privacidad..."*

Verificado en producción (SSH a `hemovet-prod`, 2026-08-02): el modelo
configurado y efectivamente cargado es **`qwen3:4b-instruct-2507-q4_K_M`**
(`OLLAMA_MODEL` en `.env`, confirmado también vía `/api/v1/chat/health` →
`runtime.model`). `llama3.2:3b` existe en el servidor Ollama como uno de
cinco modelos descargados, pero no es el configurado para producción. Mismo
error aparece en Cap II (tabla de software, línea 971) — ver
`04_capitulo_ii_solucion_propuesta/README.md`. Corregir en ambos sitios a la
vez para no dejar el documento internamente inconsistente.

## No verificado en esta pasada

Las 45+ entradas de glosario clínico-veterinario (líneas 651-780) no se
contrastaron contra literatura — son afirmaciones de dominio clínico, no
verificables contra este repositorio de código.
