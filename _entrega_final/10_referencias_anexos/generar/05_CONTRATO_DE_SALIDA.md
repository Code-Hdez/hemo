# Contrato de salida — qué tienes que devolver exactamente

---

## Formato

**Un único documento en Markdown**, continuo, listo para copiar y pegar en Microsoft Word. No
devuelvas parches ni listas de instrucciones: devuelve **el bloque entero**, desde el título de
las referencias hasta el último apartado del Anexo E, con todo lo que no cambia **reproducido
literal**.

Motivo: quien recibe esto va a seleccionar todo, copiar y pegar sobre el documento actual. Y en
este bloque hay un riesgo adicional: la bibliografía tiene decenas de entradas numeradas, y basta
perder una o alterar un número para romper todas las citas del cuerpo.

### Cómo estructurarlo

````
# Referencias Bibliográficas

[1] Entrada literal, con su número actual.
[2] …

## Referencias pendientes de incorporar
[REF-NUEVA-1] `[CITA PENDIENTE: …]`
…

# Anexo A. Matriz de riesgos actualizada del proyecto
[contenido literal + R-14 y R-15]

# Anexo E. Evidencia de la campaña de recaracterización del runtime conversacional

## E.1. Propósito y alcance
[párrafo]

## E.2. Pre-registro de hipótesis
[párrafo]

| # | Enunciado | Métrica | Criterio | Veredicto sellado |
| :--- | :--- | :--- | :--- | :--- |
| … | | | | |

*Tabla E.1. Las diez hipótesis pre-registradas de la campaña de recaracterización.*

[FIGURA E.1 — fig_F1_tablero_hipotesis]

*Figura E.1. Tablero de las diez hipótesis pre-registradas.*
````

- Los títulos de anexo son encabezados de **nivel 1**; los apartados E.1 a E.9, de **nivel 2**.
- Tablas en Markdown estándar con barras.
- Títulos de tabla y pies de figura **debajo** del elemento, en cursiva.
- Compendios **truncados a 16 caracteres** seguidos de `…`.

## Después del bloque, cuatro bloques obligatorios

### Bloque A — Registro de cambios

| Sección | Tipo | Qué cambió | Por qué |
| :--- | :--- | :--- | :--- |
| Referencias | Ampliación | Ocho entradas nuevas señaladas como pendientes | Las secciones nuevas de los capítulos I, III y VI las necesitan |
| Anexo A | Ampliación | Riesgos R-14 y R-15 | La matriz no cubría la instancia interrumpible ni la deriva de modelo |
| Anexo C | Ampliación | Apartado de la batería de contenido sustantivo | Faltaba el instrumento de aceptación del proyecto |
| Anexo E | Anexo nuevo | Evidencia de la campaña de recaracterización, nueve apartados | §6.8 sería el único resultado del proyecto sin anexo |
| … | | | |

Tipos válidos: `Corrección` · `Ampliación` · `Anexo nuevo` · `Estilo`.

### Bloque B — Referencias, estado de cada una 🔴

**El bloque más importante de tu salida.** Una tabla con las ocho:

| Marcador | Qué se necesita citar | Estado |
| :--- | :--- | :--- |
| `[REF-NUEVA-1]` | Análisis *roofline* aplicado a inferencia de transformadores | `[CITA PENDIENTE]` |
| `[REF-NUEVA-2]` | 🔴 La fuente que publica el sobrecosto de la decodificación por gramática | `[CITA PENDIENTE]` |
| … | | |

Si una referencia la tienes **verificada**, escríbela completa en formato IEEE y márcala como
verificada. Si no, déjala pendiente con una descripción **precisa** de qué hay que buscar: tipo de
publicación, y el dato concreto que debe aportar.

**Declara además** el resultado de las dos comprobaciones de reutilización:

- ¿Wilcoxon ya está citado a propósito de la validación clínica? Si sí, se reutiliza la entrada.
- ¿La referencia de Cohen para el coeficiente kappa cubre el uso para acuerdo entre corridas?

### Bloque C — Marcadores de tabla y figura pendientes

Lista de todos los marcadores que dejaste:

- `[TABLA E.3 — …]`, `[TABLA E.4 — …]`, `[TABLA E.10 — …]` si la conservas.
- `[FIGURA E.1 — …]` a `[FIGURA E.4 — …]`, más los dos o tres paneles de ausencia que elegiste.

Y **declara qué decidiste sobre la redundancia entre E.4 y E.10**.

### Bloque D — Inconsistencias detectadas

Si encuentras una contradicción entre los archivos de este paquete, o un hecho que necesitas y no
está: **no la resuelvas inventando**. Escríbela aquí con la ubicación exacta y las dos versiones
en conflicto.

---

## Checklist de verificación — recórrelo antes de entregar

### Referencias — la Regla 1

- [ ] **Ninguna referencia inventada. Ni una.**
- [ ] Todas las entradas actuales están **reproducidas literales, con sus números actuales**.
- [ ] **Ninguna entrada existente cambió de número.**
- [ ] Las ocho entradas nuevas van como `[REF-NUEVA-n]` en un apartado aparte, **no mezcladas** con
      la lista numerada.
- [ ] Cada marcador pendiente describe con precisión qué hay que buscar.
- [ ] No hay ninguna fuente de Wikipedia, blog sin autoría o foro.
- [ ] Se declaró si Wilcoxon y Cohen ya están citados en el documento.

### Anexos existentes

- [ ] Anexo A conserva **todas** sus filas actuales, más R-14 y R-15.
- [ ] R-14 y R-15 usan el **mismo formato** que las filas existentes.
- [ ] Anexo B está **íntegro y sin cambios**.
- [ ] Anexo C conserva todo su contenido actual, más el apartado nuevo.
- [ ] El apartado nuevo de C incluye la **declaración de verificación de privacidad**.
- [ ] Anexo D está **íntegro y sin cambios**.

### Anexo E

- [ ] Tiene los **nueve** apartados, de E.1 a E.9.
- [ ] **Cada apartado tiene su párrafo introductorio.** Ninguno es solo tablas.
- [ ] Las tablas E.3, E.4 y E.10 van como **marcadores**, con su párrafo introductorio escrito.
- [ ] Las figuras van como marcadores con su pie.
- [ ] Los compendios están **truncados a 16 caracteres**.
- [ ] Se declaró la decisión sobre la redundancia entre E.4 y E.10.

### Honestidad — la Regla 3

- [ ] El tablero de hipótesis se presenta **tal como está sellado**, y la discrepancia de las tres
      filas «no evaluada» está **señalada en el texto, no corregida en la tabla**.
- [ ] La aserción de verificación que **falla** está en la Tabla E.5, con su motivo y la corrección
      que produjo (16,8 % → 29,9 %).
- [ ] E.7 documenta lo que no pudo medirse, con sus dos tablas.
- [ ] Las **tres** limitaciones de la ablación están declaradas, incluida la de los valores crudos
      no persistidos.
- [ ] Está declarado que el directorio con credenciales se contabilizó pero **nunca se muestreó**.

### Altitud — la Regla 2

- [ ] Ningún apartado analiza ni interpreta los resultados: eso es §6.8.
- [ ] No aparecen «demuestra que», «lo que confirma», «se concluye».
- [ ] Ninguna recomendación.

### Estilo y contenido prohibido

- [ ] Sin código, ficheros de configuración ni volcados JSON.
- [ ] Sin datos personales de mascota, propietario ni clínica.
- [ ] Coma decimal en todos los números; espacio como separador de millares.
- [ ] Sin adjetivos de mérito.
- [ ] La extensión total está entre 7 500 y 8 600 palabras.

---

## Qué hacer si algo no encaja

Es más útil un bloque con ocho marcadores de cita honestos que uno completo con una referencia
inventada. Lo primero se cierra con una tarde en la biblioteca; lo segundo es el único error de
este documento que alguien puede verificar desde su asiento, mientras hablas.
