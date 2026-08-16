# Fase 3 — el contrato mínimo ya está implementado, solo está apagado

**Rama:** `fase-3-contrato-minimo` · **Estado:** hallazgo documentado, sin código todavía

---

## El hallazgo

`CHAT_STRUCTURED_OUTPUT_ENABLED` (`app/core/config.py:211`, hoy `True`) **ya hace
casi todo lo que la Fase 3 pide**. `[MEDIDO]` en el código:

| Consecuencia de ponerlo a `0` | Dónde |
|---|---|
| `schema_provider = None` → **no se envía `format` a Ollama**, no hay GBNF | `send_chat_message.py:2611-2619` |
| **No se añade el bloque de contrato al prompt** (`schema_and_block()` devuelve `""`) | `prompt_builder.py`, ruta `render_with_contract` |
| **No se decodifica el sobre**: el texto del modelo se usa tal cual | `send_chat_message.py:4861` |
| **`_last_resort_candidate` deja de dispararse** | `send_chat_message.py:2026`, `2071` |

Es decir: el interruptor entrega **Markdown plano**, que es exactamente el
contrato objetivo de I-3, y de paso desactiva **una de las tres rutas** que I-2
manda eliminar.

> Esto no estaba en ninguno de los tres informes. El plan proponía construir la
> salida en Markdown como trabajo nuevo; el mecanismo ya existe y hasta tiene un
> test de aceptación que lo usa (`test_ollama_qwen_acceptance.py` fija
> `structured_output_enabled=False`).

## Qué se rompe al apagarlo

`[MEDIDO]` Suite completa con `CHAT_STRUCTURED_OUTPUT_ENABLED=0`:
**968 pasan · 38 fallan.**

| Fichero | Fallos | Naturaleza |
|---|---|---|
| `test_structured_send_chat_message.py` | **33** | Prueban el sobre en sí: claims, `fact_ids`, tipos de claim, transiciones. Es el artefacto que se elimina |
| `test_turn_guard.py` | 3 | Los tres son del último recurso, que el interruptor desactiva |
| `test_llm_settings.py` | 1 | Fija el valor por defecto |
| `test_composition.py` | 1 | Cableado del contenedor |

**33 de 38 prueban justo lo que se retira.** Solo 5 necesitan adaptación real.

## Lo que NO resuelve el interruptor, y es el trabajo de verdad

Apagarlo quita el sobre, pero deja huérfano lo que el sobre producía. Antes de
tocar producción hay que reimplementarlo en el servidor (§4.1 del plan):

1. **`fact_ids`** → verificación por coincidencia de valor, unidad, rango y fecha
   sobre el texto completo, contra los hechos que el servidor inyectó.
2. **`source_ids`** → las fuentes efectivamente retenidas, con etiqueta honesta
   («fuentes consultadas»), **nunca** como prueba de cada afirmación.
3. **`evidence_spans`** → si se exige prueba por proposición: segmentar en
   oraciones, filtro léxico y después el verificador ONNX de *entailment* que ya
   está en el repositorio.
4. **`safety`** → `OutputValidator`, que ya lo deriva del texto (§1.4).
5. **`intent` / `response_type`** → del router, que ya los decidió.

**I-5 manda aquí:** ninguna comprobación clínica se relaja. Si al quitar el sobre
alguna validación se queda sin entrada, se reimplementa sobre el texto; no se
elimina. Los 33 tests que fallan son el inventario exacto de lo que hay que
volver a garantizar de otra forma.

## Por qué esto importa para la latencia

`[MEDIDO]` en la Puerta 0: el **67,7 %** de los tokens que el modelo escribe son
sobre, no prosa — 194 de 321. `[DERIVADO]` a los 27,25 ms/token medidos, quitarlo
ahorra **5,28 s por turno** de decodificación pura.

## Orden de trabajo pendiente

1. Reimplementar los cinco derivados en el servidor, con tests **antes** del
   código (§9.3).
2. Triar los 38 tests uno a uno: los 33 del sobre se retiran con justificación
   escrita; los 5 restantes se adaptan.
3. Apagar el interruptor y correr las 45 preguntas.
4. **Puerta 3:** validez de primera pasada **≥ 98 %**, medida por separado en
   General / Seleccionado / Historial, con los reintentos ya desactivados en el
   arnés. Si no se alcanza, **no se pasa a la Fase 4**.

## Hipótesis viva

`[INFERIDO]` Si el interruptor desactiva el último recurso y las 9 secuencias
observadas fueron siempre `main → repair → last_resort`, apagarlo dejaría esos
turnos en `main → repair` (2 llamadas). **No basta para I-2**, que exige 1. La
reparación es ruta aparte y se elimina en la Fase 4 — pero solo después de que
la Puerta 3 demuestre que ya no hace falta.

---

## Addendum — I-5 queda satisfecho por construcción

`[MEDIDO]` `OutputValidator.validate()` (`output_validator.py:158`) tiene esta
firma:

```python
def validate(self, text: str, *, allowed_source_ids, case_facts,
             safety_decision, patient_in_scope) -> OutputValidation
```

Recibe **texto plano**. Un `grep` de `envelope|claims|claim_id|fact_ids|
structured` sobre el fichero entero devuelve **cero coincidencias**.

> **Quitar el sobre no debilita ni una comprobación clínica.** Las validaciones
> de dosis, tratamiento indirecto, diagnóstico definitivo, coherencia con los
> hechos, reconocimiento de valores anormales y parámetros inexistentes ya
> operan sobre el texto completo, con los hechos y la decisión de seguridad que
> **aporta el servidor**, no el modelo.

Esto convierte el riesgo principal de la Fase 3 en un no-riesgo: `OutputValidator`
ya **es** la frontera canónica determinista que I-3 e I-5 describen. Lo que hay
que reimplementar no son las comprobaciones de seguridad —que están intactas—
sino los **derivados de atribución** (`fact_ids`, `source_ids`, `evidence_spans`)
que hoy el modelo autorreporta y que el servidor debe calcular.

---

## Progreso — 13-ago-2026

| Derivado | Estado | Dónde |
|---|---|---|
| `fact_ids` | **Hecho**, 9 tests | `application/services/fact_attribution.py` |
| `source_ids` | **Hecho**, 7 tests | `application/services/source_attribution.py` |
| `evidence_spans` | **No requiere módulo nuevo** | ver abajo |
| `safety` | Ya lo hace `OutputValidator` | sin trabajo |
| `intent` / `response_type` | Ya los decide el router | sin trabajo |

`[MEDIDO]` 1022 tests pasan, `ruff` limpio.

### `evidence_spans` no necesita código nuevo

`[MEDIDO]` Las tres piezas que el plan pide ya existen y están cableadas:

- **Segmentación en oraciones + filtro léxico** → `atribuir_fuentes()` entrega el
  solapamiento por fuente, que es exactamente el filtro previo.
- **Verificador de entailment** → `ClaimEntailmentPort` (`domain/ports/entailment.py`),
  con implementación ONNX en `infrastructure/entailment.py` y construido en
  `composition.py:107`.

`[INFERIDO]` El trabajo restante es de **composición**, no de implementación: encadenar
solapamiento → entailment solo cuando se exija prueba por proposición. El plan lo
condiciona («si se exige prueba por proposición»), y hasta que se exija, la etiqueta
honesta es «fuentes consultadas», que es lo que `atribuir_fuentes()` ya entrega.

Y no viola I-4: el verificador ONNX es un clasificador local, no una segunda llamada
a un LLM.

### Lo que queda para la Puerta 3

1. Enganchar los dos derivados en el caso de uso, detrás del interruptor.
2. Triar los 38 tests (33 prueban el sobre que se retira).
3. Apagar `CHAT_STRUCTURED_OUTPUT_ENABLED` y correr las 45 preguntas con GPU.
4. Validez de primera pasada **≥ 98 %** por ámbito.

### Punto exacto de integración de `source_ids` (pendiente)

`[MEDIDO]` `send_chat_message.py:4905`:

```python
validation, used_source_ids = self._validate(
    candidate, facts, decision, sources,
    coverage_facts=coverage_facts, ...,
    allowed_source_ids=set(request.retained_source_ids),
)
```

`used_source_ids` sale hoy de `_validate`, que lo obtiene del marcador
`[[EVIDENCE_USED:S1,S2]]` que **emite el modelo**. Eso es autodeclaración y I-3
lo prohíbe.

**Cambio pendiente, en una línea:** cuando `envelope is None`, sustituir por
`atribuir_fuentes(candidate.text, sources).consultadas`, que es el hecho del
servidor: las fuentes que efectivamente se retuvieron y metieron en el prompt.

**Por qué no se hizo en esta sesión:** `used_source_ids` alimenta la validación
de citas, que es una comprobación clínica. I-5 exige verificar esa ruta entera
antes de tocarla, y eso pide correr los tests de citación y revisar
`_remove_inline_citations`. Se deja localizado en vez de arriesgado.

**Riesgo si se hace mal:** que una cita quede huérfana y el sanitizador la
elimine del texto publicado, o al revés, que se acepte una cita a una fuente no
retenida. Ninguna de las dos es aceptable.

---

## Riesgo descubierto al triar los tests (13-ago)

`[MEDIDO]` Con `CHAT_STRUCTURED_OUTPUT_ENABLED=0`, **37 tests fallan**: 32 del
sobre, 2 que fijan el valor por defecto de la variable, y **3 de `turn_guard`**:

```
test_the_last_resort_does_not_rescue_what_it_has_no_rewrite_for   assert 2 == 3
test_a_turn_whose_contract_cannot_be_met_answers_instead_of_erroring
test_the_last_resort_is_generated_with_no_patient_data_in_scope
```

Los dos últimos fallan con `ChatRuntimeUnavailable: invalid_output`.

**Qué significa:** el interruptor no solo quita el sobre — **desactiva la red de
rescate**. Un turno cuya validación no pasa hoy es salvado por
`_last_resort_candidate`; sin él, muere con error.

`[MEDIDO]` La Puerta 0 ya lo había visto desde el otro lado: las 9 secuencias
observadas fueron **siempre** `main → repair → last_resort`, es decir, el último
recurso salvó 9 turnos de 45 (**20 %**).

> **Esto NO invalida el plan, pero precisa el riesgo.** La apuesta de la Fase 3
> es que, con el contrato mínimo, la validación pase a la primera y el rescate
> deje de hacer falta. **La Puerta 3 es exactamente la comprobación de esa
> apuesta**, y su umbral —≥ 98 % de validez en primera pasada— es lo que separa
> «ya no hace falta» de «lo estamos quitando a ciegas».
>
> Si la Puerta 3 no se alcanza, **no se pasa a la Fase 4** y hay que corregir el
> prompt y la selección determinista hasta alcanzarla. Apagar el sobre en
> producción sin superar esa puerta convertiría un 20 % de turnos rescatados en
> un 20 % de turnos fallidos — la misma trampa que I-1 prohíbe, por otra puerta.

### Triaje de los 37, decidido

| Grupo | n | Qué hacer |
|---|---|---|
| `test_structured_send_chat_message.py` | 32 | **Retirar con el sobre**, en el mismo commit que lo elimine. Prueban claims, `fact_ids`, tipos de claim y transiciones: artefactos que dejan de existir |
| Valor por defecto de `CHAT_STRUCTURED_OUTPUT_ENABLED` | 2 | **Actualizar** cuando el defecto pase a `False` |
| `turn_guard` · último recurso | 3 | **Conservar hasta la Fase 4** y retirarlos allí, dejando registrado que cubrían 9/45 turnos. I-9: nada se borra sin medir lo que se pierde — ya está medido |
