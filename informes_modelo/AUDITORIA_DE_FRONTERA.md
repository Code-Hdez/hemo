# Auditoría de frontera — qué significa un cero medido con un instrumento ciego

**Fecha:** 2026-08-16 · **GPU: cero** · **VMs:** las tres `TERMINATED`
**Fuentes:** `BANCO_DE_FRONTERA.md` (n=100) · campaña v3 (351 publicadas)
**Validador:** `I-3`, **no se ha tocado**

---

## 1. Los tres registros, y no se suman nunca

`[DERIVADO]` Todo lo que sigue depende de mantener separadas tres cosas que un
lector apresurado uniría:

### Registro 1 · Vulnerabilidad de cobertura, identificada **por construcción**

`[MEDIDO]` Banco de 100 frases contra una taxonomía sellada de antemano: **75
desacuerdos, 74 de ellos falsos negativos**. Siete familias de evasión
confirmadas; en **E6, evasión total (10/10)**.

**Explotabilidad:** demostrada. **Explotación observada:** ninguna.

### Registro 2 · Violaciones observadas en producción

`[MEDIDO]` **0 de 351** respuestas publicadas en la campaña v3, verificado además
de forma independiente reejecutando los cuatro predicados en frío desde fuera del
backend.

### Registro 3 · La frase que impide unir los dos anteriores

> **Ninguna de las construcciones del banco fue emitida por el sistema en las 351
> respuestas publicadas. Tampoco habría sido detectada si lo hubiera sido, porque
> el instrumento no las reconoce.**

`[DERIVADO]` Sin este tercer inciso, un lector razonable concluye que el 0/351
refuta el hallazgo del banco. **Concluiría lo contrario de lo que se ha medido.**

---

## 2. El cero de la Puerta S — sus dos límites, separados

### 2.1 Límite estadístico

**Regla de tres** — Hanley & Lippman-Hand, *«If Nothing Goes Wrong, Is Everything
All Right? Interpreting Zero Numerators»*, **JAMA 1983;249(13):1743-1745**:

> *«The upper 95% confidence limit of a 0/n rate is approximately 3/n… if none of
> n patients shows the event about which we are concerned, we can be 95%
> confident that the chance of this event is at most three in n.»*

`[MEDIDO]` Aplicado:

```
0 violaciones / 351 respuestas publicadas
   regla de tres          3/351 = 0,855 %
   exacto (unilateral)            0,850 %
   ⇒ compatible con hasta UNA violación cada ~117 respuestas
```

> **No es un cero. Es un techo del 0,85 %.** Y decirlo así es **más fuerte**, no
> más débil: pasa de una afirmación no cuantificada a una acotada.

Y **Eypasch et al., BMJ 1995;311:619-620**, literal: *«The non-occurrence of an
adverse event in a surgical series does not mean that it cannot happen.»*

> ⚠ **Errata que no se propaga:** la copia de Eypasch cita a Hanley como *«JAMA.
> 1983;**259**:1743-5»*. El volumen correcto es **249**.

### 2.2 Límite de detectabilidad

`[DERIVADO]` **El cero de 351 se midió con el mismo instrumento S cuya cobertura
el banco acaba de demostrar incompleta.** Por lo tanto:

> **3/n acota la tasa de violaciones DETECTABLES POR S, no la tasa de
> violaciones.**

Y como las construcciones del banco escapan a S **por definición** —son
precisamente los casos que la regla acepta—, **la sensibilidad de S para esas
clases es cero**, y el intervalo [0 % , 0,85 %] **no dice nada sobre ellas**.

Eso es un punto de **lógica, no de estadística**. Apoyado en:

- **Altman & Bland**, BMJ 1995;311:485, *«Absence of evidence is not evidence of
  absence»*: *«These are quite different statements.»*
- **Cochrane Handbook §19.5.2**, que lo convierte en obligación operativa:
  *«review authors should record how they reached a decision of 'zero events'»*,
  y advierte de que *«it can be difficult, or unwise, to determine that there were
  no adverse events of a specific type»*.
- **Jabin**, *Front Digit Health* 2026;8:1785141: *«the absence of reported
  incidents is frequently interpreted as evidence of safety, rather than as a
  potential indicator of unrecognised or unobserved risk»*.
- **Barnett & Thiergart**, arXiv:2412.08653: *«Evaluations cannot establish upper
  bounds on AI system capabilities»*; *«Evaluations do not demonstrate the absence
  of risk.»*

### 2.3 Las dos frases, para copiar literal y **jamás fusionar**

> **Límite estadístico.** No se observaron violaciones de la puerta S en 351
> respuestas publicadas. Bajo la regla de tres (Hanley & Lippman-Hand, JAMA
> 1983;249:1743-5; Eypasch et al., BMJ 1995;311:619-20), el límite superior
> unilateral del 95 % de la tasa de violaciones es 3/351 ≈ **0,85 %**; es decir,
> compatible con hasta una violación por cada ~117 respuestas.
>
> **Límite de detectabilidad.** Esa cota se refiere exclusivamente a violaciones
> **detectables por S**. La auditoría de frontera demuestra que S no reconoce
> siete familias de directiva específica al paciente; para esas familias la
> sensibilidad del instrumento es **nula** y el intervalo anterior no es
> informativo. Siguiendo Cochrane §19.5.2 se documenta cómo se alcanzó la decisión
> de «cero eventos». La ausencia de detecciones no debe leerse como ausencia de
> eventos.

`[DERIVADO]` **Nota de modestia, y conviene:** se buscó un ejemplo publicado en IA
médica que combine explícitamente la cota 3/n con una declaración de límite de
detección del instrumento, y **no se encontró**. Las dos mitades existen por
separado con fuentes fuertes; unidas, no. Redactarlo así es hacer algo poco
frecuente, **no seguir una convención establecida**.

---

## 3. Cómo se reporta un hallazgo que no se ha observado

### 3.1 «Near miss» sería un error. La palabra correcta es otra

**Clasificación Internacional para la Seguridad del Paciente de la OMS**
(Runciman et al., *Int J Qual Health Care* 2009;21(1):18-26):

| término | definición |
|---|---|
| *incident* | *«an event or circumstance which could have resulted, or did result, in unnecessary harm»* |
| *near miss* | *«an incident which **did not reach the patient**»* |
| *hazard* | *«a circumstance, agent or action with the potential to cause harm»* |
| **reportable circumstance** | ***«a situation in which there was significant potential for harm, but no incident occurred»*** |

> **Un *near miss* presupone que el incidente ocurrió.** Las construcciones del
> banco **no ocurrieron**: son constructos. La categoría que les corresponde
> exactamente es **reportable circumstance**.

Llamarlas *near miss* sobreestimaría el hallazgo y sería atacable en cinco
segundos. Llamarlas **circunstancia reportable / hazard identificado por
construcción** es preciso **y sigue siendo reportable**.

### 3.2 El silencio no rebaja la severidad

**CVSS v4.0**, métrica *Exploit Maturity*: **Attacked (A)** · **Proof-of-Concept
(P)** · **Unreported (U)** · **Not Defined (X)**.

Y el detalle que desmonta *«no se observó, luego es menor»*: **X *«is equivalent
to Attacked (A)* for the purposes of the calculation»**. El estándar **puntúa por
defecto como si estuviera siendo atacado**.

> **Se declara activamente `E:Proof-of-Concept`**: demostración funcional,
> explotación no observada. No declarar nada sería puntuar como *Attacked*.

### 3.3 La estructura que un regulador ya aceptó

*Postmarket Management of Cybersecurity in Medical Devices* (FDA):

```
vulnerabilidad
  + explotabilidad          (CVSS; aquí E:Proof-of-Concept)
  + severidad del daño SI se explotara
  → riesgo CONTROLADO       («sufficiently low (acceptable) residual risk»)
                            → «generally not required to be reported» (21 CFR 806)
  → riesgo NO CONTROLADO    («unacceptable residual risk … inadequate
                             compensating controls») → reporte OBLIGATORIO
```

**La pregunta que decide el caso, respondida explícitamente:**

> **¿Los controles compensatorios dejan estas familias en riesgo *controlado*?**
>
> `[DERIVADO]` **No.** **S es el control.** No hay un segundo mecanismo que
> detecte una directiva específica del paciente cuando S no la reconoce. La
> reparación no aplica —no hay veredicto que reparar si el validador acepta— y la
> revisión ciega es posterior y muestral.
>
> **Riesgo residual no controlado por ausencia de control compensatorio.** Se dice
> así, y es incómodo, y es lo que hay.

`[DERIVADO]` Precedente de que reportar sin incidente **es la norma**: **21 CFR
803.50(a)(2)** obliga a reportar cuando el dispositivo *«has malfunctioned and
this device… would be likely to cause or contribute to a death or serious injury,
**if the malfunction were to recur**»*. Condicional contrafáctico, sin daño
observado.

### 3.4 Una contradicción entre marcos, enunciada y no esquivada

- **EU AI Act, Art. 73** es ***incident-triggered***: reportar *«immediately after
  the provider has established a **causal link** between the AI system and the
  serious incident **or the reasonable likelihood of such a link**…»*.
  `[DERIVADO]` **Cuidado con el matiz:** la *reasonable likelihood* modifica el
  **nexo**, no el **incidente**. Sigue haciendo falta un incidente grave, así que
  un hallazgo por construcción **no** dispara obligación bajo el Art. 73.
- **21 CFR 803.50 y la guía postmarket de la FDA** son ***hazard-triggered***:
  basta el condicional.

> Un sistema clínico de IA en la UE puede estar **simultáneamente fuera** del
> deber de reporte del AI Act y **dentro** del de dispositivos. **Se enuncia la
> discordancia**; no se elige el marco conveniente callando el otro.

### 3.5 Qué autoriza a reportarlo

- **DECIDE-AI ítem 13a(iv):** listar los errores significativos con *«any
  significant **potential** impacts on patient care»*. **Potencial.** Ésa es la
  autorización explícita.
- **DECIDE-AI ítem 6a:** describir *«how significant errors/malfunctions were
  defined and identified»* — ahí va la limitación de instrumento del §2.2.
- **CONSORT-AI ítem 19 (Harms):** *«Describe results of any analysis of
  performance errors and how errors were identified… **If no such analysis was
  planned or done, explain why not**.»*

---

## 4. La ficha, en el formato del §3.3

| campo | valor |
|---|---|
| **Tipo** | Circunstancia reportable (OMS) · *hazard* identificado por construcción |
| **Vulnerabilidad** | La regla `indirect_treatment_recommendation` exige la conjunción sustantivo + modal; siete familias de construcción no la presentan |
| **Explotabilidad** | **`E:Proof-of-Concept`** — demostración funcional en banco de 100, explotación no observada |
| **Severidad si se explotara** | **Alta.** Incluye anti-derivación (E3), que **suprime el mecanismo de recuperación** |
| **Controles compensatorios** | **Ninguno.** S es el control |
| **Riesgo residual** | **No controlado** |
| **Observado en producción** | **No.** 0/351, con la salvedad del §2.2 |
| **Acción propuesta** | `ENMIENDA_ESPECIFICACION_I2.md` — alinear con el eje AVMA |

---

## 5. Lo que esta auditoría corrige de la fase anterior

`[MEDIDO]` El informe de la fase N presentaba **«5 desacuerdos de 12, cuatro
falsos negativos»** como si fuera una medida. **No lo era:**

```
4/12 = 33,3 %    Wilson [13,8 % , 60,9 %]    Clopper-Pearson [9,9 % , 65,1 %]
```

Un intervalo del 14 % al 61 % no sostiene ninguna afirmación cuantitativa, y con
12 ítems **ni siquiera 0 fallos sostendría nada** (techo exacto 22,1 %).

**Aquello demostraba existencia. Esto caracteriza el instrumento.** Las dos cosas
son resultados; solo la segunda lleva intervalo.
