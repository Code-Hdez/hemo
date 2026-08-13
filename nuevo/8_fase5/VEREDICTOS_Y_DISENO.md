# Fase 5 — Veredictos y diseño de mitigación

## VERIFICACIÓN 1 · CATALOGO_POLICY_RULE_IDS_ELIMINADO = **SI**

`send_chat_message.py:4283` `_last_resort_candidate()`. El docstring lo declara:

> *"Generated with **no authorized facts, no retrieved sources and no policy
> rules in scope**. That is the safety argument and it is structural…"*

```python
last_resort_policy = replace(policy,
    route=ResponseRoute.CONVERSATIONAL,
    rule_id=LAST_RESORT_RULE_ID,
    use_rag=False,
    use_clinical_context=False,          # elimina el bundle clínico
    include_sources=False,
    generation_instruction=("… Cierra sugiriendo que lo revise el veterinario. …"))
last_resort_plan = self._build_response_plan(..., facts=[])   # hechos vacíos
```

### El mecanismo es una CONTRADICCIÓN, no una omisión

Es más grave que la hipótesis original. Los tres eslabones:

1. El último recurso **retira** las reglas de política del alcance.
2. Su plan **sigue permitiendo** `SAFETY_GUIDANCE` y `URGENT_REFERRAL`.
   Evidencia en telemetría: el plan mínimo observado 15 veces es exactamente
   `['CONVERSATIONAL','LIMITATION','SAFETY_GUIDANCE','URGENT_REFERRAL']`.
3. Su instrucción **ordena** *"Cierra sugiriendo que lo revise el veterinario"*
   — que es literalmente un claim `SAFETY_GUIDANCE`.
4. `structured_response.py:137-141` lo rechaza:
   ```python
   if self.claim_type in {ClaimType.SAFETY_GUIDANCE, ClaimType.URGENT_REFERRAL} \
      and not self.policy_rule_ids:
       raise ValueError("safety guidance requires a policy_rule_id")
   ```

**El último recurso ordena al modelo emitir el claim que exige un identificador
que él mismo acaba de retirar.** El modelo no puede cumplir. Es un fallo
iatrogénico y determinista por construcción.

### Evidencia cuantitativa (recalculada de forma independiente)

```
policy_rule_id_missing según tamaño del prompt de esa llamada
  COMPLETO (>=2.000 tok)   2/67 =  3,0 %
  TRUNCADO (<2.000 tok)   13/30 = 43,3 %
  chi2 = 25,8   odds ratio = 24,9x
23 de las 30 llamadas truncadas son la llamada #3 (último recurso)
13 de los 17 fallos terminales (76 %) mueren con policy_rule_id_missing
```

Estado: **CONFIRMADO** — por código y por datos.

---

## VERIFICACIÓN 2 · SAFETY_BLOCK_USADO = **SI**  ← corrige la propuesta M-3

Los 7 booleanos **no son inertes**. Alimentan una rama de rechazo en
`send_chat_message.py:4966-4977`:

```python
if any((safety.contains_diagnosis_confirmation,
        safety.contains_medication_recommendation,
        safety.contains_dose, safety.contains_frequency,
        safety.contains_treatment_duration,
        safety.contains_personalized_treatment)):
    raise StructuredResponseError("structured_safety_flags_invalid")
```
y `requires_urgent_referral` se consulta en la línea 4977.

**M-3 (eliminar el bloque `safety`) queda DESCARTADA tal como está propuesta.**
Es una puerta de seguridad real, no telemetría. Si se quisiera recuperar esos
6,5 s habría que sustituir la autodeclaración por una comprobación determinista
sobre el texto — rediseño, no supresión.

---

## VERIFICACIÓN 3 · Arnés real — **NO COMPLETADA**

No se reconstruyó el prompt completo de 3.700-4.000 tokens ni se importó el
validador real. **Las tres cifras clínicas siguen sin existir.**

Lo único disponible sigue siendo la cota inferior del arnés de juguete de Fase 4:
con el hecho delante y citando su `fact_id`, el modelo **omite la cifra 4 de
cada 10 veces**. Es la tarea más fácil posible.

---

## DISEÑO DE MITIGACIÓN

### M-1 · No retirar el catálogo de políticas en el último recurso · **P0**

- **Fichero/línea:** `send_chat_message.py:4317-4340`, `_last_resort_candidate()`
- **Diff conceptual:** dos opciones, ninguna relaja una validación:
  - (a) conservar el catálogo de `policy_rule_ids` autorizados aunque se retiren
    hechos y fuentes — coherente con el argumento de seguridad del docstring,
    que habla de *hechos medidos*, no de reglas de política;
  - (b) restringir `allowed_claim_types` del plan de último recurso a
    `['CONVERSATIONAL','LIMITATION']`, eliminando `SAFETY_GUIDANCE`/
    `URGENT_REFERRAL`, y expresar la derivación al veterinario como
    `CONVERSATIONAL`.
- **Riesgo clínico:** (a) ninguno, añade contexto. (b) requiere comprobar que la
  derivación obligatoria sigue emitiéndose.
- **Criterio de éxito:** `policy_rule_id_missing` en llamadas de último recurso
  baja de 43,3 % a <10 %; los fallos terminales bajan de 17 a ≤6.
- **Ataca:** 13 de 17 fallos terminales.

### M-2 · Rellenar `policy_rule_ids` cuando el conjunto autorizado tenga 1 elemento · **P1**

- **Fichero:** `structured_response.py:671, 732-737` — el backend ya conoce
  `allowed_policy_rule_ids` porque los inyecta en el esquema.
- **Salvaguarda obligatoria:** sólo con cardinalidad exactamente 1. Con ≥2 la
  elección es semántica y debe seguir haciéndola el modelo.
- **Riesgo clínico:** bajo con esa salvaguarda. **Ataca:** 15 de 80 rechazos.

### M-3 · Eliminar el bloque `safety` · **DESCARTADA** (ver verificación 2)

### M-4 · Acortar identificadores de claim · **P3**
~5 tokens por claim. Riesgo nulo. Ganancia marginal.

### M-5 · Presupuesto de tokens por perfil · **P1**
`HIS-02` y `HIS-F08` agotaron `num_predict=1280`, tardaron 95,6 s y 96,2 s y
produjeron `structured_json_invalid` con `finish_reason=length`. **Con gramática
activa, agotar el presupuesto garantiza JSON inválido.** 192 s de GPU para nada.
Elimina un fallo determinista.

### NO PROPUESTAS, y por qué
Relajar `missing_required_clinical_facts` (el modelo omite la cifra 4/10 veces:
el validador protege) · más prefix caching (techo 8,7 %) · Flash Attention (ya
activo) · vLLM (beneficio de concurrencia; aquí `-np 1` y cola 0 ms) · MTP
(35-55 % de aceptación en híbridos SWA) · modelo de 9B (revalidación clínica).

---

## LEDGER DE CORRECCIONES

| Afirmación | Corrección |
|---|---|
| «El último recurso recorta el contexto» (Fase 2-3) | **Ampliada**: no sólo recorta — ordena un claim que exige lo que retira |
| «M-3: quitar el bloque safety» (`Diagnóstico_definitivo.md`) | **DESCARTADA**: alimenta una rama de rechazo real |
| «Token tax 457 tok / 3,46 chars-token» (Fase 4) | **Aceptada la crítica**: calibración sesgada (25 de 97, sólo rechazadas) |
| «Las tres cifras clínicas» (Fase 4) | **Siguen sin existir**. El arnés de Fase 4 midió otra tarea |
