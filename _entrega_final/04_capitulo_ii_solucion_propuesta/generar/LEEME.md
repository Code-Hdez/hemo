# generar/ — paquete autocontenido para reescribir el Capítulo II

Todo lo necesario para que un LLM produzca el **Capítulo II completo**, con el presupuesto
reconstruido y el entorno de demostración corregido, y te lo devuelva listo para pegar en Word.
**No requiere acceso al repositorio:** los datos están dentro.

---

## Cómo se usa

1. Abre una conversación nueva con un LLM capaz (ventana de contexto amplia).
2. Pega los archivos **en este orden**, cada uno precedido por su nombre en una línea:

```
00_PROMPT_MAESTRO.md          ← quién eres, qué produces, las tres reglas
01_TEXTO_ACTUAL.md            ← el Capítulo II íntegro tal como está hoy
02_HECHOS_VERIFICADOS.md      ← los datos del sistema y los textos ya redactados
03_ESTILO_Y_FORMATO.md        ← registro, terminología, números, tablas
04_GUION_SECCIONES_NUEVAS.md  ← arquitectura de las tres subsecciones de presupuesto
05_CONTRATO_DE_SALIDA.md      ← qué devolver y checklist de verificación
```

3. Cierra con: **«Produce ahora el Capítulo II completo según el contrato de salida.»**

Son ~9 500 palabras en total: entra en una sola petición.

## Qué te devuelve

Un documento continuo en Markdown —el capítulo entero, no parches— más cuatro bloques: registro de
cambios, **marcadores pendientes**, inventario de tablas y figuras renumeradas, e inconsistencias
detectadas.

**Para pasarlo a Word:** copia el Markdown, pégalo en un editor que lo renderice (el visor de
Markdown de VS Code, Typora, o cualquier conversor en línea), copia lo renderizado y pégalo en el
`.docx` **con formato**. Las tablas llegan como tablas reales. Después aplica el
`CHECKLIST_FORMATO.md` de la guía general.

---

## Qué contiene el paquete

| Archivo | Palabras aprox. | Contenido |
| :--- | ---: | :--- |
| `00_PROMPT_MAESTRO.md` | 1 100 | El encargo, los tres problemas del capítulo y las tres reglas |
| `01_TEXTO_ACTUAL.md` | 4 130 | El Capítulo II verbatim del `.docx (4)` |
| `02_HECHOS_VERIFICADOS.md` | 2 100 | Datos del sistema, textos ya redactados y la estructura del presupuesto |
| `03_ESTILO_Y_FORMATO.md` | 910 | Registro, convenciones numéricas, numeración de tablas |
| `04_GUION_SECCIONES_NUEVAS.md` | 1 300 | Arquitectura de las tres subsecciones de presupuesto y de la reescritura de §2.6.1 |
| `05_CONTRATO_DE_SALIDA.md` | 1 100 | Formato de entrega, cuatro bloques y checklist de 33 puntos |

---

## Por qué este capítulo importa el día de la defensa

Los capítulos técnicos los lee el asesor. **Presupuesto, entorno de demostración y criterios de
éxito los lee el comité para decidir si la demostración es viable.** Y los tres están hoy
desmentidos:

- El presupuesto de hardware **dice cero y no es cero**, además de incumplir tres exigencias
  explícitas del manual: valorar los equipos propios, dar precios en las dos monedas e incluir
  contingencia.
- El entorno de demostración describe el servidor de modelos corriendo sobre CPU y dice que la
  máquina con unidad gráfica «no se presentará como parte del entorno operativo». **La unidad
  gráfica es el camino de producción del asistente.**
- Hay un criterio de éxito —latencia por caso inferior a diez segundos— que **el sistema no cumple
  y no va a cumplir**. La mediana del asistente es de 17,6 a 21,4 segundos, y la propia tesis lo
  demuestra cuatro capítulos más adelante.

Ese último es el más caro de los tres. Un criterio de éxito que el documento se desmiente a sí
mismo es de las pocas cosas que un comité puede verificar sin conocer el proyecto.

---

## Las tres reglas, en corto

1. **El Capítulo II propone y planifica; el VI reporta.** Las cifras de §6.8 entran aquí solo como
   referencia que justifica un criterio.
2. **Ninguna cifra de dinero inventada.** Es la regla propia de este capítulo.
3. **Lo que se planifica tiene que ser lo que se hizo.** El capítulo se escribió antes del proyecto
   y no se revisó después.

---

## El riesgo real de este encargo

**Que el modelo rellene el presupuesto.**

Se le pide reconstruir una tabla de costos y no se le dan las cifras. Un modelo de lenguaje ante
una tabla vacía tiende a completarla con valores plausibles —una laptop son ochocientos dólares,
una A100 son tantos por hora— y el resultado parece un presupuesto perfectamente razonable. Lo es,
hasta que alguien pregunta de dónde sale un número.

El prompt lo prohíbe, el contrato exige un bloque entero de pendientes y el checklist pide
**contar los marcadores: si son menos de ocho, hay importes inventados**.

**Una tabla bien estructurada con importes pendientes es un entregable útil:** quien tenga acceso
a la facturación la completa en veinte minutos. Una con cifras inventadas hay que rehacerla
entera.

---

## Antes de dar por bueno lo que te devuelva

1. **Cuenta los marcadores `[PENDIENTE:` del presupuesto.** Menos de ocho significa que inventó
   importes.
2. Busca `Qwen3 4B`, `Ollama sobre CPU` y `10 segundos`. **Ninguno puede aparecer.**
3. Verifica que §2.5 tiene **cinco** subsecciones, no dos.
4. Verifica que la tabla de hardware tiene **columna en RD$** y línea de **contingencia**.
5. **Suma el presupuesto.** Ninguna partida puede estar en dos subsecciones; la máquina de
   inferencia es la candidata a duplicarse entre §2.5.1 y §2.5.5.
6. Busca «la Tabla 4» y «la Figura 2» en el cuerpo. Si quedan, la renumeración está a medias.

Si alguna falla, devuélveselo señalando el punto concreto en lugar de corregirlo a mano.

---

## Lo que este paquete NO cubre

**Las cifras del presupuesto.** Hay que conseguirlas de dos sitios: la facturación real del
proyecto en Google Cloud, y la valoración de mercado local de los dos equipos propios. Las horas
de la máquina de inferencia que sí constan están en `02` §2, con la advertencia de que **tres de
las seis ventanas son cota inferior** y de que cubren solo la campaña de medición.

**Los dos riesgos nuevos.** La matriz de riesgos no contempla la indisponibilidad de la instancia
interrumpible ni la deriva entre el modelo sellado y el instalado. **Esas dos filas se añaden en
el Anexo A**, no en §2.4, para no duplicar. Ver
[`../../10_referencias_anexos/generar/`](../../10_referencias_anexos/generar/).

**Un pendiente operativo, no de redacción.** La máquina de producción quedó temporalmente
degradada por un evento de capacidad zonal y está pendiente devolverla a su dimensionamiento
previo. **Hacerlo antes de la defensa, no durante.** Y la instancia interrumpible no tiene
vigilante de rearranque: si el proveedor la reclama, queda parada.
