# Petición de validación veterinaria — el porcentaje del diferencial en el chat

**Para:** el veterinario del equipo HemoVet
**De:** el equipo técnico · **Fecha:** 2026-08-15
**Tiempo estimado de lectura y respuesta:** 30 minutos
**Qué se pide:** una respuesta por escrito a las tres preguntas del final. Se
archivará como anexo de la tesis.

---

## 1. En una frase

Queremos **dejar de darle al modelo el porcentaje del diferencial como dato
citable**, y que sea el servidor quien publique el recuento absoluto con su
estado. Antes de hacerlo necesitamos que un veterinario confirme que eso es
clínicamente correcto y no empobrece la respuesta.

---

## 2. El problema, con el número delante

El chat rechaza una de cada cinco respuestas antes de publicarlas. El motivo más
frecuente tiene nombre: **`ambiguous_parameter_claim`**.

Ocurre así. Del hemograma le damos al modelo **dos cifras del mismo parámetro**:

```
neutrófilos, recuento absoluto  ...  dentro del rango
neutrófilos, porcentaje         ...  por encima del rango
```

El modelo escribe «los neutrófilos están altos». Nuestra comprobación automática
detecta que hay dos valores autorizados del mismo parámetro **con estados
contradictorios** y que la frase no dice a cuál se refiere, así que la rechaza.

**Y tiene razón en rechazarla.** El problema no es la comprobación: es que le
estamos pidiendo al modelo que resuelva una contradicción que nosotros mismos le
hemos puesto delante.

Lo hemos intentado cuatro veces por la vía de explicárselo mejor al modelo. Las
cuatro fallaron, medidas. En la última, la pregunta «¿qué valores aparecen fuera
del rango en este hemograma?» falló **las cinco veces** aun con la instrucción de
desambiguar activa.

---

## 2 bis. ANEXO — la campaña grande ya está hecha *(añadido el 15-ago-2026)*

Cuando escribimos esto teníamos 225 conversaciones de prueba. Ahora tenemos
**400**, y los números son más duros de lo que suponíamos.

### Es un solo parámetro: los neutrófilos

De los **31 rechazos** por esta causa, **los 31 son neutrófilos**. Ni uno solo es
de otro parámetro. Y **26 de los 31 no llegaron a publicar nada** — el usuario vio
un mensaje de error, no una respuesta peor.

La pregunta *«¿qué valores aparecen fuera del rango en este hemograma?»* falló
**9 de 9 veces**. Es la pregunta más natural que un propietario puede hacerle a un
chat de hemogramas, y hoy **no funciona nunca**.

### Y no es mala suerte de este paciente

Hemos mirado los **2429 hemogramas reales** de nuestro conjunto de datos y
comparado, en cada uno, si el neutrófilo absoluto y el porcentaje caen en la misma
categoría (bajo / normal / alto) según los rangos que usa el sistema —absoluto
2,9–11,0 ×10³/µL, porcentaje 60–80 %:

> **En 1057 de 2429 hemogramas (43,5 %) el absoluto y el porcentaje dicen cosas
> distintas.**

| absoluto ↓ · porcentaje → | bajo | normal | alto |
|---|--:|--:|--:|
| **bajo** | 83 | 20 | 4 |
| **normal** | **510** | 902 | 112 |
| **alto** | 32 | **379** | 387 |

**Casi la mitad de los hemogramas reales llevan esta contradicción dentro.** No
estamos arreglando un caso raro.

### Y tampoco es cosa de los neutrófilos

Los mismos 2429 hemogramas, para las otras dos poblaciones que reportamos en las
dos unidades:

| población | estados distintos |
|---|--:|
| Neutrófilos | **43,5 %** |
| Linfocitos | **35,8 %** |
| Monocitos | **29,8 %** |

Es decir: **la contradicción no depende del parámetro, sino de dar el absoluto y
el porcentaje a la vez.** En nuestras pruebas solo saltaron los neutrófilos porque
son los que divergen en el paciente concreto que usamos; con otro paciente habrían
saltado los linfocitos. Eso también quiere decir que **el arreglo, si lo
autorizáis, sirve para los tres**.

### Una segunda cosa que hemos visto y que preferimos preguntaros

La divergencia más común, con diferencia, es **absoluto normal + porcentaje bajo**:
**510 casos, el 21 %**. Es decir, perros con un recuento de neutrófilos
perfectamente normal cuyo porcentaje queda por debajo del 60 %.

Eso nos hace dudar de si el rango **60–80 %** que tenemos configurado es el
correcto para perro. Puede que sí y que simplemente sea así la distribución; puede
que esté demasiado estrecho y estemos fabricando parte de la contradicción
nosotros. **No lo vamos a tocar sin que nos lo digáis** — va como pregunta 4.

---

## 3. Lo que dice el estándar clínico, y por eso os preguntamos

Cornell University, College of Veterinary Medicine — *eClinPath*, sección
[WBC counts](https://eclinpath.com/hematology/tests/wbc-count/), literal:

> **«A differential count should never be interpreted in percentages but should
> always be interpreted with respect to the total WBC count.»**

Y su ejemplo:

> «30% eosinophils in an animal with a low normal WBC may not be an increase in
> absolute eosinophil count (i.e. an eosinophilia) but would certainly be called
> an eosinophilia if the WBC count was 20,000/µL (equating to 6,000/µL
> eosinophils).»

Si eso es correcto, entonces el porcentaje **no es interpretable por sí solo**, y
dárselo al modelo como un hecho citable independiente es un error nuestro, no del
modelo.

---

## 4. Lo que proponemos exactamente

**Hoy**, el chat puede escribir cualquiera de estas dos frases, y las dos le
constan como respaldadas:

> «El porcentaje de neutrófilos está elevado (78 %).»
> «Los neutrófilos absolutos están dentro del rango (8,2 ×10³/µL).»

**Con el cambio**, el porcentaje deja de ser un dato citable por su cuenta:

- Para cualquier afirmación de estado —alto, bajo, normal— el chat usa **el
  recuento absoluto**, que es el que tiene rango de referencia interpretable.
- **Si el usuario pide explícitamente el porcentaje**, el servidor lo publica,
  pero **nunca solo**: en la misma frase van el porcentaje, el absoluto y el
  recuento total de leucocitos, y la frase la construye el servidor, no el
  modelo. Por ejemplo:

  > «Neutrófilos: 78 % del diferencial, que sobre un recuento total de
  > 10,5 ×10³/µL son 8,2 ×10³/µL (dentro del rango de referencia).»

- El porcentaje **sigue apareciendo** en la ficha del hemograma y en la interfaz.
  Esto afecta solo a lo que el chat puede afirmar por su cuenta.

**No se toca ninguna comprobación de seguridad.** El cambio es sobre qué datos
entran, no sobre qué se permite decir.

---

## 5. Lo que puede salir mal, dicho por nosotros

Os lo contamos porque una validación que solo oye los argumentos a favor no vale
como validación:

1. **Respuestas más rígidas.** La frase que construye el servidor es correcta
   pero menos natural que la que escribiría el modelo. Si eso molesta al leer,
   queremos saberlo ahora.
2. **Un caso legítimo que se pierde.** Puede haber situaciones en que el
   porcentaje **sí** sea lo que un clínico quiere oír primero. Si existen,
   necesitamos ejemplos concretos para dejarlos fuera del cambio.
3. **No sabemos si funcionará.** Está medido que el problema existe; no está
   medido que este cambio lo resuelva. Tenemos escrita de antemano la regla que
   nos obligará a revertirlo si no baja al menos a la mitad.

---

## 6. Las tres preguntas

**P1.** ¿Es correcto que, en un hemograma canino, **una afirmación de estado**
(alto / bajo / normal) sobre una población leucocitaria deba hacerse sobre el
**recuento absoluto** y no sobre el porcentaje del diferencial?

☐ Sí ☐ No ☐ Sí, con matices → *¿cuáles?*

<br>

**P2.** ¿Os parece adecuada la frase que construiría el servidor cuando se pida
el porcentaje?

> «Neutrófilos: 78 % del diferencial, que sobre un recuento total de
> 10,5 ×10³/µL son 8,2 ×10³/µL (dentro del rango de referencia).»

☐ Sí ☐ No → *¿cómo la escribiríais?*

<br>

**P3.** ¿Hay algún parámetro o alguna situación clínica en que retirar el
porcentaje como dato citable **perjudique** la interpretación? Bandas, formas
inmaduras, relación neutrófilo/linfocito, o cualquier otro caso.

☐ No, ninguno ☐ Sí → *¿cuáles?*

<br>

**P4** *(añadida el 15-ago-2026, tras medir el conjunto de datos).* El rango de
referencia que tenemos configurado para el **porcentaje** de neutrófilos es
**60–80 %**. Con él, **510 de 2429 hemogramas reales (21 %)** salen con recuento
absoluto normal y porcentaje «bajo».

¿Es correcto ese rango para perro?

☐ Sí, es correcto y esa distribución es esperable
☐ No → *¿cuál usaríais?* ______________________
☐ No procede: si se retira el porcentaje como dato citable, el rango deja de
mostrarse y la pregunta se vuelve irrelevante

> **Nota nuestra:** no vamos a cambiar ese rango por nuestra cuenta, ni aunque nos
> conviniera. Va aquí porque lo hemos visto midiendo y nos parecería deshonesto
> callarlo.

---

## 7. Firma

```
Nombre y apellidos  ______________________________________________

Nº de colegiado     ______________________________________________

Fecha               ______________________________________________

Firma               ______________________________________________
```

> Este documento y la respuesta firmada se archivan juntos como anexo de la
> tesis. La justificación clínica de un cambio en los datos que ve el modelo no
> puede quedar solo en un commit.
