# Guion de §3.11 — arquitectura párrafo a párrafo

> Esto **no es texto para copiar**: es la arquitectura narrativa de la sección. Cada subsección
> dice qué idea lleva, en qué orden, con qué cifras de `02` y qué **no** debe decir.
>
> Extensión objetivo de toda §3.11: **3 a 4 páginas** (1 400 a 1 800 palabras). Once subsecciones
> en tres o cuatro páginas significa párrafos densos y sin relleno: dos o tres por subsección, y
> alguna de una sola frase larga.

---

## §3.11 · Metodología de recaracterización y pre-registro de hipótesis

**Dónde va:** después de §3.10 «Artefactos metodológicos generados», antes del Capítulo IV.

**Encabezado de nivel 2.** Las once subsecciones son de nivel 3. No bajes a nivel 4.

---

### 3.11.1 · Motivación y pregunta metodológica

**Un párrafo, dos como máximo.**

Sitúa el hecho: en agosto de 2026 el *runtime* conversacional se migró a una configuración con
aceleración por unidad de procesamiento gráfico, y el modelo servido pasó de cuatro a veintisiete
mil millones de parámetros.

Y planteando la pregunta que justifica toda la sección: **la pregunta no era si el sistema iba más
rápido —eso se observa— sino cuánto de la diferencia es atribuible a qué, y qué parte de la
comparación es siquiera legítima.** Esta sección describe el diseño con el que se respondió.

> ❌ No adelantes ninguna cifra de resultado. Ni el porcentaje de mejora, ni la latencia.

---

### 3.11.2 · Auditoría de comparabilidad previa

**Dos párrafos y una tabla pequeña, o dos párrafos y prosa.** Es la subsección más importante.

**Párrafo 1 — qué se hizo antes de medir nada.** Se inventarió la evidencia del protocolo
anterior: 208 ficheros, compendio calculado y verificado tras la copia (208 de 208 intactos).
Sobre ese corpus se reconstruyó el protocolo del 7 de agosto mediante un cuestionario de quince
preguntas de reproducibilidad. Enumera las categorías que cubren —modelo, compendio,
cuantización, versión del servidor, controlador, unidad gráfica exacta, parámetros de muestreo,
esquema de salida, mensajes renderizados, calentamiento, concurrencia y definiciones operativas de
latencia y de fallo— sin listarlas las quince una por una.

**Párrafo 2 — el resultado de la auditoría y lo que se deriva de él.** Once de las quince
preguntas no constan o constan parcialmente. De ahí se derivó un **veredicto doble de
comparabilidad**, que es la decisión metodológica central del capítulo. Preséntalo como tabla o
como prosa, pero con las dos filas explícitas:

- Fallos y comportamiento → **comparable con reservas**, declarando las desviaciones.
- Rendimiento físico → **no comparable**; toda cifra de decodificación es caracterización absoluta
  de la configuración vigente.

**Cierra con la frase de principio:** «no consta» se trató como un resultado, no como un vacío que
rellenar.

> Esta subsección es la que un miembro del comité puede usar para atacar el capítulo o para
> elogiarlo, según cómo esté escrita. Si suena a excusa —«no pudimos comparar»—, es un problema.
> Si suena a decisión —«se determinó qué era comparable antes de comparar»—, es rigor. La
> diferencia está en el orden: primero el procedimiento, después su resultado.

---

### 3.11.3 · Pre-registro de hipótesis

**Dos párrafos.**

**Párrafo 1 — el hecho.** Se redactaron y sellaron diez hipótesis con sus criterios de decisión
antes de tomar ninguna medida. El documento se selló con una función resumen criptográfica
(`5d6a0a71081e385e…`) que acredita su anterioridad. Cada hipótesis fija cuatro cosas: el
enunciado, la métrica, el umbral de decisión y qué observación la refutaría.

**Párrafo 2 — por qué importa.** Este es el párrafo que justifica la práctica, y conviene
argumentarlo con el caso concreto: sin pre-registro, un resultado cualquiera se lee como
confirmación de alguna expectativa que uno recuerde haber tenido. Con pre-registro, el criterio
está escrito antes, y **la hipótesis puede quedar refutada tanto como confirmada**. Cita los dos
criterios como ejemplo —«el p50 baja al menos un 50 %» y «la sobrecarga de gramática es de al
menos 10 ms/token, según la literatura consultada»— y señala que ambas se evaluaron con el mismo
procedimiento.

> ❌ **No digas cuál se cumplió y cuál se refutó.** Es la tentación más fuerte de toda la sección.
> El valor argumentativo está en la simetría del procedimiento, no en el desenlace.

---

### 3.11.4 · Instrumentación y caminos de medición

**Un párrafo y una enumeración breve, o dos párrafos.**

Los dos caminos, con sus propósitos distintos: el camino A mide la física del *runtime* sin la
aplicación en medio; el camino B mide el comportamiento del sistema tal como lo ve el usuario.

**Documenta por qué se separan**, y termina con la limitación del instrumento: el camino B no
expone los campos de temporización interna del servidor de modelos, lo que hizo no evaluable una
de las diez hipótesis por esa vía. **Escribe explícitamente que es una limitación del instrumento
y no del sistema.**

---

### 3.11.5 · Control de identidad del sistema medido

**Un párrafo, la Tabla 3.12, y un párrafo de cierre.**

**Párrafo previo a la tabla.** Todo el capítulo se mide bajo un único sello: modelo, compendio,
tamaño, versión del servidor, unidad gráfica, controlador, atención rápida, tipo de caché,
paralelismo y persistencia en memoria. Referencia la tabla antes de que aparezca.

**Tabla 3.12** con el contenido de `02` §4.

**Párrafo de cierre — el principio y su matiz.** La identidad no se asume: **se verifica respuesta
a respuesta**. En las 115 respuestas registradas se comprobó el identificador de modelo en todas
—censo, no muestra—. Y el matiz obligatorio: la comprobación fue necesaria porque el modelo
anterior sigue instalado en el servidor y la guarda del código no impide su uso, de modo que la
garantía es de verificación posterior y no de imposibilidad por diseño.

---

### 3.11.6 · Canario de determinismo

**Un párrafo.**

Antes de aceptar ninguna medición se verificó que el sistema fuera reproducible dentro de la misma
máquina: 20 mensajes × 5 repeticiones = 100 generaciones, con temperatura 0, `top_k` 1 y semilla
fija. El criterio: ningún mensaje puede producir más de un compendio de respuesta distinto.

**Lo importante es la función, no el número:** es una compuerta previa, y solo tras superarla se
dieron por válidas las series de rendimiento.

> ❌ No escribas el resultado del canario. Escribe que existía y cuál era su criterio.

---

### 3.11.7 · Ablación de la decodificación restringida por gramática

**Un párrafo de diseño y una enumeración de tres limitaciones.**

**Párrafo de diseño.** n = 30 por brazo, con y sin esquema de salida forzado, intercalados
A/B/A/B para neutralizar deriva térmica o de estado, con 5 descartes de calentamiento, pausa de
500 ms entre generaciones, temperatura 0, semilla fija, tope de 200 tokens de salida y ventana de
contexto fija para no forzar recarga del modelo. Seis mensajes rotados.

**Las tres limitaciones**, como enumeración genuina (esta sí lo es):

1. Ambos brazos alcanzaron el tope de tokens: se compara en régimen de decodificación pura y **no
   se mide el costo de la gramática en la terminación**.
2. La diferencia en número de tokens es cero por construcción, así que el sesgo «la gramática
   genera menos» no pudo evaluarse.
3. Solo se conservaron estadísticos resumen, no los valores crudos: no hay intervalo *bootstrap*,
   solo mediana y rango intercuartílico. **Es un incumplimiento del propio protocolo, y se
   declara.**

> La tercera limitación es la que más cuesta escribir y la que más crédito da. No la suavices.

---

### 3.11.8 · Réplica estricta pareada

**Dos párrafos.**

**Párrafo 1 — el diseño.** Para contrastar comportamiento antes y después se reejecutó el
protocolo anterior sobre la configuración nueva, pareando por identificador de caso: 64 casos con
latencia, 70 turnos para el análisis de fallos. Contraste de latencia con prueba de Wilcoxon de
rangos con signo e intervalo *bootstrap* de 10 000 remuestreos; contraste de proporción de fallos
con McNemar exacto. Declara las dos desviaciones (D-1 y D-2).

**Párrafo 2 — el criterio de aceptación sellado.** Cítalo literal: *«si la cuenta cuadra y los
identificadores no, el aparato no sirve»*. Y explica qué significa: no basta con que el número de
fallos baje, hay que comprobar si son los mismos fallos. Este párrafo es el que hace que el
resultado del Capítulo VI se lea como rigor y no como excusa, así que merece estar bien escrito.

---

### 3.11.9 · Tratamiento de proporciones y de los ceros

**Un párrafo.**

Toda proporción se reporta con intervalo de confianza de Wilson, incluidas —y sobre todo— las
observadas en cero. Explica el porqué: cero casos observados no demuestra ausencia; informar solo
el valor puntual induce a concluir que el fenómeno no existe cuando el diseño únicamente excluye
tasas superiores a la cota.

Puedes ilustrarlo con la escala de esfuerzo —acotar al 5 % exigiría del orden de 60 observaciones;
al 1 %, unas 300— sin dar la cota concreta de ningún resultado. Si prefieres darla, remite a §6.8.

---

### 3.11.10 · Análisis de potencia

**Un párrafo.**

Se calculó el tamaño de muestra necesario por grupo frente a la diferencia detectable (α = 0,05
bilateral, potencia del 80 %). Con una tasa base del 10 %, distinguir 10 % de 5 % exigiría 431
observaciones por grupo; los tamaños disponibles fueron 9, 15, 45, 64 y 70.

**La frase que tiene que quedar escrita:** este diseño distingue un efecto grande de la ausencia
de efecto, y no distingue uno intermedio. Y la razón de ponerlo aquí: declararlo en metodología
evita justificarlo caso por caso en el Capítulo VI, y convierte los resultados no concluyentes en
una limitación conocida del diseño en lugar de en un fallo del análisis.

---

### 3.11.11 · Trazabilidad y verificación de la cadena

**Un párrafo y una frase de cierre.**

Cada figura del análisis declara su fichero fuente, el compendio SHA-256 de ese fuente, el tamaño
de muestra y la marca MEDIDO o DERIVADO. Cada figura se exporta en tres formatos con compendio
propio. El cuaderno de análisis ejecuta once aserciones que recalculan desde los datos crudos las
cifras publicadas: **diez pasan y una falla, y la que falla queda declarada en el propio informe**
(la cota de alucinación publicada asumía unas 20 preguntas verificables cuando el fichero de
verdad contiene 9).

**Cierra la sección —y el capítulo— con esta idea:** un análisis que solo publica las aserciones
que pasan no es un análisis verificado.

---

## Las tres ampliaciones fuera de §3.11

Son cortas y mecánicas. El contenido exacto está en `02_HECHOS_VERIFICADOS.md` §11.

| Dónde | Qué | Extensión |
| :--- | :--- | :--- |
| §3.5.1, al final | Un párrafo sobre el congelamiento del *runtime* conversacional | 1 párrafo |
| §3.7.1, Tabla 3.8 | Una fila para la batería F de contenido sustantivo, **más una o dos frases en el cuerpo** que expliquen su aporte ortogonal: una respuesta que solo deriva pasa las demás baterías de forma vacua | 1 fila + 2 frases |
| §3.10, tabla | Siete filas con los artefactos de la campaña | 7 filas |

> La fila de la batería F **necesita las frases de acompañamiento**. Una fila suelta en una tabla
> no explica por qué hacía falta una sexta batería, y esa explicación es justamente lo que
> justifica metodológicamente el trabajo de agosto.

---

## Revisión de la entradilla del capítulo

La entradilla actual enumera lo que el capítulo cubre. Al añadir §3.11, hay que mencionarla: media
frase basta, en el mismo registro que el resto. No reescribas la entradilla entera.
