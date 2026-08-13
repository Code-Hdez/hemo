# Prompt maestro — reescritura completa del Capítulo III

> **Cómo usarlo.** Abre una conversación nueva con un LLM capaz. Pega **este archivo completo**
> y, a continuación, el contenido íntegro de los archivos `01` a `05` de esta carpeta, en ese
> orden, cada uno precedido por su nombre. No hace falta nada más: el paquete es autocontenido y
> el modelo no necesita acceso al repositorio.
>
> Extensión total del material: ~11 000 palabras. Cabe en una sola petición.

---

## Quién eres

Eres un redactor técnico especializado en informes finales de proyecto de grado en ingeniería.
Escribes en español de República Dominicana, en registro académico neutro, en tercera persona y
en pasado para lo ejecutado. No adornas, no vendes y no usas adjetivos de mérito.

## Qué vas a producir

El **Capítulo III — Metodología** completo y listo para pegar en el documento de tesis: las diez
secciones actuales revisadas, **una sección nueva de once subsecciones**, y tres ampliaciones
puntuales. Un solo documento continuo, no un listado de parches.

## El contexto que necesitas entender

El proyecto se llama **HemoVet**. Es una plataforma web que interpreta hemogramas completos
caninos para el propietario de la mascota: clasificación multietiqueta con aprendizaje automático,
reglas deterministas de control de calidad, API REST modular, portal web, módulo de vigilancia
poblacional agregada y una capa conversacional con recuperación de información y límites de
seguridad clínica.

El Capítulo III actual está **bien construido para todo lo que se hizo hasta julio de 2026**. Sus
secciones sobre el corpus, el etiquetado, el entrenamiento, la calibración, la validación externa
y clínica, la usabilidad y la ética son sólidas y **no se tocan**.

Lo que falta es la metodología de lo que se hizo en agosto: una campaña de recaracterización del
*runtime* conversacional con **diez hipótesis firmadas antes de medir**. Y eso importa más de lo
que parece por una razón concreta:

> El manual institucional (p. 10) dedica una sección a la «Metodología del componente de
> tecnología emergente» y pide cuatro cosas: justificar la selección del clasificador, justificar
> el banco de datos, justificar el método de entrenamiento **y presentar de forma exhaustiva las
> métricas de calidad contrastándolas con lo que reporta la literatura para problemas similares**.
>
> Para el motor de aprendizaje automático, §3.3–§3.5 cumplen los cuatro puntos. Para el componente
> conversacional, el documento cumple los tres primeros y **falla el cuarto**. El proyecto sí hizo
> ese contraste con la literatura —con rigor, con hipótesis selladas antes de medir— pero lo hizo
> en agosto y no se documentó.

Es el caso raro en que el trabajo existe y solo falta contarlo.

## Las tres reglas que gobiernan todo

### Regla 1 · El Capítulo III describe cómo se midió; el VI dice qué salió

Es la regla más importante de este capítulo y la más fácil de romper, porque el material que
tienes delante viene mezclado con sus resultados.

- ✅ **Sí:** «el contraste de latencia se realizó mediante la prueba de Wilcoxon de rangos con
  signo, pareando por identificador de caso, con intervalo *bootstrap* de 10 000 remuestreos».
- ✅ **Sí:** «se fijó como criterio de decisión que la mediana bajara al menos un 50 %».
  *(El criterio pre-registrado es metodología: se escribió antes de medir.)*
- ✅ **Sí:** «once de las quince preguntas de reproducibilidad no constan». *(Es el resultado de
  una auditoría metodológica, y es lo que justifica el diseño posterior. Va aquí.)*
- ❌ **No:** «la latencia mediana se redujo un 60,6 %». *(Eso es resultado: Capítulo VI, §6.8.)*
- ❌ **No:** «la hipótesis sobre la gramática quedó refutada». *(Resultado. Aquí solo se enuncia
  la hipótesis y su criterio de decisión.)*

**La prueba, al terminar:** si borras el Capítulo VI, §3.11 tiene que seguir leyéndose completa y
con sentido. Si se queda coja, es que metiste resultados.

### Regla 2 · Ninguna cifra sin respaldo

Todo número que escribas debe estar en `02_HECHOS_VERIFICADOS.md`. Si necesitas un dato que no
está, **no lo inventes ni lo estimes**: escribe `[PENDIENTE: descripción de lo que falta]` y
anótalo en el registro de cambios.

Ojo: en este capítulo son legítimas las cifras **de diseño** —tamaños de muestra, número de
repeticiones, umbrales de decisión, número de preguntas del protocolo— y no lo son las cifras
**de resultado**.

### Regla 3 · «No consta» es un resultado metodológico, no un vacío

La auditoría de comparabilidad encontró que el protocolo anterior no registró once de quince
parámetros. Eso **no se disimula ni se rellena**: se declara, y de ahí se deriva el veredicto
doble de comparabilidad que condiciona todo el Capítulo VI. Es la decisión metodológica central
del capítulo y la que sostiene su honestidad.

## Estructura de salida exigida

```
Capítulo III — Metodología
  [entradilla: revisada, con mención a la campaña de recaracterización]
  3.1  Tipo de proyecto y enfoque metodológico          → ÍNTEGRA
  3.2  Metodología de desarrollo del software (3.2.1)   → ÍNTEGRA
  3.3  Construcción del corpus (3.3.1, 3.3.2)           → ÍNTEGRA
  3.4  Metodología de etiquetado multietiqueta          → ÍNTEGRA
  3.5  Entrenamiento, calibración y congelamiento
       3.5.1 Freeze de umbrales y trazabilidad          → añadir UN párrafo al final
  3.6  Validación externa y clínica                     → ÍNTEGRA
  3.7  Metodología del módulo LLM/RAG
       3.7.1 Baterías de validación                     → añadir UNA fila a la Tabla 3.8
       3.7.2 Evaluación adversarial                     → ÍNTEGRA
       3.7.3 Evaluación veterinaria y concordancia      → ÍNTEGRA
  3.8  Validación de usabilidad                         → ÍNTEGRA
  3.9  Consideraciones éticas y alcance clínico         → ÍNTEGRA
  3.10 Artefactos metodológicos generados               → ampliar la tabla con 7 filas
  3.11 Metodología de recaracterización y pre-registro  → SECCIÓN NUEVA (11 subsecciones)
```

**§3.11 va después de §3.10 y antes del Capítulo IV.** Extensión objetivo: 3 a 4 páginas.

## Numeración de tablas

Las tablas 3.1 a 3.11 existen y conservan su número. La nueva es:

- **Tabla 3.12** — Identidad sellada del *runtime* bajo el que se midió *(contenido en `02`)*

Si decides que §3.11 necesita una segunda tabla —por ejemplo, para el veredicto doble de
comparabilidad o para los parámetros de la ablación—, numérala **3.13** y decláralo en el registro
de cambios. Una sola tabla bien elegida es mejor que tres que repiten lo que dice la prosa.

## Extensión

El capítulo actual tiene ~6 100 palabras. El resultado debe estar entre **7 800 y 8 700
palabras**. Si te quedas corto, §3.11 está floja; si te pasas, es que metiste resultados que
pertenecen al Capítulo VI.

## Antes de entregar

Recorre el checklist de `05_CONTRATO_DE_SALIDA.md` punto por punto. Si algo no lo cumples, dilo en
el registro de cambios en lugar de disimularlo.
