# Contrato de salida — qué tienes que devolver exactamente

---

## Formato

**Un único documento en Markdown**, continuo, listo para copiar y pegar en Microsoft Word. No
devuelvas parches, diferencias ni listas de instrucciones: devuelve **el capítulo entero**, desde
el título hasta la última frase de la síntesis, con las secciones que no cambian **reproducidas
íntegras**.

Motivo: quien recibe esto va a seleccionar todo, copiar y pegar sobre el capítulo actual. Si
devuelves solo lo modificado, tendrá que reconstruirlo a mano y ahí es donde se cometen los
errores.

### Cómo estructurarlo

````
# Capítulo IV — Análisis y Diseño

## 4.1. Análisis del sistema

### 4.1.4. Requerimientos no funcionales

| ID | Requerimiento | Descripción |
| :--- | :--- | :--- |
| … | … | … |
| RNF-07 | Tolerancia a la interrupción del nodo de inferencia | … |
| RNF-08 | Integridad del *runtime* servido | … |

*Tabla 4.4. Requerimientos no funcionales del sistema.*

### 4.2.5. Diseño de despliegue
[dos párrafos actuales]
[tres párrafos nuevos]

[FIGURA image__]

*Figura 4.6. Diagrama de despliegue lógico de HemoVet.*

[FIGURA PENDIENTE 4.7]

*Figura 4.7. Diagrama de despliegue de HemoVet: nodo de aplicación y nodo de inferencia…*
````

- Encabezados con `#`, `##` y `###`.
- Tablas en Markdown estándar con barras, **completas**, con todas sus filas actuales.
- Títulos de tabla y pies de figura **debajo** del elemento, en cursiva.
- Las figuras existentes se mantienen como `[FIGURA imageNN]`, en su sitio.

## Después del capítulo, cuatro bloques obligatorios

### Bloque A — Registro de cambios

| Sección | Tipo | Qué cambió | Por qué |
| :--- | :--- | :--- | :--- |
| 4.1.4 | Ampliación | RNF-07 y RNF-08 en la Tabla 4.4 | La naturaleza interrumpible del nodo y la integridad del modelo servido no estaban requeridas |
| 4.2.4 | Ampliación | Cuatro párrafos de diseño conversacional | Faltaban puerta de contenido, completado determinista, resolución de elipsis e instrumentación de citas |
| 4.2.5 | Ampliación | Tres párrafos de despliegue | El diseño de dos nodos, el manifiesto y el arranque validado existían en el código y no en el papel |
| 4.2.5 | Corrección | Referencia «Figura 4.5» → «Figura 4.6» y unificación del título | Tres textos, tres versiones |
| 4.2.6 | Ampliación | Nota de magnitud y fila de contratos de despliegue | … |
| 4.3 | Ampliación | Media frase sobre la separación del nodo de inferencia | … |
| … | | | |

Tipos válidos: `Corrección` · `Ampliación` · `Renumeración` · `Estilo`.

### Bloque B — Marcadores pendientes

- `[FIGURA PENDIENTE 4.7]` — el diagrama de despliegue, con su pie.
- `[PENDIENTE: …]` — cualquier dato que dejaste sin resolver.

**Este bloque no puede estar vacío:** el diagrama de despliegue está pendiente por diseño.

### Bloque C — Figuras, inventario final

Lista de las figuras del capítulo con su número y pie final, señalando:

- cuál cambió de referencia en el cuerpo,
- **cuál necesita que se unifique su título en la Lista de Figuras**,
- cuál está pendiente de producir.

Es un bloque específico de este capítulo porque la referencia cruzada rota afecta a tres sitios
distintos del documento, y solo uno de ellos está en tu salida.

### Bloque D — Inconsistencias detectadas

Si encuentras una contradicción entre los archivos de este paquete, o un hecho que necesitas y no
está: **no la resuelvas inventando**. Escríbela aquí con la ubicación exacta y las dos versiones
en conflicto.

---

## Checklist de verificación — recórrelo antes de entregar

### Contenido

- [ ] Están §4.1 y §4.2 con **todas** sus subsecciones, y §4.3.
- [ ] **No se añadió ninguna sección ni subsección nueva.**
- [ ] Las secciones íntegras (§4.1.1, §4.1.2, §4.1.3, §4.1.5, §4.2.1, §4.2.2, §4.2.3, §4.2.7)
      están **reproducidas completas**, no resumidas ni «mejoradas».
- [ ] §4.2.4 tiene los cuatro párrafos nuevos, en el orden dado.
- [ ] §4.2.5 tiene los tres párrafos nuevos, **después** del de dependencias de arranque.
- [ ] La Tabla 4.4 conserva todas sus filas actuales y tiene RNF-07 y RNF-08.
- [ ] La Tabla 4.6 conserva todas sus filas y tiene la de contratos de despliegue.
- [ ] La extensión total está entre 3 900 y 4 500 palabras.

### Altitud — la Regla 1, que es la que se rompe

Busca en tu salida estas expresiones. **Ninguna puede aparecer** (salvo en el párrafo del apagado
de §4.2.5):

- [ ] «se detectó», «se observó», «se identificó», «se descubrió».
- [ ] «ronda», «iteración», «en una segunda fase», «posteriormente», «más adelante».
- [ ] Cualquier cifra de cuántos turnos, casos o respuestas fallaban.
- [ ] Cualquier latencia, tasa de fallo o porcentaje de mejora.
- [ ] Cualquier fecha o mes.

Y verifica lo contrario:

- [ ] Cada párrafo nuevo enuncia **una propiedad del sistema en presente** con su razón de diseño.
- [ ] El párrafo de los dos apagados está en pasado y es **el único** que lo está.

**La prueba final:** lee los párrafos nuevos preguntándote si describen cómo es el sistema o cómo
llegó a serlo. Si cuentan una historia, están en el capítulo equivocado.

### Cifras

- [ ] Toda cifra que escribiste está en `02_HECHOS_VERIFICADOS.md`.
- [ ] La cifra de módulos de §4.2.6 **coincide** con la de §4.2.1: son doce en ambas.
- [ ] No hay ninguna cifra de medición ni de resultado.

### Referencias cruzadas

- [ ] En el cuerpo de §4.2.5 la referencia dice **Figura 4.6**, no 4.5.
- [ ] El título de esa figura es el mismo en el cuerpo que el que propones para la Lista de
      Figuras.
- [ ] El marcador `[FIGURA PENDIENTE 4.7]` está, con su pie, y **referenciado desde el texto**.
- [ ] Toda tabla y toda figura está referenciada desde el texto antes de aparecer.

### Estilo

- [ ] Coma decimal en todos los números; espacio como separador de millares.
- [ ] Sin adjetivos de mérito.
- [ ] Términos traducidos según `03_ESTILO_Y_FORMATO.md`; los que quedan en inglés, en cursiva.
- [ ] Sin nombres de fichero, funciones ni variables del código.
- [ ] La lista del completado determinista es coherente en formato con el resto de §4.2.4.

---

## Qué hacer si algo no encaja

Es más útil un capítulo con un marcador de figura honesto que uno completo con un párrafo que
describe un diagrama que nadie ha dibujado.
