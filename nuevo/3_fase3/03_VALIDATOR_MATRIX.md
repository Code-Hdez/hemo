# 03 — Matriz de validadores (con el schema real abierto)

## El hallazgo: SCHEMA_ACCEPTS → VALIDATOR_REJECTS

Se abrió `GeneratedResponseEnvelope.model_json_schema()` — el mismo objeto que
se envía a Ollama como `format`.

```
GeneratedResponseEnvelope.required = ['response_type','intent','claims','safety']
GeneratedClaim.required            = ['claim_id','text','claim_type']

fact_ids         : list = Field(default_factory=list)   <- NO required
source_ids       : list = Field(default_factory=list)   <- NO required
policy_rule_ids  : list = Field(default_factory=list)   <- NO required
evidence_spans   : list = Field(default_factory=list)   <- NO required
```

**La gramática permite explícitamente un claim con `policy_rule_ids: []`.** El
modelo produce JSON estructuralmente válido y conforme al schema. **Después**,
un validador de negocio lo rechaza.

Regla exacta, `structured_response.py:140`:

```python
} and not self.policy_rule_ids:
```
mapeada en la tabla de mensajes (`structured_response.py:640-652`):

| Mensaje de la regla | Código emitido |
|---|---|
| «safety guidance requires a policy_rule_id» | `policy_rule_id_missing` |
| «fact-based claims require at least one fact_id» | `patient_fact_ids_missing` |
| «documented general knowledge requires source_ids» | `documented_source_ids_missing` |
| «parametric knowledge claims cannot cite patient facts» | `parametric_fact_ids_forbidden` |

Y en `json_schema()` (`structured_response.py:671, 732-737`) el schema **sí**
restringe *qué* identificadores son válidos:
`constrain_identifier_array("policy_rule_ids", policy_rule_ids)` sobre
`allowed_policy_rule_ids`.

## Clasificación de cada fallo — demostrada, no supuesta

| Código | Tipo | Por qué |
|---|---|---|
| `policy_rule_id_missing` | **CONTRATO (mismatch schema/validador)** | El schema enumera los ids permitidos pero **no obliga a que el array tenga elementos**; la obligación es **condicional al `claim_type`**, y JSON Schema no la expresa. La gramática no puede impedirlo |
| `patient_fact_ids_missing` | **CONTRATO (mismo mecanismo)** | `fact_ids` tampoco es `required`; la regla lo exige sólo para claim types que citan hechos |
| `PLT:value` / `PLT:unit` | **GROUNDING/COBERTURA** | No es un campo del schema: es una comprobación de que los hechos materializados cubren el analito discutido (`missing_required_clinical_facts`) |
| `structured_schema_invalid` | **PARSER/SCHEMA** | Aquí sí es incumplimiento estructural del sobre |
| `definitive_diagnosis`, `mandatory_diagnosis_boundary`, `medical_refusal_contract` | **SAFETY** | Rechazo correcto (7 de 133) |

> **Respuesta a la pregunta crítica «¿el contrato pide algo que nunca se entregó
> al modelo?»**: **No exactamente.** El schema *sí* lleva los ids permitidos
> (están enumerados en `format`). El problema es el inverso: **el schema no
> obliga a usarlos**, y la obligación real vive en una regla posterior
> condicional al tipo de claim. El modelo cumple el contrato que se le impone
> por gramática y **falla el contrato que se le juzga después**.
> Estado: **CONFIRMADO por lectura del schema y de la regla.**

## Corrección a la Fase 2

La Fase 2 dijo: *«el fallo es semántico, no de forma»*. Con el schema abierto la
formulación correcta es más precisa: **es un fallo de contrato**, porque existe
una obligación de negocio que el artefacto que restringe la generación (el
schema) no expresa. La conclusión operativa **cambia**: sí hay margen en
constrained decoding —hacer `minItems: 1` condicional por `claim_type`— aunque
JSON Schema lo expresa con dificultad (`if/then` o `oneOf` por tipo).
