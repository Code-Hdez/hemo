# M.3 — regla de decisión, sellada ANTES de medir

**Fecha:** 2026-08-15 · **Ataca:** `unsupported_numeric_claim` (14 de 96, **13 en
`hemogram_history`**) y el resto de `unsupported_status_claim` (7)
**GPU usada al escribir esto: cero** · **VMs:** las tres `TERMINATED`
**Se sella con** `BLOQUE_M3_REGLA_DE_DECISION.sha256`

> GOAL, `I-4`: *«El primario de H es `atribucion_numerica.py` —`mal_atribuida` → 0,
> `inventada` → 0—, **no el contador del validador**, que caería a cero por
> construcción.»*

---

## 0. Por qué el contador del validador mentiría a nuestro favor

`[MEDIDO]` La ruta numérica de `claim_validation` compara **fragmentos** y le basta
**una** intersección no vacía con el hecho que dio el solape de términos:

```
cifra correcta        SOPORTADO
cifra CRUZADA         SOPORTADO      ← el valor de OTRO parámetro
cifra INVENTADA       SOPORTADO      ← 9.99, que no existe en ningún hecho
delta DERIVADO        RECHAZADO
```

El tokenizador parte `4.52` en `4` y `52`, y **la fecha del estudio aporta `2026`,
`01`, `10`**. Sin la fecha en la frase, esa misma cifra inventada **sí** se rechaza.

> **Bajo una gramática, `unsupported_numeric_claim` cae a 0 por construcción**: si
> el modelo no puede emitir un literal no autorizado, la clase desaparece sin que
> se haya demostrado nada sobre cifras alucinadas. Leer ese cero como éxito sería
> el autoengaño que este pre-registro existe para impedir.

---

## 1. Lo implementado

Mismo módulo que M.2 —`slot_rendering.py`—, más la pieza que faltaba:

**`sanear_prosa(texto)`** aplica al **borrador propio** los predicados existentes
antes de ensamblar, tal como autoriza el Anexo A §5. Recorta una oración cuando
lleva:

- **una cifra del paciente** — las escribe el servidor desde el `enum`;
- **una afirmación de estado** — ídem;
- **un predicado de seguridad** — `indirect_treatment`, `definitive_diagnosis`,
  `dose_instruction`.

**Esto no es tocar el validador (`I-2`).** Es aplicarlo, sin cambiarlo, a un texto
que todavía no se ha publicado.

`[MEDIDO]` **Se recorta, no se reintenta** (Anexo A §6). Reintentar multiplicaría
`provider_calls` y chocaría de frente con la Fase 4. El coste del recorte se mide
como sobre-rechazo en M.5, no se esconde.

### 1.1 Un defecto que encontró un test, no la lectura

`[MEDIDO]` El separador de oraciones parte «1. Los glóbulos rojos…» en dos, así
que el marcador de lista `«1.»` llegaba solo y **se contaba como oración
recortada**. Habría **inflado el sobre-rechazo de M.5**, que es justo la métrica
que decide si este bloque vale. Corregido con `_SOLO_MARCADOR`, y con su test.

---

## 2. La regla, decidida antes de ver el resultado

### 2.1 Resultado primario — **`atribucion_numerica.py`**, no el validador

| Resultado | Decisión |
|---|---|
| **`mal_atribuida` = 0 y `inventada` = 0** sobre las cifras publicadas, y el total de fallos baja | **Se conserva** |
| `mal_atribuida` > 0 | **Se revierte.** Es exactamente lo que la gramática no arregla, y si sigue ahí el bloque no ha hecho su trabajo |
| `inventada` > 0 | **Se revierte.** Con los literales restringidos por `enum` esto **no debería poder ocurrir**; si ocurre, la premisa mecánica es falsa |
| **`unsupported_numeric_claim` cae a 0 pero el primario no mejora** | **Se revierte igualmente.** Escrito antes de medirlo, y es la tercera regla que el GOAL añade a esta fase |

### 2.2 Las mismas condiciones de siempre

| | |
|---|---|
| Sube otra clase y el total no mejora | **Se revierte** |
| `p50 > 15 s` o `p95 > 25 s` | **Se revierte.** `[MEDIDO]` El p95 ya está en 24,31 s |
| `provider_calls` medio sube | **Se revierte** |
| La revisión ciega la califica peor **por daño** | **Se revierte** |

**n:** el plan v3 completo, **400 turnos**, cuatro denominadores, Wilson y `pass^6`.
**Multi-semilla**: una sola no declara nada.

---

## 3. Lo que orienta el diseño, y está medido

`[MEDIDO]` La tasa de fallo **crece con el número de hechos autorizados**:

| hechos en el contexto | fallos / turnos | tasa |
|--:|---|--:|
| 1 | 0 / 18 | **0,0 %** |
| 2 | 2 / 35 | 5,7 % |
| 4 | 7 / 61 | **11,5 %** |

Gradiente monótono. Con más valores delante, más se confunden — **lo contrario de
un modelo que inventa por falta de datos**. Por eso los `enum` se construyen **por
turno**, con solo los parámetros pertinentes, que además es lo que ya hace el
selector. `[MEDIDO]` Y el selector **nunca** deja fuera un parámetro pedido: **0 de
405**. Restringir no cuesta cobertura.

---

## 4. Lo que este bloque NO promete

- **No prueba que las cifras publicadas de la campaña v3 fueran correctas.** No lo
  autoriza nada: el validador sub-detecta y eso va en `LIMITACIONES.md`.
- **No alcanza `indirect_treatment_recommendation`.** El saneado *podría* borrar
  esas oraciones —`[MEDIDO]` 4 oraciones, 0,22 % del texto—, pero **son la
  etiología que la pregunta pedía**. Cambiar un rechazo por una respuesta que ya no
  responde es lo que la regla prohíbe. **Eso lo decide la firma.**
- `[DERIVADO]` **No hace pasar la Puerta C.** Con M.2, M.3 y §3.1 al 100 % quedan
  **6,75 %** frente a 3,25 %.
