# Capítulo I — TEXTO ACTUAL, ÍNTEGRO Y VERBATIM

> Extraído de `P1 ICC 1910 — … (4).docx` el 12 de agosto de 2026. Es el texto que hay que
> modificar. Se han desescapado los artefactos de conversión y las imágenes se han sustituido por
> marcadores `[FIGURA imageNN]`; los pies de figura se conservan tal cual.
>
> **No se ha alterado ninguna palabra del contenido.** Los errores y las cifras desactualizadas que
> contiene son deliberados: son precisamente los que hay que corregir.

---

# **Capítulo I - Marco Teórico** 

# 

Este capítulo describe los fundamentos conceptuales, clínicos y tecnológicos en los que se basa el desarrollo de HemoVet. Abarca los principios para interpretar el hemograma completo, las limitaciones de basarse únicamente en la lectura del hemograma, cómo aplicar el aprendizaje automático a datos clínicos tabulados y cómo utilizar LLM para comunicar de forma responsable los resultados del hemograma al propietario.

## **1.1. Marco Teórico** 

El marco teórico se estructura en cuatro ejes principales. En primer lugar, presenta los principios clínicos y veterinarios básicos que deben comprenderse para apreciar la utilidad diagnóstica del hemograma canino. A continuación, analiza el parecido fenotípico entre estos patrones hematológicos y la limitación instrumental que exige un enfoque computacional. Posteriormente, introduce los conceptos del aprendizaje automático para la tarea de clasificación multietiqueta de datos tabulares. Por último, sitúa la relevancia epidemiológica regional del proyecto y la falta de información por parte del propietario del paciente.

### **1.1.1. Fundamentos Clínicos-Veterinarios** 

Desarrolla los aspectos clínicos necesarios para aprender a interpretar un hemograma completo canino y por qué requiere una lectura multivariable. Describe las líneas celulares que componen el hemograma completo, los patrones hematológicos de mayor interés para el proyecto y por qué es importante el seguimiento de las enfermedades crónicas en los perros, especialmente en un contexto en el que el propietario no dispone de una intervención clínica inmediata.

#### **1.1.1.1. El hemograma completo canino: composición, valor clínico y flujo de uso** 

El hemograma completo (CBC, Complete Blood Count) es una de las pruebas diagnósticas más populares en la medicina veterinaria de pequeños animales. Su utilidad clínica no reside en un único valor, sino en el perfil cuantitativo y cualitativo de las tres principales líneas celulares sanguíneas: serie eritroide, serie leucocitaria y serie plaquetaria [[21]](#bookmark=kix.fhbh92l5z2kj). Las propiedades diagnósticas emergen de la interacción entre parámetros individuales, y es la estructura de relaciones del perfil completo la que justifica los cálculos multivariantes y complejiza la comprensión independiente por parte del propietario  [[2]](#bookmark=kix.7fsxepid0eq), [[26]](#bookmark=kix.s9g2rkxiqdym), [[27]](#bookmark=kix.etkqolha2d6i).

[FIGURA image2]

*Figura 1. Ejemplo de un hemograma completo canino generado por el analizador IDEXX ProCyte One. Se muestran las tres series hematológicas (eritroide, leucocitaria y plaquetaria), los índices hematimétricos derivados y el bloque de comentarios interpretativos del instrumento. Datos anonimizados.* 

La serie eritroide incluye los parámetros más informativos para medir la capacidad de transporte de oxígeno: recuento de eritrocitos (RBC), hemoglobina (HGB) y hematocrito (HCT), complementados por los índices derivados MCV, MCH y MCHC, que caracterizan morfológicamente cada eritrocito. La combinación de estos índices permite clasificar morfológicamente la anemia en ausencia de otras pruebas: anemia microcítica hipocrómica sugiere deficiencia de hierro o derivación portosistémica; normocrómica normocítica apunta a enfermedad crónica o insuficiencia renal; macrocítica normocrómica con policromasia es el patrón típico de regeneración medular activa [[21]](#bookmark=kix.fhbh92l5z2kj), [[28]](#bookmark=kix.9e7d43pmownt). La serie leucocitaria abarca el recuento total de leucocitos y el diferencial de cinco tipos celulares, cuyo patrón cuantitativo es el componente del hemograma de mayor complejidad interpretativa y mayor riesgo de error en análisis no especializado [[1]](#bookmark=kix.2sp1wq1trcug), [[21]](#bookmark=kix.fhbh92l5z2kj). La serie plaquetaria recoge el PLT y el MPV, siendo este último indicador del estado de la trombopoyesis medular [[21]](#bookmark=kix.fhbh92l5z2kj). El RDW, medida de anisocitosis eritrocitaria generada por los analizadores modernos, se incluye en el feature set del motor de clasificación HemoVet por su valor como indicador de anemia mixta o en fases tempranas.

#### **1.1.1.2. Interpretación multivariable de patrones hematológicos: fundamento clínico y evidencia computacional** 

El supuesto básico del razonamiento diagnóstico del CBC es que los valores individuales de los parámetros son insuficientes: el significado diagnóstico resulta de la disposición relacional del perfil completo [[1]](#bookmark=kix.2sp1wq1trcug), [[21]](#bookmark=kix.fhbh92l5z2kj), [[29]](#bookmark=kix.gw1jzaq5qv9x). Este principio, que podría denominarse la emergencia semántica de los datos hematológicos, es tanto el origen de la riqueza informativa del CBC como la razón de la brecha de comprensión del propietario no especializado.

La evidencia computacional es convergente: el trabajo descrito en [[12]](#bookmark=kix.83aoj8qzgi53) demostró que el indicador univariante óptimo de leptospirosis canina (AUC 0.775) se supera significativamente con el modelo SVM entrenado sobre el perfil completo (AUC 0.955). Por su parte, la investigación en [[10]](#bookmark=kix.pqbc27s1uks6) identificó que el MCH, el recuento de linfocitos y la globulina sérica son los tres predictores más significativos en el modelo XGBoost de derivación portosistémica, relaciones que el análisis univariante no habría revelado. En este proyecto, la implicación de diseño es que el motor de clasificación recibe el perfil completo como entrada, garantizando que el algoritmo acceda no solo a las desviaciones univariantes sino a las relaciones entre parámetros.

#### **1.1.1.3. Patrones hematológicos de interés y diagnóstico diferencial** 

La anemia canina se define como HCT por debajo del rango de referencia para el perro adulto (<37%, según los rangos de referencia canónicos observados [[21]](#bookmark=kix.fhbh92l5z2kj)), con reducciones concomitantes en HGB y RBC. La distinción entre anemia regenerativa (médula ósea funcional, patrón macrocítico normocrómico con policromasia) y no regenerativa (incapacidad de respuesta, normocítica normocrómica) es el diferencial de mayor valor informativo para el propietario: orienta la urgencia de la consulta y el curso del proceso subyacente. La policitemia (HCT, HGB y RBC elevados) puede ser relativa (deshidratación) o absoluta primaria/secundaria, con la clave interpretativa en la coherencia interna entre los parámetros del perfil [[21]](#bookmark=kix.fhbh92l5z2kj).

El leucograma inflamatorio (neutrofilia con o sin desplazamiento a la izquierda), puede ser numéricamente indistinguible del leucograma de estrés (neutrofilia + linfopenia + eosinopenia mediadas por glucocorticoides) sin contexto clínico completo [[1]](#bookmark=kix.2sp1wq1trcug), [[21]](#bookmark=kix.fhbh92l5z2kj). La trombocitopenia es el hallazgo hematológico cardinal de la ehrlichiosis monocítica canina; sin embargo, la linfopenia puede aparecer en fase aguda pero es inconstante, demandando interpretación multivariante completa [[30]](#bookmark=kix.ul8ngwakmi72). La trombocitopenia representa el diferencial de mayor complejidad en el espectro cubierto por HemoVet: un recuento de PLT de 40×10⁹/L puede corresponder a ehrlichiosis aguda, TIP, CID, babesiosis o pseudotrombocitopenia por artefacto instrumental [[21]](#bookmark=kix.fhbh92l5z2kj), [[30]](#bookmark=kix.ul8ngwakmi72), [[31]](#bookmark=kix.z93z6sutom40). Ningún diagnóstico es determinable solo por el recuento plaquetario; los datos distintivos se distribuyen por el resto del perfil. La fisiopatología de la trombocitopenia se clasifica en reducción medular (asociada a anemia no regenerativa y leucopenia), destrucción inmunomediada (típicamente profunda con MPV elevado), consumo periférico en CID (con signos de fragmentación eritrocitaria), secuestro esplénico (rango moderado), y pseudotrombocitopenia por artefacto (requiere frotis de confirmación) [[21]](#bookmark=kix.fhbh92l5z2kj). El sistema HemoVet implementa comprobaciones de coherencia interna que identifican inconsistencias entre PLT, MPV y rango de volumen plaquetario esperado, emitiendo flags de baja confiabilidad cuando se detectan.

El principio integrador de estas tres series es que la utilidad diagnóstica del CBC se deriva de la interpretación relacional del perfil completo, no de la suma de interpretaciones individuales [[21]](#bookmark=kix.fhbh92l5z2kj), [[29]](#bookmark=kix.gw1jzaq5qv9x), [[32]](#bookmark=kix.uo9j94k3u1n1). Esto determina tres decisiones de diseño del sistema: el motor recibe el perfil completo; las guardrails del LLM prohíben reducir el resultado a un único número; y el informe muestra patrones como configuraciones emergentes.

#### **1.1.1.4. El hemograma en el seguimiento crónico de enfermedades caninas** 

En enfermedades como la ehrlichiosis monocítica canina, el propietario puede acumular tres a seis hemogramas durante el seguimiento del tratamiento, sin herramientas que le permitan determinar si la evolución representa mejoría, estabilización o progresión [[5]](#bookmark=kix.7ypcggsbd32c). En el MVP, HemoVet procesa cada hemograma de forma individual y proporciona historial cronológico de consulta al propietario. La comparación analítica longitudinal automatizada (detección de tendencias entre hemogramas seriados) queda fuera del alcance del MVP y se define como extensión prioritaria (TF2, Sección 5.4).

### **1.1.2. El Fenómeno de la similitud fenotípica entre patrones hematológicos y Limitaciones Instrumentales** 

El solapamiento clínico describe el fenómeno estructural por el que entidades patológicas distintas producen perfiles cuantitativos del CBC que no son discriminables mediante análisis de parámetros individuales [[21]](#bookmark=kix.fhbh92l5z2kj), [[32]](#bookmark=kix.uo9j94k3u1n1). Es un atributo natural de los sistemas biológicos en el que los procesos fisiopatológicos de diversas etiologías convergen en respuestas celulares compartidas. La ehrlichiosis monocítica canina ilustra además la superposición diacrónica: tres fases de la misma entidad (aguda, subclínica y mielodepresiva crónica) producen patrones cualitativamente distintos, lo que hace el seguimiento longitudinal tan relevante como la clasificación puntual [[5]](#bookmark=kix.7ypcggsbd32c).

La variabilidad interobservador en la interpretación del hemograma en medicina humana (y por extensión veterinaria), introduce una fuente adicional de incertidumbre que no se comunica sistemáticamente al propietario [[33]](#bookmark=kix.dpa4otpt5h2o). El uso de los comentarios internos del analizador IDEXX como fuente de etiquetas de entrenamiento (en vez de diagnósticos clínicos del historial) sustituye la variabilidad interobservador humana por la lógica clasificatoria patentada del ProCyte One: el analizador aplica la misma función de decisión a cada muestra con independencia del operador, pero el modelo aprende el comportamiento de un instrumento específico de un fabricante específico. Esta decisión es metodológicamente explícita y se documenta como limitación de generalización instrumental (L3) en la sección 5.3.

Teniendo en cuenta esta variabilidad, la evaluación de un sistema de interpretación hematológica no podía limitarse a comparar sus resultados con los valores de referencia generados por el analizador o con las reglas establecidas en el propio sistema. El estándar de referencia en una situación clínica real también se ve influido por la interpretación del veterinario, especialmente cuando se trata de un patrón con fenotipos similares o un número reducido de casos. Por ello, la validación clínica externa permite evaluar el nivel de concordancia entre los resultados del sistema y los de evaluadores veterinarios independientes. En este contexto, el kappa de Cohen es una medida adecuada del grado en que una coincidencia va más allá de la concordancia aleatoria, en contraposición a la concordancia aleatoria basada en la distribución de clases.

El solapamiento tiene tres implicaciones de diseño para el motor de clasificación. Primera, adopción del paradigma multilabel en lugar de multiclase, dado que un perfil puede mostrar simultáneamente patrón inflamatorio, trombocitopénico y anémico. Segunda, umbrales de decisión calibrados por etiqueta, porque la probabilidad de salida refleja la ambigüedad del perfil cuando hay superposición. Tercera, comunicación de incertidumbre al usuario: cuando un perfil está en zona de ambigüedad entre dos patrones, el sistema indica la señal cualitativa (clara, moderada o débil) sin ofrecer una clasificación categórica artificial [[9]](#bookmark=kix.sxvreljxsj8k).

En cuanto a las limitaciones instrumentales, los analizadores modernos producen dos salidas simultáneas: el canal numérico (recuentos e índices) y el canal de comentarios (indicadores textuales generados por algoritmos internos que incorporan dispersión multiparamétrica y morfología óptica). En HemoVet, ambos canales son metodológicamente importantes pero con funciones distintas: el motor se entrena sobre el canal numérico, por lo que aprende las correlaciones inherentes al perfil cuantitativo sin recrear la lógica propietaria del instrumento; las etiquetas se derivan del canal de comentarios IDEXX durante el entrenamiento, pero en producción el sistema opera sobre cualquier hemograma con los parámetros numéricos estándar. La heterogeneidad instrumental entre el IDEXX ProCyte One (fuente de entrenamiento) y los instrumentos del Dog Aging Project (cohorte de validación externa) requiere estandarización intra-fuente y protocolo de evaluación del domain shift [[14]](#bookmark=kix.i069zqahukp9), [[34]](#bookmark=kix.aisymbg71472), [[35]](#bookmark=kix.s2e18okkktjf).

### **1.1.3 Aprendizaje Automático Aplicado a la Interpretación Hematológica** 

El sistema HemoVet se basa esencialmente en el aprendizaje automático, lo que permite la identificación de patrones hematológicos a partir de las relaciones multivariables entre los parámetros del hemograma completo. Se presentan las métricas de evaluación aplicadas, el procesamiento de datos tabulares, la clasificación multietiqueta, los algoritmos de conjunto, la explicabilidad con la ayuda de SHAP y los problemas de cambio de dominio entre diferentes tipos de fuentes de datos.

#### **1.1.3.1 Métricas de evaluación para clasificación multilabel con datos desbalanceados** 

La selección de métricas de evaluación en sistemas de clasificación aplicados a datos clínicos no es una decisión neutral: métricas inadecuadas pueden producir estimaciones de rendimiento artificialmente optimistas que no reflejan el comportamiento real del sistema ante la distribución de casos en producción [[36]](#bookmark=kix.17kp4r78sz1t), [[37]](#bookmark=kix.8n4r425xkhq4). En contextos donde la prevalencia de las clases positivas es estructuralmente baja, la exactitud global (accuracy) carece de valor diagnóstico: un clasificador que predijera siempre negativo alcanzaría valores aparentemente altos sin detectar ningún caso real. Esta característica hace obligatorio el uso de métricas que evalúen el rendimiento sobre la clase positiva de forma independiente de la abundancia de negativos.

La curva Precisión-Exhaustividad (Precision-Recall curve) traza la relación entre precisión (proporción de predicciones positivas que son efectivamente correctas) y exhaustividad (proporción de casos positivos reales detectados) a lo largo de todos los umbrales de decisión posibles. Davis y Goadrich demostraron formalmente que esta curva es informativamente superior a la curva ROC cuando la clase positiva es minoritaria, dado que el área bajo la curva Precision-Recall (PR-AUC) no incorpora verdaderos negativos en su cálculo y no se ve distorsionada por la abundancia estructural de negativos [[38]](#bookmark=kix.lp9v2nm7d2n8). El valor de referencia inferior del PR-AUC es la prevalencia de la clase positiva en el conjunto de evaluación, que representa el rendimiento esperado de un clasificador aleatorio, lo que sitúa cualquier valor reportado en perspectiva correcta respecto a ese umbral basal.

El área bajo la curva ROC (ROC-AUC) cuantifica la capacidad del modelo de separar instancias positivas y negativas, expresada como la probabilidad de que el modelo asigne una puntuación mayor a un caso positivo que a uno negativo seleccionados al azar [[39]](#bookmark=kix.kpnpw7pov4yx). Se reporta con frecuencia en la literatura de clasificación clínica [[10]](#bookmark=kix.pqbc27s1uks6), [[11]](#bookmark=kix.nw4lqsbgj7t), [[12]](#bookmark=kix.83aoj8qzgi53), [[13]](#bookmark=kix.lbtkblt5pxhs), pero su interpretación se ve distorsionada en presencia de desbalance severo de clases, dado que incluye verdaderos negativos en el denominador de la tasa de falsos positivos. Se identifica el PR-AUC como la métrica primaria recomendada para sistemas diagnósticos computacionales multilabel en datos clínicos desbalanceados, señalando que el ROC-AUC sobreestima sistemáticamente el rendimiento efectivo en esos escenarios [[37]](#bookmark=kix.8n4r425xkhq4).

El F1 es la media armónica de precisión y exhaustividad evaluada en un umbral de decisión fijo, y representa el rendimiento operativo real del sistema en producción, a diferencia del PR-AUC, que evalúa el clasificador con independencia del umbral [[36]](#bookmark=kix.17kp4r78sz1t). En clasificación multilabel, la optimización individual de umbrales por etiqueta es la práctica recomendada, dado que una única frontera de decisión global introduce sesgos sistemáticos en las etiquetas con menor soporte. Informes ilustran que este ajuste por etiqueta es especialmente relevante en datos médicos, donde el costo clínico de los falsos negativos y los falsos positivos no es simétrico entre clases [[36]](#bookmark=kix.17kp4r78sz1t).

La cuantificación de la incertidumbre estadística de las métricas anteriores se realiza mediante intervalos de confianza bootstrap al 95%. Se generan múltiples conjuntos de evaluación remuestreados con reemplazo, se calcula el estimador en cada uno, y el intervalo se determina por los percentiles 2.5 y 97.5 de la distribución empírica resultante. Carpenter y Bithell establecen que este procedimiento es el más apropiado para estimar la incertidumbre de métricas de rendimiento cuando el tamaño del conjunto de evaluación es limitado y no puede asumirse normalidad en la distribución del estimador [[40]](#bookmark=kix.fchbpcochp9s). La amplitud del intervalo es informativa en sí misma: intervalos amplios asociados a etiquetas con soporte reducido indican que el valor puntual debe interpretarse con cautela, con independencia del valor central observado.

#### **1.1.3.2 Datos tabulares, feature engineering y clasificación multilabel** 

La viabilidad de los datos tabulares del CBC como entrada para clasificación diagnóstica está documentada tanto en medicina humana (modelos que alcanzan más del 90% de precisión con XGBoost y Random Forest [[14]](#bookmark=kix.i069zqahukp9), [[15]](#bookmark=kix.wv2v259xzslx)) como en veterinaria, con cuatro precedentes caninos representativos: derivación portosistémica (AUC 0,976) [[10]](#bookmark=kix.pqbc27s1uks6), Babesia canis (sensibilidad 100% en test set limitado, ver [[11]](#bookmark=kix.nw4lqsbgj7t)), leptospirosis (AUC 0.955) [[12]](#bookmark=kix.83aoj8qzgi53) e hipoadrenocorticismo (AUC 0.994) [[13]](#bookmark=kix.lbtkblt5pxhs). Esta convergencia valida el principio de forma suficientemente general como para anticipar su aplicabilidad al espectro de patrones de HemoVet. El sistema incluye la etiqueta QC_REQUIERE_FROTIS para señalar los perfiles en que la confirmación morfológica sigue siendo necesaria [[11]](#bookmark=kix.nw4lqsbgj7t), [[41]](#bookmark=kix.6gn8hcofuc8e).

El conjunto de características del sistema consta de tres tipos de variables: (1) recuentos absolutos y relativos de las líneas eritroide, leucocitaria y plaquetaria; (2) índices hematimétricos (MCV, MCH, MCHC, RDW, MPV); y (3) ratios hematológicos (NLR, PLR, MLR, MPV/PLT) con valor clínico documentado [[21]](#bookmark=kix.fhbh92l5z2kj). Las características derivadas representan las interrelaciones entre los parámetros que se sabe que tienen relevancia clínica, lo que puede ayudar a minimizar la cantidad de datos a partir de los cuales debe aprender el modelo. Se utiliza la mediana por fuente de datos para imputar los valores que faltan, y los datos solo se utilizan para el conjunto de entrenamiento y se transfieren a la fase de producción.

La clasificación multilabel es el paradigma adecuado porque un perfil puede presentar simultáneamente múltiples patrones coexistentes (anemia no regenerativa + inflamatorio + trombocitopénico). Los métodos de transformación de problemas (Binary Relevance [BR], Classifier Chains [CC] y Ensemble Classifier Chains [ECC]) difieren en su tratamiento de las correlaciones entre etiquetas [[42]](#bookmark=kix.gw72qa50prqy). XGBoost en configuración multisalida es funcionalmente equivalente a BR, entrenando conjuntos de árboles independientes por etiqueta. La selección final se decide empíricamente sobre el conjunto de validación. El desequilibrio de clases es estructural en datos clínicos: prevalencias bajas (policitemia, ehrlichiosis crónica con pancitopenia) pueden producir relaciones positivo/negativo de 1:50 o menos [[36]](#bookmark=kix.17kp4r78sz1t). La estrategia adoptada combina aprendizaje sensible al costo (scale_pos_weight en XGBoost, class_weight=balanced en Random Forest) con optimización de umbrales por etiqueta en validación, maximizando F1 por etiqueta con sensibilidad mínima garantizada. La métrica principal es PR-AUC por etiqueta, que no incorpora verdaderos negativos en su cálculo y no se ve distorsionada por el tamaño de las clases negativas [[37]](#bookmark=kix.8n4r425xkhq4).

#### **1.1.3.3. Algoritmos de ensamble, explicabilidad SHAP y validación robusta** 

Los métodos de ensamble (bagging [Random Forest] y boosting por gradiente [XGBoost]) son los algoritmos de referencia en la literatura de ML aplicado a datos tabulares clínicos [[10]](#bookmark=kix.pqbc27s1uks6), [[11]](#bookmark=kix.nw4lqsbgj7t), [[12]](#bookmark=kix.83aoj8qzgi53), [[43]](#bookmark=kix.jlv8mwoyavin). Quedaron demostrados sobre 45 conjuntos de datos tabulares que Random Forest y XGBoost superan a arquitecturas de aprendizaje profundo específicamente diseñadas para tabular data, atribuyendo este resultado a su menor sensibilidad a características no informativas, invarianza a transformaciones de escala y capacidad de aprender funciones objetivo irregulares [[44]](#bookmark=kix.aepmhivrh2k). Otros escenarios de experimentación añaden que XGBoost requiere considerablemente menos esfuerzo de ajuste de hiperparámetros para alcanzar rendimiento igual o superior [[45]](#bookmark=kix.ft6jcr85uvav).

La explicabilidad mediante valores SHAP (SHapley Additive exPlanations) no es una extensión opcional sino un requisito funcional para la confianza del usuario y la auditoría del sistema [[9]](#bookmark=kix.sxvreljxsj8k), [[26]](#bookmark=kix.s9g2rkxiqdym). Los valores SHAP satisfacen simultáneamente tres axiomas que ningún otro método aditivo cumple: local accuracy, missingness y consistency [[46]](#bookmark=kix.ojvy4r8yb90p). La variante TreeSHAP calcula los valores exactos en tiempo polinomial O(TLD²), haciendo viable el cálculo en el momento de inferencia [[47]](#bookmark=kix.whdvvz9of5dj). En HemoVet, SHAP global (media de valores absolutos sobre el conjunto de evaluación) informa el ranking de importancia de características; SHAP local por instancia informa el reporte ciudadano indicando qué parámetros del hemograma específico contribuyeron más al resultado de esa clasificación.

La evaluación robusta requiere cuantificar la incertidumbre estadística mediante intervalos de confianza bootstrap: se generan B=1,000 conjuntos de prueba remuestreados con reemplazo, se calcula el estimador en cada uno, y el IC se basa en los percentiles 2.5 y 97.5 [[40]](#bookmark=kix.fchbpcochp9s). La amplitud del IC es informativa en sí misma: para PATRON_POLICITEMIA, con n=32 en test y PR-AUC puntual observado de 1,000, la distribución bootstrap con B=1,000 remuestreos arrojó una mediana de aproximadamente 0,92 con IC 95% basado en percentiles bootstrap de [0,83; 1,000], lo que refleja la incertidumbre estadística inherente a soporte pequeño sin contradecir el valor puntual observado. Se adopta partición temporal (70/15/15 por fecha de muestra) como principal mecanismo de protección contra fuga de datos cronológica [[12]](#bookmark=kix.83aoj8qzgi53).

#### **1.1.3.4. Desplazamiento de dominio entre fuentes de datos heterogéneas** 

El domain shift (diferencia en la distribución conjunta de variables de entrada y etiquetas entre entrenamiento y despliegue), produce deterioro del rendimiento sin que el sistema lo detecte por sí mismo [[34]](#bookmark=kix.aisymbg71472). En HemoVet se estudia comparando el entrenamiento (2,454 hemogramas IDEXX ProCyte One, Santiago de los Caballeros) con la validación externa (1,301 registros del Dog Aging Project, cohorte sana norteamericana con instrumentos distintos). Las dos fuentes no se fusionan para entrenar: el modelo se entrena exclusivamente sobre IDEXX y el DAP se evalúa sin reentrenamiento ni ajuste de umbrales. El desplazamiento se cuantifica mediante effect_size \= |μ_IDEXX − μ_DAP| / σ_IDEXX por feature, identificando RDW (1.55) y Monocytes (0.81) como las variables con shift severo, coherente con la mayor prevalencia de inflamación activa y enfermedades hematológicas en la población clínica tropical frente a la cohorte sana norteamericana. El caso paradigmático del modelo de sepsis de Epic, que se desactivó durante COVID-19 por cambio en la composición de la población hospitalaria [[34]](#bookmark=kix.aisymbg71472), subraya que los modelos clínicos requieren seguimiento continuo del rendimiento en producción, motivando el diseño del gate de monitorización de deriva incluido en el sistema.

#### **1.1.3.5 Extracción de datos desde PDF e integración con sistemas clínicos** 

El hemograma canino se entrega al propietario como PDF generado por el analizador, no como datos computacionalmente accesibles. El pipeline de extracción de HemoVet opera en tres etapas sobre PDFs IDEXX ProCyte One: extracción de regiones tabulares con pdfplumber mediante expresiones regulares específicas al formato; normalización de nomenclatura y conversión de unidades a espacio homogéneo de referencia; y control de calidad preinferencia con advertencias ante valores fuera de rango fisiológico extremo, parámetros ausentes o inconsistencias entre índices derivados y valores base. La tasa de extracción obtenida es 98.2% sobre 2,480 registros procesados.

La plataforma Anna [[16]](#bookmark=kix.7h6ksws3qzax) proporciona el referente de viabilidad operativa para la integración de clasificadores ML con sistemas clínicos: separación de entornos (cada clasificador con sus dependencias aisladas), automatización del preprocesamiento sin intervención humana y trazabilidad legal con almacenamiento en base de datos. HemoVet adapta estos principios al escenario ciudadano: el PDF reemplaza la HCE como fuente de datos; la separación entre motor de clasificación y capa conversacional replica el principio de desacoplamiento de Anna; y la trazabilidad opera registrando resultados y snapshots clínicos en PostgreSQL con timestamp.

#### **1.1.3.6. LLM, RAG y diseño ético para comunicación ciudadana** 

Los modelos de lenguaje de gran escala (LLM) tienen la capacidad más relevante para este proyecto: traducir el registro lingüístico, convirtiendo la síntesis técnica de patrones hematológicos en texto comprensible para un propietario sin formación médica [[48]](#bookmark=kix.e9d3ozzdn445). HemoVet adopta el paradigma de generación guiada: el LLM no genera texto libre sobre el hemograma, sino que traduce los patrones ya clasificados por el motor ML con la base de conocimiento RAG en contexto, produciendo respuestas más controladas y factuales que la generación paramétrica libre [[49]](#bookmark=kix.w9vd7mmwnjwn), [[50]](#bookmark=kix.gi8eothbtebw). La alucinación (generación de información factualmente incorrecta con apariencia de veracidad) es el riesgo con mayores implicaciones clínicas [[48]](#bookmark=kix.e9d3ozzdn445); la arquitectura de dos capas la mitiga estructuralmente haciendo que el LLM actúe únicamente como traductor sin capacidad de razonamiento diagnóstico independiente.

La generación aumentada por recuperación (RAG) complementa el conocimiento que contiene el modelo de lenguaje de los pesos internos del LLM, lo que permite seleccionar, versionar y actualizar la base de conocimientos sin necesidad de volver a entrenar el modelo de lenguaje [[51]](#bookmark=kix.78ewxehrpus8). La base de conocimientos de HemoVet está compuesta por documentos Markdown seleccionados, organizados por ámbitos temáticos que abordan las limitaciones clínicas del sistema, la interpretación del hemograma completo, la hematología veterinaria y la comunicación responsable. Estos documentos se dividen en fragmentos, se convierten en embeddings y se almacenan en una base de datos vectorial, para su recuperación semántica durante la consulta.

El ciclo operativo del módulo conversacional consta de cinco pasos: en primer lugar, la consulta del usuario pasa por una serie de filtros determinísticos, que limitan el alcance de la consulta para evitar peticiones específicas como diagnósticos definitivos, tratamientos, medicación, dosificación, etc.; a continuación, si la consulta se encuentra dentro del ámbito, se recuperan los fragmentos más similares del corpus, basándose en las características semánticas; en tercer lugar, el resultado del motor hematológico y los fragmentos recuperados se añaden a la solicitud como contexto controlado; en cuarto lugar, el LLM genera una respuesta en lenguaje natural que se limita a la explicación educativa y la orientación para la consulta veterinaria; y, por último, pasa por las reglas de seguridad y se presenta al usuario. Este diseño reduce las alucinaciones y limita el razonamiento diagnóstico del LLM a explicar los resultados que el motor de clasificación ya ha ordenado previamente, en lugar de permitir que el LLM genere sus propias ideas [[48]](#bookmark=kix.e9d3ozzdn445), [[51]](#bookmark=kix.78ewxehrpus8), [[52]](#bookmark=kix.z5fejjotxm20).

Los principios éticos de diseño no son restricciones posteriores sino decisiones que determinaron la arquitectura desde su concepción [[9]](#bookmark=kix.sxvreljxsj8k), [[22]](#bookmark=kix.ftx5czj0vuyg). El principio de no sustitución se implementa en tres niveles: el motor de clasificación muestra indicadores de confianza que reflejan la incertidumbre del modelo; el informe incluye el texto de derivación al veterinario como elemento obligatorio; y las guardrails del LLM impiden la generación de diagnósticos específicos. El principio de transparencia se opera mediante identificación explícita del sistema como intérprete de hemograma con alcance limitado, y mediante publicación del código fuente del motor de clasificación en el repositorio institucional. El principio de minimización de datos establece que el sistema no almacena información identificable del propietario ni del animal más allá de lo necesario para el funcionamiento de la sesión [[53]](#bookmark=kix.pl5ujm1h598k). La presentación de resultados sigue tres decisiones: primacía del patrón sobre el parámetro (el informe presenta patrones completos antes que valores individuales), clasificación por urgencia de seguimiento (consulta de rutina, próxima semana, urgente) sin emitir diagnóstico, e integración de la capa conversacional para profundizar la explicación al nivel requerido por el propietario [[2]](#bookmark=kix.7fsxepid0eq), [[3]](#bookmark=kix.szutss8i9xxo), [[20]](#bookmark=kix.i3gcj5tzfkax).

### **1.1.4. Contexto Epidemiológico Regional y Relevancia del Proyecto** 

El proyecto es relevante a nivel epidemiológico regional, lo que debe reflejarse más allá del ámbito tecnológico. La ehrlichiosis es una enfermedad canina que provoca manifestaciones hematológicas relevantes y es muy común en la República Dominicana y el Caribe, con especial importancia porque la interpretación del hemograma completo por parte del propietario resulta complicada sin asistencia especializada. Esta sección vincula el reto técnico del proyecto con una necesidad sanitaria o informativa.

#### **1.1.4.1. Ehrlichiosis canina en el Caribe y la República Dominicana** 

La ehrlichiosis monocítica canina (EMC), causada por Ehrlichia canis y transmitida por Rhipicephalus sanguineus, es una enfermedad de importancia veterinaria y epidemiológica primordial en el Caribe insular. La seroprevalencia registrada oscila entre el 27% a nivel regional y el 44% en poblaciones insulares concretas [[54]](#bookmark=kix.jn0cfxoh8nen), [[55]](#bookmark=kix.i7urngerapnv), [[56]](#bookmark=kix.t35z1t8s4okp). La investigación de Campos y Mangeri en la República Dominicana reportó evidencia compatible con la circulación activa del agente en la población canina doméstica de Santo Domingo [[24]](#bookmark=kix.w5vrfm18xq8z), aunque la prevalencia nacional no se ha medido sistemáticamente. La ehrlichiosis es la causa más frecuente de trombocitopenia en perros en el entorno caribeño, y sus patrones hematológicos trifásicos demandan lectura relacional del perfil completo imposible de derivar por un propietario a partir de valores numéricos aislados [[5]](#bookmark=kix.7ypcggsbd32c). La agregación de los patrones clasificados por el sistema puede contribuir, en iteraciones futuras, a datos de vigilancia epidemiológica sobre la distribución temporal y espacial de patrones compatibles con la enfermedad, siempre que se mejore la geocodificación y se amplíe la cobertura territorial.

#### **1.1.4.2. Brecha informativa del propietario y vacíos en herramientas digitales** 

El período pandémico 2020-2021 aceleró la adopción de telemedicina veterinaria, consolidando un modelo en que el propietario recibe los resultados de laboratorio de forma asincrónica sin mediación oral del profesional [[4]](#bookmark=kix.glrdrkiptqiv). En este contexto, la ausencia de herramientas de interpretación es particularmente crítica: Se ha señalado que la comunicación a distancia del hemograma es uno de los principales retos de la telemedicina veterinaria [[57]](#bookmark=kix.mq62ge56icm), y se ha subrayado que el potencial de la telemedicina en zonas de acceso limitado (como áreas rurales de la República Dominicana) solo se alcanza cuando los propietarios disponen de herramientas de mediación informativa [[4]](#bookmark=kix.glrdrkiptqiv).

Una revisión sistemática sobre aplicaciones mHealth veterinarias reveló que las herramientas actuales se centran en recordatorios de medicación, seguimiento de síntomas generales y comunicación con el veterinario, sin ninguna herramienta de interpretación de laboratorio [[17]](#bookmark=kix.lowkv9jbmqup). La superposición de la brecha tecnológica (ausencia de herramientas ciudadanas de interpretación hematológica) con la brecha de investigación (escasa cobertura de datos tabulares en IA veterinaria, 8% según informes [[18]](#bookmark=kix.a8n5citahviu)) delimita con precisión el ámbito del presente proyecto y la novedad de su contribución.

## **1.2 Definición de Términos y Glosario** 

A continuación se muestra la terminología técnica y clínica más aplicable a este proyecto en cada uno de los ámbitos temáticos.

### **A. Términos clínico-veterinarios** 

**CBC (Complete Blood Count, Hemograma completo):** Prueba de laboratorio que mide las principales series de células sanguíneas mediante un analizador automatizado: serie eritroide (RBC, HGB, HCT, MCV, MCH, MCHC, RDW), serie leucocitaria (WBC y diferencial en cinco tipos celulares) y serie plaquetaria (PLT, MPV). Su interpretación integrada orienta el diagnóstico de anemias, infecciones, inflamaciones y trastornos de hemostasia [[21]](#bookmark=kix.fhbh92l5z2kj), [[29]](#bookmark=kix.gw1jzaq5qv9x).

**Patrón hematológico:** Estructura multivariable basada en la correlación de los parámetros del hemograma completo, cuya valor clínico es emergente y no puede reducirse a la suma de la interpretación respectiva de cada variable [[21]](#bookmark=kix.fhbh92l5z2kj).

**Superposición hematológica (Hematological overlap):** Fenómeno por el cual diversas entidades patológicas producen perfiles cuantitativos del hemograma completo que son indistinguibles mediante análisis univariante, requiriendo lectura relacional del perfil completo [[32]](#bookmark=kix.uo9j94k3u1n1).

**Diagnóstico diferencial:** proceso metódico de discriminación de patologías que presentan hallazgos similares. La trombocitopenia (ehrlichiosis frente a TIP frente a CID frente a babesiosis), la anemia (regenerativa frente a no regenerativa) y los cambios leucocitarios son los puntos centrales de este proyecto [[32]](#bookmark=kix.uo9j94k3u1n1).

**Trombocitopenia:** Recuento plaquetario (PLT) reducido por debajo del rango de referencia canino (< 150 x 10⁹/L es un rango de referencia aproximado). Estas causas se clasifican en disminución de la producción medular, destrucción inmunomediada, consumo periférico y secuestro/redistribución esplénica [[21]](#bookmark=kix.fhbh92l5z2kj).

**Trombocitopenia inmune primaria (TIP):** Condición autoinmune por destrucción plaquetaria mediada por anticuerpos. Se trata de un diagnóstico de exclusión; un recuento de PLT < 12 x 10^9/L tiene una especificidad del 90 % y una sensibilidad del 60 % en perros según el consenso de la ACVIM de 2024 [[30]](#bookmark=kix.ul8ngwakmi72).

**Pseudotrombocitopenia:** Recuento plaquetario falsamente reducido por agregación plaquetaria in vitro, plaquetas gigantes o interferencias preanalíticas. Requiere confirmación con frotis sanguíneo cuando el hallazgo es inesperado [[29]](#bookmark=kix.gw1jzaq5qv9x).

**Anemia regenerativa:** Configuración eritroide con disminución de HCT, HGB y RBC acompañada de indicadores de respuesta medular activa (policromasia, macrocitosis relativa). Sugestiva de origen hemolítico o hemorrágico agudo [[21]](#bookmark=kix.fhbh92l5z2kj), [[29]](#bookmark=kix.gw1jzaq5qv9x).

**Anemia no regenerativa:** Configuración eritroide con disminución de parámetros eritrocíticos en ausencia de respuesta medular. Indica un origen crónico, relacionado con una deficiencia, aplásico o por supresión medular. Observación frecuente en la ehrlichiosis crónica [[21]](#bookmark=kix.fhbh92l5z2kj), [[29]](#bookmark=kix.gw1jzaq5qv9x).

**Policitemia:** HCT, HGB y RBC elevados, por encima de los valores de referencia caninos. Puede ser relativa (deshidratación) o absoluta (primaria: eritremia; secundaria: hipoxia crónica) [[21]](#bookmark=kix.fhbh92l5z2kj).

**Leucograma de estrés:** leucocitosis neutrofílica, linfopenia, monocitosis y eosinopenia debidas a glucocorticoides. Numéricamente, puede coincidir con leucogramas infecciosos leves [[21]](#bookmark=kix.fhbh92l5z2kj).

**Patrón inflamatorio:** Cuadro leucocitario con neutrofilia, con o sin desplazamiento a la izquierda, que sugiere una respuesta inflamatoria sistémica activa, pero no necesariamente una etiología concreta [[1]](#bookmark=kix.2sp1wq1trcug), [[21]](#bookmark=kix.fhbh92l5z2kj).

**Ehrlichiosis monocítica canina (EMC, E. canis):** Enfermedad rickettsial transmitida por Rhipicephalus sanguineus se caracteriza por: fase aguda: trombocitopenia (80–100 %); fase subclínica: hemograma casi normal; fase crónica: pancitopenia aplásica. En el Caribe, la seroprevalencia alcanza el 44 % [[5]](#bookmark=kix.7ypcggsbd32c), [[58]](#bookmark=kix.uhw9nwgl7dg8).

**Coagulación intravascular diseminada (CID):** Trastorno de coagulación descontrolada del sistema con consumo de plaquetas y factores. Implicada en la trombocitopenia en el hemograma; urgencia médica con patrón superpuesto al de ehrlichiosis aguda [[29]](#bookmark=kix.gw1jzaq5qv9x), [[32]](#bookmark=kix.uo9j94k3u1n1).

**Ratio neutrófilo/linfocito (NLR):** Índice basado en el recuento diferencial de leucocitos (neutrófilos absolutos / linfocitos absolutos) que servirá como indicador de la respuesta inflamatoria sistémica. Un atributo extraído que se utiliza para alimentar el motor de clasificación [[21]](#bookmark=kix.fhbh92l5z2kj).

### **B. Términos de aprendizaje automático y evaluación** 

**Clasificación multietiqueta (Multilabel classification):** Paradigma de aprendizaje automático en el que una instancia puede pertenecer a más de una clase. Es lo contrario de la clasificación multiclase (una clase por instancia) y el paradigma adecuado para hemogramas con múltiples patrones coexistentes [[42]](#bookmark=kix.gw72qa50prqy).

**Relevancia binaria (Binary Relevance, BR):** Algoritmo de transformación de problemas multietiqueta que aprende clasificadores independientes sin prestar atención a las relaciones entre las etiquetas [[42]](#bookmark=kix.gw72qa50prqy).

**Cadenas de clasificadores (Classifier Chains, CC):** Arquitectura multietiqueta: serie de clasificadores que utilizan predicciones de otras etiquetas como características adicionales y que reflejan las dependencias entre etiquetas [[42]](#bookmark=kix.gw72qa50prqy).

**PR-AUC (Área bajo la Curva Precision-Recall):** Es una medida de evaluación que combina el área bajo la curva P-R en varios umbrales. Se prefiere al AUC-ROC cuando existe un fuerte desequilibrio, ya que no incluye ningún verdadero negativo en su cálculo [[37]](#bookmark=kix.8n4r425xkhq4).

**Pérdida de Hamming (Hamming loss):** Fracción de etiquetas incorrectamente predichas sobre el total de etiquetas e instancias. Métrica granular de error en clasificación multietiqueta, sensible al número de etiquetas [[37]](#bookmark=kix.8n4r425xkhq4).

**Desbalance de clases (Class imbalance):** Característica en la que las clases positivas de interés son una de las clases minoritarias en el conjunto de entrenamiento. Hace engañosa la exactitud global; requiere métricas balanceadas (F1-macro, G-mean, PR-AUC) y mecanismos de compensación [[36]](#bookmark=kix.17kp4r78sz1t).

**SMOTE (Synthetic Minority Over-sampling Technique):** Método de sobremuestreo sintético que crea instancias de una clase minoritaria mediante la interpolación entre las existentes. Solo debe utilizarse con el conjunto de entrenamiento y no en casos de fuga de datos [[10]](#bookmark=kix.pqbc27s1uks6).

**Cost-sensitive learning (aprendizaje sensible al costo):** Enfoque en el que los errores de clasificación se penalizan de forma diferente según la clase, para compensar la infrarrepresentación de la clase positiva. En XGBoost: scale_pos_weight [[36]](#bookmark=kix.17kp4r78sz1t).

**XGBoost (Extreme Gradient Boosting):** Se trata de un algoritmo de boosting que construye árboles secuencialmente para corregir errores residuales con función objetivo regularizada (L1+L2) y gradiente de segundo orden. Algoritmo primario del motor de clasificación HemoVet [[14]](#bookmark=kix.i069zqahukp9), [[44]](#bookmark=kix.aepmhivrh2k).

**Random Forest:** Un conjunto de árboles de decisión seleccionados aleatoriamente y de características elegidas al azar (bagging + subespacio de características). Modelo de referencia del sistema, ya que se muestra estable con los hiperparámetros predeterminados [[8]](#bookmark=kix.en9kbvzf6uhv).

**Feature engineering (ingeniería de características):** El acto de seleccionar, construir y convertir las variables de entrada del modelo. En HemoVet: elección de los parámetros CBC directos, construcción de índices derivados (NLR) y tratamiento de valores faltantes [[14]](#bookmark=kix.i069zqahukp9).

**SHAP (SHapley Additive exPlanations):** Marco de explicabilidad basado en valores de Shapley de teoría de juegos. Mide en qué medida contribuye cada característica a una predicción y satisface los axiomas de local accuracy, missingness y consistency [[46]](#bookmark=kix.ojvy4r8yb90p).

**TreeSHAP:** Variante de SHAP para modelos de árbol con complejidad O(TLD²) que permiten calcular los valores SHAP con exactitud en el momento de la inferencia. Aplicado en XGBoost e implementado en la biblioteca shap [[47]](#bookmark=kix.whdvvz9of5dj).

**Desplazamiento de dominio (Domain shift):** Fenómeno por el cual la distribución de los datos de producción es diferente a la distribución de los datos de entrenamiento. En HemoVet: instrumental (IDEXX frente a DAP), poblacional (Caribe frente a Norteamérica) y temporal [[34]](#bookmark=kix.aisymbg71472).

**Cohen’s kappa:** Medida estadística de concordancia entre dos clasificaciones o evaluadores que tiene en cuenta la concordancia por casualidad. Se utiliza para comprobar el rendimiento del sistema en relación con la validación clínica externa, comparando la interpretación de los veterinarios en HemoVet.

**Validación clínica externa:** Procedimiento de evaluación para comparar la predicción del sistema con la interpretación de evaluadores clínicos independientes, o con casos no incluidos en el conjunto de entrenamiento. El objetivo es simular su rendimiento en circunstancias operativas más realistas.

**Concordancia interevaluador:** Grado en que dos o más evaluadores coinciden en la interpretación de un conjunto determinado de casos. En el contexto de HemoVet, pone de manifiesto que la interpretación de los resultados hematológicos puede variar entre los veterinarios y que el rendimiento del sistema debe evaluarse teniendo esto en cuenta.

### **C. Términos de sistemas de IA y arquitectura** 

**LLM (Large Language Model):** modelo de inteligencia artificial generativa capaz de procesar contexto y producir lenguaje natural. En HemoVet, el runtime conversacional verificado utiliza Qwen3 4B en una variante cuantizada, ejecutada mediante Ollama. Su función está restringida a explicar información autorizada por el sistema y no a emitir diagnósticos o tratamientos [[48]](#bookmark=kix.e9d3ozzdn445).

**Alucinación (Hallucination):** Generación de información factualmente incorrecta por un LLM con apariencia de veracidad. El principal riesgo en aplicaciones clínicas; mitigado en HemoVet mediante RAG y guardarraíles [[48]](#bookmark=kix.e9d3ozzdn445).

**Guardarraíles (Guardrails):** Restricciones de diseño explícitas en el prompt del LLM que limitan sus respuestas a un dominio y modo definidos. En HemoVet: no permiten diagnósticos definitivos y exigen la derivación a un veterinario para plantear una pregunta clínica [[48]](#bookmark=kix.e9d3ozzdn445), [[50]](#bookmark=kix.gi8eothbtebw).

**RAG (Retrieval-Augmented Generation):** Arquitectura que combina un LLM con recuperación densa sobre una base de conocimiento curada, fundamentando respuestas en documentos recuperados para reducir alucinaciones y anclar el conocimiento en fuentes verificables [[51]](#bookmark=kix.78ewxehrpus8).

**Recuperación densa (Dense retrieval):** Algoritmo de búsqueda semántica que mapea consultas y documentos a vectores en un espacio de alta dimensión (embeddings) y encuentra los más similares utilizando la similitud coseno. Forma parte de la arquitectura RAG [[51]](#bookmark=kix.78ewxehrpus8).

**API REST (Application Programming Interface basada en Representational State Transfer):** Interfaz que se utiliza para la comunicación entre sistemas mediante solicitudes HTTP estandarizadas. Mecanismo de integración entre el portal ciudadano y el motor de clasificación de HemoVet [[16]](#bookmark=kix.7h6ksws3qzax).

**Separación entrenamiento-despliegue:** Principio arquitectónico por el cual el motor de clasificación (entrenado offline, serializado) y el servidor de inferencia (online, API REST) son componentes independientes. Permite actualizar uno sin afectar el otro [[16]](#bookmark=kix.7h6ksws3qzax).

**OCR (Optical Character Recognition):** Un proceso que convierte texto contenido en imágenes o PDF a texto digital. Forma parte del flujo de procesamiento de datos de HemoVet de los archivos PDF de hemogramas generados por escáneres [[6]](#bookmark=kix.q6ybbkpm75l4), [[7]](#bookmark=kix.9o3yxbmdx2jz).

**Ollama:** servidor local para la ejecución de modelos de lenguaje. En HemoVet se utiliza para servir el modelo Qwen3 4B dentro de la infraestructura del sistema. Su operación requiere control de identidad del modelo, precarga y manejo de arranques en frío.

**Guardrail determinístico:** Regla programada y verificada de forma explícita, que detendrá o ajustará la salida de un sistema si se detecta una condición fuera del rango especificado. Las barreras de seguridad deterministas eliminan cualquier respuesta derivada de un diagnóstico definitivo, un tratamiento, una medicación o una dosificación en HemoVet.

### **D. Acrónimos del CBC canino** 

**RBC (Red Blood Cells):** Eritrocitos.

**HGB (Hemoglobin):** Hemoglobina.

**HCT (Hematocrit):** Hematocrito.

**MCV (Mean Corpuscular Volume):** Volumen corpuscular medio.

**MCH (Mean Corpuscular Hemoglobin):** Hemoglobina corpuscular media; el principal predictor en el modelo XGBoost PSS [[10]](#bookmark=kix.pqbc27s1uks6).

**MCHC (Mean Corpuscular Hemoglobin Concentration):** Concentración de hemoglobina corpuscular media.

**RDW (Red cell Distribution Width):** Amplitud de distribución de los glóbulos rojos.

**WBC (White Blood Cells):** Leucocitos totales.

**PLT (Platelets):** Plaquetas.

**MPV (Mean Platelet Volume):** Volumen plaquetario medio; uno de los predictores más importantes en la detección de Babesia canis [[11]](#bookmark=kix.nw4lqsbgj7t).

**NLR (Neutrophil-to-Lymphocyte Ratio)**: Relación neutrófilos-linfocitos.

**PSS (Portosystemic shunt, derivación portosistémica):** Anomalía vascular en la que la sangre portal elude el hígado parcial o totalmente, alterando el metabolismo hepático. En el hemograma se asocia clásicamente con anemia microcítica hipocrómica por alteración del metabolismo hepático del hierro [[10]](#bookmark=kix.pqbc27s1uks6).

**MAT (Microscopic Agglutination Test):** Prueba de aglutinación microscópica, prueba serológica de referencia para el diagnóstico de leptospirosis canina. Su rendimiento univariante es limitado frente a modelos multivariantes basados en datos del hemograma y la bioquímica [[12]](#bookmark=kix.83aoj8qzgi53).

**ECC (Ensemble Classifier Chains):** Extensión de los Classifier Chains que genera múltiples cadenas con distintos ordenamientos de etiquetas y agrega sus predicciones, reduciendo la sensibilidad al orden de encadenamiento [[42]](#bookmark=kix.gw72qa50prqy).

**BCa (Bias-Corrected and accelerated bootstrap):** Intervalo de confianza bootstrap con corrección de sesgo y aceleración, más preciso que el IC percentil simple cuando la distribución empírica del estimador es asimétrica. Requiere un número mayor de iteraciones (B ≈ 2000\) [[40]](#bookmark=kix.fchbpcochp9s).

**HCE (Historia Clínica Electrónica):** Sistema digital de registro de información clínica del paciente. En el contexto de este proyecto, equivalente funcional del EHR en medicina humana y fuente de datos de sistemas como Anna [[16]](#bookmark=kix.7h6ksws3qzax).

**EHR (Electronic Health Record):** Término anglosajón para historia clínica electrónica [[16]](#bookmark=kix.7h6ksws3qzax).

**LIS (Laboratory Information System):** Sistema de información de laboratorio clínico que gestiona la solicitud, ejecución y reporte de análisis [[16]](#bookmark=kix.7h6ksws3qzax).

**DAP (Dog Aging Project):** Estudio longitudinal poblacional de envejecimiento canino con sede en EE. UU. En HemoVet se utiliza como cohorte de validación externa independiente del conjunto de entrenamiento [[18]](#bookmark=kix.a8n5citahviu).
