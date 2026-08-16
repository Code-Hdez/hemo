# M.2 — regla de decisión, sellada ANTES de medir

**Fecha:** 2026-08-15 · **Ataca:** `ambiguous_parameter_claim` (31 de 96) y la parte
de `unsupported_status_claim` (7) que nace de la misma ambigüedad
**GPU usada al escribir esto: cero** · **VMs:** las tres `TERMINATED`
**Se sella con** `BLOQUE_M2_REGLA_DE_DECISION.sha256`

> GOAL, `I-5`: *«REGLA SELLADA ANTES DE MEDIR. Si la clase objetivo no cae se
> revierte; si cae pero sube otra y el total no mejora, también.»*

---

## 0. El hallazgo que obligó a cambiar el diseño del plan

`[MEDIDO]` El GOAL, §4.3, proponía desambiguar **por el nombre**: *«nunca
`neutrófilos` a secas: siempre `el recuento absoluto de neutrófilos`»*. Ejecutando
el validador de producción en vez de leerlo:

| redacción | validador |
|---|---|
| «Los neutrófilos están altos» *(lo que escribe hoy el modelo)* | **inválido** |
| «El recuento absoluto de neutrófilos es de 8.4 x10^3/uL, dentro del rango» | **inválido** |
| «NEU: 8.4 x10^3/uL, dentro del rango» | **inválido** |
| «Neutrófilos, recuento absoluto.⏎Valor medido: 8.4 x10^3/uL, dentro del rango» | **VÁLIDO** |

**La desambiguación por el nombre no funciona.** `generic_family_mentions` marca
`generic_family=True` para **cualquier** alias del absoluto —`neutrofilos`, `NEU`,
`NEU#`—; solo el porcentaje se desambigua solo, porque su alias lleva `%`, `pct` o
`porcentaje` dentro y `_is_explicit_percent` lo detecta.

`[MEDIDO]` Lo que sí funciona es **separar la etiqueta del valor en cláusulas
distintas**: la cláusula que nombra el parámetro no lleva cifra ni estado, y la que
los lleva no nombra el parámetro. El predicado exige **las dos cosas en la misma
cláusula**.

> **El punto entre las dos cláusulas es el mecanismo entero.** Hay un test que lo
> fija (`test_la_etiqueta_y_el_valor_van_en_clausulas_distintas`) para que nadie
> lo «arregle» concatenando.

---

## 1. Lo implementado

`backend/app/modules/llm_chat/application/services/slot_rendering.py`

- `construir_esquema_de_turno(hechos)` — el `enum` de `parametro` contiene **solo
  los códigos del turno**, nunca prosa: el modelo emite `NEU`, no «neutrófilos».
- `estado` es un `enum` de los tres estados que **calcula el servidor**.
- `valor` es un **`enum` de literales decimales en cadena**. Nunca
  `minimum`/`maximum`: no se enforcan para no-enteros.
- `fecha` va en el `enum` **a propósito**: aporta los dígitos que el validador
  numérico acepta como respaldo, así que conviene que el respaldo sea real.
- `renderizar_afirmaciones()` ensambla con la etiqueta y el valor **separados**.

**Los `enum` se construyen por turno**, no una vez. `[MEDIDO]` Es la versión
mecánica del gradiente: 0 % de fallo con 1 hecho autorizado, 5,7 % con 2, 11,5 %
con 4. Menos candidatos, menos confusión. Y el selector **nunca** deja fuera un
parámetro pedido (0 de 405), así que restringir no cuesta cobertura.

**Lo que NO se ha tocado:** el validador (`I-2`), qué está autorizado, ni el
prompt. El porcentaje **sigue** siendo un hecho citable.

---

## 2. La regla, decidida antes de ver el resultado

| Resultado en la ventana 2 (n = 400) | Decisión |
|---|---|
| `ambiguous_parameter_claim` **< 5** y el total de fallos baja | **Se conserva** |
| `ambiguous_parameter_claim` **≥ 5** | **Se revierte.** El mecanismo era la imposibilidad, no la obediencia: si sigue apareciendo, la premisa es falsa y hay que rehacerla, no ajustarla |
| Cae pero **sube otra clase** y el total no mejora | **Se revierte.** Cambiar un rechazo por otro no es una mejora |
| Cae, pero **p50 > 15 s o p95 > 25 s** | **Se revierte.** `[MEDIDO]` El p95 ya está en 24,31 s: el margen es de 0,69 s |
| Cae, pero `provider_calls` medio **sube** | **Se revierte** |
| Cae, pero la revisión ciega califica las respuestas **peores por daño** | **Se revierte** |

**n de la medición:** el plan v3 completo, **400 turnos**, con los cuatro
denominadores, Wilson y `pass^6`. **Multi-semilla**: una sola no declara nada.

---

## 3. Lo que hay que vigilar, y está dicho antes

1. `[DERIVADO]` **La naturalidad.** `[MEDIDO]` El servidor escribiría el **25,3 %**
   del texto publicado —por debajo del 60 % que el GOAL marca como señal de
   formulario—, pero el formato de dos cláusulas **es** más rígido que una frase.
   Va a la revisión ciega de M.7, y va con la rúbrica de **daño**, no de
   preferencia.
2. `[DERIVADO]` **El coste de compilar el `enum`.** `[MEDIDO]` 1400 ms con 3
   valores y 2574 ms con 300. Aquí serán decenas, pero se registra por turno
   porque entra directo en el p95.
3. `[DERIVADO]` **`maxLength` no está confirmado** que propague a la gramática
   —`enum`, `const` y `pattern` sí—. Mientras no se mida, **el servidor trunca** y
   no se confía en el esquema.
4. **`think: false` explícito** en toda petición con `format`. `[MEDIDO]` Sin él el
   modelo gasta el presupuesto entero pensando y `content` vuelve **vacío**.
5. **No mezclar `tools` con `format`.** Ya está garantizado en el adaptador
   (`if request.response_schema is not None and not request.tools`), y se deja
   dicho para que nadie lo relaje.

---

## 4. Lo que este bloque NO promete

- **No retira el validador.** Ni una comprobación.
- **No cambia qué está autorizado.** El porcentaje sigue en el contexto citable;
  retirarlo es G.1 y **necesita firma**.
- **No alcanza `indirect_treatment_recommendation`.** `AUTORRECHAZO_DEL_VALIDADOR.md`
  demuestra por qué: la regla es léxica y rechaza igual el texto que escribimos
  nosotros.
- `[DERIVADO]` **No hace pasar la Puerta C.** Ni este bloque ni todos los del
  servidor juntos: 6,75 % frente a 3,25 %. Está en `ALCANCE_DE_LA_VIA_SERVIDOR.md` §4.
