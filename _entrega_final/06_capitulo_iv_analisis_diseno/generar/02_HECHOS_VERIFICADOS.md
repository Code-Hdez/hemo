# Hechos verificados — la única fuente de datos para el Capítulo IV

> Este capítulo describe diseño, así que necesita pocas cifras y muchos invariantes. Lo que hay
> aquí son sobre todo **decisiones de diseño con su razón**, ya redactadas.
>
> **[MEDIDO]** leído directamente del código o de un artefacto · **[PENDIENTE]** no disponible:
> usar marcador, **nunca** estimar.
>
> Verificado el 12 de agosto de 2026 sobre la rama `main`, commit `f9deedb`.

---

## 1 · §4.2.5 — El diseño de despliegue que falta 🔴

### Lo que dice hoy, y que sigue siendo cierto

> «La implementación se realizó con Docker Compose. En fase de desarrollo, el frontend y el
> backend están disponibles en la red local, y en producción se integra un proxy que incluye
> terminación HTTPS. La topología de producción reenvía todo el tráfico `/api/v1/*` al backend y
> utiliza una configuración especial para el comportamiento de *streaming* de SSE […]
>
> El arranque del sistema considera dependencias estrictas: PostgreSQL y ChromaDB deben estar
> saludables, la ingesta RAG debe completarse con al menos un *chunk* aprobado, el modelo de
> Ollama debe estar disponible y el backend debe ejecutar migraciones antes de iniciar.»

**Todo eso se conserva íntegro.** Lo que falta es la mitad del diseño de despliegue que existe hoy.

### Los tres párrafos que hay que añadir tras el segundo

> «El despliegue de producción se organiza en dos nodos con responsabilidades separadas. El nodo
> de aplicación aloja el proxy con terminación TLS, el frontend, el backend, la base de datos
> relacional y el índice vectorial. El nodo de inferencia aloja exclusivamente el servidor de
> modelos de lenguaje sobre una unidad de procesamiento gráfico. Ambos se comunican mediante una
> dirección interna estática, de modo que el reemplazo del hardware de inferencia es transparente
> para el backend: la migración de la unidad L4 a la A100 se realizó heredando la dirección, sin
> modificar una sola línea del backend.
>
> El estado desplegable se describe mediante un manifiesto de versión firmado que fija, con su
> compendio criptográfico, cada componente: imágenes del backend y del frontend, imagen del
> servidor de modelos, identidad y cuantización del modelo de lenguaje, configuración del proxy,
> paquete de arranque del nodo de inferencia, y huella del índice vectorial junto con la revisión
> del corpus que lo originó. El manifiesto es el contrato entre lo que se construyó y lo que se
> ejecuta.
>
> El arranque del nodo de inferencia es a prueba de fallos. Antes de atender tráfico valida, en
> dos capas independientes, el modelo de unidad gráfica presente, la versión del controlador, la
> versión del servidor de modelos y el compendio del modelo, contrastándolos con el manifiesto. Si
> cualquiera de esas comprobaciones no se satisface, el nodo **se apaga** en lugar de operar en
> modo degradado. Esta decisión de diseño se validó de forma no planificada durante la migración:
> la cadena de validación estaba anclada al modelo de unidad gráfica anterior y apagó la máquina
> dos veces antes de que se ampliara el contrato, comportándose exactamente como estaba diseñada.
> El diseño contempla asimismo un procedimiento automatizado de reversión a la versión anterior,
> que mantiene activa la validación.»

> **Sobre la excepción a la Regla 3.** El tercer párrafo narra un hecho en pasado y es
> deliberado: los dos apagados son **la evidencia de que la decisión de diseño opera**, y sin
> ellos el párrafo sería una declaración de intenciones. Es la única cronología admitida en el
> capítulo.

### La figura recomendada

La figura actual del despliegue es una captura de pantalla. Con el diseño ampliado conviene un
**diagrama de despliegue** propiamente dicho —que el manual pide explícitamente para esta
titulación— con los dos nodos, la dirección interna estática, el flujo de validación de arranque y
la rama de apagado ante fallo.

**No puedes producirlo.** Déjalo como:

> `[FIGURA PENDIENTE 4.7]`
>
> *Figura 4.7. Diagrama de despliegue de HemoVet: nodo de aplicación y nodo de inferencia, con el
> flujo de validación de arranque y la rama de apagado ante fallo de validación.*

---

## 2 · §4.2.4 — Los cuatro componentes del diseño conversacional que faltan 🔴

El diseño actual describe la cadena: autenticación → verificación de pertenencia → clasificación
determinista del ámbito → recuperación semántica → construcción del mensaje → generación →
validación de salida. **Es correcto y se conserva**, pero está incompleto.

### Los párrafos que hay que añadir

> «**Puerta de contenido.** La validación de salida incorpora una comprobación de sustancia: una
> respuesta que únicamente contiene la derivación al veterinario se considera inválida. La
> comprobación descuenta previamente las cláusulas de incapacidad y el eco de la pregunta, de modo
> que ninguna de las dos cuenta como contenido. Esta puerta corrige un modo de fallo silencioso
> del diseño anterior, en el que una respuesta vacía satisfacía todas las validaciones de forma
> vacua, incluido el requisito de derivación, que quedaba cumplido por construcción precisamente
> cuando la respuesta **era** solo la derivación.
>
> **Completado determinista desde la base de datos.** Todo dato que el sistema ya tiene registrado
> se responde por código y no por generación: el valor, la unidad, el intervalo de referencia y el
> estado del parámetro consultado; los extremos de una serie y su resumen de cambios; el
> inventario del historial; los patrones y hallazgos registrados; la fecha, el laboratorio, el
> analizador y la lista de parámetros del estudio; la frase de derivación y la lista de preguntas
> sugeridas para la consulta veterinaria. El completado se verifica con los mismos comparadores
> que emplea el validador de salida, y actúa **reparando únicamente la parte deficiente de la
> respuesta**, sin regenerarla entera. El principio de diseño es que la información que consta en
> la base de datos no debe depender de la generación probabilística.
>
> **Resolución de elipsis y seguimientos.** Las preguntas con sujeto omitido se expanden a su forma
> autónoma antes de clasificarse, de modo que la clasificación de ámbito y las validaciones de
> seguridad operan sobre el enunciado completo y no sobre el fragmento. Un seguimiento sin
> evidencia positiva de estar fuera de dominio continúa por la vía educativa en lugar de caer al
> rechazo por omisión.
>
> **Instrumentación de la verificación de citas.** La comprobación de implicación textual entre la
> afirmación generada y el fragmento citado registra su puntuación y sus tiempos de espera,
> generando la telemetría necesaria para calibrar el umbral de aceptación de fuentes.»

> ⚠️ **La altitud de estos cuatro párrafos ya está resuelta:** están escritos en clave de decisión
> de diseño y de invariante, no de historia de desarrollo. **Reprodúcelos así.** La narración de
> cómo se llegó ahí —qué batería lo detectó, en qué ronda se corrigió— va al Capítulo V, §5.10. No
> la dupliques.

---

## 3 · §4.2.5 — La referencia cruzada rota 🟡

Tres textos distintos para la misma figura:

| Dónde | Qué dice |
| :--- | :--- |
| Cuerpo de §4.2.5 | «La **Figura 4.5** muestra la topología lógica de despliegue» |
| Pie de la figura contigua | «**Figura 4.6.** Estado de despliegue verificado en Google Cloud» |
| Lista de Figuras | «Figura 4.5 — Secuencia de consulta al módulo LLM/RAG» y «Figura 4.6 — Diagrama de despliegue lógico de HemoVet» |

**Tres textos, tres versiones.** Corrección:

- En el cuerpo, la referencia pasa a **Figura 4.6**.
- El título se unifica en los tres sitios. **Título propuesto:** *Diagrama de despliegue lógico de
  HemoVet.* Es el que usa la Lista de Figuras y el que describe mejor lo que se ve.
- Anótalo en el registro de cambios, porque la Lista de Figuras se actualiza aparte.

---

## 4 · §4.1.4 — Dos requerimientos no funcionales nuevos

El RNF-06 actual —comprobaciones de estado separadas para cada componente— cubre la
observabilidad, pero no la naturaleza interrumpible del nodo de inferencia.

> **Filas para añadir a la Tabla 4.4:**
>
> | RNF-07 | Tolerancia a la interrupción del nodo de inferencia | El nodo de inferencia opera sobre una instancia interrumpible. La indisponibilidad del servicio conversacional no debe impedir el análisis hematológico, la consulta de resultados ni el historial, que permanecen operativos. |
>
> | RNF-08 | Integridad del *runtime* servido | Toda respuesta conversacional debe proceder del modelo declarado en el manifiesto de versión vigente, verificable por su compendio en el registro de la respuesta. |

> **RNF-07 es un requisito que el sistema ya cumple por diseño**, porque la capa conversacional
> está aislada del resto. Vale la pena reclamarlo: es una de las propiedades más sólidas de la
> arquitectura y hoy no aparece en ninguna parte del documento.

---

## 5 · §4.2.6 — Contratos API

La Tabla 4.6 es correcta y su criterio —fijar el contrato a nivel de grupo funcional, no de ruta
exacta— es una buena decisión de diseño que conviene mantener y decir en voz alta.

Dos añadidos menores:

### Nota al pie con la magnitud verificable

| Dato | Valor | Marca |
| :--- | ---: | :---: |
| Módulos de dominio del backend | **12** | MEDIDO |
| Rutas declaradas bajo `/api/v1` | **40** | MEDIDO |
| Migraciones de base de datos | 15 | MEDIDO |

> Nota propuesta: «El backend declara doce módulos de dominio y cuarenta rutas bajo el prefijo
> `/api/v1`, además de las comprobaciones de estado, que quedan fuera del prefijo funcional.»

Los doce módulos coinciden con los que describe §4.2.1: es una comprobación cruzada que el
capítulo pasa, y conviene que la cifra aparezca una sola vez y coherente.

### Fila para los contratos de despliegue

Son contratos versionados aunque no sean HTTP, y hoy no se reclaman:

> | Contratos de despliegue | `hemovet.release/v1`, `hemovet.gpu-startup/v1`, `hemovet.availability/v1`, `hemovet.llm-provider/v1` | Describen el estado desplegable y el arranque validado del nodo de inferencia. |

---

## 6 · §4.3 — Media frase en la síntesis

La síntesis del diseño es correcta. Conviene añadir media frase sobre **la separación del nodo de
inferencia**, porque es la decisión arquitectónica de mayor alcance de las que se añaden y una
síntesis que no la mencione queda desactualizada respecto del propio capítulo.

No reescribas la síntesis entera.

---

## 7 · Lo que NO se toca del Capítulo IV

| Sección | Estado |
| :--- | :---: |
| §4.1.1 Actores | ✅ |
| §4.1.2 Casos de uso (CU-01 … CU-09) y su figura | ✅ |
| §4.1.3 Requerimientos funcionales | ✅ |
| §4.1.5 Restricciones de alcance clínico y ético | ✅ sigue siendo el ancla ética del documento |
| §4.2.1 Diseño modular del backend y Tabla 4.5 | ✅ los 12 módulos coinciden con el código |
| §4.2.2 Flujo de análisis hematológico | ✅ |
| §4.2.3 Persistencia y modelo de datos | ✅ |
| §4.2.7 Seguridad, autenticación y privacidad | ✅ la cookie de sesión con esquema alternativo sigue siendo exacta |

**Reprodúcelos íntegros.** No resumas, no reordenes, no «mejores» la redacción.

---

## 8 · Lo que NO debe aparecer

| Prohibido | Por qué | Dónde va |
| :--- | :--- | :--- |
| «en la ronda 4/5/6 se detectó…» | Es historia de construcción | §5.10 |
| Cifras de baterías de validación | Desarrollo o resultado | §5.10 y §6.8 |
| Latencias, tasas de fallo, porcentajes de mejora | Resultados | §6.8 |
| Fechas de cuándo se incorporó cada pieza | El diseño no tiene cronología | — |
| Nombres de fichero, funciones o variables del código | Es un documento de ingeniería, no del repositorio | — |

**La excepción única:** los dos apagados de la máquina durante la migración, en §4.2.5, porque son
la evidencia de que la política de arranque a prueba de fallos opera.
