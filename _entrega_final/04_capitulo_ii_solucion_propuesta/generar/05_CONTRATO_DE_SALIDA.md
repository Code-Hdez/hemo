# Contrato de salida — qué tienes que devolver exactamente

---

## Formato

**Un único documento en Markdown**, continuo, listo para copiar y pegar en Microsoft Word. No
devuelvas parches, diferencias ni listas de instrucciones: devuelve **el capítulo entero**, desde
el título hasta el último criterio de éxito, con las secciones que no cambian **reproducidas
íntegras**.

Motivo: quien recibe esto va a seleccionar todo, copiar y pegar sobre el capítulo actual. Si
devuelves solo lo modificado, tendrá que reconstruirlo a mano y ahí es donde se cometen los
errores. En este capítulo, además, hay una renumeración de tablas y figuras que afecta a todo el
texto: solo tiene sentido aplicarla sobre el capítulo completo.

### Cómo estructurarlo

````
# Capítulo II — Solución propuesta

## 2.1. Definición del Proyecto
[texto con la frase del modelo corregida]

## 2.5. Presupuesto
[párrafo introductorio, con las cinco categorías]

### 2.5.1. Hardware
[párrafo de criterio de valoración]

| Ítem | Especificación | Costo (USD) | Costo (RD$) | Observación |
| :--- | :--- | ---: | ---: | :--- |
| … | … | `[PENDIENTE: …]` | `[PENDIENTE: …]` | … |

*Tabla 2.4. Estimación de costos de hardware del proyecto HemoVet.*

[párrafo de tasa de cambio y de las horas de la máquina de inferencia]
````

- Encabezados con `#`, `##` y `###`.
- Tablas en Markdown estándar con barras. Word las convierte a tabla real al pegar con formato.
- Títulos de tabla y pies de figura **debajo** del elemento, en cursiva, con la numeración nueva.
- Las figuras existentes se mantienen como `[FIGURA imageNN]`, en su sitio.

## Después del capítulo, cuatro bloques obligatorios

### Bloque A — Registro de cambios

| Sección | Tipo | Qué cambió | Por qué |
| :--- | :--- | :--- | :--- |
| 2.1 | Corrección | Identidad del modelo conversacional | Decía un modelo de 4 mil millones; el *runtime* sirve 27 mil millones |
| 2.2.2 | Ampliación | Fila de la cadena de versiones desplegables | Trabajo real que no se reclamaba en ninguna parte |
| 2.5.1 | Reconstrucción | Tabla de hardware con dos monedas, equipos propios valorados, línea de GPU y contingencia | Tres incumplimientos del manual más la migración de agosto |
| 2.5.3–2.5.5 | Secciones nuevas | Datos, recursos humanos y costos operativos | El propio texto anunciaba cinco categorías y había dos |
| 2.6.1 | Reescritura | Entorno de ejecución | Describía un despliegue que ya no existe |
| 2.6.3 | Corrección | Criterio de latencia separado en dos | El umbral de 10 s no se cumple y la propia tesis lo demuestra |
| Todo | Renumeración | Tablas 1–6 → 2.1–2.6; figuras 1–3 → 2.1–2.3 | El manual pide numeración por categoría |
| … | | | |

Tipos válidos: `Corrección` · `Ampliación` · `Sección nueva` · `Reconstrucción` · `Renumeración` ·
`Estilo`.

### Bloque B — Marcadores pendientes 🔴

**El bloque más importante de este capítulo.** Lista cada `[PENDIENTE: …]` con:

- su ubicación exacta,
- **qué hay que consultar para resolverlo** (facturación del proyecto, tarifa pública del
  proveedor, valoración de mercado local, cronograma),
- y quién puede aportarlo.

**Este bloque no puede estar vacío ni ser corto.** El paquete no incluye ni una sola cifra
monetaria: todas las de la tabla de hardware, las tarifas de recursos humanos y la tasa de cambio
son pendientes por diseño. **Si te salen menos de ocho marcadores, es que inventaste importes.**

### Bloque C — Tablas y figuras, inventario final

Dos listas, con la correspondencia entre numeración vieja y nueva:

| Antes | Ahora | Título final |
| :--- | :--- | :--- |
| Tabla 4 | Tabla 2.4 | Estimación de costos de hardware del proyecto HemoVet |
| … | | |

Incluye las tablas nuevas (2.7, 2.8 y 2.9 si la usaste) y **marca las referencias del cuerpo que
tuviste que actualizar**.

### Bloque D — Inconsistencias detectadas

Si encuentras una contradicción entre los archivos de este paquete, o un hecho que necesitas y no
está: **no la resuelvas inventando**. Escríbela aquí con la ubicación exacta y las dos versiones
en conflicto.

---

## Checklist de verificación — recórrelo antes de entregar

### Contenido

- [ ] Están las seis secciones, de §2.1 a §2.6, con sus subsecciones.
- [ ] §2.5 tiene **cinco** subsecciones: 2.5.1 a 2.5.5. Las tres últimas son nuevas.
- [ ] Las secciones íntegras (§2.1.1, §2.2.1, §2.3, §2.4 y sus subsecciones, §2.6.2) están
      **reproducidas completas**, no resumidas ni «mejoradas».
- [ ] §2.6.1 está reescrita con la topología de dos nodos y los tres puntos de contingencia.
- [ ] La extensión total está entre 5 200 y 6 100 palabras.

### El presupuesto — la Regla 2

- [ ] **Ningún importe monetario está inventado ni estimado.** Cada uno está justificado o marcado
      como pendiente.
- [ ] La tabla de hardware tiene **columna en USD y columna en RD$**.
- [ ] Los dos equipos propios están valorados (o marcados como pendientes), no en 0,00.
- [ ] Hay una fila para la máquina de inferencia con unidad de procesamiento gráfico.
- [ ] Hay una línea de **contingencia del 10 %**.
- [ ] Hay una nota con la tasa de cambio y su fecha.
- [ ] **Ninguna partida aparece en dos subsecciones.** Comprueba especialmente la máquina de
      inferencia entre §2.5.1 y §2.5.5.
- [ ] Si se usan las horas de las ventanas de encendido, está escrito que **tres son cota
      inferior** y que cubren solo la campaña de medición.

### Datos del sistema

- [ ] `Qwen3 4B` **no aparece**.
- [ ] `Ollama sobre CPU` **no aparece**.
- [ ] La frase «la VM con GPU no se presentará como parte del entorno operativo» **no aparece**.
- [ ] `latencia inferior a 10 segundos` **no aparece** como criterio.
- [ ] El criterio de latencia está **separado en dos**: análisis hematológico y conversación.
- [ ] Está el criterio nuevo de identidad del modelo sellado.

### Altitud — la Regla 1

- [ ] No se reporta ningún resultado del Capítulo VI. Las cifras de §6.8 aparecen **solo** como
      referencia que justifica un criterio, con su remisión.
- [ ] No hay tablas de mediciones.

### Numeración

- [ ] Las seis tablas están renumeradas a `Tabla 2.N`.
- [ ] Las tres figuras están renumeradas a `Figura 2.N`.
- [ ] **Las referencias del cuerpo se actualizaron**: no queda ningún «la Tabla 4» ni «la
      Figura 2» apuntando a la numeración vieja.
- [ ] Las tablas nuevas continúan la serie sin repetir número.

### Estilo

- [ ] Coma decimal en todos los importes: `0,00`, no `0.0`.
- [ ] Espacio como separador de millares.
- [ ] Sin adjetivos de mérito.
- [ ] Sin código, rutas de fichero, nombres de *commit*, ni nombres de variables. Los nombres de
      máquina virtual y de tipo de instancia **sí** pueden aparecer: son parte de la descripción
      del entorno.

---

## Qué hacer si algo no encaja

Un presupuesto con ocho importes pendientes y una estructura correcta se completa en veinte
minutos con acceso a la facturación. Un presupuesto con ocho importes inventados hay que rehacerlo
entero, y si alguien pregunta por uno en la defensa, no hay respuesta posible.
