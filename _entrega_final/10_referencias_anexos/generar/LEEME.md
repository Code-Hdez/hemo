# generar/ — paquete autocontenido para referencias bibliográficas y anexos

Todo lo necesario para que un LLM produzca el bloque de **Referencias y Anexos** completo, con el
**Anexo E que hoy no existe**, y te lo devuelva listo para pegar en Word. **No requiere acceso al
repositorio:** los datos están dentro.

---

## Cómo se usa

1. Abre una conversación nueva con un LLM capaz (ventana de contexto amplia).
2. Pega los archivos **en este orden**, cada uno precedido por su nombre en una línea:

```
00_PROMPT_MAESTRO.md          ← quién eres, qué produces, las tres reglas
01_TEXTO_ACTUAL.md            ← bibliografía y anexos A–D, íntegros
02_HECHOS_VERIFICADOS.md      ← las ocho referencias que faltan y los datos del Anexo E
03_ESTILO_Y_FORMATO.md        ← registro, formato IEEE, convenciones numéricas
04_GUION_SECCIONES_NUEVAS.md  ← arquitectura de los nueve apartados del Anexo E
05_CONTRATO_DE_SALIDA.md      ← qué devolver y checklist de verificación
```

3. Cierra con: **«Produce ahora el bloque completo según el contrato de salida.»**

Son ~12 000 palabras en total: entra en una sola petición.

## Qué te devuelve

Un documento continuo en Markdown —el bloque entero, no parches— más cuatro bloques: registro de
cambios, **estado de cada referencia**, marcadores de tabla y figura pendientes, e inconsistencias
detectadas.

**Para pasarlo a Word:** copia el Markdown, pégalo en un editor que lo renderice, copia lo
renderizado y pégalo en el `.docx` **con formato**. Después aplica el `CHECKLIST_FORMATO.md` de la
guía general.

---

## Qué contiene el paquete

| Archivo | Palabras aprox. | Contenido |
| :--- | ---: | :--- |
| `00_PROMPT_MAESTRO.md` | 950 | El encargo, el diagnóstico y las tres reglas |
| `01_TEXTO_ACTUAL.md` | 5 390 | Bibliografía y anexos A–D verbatim del `.docx (4)` |
| `02_HECHOS_VERIFICADOS.md` | 2 400 | Las ocho referencias que faltan, los dos riesgos, y los datos de cada apartado del Anexo E |
| `03_ESTILO_Y_FORMATO.md` | 900 | Registro, formato IEEE, compendios truncados |
| `04_GUION_SECCIONES_NUEVAS.md` | 1 700 | Arquitectura apartado por apartado del Anexo E |
| `05_CONTRATO_DE_SALIDA.md` | 1 100 | Formato de entrega, cuatro bloques y checklist de 34 puntos |

---

## Qué falta y por qué

**El Anexo E no existe.** Los anexos A–D siguen el mismo patrón: cada resultado importante del
Capítulo VI tiene su respaldo documental. Con §6.8 incorporada, sería **el único resultado del
proyecto sin anexo** — y precisamente el que más evidencia tiene detrás: 208 ficheros auditados,
diez hipótesis firmadas antes de medir, 36 figuras y 37 tablas con procedencia criptográfica, y
once aserciones de recálculo.

**Y faltan tres cosas menores:** dos riesgos en la matriz del Anexo A, la evidencia de agosto en el
Anexo C, y ocho referencias que las secciones nuevas de los capítulos I, III y VI necesitan.

---

## Las tres reglas, en corto

1. **No inventes ni una sola referencia.** Es la regla absoluta de este bloque.
2. **Un anexo presenta evidencia; no la analiza.** El análisis es §6.8.
3. **Lo que no se pudo medir se anexa igual.** La aserción que falla, los ejes no puntuables, los
   niveles de traza vacíos y las tres limitaciones de la ablación entran en el anexo.

---

## El riesgo real de este encargo

**Que el modelo invente referencias.** Es el mismo riesgo que el paquete del Capítulo I, y aquí
está multiplicado por ocho.

Se le pide un bloque de bibliografía y se le dice que faltan ocho entradas. Un modelo de lenguaje
ante ese encargo produce, con alta probabilidad, ocho referencias perfectamente formateadas, con
autores plausibles y años verosímiles, que no existen.

> **Una referencia inventada es el único error de todo el documento que un miembro del comité puede
> verificar desde su teléfono, en treinta segundos, mientras hablas.**

Por eso el contrato de salida exige un bloque entero con el **estado de cada referencia**, y el
checklist lo comprueba antes que nada.

**Un marcador honesto se resuelve con una tarde de búsqueda. Una referencia inventada no se
resuelve.**

---

## Antes de dar por bueno lo que te devuelva

1. **Busca cada referencia que haya escrito completa** —no las pendientes— y **compruébala una por
   una**. Si citó autor, título, publicación y año, búscalo. Si no aparece, no existe.
2. Cuenta las entradas de la bibliografía original y las del resultado. **Tiene que haber las
   mismas**, con los mismos números. Las nuevas van aparte.
3. Verifica que el **tablero de hipótesis está tal como está sellado**: las tres filas que dicen
   «no evaluada» siguen diciéndolo, y la discrepancia se señala en el texto.
4. Verifica que la **aserción que falla** está en la Tabla E.5, con su motivo. Si desapareció, el
   anexo perdió lo mejor que tenía.
5. Verifica que el **Anexo E tiene sus nueve apartados y que cada uno tiene párrafo
   introductorio**. Un anexo de tablas encadenadas no se lee.
6. Busca «demuestra que», «lo que confirma», «se recomienda». Un anexo no analiza.

Si alguna falla, devuélveselo señalando el punto concreto en lugar de corregirlo a mano.

---

## Lo que este paquete NO cubre

**Conseguir las ocho referencias.** El paquete describe con precisión qué hay que citar, pero
encontrarlas es trabajo de biblioteca. La crítica es `[REF-NUEVA-2]`, la fuente que publica el
sobrecosto de la decodificación restringida por gramática: **§6.8 la refuta cuantitativamente**, y
refutar una fuente sin citarla convierte el mejor resultado del proyecto en un problema.

**Tres tablas largas.** E.3 (13 filas), E.4 (45 filas) y E.10 (58 filas) ya están generadas y el
resultado las dejará como marcadores. Están en:

- [`anexo_E_recaracterizacion/tablas/`](../anexo_E_recaracterizacion/tablas/) — procedencia y
  manifiesto de figuras, en CSV y en versión lista para pegar.
- [`../../08_capitulo_vi_resultados/6.9_recaracterizacion_a100/TRAZABILIDAD.csv`](../../08_capitulo_vi_resultados/6.9_recaracterizacion_a100/TRAZABILIDAD.csv)
  — trazabilidad.

> **E.4 y E.10 se solapan.** Recomendación: imprimir E.4 y dejar la trazabilidad como anexo
> digital. El paquete pide que esa decisión se declare en el texto, no que se resuelva en silencio.

**Las figuras.** Están en
[`../../08_capitulo_vi_resultados/6.9_recaracterizacion_a100/figuras/`](../../08_capitulo_vi_resultados/6.9_recaracterizacion_a100/figuras/),
en PDF, SVG y PNG, con versión en escala de grises. **Inserta el PDF o el SVG, nunca el PNG.**

**La verificación de privacidad.** Antes de anexar cualquier traza al Anexo C hay que comprobar
fichero por fichero que no contiene identificadores de mascota, propietario ni clínica. El material
de la campaña es de prueba, **pero eso hay que comprobarlo, no suponerlo**.

---

## Cuándo hacer este bloque

**Al final de los capítulos de contenido y antes de los preliminares.**

El Anexo E depende del Capítulo VI, y la auditoría de la bibliografía solo se puede cerrar cuando
todas las secciones nuevas —§1.1.3.7, §3.11, §5.9, §5.10, §6.6 y §6.8— estén insertadas: hasta
entonces no se sabe en qué orden aparecen las citas.

**La renumeración de citas se hace en Word con referencias cruzadas, nunca a mano.** Insertar
§1.1.3.7 en el Capítulo I desplaza toda la numeración posterior del documento: es el cambio de
mayor riesgo mecánico de toda la revisión.
