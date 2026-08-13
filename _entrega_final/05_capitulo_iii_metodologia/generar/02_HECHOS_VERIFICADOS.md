# Hechos verificados — la única fuente de cifras para el Capítulo III

> Toda cifra del capítulo debe salir de aquí. Cada entrada lleva su marca:
> **[MEDIDO]** leído directamente de un artefacto · **[DERIVADO]** calculado a partir de artefactos
> · **[NO CONSTA]** no recuperable, y eso **es un resultado**, no un vacío que rellenar ·
> **[PENDIENTE]** no disponible en este paquete: usar marcador, **nunca** estimar.
>
> Recuerda la Regla 1: aquí hay cifras **de diseño** (legítimas en este capítulo) y cifras **de
> resultado** (que pertenecen al Capítulo VI). Cada bloque dice cuál es cuál.
>
> Verificado el 12 de agosto de 2026 sobre la rama `main`, commit `f9deedb`.

---

## 1 · Auditoría de comparabilidad previa — material para §3.11.2

**Todas estas cifras son de diseño y de auditoría: van en este capítulo.**

| Dato | Valor | Marca |
| :--- | :--- | :---: |
| Ficheros de evidencia previa inventariados | **208** | MEDIDO |
| Integridad verificada tras la copia | **208 de 208** compendios intactos | MEDIDO |
| Preguntas del cuestionario de reproducibilidad | **15** | MEDIDO |
| Preguntas que **no constan o constan parcialmente** | **11 de 15** | MEDIDO |
| Fecha del protocolo reconstruido | 7 de agosto de 2026 | MEDIDO |

Las quince preguntas cubren: modelo, compendio, cuantización, versión del servidor de modelos,
controlador, unidad de procesamiento gráfico exacta, parámetros de muestreo, esquema de salida,
mensajes renderizados, calentamiento, concurrencia, definición operativa de latencia, definición
operativa de fallo, encadenado de sesión y semilla.

### El veredicto doble de comparabilidad — la decisión metodológica central

| Ámbito | Veredicto | Consecuencia metodológica |
| :--- | :--- | :--- |
| Fallos y comportamiento del sistema | **COMPARABLE CON RESERVAS** | Se puede contrastar el antes y el después, declarando las desviaciones |
| Rendimiento físico del *runtime* | **NO COMPARABLE** | Toda cifra de decodificación, MBU o TPOT es caracterización absoluta de la configuración vigente, **nunca** comparación entre unidades gráficas |

> «NO CONSTA» se trató como un resultado, no como un vacío que rellenar. Esa postura es la que
> sostiene la honestidad de todo el capítulo, y conviene que quede escrita como decisión
> deliberada y no como excusa.

---

## 2 · Pre-registro de hipótesis — material para §3.11.3

| Dato | Valor | Marca |
| :--- | :--- | :---: |
| Hipótesis redactadas y selladas **antes de medir** | **10** | MEDIDO |
| Compendio del documento de pre-registro | `5d6a0a71081e385e…` | MEDIDO |
| Contenido fijado por cada hipótesis | enunciado, métrica, umbral de decisión, y qué observación la refutaría | MEDIDO |

**Los dos criterios de decisión que conviene citar en el texto** (son metodología: se escribieron
antes de medir, y su cumplimiento o no es resultado del Capítulo VI):

- **H-5:** «el p50 por turno baja al menos un 50 %».
- **H-2:** «la sobrecarga de la decodificación restringida por gramática es de al menos
  10 ms/token», valor tomado de la literatura consultada.

> ⚠️ **Aquí NO se dice cuál se cumplió y cuál no.** Eso es §6.8. Lo que este capítulo explica es
> **por qué** importa haberlo escrito antes: sin pre-registro, cualquier resultado se lee como
> confirmación de alguna expectativa que uno recuerde haber tenido. Con pre-registro, el criterio
> estaba escrito antes y la hipótesis puede quedar refutada tanto como confirmada. Las dos cosas
> valen igual, y esa simetría es el argumento de la subsección.

---

## 3 · Instrumentación — material para §3.11.4

Dos caminos de medición con propósitos distintos:

| Camino | Qué mide | Para qué |
| :--- | :--- | :--- |
| **A · servidor de modelos directo** | Física del *runtime* sin la aplicación en medio | Tiempo por token de salida, decodificación, *prefill*, aprovechamiento de ancho de banda, determinismo, ablación de gramática |
| **B · aplicación completa** | Comportamiento del sistema tal como lo ve el usuario | Desenlace del turno, latencia extremo a extremo, contenido de la respuesta, clase de fallo |

**Limitación del instrumento que hay que declarar:** el camino B **no expone** los campos de
temporización interna del servidor de modelos (recuento y duración de evaluación, duración de
carga), lo que hizo **no evaluable** una de las diez hipótesis por ese camino. [MEDIDO]

> Esa limitación es **del instrumento, no del sistema**, y así debe presentarse. Es una distinción
> que el comité valora: confundirlas convierte una restricción de medición en un defecto del
> producto.

---

## 4 · Control de identidad del sistema medido — material para §3.11.5 y Tabla 3.12

| Campo | Valor | Marca |
| :--- | :--- | :---: |
| Modelo | Qwen3.6 de 27 mil millones de parámetros, cuantización Q4_K_M (`qwen3.6:27b-q4_K_M`) | MEDIDO |
| Compendio del modelo | `a50eda8ed977ab48…` | MEDIDO |
| Tamaño | 17 420 432 739 bytes = 16,224 GiB = 17,420 GB | MEDIDO |
| Servidor de modelos | Ollama **0.32.6** | MEDIDO |
| Unidad de procesamiento gráfico | NVIDIA **A100-SXM4-40GB**, modalidad interrumpible | MEDIDO |
| Controlador / CUDA | 580.159.03 / 13.0 | MEDIDO |
| Ventana de contexto por petición | 16 384 tokens | MEDIDO |
| Atención rápida / caché de claves y valores | activada / `q8_0` | MEDIDO |
| Paralelismo / persistencia en memoria | 1 / residente | MEDIDO |
| Respuestas registradas con identidad verificada | **115 de 115** (censo, no muestra) | MEDIDO |
| Modelos instalados en el nodo | **2**: el sellado y el anterior de 4 mil millones | MEDIDO |

**Esta tabla es la Tabla 3.12.** El principio metodológico que la acompaña: la identidad **no se
asume, se verifica respuesta a respuesta**.

> ⚠️ **Matiz obligatorio.** La verificación fue necesaria porque el modelo anterior sigue
> instalado en el servidor y la comprobación presente en el código **no impide su uso**. La
> garantía es de verificación posterior, no de imposibilidad por diseño. Declararlo aquí, en
> metodología, es lo que hace legítimo el censo.

> ⚠️ Dos correcciones que la medición impuso sobre lo que el equipo creía: el peso real es
> 17 420 432 739 bytes, **no** los 16,93 GB que se habían declarado; y el servidor es **0.32.6**,
> no 0.32.5. Si esas cifras antiguas aparecen en el capítulo, corregirlas.

---

## 5 · Canario de determinismo — material para §3.11.6

| Parámetro del diseño | Valor | Marca |
| :--- | :--- | :---: |
| Mensajes distintos | 20 | MEDIDO |
| Repeticiones por mensaje | 5 | MEDIDO |
| Generaciones totales | **100** | DERIVADO |
| Temperatura / `top_k` / semilla | 0 / 1 / fija | MEDIDO |
| Criterio de aceptación | ningún mensaje puede producir más de un compendio de respuesta | MEDIDO |

**Función metodológica:** es una **compuerta previa**. Solo tras pasarla se dieron por válidas las
series de rendimiento. El resultado del canario pertenece al Capítulo VI; lo que va aquí es que la
compuerta existía y cuál era su criterio.

---

## 6 · Ablación de la decodificación por gramática — material para §3.11.7

| Parámetro del diseño | Valor | Marca |
| :--- | :--- | :---: |
| Tamaño por brazo | **n = 30** | MEDIDO |
| Brazos | con y sin esquema de salida forzado | MEDIDO |
| Orden | **intercalado A/B/A/B**, para neutralizar deriva térmica o de estado | MEDIDO |
| Descartes de calentamiento | 5 | MEDIDO |
| Pausa entre generaciones | 500 ms | MEDIDO |
| Temperatura / semilla | 0 / fija | MEDIDO |
| Tope de tokens de salida | 200 | MEDIDO |
| Ventana de contexto | fija, para no forzar recarga del modelo | MEDIDO |
| Mensajes | 6, rotados | MEDIDO |

### Las tres limitaciones que la propia campaña declara — hay que escribirlas

1. **Ambos brazos alcanzaron el tope de tokens**, de modo que la comparación se hace en régimen de
   decodificación pura: **no se mide el costo de la gramática en la terminación**.
2. La diferencia en número de tokens generados es **cero por construcción**, así que el sesgo «la
   gramática genera menos» no pudo evaluarse con este diseño.
3. **Solo se conservaron estadísticos resumen, no los valores crudos**, de modo que no hay
   intervalo de confianza *bootstrap* para el contraste: únicamente mediana y rango
   intercuartílico. **Es un incumplimiento del propio protocolo de la campaña, y se declara.**

> La tercera es incómoda de escribir y es la que más crédito da al capítulo. Un protocolo que
> declara dónde se incumplió a sí mismo es más creíble que uno que nunca falla.

---

## 7 · Réplica estricta pareada — material para §3.11.8

| Parámetro del diseño | Valor | Marca |
| :--- | :--- | :---: |
| Casos pareados con latencia | **n = 64** | MEDIDO |
| Turnos para el análisis de fallos | **70** | MEDIDO |
| Pareo | por identificador de caso | MEDIDO |
| Contraste de latencia | **prueba de Wilcoxon de rangos con signo** | MEDIDO |
| Intervalo de confianza | *bootstrap* de **10 000 remuestreos** | MEDIDO |
| Contraste de proporción de fallos | **McNemar exacto** | MEDIDO |

### Las dos desviaciones que hay que declarar

- **D-1:** no es una réplica byte a byte. El protocolo original no registró los mensajes
  renderizados ni el compendio del modelo.
- **D-2:** el encadenado de sesión del original no consta.

### El criterio de aceptación sellado — citarlo literal

> «Si la cuenta cuadra y los identificadores no, el aparato no sirve.»

Es decir: **no basta con que el número de fallos baje; hay que comprobar si son los mismos
fallos.** Este criterio se fijó antes de medir y es el que permitió detectar, en el Capítulo VI,
que dos conjuntos de fallos de tamaño distinto correspondían a fenómenos distintos. Explicar aquí
su razón de ser es lo que hace que el resultado negativo del Capítulo VI se lea como rigor y no
como excusa.

---

## 8 · Tratamiento de proporciones y de los ceros — material para §3.11.9

| Decisión metodológica | Valor | Marca |
| :--- | :--- | :---: |
| Método para toda proporción | **intervalo de confianza de Wilson** al 95 % | MEDIDO |
| Aplicación explícita | incluidas —y sobre todo— las proporciones observadas en cero | MEDIDO |
| Preguntas verificables disponibles | 9 | MEDIDO |
| Cota superior con 0 de 9 | 29,9 % | DERIVADO |
| Observaciones necesarias para acotar al 5 % | del orden de **60** | DERIVADO |
| Observaciones necesarias para acotar al 1 % | alrededor de **300** | DERIVADO |

**El argumento que hay que escribir:** cero casos observados **no** demuestra ausencia. Informar
únicamente el valor puntual induce a concluir que el fenómeno no existe, cuando el diseño solo
excluye tasas superiores a la cota. Por eso el procedimiento se fija aquí, en metodología, y se
aplica sin excepciones en el Capítulo VI.

> Las cifras de 29,9 %, 60 y 300 son admisibles en este capítulo porque ilustran **el
> procedimiento**, no un hallazgo. Si prefieres mantener la separación estricta, puedes escribir
> el procedimiento sin la cota concreta y remitir a §6.8. Ambas opciones son defendibles; elige
> una y sé coherente.

---

## 9 · Análisis de potencia — material para §3.11.10

| Parámetro | Valor | Marca |
| :--- | :--- | :---: |
| Nivel de significación | α = 0,05 bilateral | MEDIDO |
| Potencia objetivo | 80 % | MEDIDO |
| Tasa base supuesta | 10 % | MEDIDO |
| Observaciones por grupo para distinguir 10 % de 5 % | **431** | DERIVADO |
| Tamaños de muestra disponibles | 9 · 15 · 45 · 64 · 70 | MEDIDO |

**La conclusión metodológica, que va aquí y no en el Capítulo VI:** *este diseño distingue un
efecto grande de la ausencia de efecto, y no distingue uno intermedio.* Declararlo en metodología
evita tener que justificarlo caso por caso más adelante, y convierte los resultados no
concluyentes en una limitación conocida del diseño en lugar de en un fallo del análisis.

---

## 10 · Trazabilidad y verificación — material para §3.11.11

| Elemento del procedimiento | Valor | Marca |
| :--- | :--- | :---: |
| Lo que declara cada figura | fichero fuente, compendio SHA-256, tamaño de muestra, marca MEDIDO/DERIVADO | MEDIDO |
| Formatos de exportación por figura | 3, cada uno con compendio propio | MEDIDO |
| Aserciones de recálculo ejecutadas por el cuaderno | **11** | MEDIDO |
| Aserciones que pasan / que fallan | **10 / 1**, y **la que falla queda declarada en el propio informe** | MEDIDO |

**Motivo de la aserción que falla:** la cota de alucinación publicada asumía unas 20 preguntas
verificables cuando el fichero de verdad contiene 9.

**Cerrar la subsección con esta idea:** un análisis que solo publica las aserciones que pasan no
es un análisis verificado.

---

## 11 · Ampliaciones fuera de §3.11

### 11.1 · §3.7.1 — La batería que falta en la Tabla 3.8

Las baterías A–E declaradas cubren ámbito y seguridad, robustez ortográfica, memoria multiturno,
consistencia de fuentes y exactitud de contenido. Falta la que en la práctica se convirtió en el
instrumento de aceptación del proyecto.

**Su aporte metodológico, que vale la pena escribir en el texto:** las baterías A–E miden si la
respuesta es *segura*, *robusta* y *consistente*, pero **una respuesta que solo contiene la frase
de derivación al veterinario pasa todas esas pruebas de forma vacua**. La batería de contenido
introduce un criterio ortogonal.

> **Fila para la Tabla 3.8:**
>
> | Batería F · Contenido sustantivo | 45 turnos en tres modos de uso (general, hemograma e histórico), 15 por modo, sobre el flujo de producción completo. Cada respuesta se evalúa descontando la frase de derivación, las cláusulas de incapacidad y el eco de la pregunta; se considera útil solo si queda contenido verificable. | Detectar respuestas formalmente válidas pero vacías de contenido. |

### 11.2 · §3.5.1 — El congelamiento no cubre el runtime conversacional

La sección describe un procedimiento sólido para el modelo de clasificación. Ese mismo rigor
existe hoy para el *runtime* conversacional y no está documentado.

> **Párrafo para añadir al final de §3.5.1:**
>
> «El mismo principio de congelamiento se extendió al *runtime* conversacional. Cada versión
> desplegable se describe mediante un manifiesto firmado que fija, con su compendio criptográfico,
> la imagen del backend, la del frontend, la del servidor de modelos, el modelo de lenguaje con
> su cuantización, la configuración del proxy, el paquete de arranque de la máquina de inferencia
> y la huella del índice vectorial junto con la revisión del corpus que lo originó. El arranque de
> la máquina de inferencia valida el hardware, el controlador y el compendio del modelo contra ese
> manifiesto y, si alguna comprobación falla, la máquina se apaga en lugar de servir tráfico con
> una configuración distinta de la declarada. El procedimiento de reversión a una versión anterior
> está automatizado y verificado por pruebas.»

### 11.3 · §3.10 — Siete artefactos que faltan en la tabla

| Artefacto | Contenido |
| :--- | :--- |
| Pre-registro de hipótesis sellado | Diez hipótesis con criterio de decisión, con compendio anterior a la medición |
| Registro de procedencia de fuentes | Ruta, compendio SHA-256, tamaño, número de registros y columnas de cada fuente cargada |
| Matriz de trazabilidad | Correspondencia figura → fichero fuente → compendio → tamaño de muestra → marca MEDIDO/DERIVADO |
| Manifiesto de figuras | Compendio de cada figura en sus tres formatos, tabla asociada, procedencia y nota de lectura |
| Índice de tablas del análisis | Las 37 tablas de la campaña con su procedencia |
| Registro de verificación del cuaderno | Once aserciones de recálculo, con la que falla declarada |
| Paneles de ausencia | Nueve figuras que documentan qué **no** se pudo medir y por qué |

---

## 12 · Cifras que NO deben aparecer en este capítulo

No porque sean falsas, sino porque son **resultados** y su sitio es el Capítulo VI:

| Cifra prohibida aquí | Dónde va |
| :--- | :--- |
| −60,6 % de reducción de latencia; 54,4 s → 21,4 s | §6.8 |
| 24,3 % → 8,6 % de turnos sin respuesta; p = 0,035 | §6.8 |
| 0,332 ms/token de sobrecarga de gramática | §6.8 |
| κ = −0,145; 0 de 17 identificadores coincidentes | §6.8 |
| MBU 34,90 %; TPOT 24,4802 ms; decodificación 40,849 tok/s | §6.8 |
| El veredicto de cada una de las diez hipótesis | §6.8 |
| 0 mensajes con más de un compendio en el canario | §6.8 |

**Sí pertenecen a este capítulo:** el número de hipótesis (10), el compendio del pre-registro, los
tamaños de muestra, los criterios de decisión, los parámetros del diseño, las limitaciones
declaradas y el resultado de la **auditoría de comparabilidad** (11 de 15 no constan), porque esa
auditoría es metodología: es lo que decidió cómo se podía medir.
