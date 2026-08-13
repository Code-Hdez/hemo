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
- **Nada de listas donde corresponde prosa.** El capítulo es texto corrido con tablas de apoyo, no
  una presentación con viñetas. Usa listas solo para enumeraciones genuinas —los cuatro mecanismos
  de fallo, los elementos que resuelve el completado determinista— y siempre introducidas por una
  frase completa.

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

## Tablas

- Título **debajo** de la tabla, en cursiva, numerado: *Tabla 5.10. Contrato de runtime del nodo de
  inferencia.*
- Encabezado de columna con mayúscula solo en la primera palabra.
- Columnas numéricas alineadas a la derecha; de texto, a la izquierda.
- Toda tabla debe estar **referenciada desde el texto** antes de aparecer: «…se resume en la Tabla
  5.10». Una tabla que nadie menciona es una tabla que el comité pregunta por qué está.
- No metas una tabla donde bastan dos frases.

## Figuras

- Pie **debajo**, en cursiva, numerado.
- Toda figura referenciada desde el texto.
- Para las que aún no existen, usa exactamente el marcador `[FIGURA PENDIENTE 5.N]` seguido de su
  pie. No inventes descripciones de capturas que no has visto.

## Encabezados

Cuatro niveles como máximo, según el manual:

```
Capítulo V — Desarrollo del proyecto        (nivel 1)
5.8. Cadena de release y contrato de runtime  (nivel 2)
5.8.1. El manifiesto de versión               (nivel 3)
```

Las secciones nuevas **pueden** usar nivel 3 si lo necesitan, pero no bajes a nivel 4.

## Referencias cruzadas

- A otras secciones: «§6.8», «el Capítulo VI», «§4.2.4».
- Cuando una cifra pertenezca al Capítulo VI, remite en lugar de reproducir: «la caracterización
  del comportamiento resultante se presenta en §6.8».
- **No inventes referencias bibliográficas.** Si un párrafo pediría una cita, escribe
  `[CITA PENDIENTE: tema]` y anótalo en el registro de cambios. El Capítulo V es de construcción
  propia y normalmente no necesita citas.

## Lo que NO debe aparecer en el capítulo

- ❌ Fragmentos de código, comandos de consola, nombres de fichero del repositorio, rutas.
- ❌ Volcados de estructuras de datos.
- ❌ Nombres de *commit*, identificadores de rama, referencias a control de versiones.
- ❌ Nombres de variables o funciones del código.
- ❌ Interpretación de resultados o recomendaciones (van a los capítulos VI y VII).
- ❌ Anglicismos evitables.

El capítulo describe **qué se construyó y cómo**, en el lenguaje de la ingeniería, no en el del
repositorio. Un lector técnico que no tenga acceso al código debe poder entenderlo completo.
