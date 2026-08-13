# Guion del cambio — uno solo, y dónde va

> Este es el guion más corto de los nueve paquetes, porque el encargo lo es. **Hay un solo cambio
> de contenido en todo el bloque.**
>
> El resto de este archivo no explica qué escribir: explica **qué no tocar y cómo verificar que no
> se tocó**. En un bloque sano, esa es la parte difícil.

---

## Mapa de intervención

| Sección | Qué se hace | Origen | Tamaño |
| :--- | :--- | :--- | :--- |
| Limitaciones del proyecto | Añadir una limitación al final | `02` §1 | 1 párrafo |
| Todo lo demás | **Reproducir literal** | — | — |

---

## La limitación nueva

**Va al final de la lista de limitaciones**, continuando el formato que el documento ya usa. Si
las limitaciones actuales están numeradas, numérala; si van con ordinales en prosa, sigue con el
ordinal que corresponda; si son párrafos sueltos, añade un párrafo.

**Mira cómo está escrito el bloque y sigue ese patrón.** Es la instrucción más importante de este
archivo: una limitación con formato distinto del resto se ve inmediatamente.

### Qué dice y qué no dice

El párrafo declara cuatro cosas, en este orden:

1. El componente conversacional **necesita** aceleración por unidad de procesamiento gráfico para
   dar tiempos de respuesta aceptables.
2. El equipo **no tiene** ese hardware, así que se contrata en la nube en modalidad interrumpible.
3. Esa modalidad **puede ser reclamada sin aviso**, y durante el desarrollo se registró un evento
   real de agotamiento de capacidad zonal.
4. En consecuencia, la disponibilidad continua **queda fuera del control del equipo** y el proyecto
   no contempla alta disponibilidad para ese componente.

**Lo que deliberadamente no dice:** cuánto tarda el arranque en frío, ni que no hay mecanismo
automático de rearranque. Esos detalles operativos van a §2.6.1 y §7.3, donde tienen consecuencias
prácticas. Aquí sobrecargarían el párrafo.

### El registro

Las limitaciones del documento están escritas **sin disculpas y sin dramatismo**: declaran el
hecho y su consecuencia, y ahí terminan. La nueva sigue ese patrón.

> ❌ No añadas frases del tipo «no obstante, el impacto es limitado» ni «esto no compromete los
> resultados». El lector técnico saca esa conclusión solo, y ponerla por escrito convierte una
> declaración en una defensa.

---

## Lo difícil: no tocar el resto

En un bloque sano, el trabajo del redactor consiste en resistirse. Estas son las tres tentaciones
concretas, en orden de probabilidad:

### 1 · «Actualizar» el planteamiento inicial de la solución 🔴

Es la más peligrosa. El texto describe la solución **sin mencionar ninguna tecnología**, y eso no
es un descuido: es exactamente lo que el manual (p. 5) exige de esa sección.

Un redactor que sepa que el sistema usa un modelo de veintisiete mil millones de parámetros sobre
una A100 tenderá a «corregir» el texto para que lo refleje. **Eso lo rompería.**

**Verifica:** busca XGBoost, Ollama, ChromaDB, FastAPI, React, Qwen, A100, Google Cloud en esa
sección. **Ninguno puede aparecer.**

### 2 · Reformular los objetivos

Son cinco cuando el manual recomienda un máximo de cuatro. Es una recomendación, no una
prohibición, y los cinco están demostrados como cumplidos en la Tabla 7.1 —que es lo que el manual
exige de verdad—. Fundir dos obligaría a reescribir §7.2 y debilitaría esa tabla.

**Reprodúcelos literales.** La decisión de dejarlos en cinco ya está tomada y está razonada en
`02` §2.

### 3 · Mejorar la redacción de los antecedentes

Están bien escritos y bien citados. Cualquier retoque arrastra dos riesgos: mover una cita de
sitio y desplazar la numeración.

**Regla práctica:** si un cambio no está en el mapa de intervención de arriba, no se hace.

---

## Sobre las citas

Las citas `[n]` de este bloque están numeradas por orden de aparición y resueltas contra la
bibliografía. **Reprodúcelas con su número actual, en su sitio exacto.**

La limitación nueva **no lleva cita**: describe una condición del proyecto, no una afirmación de
la literatura.

> ⚠️ Este bloque está al principio del documento, así que sus citas son las de numeración más
> baja. Alterar una desplazaría toda la bibliografía. Es el punto del documento donde una
> modificación descuidada hace más daño.

---

## Verificación final

Tres comprobaciones, todas rápidas:

1. **Cuenta las palabras.** El bloque actual tiene ~2 020; el resultado debe estar entre 2 150 y
   2 300. Fuera de esa horquilla significa que se reescribió texto que iba íntegro.
2. **Cuenta las limitaciones.** Tiene que haber exactamente una más que antes.
3. **Cuenta las citas.** Tiene que haber las mismas, con los mismos números.
