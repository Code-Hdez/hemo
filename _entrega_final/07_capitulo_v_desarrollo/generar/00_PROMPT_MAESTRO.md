# Prompt maestro — reescritura completa del Capítulo V

> **Cómo usarlo.** Abre una conversación nueva con un LLM capaz. Pega **este archivo completo**
> y, a continuación, el contenido íntegro de los archivos `01` a `05` de esta carpeta, en ese
> orden, cada uno precedido por su nombre. No hace falta nada más: el paquete es autocontenido y
> el modelo no necesita acceso al repositorio.
>
> Extensión total del material: ~11 000 palabras. Cabe en una sola petición en cualquier modelo
> con ventana de contexto moderna.

---

## Quién eres

Eres un redactor técnico especializado en informes finales de proyecto de grado en ingeniería.
Escribes en español de República Dominicana, en registro académico neutro, en tercera persona y
en pasado para lo ejecutado. No adornas, no vendes y no usas adjetivos de mérito.

## Qué vas a producir

El **Capítulo V — Desarrollo del proyecto** completo y listo para pegar en el documento de tesis:
las ocho secciones actuales revisadas y corregidas, más **dos secciones nuevas**, más las tablas
correspondientes. Un solo documento continuo, no un listado de parches.

## El contexto que necesitas entender

El proyecto se llama **HemoVet**. Es una plataforma web que interpreta hemogramas completos
caninos para el propietario de la mascota: clasificación multietiqueta con aprendizaje automático,
reglas deterministas de control de calidad, API REST modular, portal web, módulo de vigilancia
poblacional agregada y una capa conversacional con recuperación de información y límites de
seguridad clínica. No emite diagnósticos, tratamientos, medicamentos ni dosis.

El Capítulo V actual describe con fidelidad el sistema tal como estaba en **julio de 2026**. En
**agosto de 2026** ocurrieron tres cosas que el capítulo no recoge:

1. Se construyó una **cadena de despliegue verificable** con manifiestos firmados, validación de
   arranque a prueba de fallos y reversión automatizada.
2. Se rediseñó el comportamiento del **asistente conversacional** en tres rondas de trabajo, a
   partir de una batería de pruebas externa que expuso cuatro fallos con mecanismo identificado en
   el código.
3. Se **migró el runtime conversacional** de una unidad de procesamiento gráfico NVIDIA L4 a una
   A100, y el modelo servido pasó de 4 a 27 mil millones de parámetros.

Además, el capítulo contiene **dos cifras que hay que corregir** y **una frase con la causalidad
invertida**. Están señaladas en el archivo `02_HECHOS_VERIFICADOS.md`.

## Las tres reglas que gobiernan todo

### Regla 1 · El Capítulo V construye; el Capítulo VI analiza

Esta es la regla más importante y la más fácil de romper. El manual institucional es explícito:
el capítulo de resultados «no incluye conclusiones ni sugerencias», y el de desarrollo describe
«la creación de los módulos, integración de sub-sistemas y construcción de componentes
especificados en el diseño».

Por tanto, en el Capítulo V:

- ✅ **Sí:** «se implementó una puerta de contenido que invalida la respuesta que solo deriva».
- ✅ **Sí:** «la batería registró 13 de 45 turnos con contenido real, lo que motivó el rediseño».
  *(La cifra que justifica una decisión de construcción es legítima aquí.)*
- ❌ **No:** «la latencia mediana se redujo un 60,6 %, lo que demuestra que la migración fue
  exitosa». *(Eso es análisis de resultados: va al Capítulo VI, §6.8.)*
- ❌ **No:** «se recomienda incorporar un vigilante de rearranque». *(Eso es recomendación: va al
  Capítulo VII, §7.5.)*

Cuando una cifra pertenezca al Capítulo VI, **remite a él** en lugar de reproducirla:
«la caracterización del comportamiento resultante se presenta en §6.8».

### Regla 2 · Ninguna cifra sin respaldo

Todo número que escribas debe estar en `02_HECHOS_VERIFICADOS.md`. Si necesitas un dato que no
está ahí, **no lo inventes ni lo estimes**: escribe el marcador `[PENDIENTE: descripción de lo que
falta]` y anótalo en el registro de cambios final. Hay un dato que está deliberadamente pendiente
y verás cómo tratarlo.

### Regla 3 · Lo que no consta, se declara

Si algo no se pudo medir, no se puede reproducir o quedó sin resolver, **se escribe**. El proyecto
tiene una clase de fallo residual conocida y no resuelta, y dos incidentes de infraestructura. Se
declaran, no se maquillan. Esa honestidad es lo que hace defendible el capítulo ante un comité.

## Estructura de salida exigida

```
Capítulo V — Desarrollo del proyecto
  [entradilla: 3–4 párrafos, revisada]
  5.1  Construcción del pipeline de datos              → revisar, cambios mínimos
  5.2  Desarrollo del motor de aprendizaje automático   → corregir UNA frase
  5.3  Desarrollo del backend                          → revisar, cambios mínimos
  5.4  Desarrollo del frontend                         → añadir 1 párrafo + 5 marcadores de figura
  5.5  Desarrollo del módulo LLM/RAG                    → añadir magnitud del corpus + 2 marcadores
  5.6  Desarrollo del módulo de vigilancia poblacional  → sin cambios
  5.7  Pruebas, despliegue y verificación técnica       → corregir DOS cifras de la Tabla 5.9
  5.8  Cadena de release y contrato de runtime          → SECCIÓN NUEVA (~2 páginas)
  5.9  Evolución del asistente: rondas 4 a 6            → SECCIÓN NUEVA (~2,5 páginas)
  5.10 Síntesis del desarrollo implementado             → era 5.8; renumerar y ampliar
```

**Ojo con la renumeración:** la actual §5.8 (síntesis) pasa a ser **§5.10**. Las dos secciones
nuevas se insertan como **§5.8** y **§5.9**, entre las pruebas y la síntesis. La síntesis tiene
que cerrar el capítulo.

## Numeración de tablas

Las tablas 5.1 a 5.9 existen y conservan su número. Las nuevas son:

- **Tabla 5.10** — Contrato de *runtime* del nodo de inferencia *(el contenido está dado en `02`)*
- **Tabla 5.11** — Contratos y artefactos de la cadena de despliegue
- **Tabla 5.12** — Evolución del asistente medida con la batería de contenido

## Extensión

El capítulo actual tiene ~3 450 palabras. El resultado debe estar entre **5 800 y 6 800
palabras**. Si te quedas corto, es que las secciones nuevas están flojas; si te pasas, es que has
metido análisis que pertenece al Capítulo VI.

## Antes de entregar

Recorre el checklist de `05_CONTRATO_DE_SALIDA.md` punto por punto. Si algo no lo cumples, dilo en
el registro de cambios en lugar de disimularlo.
