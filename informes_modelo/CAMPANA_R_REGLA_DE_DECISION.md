# Campaña pass^5 del Bloque D — regla de decisión, escrita antes de medir

**Sellada:** 2026-08-14, antes de encender ninguna máquina.
**Rama bajo prueba:** `bloque-d-turnguard` @ `5f637000`
**Pre-registro que la gobierna:** `PUERTAS_v2_PREREGISTRO.md` (SHA-256 en su `.sha256`)

---

## Qué se mide

5 corridas × 45 preguntas = **225 turnos**, el plan pre-registrado completo, con
la desambiguación absoluto/porcentaje activa.

`K = 5` por pregunta es exactamente lo que la **Puerta R** exige, así que esta
campaña puntúa las cuatro puertas a la vez: **S**, **C**, **R** y **D**.

## Qué NO se hace

- No se toca ningún umbral del `OutputValidator`.
- No se reordena el prompt: el Bloque C dio su veredicto y el reordenamiento es
  un cambio distinto, con su propia puerta.
- No se añade ningún reintento, ni en el arnés ni en el backend.
- No se descuenta del denominador ningún turno que el sistema **sí** atendió.

## La regla, decidida antes de ver el resultado

`[DERIVADO]` La hipótesis concreta que se pone a prueba es **estrecha y
falsable**: el cambio ataca `ambiguous_parameter_claim`, y solo esa clase. En la
corrida del 14-ago fue **4 de 14** rechazos, todos terminales.

| Resultado | Decisión |
|---|---|
| `ambiguous_parameter_claim` **cae a 0** en 225 y ninguna otra clase empeora | **Se conserva.** La hipótesis se sostiene: el alcance acotado antes de generar elimina la clase |
| Cae, pero **otra clase sube** de forma que el total de fallos de contrato **no** mejora | **Se conserva el hallazgo y se revierte el cambio.** Cambiar un rechazo por otro no es una mejora, y declararlo lo sería de desvío |
| **No cae** | **Se revierte.** Sería el cuarto intento fallido sobre el mismo eje, y I-10 obliga a cambiar de hipótesis, no de intento |
| C **acepta** (≤ 8 fallos en 225) | Se abre la **Fase 4**: `provider_calls == 1` |
| C **rechaza** | No se pasa a la Fase 4. Es la regla y se respeta |

**Curtailment pre-registrado:** en cuanto los fallos de contrato lleguen a **9**,
el plan ya no puede aceptar. Se para la campaña y se rechaza. No altera α ni β
porque no adelanta ninguna aceptación — pero **las 5 corridas se completan igual**
si el presupuesto de GPU lo permite, porque la Puerta R necesita `K = 5` por
pregunta aunque C ya haya decidido.

## Lo que se publica pase lo que pase

Los cuatro denominadores, el CONSORT con la causa de cada baja, las cinco
semillas, el histograma pass^5 por pregunta y el recuento por código de rechazo.
Y la verificación job a job del despliegue que precede a la campaña.

## Una limitación que se declara ahora, no después

`[DERIVADO]` `pass^5` detecta una pregunta que está al 90 % de validez solo el
**40,95 %** de las veces. Si la campaña sale limpia, eso **no** significa que no
queden preguntas frágiles: significa que ninguna cayó en esta muestra. La Puerta
R es una red de detección para dirigir el trabajo, no un certificado.
