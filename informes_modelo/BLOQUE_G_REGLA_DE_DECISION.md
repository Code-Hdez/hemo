# Bloque G — regla de decisión, escrita antes de medir

**Fecha:** 2026-08-15 · **Pre-registro que la gobierna:** `PUERTAS_v3_PREREGISTRO.md` (SHA-256 en su `.sha256`)
**Árbol de partida:** `4cca5683` · **Estado de las VMs:** las tres `TERMINATED`, verificado.

> Se escribe **antes** de tocar una línea de la capa de datos y **antes** de
> encender ninguna máquina, para que ningún resultado se pueda interpretar a
> conveniencia después. El GOAL I-7 lo exige y esta sesión no lo va a estrenar.

Toda cifra va marcada `[MEDIDO]`, `[DERIVADO]` o `[INFERIDO]`.

---

## 0. La resta, primero, porque condiciona todo lo demás

`[MEDIDO]` Punto de partida (`campana_r_2026-08-14`, n = 225):

```
tasa de fallo de contrato        48/225  = 21,33 %
tasa que exige la Puerta C v3    13/400  =  3,25 %
REDUCCIÓN NECESARIA                        84,8 %
```

`[MEDIDO]` Reparto por frente, que la campaña muestra **perfectamente segregado
por ámbito**:

| Clase | n | tasa | Frente | Ámbito |
|---|--:|--:|---|---|
| `ambiguous_parameter_claim` | 14 | 6,22 % | **G** datos | paciente |
| `indirect_treatment_recommendation` | 12 | 5,33 % | **I** actos de habla | `general` |
| `unsupported_status_claim` | 7 | 3,11 % | **G** datos | paciente |
| `missing_evidence_attribution` | 6 | 2,67 % | **G** datos | `general` |
| `unsupported_numeric_claim` | 6 | 2,67 % | **G** datos | paciente |
| `definitive_diagnosis` | 3 | 1,33 % | **I** actos de habla | `general` |
| **frente G** | **33** | **14,67 %** | | |
| **frente I** | **15** | **6,67 %** | | |

`[DERIVADO]` **La resta, sin adornos:**

| | tasa que queda | veredicto |
|---|--:|---|
| eliminar **todo** el frente G | 6,67 % | **NO PASA** |
| eliminar **todo** el frente I | 14,67 % | **NO PASA** |
| eliminar los dos al 100 % | 0,00 % | PASA |

`[DERIVADO]` Y con eficacia parcial, que es lo realista:

| eficacia de G | eficacia de I | tasa final | veredicto |
|--:|--:|--:|---|
| 80 % | 80 % | 4,27 % | **NO PASA** |
| 80 % | 90 % | 3,60 % | **NO PASA** |
| 80 % | 100 % | 2,93 % | PASA |
| **90 %** | **80 %** | **2,80 %** | **PASA** |
| 90 % | 90 % | 2,13 % | PASA |

> **Esto es lo que hay que tener delante todo el rato.** No basta con que G
> funcione. No basta con que I funcione. **Hacen falta los dos, y con eficacia
> alta: el par (80 %, 80 %) no llega.** El umbral práctico está en torno a
> (90 %, 80 %).
>
> Se declara ahora para que, si la campaña sale en el 4-6 % de fallo, nadie lo
> lea como un fracaso del plan: sería una mejora de 15 puntos que **aun así** no
> pasa la puerta. Las dos cosas son ciertas a la vez y las dos se publicarán.

---

## 1. G.1 · El porcentaje deja de ser un hecho citable

### La hipótesis, estrecha y falsable

> **El servidor le está dando al modelo una contradicción y luego lo castiga por
> no resolverla.** Si el porcentaje del diferencial deja de estar entre los
> hechos autorizados, la clase `ambiguous_parameter_claim` **no puede
> dispararse**, y parte de `unsupported_status_claim` desaparece con ella.

`[MEDIDO]` No es una intuición sobre el modelo: es el mecanismo del validador,
leído en `output_claim_validator.py`:

```python
percent_fact = index.latest(percent or "")
if absolute_fact is None or percent_fact is None:
    continue                       # ← sin porcentaje autorizado, la clase no existe
if absolute_fact.status == percent_fact.status:
    continue                       # ← sin contradicción, tampoco
```

**El validador no se toca.** La comprobación sigue exactamente igual; lo que
cambia es que deja de haber un par contradictorio sobre el que disparar. Esto es
literalmente el patrón que arXiv:2606.01435 midió en **+10,8 pp**: resolver el
conflicto con código determinista **fuera** del modelo, en vez de con una regla
en el prompt.

### Respaldo clínico

Cornell — *eClinPath*, [WBC counts](https://eclinpath.com/hematology/tests/wbc-count/),
verificado en la fuente el 15-ago-2026:

> «A differential count should never be interpreted in percentages but should
> always be interpreted with respect to the total WBC count.»

**Requisito bloqueante:** la firma del veterinario sobre
`FIRMA_VETERINARIA_G1.md`. **Sin ella no se implementa**, aunque la aritmética
salga bien.

### Qué se implementa

1. Los códigos `*_PCT` salen del **índice de hechos autorizados** y del bloque
   `case_facts_json` del prompt. Salen de los dos: dejarlos en el índice y
   quitarlos del prompt no elimina la clase, porque el validador mira el índice.
2. Si la pregunta pide explícitamente el porcentaje, **el servidor construye la
   afirmación completa** —porcentaje, absoluto y recuento total en una sola
   frase— y la inyecta como hecho autorizado único.
3. El porcentaje **sigue** en la ficha del hemograma y en la interfaz. El cambio
   afecta solo a lo que el chat puede afirmar por su cuenta.

### La regla, decidida antes de ver el resultado

| Resultado | Decisión |
|---|---|
| `ambiguous_parameter_claim` cae a **≤ la mitad** (≤ 3,11 % de la tasa) **y** el total de fallos de contrato baja | **Se conserva** |
| Cae, pero **`unsupported_status_claim` sube** de forma que el total no mejora | **Se revierte.** Cambiar un rechazo por otro no es una mejora, y es la trampa concreta de este cambio: sin el porcentaje, un «los neutrófilos están altos» genérico deja de ser ambiguo y pasa a ser un estado no respaldado |
| **No cae** | **Se revierte.** Sería el quinto intento sobre el mismo objetivo y I-7 obliga a cambiar de hipótesis |
| Cae `ambiguous` **y** sube el número de turnos donde el selector deja fuera un parámetro que la pregunta pedía | **Se revierte**, y se mide cuánto |

**n de la medición:** el plan v3 completo, **400 turnos**. `[DERIVADO]` Con una
sola corrida de 45 no se distingue 14 de 3: los intervalos de Wilson se solapan
por completo, y esta campaña ya demostró que 4→3 en una corrida no significa
nada.

---

## 2. G.2 · Un hecho, una vez, un lugar

### La hipótesis

> El modelo cita cifras que no están autorizadas y omite la atribución de fuentes
> porque el contexto le llega **duplicado, redundante y sin estado calculado**.
> Si cada parámetro aparece exactamente una vez, con una sola representación
> numérica y un estado ya decidido por el servidor, `unsupported_numeric_claim` y
> `missing_evidence_attribution` pierden su causa.

*Ataca:* `unsupported_numeric_claim` (6, ámbitos con paciente) y
`missing_evidence_attribution` (6, `general`).

### Qué se implementa

1. **Deduplicar:** cada parámetro, una vez, con **una** representación numérica y
   **un** estado calculado por el servidor.
2. **Acotar por dominio:** solo los parámetros pertinentes a la pregunta del
   turno. Nada de «por si acaso». *Context Rot* (Chroma, 18 modelos) midió que
   **un solo distractor** ya degrada; *When More Documents Hurt RAG*
   (arXiv:2606.11350) midió una caída de 75 % a menos del 40 % por dilución.
3. **Fallback explícito:** si el selector no encuentra el parámetro, **lo dice el
   servidor**, no el modelo.

### La regla

| Resultado | Decisión |
|---|---|
| `unsupported_numeric_claim` **y** `missing_evidence_attribution` caen juntas, y el total baja | **Se conserva** |
| Cae una y sube la otra, o sube cualquier otra clase sin que el total mejore | **Se revierte** |
| Ninguna cae | **Se revierte** |
| El selector deja fuera un parámetro que la pregunta pedía en **> 2 % de los turnos** | **Se revierte**, aunque las clases hayan caído: sería comprar validez a cambio de no responder |

`[DERIVADO]` **El riesgo declarado de G.2 es el opuesto al de G.1.** G.1 quita un
dato que sobra; G.2 puede quitar uno que hacía falta. Por eso su regla incluye una
métrica que hoy **no existe** y hay que instrumentar antes de medir: *cuántas
veces el selector deja fuera un parámetro que la pregunta nombraba*.

---

## 3. G.3 · Reordenar la plantilla — condicionado, y detrás

**No se toca hasta que F.2b dé su veredicto.** Y aunque lo dé a favor, va
**detrás** de G.1, G.2 e I, por una razón medida:

`[MEDIDO]` La reutilización multi-turno es del 10,6 % y la Puerta C está en
21,33 % de fallo. `[DERIVADO]` Arreglar la caché mejora la **latencia** y no mueve
**ni un caso** de validez. G.3 es optimización; el bloqueo es la validez.

Si F.2b dice que la ventana deslizante de `_select_history` es la culpable, el
arreglo se implementa con su propia regla de decisión y su propia puerta —de
latencia, no de validez—.

---

## 4. Lo que NO se hace en este bloque

- **Ni una línea de prompt.** Cuatro intentos, cuatro revertidos, y `SEL-01`
  falla 5/5 con la instrucción activa.
- **Ni un ejemplo few-shot negativo.** *Over-prompting* (arXiv:2509.13196) mide
  degradación pasado el óptimo, peor cuanto más pequeño el modelo.
- **Ni un umbral del validador.** Es LA señal de desvío declarada.
- **Ni un reintento**, de contenido o de transporte.
- **Ni un segundo LLM.**
- **Ningún turno se descuenta del denominador.**

---

## 5. Lo que se publica pase lo que pase

Los cuatro denominadores con Wilson · el CONSORT con la causa de cada baja · las
nueve semillas · el histograma `pass^9` por pregunta · el recuento por clase · los
tres cruces (clase × desenlace, clase × ámbito, clase × posición) · `pass^6` por
consulta, i.i.d. **y** empírico · y la verificación job a job del despliegue más
el SHA leído **en la VM**.

Y si el resultado es una mejora que **no** pasa la puerta, se dice exactamente
así: cuánto mejoró, y por qué eso no basta.
