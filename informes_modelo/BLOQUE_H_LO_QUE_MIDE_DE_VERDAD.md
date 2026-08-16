# Bloque H — qué mide de verdad `unsupported_numeric_claim`, antes de implementar

**Fecha:** 2026-08-15 · **GPU: cero** · **VMs:** las tres `TERMINATED`, verificado
**Datos:** campaña v3, 405 turnos · **Validador:** `I-3`, **no se ha tocado nada**

> `BLOQUE_H_REGLA_DE_DECISION.md` §0 condiciona el bloque a dos cosas: que F.1
> diga que Ollama propaga `enum`, y **saber qué ataca**. La primera se cumplió
> (`PROPAGA`, 30/30). Este informe cierra la segunda — y lo que encontró obliga a
> revisar qué significaría la medición de H antes de gastarla.

---

## 1. Las dos condiciones selladas están cumplidas

| Condición | Estado |
|---|---|
| F.1 · ¿propaga Ollama `enum`? | `[MEDIDO]` **PROPAGA.** 30/30 dentro del enum, 0 vacías. Cota superior 95 % de violación: 9,50 % |
| Campaña v3 con el detalle terminal instrumentado | `[MEDIDO]` **hecha.** 400 turnos, 14 fallos de esta clase |

---

## 2. Lo primero que sale del dato: no es el hemograma seleccionado, es el historial

`[MEDIDO]` Los 14 fallos, por ámbito:

| ámbito | fallos |
|---|--:|
| `hemogram_history` | **13** |
| `selected_hemogram` | 1 |

Cuando la regla se selló, el reparto conocido era 5 de 6 con n = 225. Ahora es
**13 de 14 con n = 400**, y eso ya no es una tendencia: es dónde vive el problema.

`[MEDIDO]` Los cuatro terminales traen parámetro: `plt`, `rbc` (×2), `wbc`. Los
diez reparados no lo traen.

### 2.1 Y hay un gradiente monótono

`[MEDIDO]` Tasa de la clase dentro de `hemogram_history`, solo turnos publicados,
por tamaño del conjunto autorizado (`n_case_facts`):

| hechos autorizados | fallos / turnos | tasa |
|--:|---|--:|
| 1 | 0 / 18 | **0,0 %** |
| 2 | 2 / 35 | 5,7 % |
| 4 | 7 / 61 | **11,5 %** |

**Cuantos más valores autorizados hay, más falla.** Que es lo contrario de lo que
haría un modelo que inventa cifras por falta de datos.

---

## 3. Qué comprueba realmente el validador — ejecutado, no leído

La ruta numérica es
`_text_supports_claim(claim, case_fact_texts, strict_numbers=True)` en
`backend/app/modules/llm_chat/claim_validation.py`. `[MEDIDO]` Ejecutándola contra
dos hechos (`RBC 4.52` del 2026-01-10 y `WBC 15.20` del 2026-03-14):

| Afirmación | Veredicto |
|---|---|
| cifra correcta de su propio hecho | SOPORTADO |
| cifra **cruzada** entre los dos hechos | **SOPORTADO** |
| cifra **inventada** (`9.99`) | **SOPORTADO** |
| **delta derivado** (`subió 10.68`) | **RECHAZADO** |

### 3.1 Por qué pasa una cifra inventada — el mecanismo, medido

```
numeros que aporta el HECHO      : ['01', '10', '2026', '4', '52']
numeros de la frase INVENTADA    : ['01', '10', '2026', '9', '99']
interseccion                     : ['01', '10', '2026']   ← basta con que no este vacia
```

Dos cosas a la vez:

1. **El tokenizador parte `4.52` en `4` y `52`.** La comprobación no opera sobre
   la cifra, sino sobre fragmentos enteros.
2. **La fecha aporta números.** `2026`, `01` y `10` están en el hecho, así que
   cualquier frase que cite la fecha intersecta y **pasa el control sea cual sea
   el valor**.

`[MEDIDO]` La misma frase **sin la fecha** sí se rechaza:

```
RECHAZADO  El RBC fue de 9.99 millones por microlitro.
SOPORTADO  El RBC fue de 4.52 millones por microlitro.
```

### 3.2 Y una rama muerta

```python
if len(evidence_number_sets) > 1:
    evidence_number_sets.append(set().union(*evidence_number_sets))
...
evidence_numbers = evidence_number_sets[min(index, len(evidence_number_sets) - 1)]
```

`index` recorre `evidence_term_sets`, que tiene **N** entradas;
`evidence_number_sets` tiene **N+1** tras el `append`. `min(index, N)` con
`index ≤ N−1` da siempre `index`, así que **la unión se calcula y no se usa
nunca**. `[DERIVADO]` La intención aparente era un respaldo por conjunto completo;
está inerte. **No se toca** — `I-3` — pero queda anotado.

---

## 4. Lo que esto le hace al Bloque H

`[DERIVADO]` La clase **no significa «el modelo inventó un número»**. Significa
«la frase no compartía ningún fragmento numérico con el hecho que le dio el
solape de términos». En la práctica eso deja fuera casi todo salvo **las cifras
derivadas** —deltas, diferencias, medias— que son justo lo que una pregunta de
historial invita a escribir. El gradiente del §2.1 encaja: más hemogramas
autorizados, más ocasiones de restar dos y publicar el resultado.

**Y aquí está el problema con medir H:**

> Una gramática que restrinja los slots numéricos a literales autorizados hace
> que la cifra derivada sea **inescribible**. Es decir: `unsupported_numeric_claim`
> **caería a 0 por construcción**, no por haber reducido las cifras alucinadas.

La regla sellada dice «cae a 0 y el total baja → se conserva». `[DERIVADO]` Con lo
que ahora se sabe, **ese resultado llegaría casi garantizado y no probaría lo que
la regla creía que probaría**. Las dos cosas que de verdad preocupan —una cifra
inventada colada junto a una fecha, y una cifra correcta atribuida al parámetro
equivocado— **son invisibles para este validador**, así que H no puede
demostrarse contra ellas.

---

## 5. La consecuencia, dicha sin rodeos

**No se implementa H con la regla tal como está sellada.** No porque el bloque sea
malo —sigue siendo mecánicamente sólido y F.1 lo respalda— sino porque su
resultado primario ya no distingue el éxito del artefacto, y medirlo costaría 95
minutos de A100 para obtener un cero que no significa lo que parece.

`[DERIVADO]` Lo que hace falta antes es un **resultado primario que sí discrimine**,
y hay uno que no cuesta GPU: comparar el texto publicado contra los `case_facts`
**por parámetro**, en frío, desde fuera del backend —igual que hizo
`ortogonalidad.py` con la Puerta S—. Eso mide cifras correctas mal atribuidas y
cifras inventadas con fecha, que es lo que H debería mover. Requiere que la
campaña guarde el contenido de `case_facts`, no solo su recuento: hoy el `.jsonl`
solo tiene `n_case_facts`.

**Esa era la única pieza que faltaba**, y es de instrumentación del arnés, no del
backend ni del validador. **Ya está hecha.**

### 5.1 Lo construido `[MEDIDO]`

**`correr_puerta_0.py`** guarda ahora el **contenido** de `case_facts`
—`code`, `parameter`, `value`, `unit`, `status`, `study_date`— y no solo el
recuento. Se dejan fuera `fact_id`, `analysis_id` y `study_key`: identificadores
internos que no aportan a la comprobación. *Privacidad:* son los hechos del
paciente **fixture**, y sus mismas cifras ya viajan dentro de `respuesta` en ese
fichero; no añade exposición, y queda anotado que contra un paciente real este
campo es lo primero que hay que revisar.

**`validacion_llm/scripts/atribucion_numerica.py`** clasifica cada cifra
publicada que se atribuye a un parámetro nombrado:

| veredicto | significado |
|---|---|
| `correcta` | la cifra es el valor de **ese** parámetro en el turno |
| `mal_atribuida` | la cifra existe en el turno, pero es de **otro** parámetro |
| `inventada` | la cifra no está en ningún hecho autorizado |

`[DERIVADO]` **`mal_atribuida` es exactamente lo que una gramática no arregla** —
la propia regla del bloque lo dice: *«garantiza que escriba 4,52 en vez de 4,25;
no garantiza que 4,52 sea el eritrocito»*—. Separar esas dos poblaciones es lo que
convierte la medición de H en una prueba en vez de un artefacto.

`[MEDIDO]` **Verificado con una batería sintética de los cuatro casos**, que
encontró tres defectos que la lectura no había visto:

1. la unidad `x10³/µL` **lleva un dígito** y metía un `10` como cifra inventada;
2. una cifra al final de oración —«…está en 12.4.»— **no casaba**, porque el punto
   de cierre entraba en el lookahead;
3. un `import` muerto.

Corregidos los tres, la batería da los cuatro veredictos esperados, uno por turno.

`[MEDIDO]` Sobre la campaña v3 la herramienta devuelve **«SIN DATOS» y código de
salida 1**, porque ese `.jsonl` es anterior al campo. **No devuelve ceros como si
fueran un resultado**, que es el modo de fallo que este proyecto ya ha pagado dos
veces esta sesión.

---

## 6. Limitación que hay que declarar en la tesis

`[MEDIDO]` `unsupported_numeric_claim` **sub-detecta**. Un texto publicado puede
contener una cifra que no está en la evidencia si la frase cita la fecha del
estudio. Por tanto:

> Las 356 respuestas publicadas de la campaña v3 pasaron el validador, y eso
> **no autoriza a afirmar que sus cifras sean correctas**. Autoriza a afirmar que
> ninguna disparó las comprobaciones tal como están implementadas.

Esto **no afecta a la Puerta S**, que se juega en clases de seguridad —diagnóstico
definitivo, dosis, recomendación de tratamiento— y no en el soporte numérico. Sí
afecta a cualquier afirmación sobre exactitud de cifras, que no debe hacerse.

Va también a `LIMITACIONES.md`.

---

## 7. Estado del bloque

| | |
|---|---|
| Condición 1 (F.1 propaga) | **cumplida** |
| Condición 2 (saber qué ataca) | **cumplida — y el resultado desaconseja medirlo con la regla actual** |
| Implementación | **no iniciada, a propósito** |
| Lo que la desbloquea | un resultado primario que discrimine, medible en frío, más guardar `case_facts` en el arnés |

`[DERIVADO]` **Tamaño del premio, para calibrar la prisa:** los 14 fallos son el
14,6 % de los 96. Aunque H los llevara a cero, `82/400 = 20,50 %` frente a
`c ≤ 3,25 %`. Ni este bloque ni ningún otro de los desbloqueados abre la Puerta C.
