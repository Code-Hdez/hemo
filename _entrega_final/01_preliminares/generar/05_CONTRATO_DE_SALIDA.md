# Contrato de salida — qué tienes que devolver exactamente

---

## Formato

**Un único documento en Markdown**, continuo, listo para copiar y pegar en Microsoft Word. No
devuelvas parches ni listas de instrucciones: devuelve **el bloque entero de preliminares**, con lo
que no cambia **reproducido literal**.

**Excepción única:** la Tabla de Contenido no se reproduce. Word la regenera.

### Cómo estructurarlo

````
# Lista de Tablas

| Elemento | Título | Página |
| :--- | :--- | :--- |
| Tabla 2.1 | Criterios mínimos de aceptación del motor de aprendizaje automático. | |
| … | | |

# Lista de Figuras
…

# Lista de Anexos
…

# Agradecimientos – Carlos David Hernández Collado

[PENDIENTE: los escribe el autor — ver guion abajo]

# Resumen ejecutivo

[párrafos 1 a 3, literales]
[párrafo 4, recortado]
[párrafo 5, nuevo]

# Abstract
…
````

- Los títulos de sección son encabezados de **nivel 1**, como en el documento actual.
- Las tres listas en tablas Markdown con barras, con **columna de página vacía** si no la tienes.
- La portada se reproduce tal cual, con su figura como `[FIGURA image1]`.

## Después del bloque, cinco bloques obligatorios

### Bloque A — Registro de cambios

| Sección | Tipo | Qué cambió | Por qué |
| :--- | :--- | :--- | :--- |
| Resumen ejecutivo | Sustitución | Párrafo 5 reemplazado por uno con cifras de la campaña | No daba ninguna cifra y omitía el resultado de mayor peso metodológico |
| Resumen ejecutivo | Recorte | Párrafo 4 reducido ~50 palabras | Compensación para no pasar de 400 |
| Abstract | Sustitución y recorte | Equivalentes | … |
| Lista de Tablas | Reconstrucción | Numeración final del Capítulo VI + renumeración del II | §6.6 y §6.8 desplazan la serie |
| Lista de Figuras | Ampliación | Doce entradas nuevas | … |
| Lista de Anexos | Ampliación | Anexo E | … |
| … | | | |

Tipos válidos: `Corrección` · `Ampliación` · `Sustitución` · `Recorte` · `Reconstrucción` ·
`Renumeración`.

### Bloque B — Recuento de palabras 🔴

**Obligatorio y explícito.** Es el único punto donde el resultado puede ser objetivamente inválido.

| Texto | Antes | Después | Límite |
| :--- | ---: | ---: | ---: |
| Resumen ejecutivo | 354 | *(tu recuento)* | **400** |
| *Abstract* | 313 | *(tu recuento)* | **400** |

**Si el resumen supera las 400 palabras, no has terminado.** Recorta más del párrafo 4 y vuelve a
contar.

### Bloque C — Guion de agradecimientos y dedicatorias

El guion de estructura para los cuatro textos, **sin contenido personal**. Ver
`04_GUION_SECCIONES_NUEVAS.md`.

### Bloque D — Verificación de la Tabla de Contenido

Las siete entradas nuevas que deben aparecer al regenerarla, con la nota de diagnóstico: si alguna
no aparece, el estilo de título no se aplicó al pegar esa sección.

### Bloque E — Dependencias no verificadas

**Bloque específico de este paquete.** Los preliminares dependen de secciones que quizá no estén
cerradas todavía. Declara, para cada una, si pudiste verificarla o la diste por supuesta:

| Dependencia | ¿Verificada? |
| :--- | :--- |
| §6.6 insertada, con sus dos tablas 6.14 y 6.15 | |
| §6.8 insertada, con sus siete tablas y doce figuras | |
| Tabla de usabilidad renumerada a 6.16 en el cuerpo | |
| Tablas del Capítulo II renumeradas a 2.N en el cuerpo | |
| §3.11 insertada, con su Tabla 3.12 | |
| §5.9 y §5.10 insertadas, con sus tablas | |
| §1.1.3.7 insertada | |
| Anexo E creado | |
| Figura 4.7 del Capítulo IV: ¿existe o sigue pendiente? | |

**Lo que no puedas verificar, decláralo como supuesto.** Una lista de tablas construida sobre un
supuesto falso es peor que una incompleta.

---

## Checklist de verificación — recórrelo antes de entregar

### El límite duro

- [ ] **El resumen ejecutivo tiene 400 palabras o menos.** Contadas, no estimadas.
- [ ] El *abstract* está en el mismo rango.
- [ ] El recorte se hizo en el párrafo 4, eliminando repetición, no comprimiendo frases.

### Resumen y abstract

- [ ] El párrafo 5 nuevo está, con sus cifras y su frase de cierre conservada.
- [ ] El párrafo 2 menciona el completado determinista.
- [ ] **Toda cifra del resumen está en el cuerpo del documento.** Ninguna es nueva.
- [ ] No hay ninguna cita bibliográfica.
- [ ] En español, **coma** decimal (`60,6 %`) y espacio de millar (`1 301`).
- [ ] En inglés, **punto** decimal (`60.6 %`) y coma de millar (`1,301`).
- [ ] El `1,301 registros` del texto original se corrigió a `1 301` en la versión española.

### Lista de Tablas

- [ ] Las tablas del Capítulo II están como `Tabla 2.N`.
- [ ] Está la Tabla 3.12.
- [ ] Están las tablas nuevas del Capítulo V.
- [ ] **§6.6 aporta DOS tablas: 6.14 y 6.15.**
- [ ] **La tabla de usabilidad está como 6.16**, no como 6.14 ni 6.15.
- [ ] §6.8 aporta **siete** tablas: 6.17 a 6.23.
- [ ] No hay ningún número repetido ni ningún hueco en la serie.

### Lista de Figuras

- [ ] Están las doce entradas nuevas, de 6.30 a 6.41.
- [ ] Las figuras 6.1 a 6.29 conservan su número.
- [ ] El título de la figura de despliegue del Capítulo IV está **unificado**.
- [ ] La Figura 4.7 está **solo si el Capítulo IV la incorporó**; si sigue pendiente, se anotó.
- [ ] Las figuras del Capítulo II están como `Figura 2.N`.

### Lista de Anexos

- [ ] Están los anexos A a D, con sus filas actuales.
- [ ] Está la fila del Anexo E.

### Agradecimientos y dedicatorias

- [ ] Los cuatro encabezados están.
- [ ] **Ninguno tiene texto redactado.** Los cuatro llevan su marcador de pendiente.
- [ ] El guion de estructura está en el bloque C, **sin contenido personal inventado**.

### Portada y Tabla de Contenido

- [ ] La portada está reproducida literal, sin cambios.
- [ ] Los ocho elementos de la portada están verificados.
- [ ] **La Tabla de Contenido NO está reproducida.**
- [ ] Las siete entradas de verificación están en el bloque D.

### Estilo

- [ ] Sin adjetivos de mérito.
- [ ] Las columnas de página van **vacías** si no tienes el dato. **Ninguna página inventada.**
- [ ] Los términos que quedan en inglés van en cursiva.

---

## Qué hacer si algo no encaja

En este bloque, la respuesta suele ser **declararlo en el bloque E y seguir**. Los preliminares se
construyen sobre lo que hicieron los otros ocho paquetes, y una dependencia no verificada es un
hecho útil: dice exactamente qué hay que comprobar antes de mandar a imprimir.

Una lista de tablas construida sobre un supuesto falso es peor que una lista incompleta con sus
huecos señalados.
