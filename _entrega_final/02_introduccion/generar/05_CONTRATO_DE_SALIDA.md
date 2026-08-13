# Contrato de salida — qué tienes que devolver exactamente

---

## Formato

**Un único documento en Markdown**, continuo, listo para copiar y pegar en Microsoft Word. No
devuelvas parches ni listas de instrucciones: devuelve **el bloque entero**, desde «Introducción»
hasta la última limitación, con todo lo que no cambia **reproducido literal**.

Motivo: quien recibe esto va a seleccionar todo, copiar y pegar sobre el documento actual. Si
devuelves solo el párrafo nuevo, tendrá que localizar el punto exacto de inserción a mano, y en un
bloque de cuatro secciones eso es más lento y más propenso a error que sustituirlo entero.

### Cómo estructurarlo

````
# Introducción

## Antecedentes del problema
[texto literal, con sus citas [n] intactas]

## Planteamiento inicial de la solución
[texto literal — sin tecnologías]

# Objetivos del proyecto
[texto literal: general y los cinco específicos]

# Justificación del proyecto
[texto literal]

# Limitaciones del proyecto
[las limitaciones actuales, literales]

[la limitación nueva, con el mismo formato que las anteriores]
````

- «Introducción», «Objetivos del proyecto», «Justificación del proyecto» y «Limitaciones del
  proyecto» son encabezados de **nivel 1**; las subsecciones de la introducción, de **nivel 2**.
  Respeta esa jerarquía, que es la del documento actual.
- Las figuras existentes, si las hay, se mantienen como `[FIGURA imageNN]`.

## Después del bloque, tres bloques obligatorios

### Bloque A — Registro de cambios

Debe ser **corto**. Si tu registro tiene más de tres filas, hiciste cambios que no correspondían.

| Sección | Tipo | Qué cambió | Por qué |
| :--- | :--- | :--- | :--- |
| Limitaciones del proyecto | Ampliación | Limitación de infraestructura: unidad de procesamiento gráfico contratada en modalidad interrumpible | El manual pide declarar las restricciones de capacidad informática fuera del control del equipo, y sostiene §2.6.1, §7.3 y §7.7 |

Tipos válidos: `Corrección` · `Ampliación` · `Estilo`.

### Bloque B — Verificación de integridad

**Bloque específico de este paquete**, porque aquí el encargo es sobre todo no romper nada.
Declara explícitamente:

- **Número de palabras** del bloque que devuelves.
- **Número de limitaciones** antes y después.
- **Número de citas `[n]`** antes y después, y si alguna cambió de número (no debería).
- **Confirmación** de que «Planteamiento inicial de la solución» no menciona ninguna tecnología,
  con la lista de términos que verificaste.
- **Confirmación** de que los cinco objetivos específicos se reproducen literales.

### Bloque C — Inconsistencias detectadas

Si encuentras una contradicción entre los archivos de este paquete, o un hecho que necesitas y no
está: **no la resuelvas inventando**. Escríbela aquí con la ubicación exacta y las dos versiones
en conflicto.

Puede quedar vacío. Es el único de los tres que puede.

---

## Checklist de verificación — recórrelo antes de entregar

### Contenido

- [ ] Están las cuatro secciones: Introducción (con sus cuatro subsecciones), Objetivos,
      Justificación y Limitaciones.
- [ ] Todo lo que no es la limitación nueva está **reproducido literal**, no parafraseado.
- [ ] Hay exactamente **una limitación más** que en el texto original.
- [ ] La limitación nueva va **al final** de la lista y con el **mismo formato** que las
      anteriores.
- [ ] La extensión total está entre 2 150 y 2 300 palabras.

### Lo que no se pudo tocar

- [ ] «Planteamiento inicial de la solución» **no menciona** XGBoost, Ollama, ChromaDB, FastAPI,
      React, Qwen, A100, Google Cloud ni ninguna otra tecnología concreta.
- [ ] Los cinco objetivos específicos están **literales**: no se fundió ninguno, no se reordenaron,
      no se reformularon.
- [ ] Las limitaciones existentes están **íntegras**.
- [ ] La justificación conserva sus cuatro dimensiones: conveniencia, relevancia social,
      implicaciones prácticas y valor teórico.

### Citas

- [ ] Todas las citas `[n]` se reproducen con **su número actual**.
- [ ] Ninguna cita cambió de sitio.
- [ ] No se añadió ninguna cita nueva. La limitación nueva **no lleva cita**.

### Cifras y altitud

- [ ] No aparece ninguna cifra de resultado, latencia o métrica del sistema.
- [ ] La limitación nueva **no** menciona el tiempo de arranque en frío ni la ausencia de
      rearranque automático: esos detalles van a §2.6.1 y §7.3.

### Estilo

- [ ] La limitación nueva **no** lleva frases defensivas del tipo «no obstante, el impacto es
      limitado».
- [ ] Coma decimal en los números, si hay alguno.
- [ ] Los términos que quedan en inglés van en cursiva.
- [ ] Sin adjetivos de mérito.

---

## Qué hacer si algo no encaja

En este bloque, la respuesta casi siempre es **no hacer nada y anotarlo**. Es el único de los nueve
paquetes donde el error más probable no es quedarse corto, sino pasarse.
