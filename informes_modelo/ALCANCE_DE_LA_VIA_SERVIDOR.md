# Alcance de «que escriba el servidor» — qué llega y qué no, medido antes de implementar

**Fecha:** 2026-08-15 · **Herramienta:** `validacion_llm/scripts/alcance_via_servidor.py`
**Datos:** campaña v3, 405 turnos, **356 publicados**, 3650 oraciones · **GPU: cero**
**Validador:** `I-2`, **no se ha tocado** — se ejecuta, no se modifica

> GOAL, `I-3`: *«Las cifras, los estados y el nombre desambiguado del parámetro los
> pone el servidor; la prosa libre no lleva cifras ni afirmaciones de estado.»*
> Antes de escribir una línea de gramática, cuánto texto es eso y si los fallos
> caen ahí.

---

## 1. El reparto del texto publicado `[MEDIDO]`

Cada oración se clasifica ejecutando **el predicado de producción**
(`OutputClaimValidator._status_claims`), no una reimplementación:

| población | oraciones | % oraciones | % del texto |
|---|--:|--:|--:|
| **servidor** — lleva cifra del paciente o afirmación de estado | 1034 | 28,3 % | **25,3 %** |
| **prosa** — ni cifras ni estados | 2616 | 71,7 % | 74,7 % |

| ámbito | oraciones que escribiría el servidor |
|---|--:|
| `general` | 20,5 % |
| `hemogram_history` | 29,7 % |
| `selected_hemogram` | **34,7 %** |

> **El servidor escribiría el 25,3 % del texto.** El GOAL marca el 60 % como
> señal de «esto va a sonar a formulario»; estamos a menos de la mitad. `[DERIVADO]`
> Es una buena noticia para la naturalidad, y aun así va a la revisión ciega de
> M.7: que el volumen sea bajo no prueba que el resultado se lea bien.

---

## 2. La pregunta regalada — y no hay regalo `[MEDIDO]`

El GOAL sugería comprobar si prohibir afirmaciones de estado en la prosa se
llevaría también `definitive_diagnosis`, y avisaba de **no asumirlo**. Ejecutando
los dos predicados sobre frases diagnósticas:

```
dd=sí  estado=no  → prosa     Tu perro tiene anemia.
dd=sí  estado=no  → prosa     Kira tiene anemia.
dd=sí  estado=no  → prosa     Esto confirma una infeccion.
dd=sí  estado=no  → prosa     Se descarta la enfermedad.
```

**0 de 5 caen en la población `servidor`.** `_status_claims` busca `alto`/`bajo`/
`normal`; *«tiene anemia»* nombra una enfermedad, no un estado de parámetro. La
regla de cifras-y-estados **no toca `definitive_diagnosis`**.

---

## 3. Pero hay otra puerta, y el Anexo A ya la autorizaba `[MEDIDO]`

El Anexo A §5 dice: *«el servidor pasa su propio borrador por los predicados
existentes antes de ensamblar»*. Eso **no es tocar el validador** (`I-2`): es
aplicarlo, sin cambiarlo, a texto que todavía no se ha publicado.

La pregunta es qué se lleva por delante. Sobre los 356 textos publicados:

| predicado | oraciones que quitaría | turnos tocados | % del texto |
|---|--:|--:|--:|
| `definitive_diagnosis` | **0** | 0 | **0,00 %** |
| `dose_instruction` | 0 | 0 | 0,00 % |
| `indirect_treatment` | 4 | 3 | 0,22 % |

### 3.1 La asimetría, que es lo que decide si esto vale

- **`definitive_diagnosis` — sanear es un arreglo.** Cuesta **0,00 %** sobre texto
  seguro y el contenido que quitaría **no debería estar ahí**. `[DERIVADO]` Los 6
  fallos que el GOAL contaba como suelo irreducible **son alcanzables**.

- **`indirect_treatment` — sanear NO es un arreglo.** Quitaría 4 oraciones, un
  0,22 % del texto, pero esas oraciones **son la etiología clínicamente correcta
  que la pregunta pedía**. Cambiar un rechazo por una respuesta que ya no responde
  es exactamente lo que la regla de decisión prohíbe. **Eso lo decide la firma, no
  el servidor.**

`[MEDIDO]` Y la evidencia de que el problema no es de quién escribe: de las 4
coincidencias de `indirect_treatment` sobre texto publicado, **3 viven en prosa
libre y 1 en la población servidor**. Aunque el servidor escribiera la frase, el
validador la rechazaría igual — la regla es léxica y no mira quién la escribió.
Eso es lo que M.4 demuestra ejecutándolo.

---

## 4. La aritmética, corregida con lo medido

`[DERIVADO]` El GOAL parte de 63 atacables por el servidor y 9 de suelo. Con
`definitive_diagnosis` alcanzable por el saneado de prosa:

| | GOAL §0 | **medido aquí** |
|---|--:|--:|
| atacable por el servidor | 63 | **69** |
| detrás de la firma de I.2 | 24 | 24 |
| suelo irreducible | 9 | **3** |

```
solo servidor, al 100 %   →  27/400 = 6,75 %   NO PASA   (GOAL decía 8,25 %)
servidor + firma, 100 %   →   3/400 = 0,75 %   PASA      (GOAL decía 2,25 %)

removibles: 93 · hay que quitar 83 · EFICACIA MÍNIMA: 89,2 %   (GOAL decía 95,4 %)
```

> **El margen mejora de 4,6 a 10,8 puntos porcentuales.** Sigue siendo estrecho, y
> sigue siendo cierto que **sin la firma no se pasa**: 6,75 % frente a 3,25 %.

**Tres condiciones que esta corrección lleva pegadas, y no son letra pequeña:**

1. `[DERIVADO]` Que quitar la oración diagnóstica deje una respuesta que **siga
   respondiendo**. Se mide como sobre-rechazo en M.5, no se supone.
2. `[MEDIDO]` El coste sobre texto seguro es **0,00 %**, así que no hay riesgo de
   mutilar respuestas que hoy están bien. Pero los 6 fallos ocurrieron en
   **borradores rechazados que no se persisten**, y ahí el coste **no es medible
   hasta la ventana 2**.
3. Los 6 están medidos como **verdaderos positivos**: el predicado exige que el
   verbo rija el nombre de la enfermedad, y seis redacciones educativas plausibles
   no lo disparan. Sanearlos **no relaja nada**.

---

## 5. Dónde vive cada clase, y qué significa para el plan

| clase | n | ¿la alcanza el servidor? |
|---|--:|---|
| `ambiguous_parameter_claim` | 31 | **Sí** — nace de nombrar la familia genérica con un estado. Es literalmente la población `servidor` |
| `unsupported_numeric_claim` | 14 | **Sí** — una cifra del paciente, por definición |
| `missing_evidence_attribution` | 11 | **Sí** — ya implementado (`§3.1`, rama sin desplegar) |
| `unsupported_status_claim` | 7 | **Sí** — afirmación de estado |
| `definitive_diagnosis` | 6 | **Sí, por el saneado de prosa** — §3.1 de este informe |
| `indirect_treatment_recommendation` | 24 | **No.** Mecánicamente se podría borrar, pero borra la etiología. Firma |
| `intent_mismatch_scope_boundary` | 2 | **No** — sin frente |
| `internal_material_exposed` | 1 | **No** — sin frente |

---

## 6. Lo que este informe NO demuestra

`[MEDIDO]` Todo lo anterior se calcula sobre **texto publicado**. Los 96 fallos
ocurrieron en borradores que **el backend no persiste** —diseño de privacidad
clínica, `LIMITACIONES.md` §2.1—, así que:

> **No se puede verificar directamente que los 96 fallos caigan en las oraciones
> que el servidor va a escribir.** Se infiere de la definición de cada clase
> —`ambiguous_parameter_claim` **es** una afirmación de estado sobre una familia
> genérica; `unsupported_numeric_claim` **es** una cifra— y esa inferencia es
> sólida, pero es inferencia.

`[DERIVADO]` **La comprobación real es la ventana 2.** Si tras M.2 y M.3 una clase
no cae como aquí se predice, lo que falló fue esta inferencia, y se dice así en vez
de buscarle otra explicación.
