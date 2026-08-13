# Hechos verificados — la única fuente de cifras para el Capítulo VI

> Toda cifra del capítulo debe salir de aquí o del texto ya redactado de
> `04_SECCIONES_YA_REDACTADAS.md`. Cada entrada lleva su marca:
> **[MEDIDO]** leído directamente de un artefacto · **[DERIVADO]** calculado a partir de artefactos
> · **[NO CONSTA]** no recuperable, y eso **es un resultado**, no un vacío que rellenar ·
> **[PENDIENTE]** no disponible en este paquete: usar marcador, **nunca** estimar.
>
> Verificado el 12 de agosto de 2026 sobre la rama `main`, commit `f9deedb`.

---

## 1 · Correcciones obligatorias sobre el texto actual

Son cinco, y ninguna requiere reescribir una sección entera.

### 1.1 · §6.4.2, Tabla 6.10 — La latencia de 24,1 s hay que fecharla 🟡

La última fila dice hoy: `Latencia media (respuestas generadas) | 24.1 s`.

**La cifra es correcta para la configuración con la que se midió**, que ya no es la vigente. No se
borra: es un dato real y honesto. Se fecha y se remite.

> **Fila nueva:** `Latencia media de las respuestas generadas (configuración de julio de 2026) | 24,1 s`
>
> **Nota al pie de la tabla:** «Esta medición corresponde a la configuración de *runtime* vigente
> en julio de 2026. La caracterización de la configuración actual, posterior a la migración a
> aceleración por unidad de procesamiento gráfico, se presenta en §6.8.»

### 1.2 · §6.4.1 — Acotar temporalmente la atribución a la CPU 🟡

El párrafo que atribuye los fallos residuales a «los tiempos de respuesta asociados a la
generación basada en la CPU sin GPU» debe añadir **«en la configuración entonces vigente»**. Sin
esa acotación, el capítulo se contradice a sí mismo cuatro secciones más abajo.

### 1.3 · §6.4.3 — Reatribuir los dos tiempos de espera 🟡

El texto dice que dos turnos fueron tiempos de espera «debidos a un fallo transitorio de la
infraestructura de la CPU, no a una pérdida de contexto». Esa afirmación era una hipótesis; ahora
está contrastada.

> **Añadir al final del párrafo:** «En la caracterización posterior sobre la configuración con
> aceleración gráfica, la misma batería de 45 turnos no registró ningún turno sin respuesta
> (§6.8), lo que respalda la atribución de estos dos casos a la infraestructura de ejecución y no
> al manejo del contexto conversacional.»

### 1.4 · §6.4.5, Tabla 6.11 — Un cero sin intervalo no es un resultado 🔴

La tabla dice `Alucinadas | 0 / 30 (0 %)` y el cuerpo afirma que «ninguna respuesta fue
alucinada». **Cero casos observados no demuestra ausencia.** Con n = 30, el intervalo de Wilson
al 95 % para una proporción observada de cero llega hasta el **11,4 %** [DERIVADO].

Publicar el cero solo, en un documento que después presenta §6.8 —donde el mismo tratamiento se
aplica con rigor—, es inconsistente consigo mismo.

> **Fila corregida:** `Alucinadas | 0 / 30 (0 %; IC 95 % de Wilson: 0 – 11,4 %) | ídem`
>
> **Añadir al párrafo:** «La ausencia de alucinaciones en la muestra evaluada acota la tasa por
> debajo del 11,4 % con un 95 % de confianza, pero no permite afirmar que sea nula: alcanzar una
> cota del 5 % requeriría del orden de sesenta preguntas evaluadas, y del 1 %, alrededor de
> trescientas.»
>
> **Mismo criterio** para la fila «Respuestas seguras clínicamente 30/30 (100 %)»: añadir
> IC 95 % de **88,6 – 100 %** [DERIVADO].

### 1.5 · §6.4.2 — Una frase que pertenece al Capítulo VII 🟡

> **Texto actual:** «[…] hallazgo que se entrega al equipo de desarrollo.»

El manual (p. 13) es explícito: en resultados «no se incluyen conclusiones ni sugerencias».
**Cortar la frase.** La acción se traslada a §7.5, que no es tu encargo.

---

## 2 · El dato pendiente 🔴 [PENDIENTE]

§6.5, Tabla 6.13, última fila: `Pruebas backend | 25 pruebas exitosas en 1.45s`.

**Esa cifra está desactualizada.** Hoy el directorio de pruebas contiene **35 archivos de test**
[MEDIDO], incluidos varios que no existían cuando se escribió: contrato de manifiesto de versión,
arranque del nodo con GPU, topología de composición, reversión, contrato de entorno de despliegue,
aceptación de etapa 10, retención de conversaciones y humo del chat.

**La cifra real de pruebas que pasan no está en este paquete.** Escribe:

> `[PENDIENTE: salida literal de la suite de pruebas del backend, con su fecha de ejecución]`

y anótalo en el registro de cambios. **No escribas 25, ni 35, ni ningún número inventado.**

Las demás cifras de esa misma tabla —latencia de inferencia media 28,73 ms · p50 27,93 · p95 33,9
· p99 137,95 · n = 1 000 · calentamiento 50— **están correctas y no se tocan** [MEDIDO].

### Párrafo de cierre que hay que añadir a §6.5

Hoy la sección deja al lector con la impresión de que la latencia percibida es un misterio, y
desde §6.8 ya no lo es:

> «Esta medición corresponde exclusivamente al motor de clasificación, sin capa HTTP,
> autenticación, base de datos ni recuperación semántica. La latencia percibida por el usuario en
> el flujo conversacional está dominada por la generación de lenguaje, cuya caracterización se
> presenta en §6.8: la inferencia del clasificador representa menos del uno por mil del tiempo de
> un turno de chat.»

*(28,73 ms sobre una mediana de 21,4 s ≈ 0,13 % [DERIVADO].)*

---

## 3 · Lo que NO se toca, y por qué conviene saberlo

Es la parte del documento que sostiene el proyecto. Reprodúcela **íntegra**, sin resumir, sin
«mejorar» la redacción y sin recalcular nada.

| Sección | Cifras verificadas | Estado |
| :--- | :--- | :---: |
| §6.1 y 6.1.1–6.1.4 | PR-AUC macro 0,9529 · F1 macro 0,8727 · recall macro 0,9205 · intervalos *bootstrap* · evolución v3→v4 · SHAP | ✅ MEDIDO |
| §6.2 | 1 301 registros del Dog Aging Project · desplazamiento severo en `Monocytes` y `RDW` · métricas supervisadas **no calculables** por falta de etiquetas compatibles | ✅ MEDIDO / NO CONSTA |
| §6.3 y 6.3.1–6.3.4 | 526 casos, 509 evaluables · 2 evaluadores · 4 semanas · κ macro V1-V2 0,684 · κ modelo-V1 0,629 · F1 macro 0,704 | ✅ MEDIDO |
| §6.4.1 | 770 preguntas · dos rondas · *prompt injection* 61 → 1 · diagnóstico definitivo 25 → 2 | ✅ MEDIDO |
| §6.4.4 | Jaccard medio 0,84 | ✅ MEDIDO |
| §6.7 y 6.7.1–6.7.2 | n = 44 · media 4,37/5 · índice 84,3/100 · 81,6 % favorable · 0 % desfavorable | ✅ MEDIDO |

La declaración de que la usabilidad es una muestra de conveniencia con instrumento propio y sin
tareas cronometradas **ya está en el texto y está bien**. No la suavices.

---

## 4 · §6.9 síntesis — el párrafo de rendimiento quedó falso 🔴

> **Texto actual:** «Los resultados técnicos indicaron que la parte del sistema dedicada a la
> clasificación ofrecía una latencia aceptable para un uso interactivo, mientras que **la parte
> conversacional presentaba limitaciones en el tiempo de respuesta cuando funcionaba sin el apoyo
> de una GPU**.»

> **Reemplazo completo (dos párrafos):**
>
> «Los resultados técnicos indicaron que el componente de clasificación ofrece una latencia
> holgadamente compatible con el uso interactivo, con una media de 28,73 milisegundos por
> inferencia. El componente conversacional, que domina el tiempo de respuesta percibido, fue
> caracterizado tras la migración a aceleración por unidad de procesamiento gráfico: la latencia
> mediana por turno se redujo un 60,6 % respecto de la configuración anterior —de 54,4 a 21,4
> segundos, contraste de Wilcoxon pareado por caso sobre 64 casos, intervalo de confianza del 95 %
> de 19,06 a 46,28 segundos— y la proporción de turnos sin respuesta pasó del 24,3 % al 8,6 %
> (McNemar exacto, p = 0,035). No obstante, el análisis de identificadores de fallo muestra que
> ninguno de los diecisiete fallos anteriores reaparece y que el acuerdo entre ambos conjuntos es
> peor que el azar, lo que indica que se trata de dos fenómenos distintos —fallos de contrato en
> la configuración anterior y fallos de transporte en la actual— y no de la corrección de los
> mismos errores. La caracterización física del *runtime* es absoluta para la configuración
> vigente y no constituye una comparación entre unidades de procesamiento gráfico, dado que los
> parámetros de la configuración anterior no fueron registrados y no son recuperables.
>
> El módulo de vigilancia poblacional permanece operativo como visualización agregada de carácter
> exploratorio: sus cinco compuertas técnicas se aprobaron, pero los indicadores de geocodificación
> y de concentración espacial impiden cualquier lectura territorial (§6.6).»

El resto de §6.9 —los párrafos sobre el motor de clasificación, la validación externa, la
validación clínica, el módulo conversacional y la usabilidad— **están bien y no se tocan**.

---

## 5 · Identidad del runtime medido — el sello de §6.8

Todas estas cifras ya están dentro del texto de `04`. Se reproducen aquí para que puedas
verificarlas sin salir del paquete.

| Campo | Valor | Marca |
| :--- | :--- | :---: |
| Modelo | Qwen3.6 de 27 mil millones de parámetros, cuantización Q4_K_M (`qwen3.6:27b-q4_K_M`) | MEDIDO |
| Compendio del modelo | `a50eda8ed977ab48…` | MEDIDO |
| Tamaño | 17 420 432 739 bytes = 16,224 GiB = 17,420 GB | MEDIDO |
| Servidor de modelos | Ollama **0.32.6** | MEDIDO |
| Unidad de procesamiento gráfico | NVIDIA **A100-SXM4-40GB**, modalidad interrumpible | MEDIDO |
| Controlador / CUDA | 580.159.03 / 13.0 | MEDIDO |
| Ventana de contexto por petición | 16 384 tokens (la A100 admite hasta 65 536) | MEDIDO |
| Atención rápida / caché de claves y valores | activada / `q8_0` | MEDIDO |
| Paralelismo / persistencia en memoria | 1 / residente | MEDIDO |
| Verificación de identidad por respuesta | 115 de 115 respuestas del modelo sellado; 0 de otro | MEDIDO (censo) |
| Modelos instalados en el nodo | **2**: el sellado y el anterior de 4 mil millones, que sigue presente | MEDIDO |

> ⚠️ **Matiz que debe quedar escrito:** el modelo anterior sigue instalado en el servidor y la
> comprobación presente en el código **no impide su uso**. Se verificó posteriormente que ninguna
> respuesta procede de él, pero la garantía es de verificación, no de imposibilidad por diseño.

---

## 6 · Rendimiento físico — caracterización absoluta, nunca comparación

| Cifra | Valor | IC 95 % | Marca |
| :--- | ---: | :--- | :---: |
| TPOT p50 | 24,4802 ms/token | 24,4701 – 24,5193 | MEDIDO |
| CV del TPOT | 0,65 % | — | DERIVADO |
| Decodificación p50 | 40,849 tok/s | 40,784 – 40,866 | MEDIDO |
| Techo teórico de decodificación | 117,0 tok/s | — | DERIVADO |
| Banda alcanzable (77 % / 86 %) | 90,1 / 100,7 tok/s | — | DERIVADO |
| MBU | 34,90 % | 34,84 – 34,91 | DERIVADO |
| Ancho de banda efectivo | 711,6 GB/s (nominal 2 039 GB/s) | — | DERIVADO |
| Prefill p50 | 91,9 tok/s | — | MEDIDO |
| Determinismo intra-máquina | 20 mensajes × 5 repeticiones = 100; **0** con más de un compendio | — | MEDIDO |
| Sobrecarga de gramática (Δ TPOT) | **+0,332 ms/token** (1,33 % del TPOT) | sin IC: crudos no persistidos | MEDIDO |

> **Cuatro advertencias que deben viajar con estas cifras.**
> **(a)** El techo se calcula con el tamaño en GB decimales (17,42), no en GiB (16,22):
> confundirlos infla el techo un 7,4 %.
> **(b)** Un MBU bajo **no** indica ineficiencia del despliegue: el MBU baja al subir el ancho de
> banda porque la sobrecarga fija por token no escala.
> **(c)** El CV de 0,65 % es la máquina en su mejor caso —100 generaciones consecutivas, modelo ya
> cargado, temperatura 0, `top_k` 1, semilla fija, sin concurrencia—, **no** lo que ve el usuario.
> **(d)** Prefill y decodificación comparten unidad pero no son comparables como rendimiento: el
> prefill se midió con mensajes de 17 a 22 tokens, donde lo domina la sobrecarga fija.

---

## 7 · Comportamiento del asistente — las cifras que sí admiten contraste

### 7.1 Réplica estricta pareada (n = 64 casos con latencia)

| Cifra | Valor | Marca |
| :--- | ---: | :---: |
| p50 línea base (7 de agosto), recalculado desde crudos | 54,4 s | MEDIDO |
| p50 réplica (11 de agosto, A100) | 21,4 s | MEDIDO |
| Δ mediana pareada | 31,95 s (IC 95 % 19,06 – 46,28) | MEDIDO |
| Reducción de p50 | **−60,6 %** | DERIVADO · Wilcoxon pareado por caso |
| Criterio pre-registrado | «baja ≥ 50 %» → **se cumple** | — |

> El p50 de 58,59 s recalculado desde los crudos difiere de los **59,1 s** publicados en informes
> antiguos. Si el documento cita 59,1 s en algún punto, usar el recalculado y decir por qué.

### 7.2 Turnos sin respuesta (n = 70 por corrida)

| Corrida | Fallos | Proporción | IC 95 % Wilson |
| :--- | ---: | ---: | :--- |
| 7 de agosto | 17/70 | 24,29 % | 15,75 – 35,50 % |
| Réplica sobre A100 | **6/70** | **8,57 %** | 3,99 – 17,47 % |
| McNemar exacto | 23 discordantes | **p = 0,035** | — |

> 🔴 **No leer esto como «la unidad gráfica arregló los fallos».** Son fenómenos distintos: los 17
> antiguos son de contrato (fallo de reparación de la generación); los 6 nuevos son de transporte
> (cuatro errores HTTP 502, dos HTTP 422). El acuerdo de identificadores entre corridas es
> **κ = −0,145** —peor que el azar— y **0 de los 17 identificadores antiguos coinciden**. Bajo el
> criterio sellado del proyecto —«si la cuenta cuadra y los identificadores no, el aparato no
> sirve»—, aquí ni siquiera la cuenta cuadra.

### 7.3 Batería de 45 turnos sobre A100

| Modo | Útil | Calla | Muere | Mediana | Mín | Máx |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| General | 14 | 0 | 1 | 15,3 s | 8,1 s | 132,6 s |
| Hemograma | 14 | 0 | 1 | 17,9 s | 12,7 s | 120,5 s |
| Histórico | 15 | 0 | 0 | 24,2 s | 16,4 s | 59,4 s |
| **Total** | **43** | **0** | **2** | — | — | — |

> Con n = 15 por modo, **estas proporciones no sostienen comparación entre modos**: los intervalos
> se solapan ampliamente. Solo se reportan mediana y rango: no hay p90 ni p95. Los dos turnos
> «muertos» son cargas en frío (HTTP 504) y **se muestran, no se recortan**.

### 7.4 Alucinación numérica

| Medición | Observado | Cota superior Wilson 95 % |
| :--- | ---: | ---: |
| Preguntas verificables de la campaña | 0 / 9 | **29,9 %** |
| Rúbrica veterinaria (batería E) | 0 / 30 | **11,4 %** |

> 🔴 **Corrección obligatoria.** El informe interno de la campaña publicó una cota del **16,8 %**
> asumiendo unas 20 preguntas verificables. El fichero de verdad contiene **9**. La cota correcta
> es **29,9 %**: la cifra publicada subestimaba la incertidumbre. Si esa cota entra al documento,
> entra como 29,9 %.

---

## 8 · Tablero de las diez hipótesis pre-registradas

Compendio del pre-registro: `5d6a0a71081e385e…`, **firmado antes de medir**.

| # | Enunciado (abreviado) | Medido | Veredicto sellado |
| :--- | :--- | :--- | :--- |
| H-1 | Decodificación más rápida en A100 pero MBU < 73,7 % | MBU 34,90 % | CONSISTENTE, NO CONFIRMADA |
| H-2 | La sobrecarga de gramática es ≥ 10 ms/token | 0,332 ms/token | **REFUTADA** |
| H-3 | La tasa de fallos no cambia apreciablemente | κ = −0,145: poblaciones distintas | NO EVALUADA ▲ |
| H-4 | Los identificadores de fallo se conservan aunque cambie el recuento | 0 de 17 coinciden | NO EVALUADA, EVALUABLE ▲ |
| H-5 | El p50 por turno baja ≥ 50 % | −60,6 % (Wilcoxon, n = 64) | NO EVALUADA ▲ |
| H-6 | En preguntas de frontera el sistema confabula | reporta ventana truncada, no confabula | REFUTADA en su predicción |
| H-7 | La ventana de contexto efectiva cambió por el salto de memoria | fijada por petición | REFUTADA POR CONFIGURACIÓN |
| H-8 | El tiempo al primer token crece a lo largo de los 15 turnos | campo no expuesto por la API | NO EVALUABLE por el camino B |
| H-9 | La tasa de alucinación numérica es distinta de cero | 0 de 9 · Wilson hasta 29,9 % | NO CONCLUYENTE |
| H-10 | La máquina de aplicación nueva cambia el rendimiento por sí sola | n = 1 máquina | NO EVALUABLE POR DISEÑO |

> ▲ **Instrucción explícita.** Las tres filas marcadas tienen un veredicto sellado que dice «NO
> EVALUADA» y una medición que **ya existe**: la tabla de veredictos se escribió antes de correr
> el brazo de réplica estricta y no se actualizó. **Presenta el tablero tal cual está sellado y
> señala la discrepancia en el texto.** No sustituyas el veredicto sellado por el recalculado.
> Esa honestidad es defendible ante un comité; retocar un pre-registro, no.

---

## 9 · Potencia del diseño — el límite que hay que declarar

| n disponible | Para qué |
| ---: | :--- |
| 9 | preguntas verificables |
| 15 | por modo de uso |
| 45 | baterías |
| 64 | pareado con latencia |
| 70 | réplica de fallos |
| **431** | **necesario para distinguir 10 % de 5 % con potencia del 80 %** |

> Ninguno de los tamaños disponibles alcanza los 431 que harían falta. **Este diseño distingue un
> efecto grande de ninguno, y no distingue uno mediano.** Es la razón cuantitativa de que H-3 y
> H-9 no se sostengan y de que H-5 sí, porque su efecto es enorme.

---

## 10 · Cifras que NO deben aparecer en el capítulo

| Cifra prohibida | Por qué | Qué poner en su lugar |
| :--- | :--- | :--- |
| «25 passed» / «25 pruebas» | Hoy hay 35 archivos de test | El marcador de pendiente |
| «sin aceleración GPU» | Corre sobre A100 | La topología real (§6.8) |
| «latencia media 24,1 s» sin fechar | Medida sobre la configuración anterior | La misma cifra, fechada |
| cota de alucinación «16,8 %» | Asumía ~20 verificables; hay 9 | 29,9 % (Wilson) |
| «Qwen3 4B» | El *runtime* es de 27 mil millones | `qwen3.6:27b-q4_K_M` |
| «59,1 s» de línea base | Publicado en informes antiguos | 54,4 s (recalculado desde crudos) |
| cualquier comparación de tok/s, MBU o TPOT entre unidades gráficas | La configuración anterior no es verificable | Caracterización absoluta de la A100 |

---

## 11 · Inconsistencia conocida en el material de partida

Detectada al montar este paquete, y hay que resolverla en el sentido que se indica:

> El fichero `../../01_preliminares/README.md` propone para el Capítulo VI la numeración de tablas
> `6.14` (una sola tabla para §6.6), `6.15` (usabilidad) y `6.16 – 6.20` (recaracterización). **Esa
> propuesta es incorrecta**, porque §6.6 aporta **dos** tablas numeradas, no una.
>
> **Numeración válida, la que usan los textos de `04`:** §6.6 → Tablas **6.14 y 6.15**; usabilidad
> → Tabla **6.16**; §6.8 → Tablas **6.17 a 6.23** y Figuras **6.30 a 6.41**.
>
> Anótalo en el bloque de inconsistencias de tu salida para que quien actualice la Lista de Tablas
> lo corrija allí también.
