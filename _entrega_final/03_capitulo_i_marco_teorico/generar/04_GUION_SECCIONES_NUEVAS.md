# Guion de §1.1.3.7 — arquitectura párrafo a párrafo

> Esto **no es texto para copiar**: es la arquitectura narrativa de la subsección. Cada apartado
> dice qué idea lleva, en qué orden, con qué citas y qué **no** debe decir.
>
> Extensión objetivo: **≈ 2 páginas** (900 a 1 100 palabras). Cinco apartados en dos páginas
> significa un párrafo denso por apartado, o dos en el primero.

---

## §1.1.3.7 · Rendimiento de inferencia de modelos de lenguaje

**Dónde va:** al final de §1.1.3, después de «1.1.3.6. LLM, RAG y diseño ético para comunicación
ciudadana», y antes de §1.1.4.

**Encabezado de nivel 4** —`1.1.3.7.`— igual que sus hermanas. No abras subapartados: los cinco
bloques que siguen son párrafos, no encabezados.

### Párrafo de entrada

Una o dos frases que digan de qué trata la subsección y por qué está en un trabajo sobre
interpretación hematológica: **el sistema incorpora un componente generativo cuyo tiempo de
respuesta domina la experiencia del usuario, y evaluarlo exige un vocabulario que las subsecciones
anteriores no proporcionan.**

No anuncies que el Capítulo VI va a refutar nada. El marco teórico no adelanta resultados.

---

### a) El régimen limitado por memoria

**Uno o dos párrafos. Es el bloque conceptual central.**

La idea: la inferencia autorregresiva de un modelo de lenguaje, **en la fase de decodificación**,
está gobernada por el ancho de banda de memoria y no por la capacidad aritmética, porque en cada
paso hay que recorrer todos los pesos del modelo para producir un solo token.

De ahí se derivan las dos consecuencias que el resto del documento va a usar:

1. **El techo teórico de decodificación** se aproxima por el cociente entre el ancho de banda de
   memoria y el tamaño del modelo. Puedes ilustrarlo con el ancho de banda nominal de la
   arquitectura empleada (2 039 GB/s) **sin calcular el techo de este despliegue concreto**: eso
   es §6.8.
2. **La métrica de eficiencia relevante es el aprovechamiento de ancho de banda (MBU)**, no la
   utilización de cómputo. Y conviene explicar aquí, en el marco, por qué un MBU bajo no implica
   ineficiencia: el aprovechamiento baja al subir el ancho de banda disponible porque la
   sobrecarga fija por token no escala con él. Sin esta explicación, el lector interpretará mal la
   cifra cuando llegue al Capítulo VI.

**Advertencia que debe quedar escrita**, porque el Capítulo VI la usa: el tamaño del modelo debe
tomarse en unidades decimales (GB) y no binarias (GiB). Confundirlas infla el techo un 7,4 %.

Cita: `[REF-NUEVA-1]` para el análisis *roofline* aplicado a transformadores; `[REF-NUEVA-3]` para
el dato de ancho de banda nominal.

---

### b) Prefill frente a decodificación

**Un párrafo.**

Las dos fases: en el *prefill* se procesa el mensaje de entrada completo **en paralelo**; en la
decodificación se emite la respuesta **token a token, de forma secuencial**.

Y las dos consecuencias prácticas:

- Ambas se expresan en tokens por segundo, **pero no son comparables entre sí** como medida de
  rendimiento. Presentarlas juntas en una tabla sin advertirlo induce a error.
- Con mensajes de entrada cortos, la cifra de *prefill* queda **dominada por la sobrecarga fija** y
  resulta inflada respecto de lo que daría un mensaje largo. Es un artefacto de medición conocido
  y hay que declararlo como tal.

---

### c) Decodificación restringida por gramática

**Un párrafo. Es el bloque que sostiene el mejor resultado del Capítulo VI, así que es el que hay
que escribir con más cuidado.**

Tres cosas, en este orden:

1. **Qué es.** El enmascarado por gramática obliga al modelo a producir únicamente salidas que se
   ajusten a una gramática formal —por ejemplo, un esquema JSON— descartando en cada paso los
   tokens que violarían la estructura.
2. **Para qué se usa.** Garantizar la validez sintáctica de la respuesta, lo que permite tratarla
   como dato estructurado sin capa de reparación posterior.
3. **Qué costo le atribuye la literatura.** Aquí va `[REF-NUEVA-2]`, con el valor concreto que esa
   fuente publica.

**Y la frase que hace legítimo el Capítulo VI**, que hay que escribir con precisión:

> El valor publicado corresponde a un despliegue determinado —con su servidor de inferencia, su
> modelo y su hardware— y su reproducción en otro despliegue es una **pregunta empírica**, no una
> constante del método.

Esa frase es la que convierte el resultado de §6.8 en una contribución legítima en vez de en una
contradicción con la literatura. Sin ella, refutar el valor parece un error de medición; con ella,
es exactamente lo que el manual llama «señalar cómo nuestro proyecto amplía la literatura actual».

> ❌ **No adelantes el resultado.** Ni la cifra medida, ni el factor de discrepancia, ni una
> insinuación del tipo «como se verá más adelante, este valor no se reprodujo». El marco teórico
> presenta el estado de la cuestión; el suspense no es su registro.

---

### d) Determinismo de la inferencia

**Un párrafo.**

Con temperatura cero, `top_k` igual a uno y semilla fija, la generación **debería** ser
reproducible dentro de una misma máquina.

Y las dos consecuencias:

- Esa reproducibilidad **no se extiende entre máquinas distintas**: cambian el orden de reducción
  en las operaciones de punto flotante, las rutinas seleccionadas por la biblioteca de cómputo y
  la versión del controlador.
- Por eso, si se quieren comparar mediciones, hay que **sellar la identidad del hardware junto con
  la del modelo**. La identidad del modelo sola no basta.

Este párrafo es el que justifica, más adelante, que la campaña verificara el determinismo antes de
aceptar ninguna serie de rendimiento.

---

### e) Reproducibilidad de mediciones de inferencia

**Un párrafo. Cierra la subsección.**

Qué debe registrar un protocolo de medición para que sus cifras sean recuperables. Enumera las
categorías —modelo, compendio, cuantización, versión del servidor de inferencia, controlador,
unidad de procesamiento gráfico exacta, parámetros de muestreo, esquema de salida, mensajes
renderizados, calentamiento, concurrencia y definición operativa de la métrica de latencia— sin
convertirlo en una lista con viñetas: es prosa.

**Y la idea de cierre:** un conjunto de cifras de inferencia sin ese registro no es reproducible
ni comparable, con independencia de lo cuidadosa que haya sido la medición. Es una propiedad del
protocolo, no de la diligencia de quien mide.

Cita: `[REF-NUEVA-5]` cabe aquí o en el apartado (d), a propósito del pre-registro.

> ❌ No digas que el protocolo anterior de este proyecto no cumplió esos requisitos. Eso es §3.11
> y §6.8. Aquí solo se enuncia el requisito.

---

## Las catorce entradas de glosario

Ya están redactadas en `02_HECHOS_VERIFICADOS.md` §1 y §2. El trabajo aquí es de **colocación**,
y tiene dos reglas:

1. **Orden alfabético dentro de su apartado, intercaladas con las existentes.** Es lo que hace el
   documento hoy. Meterlas en bloque al final se ve a simple vista y desordena el glosario.
2. **Formato idéntico al de las entradas existentes:** término en negrita, dos puntos, definición
   en prosa continua. Sin viñetas internas, sin ejemplos de código.

| Apartado | Correcciones | Adiciones |
| :--- | :---: | :---: |
| B · aprendizaje automático y evaluación | — | 6 |
| C · sistemas de IA y arquitectura | 2 (LLM, Ollama) | 6 o 7 |

> La entrada de **verificación de implicación textual** puede ir en B o en C. Elige una, decláralo
> en el registro de cambios, y no la pongas en las dos.

---

## Revisión de conjunto, al terminar

1. **La numeración de citas.** Las citas existentes conservan su número; las nuevas van como
   `[REF-NUEVA-n]` con su lista al final. **No renumeres nada**: insertar §1.1.3.7 desplaza toda
   la numeración posterior del documento y esa operación se hace en Word con referencias cruzadas.
2. **La extensión mínima.** El manual exige diez páginas para el marco teórico. El capítulo ya las
   superaba y con §1.1.3.7 las supera más, pero verifica que no perdiste texto al reproducir las
   secciones íntegras.
3. **La prueba de altitud.** Lee §1.1.3.7 imaginando que el Capítulo VI no existe. Debe leerse
   como un texto de referencia sobre inferencia de modelos de lenguaje, completo y sin huecos. Si
   suena a preámbulo de algo, tiene resultados dentro.
