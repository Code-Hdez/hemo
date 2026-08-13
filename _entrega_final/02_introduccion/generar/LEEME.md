# generar/ — paquete autocontenido para la Introducción y bloques asociados

Todo lo necesario para que un LLM produzca el bloque de **Introducción, Objetivos, Justificación y
Limitaciones** completo, con la limitación de infraestructura que falta, y te lo devuelva listo
para pegar en Word. **No requiere acceso al repositorio:** los datos están dentro.

> **Es el paquete más pequeño de los nueve, y el encargo también.** Este bloque está sano: no
> contradice al sistema real en ningún punto sustantivo. Hay **un solo cambio de contenido**.

---

## Cómo se usa

1. Abre una conversación nueva con un LLM capaz.
2. Pega los archivos **en este orden**, cada uno precedido por su nombre en una línea:

```
00_PROMPT_MAESTRO.md          ← quién eres, qué produces, las tres reglas
01_TEXTO_ACTUAL.md            ← el bloque íntegro tal como está hoy
02_HECHOS_VERIFICADOS.md      ← el texto de la limitación y las verificaciones
03_ESTILO_Y_FORMATO.md        ← registro, terminología, números
04_GUION_SECCIONES_NUEVAS.md  ← dónde va el cambio y qué no tocar
05_CONTRATO_DE_SALIDA.md      ← qué devolver y checklist de verificación
```

3. Cierra con: **«Produce ahora el bloque completo según el contrato de salida.»**

Son ~6 500 palabras en total: entra holgadamente en una sola petición.

## Qué te devuelve

Un documento continuo en Markdown —el bloque entero, no parches— más tres bloques: registro de
cambios, **verificación de integridad** e inconsistencias detectadas.

**Para pasarlo a Word:** copia el Markdown, pégalo en un editor que lo renderice, copia lo
renderizado y pégalo en el `.docx` **con formato**. Después aplica el `CHECKLIST_FORMATO.md` de la
guía general.

---

## Qué contiene el paquete

| Archivo | Palabras aprox. | Contenido |
| :--- | ---: | :--- |
| `00_PROMPT_MAESTRO.md` | 800 | El encargo, por qué este bloque está sano, y las tres reglas |
| `01_TEXTO_ACTUAL.md` | 2 020 | Introducción, objetivos, justificación y limitaciones, verbatim |
| `02_HECHOS_VERIFICADOS.md` | 1 000 | El texto de la limitación, la nota de riesgo de los objetivos y las verificaciones |
| `03_ESTILO_Y_FORMATO.md` | 900 | Registro, traducción de anglicismos, convenciones numéricas |
| `04_GUION_SECCIONES_NUEVAS.md` | 800 | Dónde va el cambio y —sobre todo— qué no tocar |
| `05_CONTRATO_DE_SALIDA.md` | 850 | Formato de entrega, tres bloques y checklist de 21 puntos |

---

## Qué falta y por qué importa

**Una limitación de infraestructura.**

El manual pide en esa sección los elementos que «pueden afectar al desarrollo del proyecto siempre
que el estudiante no tenga el control por fuerzas mayores», y da como ejemplo textual «restricción
por capacidad informática del equipo». El proyecto tiene exactamente ese caso: el componente
conversacional depende de una unidad de procesamiento gráfico contratada en modalidad
interrumpible, que el proveedor puede reclamar sin aviso. Y no está declarado.

**No es un párrafo aislado.** Es el que da fundamento a tres pasajes de la segunda mitad del
documento: el procedimiento de contingencia de la demostración (§2.6.1), la limitación operativa
de §7.3 y la sostenibilidad económica de §7.7. Sin él, las tres aparecen de la nada.

---

## Las tres reglas, en corto

1. **La introducción plantea el problema; no lo resuelve ni lo mide.**
2. **Ninguna cifra sin respaldo.** Aquí apenas hay cifras y así debe seguir.
3. **Lo que está bien se reproduce literal.** Si al terminar has modificado más de un párrafo de
   los existentes, te has pasado.

---

## El riesgo real de este encargo

**Que el modelo lo mejore.**

Es el único de los nueve paquetes donde el error probable no es quedarse corto, sino pasarse. Un
redactor ante un texto tiende a pulirlo, y aquí cada retoque es riesgo sin beneficio.

Hay una tentación concreta y peligrosa: **«actualizar» el planteamiento inicial de la solución**.
Ese texto describe la solución sin mencionar ninguna tecnología —ni XGBoost, ni Ollama, ni ningún
modelo— y eso **no es un descuido: es lo que el manual (p. 5) exige de esa sección**. Un modelo
que sepa qué corre realmente el sistema tenderá a corregirlo. Eso lo rompería.

Por eso el contrato de salida pide un bloque de verificación de integridad con recuentos: palabras,
limitaciones, citas, y confirmación explícita de que el planteamiento sigue sin tecnologías.

---

## Antes de dar por bueno lo que te devuelva

1. **Cuenta las palabras.** Entre 2 150 y 2 300. Fuera de ahí, reescribió lo que no debía.
2. Busca `XGBoost`, `Ollama`, `Qwen`, `A100`, `Google Cloud` **en el planteamiento inicial de la
   solución**. Ninguno puede aparecer ahí. (En la limitación nueva sí es correcto mencionar la
   unidad de procesamiento gráfico: es infraestructura, no planteamiento.)
3. Cuenta las limitaciones: tiene que haber exactamente **una más**.
4. Cuenta las citas `[n]`: tienen que ser **las mismas, con los mismos números**. Este bloque está
   al principio del documento y alterar una desplazaría toda la bibliografía.
5. Verifica que los **cinco objetivos específicos** están literales, sin fusiones.
6. Busca «no obstante» en la limitación nueva. Si añadió una frase defensiva, quítala.

---

## Una decisión que ya está tomada

**Los objetivos específicos son cinco y el manual recomienda un máximo de cuatro.**

Es una recomendación, no una prohibición, y los cinco están demostrados como cumplidos en la Tabla
7.1 —que es lo que el manual exige de verdad—. Fundir OE3 y OE4 para bajar a cuatro obligaría a
reescribir §7.2 y debilitaría esa tabla.

**Se dejan en cinco.** El coste es, como máximo, un comentario del asesor. Si lo exige, la fusión
de menor daño está descrita en `02` §2.

---

## Cuándo hacer este bloque

**Cuando quieras: no depende de nada.** Es el único de los nueve que no espera a que otro capítulo
esté cerrado, porque no cita ninguna cifra del Capítulo VI.

Si tienes una hora suelta y no quieres empezar algo largo, este se cierra en esa hora.
