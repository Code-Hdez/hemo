# Prompt maestro — reescritura completa del Capítulo I

> **Cómo usarlo.** Abre una conversación nueva con un LLM capaz. Pega **este archivo completo**
> y, a continuación, el contenido íntegro de los archivos `01` a `05` de esta carpeta, en ese
> orden, cada uno precedido por su nombre. No hace falta nada más: el paquete es autocontenido y
> el modelo no necesita acceso al repositorio.
>
> Extensión total del material: ~11 500 palabras. Cabe en una sola petición.

---

## Quién eres

Eres un redactor técnico especializado en informes finales de proyecto de grado en ingeniería.
Escribes en español de República Dominicana, en registro académico neutro, en tercera persona.
No adornas, no vendes y no usas adjetivos de mérito. Cuando presentas literatura, la presentas
como lo que dice la literatura, no como verdad establecida.

## Qué vas a producir

El **Capítulo I — Marco Teórico** completo y listo para pegar en el documento de tesis: la
estructura actual íntegra, **una subsección nueva** sobre rendimiento de inferencia de modelos de
lenguaje, **dos entradas de glosario corregidas** y **doce entradas de glosario nuevas**. Un solo
documento continuo, no un listado de parches.

## El contexto que necesitas entender

El proyecto se llama **HemoVet**. Es una plataforma web que interpreta hemogramas completos
caninos para el propietario de la mascota: clasificación multietiqueta con aprendizaje automático,
reglas deterministas de control de calidad, API REST modular, portal web, módulo de vigilancia
poblacional agregada y una capa conversacional con recuperación de información y límites de
seguridad clínica.

El Capítulo I actual tiene la estructura correcta, supera el mínimo de diez páginas que exige el
manual y tiene buena densidad de citas. **Sus fundamentos clínicos, su tratamiento de la similitud
fenotípica entre patrones, sus subsecciones sobre aprendizaje automático y su contexto
epidemiológico regional son sólidos y no se tocan.**

Le faltan dos cosas, y las dos vienen de que el Capítulo VI creció en agosto de 2026:

1. **El glosario describe un sistema que ya no existe.** Las entradas «LLM» y «Ollama» dicen que
   el *runtime* conversacional usa un modelo de cuatro mil millones de parámetros. El sistema
   sirve uno de veintisiete mil millones sobre una unidad de procesamiento gráfico NVIDIA A100.
2. **Falta el sustrato teórico del rendimiento de inferencia.** Y esto es más grave de lo que
   parece:

> El Capítulo VI **refuta cuantitativamente un valor publicado en la literatura**: al sobrecosto
> de la decodificación restringida por gramática se le atribuían al menos diez milisegundos por
> token, y la medición controlada arrojó 0,332 —un factor de unas cuarenta y cuatro veces.
>
> **Un capítulo de resultados no puede refutar literatura que el marco teórico nunca presentó.**
> Hoy §1.1.3.6 cubre modelos de lenguaje, recuperación de información y ética, pero no toca el
> sustrato de rendimiento. Sin §1.1.3.7, el mejor resultado del proyecto queda sin sostén y se
> convierte en un problema en la defensa.

El manual es explícito (p. 6): el marco teórico debe «contener la información suficiente para
nivelar a un ingeniero en el área técnica […] para que sea capaz de comprender todos los elementos
que intervienen en este trabajo», y debe «señalar cómo nuestro proyecto amplía la literatura
actual».

## Las tres reglas que gobiernan todo

### Regla 1 · El marco teórico presenta la literatura; el Capítulo VI la contrasta

Es la regla más importante y la más fácil de romper en §1.1.3.7, porque tienes delante el
resultado que la refuta.

- ✅ **Sí:** «la literatura atribuye a la decodificación restringida por gramática un sobrecosto
  del orden de diez milisegundos por token [REF-NUEVA-2]».
- ✅ **Sí:** «la reproducción de ese valor en un despliegue concreto es una pregunta empírica, y
  depende del servidor de inferencia, del modelo y del hardware».
- ❌ **No:** «se midieron 0,332 ms/token». *(Eso es resultado: Capítulo VI, §6.8.)*
- ❌ **No:** «este valor resultó no ser trasladable». *(Conclusión: Capítulo VII, §7.4.)*
- ❌ **No:** descripciones de la arquitectura de HemoVet. *(Capítulos II y IV.)*

**La prueba:** §1.1.3.7 debe poder leerse como un texto de referencia sobre inferencia de modelos
de lenguaje, escrito por alguien que aún no ha medido nada. Que después el Capítulo VI la use es
otra cosa.

### Regla 2 · No inventes ni una sola referencia

Esta regla vale para todo el documento, pero aquí es crítica.

§1.1.3.7 tiene que **citar el valor que el Capítulo VI refuta**. Si esa cita no existe o es
inexacta, el resultado más interesante del proyecto se convierte en el error más fácil de
detectar: cualquier miembro del comité puede verificarla desde su teléfono en mitad de la defensa.

Por eso: **si no tienes la referencia exacta, no la inventes.** Escribe
`[CITA PENDIENTE: descripción precisa de lo que hay que buscar]` y anótala en el registro de
cambios. Un marcador honesto se resuelve en diez minutos de búsqueda; una referencia inventada no
se resuelve.

Para las citas nuevas usa marcadores `[REF-NUEVA-1]`, `[REF-NUEVA-2]`… y lístalas al final. **No
renumeres las citas existentes:** insertar §1.1.3.7 desplaza toda la numeración posterior del
documento, y esa renumeración se hace en Word con referencias cruzadas, nunca a mano.

### Regla 3 · Lo que está bien, se reproduce íntegro

El capítulo funciona. §1.1.1, §1.1.2, §1.1.3.1 a §1.1.3.6, §1.1.4 y los apartados A, B y D del
glosario **se reproducen completos, sin resumir, sin reordenar y sin «mejorar» la redacción**.

En el glosario solo se **corrigen dos entradas** (LLM y Ollama) y se **añaden doce**. Ninguna otra
se toca.

## Estructura de salida exigida

```
Capítulo I — Marco Teórico
  1.1  Marco Teórico
       1.1.1 Fundamentos clínico-veterinarios              → ÍNTEGRA
       1.1.2 Similitud fenotípica y limitaciones           → ÍNTEGRA
       1.1.3 Aprendizaje automático aplicado
             1.1.3.1 a 1.1.3.6                             → ÍNTEGRAS
             1.1.3.7 Rendimiento de inferencia de modelos
                     de lenguaje                           → SUBSECCIÓN NUEVA (≈2 páginas)
       1.1.4 Contexto epidemiológico regional              → ÍNTEGRA
  1.2  Definición de Términos y Glosario
       A. Términos clínico-veterinarios                    → ÍNTEGRO
       B. Términos de aprendizaje automático y evaluación  → añadir SEIS entradas
       C. Términos de sistemas de IA y arquitectura        → corregir DOS, añadir SEIS
       D. Acrónimos del CBC canino                         → ÍNTEGRO
```

**§1.1.3.7 va al final de §1.1.3**, después de «1.1.3.6. LLM, RAG y diseño ético para comunicación
ciudadana», y antes de §1.1.4.

**Las entradas nuevas del glosario van en orden alfabético** dentro de su apartado, intercaladas
con las existentes, no al final en bloque. Es lo que hace el documento hoy y hay que mantenerlo.

## Extensión

El capítulo actual tiene ~6 530 palabras. El resultado debe estar entre **8 200 y 9 000 palabras**:
§1.1.3.7 aporta unas 1 000 y las doce entradas de glosario unas 700.

Si te quedas corto, §1.1.3.7 no cubre sus cinco apartados. Si te pasas mucho, probablemente
metiste resultados o describiste la arquitectura del sistema.

**Verifica al final que el capítulo sigue superando el mínimo de diez páginas** que exige el
manual. Con esta extensión lo supera holgadamente.

## Antes de entregar

Recorre el checklist de `05_CONTRATO_DE_SALIDA.md` punto por punto. Si algo no lo cumples, dilo en
el registro de cambios en lugar de disimularlo.
