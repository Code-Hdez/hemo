# 03 · Capítulo I — Marco teórico y glosario

**Estado: 🟡** Estructura correcta, extensión conforme al mínimo de 10 páginas que exige el
manual, buena densidad de citas. Dos trabajos pendientes: **una subsección nueva** que dé
sustrato teórico a lo que el Capítulo VI ahora mide, y **el glosario, que quedó describiendo un
sistema que ya no existe**.

Acciones: `A-I-01`, `A-I-02`, `A-I-03`.

---

## A-I-01 · 🔴 El glosario define un runtime que no es el desplegado

**Localización:** §1.2, apartado «C. Términos de sistemas de IA y arquitectura».

### Entrada «LLM» — texto actual

> «**LLM (Large Language Model):** modelo de inteligencia artificial generativa capaz de procesar
> contexto y producir lenguaje natural. En HemoVet, el runtime conversacional verificado utiliza
> **Qwen3 4B** en una variante cuantizada, ejecutada mediante Ollama. […]»

### Reemplazo

> «**LLM (*Large Language Model*):** modelo de inteligencia artificial generativa capaz de
> procesar contexto y producir lenguaje natural. En HemoVet, el *runtime* conversacional
> verificado utiliza **Qwen3.6 de 27 mil millones de parámetros en cuantización Q4_K_M**
> (`qwen3.6:27b-q4_K_M`), ejecutado mediante Ollama sobre una unidad de procesamiento gráfico
> NVIDIA A100. La identidad del modelo se sella por su compendio criptográfico (*digest*) y se
> verifica en cada respuesta emitida. Su función está restringida a explicar información
> autorizada por el sistema y no a emitir diagnósticos o tratamientos.»

### Entrada «Ollama» — texto actual

> «**Ollama:** servidor local para la ejecución de modelos de lenguaje. En HemoVet se utiliza
> para servir el modelo **Qwen3 4B** dentro de la infraestructura del sistema. […]»

### Reemplazo

> «**Ollama:** servidor local para la ejecución de modelos de lenguaje. En HemoVet, la versión
> 0.32.6 sirve el modelo sellado dentro de la infraestructura del sistema. Su operación requiere
> control de identidad del modelo, precarga residente en memoria de vídeo y manejo explícito de
> arranques en frío, que en las mediciones realizadas superaron los dos minutos.»

---

## A-I-02 · Doce términos que el Capítulo VI usará y el glosario no define

Si se incorpora §6.9, el documento empieza a usar vocabulario de rendimiento de inferencia y de
inferencia estadística que hoy no está definido. El manual pide explícitamente que el glosario
cubra «técnicas estadísticas», «servicios utilizados» y «hardware».

### Para «B. Términos de aprendizaje automático y evaluación»

> **Intervalo de confianza de Wilson:** método para estimar el intervalo de confianza de una
> proporción binomial que, a diferencia de la aproximación normal, se mantiene válido cuando la
> proporción observada es cero o uno y cuando la muestra es pequeña. Es el procedimiento
> utilizado en este trabajo para acotar la incertidumbre de proporciones observadas en cero, en
> las que informar únicamente el valor puntual induciría a concluir erróneamente que el fenómeno
> está ausente.

> **Prueba de McNemar:** prueba estadística para datos pareados de resultado binario que evalúa
> si la proporción de discordancias entre dos condiciones aplicadas a los mismos sujetos difiere
> del azar. Se emplea aquí para contrastar la tasa de turnos sin respuesta entre dos corridas
> sobre el mismo conjunto de casos.

> **Prueba de Wilcoxon de rangos con signo:** alternativa no paramétrica a la prueba *t* pareada,
> que compara la mediana de las diferencias entre observaciones apareadas sin suponer normalidad.
> Se emplea aquí para contrastar la latencia por caso entre dos configuraciones de *hardware*.

> **Potencia estadística:** probabilidad de que un diseño experimental detecte un efecto de un
> tamaño dado cuando ese efecto realmente existe. Un diseño con potencia insuficiente no permite
> concluir ausencia de efecto a partir de un resultado no significativo.

> **Pre-registro:** práctica consistente en fijar y sellar por escrito las hipótesis, las métricas
> y los criterios de decisión de un experimento **antes** de observar los datos, de modo que el
> resultado no pueda reinterpretarse a posteriori en función de lo observado. La integridad del
> pre-registro se acredita mediante una función resumen criptográfica.

> **Coeficiente kappa de acuerdo entre corridas:** aplicación del coeficiente kappa de Cohen a la
> coincidencia de identificadores de casos fallidos entre dos ejecuciones del mismo protocolo. Un
> valor negativo indica un acuerdo peor que el esperado por azar, lo que evidencia que ambos
> conjuntos de fallos corresponden a fenómenos distintos y no a la persistencia de los mismos
> errores.

### Para «C. Términos de sistemas de IA y arquitectura»

> **TPOT (*time per output token*):** tiempo medio empleado en generar cada token de salida una
> vez iniciada la generación. Es la métrica que gobierna la velocidad percibida de una respuesta
> larga en un sistema conversacional.

> **Prefill y decodificación:** las dos fases de la inferencia de un modelo de lenguaje. En el
> *prefill* se procesa el mensaje de entrada completo en paralelo; en la decodificación se emite
> la respuesta token a token de forma secuencial. Ambas se expresan en tokens por segundo, pero
> no son comparables entre sí como medida de rendimiento.

> **MBU (*model bandwidth utilization*):** proporción del ancho de banda nominal de la memoria de
> la unidad de procesamiento gráfico que un despliegue llega a aprovechar durante la
> decodificación. En modelos limitados por memoria, el techo de decodificación se aproxima por el
> cociente entre el ancho de banda de memoria y el tamaño del modelo en disco.

> **Decodificación restringida por gramática (GBNF):** técnica que obliga al modelo a producir
> únicamente salidas que se ajusten a una gramática formal —por ejemplo, un esquema JSON—
> enmascarando en cada paso los tokens que violarían la estructura. Garantiza la validez
> sintáctica de la respuesta a cambio de un sobrecosto de cómputo por token.

> **Instancia interrumpible (*spot*):** modalidad de contratación de cómputo en la nube en la que
> el proveedor cede capacidad excedente a precio reducido y puede reclamarla en cualquier momento
> con un aviso mínimo. Reduce el costo operativo a cambio de renunciar a la garantía de
> continuidad.

> **Arranque a prueba de fallos (*fail-closed*):** política de despliegue según la cual, si
> cualquier validación del entorno de ejecución no se satisface, el sistema **no** arranca en
> modo degradado sino que se detiene. Aplicada al *runtime* conversacional, impide que el
> servicio atienda tráfico con un modelo, un controlador o un *hardware* distintos de los
> sellados.

> **Verificación de implicación textual (*entailment*):** comprobación automática de que una
> afirmación contenida en la respuesta generada está efectivamente respaldada por el fragmento
> del corpus que se cita como fuente. Permite detectar citas formalmente presentes pero que no
> sustentan lo afirmado.

---

## A-I-03 · Subsección nueva §1.1.3.7 — Rendimiento de inferencia de modelos de lenguaje

**Localización:** al final de §1.1.3, después de «1.1.3.6. LLM, RAG y diseño ético para
comunicación ciudadana».

### Por qué es necesaria

El manual es explícito (p. 6): el marco teórico debe «contener la información suficiente para
nivelar a un ingeniero en el área técnica […] para que sea capaz de comprender todos los
elementos que intervienen en este trabajo», y debe «señalar cómo nuestro proyecto amplía la
literatura actual».

Con §6.9 incorporada, el Capítulo VI **refuta cuantitativamente un valor publicado en la
literatura** (la sobrecarga de decodificación restringida por gramática: se predecían ≥ 10
ms/token, se midieron 0,332 ms/token, un factor de ~44×). Un capítulo de resultados no puede
refutar literatura que el marco teórico nunca presentó. Hoy §1.1.3.6 cubre LLM, RAG y ética, pero
no toca el sustrato de rendimiento.

### Guion propuesto (≈ 2 páginas)

**a) El régimen limitado por memoria.** La inferencia autorregresiva de un modelo de lenguaje en
la fase de decodificación está gobernada por el ancho de banda de memoria, no por la capacidad
aritmética: en cada paso hay que recorrer todos los pesos del modelo para producir un solo token.
De ahí el techo teórico de decodificación como cociente entre ancho de banda de memoria y tamaño
del modelo, y de ahí que la métrica de eficiencia relevante sea el MBU y no la utilización de
cómputo. **Advertencia que debe quedar escrita en el marco, porque el Capítulo VI la usa:** el
tamaño debe tomarse en unidades decimales (GB) y no binarias (GiB); confundirlas infla el techo
un 7,4 %.

**b) Prefill frente a decodificación.** Por qué el *prefill* procesa el mensaje en paralelo y la
decodificación va token a token; por qué ambas se expresan en tokens por segundo pero no son
comparables; y por qué con mensajes cortos la cifra de *prefill* queda dominada por la sobrecarga
fija y resulta inflada respecto a lo que daría un mensaje largo.

**c) Decodificación restringida por gramática.** Qué es el enmascarado por gramática, para qué se
usa (garantizar salida estructurada válida), y qué costo por token le atribuye la literatura.
**Aquí es donde se cita el valor que el Capítulo VI refuta.** Presentarlo como lo que es: un
valor publicado para otros despliegues, cuya reproducción en este despliegue concreto es una
pregunta empírica.

**d) Determinismo de la inferencia.** Con temperatura cero, `top_k` = 1 y semilla fija, la
generación debería ser reproducible dentro de una misma máquina. Por qué esa reproducibilidad
**no** se extiende entre máquinas distintas, y por qué eso obliga a sellar la identidad del
*hardware* junto con la del modelo si se quiere comparar mediciones.

**e) Reproducibilidad de mediciones de inferencia.** Qué debe registrar un protocolo de medición
para que sus cifras sean recuperables: modelo, compendio, cuantización, versión del servidor,
controlador, GPU exacta, parámetros de muestreo, esquema de salida, mensajes renderizados,
*warm-up*, concurrencia y definición operativa de la métrica de latencia. Este párrafo es el que
justifica, en el Capítulo VI, por qué se declara que la configuración anterior **no es
verificable**: de quince preguntas del protocolo, once no constan o constan parcialmente.

### Fuentes a incorporar

Buscar y citar en formato IEEE (mínimo cinco entradas nuevas):

1. Un trabajo de referencia sobre el análisis *roofline* aplicado a inferencia de transformadores
   (relación cómputo / ancho de banda de memoria).
2. La fuente que publica el sobrecosto de la decodificación restringida por gramática —**es la
   que el Capítulo VI refuta, así que la cita tiene que ser precisa y verificable**.
3. Documentación técnica de la arquitectura NVIDIA A100 (ancho de banda nominal de 2 039 GB/s en
   la variante SXM4 de 40 GB) — vale una *datasheet*, que el manual acepta explícitamente como
   fuente primaria.
4. Un trabajo sobre cuantización de modelos de lenguaje y su efecto en tamaño efectivo y calidad.
5. Un trabajo metodológico sobre pre-registro de hipótesis y su papel contra la reinterpretación
   posterior de resultados.
6. (Recomendable) La fuente original del intervalo de Wilson y una referencia sobre por qué la
   aproximación normal falla en proporciones cercanas a cero.

---

## Lo que NO hay que tocar del Capítulo I

- §1.1.1 Fundamentos clínico-veterinarios — sólido y bien citado.
- §1.1.2 Similitud fenotípica entre patrones y limitaciones instrumentales — sigue siendo la
  justificación del enfoque multietiqueta. ✅
- §1.1.3.1 a §1.1.3.5 — métricas para multietiqueta desbalanceado, datos tabulares, ensambles y
  SHAP, desplazamiento de dominio, extracción desde PDF. Todo vigente.
- §1.1.4 Contexto epidemiológico regional — la ehrlichiosis canina en el Caribe sigue siendo el
  ancla de la justificación y del módulo de vigilancia. ✅
- §1.2 apartados A, B y D (términos clínicos, de aprendizaje automático, acrónimos del CBC) —
  correctos; solo se **añade**, no se corrige.

## Checklist de cierre de este bloque

- [ ] Entrada «LLM» del glosario actualizada.
- [ ] Entrada «Ollama» del glosario actualizada.
- [ ] Seis términos nuevos añadidos al apartado B del glosario.
- [ ] Seis términos nuevos añadidos al apartado C del glosario.
- [ ] §1.1.3.7 redactada (≈ 2 páginas).
- [ ] Mínimo cinco referencias IEEE nuevas incorporadas y numeradas en orden de aparición.
- [ ] Verificado que el capítulo sigue superando el mínimo de 10 páginas que exige el manual.
