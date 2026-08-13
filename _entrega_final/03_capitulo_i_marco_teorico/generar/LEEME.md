# generar/ — paquete autocontenido para reescribir el Capítulo I

Todo lo necesario para que un LLM produzca el **Capítulo I completo**, con la subsección de
rendimiento de inferencia y el glosario actualizado, y te lo devuelva listo para pegar en Word.
**No requiere acceso al repositorio:** los datos están dentro.

---

## Cómo se usa

1. Abre una conversación nueva con un LLM capaz (ventana de contexto amplia).
2. Pega los archivos **en este orden**, cada uno precedido por su nombre en una línea:

```
00_PROMPT_MAESTRO.md          ← quién eres, qué produces, las tres reglas
01_TEXTO_ACTUAL.md            ← el Capítulo I íntegro tal como está hoy
02_HECHOS_VERIFICADOS.md      ← las entradas de glosario redactadas y los datos admisibles
03_ESTILO_Y_FORMATO.md        ← registro, terminología, números, citas
04_GUION_SECCIONES_NUEVAS.md  ← arquitectura párrafo a párrafo de §1.1.3.7
05_CONTRATO_DE_SALIDA.md      ← qué devolver y checklist de verificación
```

3. Cierra con: **«Produce ahora el Capítulo I completo según el contrato de salida.»**

Son ~11 500 palabras en total: entra en una sola petición.

## Qué te devuelve

Un documento continuo en Markdown —el capítulo entero, no parches— más cuatro bloques: registro de
cambios, **referencias nuevas**, marcadores pendientes e inconsistencias detectadas.

**Para pasarlo a Word:** copia el Markdown, pégalo en un editor que lo renderice (el visor de
Markdown de VS Code, Typora, o cualquier conversor en línea), copia lo renderizado y pégalo en el
`.docx` **con formato**. Después aplica el `CHECKLIST_FORMATO.md` de la guía general.

---

## Qué contiene el paquete

| Archivo | Palabras aprox. | Contenido |
| :--- | ---: | :--- |
| `00_PROMPT_MAESTRO.md` | 1 100 | El encargo, por qué hace falta §1.1.3.7, y las tres reglas |
| `01_TEXTO_ACTUAL.md` | 6 530 | El Capítulo I verbatim del `.docx (4)`, glosario incluido |
| `02_HECHOS_VERIFICADOS.md` | 1 900 | Las catorce entradas de glosario redactadas, los datos admisibles y los prohibidos |
| `03_ESTILO_Y_FORMATO.md` | 990 | Registro, formato de las entradas de glosario, convenciones de cita |
| `04_GUION_SECCIONES_NUEVAS.md` | 1 400 | Arquitectura párrafo a párrafo de los cinco apartados de §1.1.3.7 |
| `05_CONTRATO_DE_SALIDA.md` | 1 100 | Formato de entrega, cuatro bloques y checklist de 30 puntos |

---

## Por qué este capítulo hay que tocarlo

Dos motivos, y el segundo pesa más que el primero.

**El glosario describe un sistema que ya no existe.** Las entradas «LLM» y «Ollama» dicen que el
*runtime* conversacional usa un modelo de cuatro mil millones de parámetros. El sistema sirve uno
de veintisiete mil millones sobre una unidad de procesamiento gráfico NVIDIA A100.

**Y falta el sustrato teórico del rendimiento de inferencia.** El Capítulo VI refuta
cuantitativamente un valor publicado en la literatura: al sobrecosto de la decodificación
restringida por gramática se le atribuían al menos diez milisegundos por token, y la medición
arrojó unas cuarenta y cuatro veces menos.

> **Un capítulo de resultados no puede refutar literatura que el marco teórico nunca presentó.**

Sin §1.1.3.7, el mejor resultado del proyecto queda sin sostén. Con ella, es exactamente lo que el
manual (p. 6) llama «señalar cómo nuestro proyecto amplía la literatura actual».

---

## Las tres reglas, en corto

1. **El marco teórico presenta la literatura; el Capítulo VI la contrasta.** §1.1.3.7 debe poder
   leerse como un texto de referencia escrito por alguien que aún no ha medido nada.
2. **No inventes ni una sola referencia.** Es crítico aquí: la cita del valor que §6.8 refuta
   tiene que ser exacta y verificable.
3. **Lo que está bien, se reproduce íntegro.** El capítulo funciona; solo se añade.

---

## El riesgo real de este encargo

**Que el modelo invente la referencia crítica.** Es el riesgo más serio de los nueve paquetes.

§1.1.3.7 necesita citar la fuente que publica el sobrecosto de la decodificación por gramática, y
esa fuente **no está en el paquete**. Un modelo de lenguaje al que se le pide una cita técnica que
no tiene produce, con alta probabilidad, una que suena verosímil y no existe. Y esta es
precisamente la cita que un miembro del comité verificará, porque el Capítulo VI la refuta.

El prompt lo prohíbe explícitamente, el contrato de salida exige un bloque entero de referencias
con su estado, y el checklist lo comprueba. **Aun así, verifícalo tú.**

---

## Antes de dar por bueno lo que te devuelva

1. **Busca cada referencia nueva que haya escrito completa** —no las que dejó como pendientes— y
   compruébala. Si citó autor, título y año de algo, búscalo. Si no aparece, no existe.
2. Busca `0,332` y `44`. **No pueden aparecer**: son la medición y su comparación, del Capítulo VI.
3. Busca «como se verá» y «más adelante». El marco teórico no adelanta resultados.
4. Verifica que el bloque de marcadores pendientes **no esté vacío**. El paquete no incluye
   ninguna referencia nueva, así que un bloque vacío significa que se las inventó todas.
5. Cuenta las entradas del glosario en tu texto original y en el resultado. **No puede haber
   menos.** Es el capítulo donde más fácil se pierde contenido al reproducir.
6. Verifica que las entradas nuevas están **en orden alfabético e intercaladas**, no en bloque al
   final.

Si alguna falla, devuélveselo señalando el punto concreto en lugar de corregirlo a mano.

---

## Lo que este paquete NO cubre

**Conseguir las referencias.** El paquete describe con precisión qué hay que citar —seis entradas,
una de ellas crítica— pero encontrarlas es trabajo de biblioteca. Ver
[`../../10_referencias_anexos/generar/`](../../10_referencias_anexos/generar/), que coordina la
bibliografía completa.

**La renumeración de citas.** Insertar §1.1.3.7 desplaza toda la numeración posterior del
documento: es **el cambio de mayor riesgo mecánico de toda la revisión**. Se hace en Word con la
función de referencias cruzadas, nunca a mano, y **al final**, cuando todas las secciones nuevas
estén insertadas.

---

## Cuándo hacer este capítulo

**Después del VI**, porque necesitas saber exactamente qué valor de la literatura hay que
presentar para que §6.8 pueda contrastarlo. Y **antes de cerrar la bibliografía**, porque las seis
referencias nuevas entran por aquí.
