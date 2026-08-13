# Hechos verificados — la única fuente de cifras para el Capítulo VII

> Toda cifra del capítulo debe salir de aquí, **y toda cifra debe llevar la referencia a la
> sección del Capítulo VI que la reporta**. El Capítulo VII no es fuente de ninguna cifra: es su
> resumen.
>
> Marcas: **[MEDIDO]** leído de un artefacto · **[DERIVADO]** calculado a partir de artefactos ·
> **[PENDIENTE]** no disponible: usar marcador, **nunca** estimar.
>
> Verificado el 12 de agosto de 2026 sobre la rama `main`, commit `f9deedb`.

---

## 1 · Las cifras del Capítulo VI que este capítulo puede citar

Son las únicas. Cada una con la sección que la reporta.

| Cifra | Valor | Sección que la reporta | Marca |
| :--- | ---: | :--- | :---: |
| Latencia media de inferencia del clasificador | 28,73 ms | §6.5 | MEDIDO |
| Latencia mediana por turno, configuración vigente | 21,4 s | §6.8 | MEDIDO |
| Latencia mediana por turno, configuración anterior | 54,4 s | §6.8 | MEDIDO |
| Reducción de la latencia mediana | −60,6 % | §6.8 | DERIVADO |
| Turnos sin respuesta, antes → después | 24,3 % → 8,6 % | §6.8 | MEDIDO |
| Contraste de esa proporción | McNemar exacto, p = 0,035 | §6.8 | MEDIDO |
| Acuerdo de identificadores de fallo entre corridas | κ = −0,145; 0 de 17 coinciden | §6.8 | MEDIDO |
| Sobrecarga medida de la decodificación por gramática | 0,332 ms/token | §6.8 | MEDIDO |
| Valor que la literatura le atribuía | ≥ 10 ms/token | §1.1.3.7 y §6.8 | — |
| Factor de discrepancia | ~44× | §6.8 | DERIVADO |
| Cota superior de alucinación, campaña | 29,9 % (Wilson, 0 de 9) | §6.8 | DERIVADO |
| Cota superior de alucinación, rúbrica veterinaria | 11,4 % (Wilson, 0 de 30) | §6.4.5 | DERIVADO |
| Observaciones para acotar al 5 % / al 1 % | ~60 / ~300 | §6.8 | DERIVADO |
| Observaciones por grupo para distinguir 10 % de 5 % | 431 | §6.8 | DERIVADO |
| Tamaños de muestra disponibles | 9 a 70 | §6.8 | MEDIDO |
| Preguntas de reproducibilidad sin constancia | 11 de 15 | §6.8 | MEDIDO |
| Compuertas técnicas de vigilancia aprobadas | 5 de 5 | §6.6 | MEDIDO |
| Cohorte del reporte poblacional | 200 registros | §6.6 | MEDIDO |
| Señales aprobadas / en advertencia | 3 / 2 | §6.6 | MEDIDO |
| Tasa de geocodificación | nula | §6.6 | MEDIDO |
| Salida de la suite de pruebas del backend | ⚠️ **[PENDIENTE]** | §6.5 | — |

> 🔴 **El dato pendiente.** §7.6 dice hoy «25 pruebas superadas en el backend». Esa cifra está
> desactualizada: hoy hay 35 archivos de test y la suite no se ha vuelto a correr. **No escribas
> ningún número.** Remite a §6.5, que es donde se reporta: «la suite automatizada del backend,
> cuyo resultado se reporta en §6.5». Así el capítulo queda correcto aunque la cifra se cierre
> después.

---

## 2 · §7.6 — La frase que contradice al Capítulo VI 🔴

> **Texto actual, último párrafo de §7.6:** «Las pruebas técnicas de la preparación operativa
> incluyen: 25 pruebas superadas en el backend, una latencia media de inferencia de 28.73 ms y la
> validación funcional de los mecanismos de seguridad. **La limitación más relevante en términos
> de funcionamiento está relacionada con la generación conversacional, ya que el modelo de
> lenguaje se ejecuta sin aceleración GPU, lo que da lugar a tiempos de respuesta más lentos en el
> chat.**»

Dos errores en una frase: la cifra de pruebas y la afirmación sobre la aceleración gráfica.

> **Reemplazo completo (dos párrafos):**
>
> «Las pruebas técnicas de la preparación operativa incluyen la suite automatizada del backend
> —cuyo resultado se reporta en §6.5—, una latencia media de inferencia del motor de clasificación
> de 28,73 milisegundos y la validación funcional de los mecanismos de seguridad conversacional.
>
> La generación conversacional se ejecuta sobre un nodo dedicado con aceleración por unidad de
> procesamiento gráfico, separado del nodo de aplicación y comunicado con él por dirección interna
> estática. Tras esa migración, la latencia mediana por turno se sitúa en 21,4 segundos y la
> proporción de turnos sin respuesta en el 8,6 % (§6.8). La limitación operativa más relevante ya
> no es la velocidad de generación sino la naturaleza interrumpible del nodo de inferencia: opera
> bajo una modalidad de contratación en la que el proveedor puede reclamar la capacidad sin previo
> aviso, y el sistema no dispone actualmente de un mecanismo automático de rearranque. La
> arquitectura mitiga parcialmente este riesgo, ya que la indisponibilidad del nodo de inferencia
> no afecta al análisis hematológico, la consulta de resultados ni el historial, que permanecen
> operativos.»

**Además, en §7.6 párrafo 1**, donde se enumeran los contenedores: precisar que el servidor de
modelos de lenguaje corre en el nodo con unidad de procesamiento gráfico, no junto al resto.

---

## 3 · §7.3 — Las cinco limitaciones que faltan 🔴

Las siete actuales —especie canina, calidad del hemograma de entrada, etiquetas con escaso
respaldo, incompatibilidad de etiquetas del Dog Aging Project, alcance de la validación clínica,
carácter piloto de la validación conversacional, y muestra de conveniencia en usabilidad— **son
correctas y se mantienen íntegras**.

> **Texto para añadir tras la séptima limitación:**
>
> «En octavo lugar, la configuración de *runtime* conversacional anterior no es reproducible. El
> protocolo con que se midió no registró el modelo empleado, su compendio, su cuantización, la
> versión del servidor de modelos, el controlador ni la unidad de procesamiento gráfico exacta;
> de quince preguntas de reproducibilidad, once no constan o constan parcialmente. En consecuencia,
> las cifras de rendimiento físico presentadas en §6.8 constituyen una caracterización absoluta de
> la configuración vigente y **no una comparación entre unidades de procesamiento gráfico**, y la
> mejora de latencia documentada es atribuible al conjunto de la migración y no aisladamente al
> cambio de hardware.
>
> En noveno lugar, la evaluación de fabricación numérica se apoya en un número reducido de
> preguntas verificables. La ausencia de discrepancias observadas acota la tasa por debajo del
> 29,9 % con un 95 % de confianza sobre nueve preguntas verificables, y por debajo del 11,4 % sobre
> las treinta preguntas de la rúbrica veterinaria. Ninguna de las dos cotas permite afirmar que la
> tasa sea nula: alcanzar una cota del 5 % requeriría del orden de sesenta observaciones, y del
> 1 %, alrededor de trescientas.
>
> En décimo lugar, el diseño experimental de la campaña de caracterización carece de potencia para
> resolver efectos de magnitud intermedia. Distinguir una tasa del 10 % de una del 5 % con una
> potencia del 80 % requeriría cuatrocientas treinta y una observaciones por grupo, frente a los
> tamaños disponibles de nueve a setenta. El diseño distingue un efecto grande de la ausencia de
> efecto y no distingue uno intermedio, de modo que los resultados no concluyentes de la campaña
> deben interpretarse como una limitación del diseño y no como evidencia de ausencia de efecto.
>
> En undécimo lugar, el nodo de inferencia opera sobre una instancia de cómputo interrumpible, cuya
> disponibilidad depende de la capacidad excedente del proveedor y puede ser reclamada sin previo
> aviso. Durante el desarrollo se registró además un evento real de agotamiento de capacidad zonal
> que impidió temporalmente el arranque de varias familias de máquinas. El sistema no dispone de un
> mecanismo automático de rearranque ante una reclamación de la instancia.
>
> En duodécimo lugar, el modelo de lenguaje empleado en la configuración anterior permanece
> instalado en el servidor de inferencia, y la comprobación presente en el código no impide su uso.
> Se verificó que ninguna de las respuestas registradas en la campaña procede de él, mediante la
> comprobación del identificador de modelo en la totalidad de las respuestas emitidas, pero la
> garantía es de verificación posterior y no de imposibilidad por diseño.»

---

## 4 · §7.4 — Los tres hallazgos inesperados que faltan

Los cinco actuales —variabilidad del juicio veterinario, sobredetección del leucograma de estrés,
conservadurismo en policitemia, eficacia de las reglas deterministas frente al modelado
probabilístico, y las peticiones de la encuesta de usabilidad— **son buenos y se mantienen**.

> **Texto para añadir:**
>
> «El sexto hallazgo procede de la ablación de la decodificación restringida por gramática. Se
> había atribuido a esta técnica un sobrecosto de al menos diez milisegundos por token, valor
> coherente con la literatura consultada, y se esperaba que explicara buena parte del residual de
> rendimiento observado en la configuración anterior. La medición controlada arrojó un sobrecosto
> de 0,332 milisegundos por token —aproximadamente cuarenta y cuatro veces menor que el valor de
> referencia—, de modo que la hipótesis quedó refutada y el residual atribuido a la gramática
> resultó tener otro origen, que este diseño no identifica. El hallazgo ilustra que un valor
> publicado para un despliegue no es trasladable a otro sin medición propia.
>
> El séptimo hallazgo es que una reducción de la tasa de fallos puede ocultar un cambio de régimen
> en lugar de una corrección. La proporción de turnos sin respuesta descendió del 24,3 % al 8,6 %
> tras la migración, un resultado que invitaba a leerse como corrección de los errores previos. El
> análisis de identificadores mostró, sin embargo, que ninguno de los diecisiete casos que fallaban
> antes vuelve a fallar, y que el acuerdo entre ambos conjuntos de fallos es peor que el azar: se
> trata de dos fenómenos distintos —fallos de contrato en la reparación de respuestas frente a
> fallos de transporte— y no de la resolución de un conjunto identificado de errores. El criterio
> de aceptación que el proyecto había fijado de antemano, según el cual la coincidencia de
> recuentos no basta si no coinciden los identificadores, fue lo que permitió detectarlo.
>
> El octavo hallazgo es que la política de arranque a prueba de fallos del nodo de inferencia se
> validó de forma no planificada. Dicha política exige que el nodo verifique el hardware, el
> controlador, la versión del servidor y el compendio del modelo antes de atender tráfico, y que se
> apague si alguna comprobación no se satisface. Al sustituir la unidad de procesamiento gráfico,
> la cadena de validación —anclada al modelo de hardware anterior en dos capas independientes—
> apagó la máquina en dos ocasiones antes de que se ampliara el contrato. El comportamiento fue
> exactamente el diseñado, y constituye la evidencia más directa disponible de que el mecanismo de
> protección opera.»

---

## 5 · §7.2 — Las dos filas de la Tabla 7.1

El resto de la tabla y el párrafo de cierre —«se considera que se han cumplido los cinco objetivos
específicos… el OE2 se declara alcanzado con limitaciones»— **se mantienen**.

**OE4 · vigilancia comunitaria.** Hoy dice: «Módulo de vigilancia con señales agregadas, reporte
poblacional funcional y advertencias de que no representa prevalencia ni diagnóstico confirmado.»
Ahora que §6.6 existe, hay que citarla:

> «Módulo de vigilancia con cinco compuertas técnicas aprobadas y reporte poblacional sobre una
> cohorte de 200 registros con tres señales aprobadas y dos en advertencia; la limitación
> geográfica —tasa de geocodificación nula— se declara explícitamente (§6.6).»

**OE5 · capa conversacional.** Hoy dice: «Asistente LLM/RAG con corpus curado, guardrails,
seguridad 30/30, exactitud correcta o parcial de 83.3 %, concordancia veterinaria de kappa 0.841 y
reducción de prompt injection de 61 a 1 fallo tras refuerzo.» Añadir la evidencia de agosto:

> «…y caracterización posterior del *runtime* con diez hipótesis pre-registradas, que documenta una
> reducción del 60,6 % en la latencia mediana por turno y del 24,3 % al 8,6 % en la proporción de
> turnos sin respuesta (§6.8).»

> ⚠️ Al reproducir la fila de OE5, corrige de paso las cifras al formato del documento: `83,3 %` y
> `κ 0,841`, con coma decimal.

---

## 6 · §7.5 — Dos recomendaciones que ya se cumplieron

> **Texto actual, párrafo 4:** «Deberían considerarse para su implementación las siguientes
> mejoras en la experiencia del usuario, identificadas durante la encuesta […]: 1) **aumentar la
> velocidad del chat**, 2) **añadir una memoria conversacional controlada**, 3) fijar la leyenda de
> colores en su lugar, 4) añadir rangos normales a los valores, 5) añadir una función de
> exportación a través de WhatsApp o correo electrónico, 6) añadir un modo de alto contraste,
> 7) mejorar el recorrido de bienvenida, 8) ampliar el glosario de unidades y términos técnicos.»

Los puntos 1 y 2 **ya se ejecutaron** y el Capítulo VI lo demuestra.

> **Reemplazo del párrafo:**
>
> «De las mejoras solicitadas por los participantes, dos se abordaron antes del cierre del
> proyecto: la velocidad del asistente, cuya latencia mediana por turno se redujo un 60,6 % tras la
> migración del *runtime* (§6.8), y la continuidad conversacional, reforzada mediante la resolución
> de enunciados elípticos y el completado determinista de los datos ya registrados (§5.10). Quedan
> pendientes de implementación: fijar la leyenda de colores, mostrar los intervalos de referencia
> junto a cada valor, habilitar la exportación por mensajería o correo electrónico, incorporar un
> modo de alto contraste, corregir el recorrido de bienvenida y ampliar el glosario de unidades y
> términos técnicos. Varias de estas quedan cubiertas por el manual de usuario descrito en §5.7.»

> **Párrafo nuevo con los pendientes técnicos**, que hoy no están en ninguna parte del documento y
> son recomendaciones legítimas para la continuación:
>
> «Desde el punto de vista operativo se recomienda, en orden de prioridad: incorporar un mecanismo
> automático de rearranque del nodo de inferencia ante la reclamación de la instancia
> interrumpible; restituir el nodo de aplicación a su dimensionamiento previo tras la degradación
> temporal impuesta por el evento de capacidad zonal; explotar la telemetría de verificación de
> citas ya instrumentada para calibrar el umbral de aceptación de fuentes, que constituye la
> dimensión con mayor margen de mejora según la rúbrica veterinaria; reducir la clase residual de
> respuestas que agotan los intentos de reparación y recurren al último recurso; y aprovechar la
> ventana de contexto ampliada que permite la configuración vigente, actualmente infrautilizada.»

**Y acoger una frase trasladada.** §6.4.2 contiene hoy la frase «hallazgo que se entrega al equipo
de desarrollo», sobre un mensaje de fuera de ámbito que se lee como problema técnico. El manual
prohíbe sugerencias en el capítulo de resultados, de modo que **esa recomendación se recoloca
aquí**, redactada como recomendación: revisar la formulación del mensaje de rechazo por fuera de
ámbito para que no se interprete como un fallo del sistema.

> ⚠️ Escríbela solo si el Capítulo VI ya se corrigió. Si no, quedaría duplicada. Anótalo en el
> registro de cambios en cualquier caso.

**Los párrafos 1, 2, 3 y 5 de §7.5 se mantienen íntegros** —validación clínica ampliada,
ampliación del corpus, más preguntas de evaluación, y la separación entre modo ciudadano y modo
veterinario—. Este último es una buena recomendación de continuidad y conviene no diluirla.

---

## 7 · §7.7 — La sostenibilidad económica que falta

§7.7 cubre sostenibilidad técnica, del componente de inteligencia artificial, del corpus,
operativa y clínica. **No cubre la económica**, y ahora el sistema tiene un costo recurrente real.

> **Párrafo para añadir tras el de sostenibilidad operativa:**
>
> «La sostenibilidad económica del sistema está condicionada por el nodo de inferencia. A
> diferencia del resto de la plataforma, cuyo costo de cómputo es modesto y predecible, la
> generación conversacional requiere una unidad de procesamiento gráfico cuyo costo por hora
> domina el gasto operativo. Se adoptaron tres decisiones para acotarlo: la contratación en
> modalidad interrumpible, que reduce sustancialmente la tarifa a cambio de renunciar a la garantía
> de continuidad; el encendido bajo demanda del nodo en lugar de su operación permanente; y la
> separación arquitectónica que permite mantener operativo el resto del sistema con el nodo de
> inferencia apagado. La continuidad del servicio conversacional más allá del ámbito académico
> exige, por tanto, una decisión explícita sobre el modelo de financiación del cómputo, que puede
> pasar por el uso de un modelo de menor tamaño, por la contratación de generación como servicio
> externo, o por la limitación del asistente a franjas de disponibilidad definidas.»

> Nota: este párrafo **no da ninguna cifra de costo**, y es deliberado. La cifra real de
> facturación no está disponible en este paquete. Si el Capítulo II acaba incorporándola, se puede
> remitir a §2.5.1; mientras tanto, el párrafo se sostiene sin ella.

---

## 8 · §7.1 — Dos detalles

**Media frase de cierre.** El párrafo 3 evalúa el proyecto desde cuatro perspectivas: técnica,
clínica, conversacional y de usabilidad. Con §6.8 incorporada, conviene cerrarlo así:

> «…y no se detectaron alucinaciones en el conjunto de prueba. La configuración de ejecución del
> componente conversacional fue posteriormente caracterizada mediante una campaña con hipótesis
> registradas antes de medir, cuyos resultados —incluida la refutación de una de las hipótesis de
> partida— se presentan en §6.8.»

**Un punto doble.** En el mismo párrafo 3: «…técnica, clínica, conversacional y de
usabilidad**..**». Corregir.

---

## 9 · Lo que NO se toca

| Sección | Estado |
| :--- | :--- |
| §7.1 conclusiones | ✅ íntegra, salvo la media frase y el punto doble |
| §7.2 y el resto de la Tabla 7.1 | ✅ íntegros, salvo las filas de OE4 y OE5 |
| §7.3, las **siete** limitaciones actuales | ✅ **íntegras**; solo se añaden cinco |
| §7.4, los **cinco** hallazgos actuales | ✅ **íntegros**; solo se añaden tres |
| §7.5, párrafos 1, 2, 3 y 5 | ✅ íntegros |
| §7.6, salvo el último párrafo y la precisión del primero | ✅ |
| §7.7, salvo la adición del párrafo económico | ✅ |

---

## 10 · Cifras que NO deben aparecer

| Cifra prohibida | Por qué | Qué poner en su lugar |
| :--- | :--- | :--- |
| «25 pruebas superadas» | Desactualizada; hoy hay 35 archivos de test | Remisión a §6.5, sin número |
| «se ejecuta sin aceleración GPU» | Corre sobre A100 | La topología real |
| «Qwen3 4B» | El *runtime* es de 27 mil millones | El modelo sellado, o ninguna mención |
| cota de alucinación «16,8 %» | Asumía ~20 verificables; hay 9 | 29,9 % |
| Cualquier cifra que no esté en el Capítulo VI | El VII resume, no amplía | Meterla antes en el VI |
