# generar/ — paquete autocontenido para reescribir el Capítulo III

Todo lo necesario para que un LLM produzca el **Capítulo III completo**, con la sección nueva de
metodología de recaracterización, y te lo devuelva listo para pegar en Word. **No requiere acceso
al repositorio:** los datos están dentro.

---

## Cómo se usa

1. Abre una conversación nueva con un LLM capaz (ventana de contexto amplia).
2. Pega los archivos **en este orden**, cada uno precedido por su nombre en una línea:

```
00_PROMPT_MAESTRO.md          ← quién eres, qué produces, las tres reglas
01_TEXTO_ACTUAL.md            ← el Capítulo III íntegro tal como está hoy
02_HECHOS_VERIFICADOS.md      ← todas las cifras, con marca y separadas por altitud
03_ESTILO_Y_FORMATO.md        ← registro, terminología, números, tablas
04_GUION_SECCIONES_NUEVAS.md  ← arquitectura párrafo a párrafo de §3.11
05_CONTRATO_DE_SALIDA.md      ← qué devolver y checklist de verificación
```

3. Cierra con: **«Produce ahora el Capítulo III completo según el contrato de salida.»**

Son ~11 000 palabras en total: entra en una sola petición.

## Qué te devuelve

Un documento continuo en Markdown —el capítulo entero, no parches— más cuatro bloques: registro de
cambios, marcadores pendientes, inventario de tablas e inconsistencias detectadas.

**Para pasarlo a Word:** copia el Markdown, pégalo en un editor que lo renderice (el visor de
Markdown de VS Code, Typora, o cualquier conversor en línea), copia lo renderizado y pégalo en el
`.docx` **con formato**. Las tablas llegan como tablas reales. Después aplica el
`CHECKLIST_FORMATO.md` de la guía general.

---

## Qué contiene el paquete

| Archivo | Palabras aprox. | Contenido |
| :--- | ---: | :--- |
| `00_PROMPT_MAESTRO.md` | 1 100 | El encargo, por qué el manual exige esta sección, y las tres reglas |
| `01_TEXTO_ACTUAL.md` | 6 100 | El Capítulo III verbatim del `.docx (4)` |
| `02_HECHOS_VERIFICADOS.md` | 2 300 | Los parámetros de diseño de la campaña, separados de los resultados que no deben entrar |
| `03_ESTILO_Y_FORMATO.md` | 870 | Registro, traducción de anglicismos, convenciones numéricas |
| `04_GUION_SECCIONES_NUEVAS.md` | 1 700 | Arquitectura párrafo a párrafo de las once subsecciones de §3.11 |
| `05_CONTRATO_DE_SALIDA.md` | 1 000 | Formato de entrega, cuatro bloques y checklist de 33 puntos |

---

## Por qué este capítulo importa más de lo que parece

El manual (p. 10) pide cuatro cosas para la «Metodología del componente de tecnología emergente»:
justificar la selección del clasificador, justificar el banco de datos, justificar el método de
entrenamiento **y contrastar las métricas de calidad con lo que reporta la literatura para
problemas similares**.

Para el motor de aprendizaje automático, §3.3–§3.5 cumplen los cuatro puntos. Para el componente
conversacional, el documento cumple los tres primeros y **falla el cuarto**. Y resulta que el
proyecto sí hizo ese contraste —con diez hipótesis firmadas antes de medir, una de ellas tomada
directamente de la literatura— pero lo hizo en agosto y no se documentó.

Es el caso raro en que el trabajo existe y solo falta contarlo.

---

## Las tres reglas, en corto

1. **El Capítulo III describe cómo se midió; el VI dice qué salió.** Es la regla que se rompe.
2. **Ninguna cifra sin respaldo.** Distinguiendo cifras de diseño (van aquí) de cifras de
   resultado (van al VI).
3. **«No consta» es un resultado metodológico.** La auditoría encontró que once de quince
   parámetros del protocolo anterior no se registraron. Eso no se disimula: de ahí sale el
   veredicto doble de comparabilidad que condiciona todo el Capítulo VI.

---

## El riesgo real de este encargo

No es que el modelo escriba poco. Es que **escriba el Capítulo VI por error**.

El material de la campaña viene con sus resultados pegados a su metodología, y son buenos: un
−60,6 % de latencia, una hipótesis refutada por un factor de 44, un acuerdo de fallos peor que el
azar. Un redactor que los tenga delante los va a querer contar. El prompt lo prohíbe con ejemplos
de lo que sí y lo que no, `02` separa explícitamente las cifras de diseño de las de resultado, y
el checklist busca las siete cifras prohibidas una por una.

**La prueba que puedes hacer tú en treinta segundos:** busca `60,6` y `0,332` en lo que te
devuelva. Si aparecen, devuélveselo.

---

## Antes de dar por bueno lo que te devuelva

1. Busca `60,6`, `0,332`, `−0,145`, `34,90`. **Ninguna puede aparecer.**
2. Busca «REFUTADA», «CONFIRMADA», «NO EVALUADA». **No pueden aparecer**: los veredictos son del
   Capítulo VI.
3. Verifica que **sí** están los tamaños de muestra: 30, 64, 70, 100, 208, 431.
4. Verifica que están las **tres limitaciones de la ablación**, incluida la tercera —los datos
   crudos no se conservaron—, que es un incumplimiento del propio protocolo.
5. Verifica que el bloque de marcadores pendientes tiene las citas de Wilson, McNemar y Wilcoxon.
6. Lee §3.11 imaginando que el Capítulo VI no existe. Si se queda coja, el modelo metió
   resultados.

Si alguna falla, devuélveselo señalando el punto concreto en lugar de corregirlo a mano.

---

## Lo que este paquete NO cubre

**Las referencias bibliográficas.** §3.11 introduce cuatro procedimientos estadísticos que hoy no
están citados en el documento: intervalo de Wilson, McNemar, Wilcoxon y análisis de potencia. El
paquete instruye al modelo para que deje marcadores `[CITA PENDIENTE: …]`, pero conseguir las
referencias exactas y numerarlas en orden de aparición es trabajo aparte. Ver
[`../../10_referencias_anexos/generar/`](../../10_referencias_anexos/generar/).

> **Verifica antes de duplicar:** Wilcoxon puede estar ya citado a propósito de la validación
> clínica. Si lo está, se reutiliza la entrada, no se crea una nueva.

**El orden con el Capítulo VI.** Este capítulo describe cómo se midió lo que el VI reporta. Si
cambias una cifra en el VI, revisa que el diseño descrito aquí siga siendo el que la produjo.
**Haz el Capítulo VI primero.**
