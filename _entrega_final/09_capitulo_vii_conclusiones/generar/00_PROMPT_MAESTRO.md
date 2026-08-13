# Prompt maestro — reescritura completa del Capítulo VII

> **Cómo usarlo.** Abre una conversación nueva con un LLM capaz. Pega **este archivo completo**
> y, a continuación, el contenido íntegro de los archivos `01` a `05` de esta carpeta, en ese
> orden, cada uno precedido por su nombre. No hace falta nada más: el paquete es autocontenido y
> el modelo no necesita acceso al repositorio.
>
> Extensión total del material: ~10 000 palabras. Cabe en una sola petición.

---

## Quién eres

Eres un redactor técnico especializado en informes finales de proyecto de grado en ingeniería.
Escribes en español de República Dominicana, en registro académico neutro, en tercera persona y
en pasado para lo ejecutado. No adornas, no vendes y no usas adjetivos de mérito.

## Qué vas a producir

El **Capítulo VII — Conclusiones y recomendaciones** completo y listo para pegar en el documento
de tesis: las siete secciones actuales, con **cinco limitaciones nuevas**, **tres hallazgos
inesperados nuevos**, una sección reescrita, dos filas de tabla actualizadas y un párrafo de
sostenibilidad económica. Un solo documento continuo, no un listado de parches.

## El contexto que necesitas entender

El proyecto se llama **HemoVet**. Es una plataforma web que interpreta hemogramas completos
caninos para el propietario de la mascota: clasificación multietiqueta con aprendizaje automático,
reglas deterministas de control de calidad, API REST modular, portal web, módulo de vigilancia
poblacional agregada y una capa conversacional con recuperación de información y límites de
seguridad clínica.

El Capítulo VII actual **está bien escrito** y tiene los siete sub-ítems que el manual exige, en
el orden correcto. El problema es de otra naturaleza:

> **Cierra un proyecto que siguió avanzando un mes más.**

En agosto de 2026 se migró el *runtime* conversacional a una unidad de procesamiento gráfico
NVIDIA A100 y se caracterizó el cambio con una campaña de medición de diez hipótesis firmadas
antes de medir. De ahí salen tres consecuencias para este capítulo:

1. **§7.6 afirma algo que hoy es falso:** que el modelo de lenguaje se ejecuta sin aceleración
   gráfica. Además cita una cifra de pruebas desactualizada. Dos errores en una frase.
2. **§7.3 no recoge cinco limitaciones** que la campaña declaró, todas reales y todas
   documentadas.
3. **§7.4 se pierde tres hallazgos inesperados** que son de los mejores del proyecto —incluido uno
   en que una expectativa tomada de la literatura quedó refutada por un factor de cuarenta y
   cuatro.

Y una cuarta, de credibilidad: **§7.5 recomienda dos cosas que ya se hicieron**. Presentar como
pendiente un trabajo que el Capítulo VI demuestra ejecutado desperdicia el trabajo y resta
autoridad al resto de la lista.

## Las tres reglas que gobiernan todo

### Regla 1 · El Capítulo VII resume el VI; no lo amplía

Esta es la regla más importante y la más fácil de romper en este capítulo concreto, porque aquí
**sí** se permite concluir y recomendar —es su función— pero **solo sobre lo que el Capítulo VI ya
demostró**.

- ✅ **Sí:** «la latencia mediana por turno se sitúa en 21,4 segundos (§6.8)».
- ✅ **Sí:** «se recomienda incorporar un mecanismo automático de rearranque del nodo de
  inferencia». *(Es una recomendación derivada de una limitación reportada.)*
- ❌ **No:** cualquier cifra que no esté en el Capítulo VI. Si la necesitas y no está allí, hay que
  meterla allí primero, no aquí.
- ❌ **No:** cifras sin su referencia de sección.

**La prueba:** cada afirmación cuantitativa de este capítulo tiene que poder señalarse con el dedo
en el anterior. Si no puedes, no va.

### Regla 2 · Ninguna cifra sin respaldo, y toda cifra con su sección

Todo número que escribas debe estar en `02_HECHOS_VERIFICADOS.md` **y llevar la referencia a la
sección del Capítulo VI que lo reporta**: `(§6.8)`, `(§6.5)`, `(§6.6)`. El Capítulo VII no es
fuente de ninguna cifra.

Si necesitas un dato que no está, **no lo inventes ni lo estimes**: escribe
`[PENDIENTE: descripción de lo que falta]` y anótalo en el registro de cambios.

### Regla 3 · Lo que se añade se añade; lo que está, se respeta

Las siete limitaciones y los cinco hallazgos actuales **son correctos y se mantienen íntegros**.
Las limitaciones nuevas son la **octava a la duodécima**; los hallazgos nuevos son el **sexto,
séptimo y octavo**. No renumeres, no reordenes, no reescribas los existentes.

Es un capítulo que funciona. El encargo es completarlo, no rehacerlo.

## Estructura de salida exigida

```
Capítulo VII — Conclusiones y recomendaciones
  7.1  Conclusiones                       → añadir media frase de cierre + corregir un punto doble
  7.2  Resultados de los objetivos        → actualizar DOS filas de la Tabla 7.1
  7.3  Limitaciones                       → las 7 actuales ÍNTEGRAS + cinco nuevas (8ª a 12ª)
  7.4  Resultados inesperados             → los 5 actuales ÍNTEGROS + tres nuevos (6º, 7º, 8º)
  7.5  Recomendaciones                    → reformular los puntos 1 y 2 como cumplidos
                                            + un párrafo nuevo de pendientes técnicos
                                            + acoger una frase trasladada desde §6.4.2
  7.6  Puesta en funcionamiento           → reescribir el último párrafo + precisar el primero
  7.7  Sostenibilidad                     → añadir un párrafo de sostenibilidad económica
```

**No se añaden secciones nuevas.** El capítulo conserva sus siete sub-ítems: el manual los exige y
el documento ya los cumple.

## Numeración

La **Tabla 7.1** es la única del capítulo y conserva su número. Se modifican dos de sus filas
—OE4 y OE5— y ninguna otra.

## Extensión

El capítulo actual tiene ~3 070 palabras. El resultado debe estar entre **4 400 y 5 100
palabras**. Si te pasas, es que reescribiste las limitaciones o los hallazgos existentes en lugar
de añadir los nuevos.

## Antes de entregar

Recorre el checklist de `05_CONTRATO_DE_SALIDA.md` punto por punto. Si algo no lo cumples, dilo en
el registro de cambios en lugar de disimularlo.
