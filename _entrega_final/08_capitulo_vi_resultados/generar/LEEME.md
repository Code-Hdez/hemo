# generar/ — paquete autocontenido para reescribir el Capítulo VI

Todo lo necesario para que un LLM produzca el **Capítulo VI completo**, corregido y con las dos
secciones nuevas integradas, y te lo devuelva listo para pegar en Word. **No requiere acceso al
repositorio:** los datos están dentro.

> **Este es el capítulo que hay que hacer primero.** Aquí viven las cifras que los demás capítulos
> resumen: el VII las concluye, el I las fundamenta, el III describe cómo se obtuvieron y los
> preliminares las anuncian. Si cambias una cifra aquí después de haber cerrado los otros, tienes
> que volver a pasar por todos.

---

## Cómo se usa

1. Abre una conversación nueva con un LLM capaz (ventana de contexto amplia).
2. Pega los archivos **en este orden**, cada uno precedido por su nombre en una línea:

```
00_PROMPT_MAESTRO.md            ← quién eres, qué produces, las tres reglas
01_TEXTO_ACTUAL.md              ← el Capítulo VI íntegro tal como está hoy
02_HECHOS_VERIFICADOS.md        ← todas las cifras, con marca y advertencias
03_ESTILO_Y_FORMATO.md          ← registro, terminología, números, tablas
04_SECCIONES_YA_REDACTADAS.md   ← §6.6 y §6.8, escritas y verificadas
05_CONTRATO_DE_SALIDA.md        ← qué devolver y checklist de verificación
```

3. Cierra con: **«Produce ahora el Capítulo VI completo según el contrato de salida.»**

Son ~17 000 palabras de entrada. Entra en una sola petición en cualquier modelo con ventana
moderna.

### Si el modelo trunca la respuesta

La salida esperada son **10 000–11 500 palabras**, y algunos modelos cortan antes. Si pasa,
pídelo en dos partes sobre la misma conversación:

1. «Produce §6.1 a §6.5, completas y sin resumir.»
2. «Continúa con §6.6 a §6.9, más los cuatro bloques del contrato de salida.»

No vuelvas a pegar el material: ya está en el contexto.

## Qué te devuelve

Un documento continuo en Markdown —el capítulo entero, no parches— más cuatro bloques: registro de
cambios, marcadores pendientes, inventario de tablas y figuras, e inconsistencias detectadas.

**Para pasarlo a Word:** copia el Markdown, pégalo en un editor que lo renderice (el visor de
Markdown de VS Code, Typora, o cualquier conversor en línea), copia lo renderizado y pégalo en el
`.docx` **con formato**. Las tablas llegan como tablas reales. Después aplica el
`CHECKLIST_FORMATO.md` de la guía general: tipografía, interlineado 1,5 y estilos de título.

---

## Qué contiene el paquete

| Archivo | Palabras aprox. | Contenido |
| :--- | ---: | :--- |
| `00_PROMPT_MAESTRO.md` | 1 200 | El encargo, el contexto del proyecto y las tres reglas que lo gobiernan |
| `01_TEXTO_ACTUAL.md` | 5 600 | El Capítulo VI verbatim del `.docx (4)`, con sus errores intactos |
| `02_HECHOS_VERIFICADOS.md` | 3 000 | Las cinco correcciones, el dato pendiente, y todas las cifras de la campaña con su marca |
| `03_ESTILO_Y_FORMATO.md` | 950 | Registro, traducción de anglicismos, convenciones numéricas, qué no debe aparecer |
| `04_SECCIONES_YA_REDACTADAS.md` | 5 100 | §6.6 y §6.8 completas, verificadas y listas para integrar |
| `05_CONTRATO_DE_SALIDA.md` | 1 200 | Formato de entrega, cuatro bloques obligatorios y checklist de 38 puntos |

---

## Las tres reglas, en corto

1. **El Capítulo VI reporta y analiza; el VII concluye y recomienda.** El manual (p. 13) es
   literal: en resultados «no se incluyen conclusiones ni sugerencias».
2. **Ninguna cifra sin respaldo, ninguna proporción sin intervalo.** Incluidas —sobre todo— las
   observadas en cero. Un cero sin intervalo es una afirmación de ausencia que el diseño no
   sostiene.
3. **La comparabilidad tiene veredicto doble.** Fallos y comportamiento: comparable con reservas.
   Rendimiento físico: **no comparable**. Toda cifra de decodificación, MBU o TPOT es
   caracterización absoluta de la A100.

---

## Lo que hace distinto a este paquete

**Las dos secciones nuevas ya están escritas.** En los demás capítulos el LLM redacta a partir de
un guion; aquí las tiene delante, verificadas contra los artefactos, y su trabajo es integrarlas
sin estropearlas. La instrucción más importante del archivo `04` es que **no suavice ninguna
declaración de limitación**: son lo que hace creíbles las cifras buenas.

**Un dato está pendiente a propósito.** La cifra de pruebas del backend no está en el paquete
porque no se ha medido. El capítulo actual dice «25 passed» y hoy hay 35 archivos de test. El LLM
tiene instrucción explícita de dejar un marcador en lugar de inventar.

Para cerrarlo hay que ejecutar la suite —el proyecto la corre en cinco tandas separadas, con sus
variables de entorno— y copiar la línea de resumen literal con su fecha. **Cuidado:** si tienes
`APP_ENV=dev` exportado en el shell, la configuración lo rechaza y fallan 38 recolecciones; los
valores válidos son `development`, `test`, `staging` y `production`.

---

## Antes de dar por bueno lo que te devuelva

Comprueba tú mismo estas seis:

1. Busca `25 passed` y `25 pruebas`. **No pueden aparecer.**
2. Busca «se recomienda», «conviene», «debería», «se entrega al equipo». **No pueden aparecer**:
   son sugerencias, y el manual las prohíbe en este capítulo.
3. Busca `16,8` y `59,1`. **No pueden aparecer**: son las dos cifras que la campaña corrigió.
4. Busca `24,1 s` y verifica que va acompañada de «configuración de julio de 2026».
5. Verifica que **§6.9 es la síntesis** y que cierra el capítulo.
6. Verifica que el bloque de marcadores pendientes **no esté vacío**. Si lo está, el modelo
   inventó la cifra de pruebas.

Si alguna falla, devuélveselo señalando el punto concreto en lugar de corregirlo a mano: es más
rápido y evita que el error se cuele en la siguiente iteración.

---

## Lo que este paquete NO cubre

**Las figuras.** El resultado traerá los marcadores `*[Figura 6.30 — …]*` en su sitio, pero
insertarlas es trabajo de Word:

- Los archivos están en [`../6.9_recaracterizacion_a100/figuras/`](../6.9_recaracterizacion_a100/figuras/),
  en PDF, SVG y PNG. **Inserta el PDF o el SVG, nunca el PNG:** el empastado es impreso y el PNG
  se pixela.
- Los pies completos, con sus notas de lectura, están en
  [`../6.9_recaracterizacion_a100/PIES_DE_FIGURA.md`](../6.9_recaracterizacion_a100/PIES_DE_FIGURA.md).
  **Las notas de lectura no son opcionales:** son las que impiden que un revisor interprete la
  figura del acuerdo de fallos como «la unidad gráfica arregló los errores».
- Antes de mandar a imprenta, revisa cada figura en su versión en escala de grises
  ([`figuras/grises/`](../6.9_recaracterizacion_a100/figuras/grises/)).

**La cita que §6.8.3 refuta.** La sección refuta cuantitativamente un valor publicado sobre el
sobrecosto de la decodificación restringida por gramática. **Esa fuente tiene que existir en el
marco teórico (§1.1.3.7) y en la bibliografía**, con la referencia exacta. Refutar una fuente sin
citarla convierte el mejor resultado del capítulo en un problema. Ver
[`../../03_capitulo_i_marco_teorico/generar/`](../../03_capitulo_i_marco_teorico/generar/).

**La Lista de Tablas y la de Figuras.** Se rehacen al final, desde el bloque C de la salida. Ver
[`../../01_preliminares/generar/`](../../01_preliminares/generar/).
