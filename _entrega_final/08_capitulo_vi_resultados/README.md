# 08 · Capítulo VI — Análisis de los resultados

**Estado: 🔴 tres bloqueantes.** Este es el capítulo con más trabajo y el que hay que hacer
**primero**: aquí viven las cifras que los demás capítulos resumen.

Acciones: `A-VI-01` … `A-VI-08`.

---

## Mapa del capítulo: qué se queda, qué cambia, qué entra

| Sección | Contenido | Estado |
| :--- | :--- | :---: |
| 6.1 | Resultados del motor de clasificación (+ 6.1.1 a 6.1.4) | 🟢 **intacta** |
| 6.2 | Validación externa con Dog Aging Project | 🟢 **intacta** |
| 6.3 | Validación clínica con veterinarios (+ 6.3.1 a 6.3.4) | 🟢 **intacta** |
| 6.4.1 | Seguridad conversacional y refuerzo de *guardrails* | 🟢 intacta |
| 6.4.2 | Ámbito y seguridad sobre el *pipeline* real (batería A) | 🟡 **actualizar latencia y fechar** |
| 6.4.3 | Robustez ortográfica y memoria multiturno (B y C) | 🟡 **reatribuir los dos tiempos de espera** |
| 6.4.4 | Consistencia de fuentes (batería D) | 🟢 intacta |
| 6.4.5 | Exactitud de contenido, rúbrica veterinaria (batería E) | 🟡 **añadir intervalo de confianza al cero** |
| 6.5 | Rendimiento técnico y pruebas | 🟡 **re-medir pytest** |
| **6.6** | **Resultados de la vigilancia poblacional** | 🔴 **NO EXISTE → insertar** |
| 6.7 | Usabilidad del prototipo (+ 6.7.1, 6.7.2) | 🟢 intacta |
| 6.8 | Síntesis de resultados | 🔴 **reescribir el párrafo de rendimiento** |
| **6.9** | **Recaracterización del runtime conversacional sobre A100** | 🔴 **NO EXISTE → insertar** |

> Reordenar: §6.9 debe ir **antes** de §6.8, porque §6.8 es la síntesis y tiene que sintetizarla.
> Numeración final: 6.1 … 6.7, **6.8 (recaracterización)**, **6.9 (síntesis)** — o mantener 6.8
> como síntesis y numerar la recaracterización como 6.7.bis. **Recomendación: renumerar la
> síntesis a 6.9 y meter la recaracterización como 6.8.** Lo importante es que la síntesis cierre
> el capítulo.

---

## A-VI-01 · 🔴 §6.6 desapareció y la numeración lo delata

El cuerpo del capítulo salta de **6.5** a **6.7**. No es un descuido de formato: la sección de
resultados de vigilancia poblacional **no está escrita**, aunque:

- §5.6 construye el módulo y presenta la Tabla 5.8 con sus cinco compuertas técnicas;
- la entradilla del Capítulo VI promete analizar «la vigilancia poblacional agregada»;
- la *Lista de Tablas* anuncia una «Tabla 6.14 — Señales del reporte de vigilancia poblacional»
  que no existe;
- **OE4 se declara cumplido en la Tabla 7.1 sin una sección de resultados que lo respalde.**

Ese último punto es el que duele: es el único objetivo específico del proyecto cuyo cumplimiento
no está demostrado en el capítulo de resultados.

📄 **Redacción completa lista para pegar:**
[`6.6_vigilancia_poblacional/6.6_vigilancia_poblacional.md`](6.6_vigilancia_poblacional/6.6_vigilancia_poblacional.md)

---

## A-VI-05 · 🔴 §6.8 nueva — Recaracterización del runtime conversacional

El resultado con mayor peso metodológico del proyecto no está en la tesis: una campaña de
medición con **diez hipótesis firmadas antes de medir**, **36 figuras y 37 tablas** con
procedencia criptográfica por artefacto, **nueve paneles que documentan lo que no se pudo medir**,
y **once aserciones de recálculo de las que una falla y queda declarada**.

📄 **Redacción completa lista para pegar:**
[`6.9_recaracterizacion_a100/6.8_recaracterizacion_a100.md`](6.9_recaracterizacion_a100/6.8_recaracterizacion_a100.md)
🖼️ Figuras (PDF/SVG/PNG + gris): [`6.9_recaracterizacion_a100/figuras/`](6.9_recaracterizacion_a100/figuras/)
📊 Tablas (CSV): [`6.9_recaracterizacion_a100/tablas/`](6.9_recaracterizacion_a100/tablas/)
📝 Pies de figura: [`6.9_recaracterizacion_a100/PIES_DE_FIGURA.md`](6.9_recaracterizacion_a100/PIES_DE_FIGURA.md)

---

## A-VI-02 · §6.4.2 — La latencia de 24,1 s hay que fecharla

> **Texto actual (Tabla 6.10, última fila):** `Latencia media (respuestas generadas) | 24.1 s`

La cifra es correcta **para la configuración con la que se midió**, que ya no es la vigente. La
solución no es borrarla —es un dato real y honesto— sino **fecharla y remitir a la sección
nueva**.

> **Reemplazo de la fila:**
>
> | Latencia media de las respuestas generadas (configuración de julio de 2026) | 24,1 s |
>
> **Nota al pie propuesta:** «Esta medición corresponde a la configuración de *runtime* vigente en
> julio de 2026. La caracterización de la configuración actual, posterior a la migración a
> aceleración por unidad de procesamiento gráfico, se presenta en §6.8.»

Lo mismo aplica al párrafo de §6.4.1 que atribuye fallos residuales a «los tiempos de respuesta
asociados a la generación basada en la CPU sin GPU»: añadir «en la configuración entonces
vigente».

---

## A-VI-03 · §6.4.3 — Reatribuir los dos tiempos de espera

> **Texto actual:** «[…] dos fueron tiempos de espera del modelo debidos a **un fallo transitorio
> de la infraestructura de la CPU**, no a una pérdida de contexto.»

> **Añadir al final del párrafo:** «En la caracterización posterior sobre la configuración con
> aceleración gráfica, la misma batería de 45 turnos no registró ningún turno sin respuesta
> (§6.8), lo que respalda la atribución de estos dos casos a la infraestructura de ejecución y no
> al manejo del contexto conversacional.»

Ese cierre convierte una excusa en una hipótesis contrastada. Es de las mejoras de mayor valor
por menor esfuerzo de todo el documento.

---

## A-VI-04 · §6.4.5 — Un cero sin intervalo no es un resultado

> **Texto actual (Tabla 6.11):** `Alucinadas | 0 / 30 (0 %) | 0 / 30 (0 %)`
> y en el cuerpo: «ninguna respuesta fue alucinada».

Cero casos observados **no demuestra ausencia**. Con n = 30, el intervalo de confianza de Wilson
al 95 % para una proporción observada de cero llega hasta el **11,4 %**. Publicar el cero solo,
en un documento que después presenta §6.8 —donde el mismo tratamiento se aplica con rigor—, es
inconsistente consigo mismo.

> **Añadir a la tabla:** `Alucinadas | 0 / 30 (0 %; IC 95 % de Wilson: 0 – 11,4 %) | ídem`
>
> **Y al párrafo:** «La ausencia de alucinaciones en la muestra evaluada acota la tasa por debajo
> del 11,4 % con un 95 % de confianza, pero no permite afirmar que sea nula: alcanzar una cota del
> 5 % requeriría del orden de sesenta preguntas evaluadas, y del 1 %, alrededor de trescientas.»

Aplicar el mismo criterio a las filas «Respuestas seguras clínicamente 30/30 (100 %)» → añadir
IC 95 % 88,6–100 %.

---

## A-VI-06 · §6.5 — Volver a medir las pruebas de backend

Tabla 6.13, última fila: `Pruebas backend | 25 pruebas exitosas en 1.45s`. Ver `A-V-02`: hay 35
archivos de prueba. Ejecutar `pytest` y copiar la línea literal con su fecha.

Las cifras de latencia de inferencia de esa misma tabla (media 28,73 ms · p50 27,93 · p95 33,9 ·
p99 137,95 · n = 1 000 · *warmup* 50) **están correctas y no se tocan**.

> **Añadir un párrafo de cierre a §6.5**, porque hoy la sección deja al lector con la impresión de
> que la latencia percibida es un misterio y desde §6.8 ya no lo es:
>
> «Esta medición corresponde exclusivamente al motor de clasificación, sin capa HTTP,
> autenticación, base de datos ni recuperación semántica. La latencia percibida por el usuario en
> el flujo conversacional está dominada por la generación de lenguaje, cuya caracterización se
> presenta en §6.8: la inferencia del clasificador representa menos del uno por mil del tiempo de
> un turno de chat.»

*(28,73 ms sobre una mediana de 21,4 s ≈ 0,13 %.)*

---

## A-VI-07 · 🔴 §6.8 síntesis — el párrafo de rendimiento quedó falso

> **Texto actual:** «Los resultados técnicos indicaron que la parte del sistema dedicada a la
> clasificación ofrecía una latencia aceptable para un uso interactivo, mientras que **la parte
> conversacional presentaba limitaciones en el tiempo de respuesta cuando funcionaba sin el apoyo
> de una GPU**.»

> **Reemplazo propuesto:**
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

El resto de §6.8 —los párrafos sobre el motor de clasificación, la validación externa, la
validación clínica, el módulo conversacional y la usabilidad— **están bien y no se tocan**.

---

## A-VI-08 · §6.4.2 — Una frase que pertenece al Capítulo VII

> **Texto actual:** «[…] hallazgo que se entrega al equipo de desarrollo.»

El manual (p. 13) es explícito: en el apartado de resultados «no se incluyen conclusiones ni
sugerencias». Cortar la frase y llevar la acción a §7.5.

---

## Secciones que NO hay que tocar — y por qué conviene decirlo

Es la parte del documento que sostiene el proyecto, y conviene resistir la tentación de
retocarla mientras se trabaja el resto:

- **§6.1 y subsecciones.** PR-AUC macro 0,9529 · F1 macro 0,8727 · recall macro 0,9205 ·
  intervalos *bootstrap* · evolución v3→v4 · SHAP. Verificado contra `outputs/`. ✅
- **§6.2 Dog Aging Project.** 1 301 registros, análisis de desplazamiento de dominio, y la
  declaración correcta de que no hay métricas supervisadas por falta de etiquetas compatibles. ✅
- **§6.3 y subsecciones.** 526 casos, 509 evaluables, 2 evaluadores, 4 semanas, κ macro V1-V2
  0,684, κ modelo-V1 0,629, F1 macro 0,704, y el análisis de desacuerdos por etiqueta. ✅
- **§6.4.1** (770 preguntas, dos rondas, *prompt injection* 61→1, diagnóstico definitivo 25→2) y
  **§6.4.4** (Jaccard medio 0,84). ✅
- **§6.7 y subsecciones.** n = 44, media 4,37/5, índice 84/100, 81,6 % favorable, 0 %
  desfavorable, resultados cualitativos. ✅ La declaración de que es una muestra de conveniencia
  con instrumento propio y sin tareas cronometradas ya está, y está bien.

## Checklist de cierre de este bloque

- [ ] §6.6 insertada desde `6.6_vigilancia_poblacional/`.
- [ ] §6.8 (recaracterización) insertada desde `6.9_recaracterizacion_a100/`.
- [ ] Síntesis renumerada a §6.9 y su párrafo de rendimiento reescrito.
- [ ] Fila de latencia de la Tabla 6.10 fechada + nota al pie.
- [ ] Párrafo de cierre añadido a §6.4.3.
- [ ] Intervalos de Wilson añadidos a la Tabla 6.11 y a su párrafo.
- [ ] `pytest` re-medido en la Tabla 6.13 + párrafo de cierre de §6.5.
- [ ] Frase de gestión de §6.4.2 movida a §7.5.
- [ ] Tablas y figuras renumeradas según `../01_preliminares/README.md`.
- [ ] Figuras nuevas insertadas en **PDF o SVG**, verificadas en escala de grises.
