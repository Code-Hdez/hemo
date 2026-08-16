# J.1 — Qué aporta de verdad la reparación

**Fecha:** 2026-08-15 · **Datos:** `campana_r_2026-08-14`, n = 225 · **GPU usada: cero**
**Estado de las VMs:** las tres `TERMINATED`, verificado.

> El GOAL I-9 condiciona la generación única a que la Puerta C pase. Este
> documento no adelanta esa decisión: mide **qué se perdería** al retirar la
> reparación, para que cuando llegue el momento la decisión esté tomada con la
> cifra delante y no con la literatura.

Toda cifra va marcada `[MEDIDO]`, `[DERIVADO]` o `[INFERIDO]`.

---

## El resumen, en tres líneas

`[MEDIDO]` La reparación salva 21 de 48 fallos de contrato (43,8 %). Un
**reintento ciego** —volver a generar sin decirle al modelo qué falló— habría
salvado 16,8 (35,0 %), y la diferencia cae **dentro** del intervalo de la
reparación.

`[MEDIDO]` Pero el agregado esconde lo importante: la reparación es
**intercambiable** con un reintento ciego en las preguntas estocásticas, y es
**lo único que funciona** en las estructurales — donde un reintento ciego no
puede salvar nada por construcción.

`[MEDIDO]` Y ese «lo único que funciona» son **cinco turnos de 225**, todos de la
**misma pregunta**.

---

## 1. El estimador, y por qué es legítimo

No se puede correr un reintento ciego sobre la campaña sin volver a gastar GPU.
Pero la campaña **ya contiene** el estimador exacto de lo que ese reintento
habría conseguido:

> `p_ciego(pregunta)` = fracción de las 5 corridas en que la **primera**
> generación de esa pregunta superó el contrato.

Con `seed = −1`, cada corrida es un sorteo independiente de la misma
distribución. La probabilidad de que un reintento ciego de esa pregunta salga
válido **es** `p_ciego`, medida sobre 5 tiros. Es el mismo argumento que sostiene
la Puerta R, aplicado a otra pregunta.

`[DERIVADO]` **Su limitación, declarada:** `p_ciego` se estima con K = 5, así que
para una pregunta concreta el error es grande (±0,20 por tiro). La esperanza
agregada sobre 48 fallos es mucho más estable que cualquiera de sus términos, y
por eso solo se usa agregada.

---

## 2. El agregado: indistinguibles

`[MEDIDO]` Sobre los **mismos 48 fallos**:

| Mecanismo | Salva | % | |
|---|---|--:|---|
| **Reparación** (observado) | 21 / 48 | **43,8 %** | Wilson 95 % [30,7 · 57,7] |
| **Reintento ciego** (esperanza) | 16,8 / 48 | **35,0 %** | — |

**Diferencia +8,7 pts, dentro del intervalo.** Con n = 48 no se distingue una
cosa de la otra.

`[MEDIDO]` Y la reparación **cuesta el doble de latencia**:

| | n | p50 | máx |
|---|--:|--:|--:|
| 1 llamada | 177 | **10,08 s** | 18,87 s |
| 2 llamadas | 21 | **22,17 s** | 39,73 s |

**×2,20.** Coherente con la literatura: *Try Again, Don't Look Back*
(arXiv:2607.26117) mide que el resampling ciego iguala o supera al self-repair en
modelos pequeños y medianos **consumiendo 2,5-5,5× menos tokens**.

---

## 3. El desglose, que es donde está el hallazgo

`[MEDIDO]` Separando las preguntas por si su fallo es estocástico o estructural:

| | n | Reparación | Reintento ciego |
|---|--:|---|---|
| **Estocásticas** (`p_ciego > 0`) | 33 | 16 = **48,5 %** · [32,5 · 64,8] | 16,8 = **50,9 %** |
| **Estructurales** (`p_ciego = 0`) | 15 | 5 = **33,3 %** · [15,2 · 58,3] | **0,0 %** |

> **En las estocásticas el reintento ciego es nominalmente MEJOR** —50,9 % frente
> a 48,5 %— con la mitad de latencia y una fracción de los tokens. La reparación
> no está aportando nada ahí; está pagando el doble por el mismo resultado.
>
> **En las estructurales es lo único que existe.** Un reintento ciego tiene
> probabilidad **cero** de salvarlas: son preguntas que fallan las cinco veces.

### Y las estructurales son tres preguntas, no quince turnos

`[MEDIDO]`

| Pregunta | `p_ciego` | Reparada | Clase |
|---|--:|---|---|
| **`GEN-05`** «¿Por qué puede salir bajo?» | 0 % | **5 / 5** | `indirect_treatment_recommendation` |
| `HIS-02` | 0 % | 0 / 5 | `unsupported_numeric_claim` + `ambiguous_parameter_claim` |
| `SEL-01` «¿Qué valores aparecen fuera del rango?» | 0 % | 0 / 5 | `ambiguous_parameter_claim` |

`[MEDIDO]` **Todo el valor irreemplazable de la reparación en 225 turnos son los
cinco `GEN-05`.** En las otras dos preguntas estructurales la reparación falla
**10 de 10**.

`[DERIVADO]` **Eso es 5 turnos de 225 = 2,2 %**, comprado a cambio de duplicar la
latencia del 10,6 % de los turnos respondidos.

---

## 4. La consecuencia para el plan, y no es la que estaba escrita

El GOAL I-9 dice que la generación única llega «cuando C pase, no antes». La
medición añade una condición **más concreta y más útil**:

> **La reparación tiene exactamente una función que nada más cubre: rescatar
> `GEN-05`. Y `GEN-05` es justo el caso tipo del Bloque I** —una pregunta causal
> del ámbito `general` que dispara `indirect_treatment_recommendation` 5 de 5
> veces—.
>
> `[DERIVADO]` **Si el Bloque I resuelve `GEN-05` antes de generar, la reparación
> se queda sin su única contribución irreemplazable**, y retirarla deja de ser
> una pérdida: pasa a ser la eliminación de un mecanismo que duplica la latencia
> para hacer lo que un reintento haría igual de bien — y que además está
> prohibido.

Es una condición comprobable, no una intuición: se mide con la misma campaña.

---

## 5. β local: no medible con estos datos, y hay que decirlo

*Verify, Repair, Repeat, or Stop?* (arXiv:2607.17641) mide en β ≈ 0,94 bajo
estrés la probabilidad de que la reparación **dañe una salida ya válida**, y
avisa de algo peligroso: la tasa de aceptación del verificador puede seguir
subiendo mientras la validez real ya está cayendo.

`[MEDIDO]` **Ese número no se puede estimar aquí**, y la razón es estructural:

```
turnos en que el reparador vio un candidato válido: 0 de 225
```

La reparación **solo se dispara sobre salidas que ya fallaron la validación**. En
225 turnos no hay ni una observación del reparador actuando sobre un válido, así
que β es literalmente inobservable en este diseño. Inventar una cifra a partir
del 43,8 % de éxito sería confundir dos condicionales distintos.

`[DERIVADO]` **Lo que costaría medirlo:** pasar el reparador por los **177**
turnos válidos de primera pasada y revalidar la salida. Son 177 generaciones,
≈ 35 min de GPU, y produce β directamente. **Es la medición que la literatura
pide y que nadie publica**, y tiene valor para la tesis con independencia de lo
que se decida sobre la reparación.

> Se deja propuesta, no ejecutada. No entra en ninguna ventana sin orden
> explícita.

---

## 6. Lo que se pierde exactamente al retirar la reparación

`[DERIVADO]` Sobre los mismos 225 turnos, sin ningún otro cambio:

| | con reparación | sin reparación |
|---|---|---|
| **Puerta C** validez 1.ª pasada | 177/225 = 78,67 % | 177/225 = **78,67 %** — sin cambio |
| **Puerta D** indisponibilidad | 0/225 | 0/225 — **sin cambio** |
| turnos **sin respuesta publicada** | 27/225 = 12,00 % | 48/225 = **21,33 %** |
| **Puerta S** afirmación | ≥ 98,4984 % (0 en 198) | ≥ **98,3217 %** (0 en 177) |
| latencia p50 del turno reparado | 22,17 s | — (no existe) |

**C no se mueve** porque ya cuenta `RESPONDIDO_REPARADO` como fallo. **D tampoco**,
porque un fallo terminal de contrato no es una indisponibilidad. Lo que se paga
son dos cosas que ninguna puerta vigila hoy: **uno de cada cinco turnos se
quedaría sin respuesta**, y la Puerta S pierde 0,18 pts de afirmación porque su
denominador es lo publicado.

> `[INFERIDO]` Ese 21,33 % es el número que decidirá si la generación única es
> aceptable **clínicamente**, y no lo decide ninguna de las cuatro puertas. Es
> material para la revisión veterinaria del Bloque K, y conviene preguntarlo
> antes de llegar allí: *¿prefiere el veterinario una respuesta más lenta o
> ninguna respuesta?*

---

## Hipótesis vivas

1. **β local.** Inobservable en este diseño; el experimento que lo mide está
   especificado en §5 y cuesta ~35 min.
2. **Por qué la reparación arregla `GEN-05` 5/5 y `SEL-01` 0/5.** Las dos son
   estructurales; una cede al feedback textual y la otra no. Sin caracterizar.
3. **Si la reparación empeora la calidad de lo que salva.** Pasa el validador por
   definición, pero nadie ha comparado una respuesta reparada con una válida de
   primera. Es trabajo de la revisión ciega del Bloque K.
4. **Si el reintento ciego, ya que iguala a la reparación, es preferible.** No:
   sigue siendo un reintento y el GOAL lo prohíbe. Se mide para saber qué se
   pierde, no para proponerlo.
