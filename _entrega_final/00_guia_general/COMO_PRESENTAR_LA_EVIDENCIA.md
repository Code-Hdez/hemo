# Cómo se presenta la evidencia en un proyecto de grado

> Corrección de criterio aplicada el 12/08/2026. La versión inicial de esta carpeta colocaba
> ficheros JSON dentro de carpetas llamadas `evidencia/`, lo que inducía a pensar que ese material
> iba al documento. **No va.** Este archivo fija la regla y la estructura resultante.

---

## La regla

Un informe de proyecto de grado es un documento **impreso, empastado, paginado y defendido ante
un comité**. Todo lo que entra en él tiene que poder:

1. **Numerarse** — «Tabla 6.14», «Figura 6.33».
2. **Listarse** — aparecer en la Lista de Tablas o la Lista de Figuras con su página.
3. **Referenciarse desde el cuerpo** — «como muestra la Tabla 6.14…».
4. **Leerse en papel, en blanco y negro, sin ampliar.**

Un JSON no cumple ninguna de las cuatro. Un volcado de estructuras anidadas con compendios de 64
caracteres no es evidencia presentable: es el **origen** de la evidencia.

| Formato | ¿Va al documento? | Uso |
| :--- | :---: | :--- |
| **Tabla numerada** | ✅ | La forma por defecto de presentar datos. Se lista, se numera, se referencia |
| **Figura vectorial** (PDF/SVG) | ✅ | Gráficas y diagramas. No pixela en el empastado |
| **Captura de pantalla** | ✅ | El producto funcionando. Rotulada y con pie |
| **Diagrama** (casos de uso, componentes, despliegue, secuencia) | ✅ | Lo pide el manual explícitamente para ICC |
| **CSV** | ⚠️ | Solo como **anexo digital** en la copia en USB, nunca impreso |
| **JSON / JSONL / esquemas** | ❌ | Fuente de verificación. Se **cita por ruta y compendio**, no se reproduce |
| **Código fuente** | ❌ | Va al repositorio de control de versiones (Anexo II del manual) |

### Cómo se cita una fuente sin reproducirla

En lugar de pegar el JSON, el documento dice:

> «Las cifras de esta sección proceden del reporte de vigilancia poblacional generado el 12 de
> abril de 2026 sobre una cohorte de 200 registros, cuyo artefacto y compendio criptográfico
> constan en el Anexo E.»

Y el Anexo E lleva **una tabla** de procedencia con ruta, compendio truncado a 16 caracteres,
tamaño y número de registros. Eso es trazable, verificable y legible. Un JSON pegado no es
ninguna de las tres cosas.

---

## Estructura resultante de esta carpeta

Cada bloque que tiene material sigue la misma convención:

```
<capítulo>/
├── README.md      ← qué cambiar, con el texto de reemplazo
├── tablas/        ← ✅ VA AL DOCUMENTO. CSV + versión Markdown lista para pegar
├── figuras/       ← ✅ VA AL DOCUMENTO. PDF + SVG + PNG, y versión en gris para revisar
└── fuentes/       ← ❌ NO VA AL DOCUMENTO. JSON y artefactos crudos, para verificar
```

### Lo que se convirtió

| Antes (JSON en `evidencia/`) | Ahora (tabla en `tablas/`) |
| :--- | :--- |
| `fase2_canario_y_ic.json` | **Tabla 3.12** — Configuración sellada de medición |
| `population_surveillance_report_v3.json` | **Tabla 6.14** — Compuertas técnicas · **Tabla 6.15** — Señales del reporte |
| `gate_geocoding_quality_v1.json` | **Tabla 6.16** — Comprobaciones de calidad de geocodificación |
| `gpu-runtime-<versión>.json` | **Tabla 5.10** — Contrato de *runtime* del nodo de inferencia |
| `PROCEDENCIA.json` | **Tabla E.3** — Procedencia de los conjuntos de datos (13 filas) |
| `MANIFIESTO.json` | **Tabla E.4** — Manifiesto de las figuras del análisis (45 filas) |

Cada una viene en dos formatos: `.csv` (delimitado por `;`, para importar) y `.md` (tabla ya
maquetada, para copiar y pegar en el `.docx`).

---

## Convenciones de presentación que hay que respetar

### Compendios criptográficos

**Truncar a 16 caracteres seguidos de puntos suspensivos.** Una tabla con hashes de 64 caracteres
es ilegible y ocupa la página entera sin aportar. El valor íntegro consta en el repositorio, y eso
se dice en una nota al pie de la tabla. Ya está aplicado en las tablas generadas.

### Números

- **Coma decimal**, no punto: `24,48 ms`, no `24.48 ms`. El documento está en español y hoy mezcla
  ambas convenciones — hay que unificarlo en toda la tesis, no solo en las tablas nuevas.
- **Espacio como separador de millares**: `17 420 432 739`, no `17,420,432,739`.
- **Porcentajes con espacio antes del signo**: `34,90 %`.
- Las unidades no se traducen: `ms`, `tok/s`, `GB/s`.

### Tablas

- Título **debajo** de la tabla, en cursiva, numerado: *Tabla 6.14. Compuertas técnicas…*
- Sin capturas de pantalla de tablas. El manual lo dice explícitamente para el presupuesto («NO
  agregue imágenes en la tabla») y el criterio vale para todas: una tabla se maqueta, no se
  fotografía.
- Si una tabla no cabe en una página, va al anexo y en el cuerpo queda un resumen.

### Figuras

- Título **debajo**, en cursiva, numerado.
- **Insertar el PDF o el SVG**, nunca el PNG: el empastado es impreso y el PNG pixela.
- **Revisar en escala de grises antes de imprimir.** Las versiones grises están en
  `figuras/grises/`.
- Ninguna figura debe depender solo del color para distinguir series: hace falta codificación
  secundaria por marcador o trama.
- Las **notas de lectura** de las figuras de la campaña no son opcionales — son las que impiden
  que un revisor concluya «la GPU arregló los fallos» o «el sistema no fabrica datos». Si no caben
  bajo la figura, van como nota al pie de página.

---

## El hueco grande: no hay imágenes del producto

Ver [`CATALOGO_DE_FIGURAS_E_IMAGENES.md`](CATALOGO_DE_FIGURAS_E_IMAGENES.md).

Resumen: la tesis tiene 47 figuras y **ninguna muestra la plataforma funcionando**. §5.4, que
describe el desarrollo del frontend, no tiene una sola imagen. Para un proyecto de grado cuyo
producto es una aplicación web, es el vacío más visible del documento — y el manual EICT lo pide
de forma explícita.
