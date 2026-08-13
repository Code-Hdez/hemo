# Respaldo en literatura de la metodología de validación del LLM (11/7/2026)

Revisión de papers y frameworks para verificar si la forma en que HemoVet valida el
asistente LLM (rúbrica con veterinarios, evaluación adversarial, kappa, RAG) es
metodológicamente sólida y está alineada con la práctica publicada. Sirve para
justificar la sección 3.7 (metodología del módulo LLM/RAG) y 6.4 (resultados).

## Veredicto

**La metodología está bien alineada con la práctica publicada.** Los cuatro pilares
que usa HemoVet son los mismos que la literatura reconoce como estándar:

1. **Rúbrica de evaluación humana por expertos** (exactitud, cita apropiada,
   seguridad clínica) → coincide con el marco **QUEST** y con Med-PaLM 2.
2. **Evaluación adversarial / red-teaming por categorías de riesgo** → coincide con la
   metodología de red-teaming de IA médica.
3. **Métricas de RAG** (citas correctas, faithfulness, rechazo por evidencia
   insuficiente) → coincide con RAGAS / RAG-X.
4. **Concordancia inter-evaluador con kappa de Cohen** → estándar establecido.

Las dos limitaciones reales (declararlas, no ocultarlas): **número de evaluadores (2)**
y **tamaño de muestra de contenido (30 preguntas)**, ambos por debajo de lo que
recomiendan los frameworks más exigentes para uso clínico. Son aceptables para un
proyecto de grado si se declaran como limitación.

## Marcos de referencia (qué hace la literatura)

### 1. QUEST — marco de evaluación humana de LLMs en salud
Revisión de literatura que deriva 5 principios y 17 dimensiones: **Quality**
(accuracy, relevance, completeness, consistency), **Understanding/Reasoning**,
**Expression** (clarity, empathy), **Safety/Harm** (bias, harm, fabrication),
**Trust**. Recomendaciones cuantitativas:
- Muestra: mínimo **100** ítems para educación al paciente; **130** para apoyo a
  decisión clínica.
- Evaluadores: **4** para educación/investigación; **6-7** para uso clínico (por
  implicaciones de seguridad).
- Concordancia: **Cohen's kappa ≥ 0.7**, usar kappa + ICC.
- Rúbrica: opciones explícitas con definiciones (Likert 1-5 o binaria).
- **Cegado (blinding):** solo 29% de los estudios lo hacen; se recomienda.
Fuente: *A framework for human evaluation of LLMs in healthcare derived from
literature review* (PMC11437138).

### 2. Med-PaLM 2 — el estudio de referencia
Rúbrica de **9 ejes** evaluada por médicos y por legos; **ranking pareado** de
respuestas del LLM vs. respuestas de médicos sobre 1066 preguntas de consumidores.
Las respuestas del LLM fueron preferidas sobre las de médicos en 8 de 9 ejes. Valida
que **comparar contra criterio médico** es la metodología gold-standard.
Fuente: *Toward expert-level medical question answering with LLMs*, Nature Medicine
2024 (s41591-024-03423-7).

### 3. CLEVER — Clinical LLM Evaluation by Expert Review
Framework de revisión por expertos para validar salidas clínicas de LLMs.
Fuente: JMIR AI 2025 (ai.jmir.org/2025/1/e72153).

### 4. Red-teaming de IA médica
Taxonomía de **8 categorías de ataque adversarial** y 24 sub-estrategias (dosis
peligrosa, bypass de contraindicaciones, mala orientación en urgencias, escalada
multi-turno, suplantación de autoridad). 6.9% de prompts adversariales lograron
respuestas dañinas en modelos SOTA. Valida el enfoque **por categorías de riesgo**.
Fuente: *Red-Teaming Medical AI: Systematic Adversarial Evaluation of LLM Safety
Guardrails in Clinical Contexts*, medRxiv 2026.

### 5. Evaluación de RAG
Separar **recuperación** de **generación**. Métricas: faithfulness (fidelidad a las
fuentes), citation accuracy, hallucination rate, answer relevance y **negative
rejection** (decir "la evidencia no alcanza" en vez de inventar). Frameworks: RAGAS,
RAG-X. La literatura resalta que el rechazo por evidencia insuficiente suele faltar y
es deseable.
Fuente: *RAG-X: Systematic Diagnosis of RAG for Medical QA*, arXiv 2026; RAGAS.

### 5b. Métodos de concordancia inter-evaluador de refuerzo (aplicados a la batería E)

Con dos evaluadores y variables categóricas, la medida por defecto es el **kappa de
Cohen**. Pero los datos reales de HemoVet exhiben el problema clásico: la dimensión de
**seguridad clínica se calificó positivamente en el 100 % de los casos**, lo que hace que
el kappa de Cohen quede **indefinido** (sin varianza) pese a un acuerdo observado perfecto.
Este fenómeno —alto acuerdo observado pero kappa bajo o indefinido cuando los marginales
están desbalanceados— es la **paradoja de kappa**, documentada desde Feinstein & Cicchetti
(1990). Para reforzar la validación con métodos reconocidos que la literatura recomienda
precisamente para este caso, se añadieron tres estadísticos complementarios:

1. **PABAK** — *Prevalence-Adjusted Bias-Adjusted Kappa* (Byrt, Bishop & Carlin, 1993).
   Neutraliza el efecto de la prevalencia y del sesgo entre evaluadores; se calcula como
   `2·Po − 1`. Recomendado como reporte conjunto con kappa cuando la prevalencia es
   extrema.
2. **AC1 de Gwet** (Gwet, 2008, *British Journal of Mathematical and Statistical
   Psychology*). Estadístico de acuerdo por azar diseñado para **no colapsar bajo la
   paradoja de kappa**; es el más estable cuando una categoría domina. Es hoy el
   sustituto recomendado del kappa en fiabilidad clínica con marginales sesgados.
3. **Kappa ponderado** (Cohen, 1968), ponderación cuadrática, para la variable *ordinal*
   correctitud (correcto > parcialmente correcto > incorrecto/alucinado): penaliza menos
   los desacuerdos entre niveles vecinos que los extremos, reflejando mejor la severidad
   real del desacuerdo.

Adicionalmente, las **tasas** de cada dimensión se acompañan de **intervalos de confianza
al 95 % por bootstrap** (remuestreo con reemplazo), práctica estándar para cuantificar la
incertidumbre en muestras pequeñas (n = 30). Alternativas equivalentes que también habrían
servido, y que quedan como opción de ampliación: **alfa de Krippendorff** (admite cualquier
número de evaluadores y datos faltantes) e **ICC** para escalas continuas.

Resultado en HemoVet: los tres estadísticos coinciden en concordancia alta (correctitud
κ = 0.841, PABAK = 0.800, AC1 = 0.855, κ ponderado = 0.904; seguridad κ indefinido pero
PABAK = AC1 = 1.000), confirmando que el acuerdo es real y no un artefacto de la métrica.
Fuentes: Byrt et al. 1993 (*J Clin Epidemiol* 46:423-429); Gwet 2008; Feinstein & Cicchetti
1990 (*J Clin Epidemiol* 43:543-549); Cohen 1968.

### 6. Contexto veterinario (dominio de HemoVet)
La evidencia es incipiente y se basa sobre todo en exámenes de opción múltiple (p. ej.
250 preguntas, ChatGPT o1Pro ~90%) y comparaciones LLM-vs-veterinario (oftalmología:
sin diferencia significativa entre ChatGPT-4.5 y oftalmólogos). **No se encontró
literatura de interpretación de hemogramas caninos por LLM** → refuerza la novedad de
HemoVet.
Fuentes: Frontiers Vet Sci 2025 (fvets.2025.1616566); Vet Ophthalmology 2026
(vop.70052).

## Mapeo: lo que hace HemoVet vs. la literatura

| Componente HemoVet | Equivalente en literatura | Estado |
| --- | --- | --- |
| Rúbrica E: correctitud / cita / seguridad | QUEST (Accuracy, Fabrication, Harm); Med-PaLM ejes | ✅ Alineado |
| Batería A: adversarial + legítimo + fuera de ámbito | Red-teaming por categorías de riesgo | ✅ Alineado |
| Fuentes citadas `[S#]` | Citation accuracy / faithfulness (RAG) | ✅ Alineado |
| Respuesta "evidencia insuficiente" | Negative rejection (deseable, poco común) | ✅ Fortaleza |
| Batería D: consistencia entre repeticiones | Reliability / reproducibility | ✅ Válido (menos común) |
| Batería C: memoria multi-turno | Multi-turn evaluation (emergente) | ✅ Alineado |
| Kappa de Cohen entre 2 médicos | Inter-rater reliability (κ ≥ 0.7) | ✅ Alineado |
| Validadores automáticos por regex (compañero) | Scoring automático (LlamaGuard, CLEAR-Bias) + revisión humana | ✅ Alineado |

## Limitaciones a declarar (para 7.3 y 6.4)

1. **2 evaluadores** vs. 4-7 recomendados por QUEST para uso clínico. Mitigación: se
   reporta kappa y se enmarca como validación piloto; el mismo par ya validó el modelo
   diagnóstico (526/509 casos), lo que da consistencia.
2. **Muestra de contenido = 30 preguntas** vs. ≥100 recomendado. Es piloto; ampliable.
3. **Sin cegado formal** de la fuente en la rúbrica (el evaluador juzga la salida del
   LLM directamente; no hay brazo pareado LLM-vs-médico como en Med-PaLM). Es válido,
   pero mencionarlo.
4. **Sin corpus etiquetado grande** para precision/recall de recuperación (ya está
   anotado como fuera de alcance en `validacion_llm/README.md`).

## Recomendaciones de redacción

- En 3.7, citar QUEST y el red-teaming médico para justificar el diseño de baterías.
- En 6.4, reportar por dimensión (exactitud, cita, seguridad) y el kappa, con la nota
  de que κ ≥ 0.7 es el umbral de referencia.
- En 7.3/7.5, declarar las limitaciones (2 evaluadores, n=30) y proponer ampliar a
  ≥4 evaluadores y ≥100 preguntas como trabajo futuro.
- Resaltar como aporte: no hay literatura previa de interpretación de hemogramas
  caninos por LLM, y el sistema exhibe rechazo por evidencia insuficiente.

## Fuentes

- Nature Medicine 2024 — https://www.nature.com/articles/s41591-024-03423-7
- QUEST / human evaluation framework — https://pmc.ncbi.nlm.nih.gov/articles/PMC11437138/
- CLEVER (JMIR AI 2025) — https://ai.jmir.org/2025/1/e72153
- Red-Teaming Medical AI (medRxiv 2026) — https://www.medrxiv.org/content/10.64898/2026.02.26.26347212v1
- RAG survey — https://arxiv.org/html/2504.14891v1
- RAG-X (medical) — https://arxiv.org/html/2603.03541v1
- Veterinary LLM MCQ (Frontiers 2025) — https://www.frontiersin.org/journals/veterinary-science/articles/10.3389/fvets.2025.1616566/full
- Veterinary ophthalmology LLM-vs-vet (Wiley 2026) — https://onlinelibrary.wiley.com/doi/10.1111/vop.70052
