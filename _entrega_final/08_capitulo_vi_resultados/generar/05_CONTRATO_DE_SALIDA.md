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
# Capítulo VI — Análisis de los resultados

[entradilla]

## 6.1. Resultados del motor de clasificación hematológica
[texto íntegro, sin cambios]

| col | col |
| :--- | :--- |
| … | … |

*Tabla 6.1. Resumen del estado final del sistema HemoVet.*

[FIGURA image20]

*Figura 6.1. Curvas ROC y Precision-Recall del modelo HemoVet v4 en el conjunto de prueba.*

### 6.1.1. Métricas finales por etiqueta
…
````

- Encabezados con `#`, `##` y `###`.
- Tablas en Markdown estándar con barras. Word las convierte a tabla real al pegar con formato.
- Títulos de tabla y pies de figura en cursiva, **debajo** del elemento.
- Las figuras existentes se mantienen como `[FIGURA imageNN]`, en su sitio, con el mismo número.
- Las figuras nuevas de §6.8 se mantienen con el marcador que traen:
  `*[Figura 6.30 — fig_A2_corpus_evidencia: …]*`.

## Después del capítulo, cuatro bloques obligatorios

### Bloque A — Registro de cambios

Tabla con **todos** los cambios que hiciste respecto del texto original:

| Sección | Tipo | Qué cambió | Por qué |
| :--- | :--- | :--- | :--- |
| 6.4.2 | Corrección | Fila de latencia de la Tabla 6.10 fechada + nota al pie | La cifra es de una configuración que ya no está vigente |
| 6.4.2 | Traslado | Frase «hallazgo que se entrega al equipo de desarrollo» eliminada | El manual prohíbe sugerencias en resultados; va a §7.5 |
| 6.4.5 | Ampliación | Intervalos de Wilson en las filas de alucinación y seguridad | Un cero sin intervalo no es un resultado |
| 6.6 | Sección nueva | Resultados de la vigilancia poblacional | Cubre el hueco de numeración y respalda OE4 |
| 6.8 | Sección nueva | Recaracterización del *runtime* sobre A100 | … |
| 6.9 | Renumeración | Síntesis 6.8 → 6.9 | La síntesis debe cerrar el capítulo |
| 6.7.1 | Renumeración | Tabla de usabilidad 6.14 → 6.16 | §6.6 ocupa 6.14 y 6.15 |
| … | | | |

Tipos válidos: `Corrección` · `Ampliación` · `Sección nueva` · `Renumeración` · `Estilo` ·
`Traslado` · `Eliminación`.

### Bloque B — Marcadores pendientes

Lista de **todo** lo que dejaste sin resolver, con su ubicación exacta:

- `[PENDIENTE: …]` — qué falta y quién puede aportarlo.
- `[CITA PENDIENTE: …]` — si añadiste alguna.

**Este bloque no puede estar vacío**: hay al menos un dato pendiente por diseño (la salida de la
suite de pruebas del backend, en §6.5). Si te sale vacío, es que inventaste un número.

### Bloque C — Tablas y figuras, inventario final

Dos listas para actualizar los índices del documento:

- **Tablas 6.1 a 6.23** con su título final, marcando cuáles cambiaron de número.
- **Figuras 6.1 a 6.41** con su pie final, marcando cuáles son nuevas.

### Bloque D — Inconsistencias detectadas

Si encuentras una contradicción entre los archivos de este paquete, o un hecho que necesitas y no
está, **no la resuelvas inventando**: escríbela aquí con la ubicación exacta y las dos versiones
en conflicto.

Ya hay **una conocida** que debes reproducir en este bloque: la numeración de tablas que propone
`01_preliminares/README.md` (6.14 · 6.15 · 6.16–6.20) es incorrecta y la válida es la de este
paquete (6.14 · 6.15 · 6.16 · 6.17–6.23). Ver `02_HECHOS_VERIFICADOS.md` §11.

---

## Checklist de verificación — recórrelo antes de entregar

### Contenido

- [ ] Están las **nueve** secciones, numeradas 6.1 a 6.9, y la síntesis es la **6.9**.
- [ ] §6.6 está entre §6.5 y §6.7, y §6.8 entre §6.7 y la síntesis.
- [ ] Las secciones íntegras (§6.1, §6.2, §6.3, §6.4.4, §6.7) están **reproducidas completas**, no
      resumidas ni omitidas ni «mejoradas».
- [ ] Las dos secciones nuevas conservan **todas** sus declaraciones de limitación.
- [ ] La extensión total está entre 10 000 y 11 500 palabras.

### Cifras

- [ ] `25 passed` / `25 pruebas` **no aparece**; en su lugar hay un marcador de pendiente.
- [ ] La latencia de 24,1 s aparece **fechada** y con su nota al pie, no borrada.
- [ ] Las proporciones observadas en cero llevan su intervalo de Wilson (11,4 % y 29,9 %).
- [ ] La cota de alucinación de la campaña es **29,9 %**, nunca 16,8 %.
- [ ] La línea base de latencia es **54,4 s**, nunca 59,1 s.
- [ ] No aparece «Qwen3 4B» ni ninguna referencia a que el modelo corra sobre CPU.
- [ ] Toda cifra que escribiste está en `02` o en `04`. Ninguna es estimada.

### Altitud — la Regla 1

- [ ] No aparecen «se recomienda», «conviene», «debería», «se sugiere», «se entrega al equipo».
- [ ] No aparece «se concluye que» ni «demuestra que la migración fue exitosa».
- [ ] No hay ninguna propuesta de trabajo futuro.

### Comparabilidad — la Regla 3

- [ ] Ninguna cifra de decodificación, MBU o TPOT se presenta como comparación entre unidades de
      procesamiento gráfico.
- [ ] La mejora de latencia se atribuye **al conjunto de la migración**, no aisladamente al
      hardware.
- [ ] Está escrito que la configuración anterior no es reproducible (11 de 15 preguntas sin
      constancia).
- [ ] La bajada de fallos **no** se presenta como corrección de los fallos anteriores: se declara
      κ = −0,145 y 0 de 17 identificadores coincidentes.

### Numeración

- [ ] Tablas 6.1–6.13 sin cambios · 6.14 y 6.15 de §6.6 · **usabilidad renumerada a 6.16** ·
      6.17–6.23 de §6.8.
- [ ] La referencia a la tabla de usabilidad dentro de §6.7.1 se actualizó al número nuevo.
- [ ] Figuras 6.1–6.29 sin cambios · 6.30–6.41 de §6.8.
- [ ] Toda tabla y toda figura está referenciada desde el texto antes de aparecer.

### Estilo

- [ ] Coma decimal en todos los números; espacio como separador de millares. En particular,
      `1 301` y `0,9529`, no `1,301` ni `0.9529`.
- [ ] Sin adjetivos de mérito.
- [ ] Términos traducidos según `03_ESTILO_Y_FORMATO.md`; los que quedan en inglés, en cursiva.
- [ ] Sin código, rutas de fichero, nombres de *commit*, ni nombres de variables.

### Honestidad

- [ ] El tablero de hipótesis se presenta **tal como está sellado**, con la discrepancia de las
      tres filas «NO EVALUADA» señalada en el texto y no corregida.
- [ ] La aserción de verificación que falla está declarada.
- [ ] Los dos turnos «muertos» de la batería aparecen; no se recortaron.
- [ ] El modelo anterior que sigue instalado en el nodo está declarado.
- [ ] El límite de potencia del diseño (431 frente a 9–70) está escrito.

---

## Qué hacer si algo no encaja

Es más útil un capítulo con tres marcadores honestos que uno completo con tres cifras inventadas.
Lo primero se cierra en diez minutos; lo segundo puede costar la defensa.
