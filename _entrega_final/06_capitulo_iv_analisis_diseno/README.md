# 06 · Capítulo IV — Análisis y diseño

**Estado: 🟡** El análisis (§4.1) está sano: actores, casos de uso y requerimientos describen el
sistema real. El diseño (§4.2) tiene un hueco importante —**el despliegue con GPU y el contrato
de arranque no están diseñados en el papel, aunque sí en el código**— y dos vacíos menores en el
diseño del módulo conversacional.

Acciones: `A-IV-01` … `A-IV-05`.

---

## A-IV-01 · 🔴 §4.2.5 — El diseño de despliegue se quedó en la topología de julio

**Texto actual (íntegro, son tres párrafos cortos):**

> «La implementación se realizó con Docker Compose. En fase de desarrollo, el frontend y el
> backend están disponibles en la red local, y en producción se integra un proxy que incluye
> terminación HTTPS. La topología de producción reenvía todo el tráfico `/api/v1/*` al backend y
> utiliza una configuración especial para el comportamiento de *streaming* de SSE […]
>
> El arranque del sistema considera dependencias estrictas: PostgreSQL y ChromaDB deben estar
> saludables, la ingesta RAG debe completarse con al menos un *chunk* aprobado, el modelo de
> Ollama debe estar disponible y el backend debe ejecutar migraciones antes de iniciar.»

Todo eso sigue siendo cierto. Lo que falta es **la mitad del diseño de despliegue que existe
hoy**: la separación en dos máquinas, el contrato de versión, la validación de hardware y el
apagado ante fallo.

> **Párrafos propuestos para añadir tras el segundo:**
>
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

Evidencia: `deploy/gpu/validate-host.sh`, `deploy/gpu/validate-runtime.sh`,
`deploy/gpu/shutdown-on-failure.sh`, `deploy/gpu/hemovet-gpu-failure-shutdown.service`,
`deploy/gpu/rollback-release.sh`, `deploy/gpu/reconcile-release.sh`,
`deploy/gpu/gpu-runtime-release-v1.schema.json`, `deploy/releases/`.

### Figura recomendada

La Figura 4.6 actual («Estado de despliegue verificado en Google Cloud») es una captura. Con el
diseño ampliado conviene añadir un **diagrama de despliegue** —que el manual pide explícitamente
para ICC (p. 11: «Diagrama de despliegue (ICC)»)— con los dos nodos, la dirección interna
estática, el flujo de validación de arranque y la rama de apagado ante fallo.

---

## A-IV-02 · §4.2.5 — Referencia cruzada rota

> **Texto actual:** «La **Figura 4.5** muestra la topología lógica de despliegue.»
> Y la figura inmediatamente siguiente está rotulada **«Figura 4.6. Estado de despliegue
> verificado en Google Cloud»**.

Además, la Lista de Figuras dice que la Figura 4.5 es «Secuencia de consulta al módulo LLM/RAG» y
la 4.6 «Diagrama de despliegue lógico de HemoVet», mientras que el pie de la 4.6 en el cuerpo dice
«Estado de despliegue verificado en Google Cloud». **Tres textos, tres versiones.** Unificar.

---

## A-IV-04 · 🔴 §4.2.4 — Faltan tres componentes del diseño conversacional

El diseño actual describe la cadena: autenticación → verificación de pertenencia → clasificación
determinista del ámbito → recuperación semántica → construcción del *prompt* → generación →
validación de salida. Correcto, pero incompleto: en agosto se incorporaron tres piezas de diseño
que cambian el comportamiento del módulo de forma sustantiva.

> **Párrafos propuestos para añadir:**
>
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
> rechazo por omisión.»

Y una cuarta, menor pero verificable:

> «**Instrumentación de la verificación de citas.** La comprobación de implicación textual entre
> la afirmación generada y el fragmento citado registra su puntuación y sus tiempos de espera,
> generando la telemetría necesaria para calibrar el umbral de aceptación de fuentes.»

Evidencia: `backend/app/modules/llm_chat/`, `backend/scripts/nli_support_verifier.py`,
`backend/scripts/cascade_support_verifier.py`, `backend/scripts/evaluate_support_bench.py`,
`RESUMEN_PARA_EQUIPO_2026-08-11.md` §2.

> **Ojo con la altitud.** El Capítulo IV describe **diseño**, no construcción. Los párrafos de
> arriba están escritos en clave de decisión de diseño y de invariante, no de historia de
> desarrollo. La narración de cómo se llegó ahí —qué batería lo detectó, en qué ronda se
> corrigió— va al Capítulo V (§5.10). No duplicar.

---

## A-IV-03 · §4.1.4 — Requerimientos no funcionales sin el riesgo de infraestructura

**Localización:** Tabla 4.4.

El RNF-06 («Disponibilidad operativa: *healthchecks* separados para backend, RAG, Chroma, Ollama
y base de datos») cubre la observabilidad, pero no la naturaleza interrumpible del nodo de
inferencia.

> **Filas propuestas:**
>
> | RNF-07 | Tolerancia a la interrupción del nodo de inferencia | El nodo de inferencia opera sobre una instancia interrumpible. La indisponibilidad del servicio conversacional no debe impedir el análisis hematológico, la consulta de resultados ni el historial, que permanecen operativos. |
> | RNF-08 | Integridad del *runtime* servido | Toda respuesta conversacional debe proceder del modelo declarado en el manifiesto de versión vigente, verificable por su compendio en el registro de la respuesta. |

RNF-07 es además un requisito que el sistema **ya cumple por diseño**, porque la capa
conversacional está aislada del resto: vale la pena reclamarlo.

---

## A-IV-05 · §4.2.6 — Contratos API

La Tabla 4.6 es correcta y su criterio —fijar el contrato a nivel de grupo funcional, no de ruta
exacta— es una buena decisión que conviene mantener. Dos añadidos menores:

- Nota al pie con la magnitud verificable: **12 módulos de dominio y 40 rutas declaradas bajo
  `/api/v1`**, más los *healthchecks* fuera del prefijo funcional.
- Una fila para los contratos de despliegue, que también son contratos versionados aunque no sean
  HTTP:

> | Contratos de despliegue | `hemovet.release/v1`, `hemovet.gpu-startup/v1`, `hemovet.availability/v1`, `hemovet.llm-provider/v1` | Describen el estado desplegable y el arranque validado del nodo de inferencia. |

---

## Lo que NO hay que tocar del Capítulo IV

- §4.1.1 Actores. ✅
- §4.1.2 Casos de uso (CU-01…CU-09) y la Figura 4.1. ✅
- §4.1.3 Requerimientos funcionales. ✅
- §4.1.5 Restricciones de alcance clínico y ético. ✅ — sigue siendo el ancla ética del documento.
- §4.2.1 Diseño modular del backend y Tabla 4.5. ✅ Los 12 módulos coinciden con el código.
- §4.2.2 Flujo de análisis hematológico. ✅
- §4.2.3 Persistencia y modelo de datos. ✅
- §4.2.7 Seguridad, autenticación y privacidad. ✅ La cookie `hemovet_session` HttpOnly con
  esquema `Bearer` alternativo sigue siendo exacta.
- §4.3 Síntesis del diseño. ✅ — solo conviene añadir media frase sobre la separación del nodo de
  inferencia.

## Checklist de cierre de este bloque

- [ ] §4.2.5 ampliada con los tres párrafos de despliegue en dos nodos, manifiesto y arranque a
      prueba de fallos.
- [ ] Diagrama de despliegue actualizado (dos nodos + validación de arranque + rama de apagado).
- [ ] Referencia cruzada Figura 4.5/4.6 corregida y unificada con la Lista de Figuras.
- [ ] §4.2.4 ampliada con puerta de contenido, completado determinista, resolución de elipsis e
      instrumentación de citas.
- [ ] RNF-07 y RNF-08 añadidos a la Tabla 4.4.
- [ ] Nota de magnitud y fila de contratos de despliegue en §4.2.6.
- [ ] Verificado que ningún párrafo nuevo narra desarrollo en vez de diseño.
