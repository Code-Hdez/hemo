# Preliminares — TEXTO ACTUAL, ÍNTEGRO Y VERBATIM

> Extraído de `P1 ICC 1910 — … (4).docx` el 12 de agosto de 2026. Es el texto que hay que
> modificar. Se han desescapado los artefactos de conversión y las imágenes se han sustituido por
> marcadores `[FIGURA imageNN]`; los pies de figura se conservan tal cual.
>
> **No se ha alterado ninguna palabra del contenido.** Los errores y las cifras desactualizadas que
> contiene son deliberados: son precisamente los que hay que corregir.

> **La Tabla de Contenido (líneas 27-300 del original) se ha excluido a propósito:** Word la
> regenera automáticamente y reproducirla aquí solo gastaría contexto. Sí se incluyen la Lista de
> Tablas, la de Figuras y la de Anexos, porque esas hay que rehacerlas a mano.

---

**PONTIFICIA UNIVERSIDAD CATÓLICA MADRE Y MAESTRA FACULTAD DE CIENCIAS DE LA INGENIERÍA**

**ESCUELA DE INGENIERÍA EN COMPUTACIÓN Y TELECOMUNICACIONES**

[FIGURA image1]

**Plataforma Inteligente de Interpretación Hematológica en la Especie Canina para Orientación Diagnóstica, Control de Calidad y Vigilancia Poblacional.**

**Un proyecto presentado como requisito parcial para optar por el título de Ingeniero en Telemático/Sistemas y Computación en la**

**Pontificia Universidad Católica Madre y Maestra**

**Presentado Por:**

Carlos David Hernández Collado (1014-8744)

Edwin Andrés Balbuena Bisonó (1014-9910)

**Asesora:**

Lisibonny Eustina Beato Castro

Docente e Ingeniería, Facultad de Ciencias e Ingeniería

**Santiago de los Caballeros, República Dominicana Agosto, 2026**

# **Lista de Tablas** 

| Elemento | Título | Página |
| :---- | :---- | :---- |
| Tabla 1 | Criterios mínimos de aceptación del Motor ML por etiqueta. |   |
| Tabla 2 | Mapa de artefactos del pipeline HemoVet por fase de desarrollo. |   |
| Tabla 3 | Cronograma del proyecto HemoVet organizado por frente de trabajo y tareas asociadas. |   |
| Tabla 4 | Estimación de costos de hardware del proyecto HemoVet. |   |
| Tabla 5 | Estimación de costos de software del proyecto HemoVet. |   |
| Tabla 6 | Casos de prueba prevalidados para la demostración de HemoVet. |   |
| Tabla 3.1 | Estrategia metodológica aplicada al desarrollo del software. |   |
| Tabla 3.2 | Fuentes de datos utilizadas en la metodología. |   |
| Tabla 3.3 | Política final de etiquetas del sistema HemoVet. |   |
| Tabla 3.4 | Métricas finales del modelo XGBoost v3 por etiqueta oficial. |   |
| Tabla 3.5 | Umbrales congelados en el conjunto de validación. |   |
| Tabla 3.6 | Tasas de activación comparativas entre corpus clínico local y cohorte externa DAP. |   |
| Tabla 3.7 | Procedimiento metodológico aplicado al módulo LLM/RAG. |   |
| Tabla 3.8 | Baterías de validación aplicadas al asistente LLM/RAG. |   |
| Tabla 3.9 | Rúbrica veterinaria utilizada para evaluar las respuestas del módulo LLM/RAG. |   |
| Tabla 3.10 | Dimensiones metodológicas utilizadas para evaluar la usabilidad percibida del prototipo. |   |
| Tabla 3.11 | Artefactos runtime registrados en el manifiesto final. |   |
| Tabla 4.1 | Actores del sistema HemoVet. |   |
| Tabla 4.2 | Casos de uso principales del sistema. |   |
| Tabla 4.3 | Requerimientos funcionales del sistema. |   |
| Tabla 4.4 | Requerimientos no funcionales del sistema. |   |
| Tabla 4.5 | Módulos backend y responsabilidades de diseño. |   |
| Tabla 4.6 | Contratos API versionados por grupo funcional. |   |
| Tabla 5.1 | Actividades principales desarrolladas en el pipeline de datos. |   |
| Tabla 5.2 | Decisiones de desarrollo aplicadas al motor de aprendizaje automático. |   |
| Tabla 5.3 | Política de salidas implementada en el sistema final. |   |
| Tabla 5.4 | Módulos del backend implementados por dominio funcional. |   |
| Tabla 5.5 | Patrón de responsabilidades aplicado dentro del backend. |   |
| Tabla 5.6 | Funcionalidades principales implementadas en el frontend. |   |
| Tabla 5.7 | Componentes desarrollados para el módulo LLM/RAG. |   |
| Tabla 5.8 | Gates técnicos aplicados al módulo de vigilancia poblacional. |   |
| Tabla 5.9 | Evidencias técnicas de verificación del sistema desarrollado. |   |
| Tabla 6.1 | Resumen del estado final del sistema HemoVet. |   |
| Tabla 6.2 | Métricas finales del modelo por etiqueta en conjunto de prueba. |   |
| Tabla 6.3 | Intervalos de confianza bootstrap al 95 % por etiqueta. |   |
| Tabla 6.4 | Comparación de métricas entre v3 y v4 en conjunto de prueba. |   |
| Tabla 6.5 | Tasas de activación comparativas entre IDEXX y DAP. |   |
| Tabla 6.6 | Distribución semanal de la validación clínica. |   |
| Tabla 6.7 | Resumen global de la validación clínica. |   |
| Tabla 6.8 | Resultados globales del modelo frente al Veterinario 1 en validación clínica. |   |
| Tabla 6.9 | Veces que el asistente cruzó cada límite de seguridad, ronda inicial vs. final. |   |
| Tabla 6.10 | Resultados de ámbito y seguridad del asistente sobre el pipeline real. |   |
| Tabla 6.11 | Evaluación de exactitud clínica del asistente por dos veterinarios. |   |
| Tabla 6.12 | Concordancia interevaluador de la rúbrica de exactitud. |   |
| Tabla 6.13 | Resultados de rendimiento de inferencia y pruebas backend. |   |
| Tabla 6.14 | Señales del reporte de vigilancia poblacional. |   |
| Tabla 6.15 | Usabilidad percibida por dimensión, n \= 44. |   |
| Tabla 7.1 | Cumplimiento de los objetivos específicos y evidencia de respaldo. |   |

# **Lista de Figuras** 

| Elemento | Título | Página |
| :---- | :---- | :---- |
| Figura 1 | Ejemplo de un hemograma completo canino generado por el analizador IDEXX ProCyte One. |   |
| Figura 2 | Diagrama del diseño a implementar. |   |
| Figura 3 | Calendario de Jira - Periodo: Enero - Abril. |   |
| Figura 3.1 | Diseño metodológico aplicado durante el desarrollo de HemoVet. |   |
| Figura 3.2 | Flujo metodológico seguido para el componente de inteligencia artificial. |   |
| Figura 3.3 | Distribución de la política final de etiquetas. |   |
| Figura 3.4 | PR-AUC del modelo XGBoost v3 por etiqueta oficial. |   |
| Figura 4.1 | Diagrama de casos de uso actualizado de HemoVet. |   |
| Figura 4.2 | Diagrama de componentes backend y servicios asociados. |   |
| Figura 4.3 | Flujo de análisis hematológico desde carga hasta resultado. |   |
| Figura 4.4 | Modelo lógico de datos de HemoVet. |   |
| Figura 4.5 | Secuencia de consulta al módulo LLM/RAG. |   |
| Figura 4.6 | Diagrama de despliegue lógico de HemoVet. |   |
| Figura 5.1 | Salida gráfica generada durante la verificación del motor de clasificación. |   |
| Figura 5.2 | Curvas Precision-Recall generadas como artefacto de evaluación del desarrollo del modelo. |   |
| Figura 5.3 | Visualización de la política de etiquetas utilizada durante la consolidación del sistema. |   |
| Figura 5.4 | Salida SHAP generada para auditar importancia global de características por etiqueta. |   |
| Figura 5.5 | Comparación de tasas de activación entre IDEXX y DAP como verificación fuera del dominio de entrenamiento. |   |
| Figura 6.1 | Curvas ROC y Precision-Recall del modelo HemoVet v4 en el conjunto de prueba. |   |
| Figura 6.2 | Rendimiento final del modelo HemoVet v4 con intervalos de confianza al 95 %. |   |
| Figura 6.3 | Evolución de PR-AUC y F1 por versión del modelo en el conjunto de prueba. |   |
| Figura 6.4 | Heatmap comparativo de F1 y PR-AUC por versión del modelo. |   |
| Figura 6.5 | Importancia global de características por etiqueta mediante SHAP. |   |
| Figura 6.6 | Comparación de tasas de activación entre IDEXX y DAP. |   |
| Figura 6.7 | Concordancia entre Veterinario 1 y Veterinario 2 por semana y etiqueta. |   |
| Figura 6.8 | Mapa completo de Cohen kappa por semana, etiqueta y tipo de comparación. |   |
| Figura 6.9 | Concordancia del modelo v3 frente a médicos veterinarios en S1-S3. |   |
| Figura 6.10 | Precisión, recall y F1 por etiqueta frente al Veterinario 1 en la validación clínica global. |   |
| Figura 6.11 | Sensibilidad y especificidad por etiqueta en la validación clínica. |   |
| Figura 6.12 | Cohen kappa del modelo frente al Veterinario 1 antes y después del reentrenamiento. |   |
| Figura 6.13 | Impacto del reentrenamiento v3 a v4 en la concordancia con médicos veterinarios. |   |
| Figura 6.14 | Falsos positivos y falsos negativos por etiqueta frente al Veterinario 1. |   |
| Figura 6.15 | Límites de seguridad cruzados, antes y después del refuerzo. |   |
| Figura 6.16 | Reducción de fallos por categoría de riesgo. |   |
| Figura 6.17 | Naturaleza de los fallos que persisten tras el refuerzo. |   |
| Figura 6.18 | Tasas de acierto de la batería A por modo de uso. |   |
| Figura 6.19 | Robustez ortográfica y memoria multi-turno. |   |
| Figura 6.20 | Consistencia de fuentes citadas entre cinco repeticiones. |   |
| Figura 6.21 | Distribución de la exactitud clínica según cada veterinario. |   |
| Figura 6.22 | Seguridad clínica y adecuación de citas. |   |
| Figura 6.23 | Concordancia interevaluador por dimensión y estadístico. |   |
| Figura 6.24 | Índice de usabilidad por dimensión. |   |
| Figura 6.25 | Media por afirmación en escala 1-5. |   |
| Figura 6.26 | Distribución de respuestas por afirmación. |   |
| Figura 6.27 | Perfil de los participantes. |   |
| Figura 6.28 | Aspectos mejor valorados por los participantes. |   |
| Figura 6.29 | Temas más mencionados en confusiones y mejoras solicitadas. |   |

# **Lista de Anexos** 

| Anexo | Título | Contenido principal |
| :---- | :---- | :---- |
| Anexo A | Matriz de riesgos actualizada del proyecto | Riesgos técnicos, clínicos, documentales, LLM/RAG, usabilidad, privacidad, vigilancia y despliegue. |
| Anexo B | Evidencia oficial de validación clínica con médicos veterinarios | Manifiestos, respuestas de Veterinario 1, Veterinario 2, modelo, métricas y comparación clínica-modelo. |
| Anexo C | Evidencia oficial de validación del asistente conversacional LLM/RAG | CSV/JSON de red-teaming, baterías A-E, robustez, memoria, consistencia, rúbricas y evaluación veterinaria. |
| Anexo D | Instrumento y resultados de la validación de usabilidad | Cuestionario, dimensiones, ítems Likert y resultados agregados de los 44 participantes. |

# **Agradecimientos – Carlos David Hernández Collado** 

# **Agradecimientos – Edwin Andrés Balbuena Bisonó** 

# **Dedicatoria – Carlos David Hernández Collado** 

# 

# **Dedicatoria – Edwin Andrés Balbuena Bisonó** 

# 

# **Resumen ejecutivo** 

El hemograma completo canino (CBC) es una de las pruebas diagnósticas más utilizadas en la medicina veterinaria de pequeños animales. Sin embargo, los resultados suelen facilitarse al propietario en forma de una lista de valores numéricos, unidades e intervalos de referencia, sin una síntesis interpretativa comprensible. Esta carencia dificulta que el ciudadano comprenda el significado general de la prueba y limita su capacidad para formular preguntas fundamentadas durante la consulta veterinaria.

HemoVet se ha desarrollado como una plataforma web orientada al ciudadano para la interpretación indicativa de los hemogramas completos caninos. El sistema integra un motor de clasificación multietiqueta basado en aprendizaje automático, reglas determinísticas de control de calidad, una API REST modular, una interfaz web para propietarios, un módulo de vigilancia poblacional agregada y una capa conversacional LLM/RAG con límites de seguridad clínica. La plataforma no emite diagnósticos definitivos, tratamientos, medicamentos ni dosis; su función es presentar los resultados hematológicos en un lenguaje accesible y facilitar la comunicación entre el propietario y el veterinario.

El motor de clasificación utiliza un conjunto final de 43 características hematológicas, que incluyen analitos directos del hemograma completo, indicadores clínicos, índices hematológicos y variables asociadas a los reticulocitos. El sistema genera siete etiquetas oficiales mediante un modelo probabilístico, dos etiquetas mediante reglas determinísticas y excluye una etiqueta del alcance final, documentando esta exclusión como una limitación. En el conjunto de prueba, el modelo alcanzó un PR-AUC macro de 0.9529, un F1 macro de 0.8727 y un recall macro de 0.9205.

La validación externa con 1,301 registros del Dog Aging Project permitió analizar el domain shift y la coherencia en la activación de las etiquetas en una cohorte externa. El sistema obtuvo un kappa macro de 0.629 y un F1 macro de 0.704 frente al evaluador principal, mientras que la concordancia entre los veterinarios alcanzó un kappa macro de 0.684.

El módulo conversacional se evaluó en el flujo de trabajo real utilizando baterías de pruebas de seguridad, robustez, memoria, coherencia de las fuentes y revisión veterinaria. En general, HemoVet demuestra la viabilidad técnica de combinar la clasificación hematológica automatizada, la explicación controlada y la visualización responsable para los ciudadanos.

# **Abstract** 

The canine complete blood count (CBC) is one of the most widely used diagnostic tests in small animal veterinary medicine. However, the results are typically provided to the owner as a list of numerical values, units, and reference ranges, without a comprehensible interpretive synthesis. This gap makes it difficult for the citizen to understand the overall meaning of the test and limits their ability to ask informed questions during the veterinary consultation.

HemoVet was developed as a citizen-oriented web platform for the indicative interpretation of canine CBCs. The system integrates a machine learning-based multilabel classification engine, deterministic quality control rules, a modular REST API, a web interface for owners, an aggregated population surveillance module, and an LLM/RAG conversational layer with clinical guardrails. The platform does not issue definitive diagnoses, treatments, medications, or dosages; its function is to present hematological findings in accessible language and guide communication between the owner and the veterinarian.

The classification engine utilizes a final set of 43 hematological features, including direct CBC analytes, clinical flags, hematological indices, and reticulocyte-associated variables. The system produces seven official labels using a probabilistic model, two labels through deterministic rules, and keeps one label excluded as a documented limitation. On the test set, the model achieved a macro PR-AUC of 0.9529, a macro F1 of 0.8727, and a macro recall of 0.9205.

External validation with 1,301 records from the Dog Aging Project allowed for the analysis of domain shift and activation coherence in an external cohort. The system obtained a macro kappa of 0.629 and a macro F1 of 0.704 against the primary evaluator, while the inter-rater agreement between veterinarians reached a macro kappa of 0.684.

The conversational module was evaluated on the real pipeline using test batteries for safety, robustness, memory, source consistency, and veterinary review. Overall, HemoVet demonstrates the technical feasibility of combining automated hematological classification, controlled explanation, and responsible citizen visualization.
