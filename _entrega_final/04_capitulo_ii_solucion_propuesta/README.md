# 04 · Capítulo II — Solución propuesta

**Estado: 🔴 tres bloqueantes.** El capítulo describe el proyecto y su plan de recursos. Tres de
sus secciones —presupuesto, entorno de demostración y criterios de éxito— quedaron desmentidas
por la migración de agosto y, a diferencia de los capítulos técnicos, **estas son las que el
comité evaluador lee para decidir si la demostración es viable el día de la defensa**.

Acciones: `A-II-01` … `A-II-07`.

---

## A-II-01 · §2.1 — La identidad del modelo conversacional

**Localización:** §2.1 «Definición del Proyecto», tercer párrafo.

> **Texto actual:** «La capa conversacional utiliza una base de conocimiento curada, recuperación
> semántica y un modelo **Qwen3 4B** servido mediante Ollama.»

> **Reemplazo:** «La capa conversacional utiliza una base de conocimiento curada de 1 252
> documentos, recuperación semántica y un modelo **Qwen3.6 de 27 mil millones de parámetros en
> cuantización Q4_K_M**, servido mediante Ollama sobre una unidad de procesamiento gráfico
> NVIDIA A100 y sellado por su compendio criptográfico.»

Evidencia: `../99_trazabilidad/CIFRAS_OFICIALES.md` §5.

---

## A-II-02 · 🔴 §2.5.1 — El presupuesto de hardware dice cero y no es cero

**Texto actual de la Tabla 4 (Hardware):**

| Ítem | Especificación | Costo estimado (USD) |
| :--- | :--- | ---: |
| Laptop principal (existente) | RTX 4050 6 GB VRAM, 16 GB RAM, SSD 512 GB | 0.0 |
| Laptop respaldo (existente) | CPU 8 núcleos, 16 GB RAM, **sin GPU dedicada** | 0.0 |
| Almacenamiento en la nube 5 TB | Backup de datasets y modelos | 0.0 |
| VPS para hosting | — | «Depende de los recursos a solicitar» |
| **Subtotal hardware** | | **0.0** |

El manual es explícito (p. 9): *«Tome en consideración el precio de todos los equipos, aunque los
tenga disponible y sean de su propiedad. Recuerde agregar un porcentaje para contingencia. El
presupuesto debe estar en una tabla e indicar los precios en pesos (RD) y dólares (US).»*

Tres incumplimientos, dos de ellos anteriores a la migración:

1. **No se valoran los equipos propios.** El manual pide precio aunque sean del equipo. Las dos
   laptops y el almacenamiento aparecen en 0,0 USD.
2. **No hay columna en pesos dominicanos.** El manual pide **ambas** monedas.
3. **No hay porcentaje de contingencia.**
4. **Y ahora, además: el sistema depende de una A100 que cuesta dinero real.**

### Estructura propuesta para la tabla nueva

| Ítem | Especificación | Costo (USD) | Costo (RD$) | Observación |
| :--- | :--- | ---: | ---: | :--- |
| Laptop principal (existente) | RTX 4050 6 GB VRAM, 16 GB RAM, SSD 512 GB | *valor de mercado* | *conv.* | Propiedad del equipo; valorado según el manual |
| Laptop respaldo (existente) | CPU 8 núcleos, 16 GB RAM | *valor de mercado* | *conv.* | Propiedad del equipo |
| Almacenamiento en la nube 5 TB | Respaldo de conjuntos de datos y modelos | 0,00 | 0,00 | Paquete estudiantil de Google |
| VM de producción `hemovet-prod` | `e2-standard-8`, zona `us-central1-c` | *tarifa × horas* | *conv.* | Créditos académicos |
| **VM de inferencia con GPU** | **`a2-highgpu-1g` · A100-SXM4-40GB · modalidad interrumpible** | ***tarifa spot × horas*** | *conv.* | **Nuevo. Es lo que sostiene la capa conversacional** |
| Disco persistente y registro de artefactos | Imágenes de contenedor y paquete de arranque | *tarifa × GB-mes* | *conv.* | |
| Subtotal | | | | |
| Contingencia (10 %) | | | | Exigido por el manual |
| **Total** | | | | |

### 🚫 No inventar la cifra: medirla

El único camino defendible es la facturación real. Procedimiento:

```bash
# Horas de GPU efectivamente consumidas por la campaña de medición
cat 06_analisis/tablas/tab_A1_ventanas_gpu.csv

# Facturación real del proyecto (requiere que la exportación a BigQuery esté activa)
gcloud billing accounts list
```

De la campaña de medición constan **seis ventanas de encendido**:

| Ventana | Minutos | Procedencia |
| :--- | ---: | :--- |
| 1 · Fase 1, sellado + ablación E-A | 12,0 | log |
| 2 · Fase 2, canario + arrays crudos | 13,0 | log |
| 4 · batería GENERAL abortada | 2,8 | log |
| batería GENERAL | 3,7 | trazas |
| baterías HEMOGRAMA + HISTÓRICO | 13,0 | trazas |
| réplica estricta | 34,4 | trazas |

> ⚠️ **Los dos totales no se suman en uno solo porque no son la misma magnitud.** Las tres
> ventanas «log» tienen encendido y apagado registrados; las tres «trazas» solo tienen el
> intervalo entre la primera y la última marca de tiempo de sus turnos, que es una **cota
> inferior**: no incluye el arranque de la máquina virtual ni la carga del modelo, que en el
> arranque en frío medido costó más de dos minutos. Si el presupuesto usa estas cifras, tiene que
> decir que son cota inferior.

Y esas ventanas cubren **solo la campaña de medición**, no la operación del servicio. Para el
presupuesto hace falta el consumo total facturado.

---

## A-II-03 · §2.5.2 — La fila del modelo en la tabla de software

> **Fila actual:** `Ollama + Qwen3 4B cuantizado | Open-source (Apache 2.0) | 0.0`

> **Reemplazo:** `Ollama 0.32.6 + Qwen3.6 27B (cuantización Q4_K_M) | Open-source (Apache 2.0) | 0.0`

El costo de licencia sigue siendo cero y eso es correcto —lo que cuesta es el cómputo, y eso va
en la tabla de hardware—. Pero conviene añadir una fila:

| Componente | Versión / fuente | Costo (USD) |
| :--- | :--- | ---: |
| Controlador NVIDIA 580.159.03 + CUDA 13.0 | Gratuito (licencia del fabricante) | 0,00 |

---

## A-II-04 · §2.5 — «cinco categorías» y solo se presentan dos

**Localización:** §2.5, párrafo introductorio.

> **Texto actual:** «Se sistematiza en cinco categorías: hardware, software/licencias, datos,
> recursos humanos y costos operativos de despliegue.»

Solo existen §2.5.1 (hardware) y §2.5.2 (software y licencias). Faltan **datos**, **recursos
humanos** y **costos operativos de despliegue**. Dos salidas:

- **(a) Recomendada:** añadir §2.5.3 Datos, §2.5.4 Recursos humanos y §2.5.5 Costos operativos de
  despliegue. La cuarta y la quinta son fáciles de sostener: horas-persona del equipo valoradas a
  tarifa de mercado local, y el cómputo en nube ya calculado en A-II-02. La de datos puede ser
  0,00 con la nota de que el corpus IDEXX se obtuvo por convenio y el DAP es de acceso abierto —
  pero **eso hay que escribirlo**, no dejarlo implícito.
- **(b) Mínima:** cambiar la frase a «Se sistematiza en dos categorías: hardware y
  software/licencias.»

La opción (a) es la que cumple el manual.

---

## A-II-05 · 🔴 §2.6.1 — El entorno de demostración describe un despliegue que ya no existe

> **Texto actual:** «[…] el sistema principal se ejecutará en la VM `hemovet-prod` de Google
> Cloud, donde operan el proxy web, el frontend, el backend, PostgreSQL, ChromaDB y **Ollama
> sobre CPU**. […] **La VM `hemovet-llm-gpu` no se presentará como parte del entorno operativo
> mientras permanezca apagada y desconectada del despliegue automatizado.**»

Ambas frases son hoy falsas. La GPU **es** el camino de producción del chat, la VM se renombró, y
`hemovet-prod` migró de zona.

> **Reemplazo propuesto:**
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
> procedimiento de contingencia contempla: (i) verificar el estado de la máquina y de la carga
> del modelo con al menos treinta minutos de antelación a la demostración, dado que el arranque
> en frío medido supera los dos minutos; (ii) ejecutar una consulta de calentamiento antes de
> iniciar; y (iii) disponer de capturas de la interacción conversacional previamente registradas
> para el caso de indisponibilidad del proveedor.»

Evidencia: commits `3e54b2b`, `2615712`, `f9deedb`; `deploy/gpu/validate-host.sh`,
`deploy/gpu/shutdown-on-failure.sh`, `deploy/gpu/switch-to-a100.sh`.

> ⚠️ **Pendiente operativo que afecta a la demostración.** `hemovet-prod` quedó temporalmente
> degradada a `e2-standard-4` por un evento de capacidad zonal y está pendiente devolverla a
> `e2-standard-8` (corte breve). **Hacerlo antes de la defensa, no durante.** Y la instancia
> *spot* no tiene vigilante de rearranque: si el proveedor la reclama, queda parada.
> (`RESUMEN_PARA_EQUIPO_2026-08-11.md` §6, pendientes 1 y 2.)

---

## A-II-06 · 🔴 §2.6.3 — Un criterio de éxito que el sistema no cumple

> **Texto actual:** «El rendimiento se considera exitoso si: los cuatro casos producen las
> etiquetas esperadas sin error; la regla MCHC se activa en el Caso D; el LLM rechaza la
> solicitud adversaria; **la latencia de respuesta por caso es inferior a 10 segundos**; y no se
> exponen identificadores reales de pacientes.»

Ese umbral **no se cumple y no se va a cumplir**. La mediana global del chat sobre A100 es de
17,6 s, y la mediana pareada por caso es de 21,4 s. Dejar escrito un criterio de éxito que la
propia tesis demuestra incumplido, cuatro capítulos más adelante, es un regalo al comité.

El origen del problema es que el criterio mezcla dos latencias muy distintas: la del motor de
clasificación (28,73 ms de media) y la de la generación conversacional (decenas de segundos).

> **Reemplazo propuesto del criterio de latencia:**
>
> «(iv) la latencia del análisis hematológico —extracción, construcción de características,
> inferencia y persistencia— se mantiene por debajo de los dos segundos por caso, con una
> inferencia del motor de clasificación inferior a 40 ms; y la latencia de la respuesta
> conversacional se mantiene por debajo de los treinta segundos por turno, valor coherente con la
> mediana de 21,4 s medida sobre la configuración de producción vigente (véase §6.9);»

Y añadir un criterio que hoy no está y que el sistema sí cumple, porque es una de sus garantías
más fuertes:

> «(vi) todas las respuestas emitidas durante la demostración proceden del modelo sellado, lo que
> se verifica por el compendio registrado en cada respuesta.»

---

## A-II-07 · §2.2.2 — La cadena de despliegue como entregable

**Localización:** §2.2.2 «Pipeline de desarrollo y entregables», tabla de entregables.

La tabla lista los entregables por *notebook* (NB01…NB08) y termina en el portal web + LLM/RAG.
Falta el entregable de despliegue verificable, que es trabajo real, está versionado y hoy no se
reclama en ninguna parte del documento.

> **Fila propuesta:**
>
> | Cadena de release y contrato de *runtime* | — | Manifiestos de versión firmados, conjunto de artefactos con compendios, paquete de arranque para la máquina de inferencia, validación de hardware y controlador, apagado ante fallo de validación y procedimiento de reversión verificado. | 3.2.1 |

Evidencia: `deploy/releases/` (manifiestos `hemovet.release/v1`, conjuntos de artefactos y
resúmenes de RAG por revisión), `deploy/gpu/` (contrato `hemovet.gpu-startup/v1`,
`rollback-release.sh`, `reconcile-release.sh`, `validate-host.sh`, `validate-runtime.sh`).

---

## Lo que NO hay que tocar del Capítulo II

- §2.1.1 Justificación metodológica de características y orígenes de datos. ✅
- §2.2.1 Delimitación funcional y criterios de aceptación. ✅
- §2.3 Cronograma. ✅ (verificar solo que la migración de agosto cabe en el calendario mostrado, o
  añadir una barra final)
- §2.4 Plan de gestión de riesgos y §2.4.1–§2.4.2. ✅ — pero ver la nota siguiente.
- §2.6.2 Casos de prueba prevalidados (A, B, C, D). ✅ Siguen siendo válidos y bien elegidos.

> **Nota sobre §2.4 y el Anexo A.** La matriz de riesgos no contempla el riesgo de
> indisponibilidad de la instancia interrumpible ni el de deriva entre el modelo sellado y el
> instalado (el 4B sigue presente en el servidor). Dos filas nuevas, con su plan de respuesta,
> cierran el hueco. Detalle en `../10_referencias_anexos/README.md`.

## Checklist de cierre de este bloque

- [ ] §2.1 con la identidad correcta del modelo.
- [ ] Tabla de hardware recalculada, con columna en RD$, valoración de equipos propios, línea de
      GPU y contingencia.
- [ ] Tabla de software con Ollama 0.32.6 y el modelo correcto, más la fila de controlador/CUDA.
- [ ] §2.5.3, §2.5.4 y §2.5.5 añadidas (o corregida la frase de «cinco categorías»).
- [ ] §2.6.1 reescrita con la topología real y el procedimiento de contingencia.
- [ ] §2.6.3 con criterios de latencia separados y el criterio de identidad de modelo.
- [ ] §2.2.2 con el entregable de despliegue.
- [ ] `hemovet-prod` devuelta a `e2-standard-8` antes de la defensa.
