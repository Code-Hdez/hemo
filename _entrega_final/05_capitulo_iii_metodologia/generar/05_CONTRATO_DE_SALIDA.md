# Contrato de salida — qué tienes que devolver exactamente

---

## Formato

**Un único documento en Markdown**, continuo, listo para copiar y pegar en Microsoft Word. No
devuelvas parches, diferencias ni listas de instrucciones: devuelve **el capítulo entero**, desde
el título hasta la última frase de §3.11, con las secciones que no cambian **reproducidas
íntegras**.

Motivo: quien recibe esto va a seleccionar todo, copiar y pegar sobre el capítulo actual. Si
devuelves solo lo modificado, tendrá que reconstruirlo a mano y ahí es donde se cometen los
errores.

### Cómo estructurarlo

````
# Capítulo III — Metodología

[entradilla revisada]

## 3.1. Tipo de proyecto y enfoque metodológico
[texto íntegro, sin cambios]

## 3.11. Metodología de recaracterización y pre-registro de hipótesis

[párrafo de entrada]

### 3.11.1. Motivación y pregunta metodológica
[texto]

| col | col |
| :--- | :--- |
| … | … |

*Tabla 3.12. Identidad sellada del runtime bajo el que se midió.*
````

- Encabezados con `#`, `##` y `###`. **No bajes a nivel 4.**
- Tablas en Markdown estándar con barras. Word las convierte a tabla real al pegar con formato.
- Títulos de tabla **debajo** del elemento, en cursiva.
- Las figuras existentes se mantienen como `[FIGURA imageNN]`, en su sitio.

## Después del capítulo, cuatro bloques obligatorios

### Bloque A — Registro de cambios

| Sección | Tipo | Qué cambió | Por qué |
| :--- | :--- | :--- | :--- |
| Entradilla | Ampliación | Media frase sobre la campaña de recaracterización | §3.11 es nueva y la entradilla enumera el contenido |
| 3.5.1 | Ampliación | Párrafo sobre el congelamiento del *runtime* conversacional | El rigor existe y no estaba documentado |
| 3.7.1 | Ampliación | Fila de la batería F en la Tabla 3.8 + frases de justificación | Faltaba el instrumento de aceptación del proyecto |
| 3.10 | Ampliación | Siete filas de artefactos de la campaña | … |
| 3.11 | Sección nueva | Metodología de recaracterización, once subsecciones | Cumple el cuarto punto que el manual pide para el componente emergente |
| … | | | |

Tipos válidos: `Corrección` · `Ampliación` · `Sección nueva` · `Renumeración` · `Estilo`.

### Bloque B — Marcadores pendientes

- `[PENDIENTE: …]` — qué falta y quién puede aportarlo.
- `[CITA PENDIENTE: …]` — los métodos estadísticos nuevos necesitan referencia.

**Este bloque no debería estar vacío.** §3.11 introduce cuatro procedimientos estadísticos
—Wilson, McNemar, Wilcoxon y análisis de potencia— y el paquete **no incluye sus referencias
bibliográficas**. Si no las tienes, marca `[CITA PENDIENTE: intervalo de Wilson para proporciones
binomiales]` y equivalentes. Si el bloque sale vacío, comprueba que no inventaste una cita.

### Bloque C — Tablas, inventario final

Lista de las tablas 3.1 a 3.12 (o 3.13 si añadiste una segunda) con su título final, marcando
cuáles son nuevas y cuáles cambiaron de contenido.

### Bloque D — Inconsistencias detectadas

Si encuentras una contradicción entre los archivos de este paquete, o un hecho que necesitas y no
está: **no la resuelvas inventando**. Escríbela aquí con la ubicación exacta y las dos versiones
en conflicto.

---

## Checklist de verificación — recórrelo antes de entregar

### Contenido

- [ ] Están las **once** secciones, numeradas 3.1 a 3.11.
- [ ] §3.11 tiene sus **once subsecciones**, de 3.11.1 a 3.11.11.
- [ ] Las secciones íntegras (§3.1, §3.2, §3.3, §3.4, §3.6, §3.7.2, §3.7.3, §3.8, §3.9) están
      **reproducidas completas**, no resumidas ni «mejoradas».
- [ ] Las tres ampliaciones están (§3.5.1, §3.7.1, §3.10).
- [ ] La fila de la batería F va acompañada de las frases que explican su aporte.
- [ ] La extensión total está entre 7 800 y 8 700 palabras.

### Altitud — la Regla 1, que es la que se rompe

Busca cada una de estas cifras en tu salida. **Ninguna puede aparecer:**

- [ ] `60,6` · `54,4` · `21,4` — reducción y latencias.
- [ ] `24,3` · `8,6` · `0,035` — turnos sin respuesta y McNemar.
- [ ] `0,332` — sobrecarga de gramática medida.
- [ ] `−0,145` · `0 de 17` — acuerdo de identificadores.
- [ ] `34,90` · `24,4802` · `40,849` — MBU, tiempo por token, decodificación.
- [ ] El veredicto de cualquiera de las diez hipótesis (REFUTADA, CONFIRMADA, NO EVALUADA…).
- [ ] El resultado del canario de determinismo.

Y verifica lo contrario:

- [ ] **Sí** aparecen los tamaños de muestra (30, 64, 70, 100, 208, 431) y los criterios de
      decisión, porque son diseño.
- [ ] **Sí** aparece el resultado de la auditoría de comparabilidad (11 de 15 no constan), porque
      es lo que decidió cómo se podía medir.

**La prueba final:** si borraras el Capítulo VI, ¿§3.11 se sigue leyendo completa y con sentido?
Si se queda coja, metiste resultados.

### Cifras

- [ ] Toda cifra que escribiste está en `02_HECHOS_VERIFICADOS.md`. Ninguna es estimada.
- [ ] El tamaño del modelo es 17 420 432 739 bytes, **no** 16,93 GB.
- [ ] La versión del servidor de modelos es **0.32.6**, no 0.32.5.
- [ ] Los compendios van truncados a 16 caracteres con su nota al pie.

### Honestidad

- [ ] Las tres limitaciones de la ablación están declaradas, **incluida la tercera** (crudos no
      persistidos, incumplimiento del propio protocolo).
- [ ] Las dos desviaciones de la réplica (D-1 y D-2) están declaradas.
- [ ] Está escrito que la limitación del camino B es **del instrumento, no del sistema**.
- [ ] Está declarado que el modelo anterior sigue instalado y que la comprobación no impide su
      uso.
- [ ] Está escrito que el diseño no distingue un efecto intermedio.
- [ ] Está escrito que una de las once aserciones de verificación falla y queda declarada.

### Estilo

- [ ] Coma decimal en todos los números; espacio como separador de millares.
- [ ] Sin adjetivos de mérito.
- [ ] Sin código, rutas de fichero, nombres de *commit*, ni nombres de variables o funciones.
- [ ] Los nombres de fichero de artefacto se sustituyen por su descripción: «el registro de
      procedencia de fuentes», no `PROCEDENCIA.json`.
- [ ] Toda tabla está referenciada desde el texto antes de aparecer.

---

## Qué hacer si algo no encaja

Es más útil un capítulo con tres marcadores honestos que uno completo con tres cifras inventadas.
Lo primero se cierra en diez minutos; lo segundo puede costar la defensa.
