# generar/ — paquete autocontenido para reescribir el Capítulo VII

Todo lo necesario para que un LLM produzca el **Capítulo VII completo**, con las cinco
limitaciones y los tres hallazgos que faltan, y te lo devuelva listo para pegar en Word. **No
requiere acceso al repositorio:** los datos están dentro.

---

## Cómo se usa

1. Abre una conversación nueva con un LLM capaz (ventana de contexto amplia).
2. Pega los archivos **en este orden**, cada uno precedido por su nombre en una línea:

```
00_PROMPT_MAESTRO.md          ← quién eres, qué produces, las tres reglas
01_TEXTO_ACTUAL.md            ← el Capítulo VII íntegro tal como está hoy
02_HECHOS_VERIFICADOS.md      ← las cifras con su sección, y los textos nuevos redactados
03_ESTILO_Y_FORMATO.md        ← registro, terminología, números, tablas
04_GUION_SECCIONES_NUEVAS.md  ← dónde encaja cada pieza y qué tono conservar
05_CONTRATO_DE_SALIDA.md      ← qué devolver y checklist de verificación
```

3. Cierra con: **«Produce ahora el Capítulo VII completo según el contrato de salida.»**

Son ~10 000 palabras en total: entra en una sola petición.

## Qué te devuelve

Un documento continuo en Markdown —el capítulo entero, no parches— más cuatro bloques: registro de
cambios, marcadores pendientes, remisiones utilizadas e inconsistencias detectadas.

**Para pasarlo a Word:** copia el Markdown, pégalo en un editor que lo renderice (el visor de
Markdown de VS Code, Typora, o cualquier conversor en línea), copia lo renderizado y pégalo en el
`.docx` **con formato**. Después aplica el `CHECKLIST_FORMATO.md` de la guía general.

---

## Qué contiene el paquete

| Archivo | Palabras aprox. | Contenido |
| :--- | ---: | :--- |
| `00_PROMPT_MAESTRO.md` | 1 000 | El encargo, el diagnóstico del capítulo y las tres reglas |
| `01_TEXTO_ACTUAL.md` | 3 070 | El Capítulo VII verbatim del `.docx (4)` |
| `02_HECHOS_VERIFICADOS.md` | 2 700 | Las cifras con su sección de origen, y los textos nuevos ya redactados |
| `03_ESTILO_Y_FORMATO.md` | 890 | Registro, traducción de anglicismos, convenciones numéricas |
| `04_GUION_SECCIONES_NUEVAS.md` | 1 500 | Dónde encaja cada pieza, en qué orden y qué tono conservar |
| `05_CONTRATO_DE_SALIDA.md` | 1 100 | Formato de entrega, cuatro bloques y checklist de 36 puntos |

---

## El diagnóstico, en una frase

**El capítulo está bien escrito y cierra un proyecto que siguió avanzando un mes más.** Tiene los
siete sub-ítems que el manual exige, en el orden correcto. Lo que le pasa es que §7.6 afirma que
el modelo de lenguaje corre sin aceleración gráfica, §7.3 no recoge cinco limitaciones que la
campaña de agosto declaró, §7.4 se pierde tres hallazgos que están entre los mejores del proyecto,
y §7.5 recomienda dos cosas que ya se hicieron.

El encargo es **completarlo, no rehacerlo**.

---

## Las tres reglas, en corto

1. **El Capítulo VII resume el VI; no lo amplía.** Aquí sí se concluye y se recomienda —es su
   función— pero solo sobre lo que el Capítulo VI ya demostró.
2. **Ninguna cifra sin respaldo, y toda cifra con su sección.** `(§6.8)`, `(§6.5)`, `(§6.6)`. El
   Capítulo VII no es fuente de ninguna cifra.
3. **Lo que se añade se añade; lo que está, se respeta.** Las limitaciones nuevas son la octava a
   la duodécima; los hallazgos nuevos el sexto, séptimo y octavo. No se renumera nada.

---

## Lo que hace distinto a este paquete

**Casi todo el texto nuevo ya está redactado.** El archivo `02` no trae solo cifras: trae los
párrafos escritos. El trabajo del modelo es de integración —colocarlos, encadenarlos con lo que
hay y conservar el registro— más que de creación. Por eso `04` no es un guion de redacción sino un
mapa de dónde encaja cada pieza.

**Hay una dependencia con otros capítulos.** Este es el capítulo que más remite de todo el
documento: cita §6.5, §6.6, §6.8, §5.7, §5.10 y §1.1.3.7. Varias de esas secciones **todavía no
existen**: las están creando los paquetes de los otros capítulos. Por eso el contrato de salida
pide un bloque C con todas las remisiones utilizadas, para que puedas verificarlas cuando el resto
esté cerrado.

**Un dato queda sin número a propósito.** §7.6 dice hoy «25 pruebas superadas en el backend». Hoy
hay 35 archivos de test y la suite no se ha vuelto a correr. El reemplazo **no pone ningún
número**: remite a §6.5. Así este capítulo queda correcto aunque la cifra se cierre después. No lo
«mejores» poniendo un número.

---

## Antes de dar por bueno lo que te devuelva

1. Busca `25 pruebas` y `sin aceleración GPU`. **No pueden aparecer.**
2. Cuenta los ordinales de §7.3: tiene que llegar a **duodécimo** sin saltos. Y los de §7.4: hasta
   el **octavo**. Es el error mecánico más probable.
3. Recorre el capítulo buscando cifras y comprueba que **cada una lleva su `(§6.N)`**.
4. Verifica que las siete limitaciones y los cinco hallazgos **originales** siguen ahí, íntegros y
   sin renumerar.
5. Busca «no obstante, esto no invalida». Si el modelo añadió frases defensivas a las
   limitaciones, quítalas: el lector técnico saca esa conclusión solo.
6. Verifica que el séptimo hallazgo deja claro que la bajada de fallos **no** fue la corrección de
   los fallos anteriores. Es el matiz más fácil de perder y el más valioso del capítulo.

Si alguna falla, devuélveselo señalando el punto concreto en lugar de corregirlo a mano.

---

## Cuándo hacer este capítulo

**Después del VI, y preferiblemente el último de los capítulos de contenido.** Resume lo que el VI
reporta, así que cualquier cambio de cifra allí obliga a revisarlo aquí. Si lo haces antes,
lo harás dos veces.

Los únicos que van después son los preliminares —resumen, *abstract* e índices—, que dependen de
todo. Ver [`../../01_preliminares/generar/`](../../01_preliminares/generar/).

---

## Un detalle de coordinación

§7.5 tiene que acoger una frase que hoy está en §6.4.2 —«hallazgo que se entrega al equipo de
desarrollo»—, porque el manual prohíbe sugerencias en el capítulo de resultados.

**Escríbela solo si ya corregiste el Capítulo VI.** Si no, quedará duplicada. El paquete instruye
al modelo para que lo anote en el registro de cambios en cualquier caso, de modo que puedas
verificarlo al coordinar los dos capítulos.
