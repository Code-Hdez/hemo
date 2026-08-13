# Las dos secciones nuevas — YA REDACTADAS, para integrar

> A diferencia de otros capítulos, aquí **no tienes que redactar las secciones nuevas: ya están
> escritas y verificadas**. Tu trabajo con ellas es de integración, no de creación.
>
> **Qué puedes cambiar:** las referencias cruzadas, para que encajen con el capítulo final; y
> nada más.
>
> **Qué NO puedes cambiar:** las cifras, los intervalos de confianza, las declaraciones de
> limitación, el orden de los argumentos y el registro. En particular, **no suavices ninguna
> declaración de lo que el diseño no sostiene**: son lo que da crédito al resto del capítulo. Si
> una frase te parece excesivamente cauta, es que está haciendo su trabajo.
>
> Los marcadores de figura vienen en la forma `*[Figura 6.NN — nombre: descripción…]*`.
> Reprodúcelos tal cual, en su sitio: quien monte el documento en Word los sustituirá por la
> figura y su pie.

---

# §6.6 · Resultados de la vigilancia poblacional

> **Redacción lista para pegar en el Capítulo VI, entre §6.5 y §6.7.**
> Cifras verificadas contra `outputs/population_surveillance_report_v3.json`
> (generado el 12/04/2026) y `outputs/gate_geocoding_quality_v1.json`.
> Extensión: ~1,5 páginas. Sustituye el hueco que hoy deja la numeración al saltar de 6.5 a 6.7.

---

## 6.6. Resultados de la vigilancia poblacional

El módulo de vigilancia poblacional, cuya construcción se describió en §5.6, se evaluó sobre una
cohorte de 200 registros correspondientes a una ventana de 30 días. La finalidad del análisis no
es estimar prevalencia ni incidencia en la población canina, sino verificar que el módulo agrega
correctamente las señales disponibles, que preserva la privacidad y que declara con honestidad
los límites de lo que puede sostener. Ese es, precisamente, el resultado más relevante de esta
sección: **el módulo funciona y, al hacerlo, demuestra que los datos disponibles no permiten aún
una lectura territorial.**

### 6.6.1. Compuertas técnicas

Las cinco compuertas técnicas aplicadas al módulo se aprobaron en su totalidad, lo que confirma
que la agregación opera sobre artefactos íntegros y sobre la misma política de etiquetas
congelada que emplea el motor de clasificación.

| Compuerta | Resultado | Qué verifica |
| :--- | :---: | :--- |
| Paridad de características | aprobada | Las características empleadas en la agregación coinciden con las del modelo congelado |
| Auditoría de fuga | aprobada | No se detecta filtración de información entre particiones |
| Integridad del manifiesto | aprobada | Todos los artefactos requeridos están presentes y con el compendio esperado |
| Congelamiento de política | aprobada | La política de etiquetas no se alteró respecto de la versión sellada |
| Deriva básica | aprobada | La distribución de la cohorte no se aparta de la línea base más allá del umbral |

*Tabla 6.14. Compuertas técnicas del módulo de vigilancia poblacional.*

### 6.6.2. Señales temporales

El reporte evalúa cinco señales sobre la cohorte y emite un estado agregado. El resultado global
fue de **advertencia**, con tres señales aprobadas, dos en advertencia y ninguna en fallo.

| Señal | Valor | Línea base | Estado |
| :--- | ---: | ---: | :---: |
| Tasa de registros sin predicción | 0,0 % | 0,0 % | aprobada |
| Tasa de imputación parcial | 0,0 % | 0,0 % | aprobada |
| Tasa de activación de control de calidad | 35,0 % | 36,6 % | aprobada |
| Tasa de geocodificación | **0,0 %** | — | **advertencia** |
| Concentración en la ubicación principal | **100,0 %** | — | **advertencia** |

*Tabla 6.15. Señales del reporte de vigilancia poblacional sobre una cohorte de 200 registros en
una ventana de 30 días.*

Las tres primeras señales describen un módulo sano. Que la tasa de registros sin predicción y la
de imputación parcial sean nulas indica que la cadena de extracción, construcción de
características e inferencia operó sin degradación sobre la totalidad de la cohorte. Que la tasa
de activación de control de calidad —35,0 %— se mantenga próxima a su línea base de 36,6 % indica
que la cohorte agregada no presenta una desviación apreciable respecto del comportamiento
esperado del sistema, lo que es coherente con el hecho de que las compuertas de deriva y de
congelamiento de política se hayan aprobado.

### 6.6.3. El límite geográfico

Las dos señales en advertencia describen el mismo hecho desde dos ángulos: **la totalidad de los
200 registros de la cohorte se agrupa bajo una única ubicación, catalogada como desconocida, y
ninguno de ellos está geocodificado.** La concentración del 100 % en la ubicación principal no
refleja un patrón epidemiológico de agrupamiento, sino la ausencia de captura de ubicación en el
flujo de ingreso.

La consecuencia es inequívoca y debe enunciarse sin matices: **el módulo de vigilancia es
funcional en su agregación temporal y de señales, pero no sostiene ninguna lectura territorial.**
El mapa que la interfaz presenta muestra, en la práctica, un único agregado indiferenciado. Toda
interpretación de concentración geográfica sobre estos datos sería un artefacto de la ausencia de
geocodificación y no una observación sobre la población canina.

Este resultado no invalida el diseño del módulo. Al contrario: las dos advertencias son
exactamente las que el módulo fue construido para emitir, y su acción asociada —mejorar la
captura de ubicación y ampliar la cobertura territorial— es la que corresponde. Un módulo de
vigilancia que hubiera presentado un mapa aparentemente informativo a partir de doscientos
registros sin geocodificar habría sido un fallo de diseño, no un éxito.

### 6.6.4. Alcance interpretativo

Los resultados de esta sección deben leerse bajo tres restricciones, que la interfaz reproduce
como advertencias permanentes ante el usuario:

1. **No es prevalencia.** Las frecuencias observadas describen los hemogramas que fueron cargados
   en la plataforma, no la población canina. La muestra es autoseleccionada por quien decide subir
   un estudio.
2. **No es diagnóstico confirmado.** Las señales agregan salidas indicativas del modelo, que no
   constituyen confirmación clínica de ninguna condición.
3. **No es una señal territorial.** Con una tasa de geocodificación del 0 %, cualquier
   representación espacial carece de sustento.

Bajo esas tres restricciones, el módulo cumple el objetivo específico que lo motivó: agrega
señales con resguardo de privacidad, no expone ningún dato individual en la vista poblacional, y
acompaña la visualización de las advertencias metodológicas que impiden su sobreinterpretación.
La ampliación de la cobertura territorial y la mejora de la geocodificación se recogen entre las
recomendaciones del Capítulo VII.

---

## Notas para quien inserte esta sección

- **Numeración.** Las tablas van como **6.14** y **6.15**; en consecuencia, la tabla de usabilidad
  que hoy figura como 6.14 en el cuerpo pasa a **6.16**. Ver
  `../../01_preliminares/README.md` para la renumeración completa de la serie.
- **Figura opcional.** El reporte no tiene figura asociada. Si se quiere una, la de mayor valor
  es un gráfico de barras con las cinco señales y su umbral, marcando en trama las dos que están
  en advertencia. **No hacer un mapa**: sería exactamente el objeto que la sección declara
  insostenible.
- **Fecha del reporte.** El reporte se generó el 12 de abril de 2026 sobre datos de una ventana de
  30 días. Si se regenera antes de la entrega con la cohorte actual, **actualizar las cinco cifras
  y la fecha**; el texto está escrito para que solo cambien los números de las dos tablas.
- **Coherencia con §5.6.** El Capítulo V ya reporta correctamente la cohorte de 200 registros, el
  estado de advertencia y el reparto 3/2/0. Esta sección no lo repite: lo analiza.
- **Efecto sobre el Capítulo VII.** Con esta sección insertada, la fila de OE4 en la Tabla 7.1
  («Cumplido como exploratorio») pasa a tener evidencia citable. Actualizar su columna de
  evidencia a: «Módulo de vigilancia con cinco compuertas técnicas aprobadas, reporte poblacional
  sobre cohorte de 200 registros con tres señales aprobadas y dos en advertencia, y limitación
  geográfica declarada (§6.6)».

## Material generado

Las dos tablas de esta sección están además en formato importable, junto con una tercera de
comprobaciones de geocodificación que puede ir al anexo:

- [`tablas/tabla_6.14_compuertas_vigilancia.csv`](../6.6_vigilancia_poblacional/tablas/tabla_6.14_compuertas_vigilancia.csv) · [pegar](../6.6_vigilancia_poblacional/tablas/tabla_6.14_compuertas_vigilancia.md)
- [`tablas/tabla_6.15_senales_vigilancia.csv`](../6.6_vigilancia_poblacional/tablas/tabla_6.15_senales_vigilancia.csv) · [pegar](../6.6_vigilancia_poblacional/tablas/tabla_6.15_senales_vigilancia.md)
- [`tablas/tabla_calidad_geocodificacion.csv`](../6.6_vigilancia_poblacional/tablas/tabla_calidad_geocodificacion.csv) · [pegar](../6.6_vigilancia_poblacional/tablas/tabla_calidad_geocodificacion.md)

Los artefactos crudos que las respaldan están en `fuentes/` y **no se imprimen**.

## Procedencia

| Cifra | Artefacto |
| :--- | :--- |
| Cohorte de 200 registros, ventana de 30 días | `outputs/population_surveillance_report_v3.json` → `cohort_size`, `period_days` |
| Estado global «advertencia», 3 aprobadas / 2 advertencia / 0 fallo | ídem → `status`, `status_counts` |
| Las cinco señales temporales y sus valores | ídem → `temporal_signals` |
| Ubicación única «Desconocida», 200 registros, 100 % | ídem → `geographic_hotspots` |
| Las cinco compuertas técnicas | ídem → `gate_status` |
| Calidad de geocodificación | `outputs/gate_geocoding_quality_v1.json` |

---

# §6.8 · Recaracterización del runtime conversacional sobre A100

> **Redacción lista para pegar en el Capítulo VI, después de §6.7 y ANTES de la síntesis.**
> Todas las cifras están verificadas contra `06_analisis/` y recogidas en
> `../../99_trazabilidad/CIFRAS_OFICIALES.md`.
> Extensión estimada: 5–6 páginas con sus figuras.
> Numeración propuesta: tablas **6.17 a 6.21**, figuras **6.30 a 6.41**.

---

## 6.8. Recaracterización del runtime conversacional

En agosto de 2026, con posterioridad a las validaciones descritas en las secciones anteriores, el
*runtime* conversacional del sistema fue migrado a una configuración con aceleración por unidad de
procesamiento gráfico, y el modelo de lenguaje servido pasó de una variante de cuatro mil
millones de parámetros a una de veintisiete mil millones. Esta sección presenta la
caracterización de la configuración resultante.

El análisis se organiza en torno a una distinción que condiciona todo lo que sigue y que conviene
enunciar de entrada: **no todo lo observado es comparable con la configuración anterior**. El
protocolo con el que se midió el sistema previo no registró los parámetros necesarios para
reproducirlo, de modo que las cifras de rendimiento físico presentadas aquí constituyen una
caracterización absoluta de la configuración vigente y no una comparación entre unidades de
procesamiento gráfico. En cambio, el comportamiento del sistema ante un mismo conjunto de casos
sí admite contraste, con las reservas que se declaran.

### 6.8.1. Auditoría de comparabilidad

Antes de medir se auditó la evidencia disponible de la configuración anterior: 208 ficheros, cuyo
compendio criptográfico se verificó íntegro en su totalidad tras la copia. Sobre ese corpus se
reconstruyó el protocolo previo mediante un cuestionario de quince preguntas de reproducibilidad.

**Once de las quince preguntas no constan o constan solo parcialmente.** No consta el modelo
empleado, ni su compendio, ni su cuantización; no consta la versión del servidor de modelos, ni
el controlador, ni el modelo exacto de unidad de procesamiento gráfico; no constan el esquema de
salida forzado, los mensajes renderizados, el procedimiento de calentamiento, la concurrencia
configurada ni el tratamiento de los arranques en frío. Sí consta la métrica de latencia
empleada, y sí constan los identificadores de los casos que fallaron, dato que resultó decisivo.

De esta auditoría se deriva un veredicto de comparabilidad diferenciado por ámbito:

| Ámbito | Veredicto |
| :--- | :--- |
| Fallos y comportamiento del sistema | Comparable con reservas |
| Rendimiento físico del *runtime* | **No comparable** |

*Tabla 6.17. Veredicto de comparabilidad entre la configuración anterior y la vigente.*

*[Figura 6.30 — `fig_A2_corpus_evidencia`: composición del corpus de evidencia previa auditado,
n = 208.]*

*[Figura 6.31 — `fig_A4_semaforo_protocolo`: reconstrucción del protocolo anterior, estado de
recuperación de cada una de las quince preguntas, n = 15.]*

La ausencia de registro no se trató como un vacío por rellenar sino como un resultado en sí
mismo. La consecuencia práctica para la lectura de esta sección es que **toda cifra de
decodificación, utilización de ancho de banda o tiempo por token corresponde exclusivamente a la
configuración vigente**, y que la mejora de latencia documentada en §6.8.4 es atribuible al
conjunto de la migración —hardware, modelo y cambios de software acumulados— y no aisladamente a
la unidad de procesamiento gráfico.

### 6.8.2. Identidad del sistema medido

Toda la sección se mide bajo un único sello, verificado y no supuesto.

| Campo | Valor |
| :--- | :--- |
| Modelo | Qwen3.6, 27 mil millones de parámetros, cuantización Q4_K_M |
| Compendio del modelo | `a50eda8ed977ab48…` |
| Tamaño | 17 420 432 739 bytes (16,224 GiB / 17,420 GB) |
| Servidor de modelos | Ollama 0.32.6 |
| Unidad de procesamiento gráfico | NVIDIA A100-SXM4-40GB |
| Controlador / CUDA | 580.159.03 / 13.0 |
| Ventana de contexto por petición | 16 384 tokens |
| Atención rápida / tipo de caché de claves y valores | activada / `q8_0` |
| Paralelismo / persistencia en memoria | 1 / residente |

*Tabla 6.18. Identidad sellada del runtime conversacional medido.*

La medición impuso dos correcciones sobre lo que el equipo tenía documentado: el peso real del
modelo es de 17 420 432 739 bytes y no los 16,93 GB que se habían declarado, y la versión del
servidor de modelos es 0.32.6 y no 0.32.5.

La identidad del modelo no se asumió: se verificó en cada respuesta emitida. Sobre las 115
respuestas registradas en la campaña se comprobó el campo de modelo en la totalidad de ellas
—censo, no muestra— y ninguna procede de un modelo distinto del sellado. Esta verificación fue
necesaria porque el modelo anterior, de cuatro mil millones de parámetros, permanece instalado en
el servidor y la comprobación presente en el código no impide su uso.

*[Figura 6.32 — `fig_B3_identidad_por_respuesta`: origen del modelo en cada respuesta registrada,
n = 115.]*

Antes de aceptar cualquier medición de rendimiento se verificó el determinismo de la generación
dentro de la misma máquina: veinte mensajes repetidos cinco veces cada uno, con temperatura cero,
selección del token más probable y semilla fija, produjeron **cien generaciones sin que ningún
mensaje diera lugar a más de un compendio de respuesta distinto**.

### 6.8.3. Caracterización física del runtime

La decodificación de un modelo de lenguaje en régimen autorregresivo está gobernada por el ancho
de banda de memoria: cada token de salida exige recorrer la totalidad de los pesos del modelo. El
techo de decodificación se aproxima, en consecuencia, por el cociente entre el ancho de banda
nominal de la memoria y el tamaño del modelo.

| Métrica | Valor | Intervalo de confianza 95 % |
| :--- | ---: | :--- |
| Tiempo por token de salida (mediana) | 24,4802 ms | 24,4701 – 24,5193 |
| Coeficiente de variación del tiempo por token | 0,65 % | — |
| Decodificación (mediana) | 40,849 tok/s | 40,784 – 40,866 |
| Techo teórico de decodificación | 117,0 tok/s | — |
| Banda alcanzable documentada (77 % – 86 %) | 90,1 – 100,7 tok/s | — |
| Utilización del ancho de banda de memoria | 34,90 % | 34,84 – 34,91 |
| Ancho de banda efectivo | 711,6 GB/s (nominal 2 039 GB/s) | — |
| Procesamiento del mensaje de entrada (mediana) | 91,9 tok/s | — |

*Tabla 6.19. Caracterización física del runtime conversacional sobre la configuración vigente,
n = 100 generaciones.*

*[Figura 6.33 — `fig_C1_techos_decode`: rendimiento medido frente al techo nominal y a la banda
alcanzable, n = 100.]*

*[Figura 6.34 — `fig_C2_tpot_distribucion`: distribución del tiempo por token de salida, con los
cien puntos individuales y la banda del intervalo de confianza, n = 100.]*

Tres precisiones de lectura son necesarias para que estas cifras no se sobreinterpreten. Primera:
el tamaño del modelo se toma en unidades decimales —17,42 GB— y no binarias —16,22 GiB—;
confundirlas infla el techo teórico en un 7,4 %. Segunda: una utilización del ancho de banda del
34,90 % **no indica ineficiencia del despliegue**, ya que esta métrica disminuye al aumentar el
ancho de banda disponible porque la sobrecarga fija por token no escala con él. Tercera: el
coeficiente de variación del 0,65 % describe cien generaciones consecutivas con el modelo ya
residente en memoria, temperatura cero, semilla fija y sin concurrencia; **mide la máquina en su
mejor caso y no la estabilidad que percibe el usuario del servicio**.

Se realizó además una ablación de la decodificación restringida por gramática, con treinta
generaciones por brazo intercaladas y con descartes de calentamiento, para contrastar el
sobrecosto que la literatura atribuye a esta técnica.

| Brazo | Tiempo por token (mediana) | Rango intercuartílico | n |
| :--- | ---: | :--- | ---: |
| Sin esquema de salida forzado | 24,607 ms | 24,361 – 24,890 | 30 |
| Con esquema de salida forzado | 24,939 ms | 24,752 – 25,004 | 30 |
| **Diferencia** | **+0,332 ms/token** | — | 60 |

*Tabla 6.20. Ablación de la decodificación restringida por gramática.*

*[Figura 6.35 — `fig_C6_gramatica_predicho_medido`: lo predicho frente a lo medido, las tres
referencias sobre un eje común de milisegundos por token, n = 60.]*

El sobrecosto medido es de 0,332 milisegundos por token, esto es, un 1,33 % del tiempo total por
token. **El valor de referencia consultado en la literatura, de aproximadamente 14,6 milisegundos
por token, resulta unas cuarenta y cuatro veces superior al observado y no se reproduce en este
despliegue.** El resultado no cuestiona la validez de la fuente: establece que su magnitud no es
trasladable a esta configuración. Su consecuencia práctica es que el residual de rendimiento que
se había atribuido a la gramática en la configuración anterior tenía otro origen, que este diseño
no identifica.

Este resultado debe leerse con tres limitaciones declaradas: ambos brazos alcanzaron el tope de
tokens de salida, de modo que se compara en régimen de decodificación pura y no se mide el
sobrecosto de la gramática en la terminación de la respuesta; la diferencia en número de tokens
generados es nula por construcción, por lo que no pudo evaluarse si la gramática induce respuestas
más breves; y solo se conservaron estadísticos de resumen y no los valores individuales, de modo
que se reporta mediana y rango intercuartílico pero no intervalo de confianza.

### 6.8.4. Comportamiento del sistema: réplica estricta

Para contrastar el comportamiento del sistema completo se reejecutó el protocolo de la
configuración anterior, pareando cada observación por identificador de caso.

| Estadístico | Valor |
| :--- | ---: |
| Casos pareados con latencia | 64 |
| Mediana de la configuración anterior | 54,4 s |
| Mediana de la configuración vigente | 21,4 s |
| Mediana de las diferencias pareadas | 31,95 s |
| Intervalo de confianza 95 % (*bootstrap*, 10 000 remuestreos) | 19,06 – 46,28 s |
| **Reducción de la mediana** | **−60,6 %** |

*Tabla 6.21. Réplica estricta pareada del protocolo anterior sobre la configuración vigente.*

*[Figura 6.36 — `fig_E1_slopegraph_pareado`: latencia por caso entre ambas configuraciones, una
línea por caso, medianas destacadas, n = 64.]*

*[Figura 6.37 — `fig_E2_diferencias_pareadas`: distribución de las diferencias pareadas con la
línea de cero marcada, n = 64.]*

El contraste de Wilcoxon de rangos con signo, pareado por identificador de caso, arroja un
intervalo de confianza que no cruza el cero. El criterio pre-registrado exigía una reducción de al
menos el 50 % y se cumple.

Debe declararse, no obstante, que las dos series no comparten protocolo. La réplica no es
idéntica byte a byte, dado que el protocolo original no registró los mensajes renderizados ni el
compendio del modelo, y el encadenado de sesión del original no consta. La mediana de la
configuración anterior recalculada desde los datos crudos es de 58,59 segundos, frente a los 59,1
segundos publicados en los informes internos previos; se emplea el valor recalculado.

En cuanto a la proporción de turnos sin respuesta:

| Corrida | Turnos sin respuesta | Proporción | Intervalo de confianza 95 % (Wilson) |
| :--- | ---: | ---: | :--- |
| Configuración anterior | 17 / 70 | 24,29 % | 15,75 – 35,50 % |
| Configuración vigente | 6 / 70 | 8,57 % | 3,99 – 17,47 % |

*Tabla 6.22. Proporción de turnos sin respuesta por corrida. Contraste de McNemar exacto sobre 23
observaciones discordantes: p = 0,035.*

*[Figura 6.38 — `fig_E5_clases_fallo`: naturaleza de los fallos, presentados en dos gráficos
separados, n = 23.]*

**Este resultado no debe leerse como que la migración corrigió los fallos anteriores.** El
análisis de identificadores lo desmiente: de los diecisiete casos que fallaron en la configuración
anterior, **ninguno** vuelve a fallar en la réplica, y el coeficiente de acuerdo entre ambos
conjuntos es de κ = −0,145, esto es, peor que el azar. Se trata de dos fenómenos distintos: los
diecisiete fallos anteriores fueron fallos de contrato en la reparación de la respuesta generada,
mientras que los seis actuales son fallos de transporte —cuatro respuestas con código HTTP 502 y
dos con código 422—.

El criterio de aceptación fijado por el proyecto para este análisis establece que si el recuento
de fallos coincide pero los identificadores no, el instrumento no es válido para sostener la
comparación. En este caso ni siquiera coincide el recuento. Por consiguiente, la reducción
observada se reporta como un cambio de régimen de fallo, no como la corrección de un conjunto
identificado de errores.

Sobre la batería de cuarenta y cinco turnos ejecutada en tres modos de uso, la configuración
vigente registró cuarenta y tres turnos útiles, ningún turno en el que el sistema se abstuviera de
responder y dos turnos sin respuesta, ambos correspondientes a cargas en frío del modelo. Las
medianas de latencia por modo fueron de 15,3 s en el modo general, 17,9 s en el modo hemograma y
24,2 s en el modo histórico. Con quince observaciones por modo, **estas proporciones no sostienen
comparación entre modos**: los intervalos se solapan ampliamente, y solo se reportan mediana y
rango, sin percentiles altos.

### 6.8.5. Exactitud numérica y su incertidumbre

Sobre el conjunto de preguntas cuya respuesta admite verificación mecánica contra una tabla de
verdad sellada, no se observó ninguna discrepancia numérica atribuible a fabricación de datos por
parte del modelo.

*[Figura 6.39 — `fig_D7_alucinacion_wilson`: tasa de alucinación numérica y su intervalo de
confianza, punto observado en cero con la banda de Wilson al 95 %, n = 9.]*

**Cero casos observados no demuestra ausencia.** Con nueve preguntas verificables, el diseño solo
permite excluir tasas superiores al 29,9 % con un 95 % de confianza. Acotar la tasa por debajo del
5 % exigiría del orden de sesenta observaciones, y por debajo del 1 %, alrededor de trescientas.
Esta figura se incluye precisamente para impedir que un cero se interprete como una garantía de
ausencia de fabricación.

Debe consignarse una corrección respecto de los informes internos de la campaña: se publicó una
cota del 16,8 % asumiendo aproximadamente veinte preguntas verificables, cuando el fichero de
verdad sellado contiene nueve. **La cota correcta es del 29,9 %; la cifra publicada subestimaba la
incertidumbre.**

### 6.8.6. Tablero de hipótesis pre-registradas

Las diez hipótesis de la campaña se registraron y sellaron criptográficamente antes de tomar
ninguna medida, con el compendio `5d6a0a71081e385e…`.

| # | Enunciado (abreviado) | Medido | Veredicto |
| :--- | :--- | :--- | :--- |
| H-1 | Decodificación más rápida con menor utilización de ancho de banda | 34,90 % | Consistente, no confirmada |
| H-2 | El sobrecosto de gramática es ≥ 10 ms/token | 0,332 ms/token | **Refutada** |
| H-3 | La tasa de fallos terminales no cambia apreciablemente | κ = −0,145: poblaciones distintas | No evaluada ▲ |
| H-4 | Los identificadores de fallo se conservan aunque cambie el recuento | 0 de 17 coinciden | No evaluada, evaluable ▲ |
| H-5 | La mediana por turno baja al menos un 50 % | −60,6 % (Wilcoxon, n = 64) | No evaluada ▲ |
| H-6 | En preguntas de frontera el sistema fabula en vez de declinar | reporta ventana truncada | **Refutada en su predicción** |
| H-7 | La ventana de contexto efectiva cambió por el salto de memoria | fijada por petición | Refutada por configuración |
| H-8 | El costo de procesamiento del mensaje crece a lo largo de los turnos | campo no expuesto por la interfaz | No evaluable por este camino |
| H-9 | La tasa de fabricación numérica es distinta de cero | 0 de 9; Wilson hasta 29,9 % | No concluyente |
| H-10 | El cambio de máquina altera el rendimiento por sí solo | una sola máquina disponible | No evaluable por diseño |

*Tabla 6.23. Tablero de las diez hipótesis pre-registradas.*

*[Figura 6.40 — `fig_F1_tablero_hipotesis`: enunciado leído del pre-registro firmado, veredicto
leído del informe y cifra recalculada desde los datos, n = 10.]*

Las tres filas marcadas con ▲ presentan una discrepancia que se reporta tal cual y no se corrige:
su veredicto sellado indica «no evaluada» mientras que la medición correspondiente ya existe. La
tabla de veredictos del informe de la campaña se redactó antes de ejecutar el brazo de réplica
estricta y no se actualizó posteriormente. Se presenta el veredicto sellado sin sustituirlo por el
recalculado, y se señala la discrepancia, porque alterar retroactivamente un veredicto
pre-registrado anularía el propósito del pre-registro.

Conviene asimismo precisar que «no evaluable» no equivale a «no hay efecto»: significa que este
diseño no puede observarlo.

### 6.8.7. Potencia del diseño

*[Figura 6.41 — `fig_F4_potencia`: tamaño de muestra necesario por grupo frente a la diferencia
detectable, con α = 0,05 bilateral y potencia del 80 %.]*

Los tamaños de muestra disponibles fueron de nueve preguntas verificables, quince turnos por modo,
cuarenta y cinco turnos por batería, sesenta y cuatro casos pareados y setenta turnos de réplica.
Distinguir una tasa del 10 % de una del 5 % con una potencia del 80 % requeriría **cuatrocientas
treinta y una observaciones por grupo**.

Ninguno de los tamaños disponibles se aproxima a esa cifra. **Este diseño distingue un efecto
grande de la ausencia de efecto, y no distingue un efecto de magnitud intermedia.** Esta es la
razón cuantitativa por la que las hipótesis relativas a la tasa de fallos y a la tasa de
fabricación numérica no se sostienen, y por la que la relativa a la reducción de latencia sí se
sostiene: su efecto es de una magnitud que el diseño sí puede resolver.

### 6.8.8. Trazabilidad y verificación del análisis

Cada figura de esta sección declara su fichero fuente, el compendio criptográfico de ese fichero,
el tamaño de muestra y su condición de magnitud medida o derivada. El cuaderno de análisis ejecuta
once aserciones que recalculan desde los datos crudos las cifras publicadas; **diez de ellas
coinciden dentro de la tolerancia fijada y una falla**, correspondiente al número de preguntas
verificables, y esa falla se declara en el propio análisis y motiva la corrección consignada en
§6.8.5.

La campaña generó, además de las figuras presentadas, nueve paneles que documentan explícitamente
qué no pudo medirse y por qué. Su inclusión responde al mismo criterio que gobierna toda la
sección: lo que no consta se declara, no se omite.

---

---

## Anexo · Notas de inserción (NO forman parte del capítulo)

Esto es para la persona que pegue el resultado en Word. **No lo reproduzcas en tu salida.**

## Notas para quien inserte esta sección

### Dónde va exactamente

Después de §6.7 (usabilidad) y **antes** de la síntesis. Renumerar la actual §6.8 «Síntesis de
resultados» a **§6.9**, y reescribir su párrafo de rendimiento según `../README.md` (acción
A-VI-07).

### Numeración de tablas y figuras

Esta sección aporta **7 tablas (6.17 a 6.23)** y **12 figuras (6.30 a 6.41)**. Si se acepta también
§6.6 (que ocupa 6.14 y 6.15) y la de usabilidad se corre a 6.16, la serie queda cerrada sin
huecos. Ver `../../01_preliminares/README.md`.

### Formato de las figuras

Insertar los **PDF o SVG**, no los PNG: el empastado es impreso y los PNG pixelan. Los tres
formatos, con su compendio, están en `figuras/`. Antes de mandar a imprenta, revisar cada figura
en su versión en escala de grises (`figuras/grises/`): la campaña ya verificó que ninguna depende
solo del color, pero conviene comprobarlo con los ojos.

### Pies de figura

Los pies completos, con su nota de lectura, están en [`PIES_DE_FIGURA.md`](../6.9_recaracterizacion_a100/PIES_DE_FIGURA.md). **Las
notas de lectura no son opcionales**: son las que impiden que un revisor interprete la Figura del
acuerdo de fallos como «la GPU arregló los errores» o el cero de alucinación como «no fabrica
datos». Si no caben bajo la figura, van como nota al pie de página.

### Sobre las referencias

§6.8.3 cita un valor de la literatura para refutarlo. **Esa cita tiene que existir en el marco
teórico (§1.1.3.7) y en la bibliografía**, con la referencia exacta. Refutar una fuente sin
citarla es la única forma de que este resultado —que es el más interesante del capítulo— se
convierta en un problema. Ver `../../03_capitulo_i_marco_teorico/README.md`.

### Sobre el tono

El texto está escrito deliberadamente en registro técnico neutro, sin adjetivos de mérito, y
declarando cada limitación junto al resultado que limita. Es el registro que el manual pide para
el capítulo de resultados y es, además, el que hace defendible una sección que reporta un −60,6 %
sin reclamar más de lo que el diseño sostiene. **No suavizar las declaraciones de limitación al
integrarlo**: son lo que da crédito al resto.

## Procedencia de cada cifra

| §  | Cifra | Artefacto |
| :--- | :--- | :--- |
| 6.8.1 | 208 ficheros auditados, 208 íntegros | `01_auditoria_previa/inventario.ndjson` → `tab_A2` |
| 6.8.1 | 11 de 15 preguntas sin constancia | `protocolo_antiguo_reconstruido.md` → `tab_A4` |
| 6.8.1 | Veredicto doble | `veredicto_comparabilidad.md` → `tab_A5` |
| 6.8.2 | Sello del sistema | `06_analisis/fase2_canario_y_ic.json` → `tab_B1` |
| 6.8.2 | 115/115 respuestas del modelo sellado | `04_trazas/turns*.ndjson` → `tab_B3` |
| 6.8.2 | Canario 20×5, 0 divergencias | `fase2_canario_y_ic.json` → `tab_C7` |
| 6.8.3 | TPOT, decodificación, MBU, techo, *prefill* | `05_derivados/tpot_serie_n100.json` → `tab_C1`, `tab_C2`, `tab_C4`, `tab_C8` |
| 6.8.3 | Ablación de gramática | `05_derivados/ablacion_gramatica.json` → `tab_C5`, `E-A_ablacion_gramatica.md` |
| 6.8.4 | Réplica pareada, n = 64 | `04_trazas/turns_replica_estricta.ndjson` → `tab_E1`, `tab_E2`, `tab_E3` |
| 6.8.4 | Fallos y McNemar | ídem → `tab_E6`, `tab_E5`, `tab_E4` |
| 6.8.4 | Batería de 45 turnos | `04_trazas/turns.ndjson` → `tab_D1`, `tab_D3` |
| 6.8.5 | Alucinación 0/9, Wilson 29,9 % | `02_fixtures/verdad.json` → `tab_D7`, `tab_D6` |
| 6.8.6 | Tablero de hipótesis | `03_hipotesis/preregistro.md` → `tab_F1` |
| 6.8.7 | Potencia del diseño | `tab_F4` |
| 6.8.8 | Once aserciones, una falla | `fuentes/VERIFICACION_NOTEBOOK.txt` |

