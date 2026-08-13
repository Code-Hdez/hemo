# Contrato de salida — qué tienes que devolver exactamente

---

## Formato

**Un único documento en Markdown**, continuo, listo para copiar y pegar en Microsoft Word. No
devuelvas parches, diferencias ni listas de instrucciones: devuelve **el capítulo entero**, desde
el título hasta la última frase de §7.7, con las secciones que no cambian **reproducidas
íntegras**.

Motivo: quien recibe esto va a seleccionar todo, copiar y pegar sobre el capítulo actual. Si
devuelves solo lo modificado, tendrá que reconstruirlo a mano y ahí es donde se cometen los
errores.

### Cómo estructurarlo

````
# Capítulo VII — Conclusiones y recomendaciones

## 7.1. Conclusiones
[texto íntegro con la media frase de cierre añadida]

## 7.2. Resultados de los objetivos planteados
[texto]

| Objetivo | Evidencia | Estado |
| :--- | :--- | :--- |
| … | … | … |

*Tabla 7.1. Cumplimiento de los objetivos específicos del proyecto.*

[párrafo de cierre, literal]

## 7.3. Limitaciones
[las siete actuales, íntegras, y después las cinco nuevas]
````

- Encabezados con `#` y `##`.
- La Tabla 7.1 en Markdown estándar con barras, con **todas** sus filas.
- Título de tabla **debajo**, en cursiva.

## Después del capítulo, cuatro bloques obligatorios

### Bloque A — Registro de cambios

| Sección | Tipo | Qué cambió | Por qué |
| :--- | :--- | :--- | :--- |
| 7.1 | Ampliación | Media frase de cierre al párrafo 3 | §6.8 es nueva y la valoración global no la recogía |
| 7.1 | Corrección | Punto doble en «usabilidad..» | Errata |
| 7.2 | Corrección | Filas OE4 y OE5 de la Tabla 7.1 | OE4 ya tiene sección de resultados; OE5 tiene evidencia nueva |
| 7.3 | Ampliación | Cinco limitaciones nuevas, octava a duodécima | Declaradas por la campaña y ausentes del capítulo |
| 7.4 | Ampliación | Tres hallazgos nuevos, sexto a octavo | … |
| 7.5 | Corrección | Puntos 1 y 2 reformulados como cumplidos | El Capítulo VI demuestra que se ejecutaron |
| 7.6 | Corrección | Último párrafo reescrito | Afirmaba que el modelo corre sin aceleración gráfica |
| 7.7 | Ampliación | Párrafo de sostenibilidad económica | El sistema tiene un costo recurrente no declarado |
| … | | | |

Tipos válidos: `Corrección` · `Ampliación` · `Renumeración` · `Estilo` · `Traslado`.

### Bloque B — Marcadores pendientes

- `[PENDIENTE: …]` — qué falta y quién puede aportarlo.
- Cualquier remisión a una sección que quizá no exista todavía (§5.10, §6.6, §6.8, §1.1.3.7):
  **anótala aquí**, porque este capítulo remite a secciones que otros paquetes están creando.

**Este bloque no debería estar vacío.** Como mínimo debe registrar dos cosas: que la cifra de
pruebas del backend queda remitida a §6.5 sin número, y que la frase trasladada desde §6.4.2
depende de que el Capítulo VI ya se haya corregido.

### Bloque C — Remisiones utilizadas

Lista de **todas** las referencias a otras secciones que aparecen en tu salida (§6.5, §6.6, §6.8,
§5.7, §5.10, §2.5.1…), para que quien coordine el documento pueda verificar que cada una existe y
lleva el número final correcto.

Es un bloque específico de este capítulo, y hace falta porque el Capítulo VII es el que más
remisiones concentra de todo el documento.

### Bloque D — Inconsistencias detectadas

Si encuentras una contradicción entre los archivos de este paquete, o un hecho que necesitas y no
está: **no la resuelvas inventando**. Escríbela aquí con la ubicación exacta y las dos versiones
en conflicto.

---

## Checklist de verificación — recórrelo antes de entregar

### Contenido

- [ ] Están las **siete** secciones, numeradas 7.1 a 7.7. **No se añadió ninguna.**
- [ ] §7.3 tiene **doce** limitaciones, y las siete primeras están reproducidas íntegras.
- [ ] §7.4 tiene **ocho** hallazgos, y los cinco primeros están reproducidos íntegros.
- [ ] §7.5 conserva íntegros sus párrafos 1, 2, 3 y 5.
- [ ] La Tabla 7.1 está completa, con todas sus filas, y solo cambiaron OE4 y OE5.
- [ ] El párrafo de cierre de §7.2 está reproducido literal.
- [ ] La extensión total está entre 4 400 y 5 100 palabras.

### Ordinales — el error mecánico más probable

- [ ] §7.3 va de «en primer lugar» a «en duodécimo lugar», sin saltos ni repeticiones.
- [ ] §7.4 va del primer al octavo hallazgo, sin saltos ni repeticiones.
- [ ] No se renumeró ninguna limitación ni hallazgo preexistente.

### Cifras — la Regla 2

- [ ] **Toda cifra lleva su remisión** `(§6.N)`. Recorre el capítulo buscando números y
      compruébalo uno por uno.
- [ ] `25 pruebas` **no aparece**; en su lugar hay una remisión a §6.5 sin número.
- [ ] `sin aceleración GPU` **no aparece** en ninguna forma.
- [ ] `16,8` **no aparece**; la cota de alucinación de la campaña es 29,9 %.
- [ ] `Qwen3 4B` **no aparece**.
- [ ] Toda cifra que escribiste está en `02_HECHOS_VERIFICADOS.md`. Ninguna es estimada.
- [ ] Coma decimal en todos los números, incluidos los que reproduces de la tabla original
      (`83,3 %`, `0,841`).

### Altitud — la Regla 1

- [ ] Ninguna cifra de este capítulo es nueva respecto del Capítulo VI.
- [ ] No se reporta ningún resultado que el Capítulo VI no reporte antes.
- [ ] Las recomendaciones derivan de limitaciones o hallazgos declarados, no de intuiciones.

### Honestidad

- [ ] Está declarado que la configuración anterior no es reproducible (11 de 15 sin constancia).
- [ ] Está declarado que las cifras de rendimiento físico **no son una comparación entre unidades
      de procesamiento gráfico**.
- [ ] Está declarado que cero alucinaciones observadas no demuestra ausencia.
- [ ] Está declarado que el diseño no distingue un efecto intermedio.
- [ ] Está declarado que el modelo anterior sigue instalado y que la comprobación no impide su
      uso.
- [ ] Está declarado que no existe mecanismo automático de rearranque.
- [ ] En §7.4, el séptimo hallazgo deja claro que la bajada de fallos **no** fue la corrección de
      los fallos anteriores.

### Estilo

- [ ] Sin adjetivos de mérito.
- [ ] **Sin frases defensivas** del tipo «no obstante, esto no invalida los resultados» añadidas a
      las limitaciones.
- [ ] Términos traducidos según `03_ESTILO_Y_FORMATO.md`; los que quedan en inglés, en cursiva.
- [ ] Sin código, rutas de fichero, nombres de *commit*, ni nombres de variables.

---

## Qué hacer si algo no encaja

Es más útil un capítulo con tres marcadores honestos que uno completo con tres cifras inventadas.
Lo primero se cierra en diez minutos; lo segundo puede costar la defensa.
