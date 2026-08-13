# 05 · Capítulo III — Metodología

**Estado: 🔴 un bloqueante.** El capítulo está bien construido para todo lo que se hizo hasta
julio. Le falta la metodología de lo que se hizo en agosto — que es, además, **la parte del
proyecto que mejor cumple lo que el manual EICT pide para el componente de tecnología
emergente**.

Acciones: `A-III-01` … `A-III-04`.

---

## Por qué esto importa más de lo que parece

El manual (p. 10) dedica una sección entera a la «Metodología del componente de tecnología
emergente» y pide cuatro cosas: justificar la selección del clasificador, justificar el banco de
datos, justificar el método de entrenamiento **y presentar de forma exhaustiva las métricas de
calidad contrastándolas con lo que reporta la literatura para problemas similares**.

Para el motor de aprendizaje automático, §3.3–§3.5 y §6.1 cumplen los cuatro puntos. ✅

Para el componente conversacional, el documento cumple los tres primeros y **falla el cuarto**.
Y resulta que el proyecto sí hizo ese contraste con la literatura —lo hizo con rigor, con
hipótesis firmadas antes de medir— pero lo hizo en agosto y no se documentó. Es el caso raro en
que el trabajo existe y solo falta contarlo.

---

## A-III-01 · 🔴 Sección nueva §3.11 — Metodología de recaracterización y pre-registro

**Localización:** después de §3.10 «Artefactos metodológicos generados», antes del Capítulo IV.
Extensión estimada: 3–4 páginas.

### Guion completo

#### 3.11.1 · Motivación y pregunta metodológica

En agosto de 2026 el *runtime* conversacional se migró de una configuración basada en una GPU
NVIDIA L4 a una NVIDIA A100-SXM4-40GB, y el modelo servido pasó de 4 a 27 mil millones de
parámetros. La pregunta no era si el sistema iba más rápido —eso se ve— sino **cuánto de la
mejora es atribuible a qué, y qué parte de la comparación es siquiera legítima**. Esta sección
describe el diseño con el que se respondió.

#### 3.11.2 · Auditoría de comparabilidad previa

Antes de medir nada se auditó qué había registrado el protocolo anterior. Se inventariaron **208
ficheros de evidencia previa**, se calculó su compendio y se verificó su integridad tras la copia
(**208 de 208 intactos**). Sobre ese corpus se reconstruyó el protocolo del 7 de agosto mediante
un cuestionario de **quince preguntas** de reproducibilidad (modelo, compendio, cuantización,
versión del servidor, controlador, GPU exacta, parámetros de muestreo, esquema de salida,
mensajes renderizados, *warm-up*, concurrencia, definición operativa de latencia y de fallo…).

**Resultado: once de las quince preguntas no constan o constan parcialmente.** De ahí se derivó
un **veredicto doble de comparabilidad**, que es la decisión metodológica central del capítulo:

| Ámbito | Veredicto | Consecuencia |
| :--- | :--- | :--- |
| Fallos y comportamiento | COMPARABLE CON RESERVAS | Se puede contrastar el antes y el después, declarando las desviaciones |
| Rendimiento físico | **NO COMPARABLE** | Toda cifra de decodificación, MBU o TPOT es caracterización absoluta de la A100, **nunca** comparación entre GPU |

> «NO CONSTA» se trató como un resultado, no como un vacío que rellenar. Es la postura que
> sostiene la honestidad de todo el capítulo.

#### 3.11.3 · Pre-registro de hipótesis

Se redactaron y sellaron **diez hipótesis** con sus criterios de decisión **antes de tomar
ninguna medida**. El documento se selló con una función resumen criptográfica
(`5d6a0a71081e385e…`) que acredita su anterioridad. Cada hipótesis fija el enunciado, la métrica,
el umbral de decisión y qué observación la refutaría.

Explicar en el texto **por qué** esto importa: sin pre-registro, un resultado de −60,6 % en
latencia se lee como confirmación de cualquier expectativa que uno recuerde haber tenido. Con
pre-registro, el criterio «baja ≥ 50 %» estaba escrito antes y se cumplió; y, simétricamente, la
hipótesis sobre la sobrecarga de gramática estaba escrita antes y quedó **refutada por un factor
de ~44×**. Las dos cosas valen igual.

#### 3.11.4 · Instrumentación y caminos de medición

Dos caminos, con propósitos distintos:

- **Camino A — servidor de modelos directo.** Mide física del *runtime* sin la aplicación en
  medio: TPOT, decodificación, *prefill*, MBU, determinismo, ablación de gramática.
- **Camino B — aplicación completa.** Mide comportamiento del sistema tal como lo ve el usuario:
  desenlace del turno, latencia extremo a extremo, contenido de la respuesta, clase de fallo.

Documentar por qué se separan: el camino B **no expone** los campos de temporización interna del
servidor (`eval_count`, `eval_duration`, `prompt_eval_*`, `load_duration`), lo que hizo **no
evaluable** la hipótesis H-8 por ese camino. Esa limitación es del instrumento, no del sistema, y
así debe presentarse.

#### 3.11.5 · Control de identidad del sistema medido

Todo el capítulo se mide bajo un único sello: modelo, compendio, tamaño en bytes, versión del
servidor, GPU, controlador, CUDA, atención rápida, tipo de caché de claves y valores, paralelismo
y persistencia en memoria. La identidad **no se asume: se verifica respuesta a respuesta**. En
las 115 respuestas registradas, el campo de modelo se comprobó en todas —censo, no muestra— y
ninguna procede de un modelo distinto del sellado.

La comprobación fue necesaria porque el modelo anterior de 4 mil millones de parámetros **sigue
instalado** en el servidor y la guarda del código no impide su uso. Declararlo.

> 📊 **Tabla lista para el documento:** [`tablas/tabla_sello_de_medicion.csv`](tablas/tabla_sello_de_medicion.csv)
> · [versión para pegar](tablas/tabla_sello_de_medicion.md) — propuesta como **Tabla 3.12**.
> El artefacto crudo queda en `fuentes/` y no se imprime.

#### 3.11.6 · Canario de determinismo

Antes de aceptar cualquier medición se verificó que el sistema fuera reproducible dentro de la
misma máquina: **20 mensajes × 5 repeticiones = 100 generaciones** con temperatura 0, `top_k` 1 y
semilla fija. Criterio: ningún mensaje debe producir más de un compendio de respuesta distinto.
**Resultado: 0 mensajes con más de un compendio.** Solo tras pasar este control se dieron por
válidas las series de rendimiento.

#### 3.11.7 · Ablación de la decodificación restringida por gramática

Diseño: **n = 30 por brazo**, con y sin esquema de salida forzado, **intercalados A/B/A/B** para
neutralizar deriva térmica o de estado, con **5 descartes de calentamiento**, pausa de 500 ms
entre generaciones, temperatura 0, semilla fija, tope de 200 tokens de salida y ventana de
contexto fija para no forzar recarga del modelo. Seis mensajes rotados.

Declarar sus tres limitaciones, que la propia campaña declara:
1. Ambos brazos alcanzaron el tope de tokens, así que se compara en régimen de decodificación
   pura: **no se mide el costo de la gramática en la terminación**.
2. La diferencia en número de tokens es cero por construcción, así que el sesgo «la gramática
   genera menos» no pudo evaluarse.
3. **Solo se conservaron estadísticos resumen, no los valores crudos**, de modo que no hay
   intervalo de confianza *bootstrap* — solo mediana y rango intercuartílico. Es un
   incumplimiento del propio protocolo, y se declara.

#### 3.11.8 · Réplica estricta pareada

Para contrastar comportamiento antes/después se reejecutó el protocolo anterior sobre la
configuración nueva, **pareando por identificador de caso** (n = 64 casos con latencia; 70 turnos
para el análisis de fallos). Contraste de latencia con **prueba de Wilcoxon de rangos con signo**
e intervalo *bootstrap* de 10 000 remuestreos. Contraste de proporción de fallos con **McNemar
exacto**.

Dos desviaciones que hay que declarar, porque cambian la interpretación:
- **D-1:** no es una réplica byte a byte — el protocolo original no registró los mensajes
  renderizados ni el compendio del modelo.
- **D-2:** el encadenado de sesión del original no consta.

Y el **criterio de aceptación sellado del proyecto**, que conviene citar literal porque es el que
da rigor al resultado negativo: *«si la cuenta cuadra y los ids no, el aparato no sirve»*. Es
decir: no basta con que el número de fallos baje; hay que comprobar si son **los mismos** fallos.

#### 3.11.9 · Tratamiento de proporciones y de los ceros

Toda proporción se reporta con **intervalo de confianza de Wilson**, incluidas —y sobre todo— las
observadas en cero. Explicar el porqué con el caso concreto: cero alucinaciones sobre nueve
preguntas verificables **no** demuestra ausencia; el diseño solo excluye tasas superiores al
29,9 %. Acotar al 5 % exigiría del orden de 60 observaciones; al 1 %, unas 300.

#### 3.11.10 · Análisis de potencia

Se calculó el tamaño de muestra necesario por grupo frente a la diferencia detectable
(α = 0,05 bilateral, potencia 80 %). Con una tasa base del 10 %, distinguir 10 % de 5 %
exigiría **431 observaciones por grupo**; los tamaños disponibles fueron 9, 15, 45, 64 y 70.
**Este diseño distingue un efecto grande de ninguno, y no distingue uno mediano.** Declararlo
aquí evita tener que justificarlo caso por caso en el Capítulo VI.

#### 3.11.11 · Trazabilidad y verificación de la cadena

Cada figura del análisis declara: fichero fuente, compendio SHA-256 del fuente, tamaño de
muestra, y marca **[MEDIDO]** o **[DERIVADO]**. Cada figura se exporta en tres formatos con
compendio propio. El cuaderno de análisis ejecuta **once aserciones** que recalculan desde los
datos crudos las cifras publicadas; **diez pasan y una falla, y la que falla queda declarada en
el propio informe** (la cota de alucinación publicada asumía ~20 preguntas verificables cuando
el fichero de verdad contiene 9).

Cerrar la sección con esa idea: un análisis que solo publica las aserciones que pasan no es un
análisis verificado.

---

## A-III-02 · §3.7.1 — La batería de contenido no está entre las baterías declaradas

**Localización:** §3.7.1 «Baterías de validación del asistente LLM/RAG», Tabla 3.8.

Las baterías A–E cubren ámbito/seguridad, robustez ortográfica, memoria multiturno, consistencia
de fuentes y exactitud de contenido. Falta la que en la práctica se convirtió en el instrumento
de aceptación del proyecto: **la batería de 45 turnos que mide si la respuesta contiene algo
después de quitar el andamiaje**.

Su aporte metodológico es preciso y vale la pena escribirlo: las baterías A–E miden si la
respuesta es *segura*, *robusta* y *consistente*, pero **una respuesta que solo contiene la frase
de derivación al veterinario pasa todas esas pruebas de forma vacua**. La batería de contenido
introduce un criterio ortogonal: descontar las cláusulas de incapacidad («no puedo confirmar») y
el eco de la pregunta («me preguntas si…»), y verificar que queda contenido sustantivo.

> **Fila propuesta para la Tabla 3.8:**
>
> | Batería F · Contenido sustantivo | 45 turnos en tres modos de uso (general, hemograma e histórico), 15 por modo, sobre el flujo de producción completo. Cada respuesta se evalúa descontando la frase de derivación, las cláusulas de incapacidad y el eco de la pregunta; se considera útil solo si queda contenido verificable. | Detectar respuestas formalmente válidas pero vacías de contenido. |

Evidencia: `validacion_llm/resultados/rondas45_2026-08-10/` (siete baterías más sondas, con
pregunta, respuesta, etapas, razón de reparación y latencia por turno).

---

## A-III-03 · §3.5.1 — El congelamiento de artefactos no cubre el runtime conversacional

**Localización:** §3.5.1 «Freeze de umbrales y trazabilidad de artefactos».

La sección describe un procedimiento sólido para el modelo de clasificación: umbrales
congelados sobre validación, manifiesto de artefactos, compendios, política de etiquetas sellada.
Ese mismo rigor **existe hoy para el runtime conversacional** y no está documentado.

> **Párrafo propuesto para añadir al final de §3.5.1:**
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

Evidencia: `deploy/releases/release-manifest-*.json`, `deploy/releases/gpu-runtime-*.json`,
`deploy/releases/artifact-set-*.json`, `deploy/releases/rag-summary-*.json`,
`deploy/gpu/validate-host.sh`, `deploy/gpu/rollback-release.sh`,
`backend/tests/test_release_rollback.py`, `backend/tests/test_release_manifest_contract.py`.

---

## A-III-04 · §3.10 — Artefactos metodológicos generados

Añadir a la tabla las salidas de la campaña:

| Artefacto | Contenido |
| :--- | :--- |
| Pre-registro de hipótesis sellado | Diez hipótesis con criterio de decisión, con compendio anterior a la medición |
| `PROCEDENCIA.json` | Ruta, compendio SHA-256, tamaño, número de registros y columnas de cada fuente cargada |
| `TRAZABILIDAD.csv` | Correspondencia figura → fichero fuente → compendio → tamaño de muestra → marca MEDIDO/DERIVADO |
| `MANIFIESTO.json` de figuras | Compendio de cada figura en sus tres formatos, tabla asociada, procedencia y nota de lectura |
| `INDICE_TABLAS.csv` | Las 37 tablas del análisis con su procedencia |
| Registro de verificación del cuaderno | Once aserciones de recálculo, con la que falla declarada |
| Paneles de ausencia | Nueve figuras que documentan qué **no** se pudo medir y por qué |

---

## Lo que NO hay que tocar del Capítulo III

- §3.1 Tipo de proyecto y enfoque metodológico. ✅
- §3.2 y §3.2.1 Metodología de desarrollo, control de versiones, pruebas y despliegue. ✅
- §3.3, §3.3.1, §3.3.2 Corpus, limpieza, imputación e ingeniería de características. ✅
- §3.4 Etiquetado multietiqueta. ✅
- §3.5 Entrenamiento, calibración y congelamiento (solo se **añade** el párrafo de A-III-03). ✅
- §3.6 Validación externa y clínica. ✅
- §3.7.2 Evaluación adversarial y §3.7.3 Métricas de concordancia. ✅
- §3.8 Usabilidad y §3.9 Consideraciones éticas. ✅

## Checklist de cierre de este bloque

- [ ] §3.11 redactada con sus once subsecciones (3–4 páginas).
- [ ] Batería F añadida a la Tabla 3.8.
- [ ] Párrafo de congelamiento del *runtime* añadido a §3.5.1.
- [ ] Tabla de §3.10 ampliada con los siete artefactos de la campaña.
- [ ] Verificado que ninguna cifra de §3.11 se adelanta a §6.9: **la metodología describe cómo se
      midió, no qué salió.** El manual separa ambas cosas y el comité lo mira.
