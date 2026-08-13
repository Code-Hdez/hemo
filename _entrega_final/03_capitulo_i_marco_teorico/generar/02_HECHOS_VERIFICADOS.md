# Hechos verificados — la única fuente de datos para el Capítulo I

> Este capítulo es de literatura, no de medición, así que la mayor parte de lo que necesitas son
> **definiciones y conceptos**, no cifras. Las pocas cifras que aparecen están aquí con su marca.
>
> **[MEDIDO]** leído de un artefacto · **[DERIVADO]** calculado a partir de artefactos ·
> **[NOMINAL]** dato de fabricante o de especificación · **[PENDIENTE]** no disponible: usar
> marcador, **nunca** estimar.
>
> Verificado el 12 de agosto de 2026 sobre la rama `main`, commit `f9deedb`.

---

## 1 · Las dos entradas de glosario que hay que corregir 🔴

Están en §1.2, apartado «C. Términos de sistemas de IA y arquitectura».

### 1.1 · Entrada «LLM»

> **Texto actual:** «**LLM (Large Language Model):** modelo de inteligencia artificial generativa
> capaz de procesar contexto y producir lenguaje natural. En HemoVet, el runtime conversacional
> verificado utiliza **Qwen3 4B** en una variante cuantizada, ejecutada mediante Ollama. […]»

> **Reemplazo:** «**LLM (*Large Language Model*):** modelo de inteligencia artificial generativa
> capaz de procesar contexto y producir lenguaje natural. En HemoVet, el *runtime* conversacional
> verificado utiliza **Qwen3.6 de 27 mil millones de parámetros en cuantización Q4_K_M**
> (`qwen3.6:27b-q4_K_M`), ejecutado mediante Ollama sobre una unidad de procesamiento gráfico
> NVIDIA A100. La identidad del modelo se sella por su compendio criptográfico (*digest*) y se
> verifica en cada respuesta emitida. Su función está restringida a explicar información
> autorizada por el sistema y no a emitir diagnósticos o tratamientos.»

**Conserva la cita `[48]` al final de la entrada y el resto de la frase.**

### 1.2 · Entrada «Ollama»

> **Texto actual:** «**Ollama:** servidor local para la ejecución de modelos de lenguaje. En
> HemoVet se utiliza para servir el modelo **Qwen3 4B** dentro de la infraestructura del sistema.
> […]»

> **Reemplazo:** «**Ollama:** servidor local para la ejecución de modelos de lenguaje. En HemoVet,
> la versión 0.32.6 sirve el modelo sellado dentro de la infraestructura del sistema. Su operación
> requiere control de identidad del modelo, precarga residente en memoria de vídeo y manejo
> explícito de arranques en frío, que en las mediciones realizadas superaron los dos minutos.»

---

## 2 · Las doce entradas de glosario nuevas

Están redactadas. **Van en orden alfabético dentro de su apartado**, intercaladas con las
existentes, no en bloque al final.

### Para «B. Términos de aprendizaje automático y evaluación» — seis entradas

> **Coeficiente kappa de acuerdo entre corridas:** aplicación del coeficiente kappa de Cohen a la
> coincidencia de identificadores de casos fallidos entre dos ejecuciones del mismo protocolo. Un
> valor negativo indica un acuerdo peor que el esperado por azar, lo que evidencia que ambos
> conjuntos de fallos corresponden a fenómenos distintos y no a la persistencia de los mismos
> errores.

> **Intervalo de confianza de Wilson:** método para estimar el intervalo de confianza de una
> proporción binomial que, a diferencia de la aproximación normal, se mantiene válido cuando la
> proporción observada es cero o uno y cuando la muestra es pequeña. Es el procedimiento utilizado
> en este trabajo para acotar la incertidumbre de proporciones observadas en cero, en las que
> informar únicamente el valor puntual induciría a concluir erróneamente que el fenómeno está
> ausente.

> **Potencia estadística:** probabilidad de que un diseño experimental detecte un efecto de un
> tamaño dado cuando ese efecto realmente existe. Un diseño con potencia insuficiente no permite
> concluir ausencia de efecto a partir de un resultado no significativo.

> **Pre-registro:** práctica consistente en fijar y sellar por escrito las hipótesis, las métricas
> y los criterios de decisión de un experimento **antes** de observar los datos, de modo que el
> resultado no pueda reinterpretarse a posteriori en función de lo observado. La integridad del
> pre-registro se acredita mediante una función resumen criptográfica.

> **Prueba de McNemar:** prueba estadística para datos pareados de resultado binario que evalúa si
> la proporción de discordancias entre dos condiciones aplicadas a los mismos sujetos difiere del
> azar. Se emplea aquí para contrastar la tasa de turnos sin respuesta entre dos corridas sobre el
> mismo conjunto de casos.

> **Prueba de Wilcoxon de rangos con signo:** alternativa no paramétrica a la prueba *t* pareada,
> que compara la mediana de las diferencias entre observaciones apareadas sin suponer normalidad.
> Se emplea aquí para contrastar la latencia por caso entre dos configuraciones de *hardware*.

### Para «C. Términos de sistemas de IA y arquitectura» — seis entradas

> **Arranque a prueba de fallos (*fail-closed*):** política de despliegue según la cual, si
> cualquier validación del entorno de ejecución no se satisface, el sistema **no** arranca en modo
> degradado sino que se detiene. Aplicada al *runtime* conversacional, impide que el servicio
> atienda tráfico con un modelo, un controlador o un *hardware* distintos de los sellados.

> **Decodificación restringida por gramática (GBNF):** técnica que obliga al modelo a producir
> únicamente salidas que se ajusten a una gramática formal —por ejemplo, un esquema JSON—
> enmascarando en cada paso los tokens que violarían la estructura. Garantiza la validez
> sintáctica de la respuesta a cambio de un sobrecosto de cómputo por token.

> **Instancia interrumpible (*spot*):** modalidad de contratación de cómputo en la nube en la que
> el proveedor cede capacidad excedente a precio reducido y puede reclamarla en cualquier momento
> con un aviso mínimo. Reduce el costo operativo a cambio de renunciar a la garantía de
> continuidad.

> **MBU (*model bandwidth utilization*):** proporción del ancho de banda nominal de la memoria de
> la unidad de procesamiento gráfico que un despliegue llega a aprovechar durante la
> decodificación. En modelos limitados por memoria, el techo de decodificación se aproxima por el
> cociente entre el ancho de banda de memoria y el tamaño del modelo en disco.

> **Prefill y decodificación:** las dos fases de la inferencia de un modelo de lenguaje. En el
> *prefill* se procesa el mensaje de entrada completo en paralelo; en la decodificación se emite
> la respuesta token a token de forma secuencial. Ambas se expresan en tokens por segundo, pero no
> son comparables entre sí como medida de rendimiento.

> **TPOT (*time per output token*):** tiempo medio empleado en generar cada token de salida una
> vez iniciada la generación. Es la métrica que gobierna la velocidad percibida de una respuesta
> larga en un sistema conversacional.

> **Verificación de implicación textual (*entailment*):** comprobación automática de que una
> afirmación contenida en la respuesta generada está efectivamente respaldada por el fragmento del
> corpus que se cita como fuente. Permite detectar citas formalmente presentes pero que no
> sustentan lo afirmado.

> ⚠️ Son **siete** entradas para el apartado C, contando las dos correcciones aparte. Si prefieres
> ceñirte a seis, la de implicación textual puede ir a «B» por su carácter evaluativo. Elige una
> ubicación y decláralo en el registro de cambios.

---

## 3 · Los datos técnicos que §1.1.3.7 puede usar

**Solo estos, y solo como magnitudes de referencia del dominio, no como resultados del proyecto.**

| Dato | Valor | Marca | Uso admitido en este capítulo |
| :--- | :--- | :---: | :--- |
| Ancho de banda nominal de la A100-SXM4-40GB | 2 039 GB/s | NOMINAL | Sí: es especificación de fabricante, y sirve para ilustrar el cálculo del techo |
| Sobrecosto de gramática según la literatura | ≥ 10 ms/token | — | **Sí, y es obligatorio**: es el valor que §6.8 refuta |
| Diferencia entre GB decimales y GiB binarios | 7,4 % de sobreestimación del techo si se confunden | DERIVADO | Sí: es una advertencia metodológica general |
| Parámetros para inferencia determinista | temperatura 0, `top_k` 1, semilla fija | — | Sí: es la definición del régimen determinista |
| Los quince parámetros de un protocolo reproducible | modelo, compendio, cuantización, versión del servidor, controlador, unidad gráfica, muestreo, esquema de salida, mensajes renderizados, calentamiento, concurrencia, definiciones operativas… | — | Sí: es la enumeración de lo que debe registrarse |

### 🔴 Lo que NO puede aparecer en este capítulo

| Cifra prohibida | Por qué | Dónde va |
| :--- | :--- | :--- |
| 0,332 ms/token | Es la medición del proyecto | §6.8 |
| Factor de ~44× | Es la comparación del proyecto | §6.8 y §7.4 |
| MBU 34,90 % · TPOT 24,4802 ms · decodificación 40,849 tok/s | Mediciones | §6.8 |
| 117,0 tok/s de techo teórico | Es el techo **calculado para este despliegue** | §6.8 |
| 11 de 15 preguntas sin constancia | Es el resultado de la auditoría | §3.11 y §6.8 |
| Cualquier latencia del asistente | Medición | §6.8 |

**El criterio, en una frase:** este capítulo explica **por qué** el techo de decodificación se
calcula como el cociente entre ancho de banda y tamaño del modelo; el Capítulo VI dice **cuánto**
dio ese cociente para este despliegue.

---

## 4 · Las referencias nuevas — mínimo cinco

Ninguna está en el paquete. **Todas se marcan como pendientes** salvo que las tengas verificadas.

| Marcador | Qué hay que citar | Criticidad |
| :--- | :--- | :---: |
| `[REF-NUEVA-1]` | Análisis *roofline* aplicado a inferencia de transformadores: el régimen limitado por ancho de banda de memoria en la fase de decodificación | Alta |
| `[REF-NUEVA-2]` | **La fuente que publica el sobrecosto de la decodificación restringida por gramática** | 🔴 **Crítica** |
| `[REF-NUEVA-3]` | Documentación técnica de la arquitectura NVIDIA A100 (ancho de banda nominal de 2 039 GB/s en la variante SXM4 de 40 GB). Una *datasheet* sirve: el manual las acepta como fuente primaria | Media |
| `[REF-NUEVA-4]` | Cuantización de modelos de lenguaje y su efecto en tamaño efectivo y calidad | Media |
| `[REF-NUEVA-5]` | Pre-registro de hipótesis como práctica metodológica contra la reinterpretación posterior de resultados | Media |
| `[REF-NUEVA-6]` | Wilson, sobre el intervalo de confianza para proporciones binomiales, y/o por qué la aproximación normal falla cerca de cero | Recomendable |

> 🔴 **Sobre `[REF-NUEVA-2]`.** Es la referencia más importante que este capítulo va a incorporar.
> §6.8 la refuta cuantitativamente, y **refutar una fuente que no está citada es indefendible**.
> Tiene que ser exacta, verificable y localizable: autor, título, publicación, año, y el valor
> concreto que atribuye. Si no la tienes, el marcador debe describir con precisión qué se busca,
> no quedarse en «una fuente sobre gramáticas».

**Verificaciones antes de crear entradas nuevas:**

- **Wilcoxon** puede estar ya citado a propósito de la validación clínica. Si lo está, se reutiliza
  la entrada existente; no se duplica.
- **Cohen**, para el coeficiente kappa, casi con seguridad ya está citado en el capítulo de
  resultados. Reutilizar.
- El manual **prohíbe** Wikipedia, blogs sin autoría reconocida y foros.

---

## 5 · Lo que NO se toca del Capítulo I

| Sección | Contenido | Estado |
| :--- | :--- | :---: |
| §1.1.1 | Fundamentos clínico-veterinarios | ✅ sólido y bien citado |
| §1.1.2 | Similitud fenotípica entre patrones y limitaciones instrumentales | ✅ sigue siendo la justificación del enfoque multietiqueta |
| §1.1.3.1 – §1.1.3.5 | Métricas para multietiqueta desbalanceado, datos tabulares, ensambles y SHAP, desplazamiento de dominio, extracción desde PDF | ✅ todo vigente |
| §1.1.3.6 | Modelos de lenguaje, recuperación de información y diseño ético | ✅ vigente |
| §1.1.4 | Contexto epidemiológico regional | ✅ la ehrlichiosis canina en el Caribe sigue siendo el ancla de la justificación |
| §1.2 apartados A, B y D | Términos clínicos, de aprendizaje automático, acrónimos del CBC | ✅ correctos; en B solo se **añade** |

**Reprodúcelos íntegros.** No resumas, no reordenes, no «mejores» la redacción y no toques sus
citas.
