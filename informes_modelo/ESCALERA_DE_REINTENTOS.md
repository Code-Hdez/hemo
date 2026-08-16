# La escalera de reintentos — peldaños vivos y peldaños muertos, contados

**Fecha:** 2026-08-15 · **Fuente:** ledger de la campaña v3, **405 turnos**
**GPU: cero** — se cuenta sobre datos que ya existen · **VMs:** las tres `TERMINATED`

> GOAL, I-6: *«La escalera se cuenta sobre el ledger.»* Y §N.3: *«0 invocaciones →
> código muerto, se retira sin discusión. Invocaciones pero 0 cambios de veredicto
> → se retira con nota. Sólo los que cambian veredicto merecen experimento propio.»*

---

## 1. Antes de contar: ¿puede el ledger registrar los cinco peldaños?

`[MEDIDO]` **Sí.** El vocabulario es cerrado y son exactamente cinco:

```python
GENERATION_ROUTES = {main, repair, steer, last_resort, tool}
```

y los cinco están cableados a `generation_route=` en el caso de uso —líneas
**1885** (`main`), **2048** (`repair`), **4801** (`tool`), **4925**
(`last_resort`) y **5065** (`steer`)—. Además, cualquier etiqueta fuera del
vocabulario se registraría como `unknown:<x>`, y **no apareció ninguna**.

> **Esto importa más que el recuento.** Un cero puede significar «no se invocó» o
> «el ledger no sabe registrarlo», y **son conclusiones opuestas**. Aquí está
> comprobado que es lo primero.

---

## 2. El recuento `[MEDIDO]`

| peldaño | invocaciones / 405 turnos | veredicto |
|---|--:|---|
| `main` | **356** | vivo |
| `repair` | **48** | vivo |
| `steer` (`_steered_candidate`) | **0** | **código muerto** |
| `last_resort` | **0** | **código muerto** |
| `tool` (tool-call) | **0** | **código muerto** |

`[MEDIDO]` Los 49 turnos restantes no registran llamada: son los **terminales**,
y siguen en el denominador.

---

## 3. La reparación cambia el veredicto **el 100 % de las veces que se dispara**

`[MEDIDO]`

```
repair invocado          48
de esos, publicaron      48        → 100,0 %
validation_status        {'passed': 48}
```

> **No es un peldaño marginal: es el único de los cuatro auxiliares que existe, y
> cuando actúa, funciona siempre.** Retirarlo hoy convertiría 48 turnos publicados
> en 48 fallos terminales — pasaría la tasa de fallo de contrato del **24,00 %** al
> **35,80 %**.

`[DERIVADO]` Eso reordena la lista de retirada del plan: `repair` iba la primera
**porque se creía la más costosa**, y resulta ser **la única con eficacia medida
del 100 %**. Las tres que iban detrás **ya están muertas** y no hace falta
retirarlas: hace falta **borrarlas**.

---

## 4. Lo que esto NO autoriza todavía

`[DERIVADO]` El GOAL avisa, y tiene razón: **no se retira un peldaño antes de
M.2/M.3.** Este recuento es del sistema **anterior** a que el servidor escriba las
cifras. Es plausible —y hay que medirlo, no suponerlo— que con M.2/M.3 activos la
reparación tenga mucho menos que reparar y **se vacíe sola**.

**Lo que sí queda establecido, y no cambiará:**

- `steer`, `last_resort` y `tool` están **muertos en la línea base**. Si tras
  M.2/M.3 siguen a cero, se borran con dos mediciones detrás en vez de una.
- `repair` **no se toca** hasta ver su recuento con el servidor escribiendo.

---

## 5. `httpx retries` — el último de la lista, y se queda

`[MEDIDO]` `reintentos_de_conexion.py`, en local y sin GPU:

| medida | resultado |
|---|---|
| servidor levantado: conexiones · bytes | **1** · **210** (la petición, enviada una vez) |
| puerto que rechaza: `retries=0` | 0,49 ms |
| puerto que rechaza: `retries=1` | 0,66 ms |
| coste del reintento | **+0,17 ms** |

**El reintento se dispara antes de enviar un byte**, así que **no puede producir
una segunda generación ni inflar `provider_calls`**. `[DERIVADO]` `retries=0` es
una decisión de robustez y latencia, no de corrección, y **con la Puerta D pasando
con holgura el criterio por defecto es dejarlos**.

---

## 6. La excepción que casi nadie escribiría

`provider_calls == 1` cuenta las llamadas **que hace el backend**. `[MEDIDO]` En la
campaña v3: **308 de 405 turnos (76,05 %)** con una sola llamada.

> **Pero con `format` y un modelo de *thinking*, Ollama puede hacer DOS pasadas a
> `llama-server` por cada una de esas llamadas** —el `forceImmediate` /
> `currentFormat = nil` de v0.32.6— **y esas pasadas son invisibles al ledger**.
>
> Declarar «generación única» sin decir esto sería **una afirmación falsa por
> omisión**. La redacción correcta es: *una llamada al proveedor por turno; el
> proveedor puede internamente hacer dos pasadas al motor, contadas en el anexo*.

`[MEDIDO]` En F.1 el residuo de reloj fue **~3 ms (0,1 %)** en las tres
condiciones, lo que **no es compatible** con una segunda pasada completa. Es
evidencia contra la doble pasada **en aquel montaje**, con `think:false` y un
esquema de tres valores. **No autoriza a extenderlo al esquema del turno**, y por
eso la excepción sigue escrita.

---

## 7. Resumen para la siguiente sesión

```
BORRAR (0 invocaciones en 405 turnos, ledger verificado):
   steer · last_resort · tool           ← confirmar a cero tras M.2/M.3 y borrar

NO TOCAR:
   repair        48 invocaciones, 100 % de cambio de veredicto
   httpx retries pre-transmisión, +0,17 ms, no amenaza la idempotencia
```
