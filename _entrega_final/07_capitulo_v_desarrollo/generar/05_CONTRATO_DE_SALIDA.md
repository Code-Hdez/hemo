# Contrato de salida — qué tienes que devolver exactamente

---

## Formato

**Un único documento en Markdown**, continuo, listo para copiar y pegar en Microsoft Word. No
devuelvas parches, diferencias ni listas de instrucciones: devuelve **el capítulo entero**, desde
el título hasta la última frase de la síntesis, con las secciones que no cambian **reproducidas
íntegras**.

Motivo: quien recibe esto va a seleccionar todo, copiar y pegar sobre el capítulo actual. Si
devuelves solo lo modificado, tendrá que reconstruirlo a mano y ahí es donde se cometen los
errores.

### Cómo estructurarlo

````
# Capítulo V — Desarrollo del proyecto

[entradilla]

## 5.1. Construcción del pipeline de datos
[texto]

| col | col |
| :--- | :--- |
| … | … |

*Tabla 5.1. Actividades principales desarrolladas en el pipeline de datos.*

[FIGURA image15]

*Figura 5.1. Salida gráfica generada durante la verificación del motor de clasificación.*

## 5.2. Desarrollo del motor de aprendizaje automático
…
````

- Encabezados con `#` y `##` (y `###` solo si una sección nueva lo necesita).
- Tablas en Markdown estándar con barras. Word las convierte a tabla real al pegar con formato.
- Títulos de tabla y pies de figura en cursiva, **debajo** del elemento.
- Las figuras existentes se mantienen como `[FIGURA image15]` … `[FIGURA image19]`, en su sitio.
- Las figuras por producir, como `[FIGURA PENDIENTE 5.N]` seguidas de su pie.

## Después del capítulo, tres bloques obligatorios

### Bloque A — Registro de cambios

Tabla con **todos** los cambios que hiciste respecto del texto original:

| Sección | Tipo | Qué cambió | Por qué |
| :--- | :--- | :--- | :--- |
| 5.2 | Corrección | Causalidad invertida en la frase de la etiqueta de anemia regenerativa | El texto afirmaba que se incluyó *a causa de* tener pocos casos |
| 5.7 | Corrección | Tabla 5.9, fila de límites de seguridad: 50/50 → 31/40 y 15/20 | Cifra inválida que contradecía al §6.4.2 |
| 5.8 | Sección nueva | Cadena de release y contrato de runtime | … |
| … | | | |

Tipos válidos: `Corrección` · `Ampliación` · `Sección nueva` · `Renumeración` · `Estilo` ·
`Traslado`.

### Bloque B — Marcadores pendientes

Lista de **todo** lo que dejaste sin resolver, con su ubicación exacta:

- `[PENDIENTE: …]` — qué falta y quién puede aportarlo.
- `[FIGURA PENDIENTE 5.N]` — las ocho capturas por producir.
- `[CITA PENDIENTE: …]` — si añadiste alguna.

**Este bloque no puede estar vacío**: hay al menos un dato pendiente por diseño (la salida de la
suite de pruebas) y ocho figuras por producir. Si te sale vacío, es que inventaste algo.

### Bloque C — Tablas y figuras, inventario final

Dos listas para actualizar los índices del documento:

- **Tablas 5.1 a 5.12** con su título final.
- **Figuras 5.1 a 5.13** con su pie final, marcando cuáles existen y cuáles están pendientes.

---

## Checklist de verificación — recórrelo antes de entregar

### Contenido

- [ ] Están las **diez** secciones, numeradas 5.1 a 5.10, y la síntesis es la 5.10.
- [ ] Las secciones que no cambian están **reproducidas íntegras**, no resumidas ni omitidas.
- [ ] §5.8 y §5.9 son nuevas y desarrollan lo que pide `04_GUION_SECCIONES_NUEVAS.md`.
- [ ] La extensión total está entre 5 800 y 6 800 palabras.

### Cifras

- [ ] La cifra `50/50` **no aparece en ningún sitio** del documento.
- [ ] La cifra `25 passed` / `25 pruebas` **no aparece**; en su lugar hay un marcador de pendiente.
- [ ] Toda cifra que escribiste está en `02_HECHOS_VERIFICADOS.md`. Ninguna es estimada.
- [ ] Los compendios van truncados a 16 caracteres con su nota al pie.
- [ ] No aparece «Qwen3 4B» ni ninguna referencia a que el modelo corra sobre CPU.

### Altitud — la Regla 1

- [ ] No hay ningún porcentaje de mejora calculado sobre la Tabla 5.12.
- [ ] No aparecen las palabras «exitoso», «demuestra que», «se concluye que», «se recomienda».
- [ ] Las cifras que pertenecen al Capítulo VI están **remitidas**, no reproducidas.
- [ ] No hay ninguna recomendación para trabajo futuro.

### Estilo

- [ ] Coma decimal en todos los números; espacio como separador de millares.
- [ ] Sin adjetivos de mérito.
- [ ] Términos traducidos según la tabla de `03_ESTILO_Y_FORMATO.md`; los que quedan en inglés van
      en cursiva.
- [ ] Sin código, rutas de fichero, nombres de *commit*, ni nombres de variables.
- [ ] Toda tabla y toda figura está referenciada desde el texto antes de aparecer.

### Honestidad

- [ ] La clase de fallo residual está declarada como no resuelta.
- [ ] Los dos apagados de la máquina durante la migración están contados.
- [ ] El incidente de capacidad zonal está declarado.
- [ ] Los dos incidentes de disco lleno están mencionados.
- [ ] El modelo anterior que sigue instalado en el nodo está declarado, si lo mencionas.

---

## Qué hacer si algo no encaja

Si encuentras una contradicción entre los archivos de este paquete, o un hecho que necesitas y no
está: **no la resuelvas inventando**. Escríbelo al final, en un cuarto bloque llamado
«Inconsistencias detectadas», con la ubicación exacta y las dos versiones en conflicto.

Es más útil un capítulo con tres marcadores honestos que uno completo con tres cifras inventadas.
Lo primero se cierra en diez minutos; lo segundo puede costar la defensa.
