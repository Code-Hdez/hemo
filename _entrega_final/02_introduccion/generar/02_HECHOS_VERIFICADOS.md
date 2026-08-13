# Hechos verificados — la única fuente de datos para este bloque

> Este bloque apenas necesita datos: plantea el problema, no lo mide. Lo que hay aquí es **el
> texto de la limitación que falta** y las verificaciones de coherencia que conviene hacer.
>
> **[MEDIDO]** leído directamente de un artefacto · **[PENDIENTE]** no disponible: usar marcador.
>
> Verificado el 12 de agosto de 2026 sobre la rama `main`, commit `f9deedb`.

---

## 1 · La limitación que falta 🔴

**Localización:** sección «Limitaciones del proyecto», **al final de la lista**, continuando el
formato que ya usa el documento.

> **Texto para añadir:**
>
> «El componente conversacional del sistema requiere aceleración por unidad de procesamiento
> gráfico para operar con tiempos de respuesta aceptables. El equipo no dispone de hardware propio
> con esa capacidad, por lo que dicho componente se ejecuta sobre una instancia de cómputo con
> unidad de procesamiento gráfico contratada bajo la modalidad interrumpible, cuya disponibilidad
> depende de la capacidad excedente del proveedor de nube y puede ser reclamada sin previo aviso.
> Durante el desarrollo se registró además un evento real de agotamiento de capacidad zonal que
> impidió temporalmente el arranque de varias familias de máquinas. En consecuencia, la
> disponibilidad continua de la capa conversacional queda fuera del control del equipo y el
> proyecto no contempla un esquema de alta disponibilidad para dicho componente.»

### Por qué esta limitación y no otra

El manual pide en esta sección los elementos que «pueden afectar al desarrollo del proyecto siempre
que el estudiante no tenga el control por fuerzas mayores», y da como ejemplo textual **«restricción
por capacidad informática del equipo»**. El caso es literalmente ese.

### Qué sostiene esta limitación en el resto del documento

No es un párrafo aislado. Es el que da fundamento a tres pasajes posteriores:

| Sección | Qué depende de esta limitación |
| :--- | :--- |
| §2.6.1 | El procedimiento de contingencia del entorno de demostración |
| §7.3 | La undécima limitación, sobre la instancia interrumpible |
| §7.7 | El párrafo de sostenibilidad económica del *runtime* |

Sin ella declarada aquí, las tres aparecen de la nada en la segunda mitad del documento.

### Los hechos que respaldan el párrafo

| Hecho | Marca |
| :--- | :---: |
| El nodo de inferencia opera sobre una instancia interrumpible | MEDIDO |
| El proveedor puede reclamar la capacidad sin previo aviso | — (condición del servicio) |
| Durante el desarrollo se registró un evento real de agotamiento de capacidad zonal | MEDIDO |
| El sistema no dispone de mecanismo automático de rearranque | MEDIDO |
| El arranque en frío del nodo supera los dos minutos | MEDIDO |

> El párrafo propuesto **no menciona** el tiempo de arranque en frío ni la ausencia de rearranque
> automático. Es deliberado: aquí basta declarar que la disponibilidad queda fuera del control del
> equipo. El detalle operativo va a §2.6.1 y §7.3, donde tiene consecuencias.

---

## 2 · La nota de riesgo sobre los objetivos ⚠️

**Esto no es un cambio: es una decisión que conviene conocer antes de tocar nada.**

El manual dice, textual: *«se recomienda un mínimo de dos (2) y máximo cuatro (4)»* objetivos
específicos. **El documento tiene cinco: OE1 a OE5.**

Es una **recomendación**, no una prohibición. Y los cinco están demostrados como cumplidos en la
Tabla 7.1, que es lo que el manual exige de verdad: «todos los objetivos específicos enunciados
deben de demostrarse completados en el proyecto».

> **Recomendación: no tocar.** Fundir OE4 (vigilancia) con OE3 (portal) para bajar a cuatro
> debilitaría la Tabla 7.1 y obligaría a reescribir §7.2. El coste de dejarlo en cinco es, como
> máximo, un comentario del asesor; el coste de fundirlos es reescribir tres secciones.
>
> Si el asesor lo exige, la fusión de menor daño es **OE3 + OE4** bajo «portal ciudadano con
> visualización individual y comunitaria».

**Para el encargo: reproduce los cinco objetivos tal cual.** No los fundas, no los reordenes, no
los reformules.

---

## 3 · Verificación cruzada de objetivos y evidencia

No es un cambio en este bloque, pero conviene comprobarlo antes de dar el documento por cerrado.
Estado al 12 de agosto de 2026:

| Objetivo | Evidencia declarada en §7.2 | ¿Sigue vigente? |
| :--- | :--- | :---: |
| OE1 · corpus estructurado | Corpus IDEXX + 1 301 registros del Dog Aging Project + 43 características | ✅ |
| OE2 · modelo multietiqueta | 7 etiquetas, PR-AUC 0,9529, κ 0,629 | ✅ |
| OE3 · portal ciudadano | Aplicación con resumen, carga, revisión, resultado, historial, biblioteca y chat, más usabilidad con n = 44 | ✅ |
| OE4 · vigilancia comunitaria | Reporte poblacional funcional | ⚠️ la sección de resultados que lo demuestra **no existía**: se resuelve con §6.6 |
| OE5 · capa conversacional con límites de seguridad | Seguridad 30/30, exactitud 83,3 %, κ 0,841, inyección de instrucciones de 61 a 1 fallo | ⚠️ cifras de julio: se actualizan con §6.8 |

Las dos casillas de advertencia **se resuelven en el Capítulo VI**, no aquí. Este bloque no las
menciona ni las anticipa.

---

## 4 · La propiedad que hay que preservar activamente 🔴

**«Planteamiento inicial de la solución» no menciona ninguna tecnología, y eso es un acierto que
hay que conservar.**

El manual (p. 5) pide que esa sección explique la solución **sin** entrar en algoritmos,
componentes ni tecnologías concretas. Está verificado: el texto actual no menciona XGBoost, ni
Ollama, ni ningún modelo, ni ningún proveedor de nube.

Es el tipo de propiedad que se pierde sin querer cuando un redactor «actualiza» un texto para que
refleje el sistema real. **Aquí no hay que actualizar nada.**

| Término | ¿Puede aparecer en el planteamiento? |
| :--- | :---: |
| XGBoost, Ollama, ChromaDB, FastAPI, React | ❌ no |
| Qwen3.6, A100, Google Cloud | ❌ no |
| «modelo de aprendizaje automático», «asistente conversacional» | ✅ sí, son descripciones funcionales |

En la **sección de limitaciones**, en cambio, sí es correcto mencionar la unidad de procesamiento
gráfico y la modalidad de contratación: es una restricción de infraestructura, no un planteamiento
de solución.

---

## 5 · Lo que NO se toca

| Sección | Estado |
| :--- | :---: |
| Antecedentes del problema | ✅ exacto y bien citado |
| Antecedentes del proyecto | ✅ |
| Descripción del problema | ✅ |
| Planteamiento inicial de la solución | ✅ **y sin tecnologías: preservar** |
| Objetivos (general y los cinco específicos) | ✅ reproducir literal |
| Justificación (conveniencia, relevancia social, implicaciones prácticas, valor teórico) | ✅ |
| Las limitaciones existentes | ✅ **íntegras**; solo se añade una |

**Reprodúcelos literales**, con sus citas `[n]` en sus números actuales.

---

## 6 · Lo que NO debe aparecer

| Prohibido | Por qué |
| :--- | :--- |
| Cualquier cifra de resultado o de latencia | Este bloque plantea, no reporta |
| Nombres de tecnología en el planteamiento de la solución | El manual lo prohíbe y el texto hoy lo cumple |
| Cualquier mención a que falta la sección §6.6 | Es un problema del Capítulo VI, no de aquí |
| Renumeración de citas | Rompería la bibliografía de todo el documento |
| Un sexto objetivo, o la fusión de dos existentes | Ver la nota de riesgo del punto 2 |
