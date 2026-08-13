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
- **Nada de listas donde corresponde prosa.** El marco teórico es prosa argumentada con citas, no un listado de definiciones sueltas. La excepción es el glosario §1.2, que **sí** es una lista de entradas con su definición, y donde cada entrada nueva debe seguir exactamente el formato de las existentes: **término en negrita**, dos puntos, definición en prosa.

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

- Título **debajo** de la tabla, en cursiva, numerado: *Tabla 1.1. Comparación de métricas para clasificación multietiqueta desbalanceada.*
- Encabezado de columna con mayúscula solo en la primera palabra.
- Columnas numéricas alineadas a la derecha; de texto, a la izquierda.
- Toda tabla debe estar **referenciada desde el texto** antes de aparecer: «…se resume en la
  Tabla 1.1». Una tabla que nadie menciona es una tabla que el comité pregunta por qué está.
- No metas una tabla donde bastan dos frases.

## Figuras

- Pie **debajo**, en cursiva, numerado.
- Toda figura referenciada desde el texto.
- Para las que aún no existen, usa exactamente el marcador `[FIGURA PENDIENTE 1.N]` seguido de su pie. No
  inventes descripciones de capturas que no has visto.
- Las figuras nuevas se insertan en **PDF o SVG**, nunca PNG: el empastado las imprime y el PNG
  se pixela.

## Encabezados

Cuatro niveles como máximo, según el manual:

```
Capítulo I — Marco Teórico                     (nivel 1)
1.1. Marco Teórico                             (nivel 2)
1.1.3 Aprendizaje Automático Aplicado…         (nivel 3)
1.1.3.7. Rendimiento de inferencia de modelos… (nivel 4)
```

## Referencias cruzadas

- A otras secciones: «§6.8», «el Capítulo VI», «§4.2.4».
- **Cada afirmación técnica no trivial necesita cita.** Es el capítulo donde el manual más lo
  exige.
- **No inventes referencias.** Si un párrafo pide una cita que no tienes, escribe
  `[CITA PENDIENTE: tema exacto que hay que citar]` y anótalo en el registro de cambios. Es
  particularmente crítico en §1.1.3.7: ahí se cita el valor que el Capítulo VI refuta, y una
  refutación contra una fuente inventada destruye el capítulo entero.
- Las citas nuevas se numeran **por orden de aparición** a partir del número que corresponda; deja
  el marcador `[REF-NUEVA-1]`, `[REF-NUEVA-2]`… y la lista al final, porque la renumeración final
  se hace en Word con referencias cruzadas.

## Lo que NO debe aparecer

- ❌ Fragmentos de código, comandos de consola, nombres de fichero del repositorio, rutas.
- ❌ Volcados de estructuras de datos (JSON, YAML, diccionarios).
- ❌ Nombres de *commit*, identificadores de rama, referencias a control de versiones.
- ❌ Nombres de variables o funciones del código.
- ❌ Anglicismos evitables.
- ❌ **Resultados propios.** El marco teórico presenta lo que dice la literatura, no lo que midió
  este proyecto. La cifra de 0,332 ms/token **no va aquí**; aquí va el valor publicado que ella
  después refuta.
- ❌ Descripciones de la arquitectura de HemoVet. Eso es Capítulo II y IV.
- ❌ Wikipedia, blogs sin autoría, foros. El manual los prohíbe.

El capítulo tiene que dejar a un ingeniero capaz de leer el Capítulo VI sin buscar nada fuera.
Esa es la prueba: si §6.8 usa un término y §1.2 no lo define, falta trabajo aquí.
