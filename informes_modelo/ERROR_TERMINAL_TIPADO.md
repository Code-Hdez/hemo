# El error terminal tipado — los cinco asertos, por inyección

**Fecha:** 2026-08-15 · **Bloque:** M.9 (Fase 5) · **GPU: cero**
**Tests:** `backend/tests/llm_chat/test_error_terminal_tipado.py` · **VMs:** las tres `TERMINATED`

> GOAL, M.9: *«Mídelo por inyección, no esperando a que ocurra. Un flag de
> solo-test que fuerce el agotamiento de la escalera vale más que diez campañas
> esperando la coincidencia.»*

---

## 1. Por qué esto no es higiene

Suena a limpieza técnica hasta que se ve qué arregla:

> **Los turnos muertos que el método prohíbe descontar del denominador son
> exactamente éstos.** Si un fallo terminal se colara como turno persistido, se
> contaría como si hubiera respondido, y **la tasa publicada sería mejor que la
> real**.

`[MEDIDO]` En la campaña v3 hubo **49 turnos terminales de 405**, y los 49 siguen
en el denominador. Eso solo es cierto si el fallo terminal se registra en vez de
desaparecer.

---

## 2. Los cinco asertos, y cómo se comprueban

Se **fuerza el agotamiento de la escalera** con un doble de proveedor que siempre
devuelve texto inválido. No se espera a que ocurra.

| # | aserto | resultado |
|--:|---|---|
| 1 | **Clase de error tipada**, no un `500` genérico ni un `detail` de texto libre | **✔** `ChatRuntimeUnavailable` con código estable, sin espacios, en minúsculas |
| 2 | **No se persiste ningún mensaje del asistente** | **✔** `roles` no contiene `assistant` |
| 3 | **El ledger registra el turno como fallo terminal**, con su id | **✔** `mark_turn_failed` recibe `error_code` y `client_message_id` |
| 4 | **No queda escritura parcial** — ni turno huérfano, ni memoria movida | **✔** solo puede quedar el mensaje del usuario |
| 5 | **El código conserva el motivo de validación** | **✔** `invalid_output_ambiguous_parameter_claim…`, acotado a 135 caracteres |

Y un sexto que no estaba pedido y hace falta:

| 6 | **Dos terminales seguidos no se pisan** — cada uno con su `client_message_id`, y el denominador cuenta los dos | **✔** |

---

## 3. Lo que ya estaba, y no se ha rehecho

`[MEDIDO]` La ruta terminal **ya existía y funciona**:

```python
if selected is None:
    error_code = _terminal_error_code(candidates[-1].validation)
    await self._mark_turn_failed(..., error_code=error_code, ...)
    raise ChatRuntimeUnavailable(error_code)
```

Con dos códigos previos para el agotamiento de la escalera
—`generation_repair_failed` y `generation_contract_failed`— y el detallado de
`_terminal_error_code` para el fallo de contrato.

**Lo que faltaba no era el mecanismo: era la prueba de que hace las cinco cosas.**
Un mecanismo sin test es una intención.

`[MEDIDO]` **El valor del aserto 5, con número:** la campaña v3 pudo desglosar
**las 8 clases de rechazo** gracias a que el código terminal conserva el motivo.
Con un código único, los 96 fallos habrían sido un número sin causa, y ni G.1 ni
I.2 ni H tendrían frente asignado.

---

## 4. La regla pre-declarada, y su resultado

> GOAL: *«si al implementar la Fase 5 el total de turnos del denominador cambia,
> no has arreglado un error, has descubierto que antes se estaban perdiendo
> turnos. Eso se reporta como hallazgo.»*

`[MEDIDO]` **El denominador no cambia.** La campaña v3 lanzó **405** turnos y
registró **405**, con 49 terminales entre ellos. No había turnos perdiéndose, así
que no hay hallazgo que reportar por esta vía — y se dice explícitamente en vez de
dejar la regla sin resolver.

---

## 5. El quinto punto del GOAL que este informe **no** puede cerrar

> *«El front lo muestra como error, no como respuesta vacía. Un turno en blanco es
> peor que un error: parece una opinión clínica.»*

`[DERIVADO]` Eso es una aserción de **interfaz**, y estos tests son de backend. Lo
que sí queda comprobado aquí es la mitad que le corresponde al servidor: **se
lanza una excepción tipada**, así que el front no recibe un `200` con cuerpo
vacío. Que la pinte como error es responsabilidad del cliente y necesita su propia
prueba, que **no está hecha** y se declara así.

`[MEDIDO]` Y hay un dato de contexto: el `codigo_error` **público** se colapsa a
`invalid_model_output` en `router.py` **a propósito**, para que el proveedor no
pueda inferir qué comprobación lo rechazó. El código detallado viaja por el canal
interno. No es un fallo de tipado: es una decisión de seguridad, y conviene no
«arreglarla».
