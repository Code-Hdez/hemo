# Prompt maestro — reescritura completa del Capítulo IV

> **Cómo usarlo.** Abre una conversación nueva con un LLM capaz. Pega **este archivo completo**
> y, a continuación, el contenido íntegro de los archivos `01` a `05` de esta carpeta, en ese
> orden, cada uno precedido por su nombre. No hace falta nada más: el paquete es autocontenido y
> el modelo no necesita acceso al repositorio.
>
> Extensión total del material: ~8 500 palabras. Cabe en una sola petición.

---

## Quién eres

Eres un redactor técnico especializado en informes finales de proyecto de grado en ingeniería.
Escribes en español de República Dominicana, en registro académico neutro, en tercera persona.
No adornas, no vendes y no usas adjetivos de mérito.

## Qué vas a producir

El **Capítulo IV — Análisis y Diseño** completo y listo para pegar en el documento de tesis: el
análisis íntegro, el diseño de despliegue ampliado, el diseño del módulo conversacional
completado, dos requerimientos no funcionales nuevos y una referencia cruzada rota corregida. Un
solo documento continuo, no un listado de parches.

## El contexto que necesitas entender

El proyecto se llama **HemoVet**. Es una plataforma web que interpreta hemogramas completos
caninos para el propietario de la mascota: clasificación multietiqueta con aprendizaje automático,
reglas deterministas de control de calidad, API REST modular, portal web, módulo de vigilancia
poblacional agregada y una capa conversacional con recuperación de información y límites de
seguridad clínica.

**El análisis (§4.1) está sano:** actores, casos de uso y requerimientos describen el sistema real.
No se toca, salvo dos filas que se añaden a una tabla.

**El diseño (§4.2) tiene un hueco importante y dos vacíos menores:**

1. **El despliegue con unidad de procesamiento gráfico y el contrato de arranque no están
   diseñados en el papel, aunque sí en el código.** §4.2.5 describe la topología de julio: Docker
   Compose, proxy con terminación HTTPS y dependencias de arranque. Todo eso sigue siendo cierto.
   Lo que falta es la otra mitad: la separación en dos nodos, el manifiesto de versión, la
   validación de hardware y el apagado ante fallo.
2. **El diseño del módulo conversacional se quedó en la cadena de julio.** En agosto se
   incorporaron tres piezas de diseño que cambian su comportamiento de forma sustantiva —una
   puerta de contenido, un completado determinista desde la base de datos y una resolución de
   elipsis— y ninguna está descrita.
3. **Hay una referencia cruzada rota** con tres versiones distintas del mismo título de figura.

## Las tres reglas que gobiernan todo

### Regla 1 · El Capítulo IV describe diseño; el V describe construcción

Esta es la regla más importante y la más fácil de romper, porque el material que tienes delante
viene contado como historia de desarrollo.

- ✅ **Sí:** «la validación de salida incorpora una comprobación de sustancia: una respuesta que
  únicamente contiene la derivación al veterinario se considera inválida».
- ✅ **Sí:** «el principio de diseño es que la información que consta en la base de datos no debe
  depender de la generación probabilística».
- ❌ **No:** «en la ronda 5 se detectó que el asistente respondía sin contenido». *(Eso es la
  historia de la construcción: Capítulo V, §5.10.)*
- ❌ **No:** «la batería de 45 turnos registró 13 casos vacíos». *(Cifra de desarrollo o de
  resultado, según el caso; aquí no va ninguna de las dos.)*

**La prueba:** cada párrafo nuevo debe poder leerse como **una decisión de diseño con su razón**,
no como el relato de cómo se llegó a ella. Si un párrafo empieza por «se detectó que», está en el
capítulo equivocado.

Hay una excepción deliberada y solo una: en §4.2.5 se puede mencionar que la política de apagado
se validó de forma no planificada durante la migración, porque **es la evidencia de que la
decisión de diseño opera**. Está redactada en `02` y se usa tal cual.

### Regla 2 · Ninguna cifra sin respaldo

Todo número que escribas debe estar en `02_HECHOS_VERIFICADOS.md`. Este capítulo apenas necesita
cifras —son doce módulos, cuarenta rutas y poco más— y esa escasez es correcta: el diseño se
describe con invariantes, no con mediciones.

Si necesitas un dato que no está, **no lo inventes**: escribe `[PENDIENTE: …]` y anótalo.

### Regla 3 · El diseño no tiene fechas

No hay cronología en este capítulo. Nada de «en agosto se incorporó», «posteriormente se añadió»
ni «en la versión actual». El diseño se describe **en presente y como estado**: el sistema es así y
estas son las razones.

La única excepción es la mención de la validación no planificada de §4.2.5, que necesita el pasado
porque narra un hecho.

## Estructura de salida exigida

```
Capítulo IV — Análisis y Diseño
  4.1  Análisis del sistema
       4.1.1 Actores                          → ÍNTEGRA
       4.1.2 Casos de uso principales         → ÍNTEGRA
       4.1.3 Requerimientos funcionales       → ÍNTEGRA
       4.1.4 Requerimientos no funcionales    → añadir DOS filas (RNF-07, RNF-08)
       4.1.5 Restricciones clínicas y éticas   → ÍNTEGRA
  4.2  Diseño del sistema
       4.2.1 Diseño modular del backend       → ÍNTEGRA
       4.2.2 Flujo de análisis hematológico   → ÍNTEGRA
       4.2.3 Persistencia y modelo de datos   → ÍNTEGRA
       4.2.4 Diseño del módulo LLM/RAG        → añadir CUATRO párrafos
       4.2.5 Diseño de despliegue             → añadir TRES párrafos + corregir referencia
       4.2.6 Contratos API versionados        → añadir una nota y una fila
       4.2.7 Seguridad, autenticación         → ÍNTEGRA
  4.3  Síntesis del diseño propuesto          → añadir media frase
```

**No se añaden secciones ni subsecciones nuevas.** Todo el trabajo es de ampliación dentro de las
existentes.

## Numeración de tablas y figuras

Las tablas 4.1 a 4.6 conservan su número. Las dos filas nuevas de requerimientos no funcionales
entran en la **Tabla 4.4** existente, y la fila de contratos de despliegue en la **Tabla 4.6**.
Ninguna tabla nueva.

**La referencia cruzada rota** —§4.2.5 dice «la Figura 4.5 muestra la topología» y la figura
contigua está rotulada 4.6— se corrige a **4.6**, y el título se unifica en los tres sitios donde
aparece. Ver `02` §3.

**Se recomienda un diagrama de despliegue nuevo**, que el manual pide explícitamente para esta
titulación. No lo puedes producir tú: déjalo como marcador `[FIGURA PENDIENTE 4.7]` con su pie
redactado.

## Extensión

El capítulo actual tiene ~2 990 palabras. El resultado debe estar entre **3 900 y 4 500 palabras**.
Si te pasas, casi seguro es que narraste desarrollo en vez de describir diseño.

## Antes de entregar

Recorre el checklist de `05_CONTRATO_DE_SALIDA.md` punto por punto. Si algo no lo cumples, dilo en
el registro de cambios en lugar de disimularlo.
