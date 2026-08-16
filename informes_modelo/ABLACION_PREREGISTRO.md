# Pre-registro de la ablación — sellado ANTES de encender la ventana 2

**Fecha:** 2026-08-15 · **Base:** `CAMPANA_FINAL_RESULTADO.md` (n = 400, C rechaza con 96/400)
**Coste unitario medido:** una campaña de 400 turnos = **95 min de GPU** · **VMs:** las tres `TERMINATED`

> §5.7 del prompt maestro: *«Esto no se improvisa después. Decídelo y escríbelo
> antes de gastar la primera hora.»* Este documento existe para que la ventana 2
> no empiece discutiendo su propio diseño.

---

## 1. El presupuesto, con el coste real y no con una estimación

`[MEDIDO]` Una campaña completa de 400 turnos costó **95 minutos**. Con ese número:

| Diseño | celdas | **h-GPU** |
|---|--:|--:|
| 2³ completo × 3 semillas | 24 | **38,0** |
| 2³ completo × 2 semillas | 16 | 25,3 |
| 2² completo × 3 semillas | 12 | 19,0 |
| **TODO-ACTIVO × 3 semillas** | **3** | **4,8** |

`[DERIVADO]` **El 2³ × 3 semillas que §3.8 propone cuesta 38 horas de A100.** Para
un equipo de estudiantes que paga cada minuto, eso no es un diseño: es una cifra
que hay que mirar antes de comprometerse a ella.

---

## 2. La decisión: dos fases, y la segunda es CONDICIONAL

**El error de diseño que este pre-registro evita** es gastar 38 horas atribuyendo
un efecto **que puede no existir**. La pregunta primaria no es «¿cuánto aporta
cada factor?», es **«¿la combinación pasa la puerta?»**. Y esa la responde una
sola celda.

### Fase A — ¿pasa? *(3 celdas, 4,8 h-GPU)*

```
condición    TODO-ACTIVO  =  G.1 + H + I + §3.1, los cuatro a la vez
n            400 turnos por celda (9 corridas × 45)
repeticiones 3 semillas independientes
comparador   la línea base ya medida (96/400 = 24,00 %), sin gastar GPU nueva
```

**Resultado primario:** fallos de contrato en la celda TODO-ACTIVO, contra
`c ≤ 13/400` del plan v3.

**Contraste:** test **pareado por pregunta** contra la línea base. Es mucho más
potente que comparar dos proporciones, porque las 45 preguntas no son
intercambiables —tres fallan 9/9 y veinte pasan 9/9— y el pareo cancela ese
efecto. `[MEDIDO]` La variabilidad entre corridas de 45 es **σ = 2,43 pts**, con
error típico de **1,40 pts** sobre tres; el efecto esperado si los cuatro frentes
funcionan es de **~20 pts**. La potencia no es el problema aquí.

### Fase B — ¿a qué se debe? *(condicional, 2³ × 3 = 38 h-GPU)*

**Solo se ejecuta si la Fase A pasa la puerta.** Si TODO-ACTIVO no pasa, no hay
efecto que atribuir y la ablación completa sería gastar 38 horas en describir un
fracaso que ya se conoce.

Si se ejecuta: **2³ completo, nunca fraccionado.** Con k = 3 un diseño de
resolución III confundiría cada efecto principal con una interacción de dos
factores, que es exactamente lo que hay que desconfundir. El fraccionado compensa
a partir de k ≈ 5-6.

`[DERIVADO]` **Si el presupuesto no da para 38 h**, la alternativa declarada es
**2² completo (G.1 × I) con H fijo activo, × 3 semillas = 19 h**, y se declara el
tercer factor como **exploratorio**, no como medido. Lo que **no** vale es
fraccionar el 2³.

---

## 3. Multi-semilla: obligatorio, y por qué

`[MEDIDO]` Tasa de fallo de contrato por corrida en la campaña v3:

```
22,2  28,9  24,4  24,4  26,7  22,2  22,2  22,2  22,2
media 23,95 %   σ 2,43 pts   rango 6,7 pts
```

> **Entre corridas idénticas —mismo código, mismo modelo, misma hora— hay 6,7
> puntos de rango.** Una sola corrida no distingue una mejora de 5 puntos de la
> suerte, y declararla sería la señal de desvío que el GOAL lista.

**Protocolo:** tres semillas por celda, deltas por semilla, y sobre esos deltas
**bootstrap BCa + permutación *sign-flip***. Se reporta el intervalo, no solo el
punto.

`[DERIVADO]` **Limitación que se declara ahora:** el backend usa `seed = −1` y no
fija semilla, así que «tres semillas» son en realidad **tres repeticiones
independientes**. Es equivalente a efectos de varianza pero **no reproducible
turno a turno**, y eso se dice en el informe en vez de fingir un control que no
existe. Fijar la semilla sigue en la lista de deuda (≈ medio día).

---

## 4. La ortogonalidad — se demuestra, y es GRATIS

`[MEDIDO]` La campaña v3 ya refutó que la segregación por ámbito sea perfecta:
**3 de 96 fallos cruzan la frontera**. Así que la ortogonalidad **no se asume**.

**El test no cuesta un segundo de GPU:** se guarda el **texto de todas las
respuestas de todas las celdas** y se reejecutan **los cuatro validadores sobre
las cuatro condiciones**. La matriz cruzada validador × condición se calcula en
frío.

| | base | +G.1 | +H | +I |
|---|---|---|---|---|
| `ambiguous_parameter_claim` | | | | |
| `unsupported_numeric_claim` | | | | |
| `indirect_treatment_recommendation` | | | | |
| `missing_evidence_attribution` | | | | |

**Si sale diagonal**, la independencia queda **demostrada** y se pueden omitir
ablaciones adicionales **con justificación real en lugar de asumida**. Si no sale
diagonal, la Fase B es obligatoria y el diseño factorial gana su coste.

`[DERIVADO]` **El punto débil es concreto y hay que vigilarlo:** la gramática del
Bloque H **cambia el texto**, y ese texto alimenta el léxico de recomendación del
Bloque I. Es la interacción más probable de las tres.

---

## 5. Lo que se pre-registra, punto por punto

1. **Resultado primario:** fallos de contrato de primera generación en la celda
   TODO-ACTIVO, sobre n = 400, contra `c ≤ 13`.
2. **Resultados secundarios**, todos con los cuatro denominadores y Wilson: la
   tasa por clase, `pass^6` por consulta (i.i.d. **y** empírico), el histograma
   `pass^K` por pregunta, la latencia p50/p95 y la distribución de
   `provider_calls`.
3. **Regla de decisión**, la misma que ya está estrenada: si la clase objetivo de
   un frente no cae, ese frente se revierte; si cae pero sube otra y el total no
   mejora, **también**.
4. **Criterios de exclusión:** ninguno. Los turnos muertos siguen en el
   denominador.
5. **Semillas:** tres repeticiones por celda, con `seed = −1` declarado.
6. **Checkpoint del modelo:** `qwen3.6:27b-q4_K_M`,
   `digest a50eda8ed977ab48a12431878896b27ffd5cef552c17af3317d9623b939a7f1e`,
   `Q4_K_M`, verificado por `run_fingerprint` en cada corrida.
7. **Prompts:** los del árbol medido, verbatim en el repositorio.
8. **Historial de pilotaje:** la campaña v3 del 15-ago es el piloto, y sus
   resultados están publicados enteros, incluido el rechazo.

---

## 6. Lo que NO se hace

- **No se fracciona un factorial de tres factores.**
- **No se declara nada con una sola semilla.**
- **No se ejecuta la Fase B si la Fase A no pasa.** No hay efecto que atribuir.
- **No se descuenta ningún turno** del denominador.
- **No se cita un solo denominador.**
- **No se mide un frente cuya firma clínica no esté archivada.** G.1 e I.2
  dependen de `FIRMA_VETERINARIA_G1.md` y `FIRMA_VETERINARIA_I1.md`; sin ellas
  esas celdas **no existen** y la Fase A no se puede montar.

---

## 7. La condición de entrada, dicha sin rodeos

`[DERIVADO]` La celda TODO-ACTIVO **no se puede construir hoy**. G.1 e I.2 están
bloqueados por firma clínica, y sin ellos la combinación que la Fase A mide no
existe. Eliminando el 100 % de lo que sí está desbloqueado —H, §3.1 y la parte de
`unsupported_status_claim` que H alcanza— quedan **64/400 = 16,00 %**, cinco veces
la puerta.

> **Este pre-registro está listo y sellado. La ventana 2 empieza el día que
> lleguen las dos firmas, no antes.**
