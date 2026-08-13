# generar/ — paquete autocontenido para los preliminares

Todo lo necesario para que un LLM produzca el bloque de **preliminares** —listas, resumen y
*abstract*— y te lo devuelva listo para pegar en Word. **No requiere acceso al repositorio:** los
datos están dentro.

> ## ⚠️ Este es el último de los nueve
>
> **Todo lo que hay aquí depende de secciones que aún se van a insertar:** §6.6, §6.8, §3.11, §5.9,
> §5.10, §1.1.3.7 y el Anexo E. Regenerar los índices antes de aplicar esos cambios es trabajo que
> hay que repetir entero.
>
> Es el único de los nueve paquetes con un orden obligatorio. Si no has cerrado los capítulos de
> contenido, ciérralos primero.

---

## Cómo se usa

1. Abre una conversación nueva con un LLM capaz.
2. Pega los archivos **en este orden**, cada uno precedido por su nombre en una línea:

```
00_PROMPT_MAESTRO.md          ← quién eres, qué produces, las tres reglas
01_TEXTO_ACTUAL.md            ← portada, listas, resumen y abstract, verbatim
02_HECHOS_VERIFICADOS.md      ← la numeración final y los textos nuevos
03_ESTILO_Y_FORMATO.md        ← registro, convenciones numéricas, formato de listas
04_GUION_SECCIONES_NUEVAS.md  ← qué se produce, qué no, y en qué orden
05_CONTRATO_DE_SALIDA.md      ← qué devolver y checklist de verificación
```

3. Cierra con: **«Produce ahora el bloque de preliminares según el contrato de salida.»**

Son ~7 500 palabras: entra holgadamente en una sola petición.

## Qué te devuelve

Un documento continuo en Markdown más cinco bloques: registro de cambios, **recuento de palabras**,
guion de agradecimientos, verificación de la Tabla de Contenido y **dependencias no verificadas**.

**Para pasarlo a Word:** copia el Markdown, pégalo en un editor que lo renderice, copia lo
renderizado y pégalo en el `.docx` **con formato**. Después aplica el `CHECKLIST_FORMATO.md` de la
guía general y **regenera la Tabla de Contenido**.

---

## Qué contiene el paquete

| Archivo | Palabras aprox. | Contenido |
| :--- | ---: | :--- |
| `00_PROMPT_MAESTRO.md` | 850 | El encargo, la advertencia de orden y las tres reglas |
| `01_TEXTO_ACTUAL.md` | 2 320 | Portada, tres listas, encabezados vacíos, resumen y *abstract* |
| `02_HECHOS_VERIFICADOS.md` | 2 000 | La numeración final de tablas y figuras, y los textos del resumen |
| `03_ESTILO_Y_FORMATO.md` | 890 | Registro, convenciones numéricas, formato de las listas |
| `04_GUION_SECCIONES_NUEVAS.md` | 1 100 | Qué se produce, qué no, y en qué orden |
| `05_CONTRATO_DE_SALIDA.md` | 1 050 | Formato de entrega, cinco bloques y checklist de 34 puntos |

**Nota:** `01_TEXTO_ACTUAL.md` **no incluye la Tabla de Contenido** (líneas 27-300 del original).
Word la regenera automáticamente y reproducirla solo gastaría contexto. Las tres listas sí están,
porque esas hay que rehacerlas a mano.

---

## Los cuatro problemas de este bloque

1. **Los cuatro encabezados de agradecimientos y dedicatorias están vacíos.** Es lo primero que ve
   el comité al abrir el empastado.
2. **La Lista de Tablas no cuadra con el cuerpo:** anuncia una tabla que no existe y numera otra
   con un desfase de uno.
3. **La Lista de Figuras no recoge las doce figuras nuevas** y la de Anexos no recoge el Anexo E.
4. **El resumen describe el módulo conversacional en una frase genérica**, sin una sola cifra, y
   omite el resultado de mayor peso metodológico del proyecto.

---

## Las tres reglas, en corto

1. **El resumen sintetiza; no aporta.** Toda cifra tiene que estar ya en el cuerpo.
2. **El resumen tiene un límite duro de 400 palabras.** Ver abajo.
3. **Los agradecimientos y las dedicatorias no los escribe el LLM.**

---

## Los dos riesgos de este encargo

### 1 · Que el resumen se pase de 400 palabras 🔴

Hay una aritmética que el modelo tiene que resolver, no ignorar:

| | Palabras |
| :--- | ---: |
| Resumen actual | 354 |
| Lo que añade el párrafo nuevo, neto | ~90 |
| **Resultado si solo se añade** | **~445** |
| Máximo del manual | **400** |

**La solución no es recortar el párrafo nuevo, sino el párrafo 4** —validación externa y clínica—,
que hoy repite cifras que el párrafo 3 ya introduce.

El contrato exige un bloque con el recuento explícito. **Si el resultado supera las 400, el bloque
no sirve: devuélveselo.**

### 2 · Que escriba los agradecimientos 🔴

Los cuatro encabezados están vacíos, y un modelo al que se le señala un hueco tiende a llenarlo.
**Un agradecimiento generado se nota inmediatamente**: queda genérico, simétrico y sin ninguna
especificidad. Y es la primera página con texto del empastado.

El paquete pide un **guion de estructura**, no texto, y marcadores de pendiente en los cuatro
sitios.

---

## Antes de dar por bueno lo que te devuelva

1. **Cuenta las palabras del resumen.** Si pasa de 400, devuélveselo.
2. Verifica que los cuatro agradecimientos y dedicatorias llevan **marcador de pendiente**, no
   texto.
3. En la Lista de Tablas: **§6.6 aporta DOS tablas (6.14 y 6.15)** y **la de usabilidad es la
   6.16**. Es el punto donde una lista de tablas se rompe con más facilidad: una tabla que existe,
   que no cambia de contenido, pero sí de número.
4. Busca `1,301` en el resumen en español. Debe ser `1 301`.
5. Verifica que el *abstract* usa **punto** decimal y el resumen **coma**. Es correcto que
   difieran.
6. Lee el bloque E —dependencias no verificadas— **antes que nada**: te dice qué dio por supuesto.
7. Comprueba que **no reprodujo la Tabla de Contenido**.

---

## Una corrección que este paquete incorpora

El mapa de numeración de tablas del Capítulo VI que circulaba en la revisión era **incorrecto**:
asignaba a §6.6 una sola tabla, dejaba usabilidad en 6.15 y daba a §6.8 el rango 6.16–6.20.

**La numeración válida** —la que usan los textos ya redactados de esas dos secciones— es:

| Tablas | Origen |
| :--- | :--- |
| 6.14 y 6.15 | §6.6, que aporta **dos** |
| 6.16 | usabilidad, que se corre |
| 6.17 – 6.23 | §6.8, que aporta **siete** |

Está corregida en `02_HECHOS_VERIFICADOS.md` §2, que es la fuente para reconstruir la Lista de
Tablas.

---

## Lo que este paquete NO cubre

**La Tabla de Contenido.** Word la regenera desde los estilos de título. El resultado traerá la
lista de las siete entradas nuevas que deben aparecer en ella para que lo verifiques.

> Si al regenerarla alguna no aparece, el problema no es del índice: es que **el estilo de título
> no se aplicó** al pegar esa sección en Word.

**Los números de página.** Las columnas van vacías. Se llenan al regenerar los índices en Word,
con el documento ya maquetado.

**Los agradecimientos y las dedicatorias.** Una página por estudiante, paginada en números
romanos. Los escriben los autores.

**La verificación de la portada contra el manual.** El paquete lista los ocho elementos presentes;
comprobar si el manual exige alguno más es trabajo de leer el anexo de formato.
