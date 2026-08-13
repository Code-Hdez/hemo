# 05 — Forense de generación, validación y reparación

## Amplificación de llamadas

133 llamadas al modelo para 70 preguntas = **1,9 por pregunta**.

| Llamadas | Turnos | Categoría |
|---:|---:|---|
| 1 | 36 | sólo generación primaria |
| 2 | 8 | primaria + reparación |
| 3 | 23 | primaria + reparación + último recurso |
| 4 | 3 | además, un intento extra |

Veredictos de las 133 validaciones: **53 válidas, 57 inválidas, 23 reparables**
→ **60 % de lo generado se descarta**.

## Tokens desperdiciados

| Concepto | Valor |
|---|---:|
| Tokens generados (suma de `eval_count`) | ~49.900 |
| Turnos que no entregaron nada | 17 |
| GPU consumida por esos 17 turnos | **1.875 s (38,1 % del total)** |
| Media desperdiciada por `generation_repair_failed` | **110,3 s** |
| Cómputo en reparaciones | 2.046 s (**41,6 %**) |

## Por qué la corrección importa: el fallo es SEMÁNTICO, no de forma

`openai_compatible_client.py:751` envía `payload["format"] = request.response_schema`
con `GeneratedResponseEnvelope.model_json_schema()`. **La gramática ya garantiza
la forma del sobre.**

Por tanto `policy_rule_id_missing` y `PLT:value,PLT:unit` no significan «el JSON
está roto». Significan: **el sobre es válido, pero sus campos no referencian los
identificadores correctos**. Una gramática no puede arreglarlo, porque no sabe
qué `policy_rule_id` existe ni qué analito pedía la pregunta.

## Taxonomía de rechazos (133)

| Categoría | n | Detalle dominante |
|---|---:|---|
| **FORMAT/ID_REPAIR** | ~58 | `policy_rule_id_missing` (15), `patient_fact_ids_missing` (6) |
| **NUMERIC_REPAIR** | ~21 | `PLT:value,PLT:unit` (4), `WBC:value,WBC:unit`, `MCHC:flag` |
| **SAFETY_REPAIR** | **7** | `definitive_diagnosis` (2), `mandatory_diagnosis_boundary` (2), `indirect_treatment_recommendation` (2), `medical_refusal_contract` (1) |
| Otros | ~7 | `evidence_span_not_found`, `ambiguous_parameter_claim` |

**Sólo 7 de 133 (5,3 %) son barreras de seguridad clínica.**

## El salvage por claim: activo y aun así insuficiente

`_claim_rejection` (`send_chat_message.py:4634`) se invoca en la línea **4941**
dentro del bucle `kept` / `first_rejection`. El comentario del propio código
explica el límite:

> «si ninguno sobrevive, el primer rechazo se eleva exactamente como antes, de
> modo que la reparación y el último recurso ven la misma razón de siempre»

En `SEL-08`, `materialized_fact_count = 1`: hay **un solo claim relevante**, y es
el que falla. No queda nada que salvar. **El salvage protege contra «cuatro
frases mueren por la quinta», no contra «la única frase falla».**

## Máquina de estados de `generation_repair_failed`

```
generación #1  →  válida?  no → repairable
      ↓ regeneration(reason)
generación #2  (perfil *_structured_repair, temp 0.3→0.1, num_predict 1280→1024)
      ↓ MISMO fallo en 9 de 9 casos medidos
generación #3  (último recurso: prompt recortado 3.871→1.374 tok)
      ↓ falla con OTRO error: policy_rule_id_missing (5 de 9)
terminal_error: generation_repair_failed, response = null
```

**¿Por qué la reparación repite el mismo error?** La evidencia disponible dice
que no es azar: baja la temperatura a 0,1 y falla igual 9 de 9 veces, siempre en
el mismo campo. La explicación compatible con los datos es que **el contrato pide
algo que el modelo no produce de forma fiable**, y que el prompt de reparación no
se lo comunica de manera que lo corrija. **Confirmarlo exige ver los dos prompts
y las dos salidas: E-1.**
