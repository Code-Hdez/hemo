# Diagnóstico definitivo — sistema LLM de HemoVet

**Basado en los artefactos crudos de las cuatro fases**, analizados directamente:
`TABLA_REPAIRS_COMPLETA.csv` (97 llamadas), `arnes_capturas.json` (10 generaciones
crudas), `schema_real_produccion.json`, `token_tax.txt`,
`PERFIL_RENDIMIENTO_LLM.json` y los informes de las Fases 1–4.

Fecha: 8 de agosto de 2026
Veredicto sobre la necesidad de más auditoría: **la investigación está cerrada.**

---

## 0. Lo primero: hay una causa que nadie ha visto en cuatro fases

Antes del veredicto sobre la Fase 4, el hallazgo. Lo he obtenido analizando la
tabla de reparaciones que el propio agente generó y **no llegó a explotar**.

### El mecanismo de rescate es lo que mata el turno

```
policy_rule_id_missing según el tamaño del prompt de esa llamada

  prompt COMPLETO   (≥2.000 tok)  ......  2 de 67  =   3,0 %
  prompt TRUNCADO   (<2.000 tok)  ...... 13 de 30  =  43,3 %

  odds ratio = 24,9×        χ² = 25,8 (1 gl)        p < 0,001
```

Las 13 llamadas truncadas que fallan son **exactamente** las llamadas de último
recurso, con prompts de 1.373–1.404 tokens frente a los 3.769–6.897 de las
llamadas normales.

Y el desenlace:

```
Motivo de la ÚLTIMA llamada en los 17 turnos que no entregaron nada:

  13  policy_rule_id_missing          ← 76 % de todos los fallos terminales
   1  unsupported_status_claim:mchc
   1  medical_refusal_contract
   1  definitive_diagnosis
   1  structured_policy_claim_type_invalid
```

### La cadena causal completa

```
Pregunta clínica
   ↓
GENERACIÓN #1 · prompt 3.884 tok · 382 tok salida · ~34 s
   ↓ el validador rechaza (cobertura de hechos o metadatos de procedencia)
GENERACIÓN #2 · prompt COMPLETO ~3.900 tok · perfil *_structured_repair
   ↓ 8 de 34 se salvan aquí. Las otras 26 siguen mal.
ÚLTIMO RECURSO · send_chat_message.py:4283 · _last_resort_candidate()
   ↓ EL PROMPT SE RECORTA DE 3.884 A 1.380 TOKENS  (−64 %)
   ↓ con el recorte desaparece el catálogo de policy_rule_ids permitidos
   ↓ el modelo ya no puede citar identificadores que no ha recibido
GENERACIÓN #3 · 43,3 % falla por policy_rule_id_missing
   ↓
generation_repair_failed · response = null · el usuario no recibe nada
```

**El mecanismo diseñado para rescatar el turno es el que lo condena.** Es un
fallo iatrogénico: el tratamiento causa la enfermedad.

### La confirmación cruzada por perfil

Si la hipótesis es correcta —el recorte elimina el contexto clínico y de
política— los perfiles clínicos deberían sufrirlo más que los de seguridad, que
dependen menos de ese catálogo. Es exactamente lo que se observa:

| Perfil en la llamada truncada | Válidas |
|---|---|
| `hemogram_interpretation` | **2 de 9** |
| `history_comparison` | **2 de 9** |
| `hemogram_full_interpretation` | **0 de 1** |
| `source_bibliography` | **0 de 1** |
| `safety_guardrail` | **4 de 7** |
| `faq_simple` | 1 de 1 |

Los perfiles que necesitan el catálogo clínico caen a 4 de 20. Los que no lo
necesitan se mantienen en 5 de 8.

### Lo que cuesta

| | Segundos de GPU |
|---|---:|
| Total en llamadas de último recurso | **671 s** |
| De ellos, en las que además fracasaron | **468 s** |

468 segundos —casi ocho minutos de GPU en una batería de 70 preguntas— gastados
en un mecanismo de rescate que, en su configuración actual, empeora el resultado
más veces de las que lo mejora.

### Lo único que falta para cerrarlo

**Una lectura de código de diez minutos.** Hay que abrir
`_last_resort_candidate()` en `send_chat_message.py:4283` y comprobar
literalmente qué secciones del prompt elimina el recorte, y si el catálogo de
`allowed_policy_rule_ids` está entre ellas.

La correlación estadística es abrumadora (OR 24,9, p<0,001) y el patrón por
perfil es el que predice la hipótesis, pero **hasta leer esa función esto es
`EVIDENCIA_MUY_FUERTE`, no `CONFIRMADO`.**

---

## 1. Veredicto sobre la Fase 4

La Fase 4 aportó un hallazgo real y cometió tres errores que invalidan su
conclusión principal. Hay que decirlo con precisión porque el agente cerró
declarando resuelta la pregunta clínica, y no lo está.

### 1.1 ✅ Válido — el *token tax* existe y es la palanca mayor

La dirección es correcta y es el mejor hallazgo de las cuatro fases. Pero **la
magnitud está mal calculada**, y la he recalculado desde las capturas crudas.

**El error del agente:** derivó el número de tokens de `envelope_chars ÷ 3,46`.
Dos problemas encadenados:

1. `envelope_chars` sólo se registra en **25 de 97 llamadas** — y sólo en las
   generaciones **rechazadas**, que son sistemáticamente más largas. Submuestra
   sesgada.
2. La razón 3,46 chars/token se calibró sobre esa misma submuestra sesgada. Las
   capturas crudas permiten calibrarla directamente —`len(raw) ÷ eval_count` de
   la misma generación— y dan **3,03**, un 13 % más baja.

Resultado: el agente reportó 457 tokens de mediana. El valor real es **382** en
las generaciones primarias (351 en todas las llamadas). Se nota además en que
su propio modelo de latencia empeoró al usar 457: pasó de 0,0 % de error a 5,9 %,
y no lo advirtió.

**La descomposición correcta**, calibrada sobre las 10 capturas crudas:

| Componente de una generación primaria (382 tok) | Tokens | Segundos | % |
|---|---:|---:|---:|
| Bloque `safety` — 7 booleanos | **84** | **6,5 s** | **22,1 %** |
| Resto de metadatos de envoltura (`response_type`, `intent`, `schema_version`) | 42 | 3,2 s | 11,0 % |
| **Sobrecoste FIJO por llamada** | **126** | **9,7 s** | **33,0 %** |
| Andamiaje por claim (`claim_id`, `claim_type`, `fact_ids`, `policy_rule_ids`, sintaxis JSON) | variable | — | — |
| Texto clínico visible | 47–150 | 3,6–11,5 s | 12–40 % |

**El número más sólido, y el más accionable:** hay **126 tokens = 9,7 segundos de
sobrecoste fijo en cada una de las 133 llamadas**, independiente del contenido.
De ellos, 84 tokens (6,5 s) son siete campos booleanos que en **10 de 10**
capturas valen `false`.

> Matiz de honestidad que el agente no puso: el ratio visible del 12,3 % procede
> de capturas con **un solo claim**. Las respuestas de producción tienen varios,
> y el bloque fijo se amortiza. El ratio real de producción está entre el 12 % y
> el 40 %. **Lo que no depende del número de claims son los 126 tokens fijos.**
> Ése es el dato que hay que usar.

### 1.2 ⚠️ Conclusión correcta, prueba equivocada — `GRAMMAR_ENFORCED = SI`

El agente concluyó que la gramática se aplica porque pidió *«responde en texto
libre, ignora cualquier formato»* y el modelo devolvió JSON.

**Esa prueba no demuestra nada.** Un modelo cuyo prompt de sistema describe un
sobre JSON producirá JSON aunque no haya gramática alguna. No distingue
«gramática aplicada» de «modelo obediente».

**La conclusión es correcta, pero por otra evidencia** —que sí es concluyente y
está en los datos que el propio agente tenía delante:

1. Las 10 capturas respetan `additionalProperties: false` en los tres niveles del
   sobre. Ninguna emite un campo fuera del esquema. Ése es precisamente el
   síntoma que describe el issue #21228 («nombres de campo que no están en el
   esquema»), y **no aparece**.
2. Los 10 `claim_id` cumplen el patrón `^claim_[A-Za-z0-9_-]{1,80}$`.
3. Los 10 `claim_type` pertenecen al `enum` de 15 valores.
4. Y el argumento decisivo: los **24 rechazos `structured_schema_invalid`** de la
   batería tienen todos como detalle una regla de negocio
   (`policy_rule_id_missing`, `patient_fact_ids_missing`,
   `documented_evidence_spans_missing`, `parametric_fact_ids_forbidden`).
   **Ni uno solo es una violación real del JSON Schema.** Si la gramática hubiera
   caído en silencio, habría violaciones estructurales genuinas entre 133
   generaciones. No hay ninguna.

**Veredicto:** `GRAMMAR_ENFORCED = SI`, `CONFIRMADO`. Los `$defs`/`$ref` se
compilan correctamente en Ollama 0.32.5. El issue #21228 queda **descartado** para
este despliegue. Mi hipótesis H-NEW-1 era razonable y es falsa; conviene dejarlo
escrito.

### 1.3 ❌ El arnés NO reproduce producción — y esto invalida la respuesta clínica

Éste es el error grave, y el agente lo presentó como el cierre del proyecto.

Comparando las capturas con producción:

| | Arnés | Producción |
|---|---:|---:|
| Tokens de salida (mediana) | **230** | **382** |
| Tokens de prompt | no registrado, evidentemente mínimo | **3.769–6.897** |
| `fact_ids` usados | `fact_plt_001` — **inventado por el agente** | IDs reales de la BD |
| Claims por respuesta | **1** en 10/10 | variable |
| Contexto clínico | ninguno | 18 códigos autorizados, bundle completo |
| Validador aplicado | `fallos_regla` — **comprobación casera** | `structured_response.py` real |

El campo `fallos_regla` vale `[]` en las diez capturas porque es una heurística
escrita por el agente, **no el validador de producción importado en solo
lectura**, que era exactamente lo que el prompt de Fase 4 exigía.

Y hay una prueba definitiva de que no reprodujo el fallo: en producción, SEL-08
falla con `missing_required_clinical_facts: PLT:value,PLT:unit`. Ese validador
vive en `send_chat_message.py:381` y comprueba que **los hechos clínicos
materializados cubran el analito discutido**. Sin bundle clínico cargado, ese
validador **no puede ni ejecutarse**. El arnés era estructuralmente incapaz de
reproducir el fallo dominante.

**Consecuencia:** las tres cifras clínicas siguen sin existir.

```
CLINICAMENTE_CORRECTA_PERO_RECHAZADA      = NO PRODUCIDA
CLINICAMENTE_INCORRECTA_Y_BIEN_RECHAZADA  = NO PRODUCIDA
INDETERMINADA                             = NO PRODUCIDA
```

Lo que el agente midió fue una tarea distinta y mucho más fácil. Presentó el
resultado de esa tarea como respuesta a la pregunta de producción.

### 1.4 ✅ Pero el hallazgo de omisión sí vale — como cota inferior

Aun siendo una tarea de juguete, el resultado es informativo:

```
Con el valor PLT = 290 delante y su fact_id disponible:

  6 de 10  citan el hecho Y dan la cifra
  4 de 10  citan el hecho pero OMITEN la cifra
 10 de 10  emiten fact_ids correctamente
```

> ✅ *«Las plaquetas se encuentran dentro del rango normal con un valor de 290 x10^3/uL.»*
> ❌ *«Las plaquetas (PLT) se encuentran dentro del rango normal.»*

Ambas citan `fact_plt_001`. Ambas son ciertas. La segunda no dice el número.

**Esto es una cota inferior del problema.** Si el modelo omite la cifra el 40 %
de las veces en la tarea más fácil posible —un solo analito, un solo claim, sin
contexto que distraiga— en producción, con 18 analitos y un bundle de 3.900
tokens, será peor. Encaja con el 2 de 20 de la batería original.

Y aclara la naturaleza del fallo:

- **No es contrato imposible.** El modelo recibe el `fact_id` y lo cita 10/10.
- **No es fallo de grounding.** No altera el valor: lo omite.
- **No es muestreo grosero.** Es una regla de cobertura que cumple 6 de 10 veces.
- **Es un fallo de completitud**, y el validador hace bien en exigirla: para un
  veterinario, «están normales» sin la cifra es peor producto.

**Relajar `missing_required_clinical_facts` sería la mitigación equivocada.**

---

## 2. El diagnóstico, cerrado

### 2.1 Por qué HemoVet tarda tanto

De los 4.940 s de la batería (mediana 59,1 s por pregunta):

| Concepto | Segundos | % | Naturaleza |
|---|---:|---:|---|
| **Andamiaje JSON invisible** (100 % de las llamadas) | ~3.776 | 76,4 % | **evitable en parte** |
| — de ello, sobrecoste FIJO (126 tok × 133 llamadas) | ~1.286 | 26,0 % | **evitable** |
| — de ello, bloque `safety` (84 tok × 133) | ~857 | 17,3 % | **evitable** |
| 2.ª llamada (reparación, prompt completo) | 1.174 | 23,8 % | evitable si no se rechaza |
| 3.ª/4.ª llamada (último recurso truncado) | 671 | 13,6 % | **evitable — y contraproducente** |
| Texto clínico que el veterinario lee | ~532 | 10,8 % | **inevitable** |
| Prefill, carga, backend, red, cola | ~700 | 14,2 % | mayormente inevitable |

*(Las categorías se solapan: el andamiaje se paga también dentro de las llamadas
2.ª y 3.ª. El desglose es por concepto, no una partición.)*

### 2.2 El modelo de latencia, recalibrado

```
T(turno) = N_llamadas × (prefill 5,7 s + decode 382/13,05 s) + 1,8 s

  N = 1,00  →  36,8 s     medido  34,8 s     error 5,9 %
  N = 2,85  → 101,8 s     medido  98,1 s     error 3,7 %
```

Sigue habiendo exactamente tres palancas, y ahora las tres están medidas:

| Palanca | Afecta a | Estado |
|---|---|---|
| **Tokens por llamada** (382, de los que 126 son sobrecoste fijo) | **100 %** de las llamadas | **medido por fin** |
| **Llamadas por pregunta** (1 en 51,4 %, 2,85 en 48,6 %) | 48,6 % de los turnos | causa raíz identificada |
| **tok/s de decode** (13,05) | 100 % | margen 8–14 % `NO_OBSERVABLE` |

### 2.3 Las cinco causas, ordenadas

**CAUSA 1 · Sobrecoste estructural fijo — 9,7 s en cada llamada**
`CONFIRMADO`. 126 tokens de metadatos por generación, de los que 84 son siete
booleanos que valieron `false` en 10 de 10 capturas. Afecta al 100 % de las
llamadas, incluidas las que van bien. Nunca se había medido.

**CAUSA 2 · Truncación iatrogénica del último recurso — 76 % de los fallos terminales**
`EVIDENCIA_MUY_FUERTE`. El recorte de 3.884 → 1.380 tokens multiplica por 24,9
la probabilidad de `policy_rule_id_missing`. 13 de los 17 turnos que no
entregaron nada murieron así. Falta una lectura de código de diez minutos para
elevarlo a `CONFIRMADO`.

**CAUSA 3 · Desajuste entre el contrato impuesto y el contrato juzgado**
`CONFIRMADO`. `GeneratedClaim.required = [claim_id, text, claim_type]`;
`policy_rule_ids` y `fact_ids` llevan `default_factory=list` y no son `required`.
La gramática —que sí funciona— permite `[]`. La regla de
`structured_response.py:140` lo prohíbe para ciertos `claim_type`, condición que
JSON Schema plano no expresa.

**CAUSA 4 · Fallo de completitud del modelo — omite la cifra 4 de 10 veces**
`EVIDENCIA_FUERTE` (cota inferior). Recibe el hecho, cita su identificador, y no
escribe el número. El validador hace bien en rechazarlo.

**CAUSA 5 · Suelo físico del decode — 13,05 tok/s**
`CONFIRMADO`. 77 % del techo de ancho de banda de una L4, coherente con el ~81 %
que mide la literatura para decode en batch-1 en esa GPU. Margen de engine de
8–14 % documentado upstream, sin medir aquí.

### 2.4 Dos llamadas anómalas que nadie ha comentado

`HIS-02` y `HIS-F08` alcanzaron `num_predict = 1280` con `finish_reason: length`
y produjeron `structured_json_invalid`:

```
HIS-02  #1   1.280 tok   95,6 s   JSON roto por truncación
HIS-F08 #1   1.280 tok   96,2 s   JSON roto por truncación
                        ─────────
                        191,8 s de GPU para entregar JSON inválido
```

Son las dos llamadas más caras de toda la batería. El sobre no cupo en el
presupuesto y se cortó a mitad de un objeto JSON. Con la gramática activa, agotar
el presupuesto de tokens produce necesariamente JSON inválido. Es un fallo de
diseño de presupuesto, no del modelo.

---

## 3. ¿Hace falta otra auditoría? No.

**Cuatro fases han convergido. La investigación está cerrada.** Otra fase de
auditoría produciría un quinto informe elegante sin mover el problema.

Lo que queda no es investigar: es **verificar dos cosas concretas y empezar a
mitigar**.

### Lo que ya está cerrado y no debe volver a preguntarse

| | |
|---|---|
| Thinking | `DESCARTADO` — experimentalmente |
| Caché de prefijos | `FUNCIONA` — checkpoints restaurados, ahorra 24,2 % del prefill |
| GPU / offload / cola | `LIMPIO` — 133/133 en GPU completa, cola 0 ms |
| Gramática / structured output | `SE APLICA` — 0 violaciones estructurales en 133 generaciones |
| Trazabilidad código↔producción | `CERRADA` — `HEMOVET_BUILD_REVISION == HEAD` |
| Truncación por `num_predict` | `MARGINAL` — 2 de 138, pero cuestan 192 s |
| RAG | `NO ES CAUSA` — 8 de 70, 183–655 ms |
| Prefill / compresión de historial | `TECHO DEL 11 %` — no es la palanca |
| Flash Attention / KV-quant | `YA ACTIVOS` — nada que ganar |

### Lo que falta, y es poco

1. **Leer `_last_resort_candidate()`** — 10 minutos. Cierra la Causa 2.
2. **Rehacer el arnés en serio** — con el prompt real de producción y el
   validador real importado. Es lo que la Fase 4 debía hacer y no hizo. Produce
   las tres cifras clínicas.
3. **Comprobar si el bloque `safety` se usa para algo** — 20 minutos de lectura.
   Decide si se pueden recuperar 6,5 s por llamada.

Con eso, a mitigación.

---

## 4. Matriz de mitigación, ordenada por evidencia

Ninguna aplicada. Ordenadas por *segundos recuperados ÷ riesgo clínico*.

### M-1 · No truncar el prompt del último recurso — o truncar preservando el catálogo de IDs
- **Ataca:** Causa 2. **13 de 17 fallos terminales.**
- **Evidencia:** OR 24,9× · χ² 25,8 · p<0,001 · patrón por perfil consistente
- **Coste:** +2,5 s de prefill por llamada de último recurso (1.380 → 3.880 tok)
- **Ganancia:** convierte fallos totales en respuestas. Y libera hasta 468 s de GPU hoy desperdiciados
- **Riesgo clínico:** **ninguno** — se añade contexto, no se relaja ninguna validación
- **Complejidad:** baja
- **Veredicto: PRIORIDAD 1.** Es la mejor relación de toda la matriz y no toca ninguna garantía.

### M-2 · Rellenar `policy_rule_ids` de forma determinista cuando el conjunto autorizado tiene un solo elemento
- **Ataca:** Causa 3. 15 de 80 rechazos
- **Evidencia:** el backend **ya conoce** los IDs permitidos —los inyecta en el
  esquema vía `constrain_identifier_array("policy_rule_ids", allowed_policy_rule_ids)`.
  Si el conjunto autorizado tiene cardinalidad 1, el único valor válido es
  conocido de antemano y pedírselo al modelo no aporta información
- **Coste:** 0 segundos. Es una asignación en el backend
- **Riesgo clínico:** **bajo, con la salvaguarda:** rellenar **sólo** cuando el
  conjunto autorizado tenga exactamente un elemento. Con dos o más, la elección
  es semántica y debe seguir haciéndola el modelo
- **Veredicto: PRIORIDAD 2.** No es fabricar procedencia: es no preguntar lo que ya se sabe.

### M-3 · Sacar el bloque `safety` de la generación
- **Ataca:** Causa 1. **6,5 s en el 100 % de las llamadas** = ~857 s de la batería
- **Evidencia:** 84 tokens, `false` en los 7 campos en 10 de 10 capturas. Y la
  seguridad real no la impone ese bloque sino los validadores sobre el texto
  (`definitive_diagnosis`, `medical_refusal_contract`, `mandatory_diagnosis_boundary`…)
- **Coste:** 0. Es quitar campos del esquema
- **Riesgo:** **medio hasta verificar** si esos booleanos alimentan alguna
  decisión. Si sólo se registran, quitarlos es gratis. **Comprobar antes.**
- **Veredicto: PRIORIDAD 3, previa verificación de 20 minutos.**

### M-4 · Acortar convenciones de identificadores
- **Ataca:** Causa 1
- **Evidencia:** el modelo genera `claim_plt_status_01` (~8 tokens) donde `claim_1`
  serían 3. El patrón `^claim_[A-Za-z0-9_-]{1,80}$` permite lo corto
- **Ganancia:** ~5 tokens por claim ≈ 0,4 s por claim
- **Riesgo:** nulo. **Veredicto: hacer junto con M-3.**

### M-5 · Presupuesto de tokens por perfil
- **Ataca:** las dos llamadas de 96 s que produjeron JSON roto (192 s)
- **Mecanismo:** `history_comparison` genera respuestas largas y agota
  `num_predict = 1280`, cortando el JSON a mitad. Con gramática activa, agotar el
  presupuesto **garantiza** salida inválida
- **Veredicto: hacer.** Coste bajo, elimina un fallo determinista.

### M-6 · Reparación dirigida por campo en vez de regeneración completa
- **Ataca:** Causa 3. Los 1.174 s de segundas llamadas
- **Mecanismo:** si el fallo es «falta un identificador», no hace falta regenerar
  382 tokens: hace falta insertar 20
- **Riesgo:** bajo. **Complejidad:** media. **Veredicto: diseñar después de M-1 y M-2**, que pueden reducir mucho la población de casos.

### M-7 · Corregir el clasificador de ámbito
- No mejora latencia. Pero rechaza preguntas obviamente del dominio y es lo
  primero que ve el usuario. **Independiente. Hacer.**

### M-8 · Memoria de 10 pares
- `history_limit = 12` son **mensajes**, luego **6 pares**, no los 10 requeridos.
  Y puede partir un par por la mitad. **Es un incumplimiento de requisito
  funcional, no un problema de rendimiento.** Con la caché de checkpoints
  funcionando, subir a 20 mensajes cuesta poco prefill.

### No hacer (evidencia en contra)

| Mitigación | Por qué no |
|---|---|
| Relajar `missing_required_clinical_facts` | El modelo omite la cifra 4 de 10 veces. El validador protege. Relajarlo entregaría «están normales» sin el número |
| Prefix caching adicional | Ya funciona; techo del 11 % |
| Flash Attention / KV-quant | Ya activos |
| Migrar a vLLM | Sus beneficios publicados son de throughput concurrente; HemoVet corre `-np 1` con cola de 0 ms |
| MTP / speculative decoding | Aceptación medida de 35–55 % en híbridos SWA como Qwen3.6; en llama.cpp sobre Ampere se midió pérdida neta del 3–12 % |
| Bajar a un modelo de 9B | Exige revalidación clínica completa. Y el fallo de completitud probablemente empeora |
| Subir `OLLAMA_NUM_PARALLEL` | No hay contención: cola de 0 ms |

---

## 5. Escenario combinado

Sobre la mediana de 59,1 s por pregunta, y sin tocar modelo ni hardware:

| Acción | Efecto |
|---|---|
| M-3 + M-4 (quitar `safety`, acortar ids) | −7 s **en cada llamada** |
| M-1 (no truncar el último recurso) | 13 de 17 fallos → respuestas |
| M-2 (rellenar `policy_rule_ids` determinista) | menos rechazos ⇒ menos segundas llamadas |
| M-5 (presupuesto por perfil) | elimina 192 s de JSON roto |

Un turno sin reparación pasaría de ~35 s a **~28 s**. Un turno con reparación, de
~98 s a **~56 s** — y muchos dejarían de repararse. **Y los 17 turnos que hoy no
entregan nada empezarían a entregar algo.**

Ninguna de estas mitigaciones cambia el modelo, la GPU, el engine ni relaja una
sola validación clínica.

---

## 6. Lo que sigue sin demostrarse

| Incógnita | Estado | Cómo se cierra |
|---|---|---|
| Qué elimina exactamente el recorte del último recurso | `EVIDENCIA_MUY_FUERTE` | leer `_last_resort_candidate()` — 10 min |
| Si la generación descartada era clínicamente correcta | `NO PRODUCIDA` | arnés con prompt y validador reales |
| Si el bloque `safety` alimenta alguna decisión | `NO INVESTIGADO` | lectura de código — 20 min |
| Margen real de engine en esta L4 | `NO_OBSERVABLE` | `llama-bench` fuera de horas |
| Si se cumplen los 10 pares de memoria | `INCUMPLIDO` (6 pares) | prueba funcional de 15 pares |

---

## 7. Conclusión

**No pidas otra auditoría.** Pide tres verificaciones cortas y empieza a mitigar.

La causa de que HemoVet tarde tanto está identificada y cuantificada: genera 382
tokens para entregar entre 47 y 150 de contenido, a 13 tokens por segundo, y en
la mitad de los turnos lo hace 2,85 veces.

La causa de que 17 de 70 preguntas no entreguen nada también: **el mecanismo de
último recurso recorta el prompt un 64 % y, al hacerlo, retira los
identificadores que el propio contrato exige citar.** 76 % de los fallos
terminales.

Y la única pregunta clínica realmente abierta —si el contenido descartado era
correcto— no la cerró la Fase 4, pero ya no es la que decide el proyecto: las dos
mitigaciones de mayor impacto (M-1 y M-2) **no dependen de esa respuesta**,
porque ninguna relaja una validación clínica. Se pueden diseñar hoy.