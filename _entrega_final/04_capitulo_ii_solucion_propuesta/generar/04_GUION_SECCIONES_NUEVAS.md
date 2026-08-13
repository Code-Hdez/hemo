# Guion de las secciones nuevas y reescritas

> Esto **no es texto para copiar**: es la arquitectura de lo que hay que escribir. Los textos que
> ya están redactados —§2.1, §2.6.1, §2.6.3, la fila de §2.2.2— están en
> `02_HECHOS_VERIFICADOS.md`; aquí se dice **dónde encajan y qué tono llevan**.
>
> Lo único que hay que redactar de cero son **las tres subsecciones de presupuesto** y **el texto
> que acompaña a la tabla de hardware**.

---

## Mapa de intervención

| Sección | Qué se hace | Origen | Tamaño |
| :--- | :--- | :--- | :--- |
| 2.1 | Sustituir una frase | `02` §1 | 1 frase |
| 2.2.2 | Añadir una fila a la tabla de entregables | `02` §7 | 1 fila |
| 2.5 | Corregir la frase introductoria de las categorías | — | 1 frase |
| 2.5.1 | **Reconstruir la tabla** + escribir el texto que la acompaña | `02` §2 | 1 tabla + 2 párrafos |
| 2.5.2 | Corregir una fila, añadir otra, explicar el cero | `02` §3 | 2 filas + 1 frase |
| 2.5.3 | **Subsección nueva** · Datos | `02` §4 | 1 párrafo + 1 tabla |
| 2.5.4 | **Subsección nueva** · Recursos humanos | `02` §4 | 1 párrafo + 1 tabla |
| 2.5.5 | **Subsección nueva** · Costos operativos | `02` §4 | 1 párrafo |
| 2.6.1 | Reescribir entera | `02` §5 | 3 párrafos |
| 2.6.3 | Sustituir un criterio, añadir otro | `02` §6 | 2 criterios |
| Todo | Renumerar tablas 1–6 → 2.1–2.6 y figuras 1–3 → 2.1–2.3 | `00` | mecánico |

---

## §2.5 · El párrafo introductorio del presupuesto

**Una frase, pero decide la estructura de toda la sección.**

El texto anuncia cinco categorías y solo desarrolla dos. **La salida correcta es escribir las tres
que faltan, no rebajar la frase a «dos categorías».** Un presupuesto de proyecto de grado que
declara cero costo de recursos humanos y cero costo operativo es un presupuesto que el comité va a
preguntar, y la pregunta es peor que la respuesta.

Conserva la frase tal como está —anuncia cinco— y asegúrate de que las cinco existen.

---

## §2.5.1 · Hardware — la reconstrucción

**Una tabla y dos párrafos. Es el bloque de mayor riesgo del capítulo.**

### La tabla

Estructura completa en `02` §2. Nueve filas, cinco columnas, con **columna en dólares y columna en
pesos dominicanos**, subtotal, contingencia del 10 % y total.

**Todos los importes que no conozcas van como `[PENDIENTE: qué hay que consultar]`.** No como
`0,00`, no como una estimación redonda, no como un rango. La celda tiene que decir qué se consulta
para llenarla: «tarifa publicada del proveedor × horas facturadas», «valor de mercado local en
fecha».

### Párrafo previo a la tabla

Explica **el criterio de valoración**, que es lo que el manual exige y hoy falta: se valoran los
equipos propios a precio de mercado local aunque no supongan desembolso, se contabiliza el cómputo
en nube por su facturación real, y se añade un porcentaje de contingencia.

### Párrafo posterior a la tabla

Dos cosas:

1. **La nota de la tasa de cambio**, con su fecha. Sin ella, la columna en pesos no es verificable.
2. **La declaración sobre las horas de la máquina de inferencia.** Si usas los datos de las seis
   ventanas de encendido, hay que escribir que **tres de ellas son cota inferior** —solo registran
   el intervalo entre el primer y el último turno, sin el arranque de la máquina ni la carga del
   modelo, que superó los dos minutos— y que **cubren solo la campaña de medición, no la operación
   del servicio**.

> **Por qué este párrafo importa.** Un presupuesto que declara sus propios límites de medición es
> defendible. Uno que presenta una cota inferior como si fuera el consumo total, no. Y la
> diferencia entre ambos son tres frases.

---

## §2.5.2 · Software y licencias

**Dos filas y una frase.**

La corrección de la fila del modelo es mecánica. La fila del controlador y CUDA es nueva.

**La frase que hay que añadir** explica por qué el costo de licencia es cero y no es un descuido:
el software es de fuente abierta y lo que cuesta es el cómputo, que se contabiliza en la tabla de
hardware. Un cero sin explicación se lee como olvido; un cero explicado se lee como decisión.

---

## §2.5.3 · Datos — subsección nueva

**Un párrafo y una tabla de tres filas.**

Puede cerrarse en 0,00, pero **la justificación tiene que estar escrita**: el corpus clínico se
obtuvo por convenio institucional y la cohorte externa es de acceso abierto.

**El matiz que conviene añadir:** el corpus de conocimiento del asistente —1 252 documentos— es de
elaboración propia, y su costo real está en las horas de trabajo, no en una licencia. Decláralo
como 0,00 con remisión a §2.5.4, no como si no hubiera costado nada.

---

## §2.5.4 · Recursos humanos — subsección nueva

**Un párrafo y una tabla de tres filas.**

Es la subsección que más incomoda escribir en un proyecto de grado —el trabajo lo hicieron los
propios estudiantes— y es precisamente la que el manual pide valorar.

**El párrafo** explica el criterio: horas-persona valoradas a tarifa de mercado local para el rol
correspondiente, con independencia de que no supongan desembolso.

**La tabla** distingue tres roles: desarrollo e integración, ingeniería de datos y modelado, y
validación clínica. Este último es distinto: los evaluadores veterinarios son personas externas al
equipo, y su participación tiene un valor de mercado claro.

> **Sobre las horas.** El cronograma de §2.3 da los frentes de trabajo y su duración: estimarlas a
> partir de ahí es legítimo, y conviene decir en el texto que esa es la base. **Inventar la tarifa,
> no.** Deja las tarifas como pendientes.

---

## §2.5.5 · Costos operativos de despliegue — subsección nueva

**Un párrafo, sin tabla.**

El grueso —las dos máquinas virtuales— ya está en §2.5.1. Esta subsección **remite a esa tabla** y
añade lo que no cabe allí: tráfico de red, registro de imágenes de contenedor y almacenamiento de
respaldo.

> ⚠️ **No dupliques la cifra de la máquina de inferencia en dos subsecciones.** Si aparece en
> §2.5.1 y otra vez aquí, el total del presupuesto queda inflado y es un error que se detecta
> sumando. Decláralo en una y remite desde la otra.

---

## §2.6.1 · Entorno de ejecución — reescritura completa

**Tres párrafos, ya redactados en `02` §5.**

El orden importa y no conviene alterarlo:

1. **La topología real.** Dos máquinas, qué corre en cada una, y por qué se comunican por dirección
   interna estática: para que el reemplazo del hardware de inferencia no toque el backend.
2. **El arranque a prueba de fallos.** Es una garantía de la demostración: el sistema no puede
   servir tráfico con una configuración distinta de la sellada.
3. **El procedimiento de contingencia.** Tres medidas concretas, numeradas.

**El tercer párrafo es el que el comité va a leer con más atención**, porque responde a la
pregunta obvia: *¿y si el día de la defensa el proveedor reclama la máquina?* La respuesta honesta
—verificación con antelación, consulta de calentamiento, capturas de respaldo— es mejor que
fingir que no puede pasar.

> ⚠️ **Pendiente operativo que afecta a la demostración y que no es tarea del LLM:** la máquina de
> producción quedó temporalmente degradada por un evento de capacidad zonal y está pendiente
> devolverla a su dimensionamiento previo. **Hacerlo antes de la defensa, no durante.** Y la
> instancia interrumpible no tiene vigilante de rearranque: si el proveedor la reclama, queda
> parada.

---

## §2.6.3 · Criterios de éxito

**Un criterio se sustituye y otro se añade.**

**El que se sustituye (iv)** mezclaba dos latencias de órdenes de magnitud distintos: la del motor
de clasificación (milisegundos) y la de la generación conversacional (decenas de segundos). El
reemplazo las separa y fija un umbral realista para cada una.

**Explica la separación en el texto, no solo en el criterio.** Una frase basta: el análisis
hematológico y la conversación son operaciones de naturaleza distinta y evaluarlas con un mismo
umbral no informa de nada.

**El que se añade (vi)** —que toda respuesta procede del modelo sellado— es una garantía real del
sistema que hoy no se reclama en ninguna parte del documento. Es de las pocas ocasiones en que se
puede añadir un criterio de éxito **sabiendo de antemano que se cumple**, y conviene aprovecharla.

**Los demás criterios se mantienen** literales: etiquetas esperadas sin error, activación de la
regla de control de calidad en el caso D, rechazo de la solicitud adversaria, y no exposición de
identificadores reales.

---

## La renumeración

**Es mecánica pero se olvida.** Dos operaciones:

1. Cambiar los títulos: `Tabla 1` → `Tabla 2.1` … `Tabla 6` → `Tabla 2.6`, y `Figura 1` →
   `Figura 2.1` … `Figura 3` → `Figura 2.3`.
2. **Actualizar las referencias del cuerpo.** Busca en el texto cada «la Tabla 4», «la Figura 2» y
   corrígelas. Este segundo paso es el que se olvida, y una referencia rota es más visible que la
   numeración suelta que se venía a arreglar.

Las tablas nuevas continúan la serie: **2.7** (datos), **2.8** (recursos humanos) y **2.9** si
decides que §2.5.5 lleve tabla.

---

## Revisión de conjunto, al terminar

1. **Suma el presupuesto mentalmente.** Ninguna partida puede aparecer en dos subsecciones. La
   máquina de inferencia es la candidata más probable a duplicarse.
2. **Cuenta las categorías.** El párrafo de §2.5 anuncia cinco; tienen que existir cinco.
3. **Busca cifras de dinero sin marcador.** Cada importe o está justificado o está pendiente. No
   hay tercera opción.
4. **Comprueba que las cinco tablas y las tres figuras están renumeradas**, título y referencias.
