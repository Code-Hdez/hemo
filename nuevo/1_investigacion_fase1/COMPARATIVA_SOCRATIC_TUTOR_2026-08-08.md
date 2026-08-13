# Comparativa arquitectónica — HemoVet frente a Socratic Tutor

> `cristiandlahoz/socratic-tutor` clonado en modo lectura (`--depth 20`) dentro
> del directorio de investigación. No se modificó, no se abrió PR, no se hizo
> commit. Fuente: `AGENTS.md`, `ops/inference-engine/README.md`,
> `docs/academic/memoria-conversacional.md`, `compose.yml`, `pom.xml`.

---

## 1. Los dos sistemas no son comparables en propósito, y eso importa

Socratic Tutor es un tutor socrático: su trabajo es **hacer preguntas y guiar**.
HemoVet es un explicador clínico: su trabajo es **citar cifras de laboratorio
sin inventarlas**. Esa diferencia justifica que HemoVet tenga un contrato de
salida y validadores, y Socratic Tutor no.

Por eso el ejercicio útil no es «copiar lo que hace el otro», sino identificar
**qué decisiones evitaron problemas que HemoVet sí padece**, y cuáles no serían
trasladables.

---

## 2. Tabla comparativa

| Aspecto | HemoVet | Socratic Tutor |
|---|---|---|
| Backend | Python / FastAPI | Java (`pom.xml`) + TypeScript |
| Motor de inferencia | **Ollama 0.32.5** directo | **`llama-swap`**, endpoint único compatible OpenAI, enrutando por el campo `model` |
| Modelo principal | **`qwen3.6:27b-q4_K_M` — 27,8 B** | **`ornith-9b-GGUF:UD-Q4_K_XL` — 9 B** |
| Segundo modelo | **ninguno** | **`gemma-4-E4B-it-GGUF:IQ4_XS`** |
| Uso del segundo modelo | — | **guardarraíles / clasificación de seguridad**, generación de títulos, scaffolding |
| Contexto | 16.384 | 20.000 |
| GPU | NVIDIA L4 (GCP) | DigitalOcean GPU (Ansible + systemd) |
| Memoria conversacional | `history_limit = 12` **mensajes** (= 6 pares), ventana fija | **resumen sintético + turnos recientes literales**, con compactaciones sucesivas |
| Almacenamiento | mensajes/turnos | **registro de eventos** con *proyecciones* distintas para el modelo y para la interfaz |
| Salida estructurada | **sobre JSON con claims, fact_ids, policy_rule_ids** | **no se encontró** |
| Validadores | **~18 códigos de rechazo distintos** | **no se encontraron** |
| Bucle de reparación | **sí: hasta 4 llamadas por turno** | **no se encontró** |
| Concurrencia | `-np 1`, semáforo de 1 generación | `llama-swap` multiplexa modelos |

---

## 3. Las tres decisiones que evitaron problemas de HemoVet

### 3.1 Un modelo pequeño dedicado a las tareas baratas

Socratic Tutor declara explícitamente un *side-job model* para
«low/medium-stakes support jobs: guardrails / safety classification, chat title
generation».

HemoVet hace lo contrario: el perfil `safety_guardrail` usa **el mismo 27B**.
Medido, eso significa que una pregunta como *«¿eres una persona o un asistente?»*
cuesta 19–23 s a 13 tok/s, y que rechazar una petición de dosis paga el mismo
precio que interpretar un panel de 18 analitos.

**Aplicable a HemoVet:** sí, conceptualmente. **Con dos reservas medidas:**
quedan 5,6 GB de VRAM libres —suficiente para un modelo pequeño cuantizado, pero
habría que verificar el efecto sobre el KV cache—, y trasladar la barrera de
seguridad clínica a un modelo menor **exige revalidación específica**, porque es
justamente la parte del sistema que hoy funciona bien (§6 de la auditoría: 4/4
en el chat general).

### 3.2 Memoria por compactación en vez de ventana fija

Socratic Tutor almacena **todo** el historial como registro de eventos y
presenta al modelo sólo una **proyección activa**: resumen sintético de lo
antiguo más los turnos recientes literales. Sus objetivos de diseño incluyen
explícitamente *«evitar cortes arbitrarios que separen una respuesta de la
pregunta que la originó»*.

HemoVet corta por `history_limit = 12` **mensajes** — que son 6 pares, no los 10
que pide el objetivo de producto, y que **puede partir un par por la mitad**.

**Aplicable a HemoVet:** sí, y resuelve dos problemas a la vez —el objetivo de
10 pares y el crecimiento del prefill—. Con un matiz que la evidencia de HemoVet
aporta y Socratic Tutor no necesitaba: **resumir cambia el prefijo y por tanto
invalida el context checkpoint** de 149,6 MiB que hoy sí está reutilizándose
(§6 de la investigación). Un resumen que se recalcule cada turno destruiría la
caché; uno que se recalcule cada N turnos, no.

### 3.3 No tener contrato estructurado ni bucle de reparación

Socratic Tutor no tiene structured output, validadores ni repair. Por eso **no
puede sufrir el fallo dominante de HemoVet**: 60 % de generaciones descartadas y
1,9 llamadas al modelo por pregunta.

**NO aplicable a HemoVet, y conviene decirlo con claridad.** El contrato existe
porque HemoVet cita cifras clínicas y debe poder demostrar que cada número
proviene de la base de datos. Quitarlo eliminaría la latencia y también la
garantía. La lección trasladable no es «quitar el contrato» sino **«no pagar una
segunda inferencia completa por un fallo de forma»** — que es exactamente lo que
propone el *salvage* ya escrito en el propio repositorio de HemoVet
(commit `bd70e0d8`, sin conectar).

---

## 4. Lo que NO es trasladable

| Decisión de Socratic Tutor | Por qué no aplica |
|---|---|
| Modelo de 9 B | HemoVet debe copiar cifras de un panel de 18 analitos sin equivocarse y respetar barreras clínicas. Bajar de 27 B a 9 B **exige revalidación clínica completa**, no es un cambio de configuración |
| Ausencia de validadores | Es el aporte diferencial de HemoVet y su defensa ante un tribunal |
| `llama-swap` | Resuelve multiplexado de modelos; HemoVet hoy sirve uno solo. Sólo cobra sentido si se adopta 3.1 |
| Infraestructura DigitalOcean/Ansible | HemoVet está en GCP con imágenes selladas por digest; migrar no aporta nada al problema medido |

---

## 5. Conclusión

De las tres diferencias, **la que ataca la causa dominante de HemoVet es la
tercera** —no pagar una inferencia entera por un fallo de forma—, y la solución
ya está escrita dentro del propio HemoVet sin conectar.

La primera (modelo pequeño para tareas baratas) es la segunda en interés, pero
toca la barrera de seguridad y exige validación.

La segunda (memoria por compactación) resuelve el objetivo de los 10 pares, pero
debe diseñarse **respetando el context checkpoint** que HemoVet ya está
aprovechando y Socratic Tutor no documenta.

*Ninguna de estas observaciones se ha implementado. Ver
`MATRIZ_MITIGACIONES_LLM_2026-08-08.csv` (filas 1, 5 y 7).*
