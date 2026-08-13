# Guion del Anexo E — apartado por apartado

> Esto **no es texto para copiar**: es la arquitectura del anexo nuevo. Los datos están en
> `02_HECHOS_VERIFICADOS.md` §5; aquí se dice qué lleva cada apartado, en qué orden y con qué
> registro.
>
> Extensión objetivo del Anexo E: **6 a 8 páginas contando sus tablas**, que en prosa son unas
> **2 000 palabras**. Varias tablas son largas y no se transcriben: van como marcadores.

---

## Criterio general del anexo

**Este anexo no reproduce ficheros de datos.** Los artefactos crudos —salidas JSON, trazas,
manifiestos— viven en el repositorio del proyecto y se citan por descripción y compendio
criptográfico. Lo que se imprime son **tablas numeradas y figuras**, que es lo que un anexo puede
ser: leído, referenciado y verificado.

**Los compendios se muestran truncados a 16 caracteres** seguidos de `…`; el valor íntegro consta
en el repositorio. Una tabla con cadenas de 64 caracteres ocupa la página y no aporta nada.

**Cada apartado necesita su párrafo introductorio.** Un anexo que es solo tablas encadenadas no se
lee. Los anexos B, C y D del documento ya lo hacen bien: sigue su registro.

---

## E.1 · Propósito y alcance

**Un párrafo. Sin datos.**

Qué contiene el anexo y a qué secciones remite: **§3.11 para la metodología** con que se obtuvo
esta evidencia, **§6.8 para su análisis**. Y el criterio de presentación: tablas y figuras, no
ficheros; compendios truncados.

Una frase que conviene incluir: este anexo **también documenta lo que no pudo medirse**, porque esa
ausencia forma parte del resultado.

---

## E.2 · Pre-registro de hipótesis

**Un párrafo, una tabla y una figura.**

**Tabla E.1 — Las diez hipótesis pre-registradas.** Enunciado, métrica, criterio de decisión y
veredicto sellado. Los datos están en `02` §5.

**Figura E.1 — Tablero de hipótesis.** Deja el marcador
`[FIGURA E.1 — fig_F1_tablero_hipotesis]` con su pie.

**El párrafo de acompañamiento** dice dos cosas, en dos frases:

1. El compendio del documento de pre-registro es `5d6a0a71081e385e…` y **es anterior a la primera
   medición**. Por qué importa: un criterio de decisión escrito después de ver los datos no es un
   criterio, es una descripción.
2. **La discrepancia declarada.** Tres filas tienen veredicto sellado «no evaluada» y una medición
   que ya existe: la tabla se escribió antes de correr el brazo de réplica estricta y no se
   actualizó.

> 🔴 **El tablero se presenta tal como está sellado.** No corrijas los tres veredictos por los
> recalculados. Señala la discrepancia en el texto y deja la tabla intacta. Retocar un pre-registro
> después de medir lo invalida, y el comité lo sabe.

---

## E.3 · Auditoría de la evidencia previa

**Un párrafo, dos tablas y dos figuras.**

**Tabla E.2 — Reconstrucción del protocolo anterior:** las quince preguntas de reproducibilidad con
su estado (consta, parcial, no consta).

**Figura E.2 — Semáforo del protocolo.** Marcador `[FIGURA E.2 — fig_A4_semaforo_protocolo]`.

**Figura E.3 — Composición del corpus de evidencia auditado**, n = 208. Marcador
`[FIGURA E.3 — fig_A2_corpus_evidencia]`.

**Tabla del veredicto doble de comparabilidad:** dos filas. Por su brevedad puede ir integrada en
el texto en lugar de como tabla numerada. Elige y sé coherente.

**El párrafo** dice: 208 ficheros auditados, 208 compendios verificados intactos tras la copia, y
el criterio de tratamiento —**el directorio con credenciales se contabilizó y resumió por
compendio, nunca se muestreó su contenido**, y ese criterio se mantiene en el anexo—.

Esa última frase importa más de lo que parece: declara que la auditoría respetó un límite que no
tenía por qué respetar, y es el tipo de detalle que da credibilidad al resto.

---

## E.4 · Procedencia de los datos

**Un párrafo y un marcador.**

**Tabla E.3 — Procedencia de los conjuntos de datos empleados en el análisis.** Trece filas:
conjunto, ruta del artefacto, compendio truncado, bytes, registros y columnas.

**Ya está generada. No la transcribas.** Deja:

```
[TABLA E.3 — insertar desde tabla_E.3_procedencia_fuentes.md]
```

**El párrafo introductorio sí lo escribes**, y dice qué contiene la tabla y qué columnas tiene. Un
marcador sin introducción no le dice nada a quien maquete.

---

## E.5 · Manifiesto de figuras

**Un párrafo y un marcador.**

**Tabla E.4 — Manifiesto de las figuras del análisis.** Cuarenta y cinco filas —las 36 figuras y
los 9 paneles de ausencia—: identificador, título, tamaño de muestra, condición (medida o
derivada), procedencia y compendio.

```
[TABLA E.4 — insertar desde tabla_E.4_manifiesto_figuras.md]
```

**Nota de maquetación que conviene dejar escrita:** es la tabla más larga del anexo. Si ocupa más
de dos páginas, presentarla en cuerpo 10 pt y orientación apaisada, o dividirla por bloque
temático.

---

## E.6 · Registro de verificación del análisis

**Un párrafo y dos tablas. Es el apartado más importante del anexo.**

**Tabla E.5 — Aserciones de recálculo.** Once filas: aserción, valor recalculado desde los datos
crudos, valor publicado, tolerancia y resultado. **Diez coinciden y una no.**

**Tabla E.6 — Comprobaciones de diseño gráfico verificadas.** Seis filas, enumeradas en `02` §5.

**El párrafo** explica qué es una aserción de recálculo: una comprobación que vuelve a calcular,
desde los datos crudos, una cifra ya publicada, y falla si no coinciden dentro de la tolerancia.

**Y declara la que falla, con su motivo:** el número de preguntas verificables publicado era de
unas veinte y el fichero de verdad contiene nueve, lo que motivó corregir la cota de fabricación
numérica del 16,8 % al 29,9 %.

> 🔴 **La fila que falla se muestra, no se esconde.** Es lo que acredita que la verificación es
> real. Probablemente sea el detalle que mejor distinga este anexo ante el comité: un anexo que
> solo publica las comprobaciones que pasan no se distingue de uno que no comprobó nada.
>
> **No la acompañes de justificaciones.** Se declara el hecho, su motivo y la corrección que
> produjo. Ahí termina.

---

## E.7 · Lo que no pudo medirse

**Un párrafo y dos tablas.**

**Tabla E.7 — Cobertura real de la rúbrica de evaluación.** Los cinco ejes con su estado: puntuado,
no puntuable, o sin definición sellada.

**Tabla E.8 — Niveles del esquema de trazas efectivamente poblados.** Cuatro filas: sesión y turno
poblados; llamada y evento vacíos.

**El párrafo** sostiene la idea del apartado: **la ausencia de dato es un resultado.** Los campos
de temporización interna que la interfaz no expone hicieron no evaluable una de las diez hipótesis;
los ejes invocados sin definición sellada no se puntuaron.

**Selecciona dos o tres de los nueve paneles de ausencia** para ilustrarlo, con sus marcadores de
figura. Los nueve serían redundantes en un anexo.

> Este apartado es inusual: casi ningún trabajo dedica una sección a documentar lo que no consiguió
> medir. Precisamente por eso conviene que su párrafo diga **por qué está ahí**, en una frase: un
> inventario de ausencias permite que otro equipo sepa qué instrumentar antes de repetir la
> medición.

---

## E.8 · Ablación de la decodificación restringida por gramática

**Un párrafo, una tabla y una figura.**

**Tabla E.9 — Resultados por brazo:** tiempo por token, rango intercuartílico, tokens de salida y
razón de terminación.

**Figura E.4 — Lo predicho frente a lo medido.** Marcador
`[FIGURA E.4 — fig_C6_gramatica_predicho_medido]`.

**El párrafo** lleva el sello del experimento, el diseño (30 por brazo, intercalado, 5 descartes de
calentamiento) y **las tres limitaciones declaradas** —incluido el incumplimiento del propio
protocolo por no haber persistido los valores individuales, lo que impide calcular el intervalo de
confianza—.

> La tercera limitación es incómoda de escribir y es la que más crédito da. Un protocolo que
> declara dónde se incumplió a sí mismo es más creíble que uno que nunca falla.

---

## E.9 · Trazabilidad figura → fuente

**Un párrafo corto y una decisión.**

**Tabla E.10 — Trazabilidad:** figura, título, fichero fuente, compendio, tamaño de muestra y
marca. Cincuenta y ocho filas.

> ⚠️ **Solapa parcialmente con la Tabla E.4.** Publicar ambas es redundante.
>
> **Recomendación: mantener E.4** —el manifiesto, que incluye tamaño de muestra y condición— y
> dejar la trazabilidad como anexo digital en la copia entregada en soporte físico.
>
> **Escribe esa decisión en el texto**, no la resuelvas en silencio. Un párrafo que dice «esta
> correspondencia completa se entrega en el anexo digital, del que la Tabla E.4 es un resumen»
> resuelve la redundancia y explica dónde está lo que no se imprime.

Si decides imprimirla, el marcador es
`[TABLA E.10 — insertar desde TRAZABILIDAD.csv]`.

---

## Las dos ampliaciones fuera del Anexo E

### Anexo A · Dos filas de riesgo

Contenido en `02` §3. **Adapta el formato al que ya use la matriz**: si son filas de tabla, filas;
si son fichas, fichas. No introduzcas un formato nuevo para dos entradas.

R-14 es un riesgo **vivo** —la instancia puede ser reclamada en cualquier momento— y R-15 es un
riesgo **latente** con probabilidad baja e impacto alto. Que la matriz refleje esa diferencia en
sus columnas de probabilidad e impacto.

### Anexo C · La batería de contenido sustantivo

Un apartado nuevo dentro del anexo existente, con:

1. **Una o dos frases sobre su aporte ortogonal**: las baterías A–E miden si la respuesta es segura,
   robusta y consistente, pero una respuesta que solo deriva al veterinario pasa todas esas pruebas
   de forma vacua.
2. **La tabla de evolución medida**, en `02` §4.
3. **La frase de verificación de privacidad**, que se escribe como declaración del anexo y no solo
   como tarea pendiente: se comprobó que los ficheros anexados no contienen identificadores de
   mascota, propietario ni clínica.

---

## Las referencias

**No se redactan aquí: se marcan.**

Reproduce la lista actual **íntegra y con sus números**. Al final, en un apartado señalado
—«Referencias pendientes de incorporar» o equivalente—, lista los ocho marcadores
`[REF-NUEVA-n]` con la descripción precisa de qué hay que buscar.

**No las mezcles con la lista numerada existente.** La integración y la renumeración se hacen en
Word con referencias cruzadas, al final, cuando todas las secciones nuevas del documento estén
insertadas.

> 🔴 Y la regla que gobierna todo este bloque: **si no tienes una referencia verificada, no la
> escribas.** Ni con el año aproximado, ni con el título parafraseado, ni «a falta de la cita
> exacta». Un marcador honesto se resuelve con una tarde de búsqueda.
