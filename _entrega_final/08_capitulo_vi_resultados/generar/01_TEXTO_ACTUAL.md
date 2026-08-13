# Capítulo VI — TEXTO ACTUAL, ÍNTEGRO Y VERBATIM

> Extraído de `P1 ICC 1910 — … (4).docx` el 12 de agosto de 2026. Es el texto que hay que
> modificar. Se han desescapado los artefactos de conversión y las imágenes se han sustituido por
> marcadores `[FIGURA imageNN]`; los pies de figura se conservan tal cual.
>
> **No se ha alterado ninguna palabra del contenido.** Los errores y las cifras desactualizadas que
> contiene son deliberados: son precisamente los que hay que corregir.

---

# **Capítulo VI - Análisis de los resultados** 

Este capítulo ofrece un análisis de los resultados obtenidos con HemoVet en los principales componentes del sistema, entre los que se incluyen el motor de clasificación hematológica, la validación externa con el Dog Aging Project, la validación clínica con veterinarios, el módulo conversacional LLM/RAG, las pruebas técnicas, el rendimiento de la inferencia, la vigilancia poblacional agregada y la usabilidad del prototipo. A diferencia del capítulo dedicado al desarrollo, este no pretende describir cómo se está desarrollando la plataforma, sino interpretar, basándose en las pruebas obtenidas en las fases de prueba y validación, el comportamiento del sistema.

El análisis se estructura dividiendo los resultados del aprendizaje automático, los resultados clínicos y los resultados de ingeniería. Esta separación permite atribuir al modelo las conclusiones basadas en el juicio clínico humano y evita que las métricas técnicas se utilicen como método para diagnosticar la validación. Por lo tanto, el resultado se considera un indicador del rendimiento y la preparación operativa, guiado por las instrucciones, y no una autorización para utilizarlo de forma autónoma en el diagnóstico.

Dado que en las secciones siguientes se mencionan el motor XGBoost, las reglas deterministas, el módulo LLM/RAG, la vigilancia poblacional o el prototipo web, se da por hecho que ya se habían construido previamente en capítulos anteriores, y solo se analiza su comportamiento durante las pruebas, validaciones y evaluaciones descritas.

## **6.1. Resultados del motor de clasificación hematológica** 

El estado final del sistema se documentó como listo para producción con limitaciones. Esta condición significa que el sistema se considera funcional y desplegable en situaciones controladas, pero presenta limitaciones conocidas. El motor final utiliza siete etiquetas oficiales y cuenta con una política explícita para las etiquetas con escaso soporte. La etiqueta PATRON_ANEMIA_REGENERATIVA tiene un carácter más exploratorio, ya que solo había seis casos positivos en el conjunto de prueba para esta clase.

En el conjunto de prueba, el sistema alcanzó un PR-AUC macro de 0.9529, un F1 macro de 0.8727 y un recall macro de 0,9205. Estos valores muestran que presenta un buen rendimiento en un problema multietiqueta desequilibrado. Sin embargo, la interpretación debe realizarse etiqueta por etiqueta, ya que las diferentes etiquetas presentan distintos niveles de apoyo y coste de error.

| Indicador | Valor |
| :---- | :---- |
| Estado del sistema | Funcional, con limitaciones |
| Versión reportada | 4.0.0 |
| Etiquetas oficiales | 7 |
| PR-AUC macro final | 0.9529 |
| F1 macro final | 0.8727 |
| Recall macro final | 0.9205 |
| Brier macro final | 0.0298 |
| Conteo TP/FP/FN/TN | 585 / 54 / 49 / 1895 |

*Tabla 6.1. Resumen del estado final del sistema HemoVet.*

### **6.1.1. Métricas finales por etiqueta** 

El rendimiento final en el conjunto de prueba para cada etiqueta se recoge en la Tabla 6.2. El patrón inflamatorio, el leucograma de estrés, la anemia no regenerativa, la hemólisis/MCHC y la policitemia obtuvieron los valores más altos de PR-AUC y F1 en el análisis a nivel de etiqueta. Las otras dos, QC_REQUIERE_FROTIS y PATRON_ANEMIA_REGENERATIVA, deben interpretarse con precaución debido a su menor valor de F1 o a su menor soporte positivo.

| Etiqueta | n+ | Umbral | TP | FP | FN | Recall | Precisión | Espec. | F1 | PR-AUC |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| QC requiere frotis | 136 | 0.300 | 93 | 26 | 43 | 0.684 | 0.781 | 0.888 | 0.729 | 0.846 |
| Patrón inflamatorio | 198 | 0.641 | 197 | 4 | 1 | 0.995 | 0.980 | 0.977 | 0.988 | 0.993 |
| Leucograma de estrés | 172 | 0.300 | 171 | 11 | 1 | 0.994 | 0.940 | 0.944 | 0.966 | 0.983 |
| Anemia no regenerativa | 42 | 0.456 | 42 | 1 | 0 | 1.000 | 0.977 | 0.997 | 0.988 | 0.972 |
| Hemólisis/MCHC | 48 | 0.714 | 45 | 3 | 3 | 0.938 | 0.938 | 0.991 | 0.938 | 0.988 |
| Policitemia | 32 | 0.900 | 32 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| Anemia regenerativa | 6 | 0.479 | 5 | 9 | 1 | 0.833 | 0.357 | 0.975 | 0.500 | 0.889 |

*Tabla 6.2. Métricas finales del modelo por etiqueta en conjunto de prueba.* 

[FIGURA image20]

*Figura 6.1. Curvas ROC y Precision-Recall del modelo HemoVet v4 en el conjunto de prueba.*

Las curvas ROC y de Precision-Recall validan la buena separación entre clases para la mayoría de las etiquetas. Sin embargo, en el caso de una clasificación clínica desequilibrada, se prefieren el PR-AUC y el F1 operativo, ya que estas métricas son más sensibles a los errores de falsos positivos y falsos negativos de la clase positiva.

### **6.1.2. Intervalos de confianza bootstrap** 

Los intervalos de confianza del 95 % se determinaron mediante remuestreo bootstrap para estimar la incertidumbre en las métricas. La tabla 6.3 revela que los intervalos de las etiquetas con valores de soporte más altos son pequeños, y los de PATRON_ANEMIA_REGENERATIVA son amplios, lo cual concuerda con el número de ocurrencias en la etiqueta. Esta amplitud es lo suficientemente grande como para justificar su uso continuado como resultado oficial de bajo soporte, en lugar de como un resultado totalmente consolidado.

| Etiqueta | Recall medio | IC95 Recall | F1 medio | IC95 F1 | PR-AUC medio | IC95 PR-AUC |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| QC requiere frotis | 0.681 | [0.6046, 0.7561] | 0.726 | [0.6617, 0.7843] | 0.844 | [0.7932, 0.8889] |
| Patrón inflamatorio | 0.995 | [0.9838, 1.0] | 0.987 | [0.9746, 0.9974] | 0.993 | [0.9792, 1.0] |
| Leucograma de estrés | 0.994 | [0.9819, 1.0] | 0.966 | [0.946, 0.9858] | 0.983 | [0.962, 0.9965] |
| Anemia no regenerativa | 1.000 | [1.0, 1.0] | 0.988 | [0.96, 1.0] | 0.973 | [0.9117, 1.0] |
| Hemólisis/MCHC | 0.936 | [0.8571, 1.0] | 0.936 | [0.8764, 0.9811] | 0.987 | [0.9603, 1.0] |
| Policitemia | 1.000 | [1.0, 1.0] | 1.000 | [1.0, 1.0] | 1.000 | [1.0, 1.0] |
| Anemia regenerativa | 0.832 | [0.4429, 1.0] | 0.485 | [0.1654, 0.7619] | 0.887 | [0.562, 1.0] |

*Tabla 6.3. Intervalos de confianza bootstrap al 95% por etiqueta.*

[FIGURA image21]*Figura 6.2. Rendimiento final del modelo HemoVet v4 con intervalos de confianza al 95%.*

### **6.1.3. Evolución del modelo v3 a v4** 

La comparación entre la v3 y la v4 indica que, si bien la actualización no supuso una mejora uniforme en el PR-AUC, sí aumentó el recall macro y condujo a un mejor comportamiento operativo para determinadas etiquetas. El cambio más significativo se observó en QC_REQUIERE_FROTIS, donde el recall aumentó a costa de un mayor número de falsos positivos, y en PATRON_POLICITEMIA, donde el recall pasó de 0.8750 a 1.0000 en el conjunto de prueba.

| Etiqueta | PR-AUC v3 | PR-AUC v4 | Delta PR-AUC | F1 v3 | F1 v4 | Delta F1 | Recall v3 | Recall v4 | Delta Recall |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| QC requiere frotis | 0.861 | 0.846 | -0.015 | 0.711 | 0.729 | +0.018 | 0.588 | 0.684 | +0.096 |
| Patrón inflamatorio | 0.994 | 0.993 | -0.001 | 0.988 | 0.988 | +0.000 | 0.995 | 0.995 | +0.000 |
| Leucograma de estrés | 0.986 | 0.983 | -0.003 | 0.972 | 0.966 | -0.006 | 0.994 | 0.994 | +0.000 |
| Anemia no regenerativa | 0.985 | 0.972 | -0.013 | 0.988 | 0.988 | +0.000 | 1.000 | 1.000 | +0.000 |
| Hemólisis/MCHC | 0.992 | 0.988 | -0.005 | 0.936 | 0.938 | +0.001 | 0.917 | 0.938 | +0.021 |
| Policitemia | 1.000 | 1.000 | +0.000 | 0.933 | 1.000 | +0.067 | 0.875 | 1.000 | +0.125 |
| Anemia regenerativa | 0.886 | 0.889 | +0.003 | 0.500 | 0.500 | +0.000 | 0.833 | 0.833 | +0.000 |

*Tabla 6.4. Comparación de métricas entre v3 y v4 en conjunto de prueba.* 

*[FIGURA image22]*

*Figura 6.3. Evolución de PR-AUC y F1 por versión del modelo en el conjunto de prueba.*

*[FIGURA image23]*

*Figura 6.4. Heatmap comparativo de F1 y PR-AUC por versión del modelo.*

El comportamiento observado confirma un conflicto previsto entre sensibilidad y precisión. Si el sistema está orientado a ofrecer orientación a los propietarios, puede resultar aceptable aumentar la sensibilidad del sistema, siempre y cuando el resultado no sea un diagnóstico, sino una llamada a la acción para revisar el sistema. No obstante, este aumento debe equilibrarse para no activar demasiadas alarmas, especialmente en el caso de etiquetas de control de calidad o patrones en los que existe un solapamiento clínico significativo.

### **6.1.4. Explicabilidad mediante SHAP** 

Mediante la explicación global de características de SHAP, fue posible comprobar si el modelo se basaba en variables del sistema hematológico que coincidían con cada etiqueta. En las etiquetas eritroides predominan las variables: HCT, HGB, RBC y variables de reticulocitos; en las etiquetas leucocitarias predominan las variables: monocitos, linfocitos, WBC y variables derivadas; en las etiquetas asociadas a las variables directamente relacionadas con los índices eritroides, predominan variables como MCHC o la policitemia. Se trata de un cuadro hematológico típico.

[FIGURA image24]

*Figura 6.5. Importancia global de características por etiqueta mediante SHAP.*

## **6.2. Validación externa con Dog Aging Project** 

La validación externa se llevó a cabo con 1,301 registros del Dog Aging Project (DAP). Esta cohorte no era adecuada para el esquema supervisado de HemoVet y, por lo tanto, no incluía etiquetas adecuadas para el cálculo de F1 y PR-AUC para el DAP. Su objetivo era medir el desplazamiento de dominio y la consistencia biológica mediante las tasas de activación, sin volver a entrenar el modelo ni modificar su umbral.

El análisis reveló un desplazamiento elevado en los monocitos y cambios moderados en los leucocitos, los neutrófilos, las plaquetas, el hematocrito (HCT), la concentración media de hemoglobina en los glóbulos rojos (MCHC), el volumen medio de plaquetas (MPV) y el volumen medio de glóbulos rojos (MCV). Esta diferencia era previsible, ya que la población de IDEXX es de carácter local y clínico, mientras que la del DAP es independiente desde el punto de vista geográfico y externo, y en su mayoría sana.

| Etiqueta | Activación IDEXX | Activación DAP | Ratio DAP/IDEXX | Diagnóstico de coherencia |
| :---- | :---- | :---- | :---- | :---- |
| QC requiere frotis | 36.86% | 28.52% | 0.774 | aprox comparable |
| Patrón inflamatorio | 53.66% | 1.77% | 0.033 | OK esperado (DAP sano) |
| Leucograma de estrés | 46.61% | 19.14% | 0.411 | aprox comparable |
| Anemia no regenerativa | 11.38% | 0.61% | 0.054 | OK esperado (DAP sano) |
| Hemólisis/MCHC | 13.01% | 1.84% | 0.142 | OK esperado (DAP sano) |
| Policitemia | 8.67% | 2.15% | 0.248 | OK esperado (DAP sano) |
| Anemia regenerativa | 0.00% | 0.08% | inf | WARNING ALTO -- posible sobreprediccion |

*Tabla 6.5. Tasas de activación comparativas entre IDEXX y DAP.* 

*[FIGURA image25]*

*Figura 6.6. Comparación de tasas de activación entre IDEXX y DAP.*

Los porcentajes de activación de PATRON_INFLAMATORIO, PATRON_ANEMIA_NO_REGENERATIVA, PATRON_HEMOLISIS_MCHC y PATRON_POLICITEMIA fueron significativamente más bajos en DAP que en IDEXX. Este hallazgo concuerda con la diferencia entre una población clínica y una población de investigación externa. Sin embargo, QC_REQUIERE_FROTIS y PATRON_LEUCOGRAMA_ESTRES presentan tasas menos divergentes y, por lo tanto, deben supervisarse durante futuras implementaciones para garantizar que no muestren una actividad excesiva en un entorno no clínico.

## **6.3. Validación clínica con médicos veterinarios** 

Entre el periodo de 25/05/2026 y el 18/06/2026 se utilizaron 60 lotes (526 casos en total, 509 evaluables por el modelo), dos evaluadores veterinarios y 4 semanas de revisión para la validación clínica. El modelo v3 se probó durante S1, S2 y S3, y el v4 se probó durante S4.

| Semana | Periodo | Batches | Casos | Modelo |
| :---- | :---- | :---- | :---- | :---- |
| S1 | 25-29 may 2026 | 12 | 116 | v3 |
| S2 | 2-7 jun 2026 | 12 | 100 | v3 |
| S3 | 9-13 jun 2026 | 12 | 105 | v3 |
| S4 | 14-18 jun 2026 | 24 | 205 | v4 |

   
*Tabla 6.6. Distribución semanal de la validación clínica.*

| Métrica | Valor |
| :---- | :---- |
| Casos totales | 526 |
| Casos evaluables con modelo | 509 |
| Evaluadores veterinarios | 2 |
| Semanas evaluadas | 4 |
| Batches revisados | 60 |
| Macro kappa M1 vs M2 | 0.684 |
| Macro kappa modelo vs M1 | 0.629 |
| Macro F1 modelo vs M1 | 0.704 |

*Tabla 6.7. Resumen global de la validación clínica.*

No se interpretó la validación clínica como una comparación con una verdad absoluta. Además, existe variabilidad en el juicio humano respecto a patrones con solapamiento fenotípico y/o menor respaldo en el campo de la hematología. Por lo tanto, primero se comprobó la concordancia entre los dos veterinarios y, posteriormente, se comparó el modelo con cada evaluador.

### **6.3.1. Concordancia interevaluador** 

El límite máximo para el problema de rendimiento humano se basó en la concordancia entre el Veterinario 1 y el Veterinario 2. Se observó un alto nivel de concordancia, aunque no total, entre M1 y M2; el macro-kappa fue de 0.684. Se trata de un resultado metodológico, ya que la posibilidad de que cualquier discrepancia entre el modelo y el clínico no se interpretara como un error del modelo.

[FIGURA image26]

*Figura 6.7. Concordancia entre* Veterinario *1 y* Veterinario *2 por semana y etiqueta.*

*[FIGURA image27]*

*Figura 6.8. Mapa completo de Cohen kappa por semana, etiqueta y tipo de comparación.*

### **6.3.2. Concordancia modelo-clínico** 

El macro-kappa del modelo con el Veterinario 1 fue de 0.629 y el macro-F1 con el Veterinario 1 fue de 0.704. Los valores mostraron que el sistema era capaz de aproximarse al juicio del médico principal a un nivel similar a la variabilidad entre evaluadores, con claras debilidades específicas en cada etiqueta. Las puntuaciones más altas se observaron en PATRON_INFLAMATORIO y QC_AGREGADOS_PLAQUETARIOS. Se detectaron debilidades en relación con el leucograma de estrés, la policitemia y la hemólisis/MCHC.

| Etiqueta | F1 | Sensibilidad | Especificidad |
| :---- | :---- | :---- | :---- |
| QC requiere frotis | 0.788 | 0.768 | 0.884 |
| Patrón inflamatorio | 0.863 | 0.901 | 0.876 |
| Leucograma de estrés | 0.689 | 0.841 | 0.733 |
| Anemia no regenerativa | 0.652 | 0.548 | 0.974 |
| Hemólisis/MCHC | 0.597 | 0.597 | 0.944 |
| Policitemia | 0.592 | 0.463 | 0.981 |
| Anemia regenerativa | 0.610 | 0.514 | 0.987 |
| Agregados plaquetarios | 0.839 | 0.743 | 0.998 |

*Tabla 6.8. Resultados globales del modelo frente al* Veterinario *1 en validación clínica.* 

[FIGURA image28]

*Figura 6.9. Concordancia del modelo v3 frente a médicos veterinarios en S1-S3.*

*[FIGURA image29]*

*Figura 6.10. Precisión, recall y F1 por etiqueta frente al* Veterinario *1 en la validación clínica global.*

*[FIGURA image30]*

*Figura 6.11. Sensibilidad y especificidad por etiqueta en la validación clínica.*

### **6.3.3. Impacto del reentrenamiento clínico v3 a v4** 

El reentrenamiento a la versión v4 se llevó a cabo debido a las discrepancias observadas durante las tres primeras semanas de validación. Los parámetros QC_REQUIERE_FROTIS, PATRON_INFLAMATORIO, PATRON_HEMOLISIS_MCHC y PATRON_POLICITEMIA mejoraron al comparar los periodos anteriores con el S4, mientras que PATRON_ANEMIA_REGENERATIVA experimentó un ligero descenso. Este análisis respalda la conclusión de que el ajuste mitigó una serie de señales operativas, pero no resolvió los problemas de rendimiento relacionados con las etiquetas de bajo soporte o con aquellas que presentaban una discrepancia clínica significativa.

[FIGURA image31]

*Figura 6.12. Cohen kappa del modelo frente al* Veterinario *1 antes y después del reentrenamiento.*

*[FIGURA image32]*

*Figura 6.13. Impacto del reentrenamiento v3 a v4 en la concordancia con médicos veterinarios.*

### **6.3.4. Análisis de desacuerdos** 

El análisis de discrepancias reveló que PATRON_LEUCOGRAMA_ESTRES tendía a clasificar erróneamente los casos que el evaluador no había etiquetado como estrés, lo que indica falsos positivos del modelo a la hora de detectar configuraciones hematológicas asociadas al estrés. La etiqueta PATRON_POLICITEMIA mostró diagnósticos falsos negativos, lo que sugiere que el modelo adopta un enfoque más conservador con esta clase en comparación con la práctica clínica. Las discrepancias observadas en PATRON_HEMOLISIS_MCHC fueron una combinación de problemas con los criterios clínicos y una preocupación por la circularidad en la aplicación del MCHC.

[FIGURA image33]

*Figura 6.14. Falsos positivos y falsos negativos por etiqueta frente al* Veterinario *1.*

Estas diferencias deben tomarse con cautela. Un falso positivo puede dar lugar a una recomendación de consultar a un veterinario, y un falso negativo puede hacer que se pase por alto algo importante para la discusión clínica. Por ello, la redacción del sistema está orientada a ofrecer orientación, advertencias sobre el alcance y una referencia clara a un profesional.

## **6.4. Resultados del módulo LLM/RAG** 

El módulo conversacional se analizó en el marco del flujo de trabajo operativo adoptado en la plataforma y descrito en el capítulo V: control del alcance mediante medidas de seguridad, recuperación de fuentes del corpus RAG, generación de la respuesta y validación del resultado. En este capítulo no se repite la construcción técnica del componente, pero se evalúa su comportamiento en condiciones de uso mediante diversas pruebas, entre las que se incluyen la seguridad, la robustez, la coherencia y la revisión veterinaria.

Se utilizaron tres métodos complementarios de validación: una evaluación de seguridad mediante red teaming, que incluía un conjunto de preguntas clasificadas por riesgo; cuatro baterías de pruebas automatizadas, realizadas en el propio canal de producción; y una evaluación de la exactitud clínica, llevada a cabo por dos veterinarios.

### **6.4.1. Seguridad conversacional y refuerzo de guardrails** 

El asistente recopiló un conjunto de 770 preguntas organizadas en función del tipo de riesgo: diagnóstico directo, medicamentos/dosis, intentos de manipulación o inyección, alucinaciones, preguntas fuera del ámbito de aplicación o solicitudes de fuentes, tal y como las plantearía un usuario real al interactuar con el endpoint de producción. La evaluación se llevó a cabo en dos fases: en la primera ronda se realizó la exposición y, en la segunda, se reforzaron las reglas de seguridad.

| Límite de seguridad | Ronda inicial | Ronda final |
| :---- | :---- | :---- |
| Resistencia a la manipulación (prompt injection) | 61 | 1 |
| No afirmar un diagnóstico definitivo | 25 | 2 |
| No responder fuera de su ámbito | 11 | 1 |
| No filtrar instrucciones internas | 6 | 0 |

   
*Tabla 6.9. Veces que el asistente cruzó cada límite de seguridad (ronda inicial vs. final).*

[FIGURA image34]

*Figura 6.15. Límites de seguridad cruzados, antes y después del refuerzo.*

*[FIGURA image35]*

*Figura 6.16. Reducción de fallos por categoría de riesgo.*

Los errores restantes en la última ronda no eran peligrosos. Se debían a una decisión sobre el ámbito de aplicación; en este caso, la pregunta ¿Este hemograma completo indica anemia? la formula con cautela el asistente, que no establece un diagnóstico, y el criterio de evaluación considera que esta pregunta debería dar lugar a una derivación, y no al resultado de la respuesta del asistente. También se debían a los tiempos de respuesta asociados a la generación basada en la CPU sin GPU.

[FIGURA image36]

*Figura 6.17. Naturaleza de los fallos que persisten tras el refuerzo (ninguno de seguridad).*

### **6.4.2. Ámbito y seguridad sobre el pipeline real (batería A)** 

Sobre 90 casos evaluados en tres modos de uso contra el pipeline real de producción:

| Indicador | Valor |
| :---- | :---- |
| Prompts adversariales rechazados | 31 / 40 (77.5 %) |
| Prompts legítimos aceptados | 15 / 20 (75.0 %) |
| Fuera de ámbito con mensaje claro | 17 / 30 (56.7 %) |
| Latencia media (respuestas generadas) | 24.1 s |

   
*Tabla 6.10. Resultados de ámbito y seguridad del asistente (pipeline real).*

[FIGURA image37]

*Figura 6.18. Tasas de acierto de la batería A por modo de uso.*

El asistente rechaza la mayoría de solicitudes adversariales y acepta la mayoría de consultas educativas legítimas. La claridad del mensaje fuera de ámbito (56.7 %) evidencia una limitación conocida: en parte de los casos el mensaje se lee como "problema técnico" en vez de “fuera de ámbito”, hallazgo que se entrega al equipo de desarrollo.

### **6.4.3. Robustez ortográfica y memoria multi-turno (baterías B y C)** 

Se dio una respuesta sustantiva a las 20 variantes con errores ortográficos (20/20): una consulta mal redactada no reduce la utilidad del asistente. Los 17 turnos de la batería C incluyeron 9 turnos de seguimiento en los que el modelo respondió de forma sustantiva a la entrada; 15 turnos fueron de este tipo, y dos fueron tiempos de espera del modelo debidos a un fallo transitorio de la infraestructura de la CPU, no a una pérdida de contexto.

[FIGURA image38]

*Figura 6.19. Robustez ortográfica (batería B) y memoria multi-turno (batería C).*

### **6.4.4. Consistencia de fuentes (batería D)** 

Se observó un alto nivel de coherencia en las fuentes citadas para cada consulta repetida cinco veces con un nivel de 0.1 (índice de Jaccard medio de 0.84; tres de las cinco consultas mostraron una coherencia total en cuanto a la medida de seguridad adoptada).

[FIGURA image39]

*Figura 6.20. Consistencia de fuentes citadas entre 5 repeticiones (índice de Jaccard).*

### **6.4.5. Exactitud de contenido - rúbrica veterinaria (batería E)** 

Las respuestas del asistente a las 30 preguntas se remitieron a dos veterinarios para que las evaluaran de forma independiente y ciega en tres aspectos: exactitud clínica, idoneidad de las citas y seguridad clínica.

| Dimensión | Veterinario 1 | Veterinario 2 |
| :---- | :---- | :---- |
| Respuestas seguras clínicamente | 30 / 30 (100 %) | 30 / 30 (100 %) |
| Correctas | 11 / 30 (36.7 %) | 14 / 30 (46.7 %) |
| Parcialmente correctas | 14 / 30 (46.7 %) | 11 / 30 (36.7 %) |
| Incorrectas | 5 / 30 (16.7 %) | 5 / 30 (16.7 %) |
| Alucinadas | 0 / 30 (0 %) | 0 / 30 (0 %) |
| Citas apropiadas | 19 / 30 (63.3 %) | 19 / 30 (63.3 %) |

   
*Tabla 6.11. Evaluación de exactitud clínica del asistente por dos veterinarios (batería E).*

[FIGURA image40]

*Figura 6.21. Distribución de la exactitud clínica según cada veterinario.*

*[FIGURA image41]*

*Figura 6.22. Seguridad clínica y adecuación de citas.*

Ambos evaluadores coincidieron en que el asistente no estableció diagnósticos definitivos ni planes de tratamiento, y no intentó diagnosticar ni tratar ningún caso en esta ronda; únicamente derivó a un veterinario cuando fue apropiado. Según la puntuación más conservadora de los dos evaluadores, el 83.3 % de las respuestas fueron correctas o parcialmente correctas (intervalo de confianza del bootstrap del 95 %: 70-97 %) y ninguna respuesta fue alucinada. Cinco respuestas fueron calificadas como incorrectas por ambos evaluadores y representaron el 16.7 % restante de las respuestas. En todos los casos se trataba de errores de contenido (explicaciones fisiológicas mal definidas o mal aplicadas) y se señalaron en el corpus y en el prompt para su corrección.

La concordancia entre los dos veterinarios fue casi perfecta (27 de 30 casos idénticos en exactitud; los tres desacuerdos, todos entre categorías vecinas):

| Dimensión | Acuerdo obs. | kappa de Cohen | PABAK | AC1 de Gwet | kappa ponderado |
| :---- | :---- | :---- | :---- | :---- | :---- |
| Exactitud | 90.0 % | 0.841 | 0.800 | 0.855 | 0.904 |
| Cita apropiada | 100 % | 1.000 | 1.000 | 1.000 | - |
| Seguridad clínica | 100 % | indefinido1 | 1.000 | 1.000 | - |

 *Tabla 6.12. Concordancia inter-evaluador de la rúbrica de exactitud (batería E).*

*1 El kappa de Cohen queda indefinido cuando no hay varianza (ambos marcaron el 100 % seguro); por eso se reportan PABAK y AC1 de Gwet, robustos a los marginales desbalanceados (paradoja de kappa).*

*[FIGURA image42]*

*Figura 6.23. Concordancia inter-evaluador por dimensión y estadístico.*

En general, tras el refuerzo, el módulo LLM/RAG es seguro, robusto en lo que respecta a los errores de redacción, coherente con la fuente, clínicamente seguro y, en su mayor parte, preciso, según los criterios veterinarios, pero puede mejorarse en cuanto a la idoneidad de las citas. Su mantenimiento continuo debería basarse en pruebas periódicas con entradas adversarias, la validación de los resultados y el seguimiento de las conversaciones. Esta validación de la precisión se describe como de carácter piloto, llevada a cabo por dos evaluadores y con 30 preguntas; véanse las limitaciones en el capítulo VII.

## **6.5. Resultados de rendimiento técnico y pruebas** 

La prueba de rendimiento de inferencia consistió en 1,000 solicitudes en curso realizadas al motor de aprendizaje automático, sin incluir HTTP, autenticación, base de datos ni RAG. La latencia media fue de 28.73 ms, con un p50 de 27.93 ms y un p95 de 33.9 ms. Estos valores sugieren que la principal limitación del sistema no es la inferencia del modelo, sino que la extracción, la persistencia, la comunicación de red y la generación de conversaciones serán los factores principales que afecten a los tiempos de respuesta percibidos por el usuario.

| Indicador | Valor |
| :---- | :---- |
| Solicitudes medidas | 1000 |
| Warmup | 50 |
| Latencia mínima | 9.98 ms |
| Latencia media | 28.73 ms |
| p50 | 27.93 ms |
| p95 | 33.9 ms |
| p99 | 137.95 ms |
| Pruebas backend | 25 pruebas exitosas en 1.45s |

*Tabla 6.13. Resultados de rendimiento de inferencia y pruebas backend.*

## **6.7. Resultados de la validación de usabilidad del prototipo** 

El prototipo funcional descrito en el capítulo V, que incluía la pantalla de inicio, el flujo de trabajo de carga y revisión del hemograma completo, la presentación de resultados, los mensajes de alcance y los elementos de asistencia al usuario, se utilizó para la validación de la usabilidad. Esta evaluación no tenía como objetivo medir el rendimiento clínico ni la precisión de los modelos, sino determinar si los usuarios objetivo comprendían la interfaz y percibían el valor del flujo de trabajo de orientación hematológica.

Se entregó un cuestionario a 44 usuarios del prototipo para evaluar su usabilidad. El cuestionario constaba de 13 preguntas, cada una de ellas valorada en una escala de Likert del 1 al 5, basadas en las fases del recorrido del usuario: pantalla de inicio, proceso de análisis, resultado y comprensión, y ayuda/utilidad, así como tres preguntas abiertas. La muestra es representativa del público objetivo: el 50 % son propietarios de mascotas y el 77 % nunca había visto un hemograma completo, lo que significa que se trataba de usuarios sin conocimientos especializados.

### **6.7.1. Resultados cuantitativos** 

La media global fue de 4.37/5, lo que supone una valoración positiva; tras normalizar la media mediante la fórmula ((media - 1\) / 4\) × 100, se obtuvo un índice de usabilidad de 84/100; el resto de valoraciones también fueron positivas en su conjunto. De los 13 ítems, el 81.6 % (4+5) de las respuestas fueron favorables, mientras que el 0 % (1+2) fueron desfavorables.

| Dimensión | Media | % favorable | Índice /100 |
| :---- | :---- | :---- | :---- |
| Pantalla principal y diseño | 4.33 | 82.6 % | 83.3 |
| Proceso de análisis | 4.40 | 82.6 % | 85.0 |
| Resultados y comprensión | 4.45 | 84.1 % | 86.2 |
| Ayuda, confianza y utilidad | 4.27 | 76.5 % | 81.8 |
| Global | 4.37 | 81.6 % | 84.3 |

   
*Tabla 6.14. Usabilidad percibida por dimensión (n \= 44).*

[FIGURA image43]

*Figura 6.24. Índice de usabilidad (0-100) por dimensión.*

*[FIGURA image44]*

*Figura 6.25. Media por afirmación (13 ítems, escala 1-5).*

*[FIGURA image45]*

*Figura 6.26. Distribución de respuestas por afirmación (solo se registraron valores 3-5).*

*[FIGURA image46]*

*Figura 6.27. Perfil de los participantes.*

Las afirmaciones que recibieron las puntuaciones más altas fueron: los resultados eran fáciles de entender (4.52), el lenguaje utilizado era claro para un usuario no experto (4.45) y el usuario sabía que debía revisar los valores antes de confirmarlos (4.43). Las cifras justifican dos decisiones clave de diseño: la traducción del hemograma completo (CBC) a un lenguaje sencillo y la necesidad de una revisión humana.

### **6.7.2. Resultados cualitativos** 

El diccionario/glosario, la guía de tres pasos, la posibilidad de corregir valores extraídos erróneamente, el resumen final, los colores semánticos de los resultados, el aviso de que el sistema no debe sustituir al veterinario y el modo invitado son los puntos fuertes más valorados, todos ellos elecciones de diseño deliberadas. Las fuentes de confusión señaladas y las mejoras solicitadas son específicas y aplicables, y varias de ellas repiten problemas conocidos, como la velocidad de los chats, los problemas de memoria (latencia de la CPU), las dudas sobre si los chats son reales (validados por veterinarios como reales) y otras áreas relacionadas.

[FIGURA image47]

*Figura 6.28. Aspectos mejor valorados por los participantes.*

*[FIGURA image48]*

*Figura 6.29. Temas más mencionados en confusiones y mejoras solicitadas.*

Esta validación se basa en una muestra de conveniencia (n \= 44\) y en un instrumento personalizado, en lugar de un cuestionario SUS estandarizado, para medir la usabilidad percibida. No incluye mediciones de tareas cronometradas ni una tasa de error observada. Las sugerencias citadas en el capítulo VII ofrecen más detalles sobre las mejoras solicitadas.

## **6.8. Síntesis de resultados** 

Los resultados así obtenidos permiten organizar el comportamiento de HemoVet en cinco áreas de análisis: rendimiento del motor de clasificación, validación externa, validación clínica, comportamiento del módulo conversacional y experiencia de usuario del prototipo. El motor de clasificación obtuvo buenos resultados técnicos en el conjunto de prueba, con un PR-AUC macro superior a 0,95 y un F1 macro superior a 0,87. El análisis a nivel de etiqueta demostró un mejor rendimiento: los patrones inflamatorios, el leucograma de estrés, la anemia no regenerativa, la hemólisis/MCHC y la policitemia se reconocieron como de buen rendimiento, con incertidumbre y apoyo, respectivamente, o como operativos; QC_REQUIERE_FROTIS y PATRON_ANEMIA_REGENERATIVA requerían mayor precaución.

Se utilizó el Dog Aging Project para la validación externa, pero no se pudo estimar el rendimiento supervisado debido a la falta de etiquetas equivalentes a las del sistema. Sin embargo, sí ofreció algunas perspectivas valiosas sobre el cambio de dominio y la consistencia de la activación en un grupo externo. Esta evaluación puso de manifiesto que existía cierta diferencia de distribución entre el corpus clínico local y la cohorte externa, especialmente en las variables hematológicas relevantes para la población y el instrumento, así como para el contexto clínico. Este resultado es un indicador de la generalizabilidad del modelo y subraya la necesidad de considerar la validación externa como una medida de la robustez distributiva más que de la precisión clínica.

La validación clínica con veterinarios resultó más compleja que el conjunto de pruebas interno. Se comprobó que el modelo era capaz de reproducir el juicio del evaluador principal, aunque también quedó patente que existían diferencias en los juicios entre los evaluadores humanos y discrepancias entre las etiquetas. Este comportamiento fue más pronunciado en los patrones con solapamiento hematológico, menor respaldo estadístico o mayor dependencia del contexto. Cabe señalar que, por lo tanto, los datos presentados en esta sección deben interpretarse como un reflejo de los niveles de acuerdo y desacuerdo, más que como una prueba concluyente del diagnóstico.

Con la muestra que se presentó a los evaluadores veterinarios, el módulo LLM/RAG funcionó de forma clínicamente segura en el proceso evaluado; los dos evaluadores veterinarios consideraron que las 30 respuestas eran clínicamente seguras. La mayoría de las respuestas también se consideraron correctas o parcialmente correctas, mientras que no se detectaron alucinaciones en la muestra evaluada, y aún había margen de mejora en cuanto a la idoneidad de las citas. Las pruebas de seguridad conversacional revelaron que se produjo una disminución significativa del número de fallos relacionados con la manipulación cuando se reforzaron las medidas de protección; sin embargo, aún se produjeron algunos fallos que debían ajustarse en la frontera entre la orientación educativa, el rechazo basado en el alcance y la respuesta cuando las pruebas aportadas no son suficientes.

Los resultados técnicos indicaron que la parte del sistema dedicada a la clasificación ofrecía una latencia aceptable para un uso interactivo, mientras que la parte conversacional presentaba limitaciones en el tiempo de respuesta cuando funcionaba sin el apoyo de una GPU. El módulo de vigilancia de la población sigue activo como visualización agregada de carácter exploratorio, pero los indicadores de geocodificación y concentración espacial no permiten la interpretación de un territorio. La validación de la usabilidad, que se llevó a cabo simultáneamente, arrojó una actitud positiva hacia el prototipo, ya que 44 participantes otorgaron un índice de usabilidad elevado y no se registraron valoraciones negativas; sin embargo, las respuestas abiertas indicaron que el prototipo debe mejorarse en cuanto a la claridad de las unidades, el uso de leyendas, la velocidad del chat, la memoria conversacional y la exportación o el intercambio de resultados.
