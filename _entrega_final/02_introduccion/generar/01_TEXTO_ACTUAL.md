# Introducción, objetivos, justificación y limitaciones — TEXTO ACTUAL, ÍNTEGRO Y VERBATIM

> Extraído de `P1 ICC 1910 — … (4).docx` el 12 de agosto de 2026. Es el texto que hay que
> modificar. Se han desescapado los artefactos de conversión y las imágenes se han sustituido por
> marcadores `[FIGURA imageNN]`; los pies de figura se conservan tal cual.
>
> **No se ha alterado ninguna palabra del contenido.** Los errores y las cifras desactualizadas que
> contiene son deliberados: son precisamente los que hay que corregir.

---

# **Introducción**

## **Antecedentes del problema**

Una de las prácticas de laboratorio más comunes en medicina veterinaria de pequeños animales es la interpretación del hemograma completo (CBC) [[1]](#bookmark=kix.2sp1wq1trcug). Su valor clínico reside no solo en los valores aislados, sino en los patrones hematológicos que emergen de la lectura relacional de las series eritroide, leucocitaria y plaquetaria. Sin embargo, cuando el resultado se entrega al propietario del paciente, este recibe un documento técnico y multivariado que carece de síntesis interpretativa: una lista de parámetros numéricos, unidades y rangos de referencia sin explicación de su significado integrado.

Diversos estudios de comunicación clínica veterinaria han demostrado que la información proporcionada a los propietarios supera sistemáticamente el nivel de lectura recomendado por organismos internacionales de salud, y que la terminología empleada en los informes de laboratorio resulta inaccesible para la mayoría de los propietarios evaluados [[2]](#bookmark=kix.7fsxepid0eq), [[3]](#bookmark=kix.szutss8i9xxo). Esta limitación se agrava en tres escenarios cada vez más frecuentes: cuando restricciones geográficas o económicas limitan el acceso presencial al veterinario, cuando la consulta se realiza por telemedicina sin mediación oral del profesional [[4]](#bookmark=kix.glrdrkiptqiv), y cuando se acumulan hemogramas seriados durante el seguimiento crónico de enfermedades como la ehrlichiosis canina [[5]](#bookmark=kix.7ypcggsbd32c). En este último escenario, el propietario se enfrenta a los datos sin herramientas que le permitan interpretar cada resultado de manera individual. Para dar respuesta a esta necesidad, el proyecto HemoVet aborda el análisis y la explicación caso a caso.

Los sistemas tecnológicos disponibles en el mercado presentan una brecha estructural: las interfaces de los analizadores IDEXX [[6]](#bookmark=kix.q6ybbkpm75l4) y Mindray [[7]](#bookmark=kix.9o3yxbmdx2jz), mencionados por ser los equipos de hematología veterinaria de mayor adopción y estandarización en la práctica clínica a nivel global, se limitan a señalar valores fuera de rango mediante flags cualitativos. Estos equipos no generan una síntesis clínica ni una explicación de patrones complejos diseñada para el usuario final. La deficiencia detectada no radica en la falta de datos hematológicos, sino en la ausencia de un mecanismo que transforme los valores tabulados del hemograma completo canino en información comprensible para una persona sin formación clínica especializada [[8]](#bookmark=kix.en9kbvzf6uhv), [[9]](#bookmark=kix.sxvreljxsj8k).

## **Antecedentes del proyecto**

El procesamiento de datos estructurados de hemograma para identificación de patrones diagnósticos es un campo activo en informática clínica veterinaria. Estudios recientes han aplicado modelos de ensamble (Random Forest y XGBoost) para identificar derivaciones portosistémicas (AUC 0.976) [[10]](#bookmark=kix.pqbc27s1uks6), infecciones por *Babesia canis* (sensibilidad 100%) [[11]](#bookmark=kix.nw4lqsbgj7t), leptospirosis (AUC 0.955) [[12]](#bookmark=kix.83aoj8qzgi53) e hipoadrenocorticismo (AUC 0.994) [[13]](#bookmark=kix.lbtkblt5pxhs) a partir de valores numéricos de hemograma y paneles bioquímicos. Estos trabajos confirman que las correlaciones multivariantes entre parámetros del CBC contienen información discriminatoria suficiente para múltiples tareas de clasificación clínica [[14]](#bookmark=kix.i069zqahukp9), [[15]](#bookmark=kix.wv2v259xzslx).

Sin embargo, un análisis crítico de la literatura existente revela que todas estas soluciones se han concebido con el veterinario como destinatario final. Sistemas como Anna, que integra clasificadores ML con historias clínicas electrónicas para proporcionar predicciones en tiempo real al clínico [[16]](#bookmark=kix.7h6ksws3qzax), presuponen un usuario con capacidad de contextualizar y validar resultados. Se ha determinado que las aplicaciones digitales actuales para propietarios de mascotas no incluyen ninguna herramienta para interpretar resultados de laboratorio [[17]](#bookmark=kix.lowkv9jbmqup), y se reporta que solo el 8% de los estudios de IA veterinaria aborda datos tabulares estructurados [[18]](#bookmark=kix.a8n5citahviu). Esta distribución confirma el vacío que el presente proyecto busca llenar.

La escasez de herramientas orientadas al usuario final y el bajo porcentaje de estudios sobre datos tabulares no son casuales, sino que responden a barreras tecnológicas documentadas en la especialidad. Específicamente, se ha señalado que la heterogeneidad instrumental entre analizadores (como las variaciones algorítmicas en los reportes de equipos comerciales) y las limitaciones en la cobertura de variables representan obstáculos metodológicos significativos para la implementación de aprendizaje automático en este dominio [[6]](#bookmark=kix.q6ybbkpm75l4), [[19]](#bookmark=kix.oxqs8dl2gkmg). Esta realidad técnica establece que cualquier nuevo sistema predictivo requerirá metodologías rigurosas de curación de datos, ingeniería de características multivariables y protocolos de validación externa para asegurar su solidez y capacidad de generalización.

## **Descripción del problema**

El hemograma canino es una prueba de alta disponibilidad en el ecosistema veterinario dominicano: se genera de forma rutinaria en distintos niveles de atención veterinaria mediante analizadores automatizados, y su informe se entrega sistemáticamente al propietario del paciente. Sin embargo, como se ha documentado, la disponibilidad de datos no equivale a comprensión [[20]](#bookmark=kix.i3gcj5tzfkax). El valor diagnóstico del hemograma no reside en los valores individuales, sino en los patrones que emergen de su interpretación relacional: un recuento bajo de plaquetas puede tener implicaciones clínicas radicalmente distintas en función del comportamiento concomitante de otros índices leucocitarios, eritroides y plaquetarios [[1]](#bookmark=kix.2sp1wq1trcug), [[21]](#bookmark=kix.fhbh92l5z2kj). Este grado de interpretación presupone formación especializada que el propietario, por definición, no posee.

Los analizadores IDEXX y Mindray, junto con sus interfaces de informes no generan ninguna representación del significado integrado de los resultados: señalan valores fuera de rango, pero no sintetizan patrones ni explican implicaciones clínicas para el usuario final [[6]](#bookmark=kix.q6ybbkpm75l4), [[7]](#bookmark=kix.9o3yxbmdx2jz). Las implicaciones prácticas son que el propietario, al recibir el informe, no tiene mecanismo para evaluar si la combinación de valores representa un hallazgo clínicamente significativo, una fluctuación fisiológica normal o un patrón que justifica consulta urgente.

Aunque el uso de aprendizaje automático sobre datos tabulares ha demostrado una alta eficacia para clasificar afecciones caninas complejas a partir del hemograma (como se evidencia en la detección de derivaciones portosistémicas [[10]](#bookmark=kix.pqbc27s1uks6) y en la identificación temprana de leptospirosis e hipoadrenocorticismo [[12]](#bookmark=kix.83aoj8qzgi53), [[13]](#bookmark=kix.lbtkblt5pxhs)), la literatura advierte que esta área se encuentra subexplotada. De hecho, una revisión reciente señala que el análisis de datos tabulares estructurados representa apenas un 8 % de las investigaciones actuales en inteligencia artificial veterinaria [[18]](#bookmark=kix.a8n5citahviu). A esta brecha de investigación se suma que los modelos predictivos existentes están diseñados exclusivamente para el entorno clínico asistencial. Una revisión sistemática sobre aplicaciones móviles de salud (mHealth) determinó que las herramientas digitales actuales dejan al margen al usuario final, ya que no ofrecen ninguna funcionalidad para que el propietario interprete resultados de laboratorio [[17]](#bookmark=kix.lowkv9jbmqup). Por lo tanto, el problema de ingeniería a resolver radica en la necesidad de desarrollar un sistema que integre ambos frentes: aprovechar computacionalmente el perfil tabular del hemograma canino para la clasificación automatizada de patrones, y traducir esos resultados a un formato estructurado y comprensible para el propietario, operando bajo principios de explicabilidad que no sustituyan el criterio clínico del veterinario [[8]](#bookmark=kix.en9kbvzf6uhv), [[9]](#bookmark=kix.sxvreljxsj8k), [[22]](#bookmark=kix.ftx5czj0vuyg).

## **Planteamiento inicial de la solución**

La solución propuesta se estructura en tres capas funcionales integradas.

El primero corresponde al núcleo analítico, constituido por el motor de clasificación multietiqueta y las reglas determinísticas de control de calidad que operan sobre los valores tabulares del hemograma completo canino.

El segundo corresponde al portal web para ciudadanos, concebido como un panel de control de orientación hematológica que organiza la experiencia del propietario en un resumen personal, una vista explicativa del resultado actual, una visualización longitudinal por mascota y un módulo de vigilancia comunitaria basado en los hemogramas completos registrados.

El tercero corresponde a la capa conversacional, en la que un modelo de lenguaje actúa como mecanismo de explicación y traducción controlada de los resultados, bajo límites explícitos que impiden la emisión de diagnósticos, tratamientos o dosificaciones.

En su versión final, HemoVet funciona como una plataforma web que incluye autenticación, gestión de mascotas, carga de hemogramas completos, extracción y revisión de valores, clasificación de patrones, consultas conversacionales con límites de seguridad y visualización agregada de la población. La plataforma no emite diagnósticos definitivos ni recomendaciones terapéuticas; su resultado se limita a orientar la conversación entre el propietario y el veterinario.

# **Objetivos del proyecto**

**Objetivo general**

Desarrollar una plataforma web orientada a los ciudadanos que integre la clasificación multietiqueta mediante aprendizaje automático a partir de datos tabulares de hemogramas completos caninos, una capa conversacional con límites de seguridad y un panel de orientación hematológica, con el fin de identificar patrones hematológicos de interés, comunicar sus resultados en un lenguaje comprensible al propietario, facilitar el control de calidad de la lectura y permitir la visualización individual y comunitaria de los hemogramas completos registrados.

**Objetivos específicos**

**Conformar** un conjunto de datos clínicos estructurado a partir de registros hematológicos caninos de clínicas locales de Santiago de los Caballeros y del Dog Aging Project, sometido a procesos de limpieza, imputación y estandarización.

**Construir** un modelo de aprendizaje automático de clasificación multietiqueta capaz de predecir anomalías hematológicas específicas (como indicios de infección, alteraciones eritroides o deficiencias plaquetarias) a partir de los valores tabulares del hemograma.

**Desarrollar** un portal web para ciudadanos que utilice el motor de clasificación y organice la experiencia del usuario en un resumen personal, un resultado actual explicativo, una vista de la evolución longitudinal por mascota.

**Crear** un módulo de vigilancia comunitaria que visualice, por zonas agregadas y con garantías de privacidad, la concentración de hemogramas completos registrados, la frecuencia de hallazgos indicativos y su actividad temporal, acompañado de advertencias metodológicas explícitas que impidan su interpretación como un diagnóstico confirmado o una prevalencia real en la población canina.

**Implementar** una capa de explicación conversacional basada en un modelo lingüístico con límites explícitos, destinada a explicar términos, valores, resultados y cambios observados entre los CBC, así como a orientar la preparación de preguntas para la consulta veterinaria, sin ofrecer diagnósticos, tratamientos ni dosis.

# **Justificación del proyecto**

El proyecto responde a una necesidad concreta y documentada en la República Dominicana, la cual se fundamenta en los siguientes tres planos complementarios:

**1. Accesibilidad para el ciudadano.** El propietario de un animal de compañía es el receptor final del hemograma, pero carece de herramientas para interpretarlo. Estudios de comunicación veterinaria reportan que la información entregada a los propietarios supera el nivel de legibilidad recomendado por organismos internacionales de salud [[2]](#bookmark=kix.7fsxepid0eq), [[3]](#bookmark=kix.szutss8i9xxo), y que las fallas en el intercambio informativo entre el profesional y el propietario constituyen una barrera estructural en la toma de decisiones sobre salud animal [[20]](#bookmark=kix.i3gcj5tzfkax), [[23]](#bookmark=kix.tss2ppthosm). Esta brecha es especialmente crítica en seguimientos crónicos (ehrlichiosis, babesiosis) donde el propietario acumula múltiples hemogramas y requiere interpretar cada resultado individualmente, así como en contextos de telemedicina veterinaria donde el resultado se entrega de forma asincrónica [[4]](#bookmark=kix.glrdrkiptqiv). HemoVet aborda la interpretación puntual de cada hemograma en el MVP.

**2. Relevancia epidemiológica regional e innovación.** La ehrlichiosis monocítica canina, cuyo vector *Rhipicephalus sanguineus* está presente en el Caribe, genera patrones hematológicos trifásicos de alta complejidad interpretativa [[5]](#bookmark=kix.7ypcggsbd32c). La falta de herramientas de interpretación representa una amenaza tangible en un contexto de alta prevalencia regional reportada [[24]](#bookmark=kix.w5vrfm18xq8z), [[25]](#bookmark=kix.7nlmf1jabflx). Tecnológicamente, solo el 8% de los estudios de IA veterinaria abordan datos tabulares estructurados [[18]](#bookmark=kix.a8n5citahviu) y ninguno de los identificados produce resultados dirigidos al propietario como usuario final [[17]](#bookmark=kix.lowkv9jbmqup). El presente proyecto cubre ese vacío.

**3. Viabilidad técnica e ingeniería responsable.** La separación entre el motor de clasificación probabilístico y la capa conversacional favorece que la clasificación pueda ser auditable independientemente del lenguaje utilizado para comunicarla, y que el módulo LLM actúe únicamente como capa de explicación controlada de patrones ya clasificados, sin capacidad de razonamiento diagnóstico independiente [[9]](#bookmark=kix.sxvreljxsj8k), [[22]](#bookmark=kix.ftx5czj0vuyg), [[26]](#bookmark=kix.s9g2rkxiqdym). Esta arquitectura responde a los principios de explicabilidad y responsabilidad en sistemas de apoyo informativo ciudadano en salud animal.

# **Limitaciones del proyecto** 

* **Alcance de especie:** El sistema está entrenado, diseñado y validado exclusivamente para pacientes caninos. No es aplicable a felinos, equinos ni humanos.

* **Datos de entrada:** El sistema procesa únicamente datos tabulares numéricos de hemogramas completos generados por analizadores automatizados. No procesa imágenes de frotis sanguíneos, radiografías, datos bioquímicos ni ningún otro parámetro clínico.

* **Carácter no sustitutivo:** Los patrones identificados son el resultado de cálculos probabilísticos y no constituyen diagnóstico clínico ni definitivo. El sistema no identifica enfermedades concretas como diagnósticos y exige derivación expresa al veterinario ante cualquier consulta clínica.

* **Capa conversacional:** El modelo de lenguaje integrado está limitado a traducir los patrones ya clasificados por el motor ML. No realiza razonamiento clínico independiente ni interpreta síntomas adicionales del paciente informados por el propietario.

* **Calidad de los datos:** La precisión de la clasificación asume que los valores del hemograma sean analíticamente válidos. Errores de calibración instrumental, hemólisis o artefactos preanalíticos no documentados producen clasificaciones inexactas.

* **Alcance del prototipo:** El prototipo no incluye conectividad nativa con software LIS de terceros (carga manual vía PDF), procesamiento de imágenes de frotis, ni integración bidireccional con historias clínicas electrónicas.
