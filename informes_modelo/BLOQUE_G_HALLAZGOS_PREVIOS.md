# Bloque G — lo que la lectura del código cambia del plan, antes de tocarlo

**Fecha:** 2026-08-15 · **Árbol:** `4cca5683` · **GPU usada: cero**
**Estado de las VMs:** las tres `TERMINATED`, verificado.

> Se escribe después de sellar `BLOQUE_G_REGLA_DE_DECISION.md` y **antes** de
> implementar nada, porque leer el código cambió dos de las tres piezas del
> bloque. Media jornada de trabajo que no hay que hacer.

Toda cifra va marcada `[MEDIDO]`, `[DERIVADO]` o `[INFERIDO]`.

---

## 1. G.2 «deduplicar» ya está hecho — el plan lo daba por pendiente

El prompt maestro §G.2 pide: *«cada parámetro aparece **exactamente una vez** en
el contexto, con **una sola** representación numérica y **un estado ya calculado
por el servidor**»*.

`[MEDIDO]` Las tres cosas ya están implementadas en
`clinical_facts.py::enrich_case_facts`:

```python
study_facts = facts_by_study.setdefault(lab_fact.analysis_id, {})
if lab_fact.code in study_facts:
    raise ValueError("clinical_facts_duplicate_analysis_parameter")   # ← una vez, y explota si no
study_facts[lab_fact.code] = lab_fact
...
copy["derived_status"] = lab_fact.status                              # ← estado del servidor
```

- **Una vez por estudio:** no es una convención, es una excepción. Duplicar un
  parámetro dentro del mismo estudio **aborta el turno**.
- **Estado calculado por el servidor:** `derived_status` viaja con cada hecho.
- **Acotado por dominio:** `[MEDIDO]` el selector determinista ya reduce a 1-4
  hechos por turno (`n_case_facts`: `0 1 1 4 1 1 1 1 4 1 1 4 4 4 4`), no manda
  el hemograma entero «por si acaso».

`[DERIVADO]` **Lo único que sobrevive de G.2 es el *fallback* explícito**, y ni
siquiera está claro que falte. Un parámetro **sí** aparece más de una vez cuando
hay varios estudios —es longitudinal y es deliberado— y el absoluto y el
porcentaje son códigos distintos, que es el objetivo de **G.1**, no de G.2.

> **Consecuencia:** G.2 se reduce a instrumentar la métrica de su propia regla de
> decisión —cuántas veces el selector deja fuera un parámetro que la pregunta
> nombraba— y a comprobar si ese número es distinto de cero. Si es cero, G.2 no
> tiene trabajo que hacer y sus 12 fallos hay que atribuirlos a otra causa.

---

## 2. `missing_evidence_attribution`: la causa NO se puede determinar hoy

### 2.1 Un defecto de método propio, cazado antes de publicarlo

`[MEDIDO]` Primera lectura de los datos, y parecía concluyente:

| `n_fuentes` | turnos de `general` | `missing_evidence` | tasa |
|---|--:|--:|--:|
| 0 | 25 | 5 | **20,0 %** |
| 1 | 26 | 1 | 3,8 % |
| 2 | 24 | 0 | 0,0 % |

La lectura tentadora: *«se le exige al modelo que cite evidencia que el servidor
no recuperó»*. Encajaba con el principio del plan entero y era una causa
determinista y barata de arreglar.

**Es falsa, y la trampa está en qué mide el campo.** El arnés graba

```python
"n_fuentes": len(cuerpo.get("sources") or [])
```

es decir, las fuentes **de la respuesta publicada**. Y el backend, en
`_attributed_sources`, devuelve lista vacía **justo cuando la atribución falla**:

```python
if not include_sources or not used_source_ids:
    return []
```

`[MEDIDO]` Desglosando por si hubo cuerpo publicado, la correlación se evapora:

| | n | `n_fuentes` observado |
|---|--:|---|
| turnos TERMINALES de `general` | 8 | **todos 0** — no hay cuerpo, el campo no puede ser otra cosa |
| turnos con respuesta publicada | 67 | 0→17 · 1→26 · 2→24 |

Y entre los que **sí** tienen cuerpo:

| `n_fuentes` | n | `missing_evidence` |
|---|--:|--:|
| 0 | 17 | **0** |
| 1 | 26 | 1 |
| 2 | 24 | 0 |

> **Cero de 17.** La relación era un artefacto: el `0` es **consecuencia** del
> fallo, no su causa, y los turnos terminales lo tienen a cero por construcción.
>
> Es exactamente la trampa que este proyecto ya tiene documentada —clasificar por
> un campo que se rellena *después* del hecho que se quiere explicar—, y estuvo a
> punto de producir un arreglo para un problema inexistente. Se cazó preguntando
> **qué mide el campo** antes de creerse la tabla.

### 2.2 Lo que el código sí dice

`[MEDIDO]` `_missing_evidence_attribution` **no puede** dispararse sin fuentes:

```python
if not (policy.include_sources and sources and not used_source_ids):
    return False
```

Y hay un guardián en `prompt_builder.py` que apaga `include_sources` cuando el
presupuesto ha eliminado las filas de fuente:

```python
if policy.get("include_sources") and not source_rows:
    policy["include_sources"] = False
```

`[DERIVADO]` Luego en los 6 casos **la recuperación sí devolvió chunks**. La
recuperación automática de la atribución no actuó, y sus guardas dicen por qué
puede no actuar:

```python
if (used_source_ids or declared_source_ids or evidence_marker_found
        or not policy.use_rag or not policy.include_sources
        or policy.use_clinical_context or not sources):
    return used_source_ids
```

En `general`, `use_clinical_context` es falso y `sources` no está vacío. `[INFERIDO]`
Quedan `declared_source_ids` y `evidence_marker_found`: **el modelo escribió un
marcador vacío o inválido**, y el código lo respeta a propósito — *«an explicit
empty or invalid declaration from the model is still never overridden»*.

**Es una hipótesis, no un hecho**, y no se puede confirmar con lo que hay.

### 2.3 El hueco de instrumentación, que es lo accionable

`[MEDIDO]` Ni `evidence_marker_found` ni `declared_source_ids` viajan a ningún
sitio observable: no están en el `route_trace`, no están en el sobre de error y
no están en el `.jsonl`. Sin ellos **no se puede separar**:

- «el modelo se olvidó de poner el marcador» — recuperable por el servidor, y
- «el modelo declaró un marcador inválido» — respetar eso es una decisión
  deliberada.

Son dos causas distintas con dos arreglos distintos, y hoy se cuentan juntas.

> **Propuesta, mismo patrón que ya funcionó una vez.** El commit `855566ff`
> —hacer visible el motivo del error terminal— es lo que convirtió «7 rechazos
> ciegos» en una taxonomía. Aquí toca lo mismo, y es igual de barato: exponer
> `evidence_marker_found` y el recuento de `declared_source_ids` en el
> `route_trace`. **No cambia el comportamiento**, y por
> `COMPARABILIDAD_COMMITS.md` §1 la instrumentación no rompe la comparabilidad
> entre corridas.

---

## 3. G.1 sigue en pie, y es el único de los tres que no cambia

`[MEDIDO]` El mecanismo está en `output_claim_validator.py` y es exactamente el
que la regla de decisión describe: la clase exige **los dos** hechos autorizados
con **estados distintos**. Sin el porcentaje en el índice, no puede dispararse.
Sin tocar el validador.

**Sigue bloqueado por la firma veterinaria** (`FIRMA_VETERINARIA_G1.md`).

---

## 4. Lo que esto cambia del reparto de trabajo

| Pieza | Estado antes de leer | Estado real |
|---|---|---|
| G.1 · el porcentaje deja de ser citable | por implementar | **por implementar**, bloqueado por la firma |
| G.2 · deduplicar | por implementar | **ya hecho** — y con excepción, no con convención |
| G.2 · estado calculado por el servidor | por implementar | **ya hecho** (`derived_status`) |
| G.2 · acotar por dominio | por implementar | **ya hecho** (1-4 hechos por turno, medido) |
| G.2 · *fallback* explícito | por implementar | **por medir primero**: puede no haber caso |
| `missing_evidence_attribution` (6) | atribuido a G.2 | **causa desconocida**; hace falta instrumentar antes |

---

## 5. La cadena completa, y el bloque que compra el margen

`[DERIVADO]` Asignando cada clase al bloque que la ataca —`unsupported_numeric_claim`
**sí** la tiene asignada: es el objetivo «por construcción» del Bloque H—:

| Clase | n | Bloque |
|---|--:|---|
| `ambiguous_parameter_claim` | 14 | **G.1** |
| `indirect_treatment_recommendation` | 12 | **I** |
| `unsupported_status_claim` | 7 | **G.1 + H** |
| `missing_evidence_attribution` | 6 | **SIN ASIGNAR** |
| `unsupported_numeric_claim` | 6 | **H** (por construcción) |
| `definitive_diagnosis` | 3 | **I** |

`[DERIVADO]` Con `missing_evidence_attribution` **sin atacar**, y todo lo demás
al 100 %, queda `6/225 = 2,67 %` frente al 3,25 % de la puerta: **pasa por
0,58 puntos**. Un margen de nada. Y la sensibilidad es brutal:

| G.1 | H | I | tasa final | veredicto |
|--:|--:|--:|--:|---|
| 100 % | 100 % | 100 % | 2,67 % | **PASA** (margen +0,58) |
| **95 %** | **95 %** | **95 %** | **3,60 %** | **NO PASA** |
| 90 % | 90 % | 90 % | 4,53 % | NO PASA |
| 80 % | 80 % | 80 % | 6,40 % | NO PASA |

`[DERIVADO]` Y si **además** se resuelve `missing_evidence_attribution`:

| eficacia en TODO | tasa final | veredicto |
|--:|--:|---|
| 90 % | 2,13 % | **PASA** |
| **85 %** | **3,20 %** | **PASA** |
| 80 % | 4,27 % | NO PASA |

> **Esa clase de 6 casos es la que compra el margen del plan entero.** Sin ella,
> los tres bloques tienen que salir perfectos y basta un 95 % para suspender.
> Con ella, el plan tolera un 85 % en todo.
>
> `[DERIVADO]` Deja de ser una clase menor y pasa a ser **la de mayor
> apalancamiento por caso**: 6 fallos que convierten «todo tiene que ser
> perfecto» en «basta con el 85 %». Y su causa hoy **no se puede diagnosticar**
> por el hueco de instrumentación de §2.3.
>
> **Prioridad que esto impone:** instrumentar `evidence_marker_found` y
> `declared_source_ids` es ahora el trabajo sin GPU de mayor valor que queda.

## Hipótesis vivas

1. **Qué causa los 6 `missing_evidence_attribution`.** Marcador olvidado o
   marcador inválido. Se separa con la instrumentación de §2.3.
2. **Qué causa los 6 `unsupported_numeric_claim`.** El desglose por parámetro ya
   los nombra (`hct`, `neu_pct`, `plt`, `wbc`), pero no está caracterizado si la
   cifra es inventada o simplemente no autorizada.
3. **Si el *fallback* del selector tiene algún caso real.** Métrica pendiente.
