# Guion de los preliminares — qué se produce y qué no

> Este bloque tiene una particularidad que ninguno de los otros ocho tiene: **una parte del trabajo
> no la hace el LLM y no debe intentarlo.** Empezamos por ahí.

---

## Los agradecimientos y las dedicatorias: guion, no texto 🔴

Los cuatro encabezados existen con el cuerpo vacío. Hay que llenarlos, pero **no es un encargo de
redacción técnica**.

### Por qué el LLM no los escribe

Son textos personales de dos personas concretas: sobre su familia, sus profesores, su recorrido,
las cosas que les costaron. **Un agradecimiento generado se nota inmediatamente** —queda genérico,
simétrico y sin ninguna especificidad— y es de las pocas partes de una tesis donde eso salta a la
vista de cualquiera que lo lea.

Además, el comité los lee **antes que nada**: son la primera página con texto del empastado.

### Qué se produce en su lugar

Un guion de estructura por cada tipo, para que cada estudiante lo escriba. Algo de esta forma, sin
contenido personal inventado:

**Agradecimientos** — una página, prosa continua, sin viñetas. Suele recorrer, en este orden:

1. Las personas del ámbito académico que intervinieron en el trabajo: asesora, profesores, la
   escuela.
2. Las personas externas que hicieron posible partes concretas del proyecto: en este caso, los
   médicos veterinarios que participaron en la validación clínica y quienes facilitaron el acceso
   al corpus.
3. La familia y las personas cercanas.
4. Una frase de cierre.

**Dedicatoria** — media página o menos, más breve y más personal que los agradecimientos. Una o
dos personas, sin enumeración.

> **Lo que el guion debe decir explícitamente:** que se escriben en primera persona —es la única
> parte del documento donde corresponde— y que no llevan citas, cifras ni referencias al contenido
> técnico.

**Marcador que debe aparecer en la salida:**

```
[PENDIENTE: agradecimientos de Carlos David Hernández Collado — los escribe el autor]
[PENDIENTE: agradecimientos de Edwin Andrés Balbuena Bisonó — los escribe el autor]
[PENDIENTE: dedicatoria de Carlos David Hernández Collado — la escribe el autor]
[PENDIENTE: dedicatoria de Edwin Andrés Balbuena Bisonó — la escribe el autor]
```

---

## El resumen ejecutivo

**Dos operaciones, y la segunda es la que se olvida.**

### 1 · Sustituir el párrafo 5

El texto está en `02` §1. Entra donde estaba el actual, al final del resumen, y conserva la frase
de cierre —«HemoVet demuestra la viabilidad técnica de combinar…»— que ya funcionaba.

### 2 · Recortar el párrafo 4 🔴

**Sin este paso, el resumen se pasa del máximo.** La aritmética está en `02` §1: el párrafo nuevo
añade unas 90 palabras netas sobre un texto que ya tenía 354, y el manual sugiere un máximo de 400.

**Qué recortar:** el párrafo 4 —validación externa y clínica— repite cifras que el párrafo 3 ya
introduce. Unas cincuenta palabras de solapamiento.

**Cómo recortar:** eliminando la repetición, no comprimiendo las frases. Un resumen con frases
telegráficas se lee peor que uno con una idea menos.

### 3 · La corrección del párrafo 2

Donde describe la capa conversacional, añadir el completado determinista. Es media línea y pone al
día la descripción del sistema.

### 4 · Contar y declarar

**Cuenta las palabras del resumen final y decláralo en la salida.** Es el único límite duro de este
encargo y el único punto donde el resultado puede ser objetivamente inválido.

---

## El abstract

**Es la traducción del resumen, no un texto independiente.** Las mismas cuatro operaciones:
sustituir el párrafo equivalente, recortar en compensación, corregir la descripción de la capa
conversacional, y contar.

### Los dos detalles que se hacen mal

1. **Los decimales cambian de signo.** En español, coma: `60,6 %`. En inglés, punto: `60.6 %`. Es
   correcto que difieran entre los dos textos, y es el error más frecuente al traducir.
2. **Los millares también.** `1 301` en español; `1,301` en inglés.

**El registro del *abstract*** es el mismo que el del resumen: académico neutro, tercera persona,
sin adjetivos de mérito. No es una traducción literal palabra por palabra, pero tampoco una
reescritura: las mismas ideas, en el mismo orden, con las mismas cifras.

---

## Las tres listas

**Es la parte más mecánica y la que más errores acumula**, porque depende de que todos los demás
capítulos estén cerrados.

### Lista de Tablas

**Reconstruir entera**, con la numeración final que está en `02` §2. Tres bloques cambian:

- **Capítulo II:** renumeración de `Tabla 1`…`Tabla 6` a `Tabla 2.1`…`Tabla 2.6`, más las tablas
  nuevas de presupuesto.
- **Capítulo III:** entra la Tabla 3.12.
- **Capítulo V:** entran las tablas de §5.9 y §5.10.
- **Capítulo VI:** entra el bloque 6.14–6.23, y **la tabla de usabilidad se corre de 6.14 a 6.16**.

> 🔴 **Verifica el desplazamiento de usabilidad.** Es el punto donde una lista de tablas se rompe
> con más facilidad: una tabla que existe, que no cambia de contenido, pero sí de número. Si el
> cuerpo del Capítulo VI la renumeró y la lista no, quedan descuadrados.

### Lista de Figuras

**Añadir las doce entradas nuevas** después de la actual Figura 6.29. Están en `02` §3.

**Y verificar dos cosas más:**

- Si el Capítulo IV incorporó su diagrama de despliegue, añadir la `Figura 4.7`. Si sigue
  pendiente de dibujar, **no la añadas** y anótalo.
- Unificar el título de la figura de despliegue del Capítulo IV, que hoy tiene **tres versiones
  distintas** entre el cuerpo, el pie y esta lista.

### Lista de Anexos

**Una fila**, la del Anexo E. Está en `02` §4.

---

## La Tabla de Contenido

**No se produce.** Word la regenera desde los estilos de título, y reproducirla aquí sería trabajo
tirado.

Lo que sí se produce es **la lista de verificación**: las siete entradas nuevas que deben aparecer
en ella, con su página. Está en `02` §5.

> Si al regenerar la Tabla de Contenido alguna de las siete no aparece, el problema no es del
> índice: es que **el estilo de título no se aplicó** al pegar esa sección en Word. Conviene que
> esa frase esté en la salida, porque es el diagnóstico que ahorra media hora.

---

## La portada

**Verificación, no reescritura.** La checklist está en `02` §6. Ocho elementos, todos presentes.

Si el manual exige alguno adicional que no está, se anota como pendiente. **No se inventa.**

---

## El orden en que conviene hacerlo

Dentro de este bloque, y contando con que los capítulos ya están cerrados:

1. **Resumen y *abstract*** — no dependen de las listas y son lo que más piensa.
2. **Lista de Tablas** — la más delicada por el desplazamiento de usabilidad.
3. **Lista de Figuras** y **Lista de Anexos**.
4. **Verificación de la portada.**
5. **Guion de agradecimientos y dedicatorias.**
6. **Lista de verificación de la Tabla de Contenido.**

La Tabla de Contenido real se regenera en Word **después** de haber pegado todo lo demás y de
haber verificado que los estilos de título están aplicados.

---

## Una comprobación final que solo se puede hacer aquí

Los preliminares son el único punto del documento desde el que se ve el conjunto. Aprovéchalo:

**Recorre las tres listas y comprueba que cada entrada corresponde a algo que existe en el cuerpo,
y que cada tabla y figura del cuerpo aparece en su lista.** Es tedioso y es exactamente el tipo de
descuadre que un comité encuentra hojeando, sin buscarlo.
