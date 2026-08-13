# HemoVet — Rondas 4 y 5: contenido real, y la reparación deja de costar la respuesta entera

**Fecha:** 9 de agosto de 2026 (noche) · **Commit:** `663094b` · **Disparador:** el
test independiente de 45 turnos (`test_domingo/pruebas_conversacion_3modos_2026-08-09`)
y los 5 ejemplos adicionales del dueño, con su mandato: *el sistema siempre debe
devolver información real — respondiendo o rechazando con sustancia — y las
restricciones que compiten entre sí se eliminan.*

---

## 0 · Lo que el test independiente enseñó (y nuestra batería no medía)

La batería del proyecto medía **errores terminales** (17/70 → 1/70 en la
jornada). El test del compañero midió otra capa: **¿la respuesta contiene algo
después de quitar el andamiaje?** Resultado: 13 de 45 turnos devolvían HTTP 200,
texto, cero errores — y nada dentro. Solo la frase de derivación y el bloque de
hallazgo del sistema. Ambas mediciones eran correctas: el sistema había
aprendido a *sobrevivir* la validación entregando sobres formalmente válidos y
clínicamente vacíos. Sobrevivir no es responder.

Las cuatro fallas, con su mecanismo exacto medido en código:

1. **Ninguna puerta exigía sustancia.** Con una sola claim CONVERSATIONAL, la
   cobertura de hechos era vacuamente válida, y las dos salidas tempranas de
   `_clinical_answer_contract` devolvían «sin fallo» sin mirar qué decía la
   respuesta. Una respuesta que era *solo* la derivación satisfacía el
   requisito de derivación por construcción. La política
   (`core_policy_es.txt`: «derivar sin aportar contenido no es responder»)
   vivía en prosa; nada la hacía cumplir.
2. **El mismo turno se clasificaba dos veces sobre textos distintos.** La
   política de seguridad evaluaba la pregunta expandida (ALLOW), pero el router
   re-clasificaba la pregunta original sin expandir; el *fallthrough* «no pude
   clasificar esto» se trataba como evidencia de fuera-de-dominio y rechazaba
   seguimientos legítimos («¿De qué está compuesto?», «¿Para qué sirven?»,
   «Explícamelo más simple», «Retomando el primer tema…»).
3. **El hallazgo del estudio equivocado en historial.** Los estudios llegan en
   orden cronológico ascendente y tanto el backstop como el prompt tomaban la
   primera observación no cubierta: el «sin patrones» del estudio viejo
   sombreaba la Policitemia (99,89 %) del reciente.
4. **Instrucciones que competían con la política.** La instrucción de
   selected/history presuponía «el parámetro solicitado» y terminaba mandando
   la derivación: ante preguntas sin parámetro (¿de qué fecha es?, ¿cuántos
   estudios hay?) el cuerpo no aplicaba y el modelo emitía solo el cierre
   obligatorio — la plantilla exacta de los turnos vacíos.

## 1 · Los cambios (todos en `663094b`)

### 1.1 La puerta de contenido real — `content_free_answer`

En turnos **ALLOW** con contexto clínico, una respuesta sin ningún dígito y sin
ninguna cláusula informativa de ≥25 caracteres que no sea la propia derivación
es **reparable**: el modelo recibe la instrucción explícita de responder con
los datos autorizados (valores, fechas, conteos, hallazgos) y que la derivación
solo puede cerrar la respuesta. Se evalúa por **cláusulas** (el mismo split del
matcher de derivación), así que una oración que trae contenido y derivación
juntos («…neutrófilos altos…; revisar el frotis con un veterinario») pasa.

Los rechazos quedan fuera a propósito: su contrato ya exige las dos ideas del
rechazo, y añadir esta puerta ahí sería crear una restricción nueva que
compite. La puerta clínica protegida (`missing_required_clinical_facts`) queda
intacta.

### 1.2 Elipsis y ámbito — los seguimientos siguen la conversación

- `_FOLLOW_UP` acepta las **preguntas con sujeto omitido** y los imperativos
  con clítico: «de qué», «para qué», «en qué», «con qué», «a qué», «cuál
  era/fue», «explícamelo», «resúmemelo», «dime más»… El sujeto elidido ES la
  anáfora: la frase es gramaticalmente incompleta sin el turno anterior.
- **«primer tema» lleva su tema elegido a la expansión**: antes el standalone
  decía `topics[-1]` mientras `referenced_parameter` decía `topics[0]` — las
  dos mitades del turno se contradecían.
- **El router clasifica el standalone** (la misma cadena que ya juzga la
  política de seguridad) para el intent funcional, y el veto del fallthrough
  OUT_OF_DOMAIN ya no aplica a seguimientos. Las ramas literales (cortesía,
  saludo, identidad, palabras clave explícitas de temas ajenos) siguen leyendo
  **lo que el usuario escribió** — la despedida en conversación clínica
  (FLU-12) sigue siendo despedida, y «¿y eso cómo lo programo en python?»
  sigue sin explicar programación (rutea a dominio mixto, que responde solo la
  parte hematológica y rechaza la externa).

### 1.3 El hallazgo del estudio reciente

`_clinical_observations` (backstop) y `PromptBuilder._extract_observations`
recorren los estudios **del más reciente al más viejo**. La Policitemia del
último estudio ya no queda sombreada por el «sin patrones» del anterior — ni
en el bloque visible ni en lo que el modelo ve junto a la pregunta.

### 1.4 Instrucciones que responden en vez de derivar (y más jugosas)

- **Selected**: las preguntas sin parámetro (fecha del estudio, cuántos
  parámetros, hallazgos registrados, qué preguntar al veterinario) se
  responden con los datos autorizados del estudio, nunca solo con derivación.
  Los valores fuera de rango se enumeran con valor, unidad y clasificación. El
  valor solicitado va acompañado de su rango de referencia, su clasificación y
  una oración breve de qué mide el parámetro (antes: «solo si el usuario los
  solicita explícitamente» — la restricción que producía respuestas secas).
- **History**: las preguntas sin parámetro (cuántos estudios, de qué fechas,
  qué hallazgos) se responden con número de estudios, fechas y hallazgos
  registrados de cada uno.
- **Educativa general**: explicación completa — qué es, qué mide o qué función
  cumple, y por qué es relevante en el perro — en vez de la mínima.

## 2 · La evaluación del modelo: se queda `qwen3.6:27b`

El mandato incluía «cambia de modelo si es necesario». No es necesario, y la
evidencia es del propio test del compañero:

- **Cuando el modelo respondió, respondió bien**: los 3 valores que citó son
  exactos contra la verdad de terreno (WBC 15.23, RBC 8.93, HCT 63.6 %), las
  clasificaciones contra rango correctas, y **cero alucinaciones en 45
  turnos**. En el ejemplo 5 del dueño comparó WBC entre fechas correctamente.
- **Las cuatro fallas eran del sistema, no del modelo**: puertas que aceptaban
  sobres vacíos, un router de regex que rechazaba elipsis, un orden de lista
  equivocado y una instrucción que mandaba derivar. Otro modelo detrás de las
  mismas puertas habría producido los mismos vacíos válidos.
- **Operativo**: la L4 (24 GB) corre el 27b-q4 con contexto 16384 a ~17 GB de
  VRAM; no cabe nada materialmente mejor sin pagar latencia. Y cambiar el
  modelo invalidaría la línea base sellada del experimento de la tesis.

## 3 · Verificación local

- **1304 tests en verde, 1 skip** (suite completa, `-p no:asyncio`), ruff
  limpio. 10 tests nuevos fijan: la puerta de contenido (plantillas vacías
  reales del test del compañero mueren; respuesta con dato + derivación pasa;
  aclaraciones pasan), las 4 elipsis rechazadas ahora rutean, «primer tema»
  expande con `topics[0]`, el guard explícito sobrevive al veto, y el backstop
  prefiere el estudio reciente.
- La suite atrapó un falso positivo real antes de desplegar: una respuesta de
  patrón en una sola oración con derivación incrustada caía en la puerta; el
  análisis por cláusulas lo corrigió.
- `detect_changes`: riesgo **MEDIUM**, 24 símbolos en los 6 archivos
  esperados, sin colaterales.

## 3-bis · Ronda 5 — arreglar solo la parte dañada, no toda la respuesta

Mandato del dueño («las reparaciones siempre tardan demasiado… enfócate en
arreglar solo la parte de la respuesta que se daña»). Tres piezas:

1. **Completado determinista** (`deterministic_completion`): cuando la única
   falla es una omisión que el backend ya tiene verificada, la respuesta se
   completa por código y **no se regenera nada**:
   - `missing_veterinary_referral` → se añade la oración de derivación
     (boilerplate, no prosa clínica). Antes: 40-80 s de regeneración para
     añadir una frase.
   - `missing_required_clinical_facts` en turnos ALLOW → se añade «Dato
     registrado del estudio H1 (fecha) — WBC: 22.4 ×10⁹/L, rango…», construido
     desde el mismo `HemogramParameter` autorizado que el validador usa para
     verificar. Mismo argumento de seguridad que el backstop de hallazgos: es
     el registro del sistema que el producto ya muestra en `case_facts`,
     no texto del modelo. Todo lo que el modelo escribió se conserva.
   - El sobre vacío con parámetro resuelto sale como dato + derivación al
     instante; la puerta `content_free_answer` queda para los vacíos sin
     parámetro (fechas, conteos), que sí exigen que el modelo redacte.
   - Los rechazos quedan fuera: corregir una premisa falsa sigue siendo
     trabajo del modelo (reparación), y el completado se verifica con los
     mismos matchers antes de aceptarse — si no cierra, cae a la reparación
     de siempre (fail-safe).
2. **Reparación compacta** (`repair_compacted`): para las clases que sí
   regeneran (`content_free_answer`, `missing_required_clinical_facts` en
   rechazos, `structured_patient_fact_coverage_missing`), la segunda
   generación ya no reenvía el prompt completo de 16k: pregunta, hechos
   implicados y el error. Sin memoria conversacional, sin historial, sin
   fuentes — y el interruptor existente de validación database-only cubre el
   caso sin fuentes retenidas. Menos prefill, reparación más corta.
3. El bloque de corrección se factorizó (`_structured_repair_block`) y la
   petición compacta lo comparte.

## 4 · Validación contra producción — el bucle batería → análisis → ajuste

Instrumento: el banco de 45 preguntas del test independiente
(`test_domingo/…/casos_45_preguntas.csv`), corrido por el mismo camino del
navegador (SSE + sesión encadenada por modo), guardando pregunta, respuesta,
etapas, razón de reparación y latencia por turno. **Contenido** se clasifica
con el criterio estricto: dígitos o una cláusula sustantiva — la derivación,
la incapacidad («no puedo confirmar») y el eco de la pregunta no cuentan.

### Turnos CON contenido real (de 15 por modo)

| Modo | Línea base (compañero) | Ronda 4 (test5) | Ronda 5 (test5) | **Ronda 5 (cuenta NUEVA)** |
|---|---:|---:|---:|---:|
| general | 8/15 (4 rechazos) | **15/15** | **15/15** | **15/15** · mediana 34 s |
| selected_hemogram | 5/15 (1 muerte) | 13/15 (2 muertes) | 13/15 (2 muertes) | **13/15** (2 muertes) · 84 s |
| hemogram_history | **0/15** | 0/15 (relleno) | 13/15 (1 muerte) | **15/15 · 0 muertes · mediana 47 s** |
| **Total** | **13/45** | 28/45 | 41/45 | **43/45** |

La corrida de cuenta nueva ejercitó el recorrido real completo en producción:
registro → residencia → creación de mascota → **dos subidas de PDF con
extracción** → análisis → chat por SSE con hilos encadenados — «sin importar
el usuario», como exige el criterio. Con los dos estudios idénticos (mismo
PDF), HIS-04 respondió con honestidad exacta: «valores iguales, no existe una
dirección de cambio temporal ni tendencia observable» — razonamiento correcto
sobre los datos reales, más los datos registrados adjuntos.

### Qué movió cada ronda (medido)

- **Ronda 4** arregló general por completo (las elipsis «¿De qué está
  compuesto?», «¿Para qué sirven?», «primer tema» responden; cero
  reparaciones, mediana 25 s) y la puerta `content_free_answer` convirtió los
  vacíos de selected en reparaciones con contenido (5→0 vacíos). Pero en
  historial la reparación también fallaba y el last-resort entregaba
  relleno: 15/15 reparando, mediana 110 s, 0/15 con datos.
- **Ronda 5** es la que abrió historial: HIS-01 entrega el inventario exacto
  («El historial autorizado contiene 2 estudios: H1 (2025-12-17), H2
  (2025-12-18)») y HIS-05 los dos extremos con valores («Los linfocitos
  bajaron de 2.86 a 2.81 x10^9/L…») — por completado determinista, sin
  regenerar. 6 turnos de historial salen limpios en ~40-60 s donde antes
  todos pagaban ~110 s de reparación.
- GEN-02, que en ronda 4 pedía «reformúlala», en ronda 5 responde con la
  explicación completa de las tres líneas celulares (el seguimiento cae a la
  ruta educativa).

### La batería de cierre (test5/`hola`, tras desplegar `585b4f8`)

```
general            14/15 contenido · 1 generation_queue_timeout (cola GPU, ruido)
selected_hemogram  15/15 contenido · 0 muertes · mediana 51 s   ← COMPLETO
hemogram_history    8/15 contenido · 0 muertes · mediana 97 s
CERO generation_repair_failed en toda la corrida (primera de las cinco)
```

- **SEL-08 respondió en 28 s** con el dato exacto («RBC: 8.93 10^12/L») —
  había muerto en las 4 corridas previas.
- **SEL-12 respondió en 51 s** con la lista limpia de preguntas — había
  muerto en TODAS las corridas medidas.
- El historial en `hola` oscila entre 8/15 y 13/15 según el sorteo de la
  lotería de reparación en las preguntas de comparación sin parámetro (la
  clase residual de la ronda 6); en la cuenta nueva salió 15/15. Ningún
  turno muere: el suelo es relleno honesto, ya no errores.

Corridas completas (pregunta, respuesta, etapas, razones, latencias) y el
runner: `validacion_llm/resultados/rondas45_2026-08-10/`.

### Los dos recurrentes, cerrados de raíz tras la última batería

- **SEL-08 «¿Qué unidad tiene?»** (murió en rondas 4 y 5): la elipsis no
  resolvía parámetro y el turno no tenía objetivo clínico. `75001fc`: la
  pregunta de propiedad (unidad, rango, fecha, valor, clasificación, estado)
  resuelve el **parámetro recordado** — solo es respondible contra él — y el
  completado determinista entrega el dato.
- **SEL-12 (preguntas para el veterinario)** — murió en TODAS las corridas
  medidas, incluida la del compañero: el modelo nombra códigos sin fact_id,
  las claims caen y la reparación nunca aterrizaba el sobre. `585b4f8`: el
  vacío de vet_questions sale como la **lista genérica de preguntas sin
  cifras ni códigos** — el registro exacto que su contrato exige.
  *`detect_changes` marcó CRITICAL en este commit por tocar
  `_clinical_answer_contract` (el hub de todo turno clínico), como el
  precedente documentado del despliegue 5 de la jornada; el cambio real es
  una rama acotada a VET_QUESTIONS+ALLOW+vacío, 1313 tests en verde.*

### La ronda 6, medida (batería guardada: `bateria_ronda6.jsonl`)

Pedida por el dueño en la misma sesión y desplegada (`a1b1286`):
el **resumen determinista de cambios por extremos**, los **hallazgos con
precaución**, el **entailment instrumentado** (cada timeout y cada veredicto
con su score quedan en logs) y el **prune de disco por presión** (≥70 % →
poda completa en `deploy-release.sh`).

Resultado en test5/`hola` — la cuenta donde vivía la lotería:

```
general            15/15 contenido · 0 reparaciones · mediana 29.8 s
selected_hemogram  14/15 contenido · mediana 68.1 s
hemogram_history   15/15 contenido · 0 muertes · 4 reparaciones · mediana 53.6 s
                   (venía de 8/15 y 97 s en esta misma cuenta)
Total: 44/45 con contenido real
```

HIS-02 «¿Qué cambió entre los estudios?» entrega ahora el resumen calculado:

> Cambios registrados entre H1 (2025-12-17) y H2 (2025-12-18):
> - RBC: subió de 7.84 a 8.93 10^12/L; el valor más reciente está alto
> - HGB: subió de 16.8 a 20.8 g/dL; el valor más reciente está alto
> - HCT: subió de 51.1 a 63.6 %; el valor más reciente está alto
> - EOS: bajó de 2.7 a 0.29 10^9/L; …dentro del rango de referencia
> - NEU: subió de 8.64 a 11.49 10^9/L; el valor más reciente está alto

La única muerte fue SEL-12 con una razón nueva
(`intent_mismatch_vet_questions`: trajo prosa pero ni una pregunta);
generalizado en `7ba094b` — sin «?» en la respuesta, la prosa se conserva y
la lista genérica cierra.

### Lo que queda señalado para la ronda 7

- **La lotería de citas**: con la instrumentación nueva, la próxima batería
  dirá si el entailment opina-y-rechaza o cae al léxico por timeout — y con
  esa evidencia se ajusta umbral o timeout (§8.1 de la jornada).
- **Verificar SEL-12** con el fix generalizado de `7ba094b` (desplegado
  después de la batería de la ronda 6) en la próxima corrida.
- Las reparaciones restantes de selected (~7-8 por corrida, medianas 68-90 s)
  son las clases de esquema/atribución preexistentes — el siguiente
  escalón de latencia si se quiere seguir bajando.

## 5 · Lo que queda

- **El last-resort sigue siendo el suelo** («en este turno no puedo
  confirmarlos»): por diseño no puede citar hechos (esquema sin ids —
  inconstructible). Esta ronda reduce cuántos turnos LLEGAN ahí; si tras medir
  siguen llegando muchos en historial, el siguiente paso es la reparación
  compacta con hechos para preguntas sin parámetro.
- **`semantic_scope.py` sigue sin cablear**: el rescate por entailment para
  ámbito existe escrito y nada lo importa. Con los fixes léxicos de esta ronda
  puede no hacer falta; queda como palanca si el banco muestra rechazos
  residuales.
- El enum de spans en turnos de historial cargados (HIS-F01,
  `context_budget_exceeded`) sigue pendiente de la ronda 3.
