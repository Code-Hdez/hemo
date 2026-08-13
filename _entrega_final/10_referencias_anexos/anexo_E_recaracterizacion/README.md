# Anexo E — Evidencia de la campaña de recaracterización del runtime conversacional

> **Estructura del anexo, en tablas numeradas y figuras.** Sigue el patrón de los anexos B, C y D:
> presenta la evidencia que respalda una sección de resultados, sin repetir su análisis.
> Extensión estimada: 6–8 páginas.

---

## Criterio de presentación

Este anexo **no reproduce ficheros de datos**. Los artefactos crudos de la campaña —salidas JSON,
trazas, manifiestos— viven en el repositorio del proyecto y se citan por ruta y compendio
criptográfico. Lo que se imprime son **tablas numeradas y figuras**, que es lo que un anexo puede
ser leído, referenciado y verificado.

Los compendios se muestran **truncados a 16 caracteres**; el valor íntegro consta en el
repositorio. Una tabla con cadenas de 64 caracteres ocupa la página y no aporta.

---

## E.1 · Propósito y alcance

Un párrafo de apertura que explique qué contiene el anexo y a qué sección remite (§3.11 para la
metodología, §6.8 para el análisis). Sin datos.

## E.2 · Pre-registro de hipótesis

**Tabla E.1 — Las diez hipótesis pre-registradas.**
Enunciado, métrica, criterio de decisión y veredicto sellado.
📊 Ya disponible: `../../08_capitulo_vi_resultados/6.9_recaracterizacion_a100/tablas/tab_F1_tablero_hipotesis.csv`

**Figura E.1 — Tablero de hipótesis.**
📁 `fig_F1_tablero_hipotesis.pdf`

Texto de acompañamiento: el compendio del documento de pre-registro es `5d6a0a71081e385e…` y es
anterior a la primera medición. Explicar en dos frases por qué eso importa, y señalar la
discrepancia declarada en las tres filas cuyo veredicto sellado es «no evaluada» y cuya medición
ya existe.

## E.3 · Auditoría de la evidencia previa

**Tabla E.2 — Reconstrucción del protocolo anterior.**
Las quince preguntas de reproducibilidad con su estado: consta, parcial o no consta.
📊 `tab_A4_semaforo_protocolo.csv`

**Figura E.2 — Semáforo del protocolo.** 📁 `fig_A4_semaforo_protocolo.pdf`

**Figura E.3 — Composición del corpus de evidencia auditado**, n = 208.
📁 `fig_A2_corpus_evidencia.pdf`

Texto: 208 ficheros auditados, 208 compendios verificados intactos tras la copia. El directorio
con credenciales se contabilizó y resumió por compendio, **nunca se muestreó su contenido** — y
ese criterio se mantiene en este anexo.

**Tabla — Veredicto doble de comparabilidad.** 📊 `tab_A5_veredicto_doble.csv` (2 filas; puede ir
integrada en el texto por su brevedad).

## E.4 · Procedencia de los datos

**Tabla E.3 — Procedencia de los conjuntos de datos empleados en el análisis.**
Conjunto, ruta del artefacto, compendio SHA-256 truncado, bytes, registros y columnas. 13 filas.
📊 **Ya generada:** [`tablas/tabla_E.3_procedencia_fuentes.csv`](tablas/tabla_E.3_procedencia_fuentes.csv)
· [versión lista para pegar](tablas/tabla_E.3_procedencia_fuentes.md)

## E.5 · Manifiesto de figuras

**Tabla E.4 — Manifiesto de las figuras del análisis.**
Identificador, título, tamaño de muestra, condición (medida o derivada), procedencia y compendio.
45 filas — las 36 figuras y los 9 paneles de ausencia.
📊 **Ya generada:** [`tablas/tabla_E.4_manifiesto_figuras.csv`](tablas/tabla_E.4_manifiesto_figuras.csv)
· [versión lista para pegar](tablas/tabla_E.4_manifiesto_figuras.md)

> Es la tabla más larga del anexo. Si ocupa más de dos páginas, presentarla en cuerpo 10 pt y
> orientación apaisada, o dividirla por bloque temático (A, B, C, D, E, F).

## E.6 · Registro de verificación del análisis

**Tabla E.5 — Aserciones de recálculo.**
Once filas: aserción, valor recalculado desde los datos crudos, valor publicado, tolerancia y
resultado. **Diez coinciden y una falla.**
📄 Origen: `fuentes/VERIFICACION_NOTEBOOK.txt`

> 🔴 **La fila que falla se muestra, no se esconde.** Es la que acredita que la verificación es
> real: el número de preguntas verificables publicado fue de aproximadamente veinte y el fichero
> de verdad contiene nueve, lo que motiva la corrección de la cota de fabricación numérica del
> 16,8 % al 29,9 % consignada en §6.8.5. Probablemente sea el detalle que mejor distinga este
> anexo ante el comité.

**Tabla E.6 — Comprobaciones de diseño gráfico verificadas.**
Seis filas: ausencia de ejes dobles, ausencia de gráficos circulares, nota de lectura o
declaración de ausencia en toda figura, exportación en tres formatos, intervalo de confianza en
toda proporción representada, marca de corte en todo eje truncado.

## E.7 · Lo que no pudo medirse

**Tabla E.7 — Cobertura real de la rúbrica de evaluación.**
Los cinco ejes con su estado: puntuado, no puntuable o sin definición sellada.
📊 `tab_D8_rubrica_cobertura.csv`

**Tabla E.8 — Niveles del esquema de trazas efectivamente poblados.**
Cuatro filas: sesión y turno poblados; llamada y evento vacíos.
📊 `tab_F3_cobertura_esquema.csv`

Texto: la ausencia de dato es un resultado. Los campos de temporización interna que la interfaz no
expone hicieron no evaluable una de las hipótesis; los ejes invocados sin definición sellada no se
puntuaron. Seleccionar **dos o tres** de los nueve paneles de ausencia para ilustrarlo — no los
nueve, que sería redundante en un anexo.

## E.8 · Ablación de la decodificación restringida por gramática

**Tabla E.9 — Resultados por brazo.**
Tiempo por token, rango intercuartílico, tokens de salida y razón de terminación.
📊 `tab_C5_ablacion_brazos.csv`

**Figura E.4 — Lo predicho frente a lo medido.** 📁 `fig_C6_gramatica_predicho_medido.pdf`

Texto: sello del experimento, diseño (30 por brazo, intercalado, 5 descartes de calentamiento) y
**las tres limitaciones declaradas**, incluido el incumplimiento del propio protocolo por no haber
persistido los valores individuales, lo que impide calcular el intervalo de confianza.
📄 Origen: `../../08_capitulo_vi_resultados/6.9_recaracterizacion_a100/E-A_ablacion_gramatica.md`

## E.9 · Trazabilidad figura → fuente

**Tabla E.10 — Trazabilidad.**
Figura, título, fichero fuente, compendio, tamaño de muestra y marca. 58 filas.
📊 `../../08_capitulo_vi_resultados/6.9_recaracterizacion_a100/TRAZABILIDAD.csv`

> Solapa parcialmente con la Tabla E.4. **Elegir una de las dos** para el anexo impreso y remitir a
> la otra en el repositorio; publicar ambas es redundante. Recomendación: mantener la E.4
> (manifiesto, que incluye el tamaño de muestra y la condición) y dejar la trazabilidad como
> anexo digital en la copia en USB.

---

## Estado del material

| Elemento | Estado |
| :--- | :---: |
| Tabla E.1 (hipótesis) | ✅ generada |
| Tabla E.2 (protocolo) | ✅ generada |
| Tabla E.3 (procedencia) | ✅ **generada en `tablas/`** |
| Tabla E.4 (manifiesto de figuras) | ✅ **generada en `tablas/`** |
| Tabla E.5 (aserciones) | 🟡 maquetar desde `fuentes/VERIFICACION_NOTEBOOK.txt` |
| Tabla E.6 (comprobaciones gráficas) | 🟡 maquetar desde la misma fuente |
| Tablas E.7 y E.8 (ausencias) | ✅ generadas |
| Tabla E.9 (ablación) | ✅ generada |
| Figuras E.1 a E.4 | ✅ en PDF, SVG y PNG, con versión en gris |

Todo el material está en
[`../../08_capitulo_vi_resultados/6.9_recaracterizacion_a100/`](../../08_capitulo_vi_resultados/6.9_recaracterizacion_a100/):

```
6.9_recaracterizacion_a100/
├── 6.8_recaracterizacion_a100.md   ← redacción de la sección del Capítulo VI
├── PIES_DE_FIGURA.md               ← pies completos con sus notas de lectura
├── E-A_ablacion_gramatica.md       ← informe del experimento de ablación
├── TRAZABILIDAD.csv                ← tabla E.10
├── tablas/                         ← 25 tablas + índice, en CSV
├── figuras/                        ← 12 figuras × (PDF + SVG + PNG)
│   └── grises/                     ← para verificar el empastado antes de imprimir
└── fuentes/                        ← ❌ NO se imprime: JSON y registros de verificación
```

---

## Cómo redactarlo

- **Cada apartado necesita un párrafo introductorio.** Un anexo que es solo tablas encadenadas no
  se lee. Los anexos B, C y D ya lo hacen bien; seguir su registro.
- **Las notas de lectura viajan con las figuras.** Son parte del resultado, no adorno: son lo que
  impide que un revisor concluya «la GPU arregló los fallos» a partir de la Figura del acuerdo de
  identificadores, o «el sistema no fabrica datos» a partir del cero de alucinación.
- **No incluir código ni ficheros de configuración.** Van al repositorio de control de versiones,
  que es lo que el manual pide en su Anexo II.
- **Verificar privacidad antes de anexar cualquier traza.** El *fixture* de la campaña es de
  prueba, pero eso hay que comprobarlo fichero por fichero, no suponerlo.
