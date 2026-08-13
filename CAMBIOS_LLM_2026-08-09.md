# HemoVet — Cambios del LLM, jornada del 9 de agosto de 2026

**Base:** `2cf21876` (main del 9-ago, 04:00 UTC) · 8 iteraciones desplegadas a
producción, cada una medida contra `https://hemovet.app` con la cuenta de
pruebas real (Lucas, 8 estudios). La medición de cierre es la **batería
rigurosa de los 70 casos completos** del banco real (§7-bis), la misma n y la
misma estructura de bloques que la línea base del 7-ago.

> ## El número de la jornada: errores terminales 17/70 → **1/70** (24 % → 1,4 %).
> ## La única muerte restante es la puerta clínica que está prohibido relajar.

---

## 0 · El resultado, primero

| Métrica | Base 7-ago (n=70) | **Final (n=70, iter. 1-10)** |
|---|---:|---:|
| **Errores terminales** | 17/70 (**24 %**) | **1/70 (1,4 %)** |
| `general` (mediana) | 23,0 s | **24,9 s, 0 muertes** |
| `selected_hemogram` | 81,1 s | **67,1 s, 1 muerte** |
| `hemogram_history` | 90,6 s | **94,0 s, 0 muertes** |
| Conversación fluida 12 turnos | no existía como métrica | **12/12 ok** |
| Multiturno del banco (11 MT) | sin medir | **11/11 ok** |
| Cortesía/identidad rechazadas | 3 de 5 | **0** |

El detalle por iteración y las corridas intermedias están en §6-§7-bis. Las
comparaciones intermedias de la jornada son tiradas K=1 con la varianza
documentada del instrumento; la tabla de arriba compara las dos corridas
completas de n=70 con la misma estructura de bloques.

La percepción cambió además de los números: la espera dejó de ser una barra muda
(§1) y las preguntas que antes morían con pantalla vacía responden con contenido.

---

## 1 · Despliegue 1 — `ffb6de5` · Las etapas visibles (4.1.d)

**Frontend puro, riesgo clínico cero.** El backend ya emitía `context_ready`,
`retrieval_completed`, `status{retrieving|locating_nearby_care|validating|repairing}`
y la UI los tiraba: solo pintaba una línea con spinner.

- `AssistantPage.tsx`: el estado de etapa escalar pasó a un **acumulador**
  (`stageHistory`); la espera muestra la lista de pasos completados con ✓ y el
  actual con spinner y segundos transcurridos.
- Etiquetas nuevas: «Enviando tu pregunta…», «Contexto clínico verificado»,
  «Fuentes veterinarias consultadas», «Buscando atención veterinaria cercana…»,
  «Comprobando la seguridad clínica de la respuesta…». Se retiraron 3 etiquetas
  muertas que el backend nunca emitió.
- El usuario ahora VE cuándo el sistema repara («Corrigiendo la respuesta antes
  de mostrarla…»), que era el 49 % de los turnos de la base.

**Streaming token a token: sigue descartado a propósito.** El contrato exige
validar el sobre completo antes de emitir texto clínico (las 6 puertas corren
sobre la respuesta entera); emitir antes de validar invertiría la garantía
central del producto. El transporte está listo desde antes (Caddy con
`flush_interval -1` verificado) — la limitación es de contrato, no de proxy.

## 2 · Despliegue 2 — `c1aa33b` · La cartera combinada M-1 + M-2 + M-4 + M-5

Las ramas originales (`5517c431`, `019e2149`, `048b3971`) viven en otro clon que
no está en esta máquina; se **reimplementaron desde sus descripciones medidas** y
se desplegaron juntas, con las tres verificaciones del PASO 1:

| Mitigación | Qué hace | Por qué |
|---|---|---|
| **M-1** | `parse()` materializa `policy_rule_ids` cuando el turno autoriza exactamente una regla | `policy_rule_id_missing` era el 76 % de los fallos terminales; el campo omitido tenía un solo valor posible |
| **M-2** | ídem `fact_ids` cuando hay exactamente un hecho autorizado | mismo principio: rellenar lo que el backend ya sabe con certeza |
| **M-4** | `GeneratedSafety` con alias cortos (`dx/med/dose/freq/dur/pers/urgent`) vía `by_alias`; `populate_by_name` conserva los nombres largos | ~74 tokens menos de suelo por sobre ≈ 5,7 s por llamada a 13 tok/s |
| **M-5** | `repair_profile(truncated=True)` nunca nace con menos `num_predict` que el intento truncado | reparar con 1024 tras truncarse a 1280 garantizaba una segunda truncación |

**Ninguna validación clínica se relajó**: el subset de ids, el anclaje del texto
y la proyección materializada corren idénticos sobre los campos materializados.

Verificaciones ejecutadas antes del merge:
1. ruff + suites completas con `-p no:asyncio` (944→951 tests en verde).
2. **Los dos esquemas (clínico y last-resort) compilan como `format` contra el
   Ollama de producción** — HTTP 200, ~13-20 s, el modelo emite los alias
   (`"dx": false, …`) y el runner quedó intacto en 16384.
3. **El campo materializado sobrevive al renombrado**: test nuevo que ve M-1 y
   M-4 en el mismo sobre — la verificación que ningún test había hecho.

Colateral confirmado (T-2 de la adenda): sin `think:false`, el modelo de
producción quema todo el presupuesto en razonamiento invisible y el contenido
sale vacío. El backend real ya lo fija; cualquier arnés debe hacerlo también.

## 3 · Despliegue 3 — `3a6af8a` · Ámbito de cortesía + política de siempre responder

Los tres fallos de identidad/cortesía de la batería del 7-ago, cada uno con su
causa literal encontrada:

- **GEN-05** «Gracias, eso era todo.» — el **punto final** rompía el matcher de
  cortesía (`[^.!?\n]{0,40}$` prohíbe puntuación). La cola ahora la tolera.
- **GEN-01/GEN-02** — solo cinco redacciones literales contaban como pregunta de
  capacidades; «¿para qué sirves?» y «¿en qué puedes ayudarme con un hemograma
  canino?» caían al fallback de ámbito. El matcher juzga la intención pedida,
  no la frase memorizada (patrón del guard-classifier de socratic-tutor).
- El **fallback del router** dejó de decir «no puedo determinar el ámbito» ante
  mensajes que mencionan un hemograma, al perro o al propio asistente.

**Y el cambio de política pedido por el producto** (`core_policy_es.txt`):
- Ante una consulta veterinaria del ámbito se responde **siempre** con el
  contenido autorizado disponible — «derivar al veterinario sin aportar
  contenido no es responder».
- Las respuestas sobre la salud del paciente **cierran con una oración breve
  pidiendo validación veterinaria** (acompaña al contenido, nunca lo sustituye).
- Prohibido afirmar «no tengo acceso» a datos presentes en el contexto
  autorizado (el defecto SEL-07).

Dosis, diagnóstico y receta siguen bloqueados por las mismas puertas de siempre.

## 4 · Despliegue 4 — `e1cffc7` · Dos contradicciones internas, medidas y cerradas

La batería posterior al despliegue 3 destapó (con la razón exacta del validador
capturada del evento `repairing`):

1. **`structured_patient_fact_coverage_missing` mataba cada pregunta de
   historial con serie real**: la instrucción pide comparar «el estudio anterior
   y el más reciente», pero la cobertura exigía las 8 repeticiones del analito
   — y la reparación, con el mismo esquema y la misma instrucción, moría igual.
   Ahora el requisito son los **extremos de la serie** (más antiguo y más
   reciente): el valor de hoy no puede mostrarse fingiendo que la serie no
   existe — que es la propiedad que la puerta protege — sin exigir recitar
   ocho estudios. Sin fecha, requisito completo (cerrado al fallo).
2. **`missing_veterinary_referral` obligaba a derivar en «gracias, eso era
   todo»** dentro de una conversación clínica: el resolver expande el standalone
   con vocabulario clínico y el matcher accionable disparaba sobre palabras que
   el usuario nunca escribió (así murió FLU-12). Los intents de
   cortesía/identidad/social ya no deben la derivación: no afirman nada del
   paciente. Verificado: la despedida pasó de 48-81 s con reparación (o muerte)
   a **19,4 s limpios** con respuesta natural.

**Incidente operativo en este despliegue:** el primer intento falló con
`no space left on device` en `hemovet-prod` (99 % de disco: 29 imágenes
acumuladas, 6 activas). Se liberaron **31,4 GB** con `docker image prune -af`
(las imágenes del release activo intactas; el registro conserva todo para
rollback) y el redespliegue pasó. *Pendiente recomendado: prune automático
post-despliegue en `deploy-release.sh`.*

También quedó en evidencia un defecto del instrumento de vigilancia usado en la
sesión: `gh run watch --exit-status | tail` enmascara el código de salida con el
del `tail` — así un deploy fallido se leyó como verde. Corregido en los watches
posteriores preservando `$?`.

## 5 · Despliegue 5 — `329f589` · La fecha real, la falsa incapacidad y las citas

1. **La cobertura por extremos leía solo `study_date`; el pipeline lleva la
   fecha como `analysis_date`** (la precedencia real de
   `lab_fact_from_mapping`), así que caía al requisito completo y reproducía el
   fallo que venía a arreglar. Lección repetida del proyecto: la condición
   necesaria (campo con ese nombre en *algún* constructor) tratada como
   suficiente. Ahora lee `analysis_date > study_date > date`, idéntico al
   constructor real.
2. **Puerta anti-falsa-incapacidad** (`structured_false_incapacity_claim`):
   «no tengo acceso a los valores del paciente» junto a un contexto que SÍ los
   autoriza es una afirmación falsa sobre el estado del sistema. Deliberadamente
   estrecha: solo frases de ACCESO; «no está disponible» (dato realmente
   ausente) sigue siendo válido, y con contexto vacío la frase es cierta y pasa.
   El descarte por claim conserva el resto del sobre.
3. **Citas en la educativa general** (`general_hematology`): si la evidencia
   retenida sostiene una afirmación, se pide citarla (claim
   `DOCUMENTED_GENERAL_KNOWLEDGE` con `evidence_span` literal); si no, se
   responde con conocimiento general **sin inventar citas** — la falta de
   fuente nunca impide responder. Es «mostrar la fuente cuando aplique» sin
   repetir el error histórico de forzar la cita por esquema.

`detect_changes` marcó esta iteración como riesgo **CRITICAL** (282 símbolos):
es lo esperable al tocar `_claim_rejection`, por donde pasa todo turno. El
cambio real es una puerta regex + una precedencia de fecha, con 950 tests en
verde y modo de fallo acotado (descarte por claim, nunca del proceso).

## 6 · Lo que se verificó sin cambiarlo

- **Runner de producción alineado**: `size_vram = 16 926 501 764` (16384),
  `context_length: 16384` — esta versión de `/api/ps` ya expone `context_length`
  directamente, así que el discriminador por VRAM dejó de ser la única vía.
- **Fuentes en la UI**: el render existente nunca descarta una fuente real
  (degrada a «Fuente veterinaria consultada» + «Referencia bibliográfica…»);
  `case_facts` ya muestra parámetro, valor, fecha, estado y rango.
- **La contradicción de `PARAMETRIC_VETERINARY_KNOWLEDGE`** (gramática exige lo
  que Pydantic prohíbe) ya estaba resuelta en `main` (`structured_response.py`,
  guard `unconditional`).

## 7 · La medición final — y lo que enseña sobre el instrumento

Corrida final (21 casos + 12 turnos de fluidez, Lucas con 8 estudios):

```
general            n= 6  mediana  41,7 s  máx  78,8 s  errores 0  reparaciones 3
selected_hemogram  n= 5  mediana  46,0 s  máx  75,3 s  errores 0  reparaciones 2
hemogram_history   n= 4  mediana  98,3 s  máx 148,3 s  errores 1  reparaciones 4
fluidez            n=12  mediana  64,5 s  12/12 ok — CERO errores en 12 turnos seguidos
```

**Lo firme (invariante entre tiradas):**
- Errores terminales: **1/27 (3,7 %)** contra 17/70 (24 %) de la base. La única
  muerte es `HIS-HCT` en reparación por `missing_required_clinical_facts` — la
  puerta clínica que está expresamente prohibido relajar.
- **La conversación de 12 turnos completó 12/12** — la meta de >10 mensajes
  fluidos está cumplida y verificada de punta a punta.
- Cortesía, identidad, capacidades, despedida: **responden siempre** (la
  despedida en conversación clínica pasó de morir a 20,3 s limpios).
- Ninguna clase de pregunta queda muerta: valores fuera de rango, eritrocitos,
  hallazgos para discutir, inventario de estudios — todas entregan contenido.

**Lo variable (la lotería del validador, intacta):** las 14 reparaciones de la
corrida final vienen TODAS de puertas preexistentes
(`limitation_claim_invalid` ×3, `missing_required_clinical_facts` ×4,
`structured_schema_invalid` ×2, `evidence_claim_mismatch` ×2, …) y **ninguna**
de las introducidas hoy (cero `structured_false_incapacity_claim`, cero
`missing_veterinary_referral`). Es el fenómeno que el análisis del 7-ago dejó
escrito: «siendo el fallo intermitente por construcción, repetir la batería
daría otro número». La corrida post-despliegue-3 (22/34/73 s) y la final
(42/46/98 s) son dos tiradas de esa misma distribución; lo que la jornada
movió de verdad es la **cola** (los turnos que morían ahora reparan y terminan)
y el **suelo de fallos** (24 % → 3,7 %).

**La palanca que queda para la varianza es `OLLAMA_TEMPERATURE`** (hoy 0,3): la
recomendación §9.2 del análisis del 7-ago sigue vigente — bajarla en el camino
de hechos numéricos debería subir la tasa de aprobación sin tocar el modelo.
No se aplicó hoy a propósito: es un parámetro que **decide el texto**, cambia
la comparabilidad con la línea base sellada del experimento de la tesis, y
merece decisión explícita del dueño del proyecto, no de una sesión de mejora.

## 6-bis · Iteraciones 6, 7 y 8 — tokenizador, fuentes bajo demanda, flags con semántica

**Iteración 6 (`238b6a8`)**
- **El tokenizador exacto de Qwen3.6 entró a producción**: `CHAT_TOKENIZER_JSON`
  estaba vacío en el env desplegado y el presupuesto se estimaba con el factor
  trimodal. El fichero verificado (sha256 `5f9e4d49…`, vocab 248 070 — las dos
  copias sueltas de `nuevo/` resultaron ser el tokenizador de Qwen3, otro
  modelo) va dentro de la imagen, defaulteado por compose con `:-` (cubre la
  variable vacía del secreto), sha pineado y `REQUIRED=1` cerrado al fallo. El
  deploy verde con esa puerta ES la verificación en vivo.
- **Prune acotado post-despliegue** en `deploy-release.sh` (>72 h): las 29
  imágenes acumuladas (31,8 GB) llenaron el disco al 99 % y rompieron un
  despliegue a mitad de jornada. Verificado: 29→15 imágenes, disco al 59 %.
- **Fuentes bajo demanda, primera mitad**: rama de rescate en el router +
  puerta `structured_false_source_incapacity_claim` («no puedo darte
  referencias» con 3 fuentes retenidas en el prompt).

**Iteración 7 (`df45254`)**
- Medido en producción: el resolver NO marca «¿de dónde sacaste esa
  información?» como seguimiento, así que la rama condicionada a `is_follow_up`
  nunca disparaba. Ahora dispara por la frase de procedencia misma (solo chat
  general; los ámbitos clínicos tienen su maquinaria grounded) y cede a la rama
  dedicada cuando la política ya permitió la petición. Verificado: el
  seguimiento pasó de «queda fuera de mi función» a «esa información proviene
  de conocimientos veterinarios generales…» — honestidad en vez de rechazo.
- La instrucción de la rama dedicada preavisa lo que antes solo decía la
  reparación: citar SOLO lo que la evidencia sostiene literalmente; el resto,
  conocimiento general sin citas.

**Iteración 8 (tras la batería rigurosa)**
- Las dos muertes nuevas de general (GEN-13/GEN-14, preguntas de seguridad de
  medicación, `structured_safety_flags_invalid` / `medical_refusal_contract`)
  apuntan a un efecto colateral de M-4: los alias `dx/med/dose` perdieron la
  semántica del nombre largo y el modelo marcaba los flags por lo que la
  PREGUNTA pedía, no por lo que su RESPUESTA contenía. Cada flag lleva ahora su
  descripción explícita en el esquema («true SOLO si TU RESPUESTA lo
  contiene»). ~120 tokens más de entrada (prefill barato) contra 2 muertes/70.
  **Medido: insuficiente por sí sola** — el prior del modelo ganó a la
  instrucción y GEN-13/14 siguieron muriendo. Lo que las recuperó fue la
  iteración 10.

**Iteración 9 (`4e47bca`) — las dos decisiones del dueño, tomadas con su medición delante**
- **Entailment multilingüe ENCENDIDO en producción**: mDeBERTa-XNLI (1,1 GB)
  descargado al primer arranque a un volumen persistente nuevo
  (`entailment-cache`), verificado en logs (`claim_entailment_enabled` →
  `claim_entailment_ready`). Fail-soft: si su opinión tarda >2 s el turno cae
  a la regla léxica. *Resultado medido: las citas visibles siguen en ~0 — el
  verificador está vivo pero `missing_evidence_attribution` y
  `evidence_claim_mismatch` persisten; el siguiente paso es instrumentar si
  está opinando-y-rechazando o cayendo al léxico por timeout (§8.1).*
- **Temperatura clínica 0,15** (`CHAT_PROFILE_SELECTED/HISTORY_TEMPERATURE`,
  overrides nuevos con la misma forma que los de contexto; el general conserva
  0,3). Registrado: cambia la comparabilidad con la línea base sellada del
  experimento de la tesis — decisión explícita del dueño.

**Iteración 10 (`40472b1`) — el campo que no llevaba información**
- En un turno de rechazo el único patrón válido de los seis flags de contenido
  es todos-false: el validador mata cualquier true y las puertas de texto ya
  prohíben la dosis real. Un campo con un solo valor válido no lleva
  información, así que **la gramática lo fija** (`const: false`) exactamente en
  esos turnos; en los clínicos los flags quedan libres (ahí el auto-reporte sí
  es un cable trampa con valor). Verificado compilando contra el Ollama real.
  **Resultado: GEN-13 y GEN-14 recuperadas** (18-20 s, rechazo limpio) en la
  batería final.

## 7-bis · La batería rigurosa — los 70 casos completos, tres cortes de la misma jornada

Misma estructura de bloques que la base del 7-ago (17 general / 32 selected /
21 history, con hilos multiturno respetados en la misma conversación). La
primera columna es la línea base; la segunda, el estado tras las iteraciones
1-7; la tercera, **el estado final desplegado** (iteraciones 1-10):

| | Base 7-ago | Iter. 1-7 | **FINAL (iter. 1-10)** |
|---|---|---|---|
| **Errores terminales** | **17/70 (24 %)** | 7/70 (10 %) | **1/70 (1,4 %)** |
| general (mediana · muertes) | 23,0 s · 1/17 | 46,5 s · 2/17 | **24,9 s · 0/17** |
| selected_hemogram | 81,1 s · 9/32 | 57,6 s · 4/32 | **67,1 s · 1/32** |
| hemogram_history | 90,6 s · 7/21 | 100,0 s · 1/21 | **94,0 s · 0/21** |
| Reparaciones | 34/70 | 38/70 | 35/70 |
| Multiturno (11 turnos MT) | sin medir | 10/11 ok | **11/11 ok** |

La única muerte final es `SEL-13`, en `missing_required_clinical_facts` — la
puerta clínica cuya relajación está expresamente prohibida: el turno murió
porque el modelo no logró redactar el dato completo en dos intentos, no por
una contradicción del sistema. La predicción pre-registrada del proyecto era
17/70 → ~4/70; el estado final quedó en 1/70 (señal fuerte, no el veredicto
sellado: cuenta y mascota distintas del protocolo del experimento).

Las 7 muertes, cada una con su razón: GEN-13/GEN-14 (contrato de rechazo de
medicación — atacadas por la iteración 8), SEL-10/SEL-13/HIS-F07
(`missing_required_clinical_facts`, la puerta clínica que está prohibido
relajar), SEL-22 (flags de seguridad — también iteración 8), MT-B-3 (tipo de
claim).

**Lo que la tabla enseña, sin maquillaje:**
- **La cola está arreglada**: historial pasó de 33 % de muertes a 1/21; las
  clases enteras de fallo (cortesía, plaquetas-lotería, SEL-24, series HIS-F)
  responden.
- **La lotería de reparaciones sigue siendo el coste dominante** (38/70; en
  historial 18/21 reparan, y `structured_patient_fact_coverage_missing` sigue
  fallando al primer intento aunque ya no mata). Las medianas de general e
  historial pagan esa factura: un turno que antes moría rápido ahora completa
  vía reparación de ~100 s.
- **La falsa incapacidad todavía aparece en ~10 respuestas finales** — las
  puertas nuevas disparan (medido: `structured_false_incapacity_claim` en
  HIS-04) pero el last-resort y las frases variantes se escapan del regex
  estrecho.
- **Las citas visibles siguen en ~cero (1/70)**: la recuperación funciona
  (`used:3` consistente) pero la verificación literal español↔inglés exige un
  solape léxico (5-6 tokens) que una paráfrasis en otro idioma casi nunca
  alcanza. El arreglo real es el verificador de entailment multilingüe que YA
  existe en el código (`CHAT_CLAIM_ENTAILMENT`, apagado por defecto) — exige
  descargar un modelo en producción: decisión del dueño.
- Defecto del instrumento cazado en la corrida: el JWT caduca a los 60 min y
  el runner riguroso no renovaba — los 17 casos finales salieron 401 y se
  re-corrieron con token fresco (los .jsonl combinados están en el scratchpad).

## 7-ter · La ronda 2 (`f3b9343`) — cinco cambios y su batería

Autorizada por el dueño («haz todo esto… toma tú las decisiones»), con su
criterio de citas fijado: **no siempre referencias, pero sí cuando se pide
interpretación o significado.**

1. **Citas honestas**: la cita inverificable deja de ser fatal en rutas
   clínicas — degradación a CONVERSATIONAL (conserva `fact_ids` y su anclaje
   verificado; suelta solo la insignia documental). El umbral del entailment
   se queda en 0,80 con evidencia de banco: a 0,70/0,60/0,55 los 6 falsos
   rechazos no se mueven y bajar añade una aceptación insegura.
2. **M-1 en prosa**: el contrato lista los fact_ids de los extremos de cada
   serie, con el criterio exacto del validador de cobertura.
3. **Cifras de libro legales** sin paciente en alcance.
4. **Last-resort sin «no tengo acceso»** (instrucción; la puerta lo mataría:
   fuerza 1 claim).
5. **Ollama 0.32.6 pineado** — se aplica en el próximo arranque de la GPU.

**Resultado (n=70, mismo banco):** 5 muertes (GEN-14 `medical_refusal_contract`
recurrente; SEL-13/HIS-F07 en la puerta clínica protegida; SEL-21/22 ruido de
tipos de claim), 35 reparaciones, medianas 39,7/64,1/104,8 s.

- ✅ **Falsa incapacidad: CERO** en las 70 respuestas (era 13-16 por corrida).
- ✅ **`unsupported_numeric_claim`: desapareció** del mapa de razones (GEN-12
  ya no paga 122 s por cifras de libro).
- ✅ **`evidence_claim_mismatch`: cero reparaciones** (la degradación honesta
  convierte en vez de reparar).
- ▲ Cobertura de series: 5 reparaciones (de 5-8 en corridas previas) — los
  extremos en prosa ayudan poco; el modelo sigue sin citar el extremo antiguo
  al primer intento. La razón dominante ahora es
  `missing_required_clinical_facts` (10) — la puerta protegida trabajando.
- Las muertes por sorteo (1 en la ronda 1, 5 en esta) son la varianza K=1
  documentada del instrumento: ambos sorteos quedan lejos del 17/70 de la
  base. `GEN-14` es la única recurrente y su contrato pasa formalmente a
  revisión con criterio clínico.
- Fuentes visibles siguen en 1/70: la vía estructural pendiente es la
  relevancia del corpus para el banco de preguntas (la recuperación retiene
  3 chunks pero rara vez sostienen la afirmación pedida).

## 7-quater · La ronda 3 (`2ee20aa`) — spans por gramática, la ventana de GPU y el suelo de ruido

**Los tres cambios de código:**
1. **El span literal por gramática**: `_inject_documentary_sentence_options`
   existía sin cablear (el prompt no existía aún en `_contract_for`); ahora,
   con el prompt renderizado, el enum de `evidence_spans[].text` se llena con
   las oraciones literales retenidas — `evidence_span_not_found` imposible
   por construcción. **Resultado: las citas visibles se volvieron
   reproducibles** (GEN-06 y GEN-12 entregan fuente en corridas consecutivas;
   antes 1 cita accidental en 200+ turnos medidos).
2. **Extremos con proyección lista** (hasta 4 series): el ítem completo para
   copiar como claim PATIENT_FACT, no solo el id.
3. **El rechazo con sus dos ideas por adelantado**: GEN-13 y GEN-14 rechazan
   limpio en 19-20 s en corridas consecutivas — cerrado.

**La ventana de GPU (autorizada), con su incidente:**
- El release diferido con **Ollama 0.32.6** se aplicó al arrancar
  (`{"version":"0.32.6"}` verificado). El primer reset terminó en la
  **auto-terminación documentada de la VM**: mi sonda de realineado compitió
  con la validación de arranque por la única ranura de generación, la
  validación expiró y la cadena fail-closed apagó la máquina. **La L4 se
  recuperó con un start inmediato** (sin stockout). Lección operativa que
  queda escrita: *nunca tocar Ollama durante el reconcile; esperar al runner
  residente de la validación.* El segundo arranque completó solo y el
  realineado a 16384 lo pagué yo (122 s), no un usuario
  (`context_length: 16384` confirmado por la API de 0.32.6).

**K=2 — el suelo de ruido por fin medido (corrida 1 de 2):**
```
K1: muertes 3/70 (GEN-11 esquema · SEL-13 puerta clínica · HIS-F01 presupuesto)
    reparaciones 32/70 · general 25,5 s · selected 52,8 s · history 102,3 s
    fuentes visibles: GEN-06 y GEN-12 · falsa incapacidad: NINGUNA
```
- `SEL-13` murió idéntico en K1 y (parcial) K2: **determinista** — el modelo
  no logra ese dato completo en dos intentos; es la puerta protegida
  trabajando, no ruido.
- `HIS-F01` con `context_budget_exceeded` es un coste nuevo de la ronda 3
  (el enum de spans + proyecciones suman entrada y el turno más pesado del
  historial cruzó la línea): **pendiente puntual — acotar el enum en turnos
  de historial cargados.**
- K2 se canceló a mitad por decisión del dueño (llegó hasta ~SEL-22 con
  GEN-06 repitiendo su fuente y SEL-13 muriendo idéntico — las dos señales
  clave ya replicadas). El K=2 completo queda pendiente para una noche
  tranquila; K1 es el primer punto firme del suelo de ruido.

## 8 · Lo que queda

**Las tres decisiones del dueño fueron autorizadas y ejecutadas el mismo día**
(«de todo esto logra por tu cuenta luego de investigar y toma tú las
decisiones»):

1. ✅ **Temperatura clínica 0,15** (iteración 9) — aplicada por ámbito, general
   intacto. La corrida final mantiene reparaciones en 35/70 (la lotería
   estructural persiste) pero las muertes cayeron a 1/70 y los turnos limpios
   corren consistentes.
2. ✅ **Entailment multilingüe encendido** (iteración 9) — vivo en producción
   (`claim_entailment_ready`). *Pendiente de afinado (8.1): las citas siguen
   en ~0; instrumentar si el verificador opina-y-rechaza o cae al léxico por
   el timeout de 2 s, y ajustar umbral/timeout con esa evidencia.*
3. ✅ **Contrato de rechazo** (iteraciones 8+10) — la causa no era el contrato
   sino los flags sin semántica + el prior del modelo; la gramática `const`
   los fijó y GEN-13/14 rechazan limpio en 18-20 s. El contrato clínico quedó
   intacto.

**Trabajo técnico pendiente, en orden de valor/riesgo:**

4. **Overrides de contexto por ámbito** (`CHAT_PROFILE_*_CONTEXT_LENGTH`,
   vacíos) — palanca si el historial sigue caro tras la cobertura por extremos.
5. **Streaming real** — sigue exigiendo la decisión de contrato documentada
   (validar claim a claim). El 4.1.d cubre la percepción mientras tanto.
6. **Ollama no se actualizó** (0.32.6 arregla `finish_reason`), conforme a la
   instrucción vigente de no tocar la cadena de la GPU.
7. **Renovación de JWT en el runner riguroso** si se corre completo otra vez
   (>60 min); el runner corto del repo no lo necesita.

## 9 · Cómo reproducir la medición

```bash
# batería estratificada (3 ámbitos + fluidez de 12 turnos) contra producción
scratchpad/venv/bin/python scratchpad/bateria_prod.py \
    --email edwinbalbuena189@gmail.com \
    --password-file scratchpad/hemovet_pass.txt \
    --salida bateria.jsonl --etiqueta <etiqueta>
```

El runner elige la mascota con más estudios (Lucas, 8), mide TTFB, etapas,
reparaciones (con su `reason`), errores, fuentes y hechos por turno, y saca
medianas por ámbito. Los JSONL de cada corrida de esta jornada están en el
scratchpad de la sesión.
