# Fase 2 — Resumen ejecutivo

**Investigación read-only. Nada modificado.** Worktree al empezar y al terminar:
`HEAD 21f18fd8889541dbd947c3692ccbdc0fc6ee0660`, rama `main`, **0 ficheros
modificados**. Evidencia en `evidence/git_head_antes.txt` y `git_status_antes.txt`.

---

## Lo primero: tres correcciones a la Fase 1

Esta fase no confirmó la anterior. **La corrigió en tres puntos, y dos de ellos
invalidan sus recomendaciones principales.**

### C-1 · La trazabilidad Git→producción está CERRADA (era `NO_OBSERVABLE`)

Dentro del contenedor en ejecución:

```
HEMOVET_BUILD_REVISION=21f18fd8889541dbd947c3692ccbdc0fc6ee0660
git rev-parse HEAD (local) = 21f18fd8889541dbd947c3692ccbdc0fc6ee0660
```

Coinciden exactamente. Imagen `backend@sha256:86833576b609be…`, desplegada desde
`/opt/hemovet-prod/releases/c1193ae29dc95275606acd7b5c5abafb8170aa02/`,
contenedor creado el **2026-08-06T19:13:03Z**, anterior a la batería del
2026-08-07T23:49Z.

→ **`CONFIRMADO`: el código leído es exactamente el que produjo las 70
respuestas.** Todo el análisis de código de ambas fases queda validado.

### C-2 · La decodificación restringida YA está en uso (la Fase 1 la propuso como mitigación)

`infrastructure/llm/openai_compatible_client.py:751`:

```python
payload["format"] = request.response_schema
```

con el esquema de `GeneratedResponseEnvelope.model_json_schema()`
(`services/structured_response.py:688`). El propio commit `bd70e0d8` lo dice:
*«`format` y `tools` nunca se envían juntos: una gramática que fuerza el sobre no
deja tokens en los que emitir una llamada de herramienta»*.

→ **La mitigación nº 4 de la Fase 1 («generación con gramatica/JSON Schema»)
estaba ya implementada.** Y la consecuencia es más importante que la corrección:
si la gramática garantiza la **forma**, entonces `policy_rule_id_missing` y
`PLT:value,PLT:unit` **no son fallos de forma**. Son fallos de **contenido
semántico**: el modelo emite un sobre estructuralmente válido cuyos campos no
referencian los identificadores correctos. **Ninguna técnica de constrained
decoding puede arreglar eso**, porque una gramática no sabe qué `policy_rule_id`
existe ni qué analito pedía la pregunta.

### C-3 · El salvage por claim YA está desplegado y NO evita los fallos

La Fase 1 lo situó como mitigación **P0** basándose en el mensaje del commit
(«neither wired into a turn yet»). Ese mensaje era cierto **en su momento**;
después llegaron `9bb39866` y `21f18fd8`.

En HEAD —que es producción, por C-1— `_claim_rejection` se define en
`send_chat_message.py:4634` y **se invoca en la línea 4941**, dentro del bucle de
salvage (`kept`, `first_rejection`).

→ **Está vivo, corriendo, y los 17 `generation_repair_failed` ocurrieron con él
activo.** El propio comentario del código explica por qué no basta: *«si ninguno
sobrevive, la primera rechazo se eleva exactamente como antes»*. En el caso PLT,
`materialized_fact_count = 1`: el único claim que importa es el que falla, así
que no queda nada que salvar.

**La mitigación nº 1 de la Fase 1 queda invalidada.**

---

## Lo que la Fase 2 revalidó y reforzó

### El reparto de latencia, ahora con doble corroboración independiente

| Fuente | prefill | decode | % decode |
|---|---:|---:|---:|
| Telemetría del backend (133 llamadas) | 551 s | 4.241 s | **88,5 %** |
| Log de `llama-server` (138 tareas) | 572 s | 4.360 s | **88,4 %** |

Dos relojes distintos, dos sistemas que no se conocen, **misma cifra**. Y la
verificación cruzada de tokens:

- `eval_count`: **133 de 133 coinciden (100 %)** entre ambas fuentes → el lado
  decode está corroborado token a token.
- `prompt_eval_count`: coinciden 98 de 133 (73,7 %). **La discrepancia no es
  error: es la firma del caché.** Ollama informa del prompt completo;
  `llama-server` informa de lo que realmente evaluó.

### El caché de prefijo, ahora cuantificado

`llama-server` procesó **376.870 tokens de los 496.909** contenidos en los
prompts → **el caché ahorra el 24,2 % de los tokens de entrada**. 37 de 138
tareas entraron con menos de 1.000 tokens de prefill (una con **4**).

> **Consecuencia aritmética, y es el argumento que cierra el debate del caching:**
> el prefill es el 11,5 % del tiempo del modelo y ya se está ahorrando el 24,2 %
> de él. Una optimización de prefill *perfecta* —eliminar el 100 % restante—
> recortaría **~8,7 % de la latencia total**. Es el techo, no la estimación.

---

## El mapa causal, en una frase por causa

| # | Causa | Estado | Contribución |
|---|---|---|---|
| 1 | **Decode de 27B en L4**: 13,05 tok/s, limitado por ancho de banda | `CONFIRMADO` (doble fuente) | 88,4 % del tiempo del modelo |
| 2 | **Amplificación de generación**: 1,9 llamadas por pregunta, 60 % descartado | `CONFIRMADO` | ×1,9 sobre la causa 1 |
| 3 | **Fallo semántico del contrato**, no de forma (la gramática ya actúa) | `CONFIRMADO` por C-2 | 1/10 de acierto a la primera |
| 4 | **La reparación no repara**: 0/9, mismo detalle, incluso a temp 0,1 | `CONFIRMADO` | 41,6 % del cómputo |
| 5 | **El salvage no cubre el caso de un solo claim** | `CONFIRMADO` por C-3 | los 17 fallos ocurrieron con él activo |
| 6 | **Clasificador de ámbito regex** rechaza su propio dominio | `CONFIRMADO` | 3/5 preguntas de cortesía |

**Producto de 1 y 2:** el usuario espera ~59 s de mediana porque el sistema
genera **dos respuestas completas a 13 tok/s** para entregarle una — y en 17 de
70 casos, ninguna.

---

## Las cinco mitigaciones con mayor respaldo, tras las correcciones

| P | Mitigación | Por qué, con la evidencia |
|---|---|---|
| **P0** | **Reparación dirigida al campo que falta, sin nueva inferencia** | El fallo es semántico y concreto (`policy_rule_id`, `PLT:value`). El sistema ya *sabe* qué falta —lo publica en `validation_detail_code`—. Regenerar 300 tokens para añadir un identificador que el backend conoce es el desperdicio más claro del sistema |
| **P0** | **Suprimir la 2.ª llamada tal cual está** | 0 de 9 éxitos medidos, ~23 s de GPU cada vez. Es coste puro. El último recurso (4/9) hace el trabajo |
| **P1** | **Revisar la exigencia de `policy_rule_id`** | Es el detalle que más rechazos causa (15) y mata al último recurso 5 de 9 veces |
| **P1** | **Modelo pequeño para ámbito, identidad y guardarraíles** | Hoy una pregunta de identidad cuesta 19-23 s a 13 tok/s. Socratic Tutor lo resuelve con un modelo aparte |
| **P2** | **Speculative decoding / MTP** | Es la única técnica que ataca la causa 1, que es la dominante. Requiere cambio de motor y experimento |

**Degradadas respecto a la Fase 1:** constrained decoding (ya está), salvage
(ya está), prefix caching (techo del 8,7 %).

---

## Lo que sigue sin poder observarse

**Si la primera generación era clínicamente correcta.** Y tras C-2 la pregunta
es más precisa e importante: como la gramática garantiza la forma, lo que se
descarta es un sobre **bien formado**. Saber si su *contenido* era correcto
decide entre `VALIDATOR_FALSE_POSITIVE` y `VALIDATOR_TRUE_POSITIVE`, y con ello
toda la estrategia.

Sigue siendo `NO_OBSERVABLE` por tres vías comprobadas. El experimento **E-1**
(volcado controlado) sigue siendo el de mayor valor de todo el backlog.

---

*Ver `14_FINAL_REPORT.md` para el desarrollo completo, `10_ROOT_CAUSE_MATRIX.md`
y `11_MITIGATION_MATRIX.md` para las matrices corregidas.*
