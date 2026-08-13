# Pies de figura — HemoVet · RECARACTERIZACION-A100

**Figura E4.** La puerta de aceptación: coincidencia de identificadores de fallo. Conjuntos de identificadores de fallo de ambas corridas y acuerdo entre ellas. n = 70. [MEDIDO]. Fuente: 04_trazas/turns_replica_estricta.ndjson.

> *Nota de lectura.* Criterio sellado del proyecto, literal: «si la cuenta cuadra y los ids no, el aparato no sirve». Aquí ni siquiera cuadra la cuenta. Un κ negativo significa acuerdo peor que el azar. Esta figura NO debe leerse como que la GPU arregló los fallos: los 17 antiguos son de contrato (generation_repair_failed) y los 6 nuevos son timeouts — fenómenos distintos. Confusores vivos: el encadenado de sesión del original no consta (D-2) y el digest del modelo del 7-ago tampoco.

**Figura D7.** Tasa de alucinación numérica y su intervalo de confianza. Punto observado en cero con la banda de Wilson del 95 %. n = 9. [DERIVADO]. Fuente: 02_fixtures/verdad.json, 04_trazas/turns.ndjson.

> *Nota de lectura.* Cero casos observados NO demuestra ausencia: el diseño solo excluye tasas superiores al 29,9 %. Con n = 9 preguntas verificables la cota es ancha; acotarla al 5 % exigiría del orden de 60 observaciones, y al 1 %, unas 300. Esta figura existe precisamente para impedir que un cero se lea como «no alucina». DISCREPANCIA: el informe publico una cota del 16,8 % asumiendo ~20 preguntas verificables; verdad.json contiene 9, y la cota correcta es 29,9 %. La cifra publicada subestimaba la incertidumbre.

**Figura A1.** Ventanas de GPU: lo que el log registra y lo que sólo consta en las trazas. Duración de cada ventana de encendido; entre ellas la instancia estuvo TERMINATED. n = 6. [MEDIDO]. Fuente: 99_operacion/log_instancia.md, 04_trazas/turns.ndjson, 04_trazas/turns_replica_estricta.ndjson.

> *Nota de lectura.* El log de operación sólo registra encendido y apagado de tres ventanas. De las otras tres no consta ni la hora de arranque ni la de apagado, así que su duración NO es recuperable: lo que se dibuja con trama es el intervalo entre la primera y la última marca de tiempo de sus turnos, que es una cota INFERIOR —no incluye el arranque de la VM ni la carga del modelo, que en el arranque en frío medido en D2 costó más de dos minutos—. Los dos totales no se suman en uno solo porque no son la misma magnitud.

**Figura A2.** Composición del corpus de evidencia previa. Distribución de los 208 ficheros por directorio de primer nivel. n = 208. [MEDIDO]. Fuente: 01_auditoria_previa/inventario.ndjson.

> *Nota de lectura.* _CONTIENE_SECRETOS va con trama: hasheado y contado, jamás muestreado. 208/208 hashes verificados intactos tras la copia.

**Figura A4.** Reconstrucción del protocolo del 7-ago: semáforo de las quince preguntas. Estado de recuperación de cada una de las quince preguntas del protocolo. n = 15. [MEDIDO]. Fuente: 01_auditoria_previa/protocolo_antiguo_reconstruido.md.

> *Nota de lectura.* «NO CONSTA» es un resultado, no un fallo del análisis. Dos filas decidieron la campaña: los 17 ids SÍ constan (por eso H-4 fue evaluable) y el digest del modelo NO consta.

**Figura A5.** Veredicto doble de comparabilidad. Veredicto por ámbito; la comparabilidad no es única. n = 2. [DERIVADO]. Fuente: 01_auditoria_previa/veredicto_comparabilidad.md.

> *Nota de lectura.* La física de la L4 no es verificable: toda cifra de decode, MBU o TPOT de esta tesis es caracterización absoluta de la A100, no comparación entre GPU.

**Figura B1.** Ficha de identidad del sistema medido. Sello bajo el que se midió todo el capítulo. n = 8. [MEDIDO]. Fuente: 06_analisis/fase2_canario_y_ic.json.

> *Nota de lectura.* Dos correcciones que la medición impuso sobre el plan: el peso real es 17 420 432 739 B (16,224 GiB / 17,420 GB), no los 16,93 GB declarados; y Ollama es 0.32.6, no 0.32.5.

**Figura B3.** Verificación de identidad de modelo en cada respuesta. Origen del modelo en cada respuesta registrada. n = 115. [MEDIDO]. Fuente: 04_trazas/turns.ndjson, 04_trazas/turns_replica_estricta.ndjson.

> *Nota de lectura.* Aquí cero SÍ es censo, no muestra: se verificó el campo model en TODAS las respuestas, no en un subconjunto. Es distinto del caso de D7, donde cero necesita intervalo. La comprobación fue necesaria porque el 4B sigue instalado y la guarda del código no protege.

**Figura B4.** Modelos presentes en el servidor de producción. Convivencia del modelo sellado con el 4B. n = 2. [MEDIDO]. Fuente: 06_analisis/fase2_canario_y_ic.json.

> *Nota de lectura.* Que el 4B esté instalado no implica que se usara: ver B3, donde se verifica respuesta a respuesta.

**Figura C1.** Techos de decodificación y rendimiento medido. Rendimiento medido frente al techo nominal y a la banda alcanzable. n = 100. [DERIVADO]. Fuente: 05_derivados/tpot_serie_n100.json.

> *Nota de lectura.* Techo = ancho de banda / tamaño del modelo. El tamaño se toma en GB decimales (17,42 GB), no en GiB (16,22 GiB): confundirlos infla el techo un 7,4 %. La L4 NO aparece: su física no es verificable.

**Figura C2.** Distribución del tiempo por token de salida (TPOT). Histograma con los 100 puntos individuales bajo el eje y la banda del IC bootstrap. n = 100. [MEDIDO]. Fuente: 05_derivados/tpot_serie_n100.json.

> *Nota de lectura.* Un CV del 0,65 % NO significa que el usuario vea esta estabilidad: son 100 generaciones consecutivas con el modelo ya cargado, temperature 0, top_k 1, semilla fija y sin concurrencia. Mide la máquina en su mejor caso, no el servicio. La serie de origen lleva ADVERTENCIA_DE_PROCEDENCIA: el arnés de la Fase 2 no la volcó a disco y estos 100 valores se rescataron de su salida estándar, de modo que su cadena de custodia es más débil que la del resto de artefactos.

**Figura C4.** Utilización del ancho de banda de memoria (MBU) en contexto. MBU medido con su IC sobre el rango documentado. n = 100. [DERIVADO]. Fuente: 05_derivados/tpot_serie_n100.json.

> *Nota de lectura.* Un MBU bajo NO indica ineficiencia del despliegue: el MBU baja al subir el ancho de banda porque la sobrecarga fija por token no escala. Enlaza con H-1, «consistente, no confirmada».

**Figura C6.** Lo predicho frente a lo medido: la sobrecarga de gramática. Las tres referencias sobre un eje común de ms/token. n = 60. [MEDIDO]. Fuente: 05_derivados/ablacion_gramatica.json.

> *Nota de lectura.* El residual de 20,20 ms/token atribuido a la L4 NO era la gramática; dónde estaba sigue abierto. Esto no dice que la literatura esté mal: dice que en ESTE despliegue no aplica.

**Figura C8.** Prefill y decodificación sobre el mismo eje. Las dos fases sobre el mismo eje: ambas se miden en tok/s. n = 100. [MEDIDO]. Fuente: 06_analisis/fase2_canario_y_ic.json.

> *Nota de lectura.* Comparten eje porque comparten unidad, pero NO son comparables como rendimiento: el prefill se midió con prompts de 17–22 tokens y a esa escala lo domina la sobrecarga fija, así que la cifra está inflada respecto a lo que daría un prompt largo. Que el prefill supere al decode es lo esperado —procesa el prompt en paralelo mientras la decodificación va token a token— y no significa que el prefill sea el punto rápido del sistema.

**Figura D1.** Desenlace de los turnos por modo. Reparto útil/calla/muere con el IC de Wilson de la proporción de útiles. n = 45. [MEDIDO]. Fuente: 04_trazas/turns.ndjson.

> *Nota de lectura.* Con n = 15 por modo, estas proporciones NO sostienen comparación entre modos: los intervalos se solapan ampliamente.

**Figura D2.** Latencia por posición de turno y modo. Los 15 turnos de cada modo; marcador distinto por modo (codificación secundaria). n = 45. [MEDIDO]. Fuente: 04_trazas/turns.ndjson.

> *Nota de lectura.* La línea conecta observaciones consecutivas; NO modela una tendencia ni hay ajuste. Los dos turnos con X son cargas en frío (HTTP 504) y se muestran, no se recortan.

**Figura D3.** Distribución de latencia por modo. Caja con los 15 puntos superpuestos, en dos paneles: con y sin los turnos de carga en frío. n = 45. [MEDIDO]. Fuente: 04_trazas/turns.ndjson.

> *Nota de lectura.* Con n = 15 solo se reportan mediana y rango: no hay p90 ni p95. Los puntos van superpuestos porque una caja sobre 15 observaciones oculta más de lo que muestra.

**Figura D9.** El hemograma de referencia. Cada parámetro situado sobre su rango de referencia normalizado. n = 18. [MEDIDO]. Fuente: 02_fixtures/fixture_hemograma.json.

> *Nota de lectura.* Describe un fixture de PRUEBA (mascota b573826b…, 'hola'/'test'), no un caso clínico real, y no constituye diagnóstico. Es la misma mascota que usó la línea base, lo cual es lo mejor posible para la comparabilidad.

**Figura E1.** Latencia por caso: L4 → A100. Una línea por id_caso; medianas destacadas en negro. n = 64. [MEDIDO]. Fuente: 04_trazas/turns_replica_estricta.ndjson.

> *Nota de lectura.* La mejora de latencia es atribuible al CONJUNTO de la migración, no aisladamente a la GPU. Desviaciones declaradas: D-1 (no es réplica byte a byte, el original no registró prompts renderizados ni digest) y D-2 (el encadenado de sesión del original no consta).

**Figura E2.** Distribución de las diferencias pareadas. Diferencias por caso con la línea de cero marcada. n = 64. [DERIVADO]. Fuente: 04_trazas/turns_replica_estricta.ndjson.

> *Nota de lectura.* Wilcoxon de rangos con signo, pareado por id_caso. El IC no cruza cero: es el sustento de H-5. El criterio pre-registrado era «baja ≥ 50 %» y se cumple.

**Figura E3.** Función de distribución acumulada de la latencia. Ambas distribuciones completas, no solo sus medianas. n = 64. [MEDIDO]. Fuente: 04_trazas/turns_replica_estricta.ndjson.

> *Nota de lectura.* Las dos series NO comparten protocolo: ver desviaciones D-1 y D-2 en E1. La línea base recalculada desde los crudos da p50 58,59 s frente a los 59,1 s publicados en los informes antiguos.

**Figura E5.** Naturaleza de los fallos: dos fenómenos distintos. Dos gráficos separados: la separación física ES el argumento. n = 23. [MEDIDO]. Fuente: 04_trazas/turns_replica_estricta.ndjson.

> *Nota de lectura.* Nunca apilar ambos en la misma barra: sugeriría continuidad entre fenómenos que no la tienen.

**Figura F1.** Tablero de las diez hipótesis pre-registradas. Enunciado leído del pre-registro firmado, veredicto leído del informe, cifra recalculada desde los datos. n = 10. [DERIVADO]. Fuente: 03_hipotesis/preregistro.md, 07_informes/INFORME_RECARACTERIZACION_A100.md.

> *Nota de lectura.* Hash del pre-registro: 5d6a0a71081e385e… — firmado ANTES de medir. Las tres filas marcadas con ▲ tienen un veredicto sellado que dice «NO EVALUADA» y una medición que ya existe: la tabla de veredictos del informe se escribió ANTES de correr el brazo de réplica estricta y no se actualizó después. La figura no sustituye el veredicto sellado por el mío; lo muestra tal cual y señala la discrepancia, que es un encargo pendiente sobre el informe. «No evaluable» tampoco significa «no hay efecto»: significa que este diseño no puede verlo. Los enunciados van recortados a 96 caracteres; el íntegro está en el pre-registro.

**Figura F4.** Potencia del diseño. n necesario por grupo frente a la diferencia detectable (α = 0,05 bilateral, potencia 80 %). n = 6. [DERIVADO]. Fuente: 04_trazas/turns.ndjson.

> *Nota de lectura.* La curva se detiene en 10 puntos porque con una tasa base del 10 % no existe una diferencia mayor. Ninguno de los tamaños de muestra disponibles alcanza los 431 que harían falta para distinguir 10 % de 5 % con potencia del 80 %: este diseño distingue un efecto grande de ninguno, y no distingue uno mediano. Es la razón cuantitativa de que H-3 y H-9 no se sostengan y de que H-5 sí, porque su efecto es enorme.

**Figura A3.** Qué registra cada instrumento: cobertura comparada. Presencia y poblamiento real de cada capacidad de medida en los dos instrumentos; la trama diagonal marca ausencia. n = 17. [MEDIDO]. Fuente: 01_auditoria_previa/copia/bateria_latencias_2026-08-07.jsonl, 04_trazas/turns.ndjson.

> *Nota de lectura.* La cobertura NO crece de forma monótona: el instrumento antiguo registraba ttfb_s, etapas, duración por etapa, eventos SSE y reparaciones —70/70 turnos— y el nuevo no registra ninguna. El nuevo aporta trazabilidad (hashes, sello de corrida, verificabilidad) que el antiguo no tenía. Son instrumentos distintos, no uno mejor. Ninguno de los dos captura los crudos de Ollama, que es la carencia que bloquea X1, X3 y H-8.

**Figura B2.** Las limitaciones declaradas y en qué momento se declararon. Cada limitación sellada en 07_informes/LIMITACIONES.md, con el momento en que se declaró y las hipótesis que menciona. n = 17. [MEDIDO]. Fuente: 07_informes/LIMITACIONES.md.

> *Nota de lectura.* El catálogo de figuras planificaba «18 confusores». Esa cifra aparece una sola vez en toda la campaña, en la tabla de presupuesto de 99_operacion/log_instancia.md («Fase 1 · sellado + 18 confusores»), y ningún fichero llega a enumerarlos: los códigos E-n del corpus antiguo son identificadores de EXPERIMENTO, no de confusor. Lo que sí consta sellado son 17 limitaciones, y es lo que se dibuja. 6 de ellas se declararon sólo después de medir: el pre-registro no las anticipó.

**Figura C3.** Distribución bootstrap de la mediana del TPOT. 10 000 remuestreos con reposición de los 100 TPOT medidos, semilla 20260811. n = 100. [DERIVADO]. Fuente: 05_derivados/tpot_serie_n100.json.

> *Nota de lectura.* La distribución es multimodal a propósito de la aritmética, no del sistema: la mediana de un remuestreo de 100 valores discretos sólo puede caer en un número reducido de valores, y por eso el histograma es escalonado en vez de acampanado. El intervalo es estrechísimo (CV 0,65 %) porque mide la precisión de la mediana bajo condiciones fijas y un único modelo cargado: NO es un intervalo sobre el rendimiento que vería un usuario. La serie de origen lleva ADVERTENCIA_DE_PROCEDENCIA: el arnés no la volcó a disco y se rescató de la salida estándar.

**Figura C5.** Ablación de la gramática: los dos brazos por separado. Mediana y rango intercuartílico de cada brazo, 30 medidas por brazo. Eje truncado y marcado. n = 60. [MEDIDO]. Fuente: 05_derivados/ablacion_gramatica.json.

> *Nota de lectura.* No es un diagrama de violín ni de caja completo: los 60 valores crudos NO se persistieron, sólo mediana e IQR por brazo, así que se dibuja exactamente eso. Los IQR se solapan. Ambos brazos toparon en num_predict = 200 con done_reason «length», de modo que esto mide el coste de la gramática en decodificación pura y NO en la terminación, que es donde la evidencia antigua situaba el fallo duro.

**Figura C7.** Determinismo intra-máquina: 20 prompts × 5 repeticiones. Cada celda es una generación; el color uniforme indica que todas las repeticiones de un prompt produjeron el mismo hash. n = 100. [DERIVADO]. Fuente: 06_analisis/fase2_canario_y_ic.json.

> *Nota de lectura.* Los hashes celda a celda NO se persistieron: lo que consta es el agregado «0 prompts con más de un hash» sobre 20. La rejilla es la representación fiel de ese agregado, no 100 hashes registrados de forma independiente. El fixture planificaba 10 repeticiones y la corrida ejecutó 5. Esto NO demuestra equivalencia entre máquinas: §6.2 quedó cancelada porque no constan los prompts renderizados del 7-ago.

**Figura D4.** La frontera de la ventana, turno a turno y modo a modo. Los nueve turnos de sonda de frontera: tres posiciones × tres modos. n = 9. [MEDIDO]. Fuente: 04_trazas/turns.ndjson.

> *Nota de lectura.* Los nueve turnos de frontera respondieron: ninguno murió ni calló. El tamaño de la ventana NO se mide aquí — se infiere de una sola observación (GENERAL-14 devuelve el turno 2 como «primera pregunta»), y con n = 1 y history_messages_count nulo en las nueve celdas no sostiene una cifra. Por eso la anotación dice «inferida».

**Figura D5.** Qué responde el sistema al preguntarle por el principio de la conversación. Texto literal de los tres turnos de frontera del modo GENERAL. n = 3. [MEDIDO]. Fuente: 04_trazas/turns.ndjson.

> *Nota de lectura.* H-6 predecía confabulación y no la hubo: el sistema reporta lo que conserva. El fallo real es distinto y más sutil — no declara el límite de su ventana. GENERAL-14 responde «¿De qué está compuesto?», que fue el turno 2 y no el 1, y lo hace prologado con «según el historial de esta sesión»: un error factual expresado con la misma seguridad que un acierto. Eso es lo que un usuario clínico no puede detectar. Los textos van truncados a 250 caracteres; el íntegro está en la tabla gemela.

**Figura D6.** Verificación mecánica contra la tabla de verdad sellada. Comprobación literal de si la respuesta contiene el valor sellado en 02_fixtures/verdad.json antes de medir. n = 9. [MEDIDO]. Fuente: 02_fixtures/verdad.json, 04_trazas/turns.ndjson.

> *Nota de lectura.* «NO CONTIENE» no es sinónimo de alucinación y la figura no lo afirma. HEMO-04 no contiene el rango [5,5 · 16,9] porque respondió otra cosa —enumeró los 18 parámetros— sin afirmar ningún rango falso. HEMO-08 dice «10^12/L» donde el fixture selló «x10⁶/µL»: es la misma magnitud en otro convenio, no un número inventado. HEMO-01 murió y no entregó texto. De ahí que el denominador efectivo de la tasa de alucinación de D7 sea aún menor que 9, y su intervalo aún más ancho.

**Figura D8.** Cobertura real de la rúbrica de cinco ejes. Estado de cada eje de la rúbrica de juicio; la trama diagonal marca lo no puntuado. n = 5. [MEDIDO]. Fuente: 07_informes/LIMITACIONES.md, 02_fixtures/criterios.md, 03_hipotesis/preregistro.md.

> *Nota de lectura.* Éste es un resultado incómodo y se dibuja igual de bien que los demás. De los cinco ejes previstos sólo el 1 se puntuó. Los ejes 2 y 5 son inevaluables por una carencia del instrumento —la API no devuelve el prompt renderizado ni el recuento de mensajes—, y de los ejes 3 y 4 no consta definición operativa en ningún artefacto sellado, pese a que criterios.md los invoca. Puntuarlos ahora sería juicio disfrazado de medida.

**Figura E6.** Proporción de turnos sin respuesta, con intervalo de confianza. Intervalos de Wilson al 95 % sobre el mismo corpus de 70 turnos recorrido dos veces. n = 70. [DERIVADO]. Fuente: 04_trazas/turns_replica_estricta.ndjson.

> *Nota de lectura.* Los dos intervalos de Wilson SÍ se solapan, y por eso no bastan para concluir nada: son intervalos independientes aplicados a datos pareados. El contraste correcto, McNemar exacto sobre los 23 turnos discordantes, da p = 0,035, de modo que la caída de proporción sí es significativa al 5 %. Que lo sea NO significa que la GPU arreglara los fallos antiguos: los 17 de la línea base son de contrato (generation_repair_failed) y los 6 nuevos son de transporte (4 × HTTP 502, 2 × HTTP 422), y κ = −0,145 sobre los identificadores dice que ni un solo caso coincide. Desapareció una población de fallos y apareció otra distinta.

**Figura F2.** Los cinco efectos medidos, cada uno en su escala. Magnitud de cada efecto con su intervalo cuando existe. n = 5. [DERIVADO]. Fuente: 04_trazas/turns_replica_estricta.ndjson, 05_derivados/ablacion_gramatica.json, 02_fixtures/verdad.json.

> *Nota de lectura.* No es un forest plot canónico y no debe leerse como tal: las unidades son incomparables entre sí, por eso cada panel lleva su propia escala en vez de compartir un eje que sugeriría magnitudes comparables. Tres de los cinco efectos no tienen intervalo de confianza y lo dicen en el propio panel: la ausencia de IC es información, no un detalle de formato.

**Figura F3.** Qué niveles del esquema de trazas llegó a poblar la campaña. Los cuatro niveles del esquema de trazas y cuántos registros consiguió poblar cada uno. n = 115. [MEDIDO]. Fuente: 04_trazas/turns.ndjson, 04_trazas/turns_replica_estricta.ndjson, 07_informes/LIMITACIONES.md.

> *Nota de lectura.* Poblar calls_in_turn = null para que el validador de trazas pasara habría sido el patrón «condición necesaria tratada como suficiente» aplicado al propio instrumento. Se dejó fallar y se declaró. Los niveles vacíos son exactamente los que bloquean X1, X3 y H-8.

**Figura X1.** Descomposición prefill/decode por turno. NO PRODUCIBLE — El nivel de LLAMADA está vacío: la API pública del camino B no expone eval_count, eval_duration, load_duration ni done_reason.

**Figura X2.** Crecimiento del prefill a lo largo de los 15 turnos. NO PRODUCIBLE — history_messages_count vino null en los 45 turnos: la API no lo devuelve.

**Figura X3.** ttft_per_1k_in por posición de turno. NO PRODUCIBLE — Sin streaming y sin prompt_eval_duration por turno, la métrica no es calculable por el camino B.

**Figura X4.** Relojes, temperatura y potencia durante la medición. NO PRODUCIBLE — No se capturó log de nvidia-smi concurrente en ninguna de las 6 ventanas identificadas en A1.

**Figura X5.** Comparación de decode, MBU o TPOT entre L4 y A100. NO PRODUCIBLE — La línea base del 7-ago no contiene NINGUNA métrica de servidor: solo reloj de cliente.

**Figura X6.** Verificación de identidad de modelo entre corridas. NO PRODUCIBLE — El digest del modelo del 7-ago no consta en ningún fichero de la evidencia.

**Figura X7.** Canario de equivalencia inter-máquina. NO PRODUCIBLE — Los prompts renderizados del 7-ago no constan: el instrumento antiguo solo guardaba el texto lógico.

**Figura X8.** Tendencia de parámetros en el historial. NO PRODUCIBLE — El fixture tiene n_estudios = 2: dos puntos definen siempre una recta, así que 'tendencia' no es medible.

**Figura X9.** Radar completo de los cinco ejes de la rúbrica. NO PRODUCIBLE — Los ejes 2 y 5 no son puntuables: §9.4 exige decidir referente_recuperable sobre el prompt renderizado real, que no existe.
