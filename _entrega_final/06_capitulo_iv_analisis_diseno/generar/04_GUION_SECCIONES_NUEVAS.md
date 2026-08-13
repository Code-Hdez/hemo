# Guion de las ampliaciones — dónde va cada cosa y con qué altitud

> Esto **no es texto para copiar**: los párrafos nuevos ya están redactados en
> `02_HECHOS_VERIFICADOS.md`. Este archivo dice **dónde encajan, en qué orden y qué hay que
> vigilar al integrarlos**.
>
> No hay secciones nuevas en este capítulo. Todo el trabajo es de ampliación dentro de las
> existentes, y el riesgo no es escribir poco: es escribir el Capítulo V por error.

---

## Mapa de intervención

| Sección | Qué se hace | Origen | Tamaño |
| :--- | :--- | :--- | :--- |
| 4.1.4 | Añadir dos filas a la Tabla 4.4 | `02` §4 | 2 filas |
| 4.2.4 | Añadir cuatro párrafos al final | `02` §2 | 4 párrafos |
| 4.2.5 | Añadir tres párrafos tras el segundo + corregir referencia + marcador de figura | `02` §1 y §3 | 3 párrafos |
| 4.2.6 | Añadir una nota al pie y una fila | `02` §5 | 1 nota + 1 fila |
| 4.3 | Añadir media frase | `02` §6 | media frase |

Todo lo demás se reproduce **íntegro**.

---

## §4.1.4 · Requerimientos no funcionales

**Dos filas al final de la Tabla 4.4, continuando la numeración.**

RNF-07 y RNF-08. Reproduce la tabla completa con todas sus filas actuales y añade las dos al
final.

**Lo que conviene notar en el texto que rodea a la tabla:** RNF-07 no es una aspiración, es un
requisito **que el sistema ya cumple por diseño**, porque la capa conversacional está aislada del
resto del sistema. Si el párrafo que introduce la tabla enumera los tipos de requerimiento,
menciónalo ahí; si no, la fila se sostiene sola.

> No conviertas esto en un párrafo de justificación. Es una tabla de requerimientos: las filas
> hablan por sí solas.

---

## §4.2.4 · Diseño del módulo LLM/RAG

**Cuatro párrafos al final de la subsección, después de la descripción de la cadena actual.**

El orden está pensado y no conviene alterarlo, porque va de lo más estructural a lo más
instrumental:

1. **Puerta de contenido.** Es la que corrige un modo de fallo del diseño anterior, así que va
   primera: explica por qué la cadena de validación previa era insuficiente.
2. **Completado determinista desde la base de datos.** Es el cambio de mayor alcance: establece
   un principio —lo que el sistema ya sabe no se genera— que reordena la responsabilidad entre
   código y modelo.
3. **Resolución de elipsis y seguimientos.** Actúa antes en la cadena, pero se explica después
   porque depende de entender la clasificación de ámbito que ya está descrita.
4. **Instrumentación de la verificación de citas.** Es el más menor de los cuatro y cierra.

### Lo que hay que vigilar

**El primer párrafo contiene la única observación que podría leerse como narrativa de desarrollo:**
que la puerta «corrige un modo de fallo silencioso del diseño anterior». Está formulada como
**propiedad del diseño previo**, no como episodio: dice qué fallaba en la arquitectura, no cuándo
se descubrió ni quién lo detectó. Mantenlo así.

**El segundo párrafo lleva una lista larga** —los datos que se responden por código— y es una
enumeración genuina, así que puede ir como lista o como prosa con punto y coma, según cómo esté
escrito el resto de §4.2.4. Elige lo que sea coherente con la subsección, no lo que sea más
cómodo.

> ❌ **Lo que no puede aparecer en ninguno de los cuatro:** el número de la ronda de trabajo, la
> batería que detectó cada problema, ninguna cifra de cuántos turnos fallaban. Todo eso es §5.10.

---

## §4.2.5 · Diseño de despliegue

**La ampliación más grande del capítulo. Tres párrafos, y tres operaciones distintas.**

### 1 · Los tres párrafos

Van **después del segundo párrafo actual** —el de las dependencias estrictas de arranque— y antes
de la figura.

El orden es de fuera hacia dentro, y es el correcto:

1. **La topología de dos nodos.** Qué corre en cada uno y por qué se comunican por dirección
   interna estática. Termina con la consecuencia práctica: la migración de hardware se hizo sin
   tocar el backend. Esa frase es la que demuestra que la separación no era decorativa.
2. **El manifiesto de versión.** Qué fija y por qué. La frase de cierre —«el manifiesto es el
   contrato entre lo que se construyó y lo que se ejecuta»— es la que da sentido a todo el
   párrafo; no la recortes.
3. **El arranque a prueba de fallos.** Qué valida, en cuántas capas, y qué hace si falla.

### 2 · La excepción de cronología

El tercer párrafo narra en pasado los dos apagados de la máquina durante la migración. **Es la
única cronología admitida en el capítulo**, y está justificada: son la evidencia de que la
política opera. Un mecanismo de protección que nunca se ha disparado es una declaración de
intenciones; uno que se disparó dos veces cuando debía es un hecho verificado.

**Mantén el registro sobrio.** No es una anécdota ni un contratiempo: es una validación no
planificada. La frase «comportándose exactamente como estaba diseñada» es la que fija esa lectura.

### 3 · La referencia cruzada y la figura

Dos cosas mecánicas que se olvidan:

- **Corregir «Figura 4.5» a «Figura 4.6»** en el cuerpo, y unificar el título en los tres sitios
  donde aparece. Detalle en `02` §3.
- **Añadir el marcador `[FIGURA PENDIENTE 4.7]`** con su pie redactado, para el diagrama de
  despliegue que el manual pide para esta titulación y que hoy no existe. Colócalo después de los
  tres párrafos nuevos y **referéncialo desde el texto**, como cualquier otra figura.

> No describas lo que se vería en un diagrama que no has visto. El pie que está en `02` dice qué
> debe contener; eso basta.

---

## §4.2.6 · Contratos API versionados

**Una nota y una fila.**

La nota de magnitud —doce módulos, cuarenta rutas— va como nota al pie de la Tabla 4.6 o como
frase en el párrafo que la introduce. **Comprueba que la cifra de módulos coincide con la que dice
§4.2.1**: son los mismos doce, y una discrepancia entre dos secciones del mismo capítulo es de las
cosas que un lector atento encuentra.

La fila de contratos de despliegue va al final de la tabla. **El punto que la justifica** —y que
conviene que quede dicho en una frase— es que son contratos versionados igual que los HTTP, aunque
no lo sean: describen un estado desplegable y su compatibilidad, y cambiar uno rompe cosas
exactamente igual.

---

## §4.3 · Síntesis del diseño propuesto

**Media frase, no más.**

La síntesis funciona. Solo hay que mencionar la separación del nodo de inferencia, porque es la
decisión arquitectónica de mayor alcance de las que se añaden y una síntesis que no la recoja
queda desactualizada respecto de su propio capítulo.

Intégrala en la frase que ya hable de la arquitectura de despliegue, si la hay. No abras un
párrafo nuevo.

---

## La prueba de altitud, al terminar

Es la comprobación más importante de este encargo. Recorre los párrafos nuevos y hazte, en cada
uno, esta pregunta:

> **¿Esto describe cómo es el sistema, o cuenta cómo llegó a serlo?**

Señales de que un párrafo se ha ido al Capítulo V:

- Empieza por «se detectó», «se observó», «se identificó».
- Menciona una ronda, una iteración, una versión previa del software.
- Da una cifra de cuántas veces fallaba algo.
- Usa «posteriormente», «más adelante», «en una segunda fase».

Señales de que está en su sitio:

- Enuncia una propiedad del sistema en presente.
- Da la razón de una decisión en términos de qué garantiza, no de qué problema apareció.
- Podría leerse antes de que el sistema existiera, como especificación.

**La única excepción autorizada** son los dos apagados de §4.2.5. Si encuentras cualquier otra
cronología, sobra.
