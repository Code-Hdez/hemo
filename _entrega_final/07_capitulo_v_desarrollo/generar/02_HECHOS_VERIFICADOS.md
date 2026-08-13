# Hechos verificados — la única fuente de cifras para el Capítulo V

> Toda cifra del capítulo debe salir de aquí. Cada entrada lleva su marca:
> **[MEDIDO]** leído directamente de un artefacto · **[DERIVADO]** calculado a partir de artefactos
> · **[PENDIENTE]** no disponible: usar marcador, **nunca** estimar.
>
> Verificado el 12 de agosto de 2026 sobre la rama `main`, commit `f9deedb`.

---

## 1 · Correcciones obligatorias sobre el texto actual

### 1.1 · La cifra inválida de la Tabla 5.9 🔴

La tercera fila de la Tabla 5.9 dice hoy:

> `Guardrails LLM/RAG | 50/50 adversariales rechazados; 20/20 legítimos aceptados`

**Esa cifra es inválida.** Procede de un artefacto que se descartó, y contradice frontalmente lo
que el Capítulo VI reporta en §6.4.2. Los valores correctos son:

| Indicador | Valor correcto | Marca |
| :--- | ---: | :---: |
| Solicitudes adversariales rechazadas | **31 / 40 (77,5 %)** | MEDIDO |
| Consultas legítimas aceptadas | **15 / 20 (75,0 %)** | MEDIDO |
| Consultas fuera de ámbito con mensaje claro | 17 / 30 (56,7 %) | MEDIDO |

Redacción sugerida para la fila: *«Ámbito y seguridad del asistente | 31/40 solicitudes
adversariales rechazadas (77,5 %); 15/20 consultas legítimas aceptadas (75,0 %) | Validación de
alcance conversacional sobre el flujo de producción. El análisis detallado se desarrolla en
§6.4.2.»*

### 1.2 · Las pruebas de backend 🔴 [PENDIENTE]

La Tabla 5.9 dice `25 passed, 114 warnings in 1.45s`. **Esa cifra está desactualizada:** hoy el
directorio de pruebas contiene **35 archivos de test** [MEDIDO], incluidos varios que no existían
cuando se escribió: contrato de manifiesto de versión, arranque del nodo con GPU, topología de
composición, reversión, contrato de entorno de despliegue, aceptación de etapa 10, retención de
conversaciones y humo del chat.

**La cifra real de pruebas que pasan no está disponible en este paquete.** Escribe:

> `[PENDIENTE: salida literal de la suite de pruebas del backend, con su fecha de ejecución]`

y anótalo en el registro de cambios. **No escribas 25, ni 35, ni ningún número inventado.** La
suite se ejecuta en cinco tandas separadas y el dato debe copiarse literal.

### 1.3 · La frase con la causalidad invertida

En §5.2, párrafo tercero, el texto dice hoy:

> «Se incluyó la etiqueta PATRON_ANEMIA_REGENERATIVA **porque** solo había seis casos positivos en
> el conjunto de prueba; por ello se consideró un resultado exploratorio con escaso respaldo.»

Dice literalmente que la etiqueta se incluyó *a causa de* tener pocos casos. Es lo contrario de lo
que ocurrió. Corregir a:

> «Se mantuvo la etiqueta PATRON_ANEMIA_REGENERATIVA entre las salidas oficiales **pese a** contar
> únicamente con seis casos positivos en el conjunto de prueba, dada su relevancia clínica; por esa
> razón se declara como resultado exploratorio con escaso respaldo estadístico.»

---

## 2 · Identidad del runtime conversacional

El Capítulo V actual **no menciona** el modelo de lenguaje ni el hardware. Otras secciones del
documento dicen «Qwen3 4B sobre CPU», que es **falso**. Lo que corre en producción:

| Campo | Valor | Marca |
| :--- | :--- | :---: |
| Modelo | Qwen3.6 de 27 mil millones de parámetros, cuantización Q4_K_M (`qwen3.6:27b-q4_K_M`) | MEDIDO |
| Compendio del modelo | `a50eda8ed977ab48…` | MEDIDO |
| Tamaño | 17 420 432 739 bytes = 16,224 GiB = 17,420 GB | MEDIDO |
| Servidor de modelos | Ollama **0.32.6** | MEDIDO |
| Unidad de procesamiento gráfico | NVIDIA **A100-SXM4-40GB**, modalidad interrumpible | MEDIDO |
| Controlador / CUDA | 580.159.03 / 13.0 | MEDIDO |
| Ventana de contexto por petición | 16 384 tokens (la A100 admite hasta 65 536) | MEDIDO |
| Atención rápida / caché de claves y valores | activada / `q8_0` | MEDIDO |
| Paralelismo / persistencia en memoria | 1 / residente | MEDIDO |
| Verificación de identidad por respuesta | 115 de 115 respuestas del modelo sellado; 0 de otro | MEDIDO (censo) |
| Modelos instalados en el nodo | **2**: el sellado y el anterior de 4 mil millones, que sigue presente | MEDIDO |

> ⚠️ **Matiz que debe quedar escrito:** el modelo anterior sigue instalado en el servidor y la
> comprobación presente en el código **no impide su uso**. Se verificó posteriormente que ninguna
> respuesta procede de él, pero la garantía es de verificación, no de imposibilidad por diseño.
> Es una limitación operativa real.

> ⚠️ Dos correcciones que la medición impuso sobre lo que el equipo creía: el peso real es
> 17 420 432 739 bytes, **no** los 16,93 GB que se habían declarado; y el servidor es **0.32.6**,
> no 0.32.5.

---

## 3 · La cadena de despliegue (material para §5.8)

### 3.1 · Manifiesto de versión

Cada estado desplegable se materializa en un manifiesto firmado que fija, **por compendio
criptográfico**: imagen del backend, imagen del frontend, imagen del servidor de modelos,
identidad y cuantización del modelo de lenguaje, configuración del proxy, paquete de arranque del
nodo de inferencia, y huella del índice vectorial junto con la revisión exacta del corpus que lo
originó. [MEDIDO]

### 3.2 · Contrato de runtime del nodo de inferencia — contenido para la Tabla 5.10

| Campo del contrato | Valor |
| :--- | :--- |
| Versión del contrato | `hemovet.gpu-runtime-release/v1` |
| Contrato de origen | `hemovet.release/v1` |
| Identificador de versión | `515d343ac8057779…` |
| Momento de aplicación | Próximo arranque del nodo |
| Modificación en caliente | No permitida |
| Estado inicial | Pendiente de validación de arranque |
| Imagen del servidor de modelos (compendio) | `b526b1d4bc30d0cc…` |
| Contrato de arranque | `hemovet.gpu-startup/v1` |
| Paquete de arranque (compendio) | `5b6419fcd4f1bd62…` |
| Modelo de lenguaje | `qwen3.6:27b-q4_K_M` |
| Compendio del modelo | `a50eda8ed977ab48…` |
| Cuantización | `Q4_K_M` |

Nota al pie obligatoria de esa tabla: *«Los compendios se muestran truncados a 16 caracteres; el
valor íntegro consta en el repositorio del proyecto.»*

### 3.3 · Contratos y artefactos — contenido para la Tabla 5.11

| Contrato o artefacto | Qué fija |
| :--- | :--- |
| `hemovet.release/v1` | Estado desplegable completo, por compendio |
| `hemovet.gpu-startup/v1` | Paquete y secuencia de arranque del nodo de inferencia |
| `hemovet.availability/v1` | Contrato de disponibilidad de los servicios |
| `hemovet.llm-provider/v1` | Contrato del proveedor de generación |
| Conjunto de artefactos de modelo | Artefactos de aprendizaje automático por versión |
| Resumen de corpus | Huella del índice vectorial y revisión del corpus que lo originó |

### 3.4 · Validación de arranque a prueba de fallos

Antes de atender tráfico, el nodo de inferencia valida en **dos capas independientes**: el modelo
de unidad de procesamiento gráfico presente, la versión del controlador, la versión del servidor de
modelos y el compendio del modelo, contrastándolos con el manifiesto. Si cualquier comprobación no
se satisface, **el nodo se apaga** en lugar de operar en modo degradado. [MEDIDO]

### 3.5 · Reversión

El procedimiento de reversión a la versión anterior está automatizado y **mantiene activa la
validación**. Está cubierto por pruebas automatizadas de contrato. [MEDIDO]

### 3.6 · La migración como prueba no planificada del diseño

Al sustituir la unidad de procesamiento gráfico, la cadena de validación —anclada al modelo de
hardware anterior en sus dos capas— **apagó la máquina en dos ocasiones**, comportándose
exactamente como estaba diseñada. Se amplió el contrato para admitir ambos modelos manteniendo la
validación de la reversión, se regeneró el manifiesto, y el paquete de arranque se instaló mediante
intervención sobre el disco fuera de línea. [MEDIDO]

La dirección interna del nodo de inferencia se promovió a estática y se heredó en el nodo nuevo, de
modo que **el backend no requirió ninguna modificación**. [MEDIDO]

### 3.7 · Incidente de capacidad zonal

Durante la migración se produjo un **agotamiento real de capacidad en la zona** que impidió el
arranque de varias familias de máquinas. El nodo de aplicación quedó temporalmente en una
configuración reducida. [MEDIDO] — Declararlo como desviación; el manual pide que se expliquen.

### 3.8 · Topología

Dos nodos con responsabilidades separadas. Nodo de aplicación: proxy con terminación TLS,
frontend, backend, base de datos relacional e índice vectorial. Nodo de inferencia: exclusivamente
el servidor de modelos sobre la unidad de procesamiento gráfico. Comunicación por dirección interna
estática. [MEDIDO]

---

## 4 · La evolución del asistente (material para §5.9)

### 4.1 · El instrumento que expuso el problema

Una batería externa de **45 turnos** en tres modos de uso midió algo que las baterías anteriores no
medían: **si la respuesta contiene contenido sustantivo después de descontar el andamiaje**. La
batería se verificó como válida antes de aceptar sus conclusiones.

Resultado inicial: **13 de 45 turnos con contenido real**, **0 de 15 en el modo historial**, y
turnos que devolvían un código de éxito HTTP con únicamente la frase de derivación al veterinario.
[MEDIDO]

### 4.2 · Los cuatro mecanismos exactos del fallo

Esto es el núcleo de la sección: no fueron cuatro síntomas, fueron cuatro causas localizadas en el
código.

1. **Ninguna validación exigía sustancia.** Una respuesta con una sola afirmación de tipo
   conversacional superaba todas las comprobaciones de forma vacua, y el requisito de derivación
   quedaba satisfecho **por construcción** justamente cuando la respuesta *era* solo la derivación.
2. **El clasificador de ámbito operaba sobre el fragmento, no sobre el enunciado expandido.** Las
   preguntas elípticas —«¿de qué está compuesto?», «¿para qué sirven?»— caían al rechazo por
   omisión y se descartaban, aun cuando la validación de seguridad sí se aplicaba sobre la forma
   expandida.
3. **El hallazgo del historial correspondía al estudio equivocado.** Los estudios llegan en orden
   cronológico ascendente y el mecanismo de respaldo tomaba la primera observación no cubierta, de
   modo que un estudio antiguo sin patrones sombreaba el hallazgo del estudio más reciente.
4. **Instrucciones en conflicto.** La instrucción para consultas con estudio seleccionado o
   historial presuponía la existencia de un parámetro solicitado y terminaba induciendo la
   derivación; para preguntas sin parámetro, el modelo emitía únicamente la frase de cierre.

### 4.3 · Qué se construyó

**Puerta de contenido.** La validación de salida incorpora una comprobación de sustancia: la
respuesta que solo deriva es inválida. La comprobación descuenta previamente las cláusulas de
incapacidad («no puedo confirmar») y el eco de la pregunta («me preguntas si…»), de modo que
ninguna cuenta como contenido.

**Completado determinista desde la base de datos.** Principio rector, textual del proyecto: *todo
lo que la base de datos ya sabe se responde desde la base de datos, y se arregla solo la parte
dañada de la respuesta, nunca se regenera entera*. Sale por código, a costo de cómputo cero,
verificado con los mismos comparadores que emplea el validador:

- el valor, la unidad, el intervalo de referencia y el estado del parámetro consultado;
- los extremos de una serie y el resumen de cambios (por ejemplo: «RBC: subió de 7,84 a 8,93
  10^12/L; el más reciente está alto»);
- el inventario del historial: número de estudios y sus fechas;
- los patrones y hallazgos registrados, **encabezando** la respuesta; y si no hay nada anormal, la
  declaración honesta de que no hay hallazgos registrados más la precaución de vigilar signos;
- la fecha, el laboratorio, el analizador y la lista de parámetros del estudio;
- la frase de derivación faltante y la lista de preguntas sugeridas para la consulta veterinaria.

**Resolución de elipsis y seguimientos.** El resolutor expande las preguntas con sujeto omitido y
las de propiedad («¿qué unidad tiene?» resuelve el parámetro recordado); el clasificador opera
sobre el enunciado autónomo; y un seguimiento sin evidencia positiva de estar fuera de dominio
continúa por la vía educativa.

**Reparación compacta con guardas de raíz.** Para lo que sí se regenera: negar la derivación o
declarar una incapacidad falsa **obliga a reescribir la respuesta entera**, porque completarla
enmascararía el error.

**Instrumentación.** La verificación de implicación textual de cada cita registra su puntuación y
sus tiempos de espera —la evidencia que faltaba para calibrar el umbral de aceptación de fuentes—.
Y se añadió poda de disco activada por presión de ocupación (≥ 70 %), tras dos incidentes reales
de disco lleno.

### 4.4 · Evolución medida — contenido para la Tabla 5.12

| Métrica | Corrida inicial | Ronda 6 | Configuración vigente |
| :--- | ---: | ---: | ---: |
| Turnos con contenido real | 13/45 | 44/45 | 40/45 |
| Turnos sin respuesta | 1 (+13 vacíos) | 1 | **0** |
| Mediana global de latencia | ~46 s | 44 s | **17,6 s** |
| Modo con estudio seleccionado, mediana | 32 s | 68 s | **17,6 s** |
| Modo historial con datos | 0/15 | 15/15 | 12/15 |
| Peor turno | 118 s | 161 s | **65 s** |

[MEDIDO] · **Uso permitido:** esta tabla documenta la evolución de la construcción y es legítima
en el Capítulo V. **No la interpretes**: no escribas que la migración «fue exitosa» ni calcules
porcentajes de mejora. El análisis va en §6.8.

### 4.5 · La clase residual, declarada

Los cuatro o cinco turnos flojos por corrida son la variabilidad de las reparaciones que agotan
los intentos y recurren al último recurso. **Es una clase de fallo conocida, documentada y no
resuelta.** El modelo se conservó entre rondas: cuando responde, es exacto — todas las fallas eran
del sistema, no del modelo. [MEDIDO]

---

## 5 · Datos para completar las secciones existentes

### 5.1 · Corpus de conocimiento (para §5.5)

| Dato | Valor | Marca |
| :--- | :--- | :---: |
| Documentos Markdown curados | **1 252** | MEDIDO |
| Organización | material de origen, micro-fichas, políticas, revisiones expertas, manifiestos | MEDIDO |
| Modelo de *embeddings* | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | MEDIDO |
| Esquema del índice | `hemovet-rag-v2` | MEDIDO |
| Trazabilidad | cada versión desplegada registra la huella del índice y la revisión del corpus | MEDIDO |

### 5.2 · Backend (para §5.3, confirmatorio)

| Dato | Valor | Marca |
| :--- | :--- | :---: |
| Módulos de dominio | 12 | MEDIDO |
| Rutas declaradas bajo `/api/v1` | 40 | MEDIDO |
| Migraciones de esquema | 15 | MEDIDO |

Los doce módulos que la Tabla 5.4 ya lista **coinciden exactamente con el código**. No hay que
tocar esa tabla.

### 5.3 · Frontend (para §5.4)

La duplicación histórica de implementaciones **se resolvió**: hay una única implementación activa
con 95 ficheros versionados, y la obsoleta se retiró del control de versiones. [MEDIDO]

Redacción sugerida para el cierre de la sección:

> «Durante el desarrollo coexistieron dos implementaciones del portal. La duplicación se resolvió
> consolidando una única implementación activa y retirando la obsoleta del control de versiones,
> con el fin de eliminar la ambigüedad sobre qué código se despliega.»

### 5.4 · Rendimiento de inferencia del clasificador (§5.7, ya correcto)

Media 28,73 ms · p50 27,93 ms · p95 33,9 ms · p99 137,95 ms · n = 1 000 solicitudes · 50
iteraciones de calentamiento · medición sin capa HTTP, autenticación, base de datos ni recuperación
semántica. [MEDIDO] — **Estas cifras están bien y no se tocan.**

### 5.5 · Vigilancia poblacional (§5.6, ya correcto)

Cohorte de 200 registros, ventana de 30 días, estado global de advertencia, cinco compuertas
técnicas aprobadas, tres señales aprobadas y dos en advertencia por falta de geocodificación.
[MEDIDO] — **Sección correcta, no se toca.**

---

## 6 · Marcadores de figura a insertar

El capítulo actual tiene cinco figuras, todas salidas de aprendizaje automático (`image15` a
`image19`). **Ninguna muestra el producto funcionando**, que es el vacío más visible del documento.

Inserta marcadores en el lugar que corresponda, con su pie redactado, para que el equipo produzca
las capturas después:

| Marcador | Sección | Pie propuesto |
| :--- | :---: | :--- |
| `[FIGURA PENDIENTE 5.6]` | §5.4 | *Figura 5.6. Pantalla de resumen personal del propietario.* |
| `[FIGURA PENDIENTE 5.7]` | §5.4 | *Figura 5.7. Carga de un hemograma completo.* |
| `[FIGURA PENDIENTE 5.8]` | §5.4 | *Figura 5.8. Pantalla de revisión y corrección de los valores extraídos, previa a la confirmación del análisis.* |
| `[FIGURA PENDIENTE 5.9]` | §5.4 | *Figura 5.9. Presentación del resultado interpretativo, con los patrones activos y la advertencia de alcance.* |
| `[FIGURA PENDIENTE 5.10]` | §5.4 | *Figura 5.10. Consulta del historial de una mascota.* |
| `[FIGURA PENDIENTE 5.11]` | §5.5 | *Figura 5.11. Interacción con el asistente conversacional, con las fuentes citadas.* |
| `[FIGURA PENDIENTE 5.12]` | §5.5 | *Figura 5.12. Respuesta del asistente ante una consulta fuera de su ámbito autorizado.* |
| `[FIGURA PENDIENTE 5.13]` | §5.8 | *Figura 5.13. Secuencia de validación de arranque del nodo de inferencia.* |

Las cinco figuras actuales (`image15`–`image19`) **se conservan con su numeración 5.1 a 5.5**.
