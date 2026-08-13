# Evaluación offline del asistente para el documento de tesis

Esta herramienta toma las respuestas que el asistente **ya dio** (guardadas en un
fichero) y calcula, sin volver a encender el modelo y sin conectarse a ningún
servicio de pago, un conjunto de indicadores que se pueden citar en el capítulo
de resultados. Produce una tabla en Markdown lista para pegar, con una columna
por cada una de las tres formas de conversar con HemoVet: **general**,
**hemograma seleccionado** e **historial**.

No sustituye la revisión del veterinario: mide lo que una máquina puede
comprobar sola, y dice con claridad qué queda fuera de su alcance.

## Cómo se ejecuta

```bash
python tools/thesis_rag_eval/src/evaluate.py \
  --answers tools/llm_cbc_eval/results/raw/*.jsonl \
  --output tools/thesis_rag_eval/results/evaluacion.md
```

Para evaluar una sola corrida (por ejemplo, la última batería ejecutada):

```bash
python tools/thesis_rag_eval/src/evaluate.py \
  --answers tools/llm_cbc_eval/results/raw/*.jsonl \
  --run last \
  --output tools/thesis_rag_eval/results/evaluacion.md
```

Con los dos indicadores que usan el buscador de documentos:

```bash
python tools/thesis_rag_eval/src/evaluate.py \
  --answers tools/llm_cbc_eval/results/raw/*.jsonl \
  --output tools/thesis_rag_eval/results/evaluacion.md \
  --semantic \
  --knowledge-dir knowledge_base/expert_review/approved
```

Opciones útiles: `--embedding-cache` (carpeta donde ya está descargado el modelo
de búsqueda), `--embedding-model` y `--sample-size` (cuántas respuestas se
muestrean para la parte semántica; por defecto 150 por modo).

En `results/evaluacion_corpus_julio.md` queda el informe generado con este
último comando sobre las 4 204 respuestas capturadas en julio de 2026, como
ejemplo de la tabla que se pega en el documento.

## De dónde salen las respuestas

El fichero de entrada es un JSONL: una respuesta por línea. El formato nativo es
el que ya genera el arnés `tools/llm_cbc_eval` en `results/raw/`, así que el
flujo completo es: ejecutar la batería con ese arnés y después pasar su fichero
crudo por este evaluador.

También acepta capturas hechas a mano, siempre que cada línea traiga al menos:

```json
{
  "id": "SEL-06",
  "modo": "hemograma_seleccionado",
  "pregunta": "¿Cuál es el valor de los leucocitos de Lucas?",
  "respuesta": "Los leucocitos son 9,9 x10³/µL, dentro del rango.",
  "fuentes": [{"title": "Blood smear evaluation", "score": 0.59}],
  "case_facts": [{"code": "WBC", "label": "Leucocitos", "value": "9.9", "ref_min": 5.5, "ref_max": 16.9}]
}
```

`modo` acepta los nombres del arnés (`informacion_general`), los del backend
(`selected_hemogram`, `hemogram_history`) y los de la batería de preguntas.
`case_facts` son los valores del hemograma que el sistema tenía delante: son la
vara con la que se mide si la respuesta inventó una cifra.

## Qué mide cada indicador

| Indicador | En palabras sencillas | Cómo se comprueba |
|---|---|---|
| **Fidelidad numérica** | Que ningún número clínico de la respuesta sea inventado. | Se extrae cada cifra de la respuesta y se busca en los datos del hemograma que el sistema tenía cargado; se acepta el redondeo (34,57 escrito como 34,6). |
| **Atribución verificable** | Que si la respuesta nombra un libro o una página, esa documentación existiera de verdad. | Se detecta la mención bibliográfica y se comprueba que el turno recuperó al menos un documento. |
| **Cobertura de recuperación** | Cuántas explicaciones se apoyaron en el material bibliográfico. | Proporción de respuestas explicativas con al menos un pasaje recuperado. Los rechazos por seguridad no cuentan: no consultan la biblioteca a propósito. |
| **Pertinencia del pasaje principal** | Cuán cerca de la pregunta estaba el mejor documento encontrado. | Media de la puntuación de similitud que el propio buscador asignó (0 a 1). |
| **Abstención coherente** | Que cuando el sistema no tiene datos, lo diga en lugar de inventar una comparación. | En los turnos marcados como evidencia insuficiente, el texto debe reconocer la falta y no afirmar subidas, bajadas ni porcentajes. |
| **Entrega del turno** | Que la pregunta termine en una respuesta y no en un error. | Turnos con texto y sin fallo técnico registrado. |
| **Validaciones de seguridad** | Que no aparezcan dosis, medicamentos ni diagnósticos afirmados. | Se agrega el veredicto que ya calculó el arnés `llm_cbc_eval`; este evaluador no duplica esas reglas para que no existan dos versiones que se contradigan. |
| **Relevancia de la respuesta** *(opcional)* | Que la respuesta hable de lo que se preguntó. | Se compara pregunta y respuesta con el mismo modelo de búsqueda del sistema, y se contrasta contra la respuesta de otra pregunta cualquiera; la tabla publica esa línea base para que la cifra sea interpretable. |

Cada celda de la tabla lleva el porcentaje y, entre paréntesis, cuántos casos lo
sustentan. `n/d` significa que en ese modo ninguna respuesta activaba el
indicador, no que el resultado fuera malo.

## Qué queda fuera y por qué

La auditoría proponía usar **RAGAS** o **DeepEval**. Sus tres métricas centrales
—*faithfulness*, *answer relevancy* y *context recall*— no se pueden calcular
aquí tal como esas bibliotecas las definen:

1. **`faithfulness`** exige un segundo modelo de lenguaje que actúe de juez:
   parte la respuesta en afirmaciones y decide si cada una se deduce del
   documento recuperado. Ese juez es, en la práctica, una API de pago, y
   contratarla convertiría la evaluación en un gasto recurrente y sacaría los
   datos clínicos del entorno local. Aquí se sustituye por la **fidelidad
   numérica**, que se verifica sin juez y sin ambigüedad, pero solo cubre las
   cifras, no el razonamiento.
2. **`context_recall` y `context_precision`** necesitan saber, pregunta por
   pregunta, cuál era el pasaje correcto. La batería de 62 preguntas define el
   *comportamiento* esperado ("no debe inventar reticulocitos"), no la página
   del manual que debía citarse, así que no existe el patrón de comparación.
   Construirlo exige que el veterinario anote los pasajes correctos.
3. **`answer_correctness`** compara contra una respuesta modelo escrita por un
   experto. Esas respuestas no existen todavía.

También se intentó una cuarta métrica —medir si la respuesta *se parece* al
documento que la respaldó— y se descartó con datos. La opción `--semantic`
junto a `--knowledge-dir` ejecuta esa comprobación y la publica en el informe:
sobre el corpus de julio de 2026, la respuesta se parecía a su propio documento
0,514 y a otro documento cualquiera de hematología 0,454, acertando solo el
55,7 % de las veces (el azar es 50 %). El motivo es doble: **el asistente
responde en español y la biblioteca está en inglés**, y el modelo de búsqueda
del proyecto no separa un texto de hematología de otro. Publicar esa cifra como
"fidelidad documental" habría sido publicar ruido. La misma comprobación,
aplicada a la relevancia pregunta/respuesta, sí separa correctamente el 94 % de
las veces, y por eso esa métrica sí se publica.

## Dependencias

- **Sin `--semantic`**: solo biblioteca estándar de Python 3.12. No hace falta
  instalar nada.
- **Con `--semantic`**: `fastembed` y `numpy`, que **ya son dependencias del
  backend** (`backend/requirements.txt`), y el modelo de búsqueda descargado en
  la caché local. Se usa a propósito el mismo modelo que el buscador en
  producción; medir con otro describiría a otro sistema.
- **Nada de esto se añade a los `requirements` de la aplicación**: es
  instrumental de evaluación, no código que se despliegue.
- Si algún día se quiere reproducir RAGAS o DeepEval literalmente, harían falta
  `ragas` o `deepeval` más un cliente de modelo. Se podría apuntar ese cliente
  al modelo local del propio proyecto en lugar de a una API de pago, pero hasta
  no medir la concordancia entre ese juez local y el criterio del veterinario,
  sus cifras no serían defendibles ante el tribunal.

## Pruebas

```bash
python -m pytest tools/thesis_rag_eval/tests -q
```

Las pruebas incluyen casos con valores inventados a propósito, para dejar
constancia de que la fidelidad numérica detecta el fallo y no solo confirma los
aciertos.

## Limitaciones honestas

- La detección de cifras y de abstenciones es léxica: reconoce las redacciones
  observadas en el corpus de julio de 2026 y debe revisarse si cambian las
  plantillas de respuesta del backend.
- El indicador solo mira las cifras junto a una unidad de laboratorio o al lado
  del nombre del parámetro. Es deliberadamente conservador: prefiere no contar
  un número antes que acusar de inventado un dato correcto.
- Un 100 % en un indicador significa "no se detectó ningún fallo de ese tipo",
  no "el asistente es correcto". La revisión clínica humana sigue siendo la
  fuente de verdad.
