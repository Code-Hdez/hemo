# Hechos verificados — la única fuente de datos para el Capítulo II

> Toda cifra del capítulo debe salir de aquí. Cada entrada lleva su marca:
> **[MEDIDO]** leído de un artefacto · **[DERIVADO]** calculado a partir de artefactos ·
> **[PENDIENTE]** no disponible en este paquete: usar marcador, **nunca** estimar.
>
> Este capítulo tiene **más datos pendientes que ningún otro**, y es deliberado: el presupuesto
> exige cifras de facturación real que no están aquí. Ver la Regla 2 del prompt maestro.
>
> Verificado el 12 de agosto de 2026 sobre la rama `main`, commit `f9deedb`.

---

## 1 · §2.1 — La identidad del modelo conversacional

> **Texto actual, tercer párrafo:** «La capa conversacional utiliza una base de conocimiento
> curada, recuperación semántica y un modelo **Qwen3 4B** servido mediante Ollama.»

> **Reemplazo:** «La capa conversacional utiliza una base de conocimiento curada de 1 252
> documentos, recuperación semántica y un modelo **Qwen3.6 de 27 mil millones de parámetros en
> cuantización Q4_K_M**, servido mediante Ollama sobre una unidad de procesamiento gráfico NVIDIA
> A100 y sellado por su compendio criptográfico.»

Datos de apoyo, por si el párrafo los necesita:

| Campo | Valor | Marca |
| :--- | :--- | :---: |
| Documentos del corpus de conocimiento | 1 252 | MEDIDO |
| Modelo | `qwen3.6:27b-q4_K_M` | MEDIDO |
| Servidor de modelos | Ollama 0.32.6 | MEDIDO |
| Unidad de procesamiento gráfico | NVIDIA A100-SXM4-40GB, modalidad interrumpible | MEDIDO |
| Controlador / CUDA | 580.159.03 / 13.0 | MEDIDO |

---

## 2 · §2.5.1 — El presupuesto de hardware 🔴

### Lo que dice hoy la tabla

| Ítem | Especificación | Costo estimado (USD) |
| :--- | :--- | ---: |
| Laptop principal (existente) | RTX 4050 6 GB VRAM, 16 GB RAM, SSD 512 GB | 0.0 |
| Laptop respaldo (existente) | CPU 8 núcleos, 16 GB RAM, sin GPU dedicada | 0.0 |
| Almacenamiento en la nube 5 TB | Respaldo de conjuntos de datos y modelos | 0.0 |
| VPS para hosting | — | «Depende de los recursos a solicitar» |
| **Subtotal hardware** | | **0.0** |

### Los cuatro incumplimientos

El manual es explícito (p. 9): *«Tome en consideración el precio de todos los equipos, aunque los
tenga disponible y sean de su propiedad. Recuerde agregar un porcentaje para contingencia. El
presupuesto debe estar en una tabla e indicar los precios en pesos (RD) y dólares (US).»*

1. **No se valoran los equipos propios.** El manual pide precio aunque sean del equipo.
2. **No hay columna en pesos dominicanos.** El manual pide **ambas** monedas.
3. **No hay porcentaje de contingencia.**
4. **El sistema depende de una unidad de procesamiento gráfico que cuesta dinero real**, y no
   aparece en ninguna fila.

### Estructura de la tabla nueva

| Ítem | Especificación | Costo (USD) | Costo (RD$) | Observación |
| :--- | :--- | ---: | ---: | :--- |
| Laptop principal (existente) | RTX 4050 6 GB VRAM, 16 GB RAM, SSD 512 GB | `[PENDIENTE: valor de mercado]` | `[PENDIENTE]` | Propiedad del equipo; valorada según exige el manual |
| Laptop de respaldo (existente) | CPU de 8 núcleos, 16 GB RAM | `[PENDIENTE: valor de mercado]` | `[PENDIENTE]` | Propiedad del equipo |
| Almacenamiento en la nube, 5 TB | Respaldo de conjuntos de datos y modelos | 0,00 | 0,00 | Paquete estudiantil de Google |
| Máquina virtual de producción | `e2-standard-8`, zona `us-central1-c` | `[PENDIENTE: tarifa × horas]` | `[PENDIENTE]` | Créditos académicos |
| **Máquina virtual de inferencia** | **`a2-highgpu-1g` · NVIDIA A100-SXM4-40GB · modalidad interrumpible** | `[PENDIENTE: tarifa interrumpible × horas]` | `[PENDIENTE]` | **Es lo que sostiene la capa conversacional** |
| Disco persistente y registro de artefactos | Imágenes de contenedor y paquete de arranque | `[PENDIENTE: tarifa × GB-mes]` | `[PENDIENTE]` | |
| **Subtotal** | | `[PENDIENTE]` | `[PENDIENTE]` | |
| **Contingencia (10 %)** | | `[PENDIENTE]` | `[PENDIENTE]` | Exigida por el manual |
| **Total** | | `[PENDIENTE]` | `[PENDIENTE]` | |

**Añade también una nota al pie con la tasa de cambio utilizada y su fecha.** Sin ella, la columna
en pesos no es verificable.

### 🚫 No inventes las cifras: el texto debe decir de dónde salen

El único camino defendible es la facturación real. En el texto que acompaña a la tabla, declara
que los importes de cómputo proceden de la facturación del proyecto y los de equipo propio de su
valoración a precio de mercado local en la fecha indicada.

### El dato de horas de GPU que sí consta [MEDIDO]

De la campaña de medición constan **seis ventanas de encendido**:

| Ventana | Minutos | Procedencia |
| :--- | ---: | :--- |
| Fase 1 · sellado y ablación | 12,0 | registro |
| Fase 2 · canario y series crudas | 13,0 | registro |
| Batería general abortada | 2,8 | registro |
| Batería general | 3,7 | trazas |
| Baterías de hemograma e histórico | 13,0 | trazas |
| Réplica estricta | 34,4 | trazas |

> ⚠️ **Los dos grupos no se suman en un total único porque no son la misma magnitud.** Las tres
> ventanas de «registro» tienen encendido y apagado registrados. Las tres de «trazas» solo tienen
> el intervalo entre la primera y la última marca de tiempo de sus turnos, que es una **cota
> inferior**: no incluye el arranque de la máquina virtual ni la carga del modelo, que en el
> arranque en frío medido costó más de dos minutos.
>
> **Si el presupuesto usa estas cifras, tiene que decir que son cota inferior.** Y advertir que
> cubren **solo la campaña de medición**, no la operación del servicio: para el presupuesto hace
> falta el consumo total facturado.

---

## 3 · §2.5.2 — La tabla de software

> **Fila actual:** `Ollama + Qwen3 4B cuantizado | Open-source (Apache 2.0) | 0.0`

> **Reemplazo:** `Ollama 0.32.6 + Qwen3.6 27B (cuantización Q4_K_M) | Open-source (Apache 2.0) | 0,00`

**El costo de licencia sigue siendo cero y eso es correcto**: lo que cuesta es el cómputo, y eso
va en la tabla de hardware. Conviene decirlo explícitamente en el texto, porque un cero sin
explicación se lee como descuido.

> **Fila nueva para añadir:**
>
> | Controlador NVIDIA 580.159.03 + CUDA 13.0 | Gratuito (licencia del fabricante) | 0,00 |

---

## 4 · §2.5 — «Cinco categorías» y solo se presentan dos 🔴

> **Texto actual del párrafo introductorio:** «Se sistematiza en cinco categorías: hardware,
> software/licencias, datos, recursos humanos y costos operativos de despliegue.»

Solo existen §2.5.1 (hardware) y §2.5.2 (software y licencias). **Faltan tres subsecciones que el
propio texto anuncia.** Es el tipo de incoherencia que el comité detecta leyendo el índice.

**La solución es escribirlas**, no rebajar la frase. Las tres son sostenibles:

### §2.5.3 · Datos

Puede cerrarse en 0,00 con la justificación escrita —**no implícita**—: el corpus clínico se
obtuvo por convenio y el conjunto externo es de acceso abierto. Declararlo es lo que convierte un
cero en una decisión documentada.

| Concepto | Origen | Costo |
| :--- | :--- | ---: |
| Corpus clínico IDEXX | Convenio institucional | 0,00 |
| Cohorte externa Dog Aging Project | Acceso abierto | 0,00 |
| Corpus de conocimiento del asistente (1 252 documentos) | Elaboración propia | 0,00 (contabilizado en recursos humanos) |

### §2.5.4 · Recursos humanos

Horas-persona del equipo valoradas a tarifa de mercado local. **Los importes van pendientes**; la
estructura, no:

| Rol | Horas | Tarifa (USD/h) | Costo (USD) | Costo (RD$) |
| :--- | ---: | ---: | ---: | ---: |
| Desarrollo e integración | `[PENDIENTE]` | `[PENDIENTE]` | `[PENDIENTE]` | `[PENDIENTE]` |
| Ingeniería de datos y modelado | `[PENDIENTE]` | `[PENDIENTE]` | `[PENDIENTE]` | `[PENDIENTE]` |
| Validación clínica (evaluadores veterinarios) | `[PENDIENTE]` | `[PENDIENTE]` | `[PENDIENTE]` | `[PENDIENTE]` |

> El cronograma de §2.3 da los frentes de trabajo y su duración: es la base para estimar las
> horas. **Estimarlas a partir del cronograma es legítimo; inventar la tarifa, no.**

### §2.5.5 · Costos operativos de despliegue

Es el cómputo en nube, que ya se calcula en §2.5.1. Esta subsección puede remitir a esa tabla y
añadir lo que no cabe allí: tráfico de red, registro de artefactos y almacenamiento de respaldo.
**No dupliques la cifra de la GPU en dos subsecciones**: decláralo en una y remite desde la otra.

---

## 5 · §2.6.1 — El entorno de demostración 🔴

> **Texto actual:** «[…] el sistema principal se ejecutará en la VM `hemovet-prod` de Google
> Cloud, donde operan el proxy web, el frontend, el backend, PostgreSQL, ChromaDB y **Ollama sobre
> CPU**. […] **La VM `hemovet-llm-gpu` no se presentará como parte del entorno operativo mientras
> permanezca apagada y desconectada del despliegue automatizado.**»

**Ambas frases son hoy falsas.** La unidad gráfica es el camino de producción del asistente, la
máquina se renombró, y la de producción migró de zona.

> **Reemplazo completo (tres párrafos):**
>
> «La demostración se realizará en una sala de presentación con conexión estable a internet,
> proyector y equipo de respaldo. La interfaz se accede desde un navegador web. El sistema opera
> en Google Cloud sobre dos máquinas virtuales: `hemovet-prod`, en la zona `us-central1-c`, que
> aloja el proxy web con terminación TLS, el frontend, el backend, PostgreSQL y ChromaDB; y una
> segunda máquina con unidad de procesamiento gráfico NVIDIA A100-SXM4-40GB contratada en
> modalidad interrumpible, que ejecuta exclusivamente el servidor de modelos Ollama. Ambas se
> comunican por dirección interna estática, de modo que el reemplazo del hardware de inferencia
> no requiere cambios en el backend.
>
> El arranque de la máquina de inferencia es a prueba de fallos: valida el hardware, el
> controlador, la versión del servidor y el compendio del modelo contra un manifiesto firmado, y
> si cualquiera de esas comprobaciones no se satisface, la máquina se apaga en lugar de atender
> tráfico con una configuración distinta de la sellada.
>
> Se conservará una copia local de los casos de prueba y un procedimiento de contingencia. Dado
> que la instancia de inferencia es interrumpible y puede ser reclamada por el proveedor, el
> procedimiento de contingencia contempla: (i) verificar el estado de la máquina y de la carga del
> modelo con al menos treinta minutos de antelación a la demostración, dado que el arranque en
> frío medido supera los dos minutos; (ii) ejecutar una consulta de calentamiento antes de
> iniciar; y (iii) disponer de capturas de la interacción conversacional previamente registradas
> para el caso de indisponibilidad del proveedor.»

---

## 6 · §2.6.3 — Un criterio de éxito que el sistema no cumple 🔴

> **Texto actual:** «El rendimiento se considera exitoso si: los cuatro casos producen las
> etiquetas esperadas sin error; la regla MCHC se activa en el Caso D; el LLM rechaza la solicitud
> adversaria; **la latencia de respuesta por caso es inferior a 10 segundos**; y no se exponen
> identificadores reales de pacientes.»

**Ese umbral no se cumple y no se va a cumplir.** La mediana global del asistente es de 17,6 s y
la mediana pareada por caso, de 21,4 s [MEDIDO, §6.8].

El origen del problema es que **el criterio mezcla dos latencias muy distintas**: la del motor de
clasificación (28,73 ms de media) y la de la generación conversacional (decenas de segundos).

> **Reemplazo del criterio de latencia:**
>
> «(iv) la latencia del análisis hematológico —extracción, construcción de características,
> inferencia y persistencia— se mantiene por debajo de los dos segundos por caso, con una
> inferencia del motor de clasificación inferior a 40 ms; y la latencia de la respuesta
> conversacional se mantiene por debajo de los treinta segundos por turno, valor coherente con la
> mediana de 21,4 s medida sobre la configuración de producción vigente (véase §6.8);»

> **Criterio nuevo para añadir**, porque el sistema lo cumple y hoy no se reclama en ninguna
> parte:
>
> «(vi) todas las respuestas emitidas durante la demostración proceden del modelo sellado, lo que
> se verifica por el compendio registrado en cada respuesta.»

---

## 7 · §2.2.2 — La cadena de despliegue como entregable

La tabla de entregables lista los productos por cuaderno de análisis y termina en el portal web y
el módulo conversacional. Falta el entregable de despliegue verificable, que es trabajo real, está
versionado y hoy no se reclama en ninguna parte del documento.

> **Fila propuesta:**
>
> | Cadena de versiones desplegables y contrato de *runtime* | — | Manifiestos de versión firmados, conjunto de artefactos con compendios, paquete de arranque para la máquina de inferencia, validación de hardware y controlador, apagado ante fallo de validación y procedimiento de reversión verificado. | 3.2.1 |

---

## 8 · Lo que NO se toca del Capítulo II

| Sección | Estado |
| :--- | :---: |
| §2.1.1 Justificación metodológica de características y orígenes de datos | ✅ |
| §2.2.1 Delimitación funcional y criterios de aceptación | ✅ |
| §2.3 Cronograma | ✅ — solo verificar que la migración de agosto cabe en el calendario mostrado, o añadir una barra final |
| §2.4, §2.4.1 y §2.4.2 Plan de gestión de riesgos | ✅ — ver la nota siguiente |
| §2.6.2 Casos de prueba prevalidados (A, B, C, D) | ✅ siguen siendo válidos y bien elegidos |

> **Nota sobre §2.4.** La matriz de riesgos no contempla la indisponibilidad de la instancia
> interrumpible ni la deriva entre el modelo sellado y el instalado. **Esas dos filas se añaden en
> el Anexo A**, no aquí, para no duplicar. Si §2.4 reproduce la matriz completa, coordina con el
> paquete de anexos antes de tocarla; en la duda, **déjala como está y anótalo**.

---

## 9 · Datos que NO deben aparecer

| Dato prohibido | Por qué | Qué poner en su lugar |
| :--- | :--- | :--- |
| «Qwen3 4B» | El *runtime* es de 27 mil millones | `qwen3.6:27b-q4_K_M` |
| «Ollama sobre CPU» | Corre sobre A100 en máquina separada | La topología de dos nodos |
| «la VM con GPU no se presentará» | Es el camino de producción | La descripción real |
| «latencia inferior a 10 segundos» | El sistema mide 17,6–21,4 s p50 | Criterios separados: ML < 40 ms; conversación ≤ 30 s |
| Cualquier importe monetario no verificado | Un presupuesto inventado no tiene defensa | `[PENDIENTE: qué consultar]` |
| Cifras de resultado del Capítulo VI | Este capítulo propone, no reporta | Remisión «véase §6.8» |
