# Contrato de salida — qué tienes que devolver exactamente

---

## Formato

**Un único documento en Markdown**, continuo, listo para copiar y pegar en Microsoft Word. No
devuelvas parches, diferencias ni listas de instrucciones: devuelve **el capítulo entero**, desde
el título hasta la última entrada del glosario, con las secciones que no cambian **reproducidas
íntegras**.

Motivo: quien recibe esto va a seleccionar todo, copiar y pegar sobre el capítulo actual. Si
devuelves solo lo modificado, tendrá que reconstruirlo a mano y ahí es donde se cometen los
errores. Y en este capítulo el riesgo es mayor que en otros, porque el glosario tiene decenas de
entradas y basta perder una para que el documento quede peor que antes.

### Cómo estructurarlo

````
# Capítulo I — Marco Teórico

## 1.1. Marco Teórico

### 1.1.1. Fundamentos Clínicos-Veterinarios
[texto íntegro, con sus citas [n] intactas]

#### 1.1.3.7. Rendimiento de inferencia de modelos de lenguaje
[texto nuevo]

## 1.2. Definición de Términos y Glosario

### C. Términos de sistemas de IA y arquitectura

**Arranque a prueba de fallos (*fail-closed*):** definición…

**Decodificación restringida por gramática (GBNF):** definición…
````

- Encabezados con `#`, `##`, `###` y `####`. §1.1.3.7 es de nivel 4, como sus hermanas.
- Las entradas de glosario con el término en negrita seguido de dos puntos, en prosa continua.
- Las figuras existentes se mantienen como `[FIGURA imageNN]`, en su sitio.
- **Las citas `[n]` existentes se reproducen con su número actual, sin excepción.**

## Después del capítulo, cuatro bloques obligatorios

### Bloque A — Registro de cambios

| Sección | Tipo | Qué cambió | Por qué |
| :--- | :--- | :--- | :--- |
| 1.1.3.7 | Sección nueva | Rendimiento de inferencia de modelos de lenguaje | §6.8 refuta un valor de la literatura que el marco no presentaba |
| 1.2 C | Corrección | Entrada «LLM» | Describía un modelo de 4 mil millones sobre un *runtime* que sirve 27 mil millones |
| 1.2 C | Corrección | Entrada «Ollama» | Versión y modelo desactualizados |
| 1.2 B | Ampliación | Seis términos de inferencia estadística | El Capítulo VI los usa y el glosario no los definía |
| 1.2 C | Ampliación | Seis términos de rendimiento y despliegue | … |
| … | | | |

Tipos válidos: `Corrección` · `Ampliación` · `Sección nueva` · `Estilo`.

### Bloque B — Referencias nuevas

**El bloque más importante de tu salida.** Una tabla con cada marcador que hayas usado:

| Marcador | Qué se necesita citar | ¿La tienes? |
| :--- | :--- | :--- |
| `[REF-NUEVA-1]` | Análisis *roofline* aplicado a inferencia de transformadores | `[CITA PENDIENTE]` |
| `[REF-NUEVA-2]` | 🔴 La fuente que publica el sobrecosto de la decodificación por gramática | `[CITA PENDIENTE]` |
| … | | |

Si tienes una referencia **verificada**, escríbela completa en formato IEEE. Si no la tienes,
déjala como `[CITA PENDIENTE: …]` con una descripción **precisa** de qué hay que buscar: autor
probable, tipo de publicación, y el dato concreto que debe aportar.

> 🔴 **`[REF-NUEVA-2]` no admite aproximaciones.** §6.8 refuta cuantitativamente el valor que
> publica esa fuente. Una cita inexacta convierte el mejor resultado del proyecto en el error más
> fácil de verificar durante la defensa. Si no la tienes, dilo con claridad y describe con
> precisión qué se busca.

### Bloque C — Marcadores pendientes

- `[CITA PENDIENTE: …]` — todas, repetidas aquí con su ubicación exacta en el texto.
- `[PENDIENTE: …]` — cualquier otro dato que dejaste sin resolver.

**Este bloque no puede estar vacío:** el paquete no incluye ni una sola de las referencias nuevas.
Si te sale vacío, es que inventaste una cita.

### Bloque D — Inconsistencias detectadas

Si encuentras una contradicción entre los archivos de este paquete, o un hecho que necesitas y no
está: **no la resuelvas inventando**. Escríbela aquí con la ubicación exacta y las dos versiones
en conflicto.

---

## Checklist de verificación — recórrelo antes de entregar

### Contenido

- [ ] §1.1.1, §1.1.2, §1.1.3.1 a §1.1.3.6 y §1.1.4 están **reproducidas íntegras**, sin resumir,
      sin reordenar y sin retoques de redacción.
- [ ] §1.1.3.7 existe, va al final de §1.1.3 y cubre sus **cinco** apartados: régimen limitado por
      memoria, *prefill* frente a decodificación, decodificación por gramática, determinismo y
      reproducibilidad de mediciones.
- [ ] El glosario conserva **todas** sus entradas actuales de los apartados A, B y D.
- [ ] Las entradas «LLM» y «Ollama» están corregidas.
- [ ] Hay **doce entradas nuevas** de glosario, en orden alfabético dentro de su apartado.
- [ ] La extensión total está entre 8 200 y 9 000 palabras.

### Altitud — la Regla 1

Busca estas cifras en tu salida. **Ninguna puede aparecer:**

- [ ] `0,332` — la sobrecarga medida.
- [ ] `44` como factor de discrepancia.
- [ ] `34,90` · `24,4802` · `40,849` · `117,0` — mediciones y techo calculado.
- [ ] `11 de 15` — resultado de la auditoría de comparabilidad.
- [ ] Cualquier latencia del asistente.

Y verifica lo contrario:

- [ ] **Sí** aparece el valor que la literatura atribuye a la gramática (≥ 10 ms/token), con su
      cita o su marcador.
- [ ] **Sí** aparece la frase que declara que ese valor corresponde a un despliegue concreto y su
      reproducción es una pregunta empírica.
- [ ] **Sí** aparece la advertencia de GB frente a GiB.
- [ ] No hay ninguna descripción de la arquitectura de HemoVet (eso es Capítulo II y IV).
- [ ] No hay ninguna insinuación del tipo «como se verá más adelante».

**La prueba final:** lee §1.1.3.7 imaginando que el Capítulo VI no existe. Si suena a preámbulo de
algo, tiene resultados dentro.

### Citas — la Regla 2

- [ ] **Ninguna referencia inventada.** Ni una.
- [ ] Todas las citas nuevas van como `[REF-NUEVA-n]`, listadas en el bloque B.
- [ ] **Ninguna cita existente cambió de número.**
- [ ] Se verificó si Wilcoxon y Cohen ya están citados en el documento antes de proponer entradas
      nuevas; si lo están, se reutilizan.
- [ ] No hay ninguna fuente de Wikipedia, blog sin autoría o foro.

### Estilo

- [ ] Las entradas nuevas de glosario tienen el **mismo formato** que las existentes: término en
      negrita, dos puntos, prosa continua.
- [ ] Coma decimal en todos los números; espacio como separador de millares (`2 039 GB/s`).
- [ ] Los términos que quedan en inglés van en cursiva.
- [ ] Sin código, rutas de fichero, nombres de *commit*, ni nombres de variables.
- [ ] Sin adjetivos de mérito.

---

## Qué hacer si algo no encaja

Es más útil un capítulo con cinco marcadores de cita honestos que uno completo con una referencia
inventada. Lo primero se cierra con una tarde de búsqueda; lo segundo es el único error de este
documento que un miembro del comité puede verificar desde su teléfono en treinta segundos.
