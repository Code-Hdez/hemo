# Prompt maestro — reescritura completa del Capítulo II

> **Cómo usarlo.** Abre una conversación nueva con un LLM capaz. Pega **este archivo completo**
> y, a continuación, el contenido íntegro de los archivos `01` a `05` de esta carpeta, en ese
> orden, cada uno precedido por su nombre. No hace falta nada más: el paquete es autocontenido y
> el modelo no necesita acceso al repositorio.
>
> Extensión total del material: ~9 500 palabras. Cabe en una sola petición.

---

## Quién eres

Eres un redactor técnico especializado en informes finales de proyecto de grado en ingeniería.
Escribes en español de República Dominicana, en registro académico neutro, en tercera persona.
No adornas, no vendes y no usas adjetivos de mérito.

## Qué vas a producir

El **Capítulo II — Solución propuesta** completo y listo para pegar en el documento de tesis: la
definición del proyecto corregida, el presupuesto reconstruido conforme al manual, **tres
subsecciones nuevas de presupuesto**, el entorno de demostración reescrito y los criterios de
éxito corregidos. Un solo documento continuo, no un listado de parches.

## El contexto que necesitas entender

El proyecto se llama **HemoVet**. Es una plataforma web que interpreta hemogramas completos
caninos para el propietario de la mascota: clasificación multietiqueta con aprendizaje automático,
reglas deterministas de control de calidad, API REST modular, portal web, módulo de vigilancia
poblacional agregada y una capa conversacional con recuperación de información y límites de
seguridad clínica.

El Capítulo II describe el proyecto y su plan de recursos. **Sus secciones sobre justificación
metodológica, delimitación funcional, cronograma, gestión de riesgos y casos de prueba
prevalidados son correctas y no se tocan.**

El problema está en otras tres, y tiene una consecuencia práctica que conviene tener presente:

> **Presupuesto, entorno de demostración y criterios de éxito son las secciones que el comité
> evaluador lee para decidir si la demostración es viable el día de la defensa.**

1. **El presupuesto de hardware dice cero y no es cero.** Además incumple tres exigencias
   explícitas del manual, dos de ellas anteriores a la migración de agosto: no valora los equipos
   propios, no da precios en pesos dominicanos y no incluye porcentaje de contingencia. Y ahora,
   encima, el sistema depende de una unidad de procesamiento gráfico que cuesta dinero real.
2. **El entorno de demostración describe un despliegue que ya no existe.** Dice que el servidor de
   modelos corre sobre CPU en la máquina de producción, y que la máquina con unidad gráfica «no se
   presentará como parte del entorno operativo mientras permanezca apagada». Ambas frases son hoy
   falsas: la unidad gráfica **es** el camino de producción del asistente.
3. **Hay un criterio de éxito que el sistema no cumple ni va a cumplir.** Dice que la latencia de
   respuesta por caso debe ser inferior a diez segundos. La mediana del asistente es de 17,6 a
   21,4 segundos. Dejar escrito un criterio de éxito que la propia tesis demuestra incumplido,
   cuatro capítulos más adelante, es un regalo al comité.

## Las tres reglas que gobiernan todo

### Regla 1 · El Capítulo II propone y planifica; el VI reporta

- ✅ **Sí:** «la latencia de la respuesta conversacional se mantiene por debajo de los treinta
  segundos por turno». *(Es un criterio de aceptación: pertenece aquí.)*
- ✅ **Sí:** «valor coherente con la mediana medida sobre la configuración de producción vigente
  (véase §6.8)». *(Remisión que justifica el criterio, sin reportar el resultado.)*
- ❌ **No:** «la latencia mediana se redujo un 60,6 %». *(Resultado: §6.8.)*
- ❌ **No:** cualquier tabla de mediciones.

Las cifras del Capítulo VI entran aquí **solo como referencia que justifica un criterio**, nunca
como resultado reportado.

### Regla 2 · Ninguna cifra de dinero inventada 🔴

Esta regla es específica de este capítulo y es la más importante de las tres.

El presupuesto tiene que reconstruirse, pero **el paquete no incluye las tarifas reales ni la
facturación del proyecto**. La tentación de rellenar la tabla con cifras plausibles es fuerte y
hay que resistirla: un presupuesto inventado es un documento que el comité puede cuestionar dato
por dato, y no hay defensa posible.

**Construye la tabla completa, con todas sus filas y columnas, y deja cada importe como
`[PENDIENTE: …]` describiendo qué hay que consultar.** Una tabla bien estructurada con importes
pendientes es un entregable útil: quien tenga acceso a la facturación la completa en veinte
minutos. Una tabla con cifras inventadas hay que rehacerla entera.

### Regla 3 · Lo que se planifica tiene que ser lo que se hizo

El capítulo se escribió antes del proyecto y no se revisó después. Cada vez que describa una
tecnología, una topología o un umbral, **compruébalo contra `02_HECHOS_VERIFICADOS.md`**. Si el
documento dice una cosa y los hechos dicen otra, ganan los hechos.

## Estructura de salida exigida

```
Capítulo II — Solución propuesta
  2.1  Definición del Proyecto                → corregir la identidad del modelo
       2.1.1 Justificación metodológica       → ÍNTEGRA
  2.2  Productos del Proyecto
       2.2.1 Delimitación funcional           → ÍNTEGRA
       2.2.2 Pipeline y entregables           → añadir UNA fila
  2.3  Cronograma del Proyecto                → ÍNTEGRA (verificar que agosto cabe)
  2.4  Plan de Gestión de Riesgos (2.4.1, 2.4.2) → ÍNTEGRAS
  2.5  Presupuesto                            → corregir la frase de «cinco categorías»
       2.5.1 Hardware                         → RECONSTRUIR la tabla
       2.5.2 Software y licencias             → corregir una fila, añadir otra
       2.5.3 Datos                            → SUBSECCIÓN NUEVA
       2.5.4 Recursos humanos                 → SUBSECCIÓN NUEVA
       2.5.5 Costos operativos de despliegue  → SUBSECCIÓN NUEVA
  2.6  Definición de la Demostración
       2.6.1 Entorno de ejecución             → REESCRIBIR
       2.6.2 Casos de prueba prevalidados     → ÍNTEGRA
       2.6.3 Flujo y criterios de éxito       → corregir el criterio de latencia + añadir uno
```

## Numeración de tablas y figuras 🔴

**Este capítulo es el único del documento con numeración suelta**, y el manual pide numeración
consecutiva por categoría. Renumera:

| Actual | Nuevo | Título |
| :--- | :--- | :--- |
| Tabla 1 | **Tabla 2.1** | Criterios mínimos de aceptación del motor de aprendizaje automático |
| Tabla 2 | **Tabla 2.2** | Mapa de artefactos del *pipeline* por fase de desarrollo |
| Tabla 3 | **Tabla 2.3** | Cronograma del proyecto por frente de trabajo |
| Tabla 4 | **Tabla 2.4** | Estimación de costos de hardware |
| Tabla 5 | **Tabla 2.5** | Estimación de costos de software |
| Tabla 6 | **Tabla 2.6** | Casos de prueba prevalidados para la demostración |
| Figura 1 | **Figura 2.1** | *(conservar su título actual)* |
| Figura 2 | **Figura 2.2** | *(conservar su título actual)* |
| Figura 3 | **Figura 2.3** | *(conservar su título actual)* |

**Y actualiza todas las referencias del cuerpo** que digan «la Tabla 4» o «la Figura 2». Es un
cambio mecánico de bajo riesgo que elimina una observación segura del comité.

Las tablas nuevas de §2.5.3, §2.5.4 y §2.5.5 continúan la serie: **2.7, 2.8 y 2.9** si decides que
cada una lleve tabla. Si alguna se resuelve mejor en prosa, resuélvela en prosa y decláralo.

## Extensión

El capítulo actual tiene ~4 130 palabras. El resultado debe estar entre **5 200 y 6 100 palabras**.
Si te pasas mucho, probablemente reescribiste el cronograma o la matriz de riesgos, que van
íntegros.

## Antes de entregar

Recorre el checklist de `05_CONTRATO_DE_SALIDA.md` punto por punto. Si algo no lo cumples, dilo en
el registro de cambios en lugar de disimularlo.
