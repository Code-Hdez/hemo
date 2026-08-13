# Estilo y formato — cómo tiene que estar escrito

---

## Registro

- **Tercera persona, impersonal.** «Se implementó», «el sistema valida», «la cadena de
  despliegue fija». Nunca «implementamos», «nuestro sistema», «yo».
- **Pasado para lo ejecutado, presente para lo que el sistema hace de forma permanente.**
  «Se construyó una puerta de contenido» / «la puerta invalida la respuesta que solo deriva».
- **Sin adjetivos de mérito.** Prohibidos: robusto, potente, exitoso, excelente, innovador,
  puntero, de última generación, impresionante, notable. El lector juzga; el texto informa.
- **Sin superlativos ni intensificadores vacíos:** muy, sumamente, altamente, extremadamente.
- **Sin lenguaje comercial.** No es una propuesta de venta, es un informe.
- **Frases de longitud media.** Si una frase pasa de cuatro líneas, pártela.
- **Nada de listas donde corresponde prosa.** Los agradecimientos y las dedicatorias son prosa continua, no listas de nombres con viñetas. El resumen ejecutivo es **un solo bloque de párrafos**, sin viñetas ni encabezados internos. Las listas de tablas, figuras y anexos sí son tablas, y esas son la excepción.

## Terminología: usar el término español

El documento está en español y su glosario define los términos en español. Traduce, y deja el
término inglés entre paréntesis solo la primera vez si aporta:

| No escribir | Escribir |
| :--- | :--- |
| GPU | unidad de procesamiento gráfico |
| hash, digest | compendio criptográfico |
| release | versión desplegable |
| rollback | reversión |
| fail-closed | arranque a prueba de fallos |
| guardrail | límite de seguridad, barrera de seguridad |
| prompt | mensaje, instrucción |
| embeddings | representaciones vectoriales |
| endpoint | punto de acceso, ruta |
| timeout | tiempo de espera agotado |
| deploy, deployment | despliegue |
| spot, preemptible | instancia interrumpible |
| entailment | implicación textual |
| streaming | transmisión en flujo |
| warm-up | calentamiento |
| health check | comprobación de estado |

**Cursivas** para los términos que se dejen en otro idioma —lo exige el manual institucional—:
*prompt injection*, *spot*, *fail-closed*, *prefill*, *bootstrap*, *dataset*, *pipeline*,
*overlay*, *flag*, *dashboard*.

Los nombres propios de tecnología **no se traducen** y van sin cursiva: FastAPI, PostgreSQL,
SQLAlchemy, Alembic, React, Vite, TypeScript, Docker, ChromaDB, FastEmbed, Ollama, XGBoost,
Pydantic, NVIDIA A100, CUDA.

## Números

- **Coma decimal**, siempre: `24,48 ms`, `77,5 %`, `0,332`. Nunca `24.48`.
- **Espacio fino como separador de millares**: `17 420 432 739`, `1 252`, `1 000`. Nunca comas.
- **Espacio antes del signo de porcentaje**: `77,5 %`.
- Unidades sin traducir y sin cursiva: `ms`, `s`, `tok/s`, `GB`, `GiB`, `GB/s`, `B`.
- Cifras de cero a nueve en palabras cuando no son medidas: «dos capas independientes», «cuatro
  mecanismos». Con unidad, siempre en dígitos: «5 descartes», «30 generaciones».
- **Compendios criptográficos truncados a 16 caracteres** seguidos de `…`, con nota al pie en la
  primera tabla que los use.

> ⚠️ El documento actual mezcla `1,301 registros` (coma de millar inglesa) con `0.9529` (punto
> decimal inglés). **Ambos son errores de estilo** que hay que corregir al pasar por el texto:
> `1 301 registros` y `0,9529`.

## Tablas

- Título **debajo** de la tabla, en cursiva, numerado: *Tabla 6.14. Señales del reporte de vigilancia poblacional.*
- Encabezado de columna con mayúscula solo en la primera palabra.
- Columnas numéricas alineadas a la derecha; de texto, a la izquierda.
- Toda tabla debe estar **referenciada desde el texto** antes de aparecer: «…se resume en la
  Tabla 6.14». Una tabla que nadie menciona es una tabla que el comité pregunta por qué está.
- No metas una tabla donde bastan dos frases.

## Figuras

- Pie **debajo**, en cursiva, numerado.
- Toda figura referenciada desde el texto.
- Para las que aún no existen, usa exactamente el marcador `[FIGURA PENDIENTE 6.N]` seguido de su pie. No
  inventes descripciones de capturas que no has visto.
- Las figuras nuevas se insertan en **PDF o SVG**, nunca PNG: el empastado las imprime y el PNG
  se pixela.

## Encabezados

Cuatro niveles como máximo, según el manual:

```
Resumen ejecutivo                              (nivel 1)
Agradecimientos – Carlos David Hernández Collado  (nivel 1)
Lista de Tablas                                (nivel 1)
```

## Referencias cruzadas

- A otras secciones: «§6.8», «el Capítulo VI», «§4.2.4».
- Las tres listas y el índice llevan **número de página**. Si no lo tienes, deja la celda vacía
  y anótalo: no inventes páginas.
- **No inventes referencias bibliográficas** en el resumen. El resumen ejecutivo no lleva citas.

## Lo que NO debe aparecer

- ❌ Fragmentos de código, comandos de consola, nombres de fichero del repositorio, rutas.
- ❌ Volcados de estructuras de datos (JSON, YAML, diccionarios).
- ❌ Nombres de *commit*, identificadores de rama, referencias a control de versiones.
- ❌ Nombres de variables o funciones del código.
- ❌ Anglicismos evitables.
- ❌ Cifras que no aparezcan en el cuerpo del documento. El resumen **sintetiza**, no aporta.
- ❌ Citas bibliográficas en el resumen ejecutivo o en el *abstract*.
- ❌ Interpretación o valoración del proyecto en los agradecimientos.

Los preliminares son lo primero que el comité lee y lo último que se escribe. Un resumen que
no da una sola cifra, o un agradecimiento vacío bajo un encabezado que sí está, son los dos
errores que más caros salen por lo poco que cuesta evitarlos.
