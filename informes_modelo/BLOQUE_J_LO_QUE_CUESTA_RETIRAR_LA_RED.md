# Bloque J — qué cuesta exactamente retirar la red

**Fecha:** 2026-08-15 · **Árbol:** `4cca5683` · **GPU usada: cero**
**VMs:** las tres `TERMINATED`, verificado.

> **J no se ejecuta hasta que la Puerta C acepte.** Es la regla y lleva
> respetándose cuatro sesiones. Pero J.4 pide explícitamente *«si se retiran, se
> mide antes qué se pierde»*, y eso se puede medir hoy, con las máquinas
> apagadas. Este documento es esa medición.

Toda cifra va marcada `[MEDIDO]`, `[DERIVADO]` o `[INFERIDO]`.

---

## 1. De las cinco rutas de I-9, TRES ya están muertas

`[MEDIDO]` Rutas de generación realmente usadas en los 225 turnos de la campaña,
según `provider_call_routes`:

```
main          198
repair         21
last_resort     0      ← nunca
steer           0      ← nunca
tool            0      ← nunca
```

`[MEDIDO]` Y no es que no salieran en el sorteo: dos de las tres están **cerradas
por configuración**, no por suerte.

| Ruta | Guarda | Estado en producción |
|---|---|---|
| `_last_resort_candidate` | `if selected is None and self.structured_output_enabled:` | **inalcanzable** — `CHAT_STRUCTURED_OUTPUT_ENABLED=0` |
| `build_tool_selection` | `CHAT_TOOLS_ENABLED` | **inalcanzable** — `False` por defecto y en producción |
| `_steered_candidate` | `steer is not None`, y `_STEER_ACTIONS = {REFUSE_DIAGNOSIS}` | **alcanzable**, pero 0 de 225 |

> `[DERIVADO]` **Retirar `_last_resort_candidate` y el tool-call es eliminación de
> código muerto en esta configuración: cero cambio de comportamiento.** Lo que
> queda vivo de verdad es **una** ruta, la reparación, con 21 de 225.

---

## 2. Una corrección a I-9: nombra la ruta equivocada

El GOAL I-9 avisa:

> *«`provider_calls = 1` exige retirar `_last_resort_candidate` (ruta aparte:
> `CHAT_MAX_GENERATION_ATTEMPTS=1` NO la desactiva)»*

`[MEDIDO]` **El aviso es correcto en su forma y equivocado en su objeto.** Es
cierto que existe una ruta que `CHAT_MAX_GENERATION_ATTEMPTS=1` no desactiva —
pero **no es `_last_resort_candidate`**, que está cerrada por
`structured_output_enabled`. Es **`_steered_candidate`**:

```python
if selected is None:
    ...
    if (steer is not None
            and remaining_seconds >= ...repair_min_remaining_seconds):
        steered_candidate = await self._steered_candidate(...)
```

**Ese bloque no comprueba `max_generation_attempts` en ningún punto.** Con el
contrato mínimo activo y `CHAT_MAX_GENERATION_ATTEMPTS=1`, un turno cuya
`SafetyDecision` sea `REFUSE_DIAGNOSIS` seguiría gastando dos llamadas.

`[DERIVADO]` **Consecuencia para la Fase 4:** la aserción del invariante
`provider_calls == 1` como **excepción** —no como log— sigue siendo obligatoria,
exactamente como I-9 pide. Solo cambia cuál es el agujero que tapa.

`[MEDIDO]` El origen del error es rastreable: la Puerta 0 midió
`main 45 · repair 9 · last_resort 9 · steer 0` **con el sobre activo**, y de ahí
salió el aviso. Con el contrato mínimo el reparto es otro, y la ruta que
sobrevive a un cambio de configuración es la contraria.

---

## 3. Qué cobertura de test se pierde con cada retirada

`[MEDIDO]` Referencias directas en `backend/tests/`:

| Símbolo a retirar | Ficheros de test | Referencias |
|---|--:|--:|
| `_last_resort_candidate` | **0** | **0** |
| `_steered_candidate` | **0** | **0** |
| `build_tool_selection` | **0** | **0** |

> **Ninguno de los tres tiene un solo test que lo ejerza directamente.** Retirar
> los tres no elimina ninguna garantía escrita sobre ellos — lo que también dice
> algo incómodo sobre cuánta confianza merecían mientras estaban vivos.

`[MEDIDO]` El sobre estructurado es otra historia:

| Fichero | Tests |
|---|--:|
| `test_structured_send_chat_message.py` | **48** |
| `test_structured_response.py` | **29** |
| **total dedicado al sobre** | **77** |
| `structured_response.py` | **1 593 líneas** |

> **Corrección al prompt maestro §J.4**, que habla de «~32 tests del sobre
> estructurado». `[MEDIDO]` Son **77** en los dos ficheros dedicados, más
> referencias sueltas en otros ocho ficheros. Es **más del doble** de lo
> estimado, y cambia el coste de esa limpieza.

`[MEDIDO]` `test_turn_guard.py` tiene **16** tests, de los cuales **dos** nombran
el último recurso:

```
test_the_last_resort_does_not_rescue_what_it_has_no_rewrite_for
test_the_last_resort_is_generated_with_no_patient_data_in_scope
```

> **Corrección al prompt maestro §J.4**, que dice «los 3 tests de `turn_guard`
> (último recurso) cubrían 9/45 turnos». `[MEDIDO]` Son **dos**, y los 9/45 son
> de la Puerta 0 **con el sobre activo**: en el contrato mínimo esa ruta cubre
> **0 de 225**.

---

## 4. El orden de retirada, revisado con los datos

El GOAL propone cinco pasos. `[DERIVADO]` Con lo medido, el coste y el riesgo de
cada uno son muy distintos:

| # | Paso | Riesgo | Qué se pierde de verdad |
|---|---|---|---|
| 1 | `_last_resort_candidate` | **nulo** | nada: inalcanzable con `structured_output=0`, 0 tests directos |
| 2 | tool-call | **nulo** | nada: `CHAT_TOOLS_ENABLED=False`, 0 tests directos |
| 3 | `_steered_candidate` | **bajo** | 0 de 225 usos, 0 tests directos — **pero es la ruta que sobrevive a un cambio de configuración**, así que retirarla es lo que de verdad cierra el invariante |
| 4 | **la reparación** (`CHAT_MAX_GENERATION_ATTEMPTS → 1`) | **el único real** | 21 turnos de 225 que hoy se salvan; ver §5 |
| 5 | `httpx retries=0` | bajo | reintentos de transporte; hay que medir si alguno se está usando |

`[DERIVADO]` **El orden del GOAL pone `_steered_candidate` en el paso 2 y el
tool-call en el 3.** Los datos sugieren invertirlos: el tool-call es código muerto
por configuración y `_steered_candidate` es el que cierra el invariante. Retirar
primero lo inerte deja el árbol más pequeño antes de tocar lo que sí puede
cambiar comportamiento.

**No se aplica ese cambio de orden aquí.** Es una propuesta con su medición
delante, y el orden lo decide quien abra la Fase 4.

---

## 5. Lo que cuesta el paso 4, que es el único que cuesta algo

Medido en `APORTE_REAL_DE_LA_REPARACION.md` y resumido aquí:

| | con reparación | sin reparación |
|---|---|---|
| **Puerta C** validez 1.ª pasada | 78,67 % | **78,67 %** — sin cambio |
| **Puerta D** indisponibilidad | 0/225 | **0/225** — sin cambio |
| turnos **sin respuesta publicada** | 27/225 = 12,00 % | 48/225 = **21,33 %** |
| **Puerta S** afirmación | ≥ 98,4984 % | ≥ **98,3217 %** |
| latencia del turno reparado | 22,17 s (×2,20) | — |

`[MEDIDO]` Y lo irreemplazable: la reparación iguala a un reintento ciego en las
preguntas estocásticas (48,5 % vs 50,9 %) y es lo único que funciona en las
estructurales — donde son **cinco turnos, todos de `GEN-05`**.

`[DERIVADO]` **`GEN-05` es el objetivo del Bloque I.** Si I lo resuelve antes de
generar, el paso 4 deja de perder nada irreemplazable.

---

## 6. La pregunta que ninguna puerta responde, y hay que hacerla antes

`[DERIVADO]` Retirar la reparación lleva los turnos sin respuesta del **12,00 %**
al **21,33 %**. Ninguna de las cuatro puertas lo vigila: C ya los cuenta como
fallo y D no los ve porque no son indisponibilidad.

> **Uno de cada cinco turnos sin ninguna respuesta es una decisión de producto y
> de clínica, no de ingeniería.** Va a la revisión veterinaria del Bloque K, y
> conviene preguntarlo antes de llegar allí:
>
> *¿prefiere el veterinario una respuesta más lenta, o ninguna respuesta?*

---

## 7. El paso 5 (`httpx retries=0`) y la desalineación `num_ctx`, medidos

Dos hipótesis que llevaban abiertas desde la Puerta 3 y que los datos existentes
sí pueden acotar. Cero GPU.

### 7.1 La desalineación `num_ctx` NO se manifiesta en régimen — hipótesis cerrada

El diagnóstico del 14-ago señaló que el contenedor tiene
`OLLAMA_CONTEXT_LENGTH=65536` mientras el backend pide `num_ctx=16384` en cada
`generation_config`, y que con `OLLAMA_MAX_LOADED_MODELS=1` eso **obliga a
evictar y recargar** el runner aunque `OLLAMA_KEEP_ALIVE=-1`.

`[MEDIDO]` Sobre los 198 turnos de la campaña con métricas de carga:

```
load_duration_ms   p50 542,7   p95 557,5   máx 574,0
turnos por encima de 1 s    : 0
turnos por encima de 10 s   : 0
size_vram_bytes distintos   : {16 663 193 844}  ← uno solo, en los 198
```

> **En 225 turnos el runner no se recarga ni una vez.** La desalineación existe,
> pero **no se manifiesta en régimen de batería**: la recarga que se observó el
> 14-ago ocurrió con la VRAM a cero después de un arranque, que es otra
> situación. `[DERIVADO]` La hipótesis queda **acotada, no viva**: cuadrar
> `OLLAMA_CONTEXT_LENGTH` con el `num_ctx` de producción sigue siendo higiene
> razonable, pero **no compra latencia** en el caso que la campaña mide, y por
> tanto no entra en el camino crítico de la Puerta C.

### 7.2 El paso 5 no está refutado — está sin instrumentar, y hay que decirlo

`[MEDIDO]` La configuración desplegada permite **un** reintento de transporte:

```
backend/app/core/config.py:130   OLLAMA_MAX_RETRIES: int = Field(default=1, ge=0, le=1)
.env.production.example:159      OLLAMA_MAX_RETRIES=1
```

`[MEDIDO]` Y en los 177 turnos de una sola llamada, **ninguno** presenta una
latencia compatible con un timeout de conexión: p50 10,08 s, p95 15,95 s, máx
**18,87 s**, y cero por encima de 60 s.

`[DERIVADO]` **Eso descarta el caso lento, no el rápido.** Un fallo de conexión
que rebote de inmediato y se reintente con éxito añadiría milisegundos, no
segundos, y sería **invisible** tanto en la latencia del cliente como en el
ledger — que cuenta llamadas de **generación**, no de conexión.

> **Conclusión honesta:** no se puede afirmar que el reintento de transporte no
> se esté usando. Lo que sí se puede afirmar es que **si se usa, nunca ha costado
> más de 18,87 s a un turno**. Retirar `retries` a 0 significa que un fallo TCP
> transitorio mata el turno en vez de reintentar, y con la Puerta D en 0/225 no
> hay forma de saber si alguno de esos 225 se salvó así.
>
> `[DERIVADO]` **Antes del paso 5 hace falta contar los reintentos de conexión**,
> no deducirlos. Es una línea en el adaptador —el mismo patrón del ledger— y su
> coste es cero comparado con retirar a ciegas una red que quizá esté sosteniendo
> la única puerta que hoy pasa con holgura.

### 7.3 Y resulta que contarlos no hacía falta — medido el 15-ago

`[MEDIDO]` §7.2 pedía **contar** los reintentos antes del paso 5, siguiendo `I-7`.
Al ir a instrumentarlo salió que **no se pueden contar desde la aplicación**: el
bucle vive en `httpcore._async.connection.AsyncHTTPConnection._connect`
—`while True`, captura `ConnectError`/`ConnectTimeout`, retroceso exponencial— y
es **interno a httpcore**. `httpx` no expone gancho ninguno: ni `event_hook`, ni
método del transporte, ni contador.

Contarlos en producción exigiría parchear un interno de httpcore, o mover el
reintento a nuestro envoltorio con `retries=0` debajo —que **es** el cambio que
había que decidir, así que no puede ser su instrumento—, o contar SYN fuera de la
aplicación.

**Pero la pregunta de verdad tenía otra respuesta, y es medible en local.**
`validacion_llm/scripts/reintentos_de_conexion.py`, sin GPU ni Ollama:

| medida | resultado |
|---|---|
| servidor levantado: conexiones aceptadas | **1** |
| servidor levantado: bytes recibidos | **210** (la petición, enviada una vez) |
| puerto que rechaza: `retries=0` | mediana **0,49 ms** |
| puerto que rechaza: `retries=1` | mediana **0,66 ms** |
| coste del reintento | **+0,17 ms** por fallo de conexión |

`[MEDIDO]` **El reintento se dispara solo al establecer la conexión, antes de
enviar un byte.** Por tanto:

> - **no puede producir una segunda generación**;
> - **no puede inflar `provider_calls`**;
> - **no es una amenaza para `provider_calls == 1`**.

`[DERIVADO]` `retries=0` es una decisión de **robustez y latencia**, no de
corrección. El prerrequisito que `I-7` le pone —contar los reintentos— protegía
de un riesgo que **no existe**, y el paso 5 puede decidirse por su verdadero
criterio: si merece la pena que un fallo TCP transitorio mate el turno para
ahorrar 0,17 ms. `[DERIVADO]` Con la Puerta D pasando con holgura, la respuesta
por defecto es **no retirarlo**.

---

## Hipótesis vivas

1. ~~Si algún reintento de transporte de `httpx` se está usando.~~ **Acotada en
   §7.2**: si se usa, nunca costó más de 18,87 s. Para cerrarla hace falta
   contarlos, no deducirlos — y eso va **antes** del paso 5.
2. ~~La desalineación `num_ctx` app 16 384 / servidor 65 536.~~ **Cerrada en
   §7.1**: cero recargas en 225 turnos. No está en el camino crítico.
3. **Si `_steered_candidate` está muerta o solo dormida.** 0 de 225, pero su
   guarda es una `SafetyDecision` (`REFUSE_DIAGNOSIS`) que este corpus no
   produce. Otro corpus podría. **Y es la ruta que sobrevive a un cambio de
   configuración**, así que la aserción del invariante sigue siendo obligatoria.
4. **Qué se pierde al retirar las 77 pruebas del sobre.** Cubren un contrato que
   ya no se usa, pero algunas podrían estar fijando conductas del validador que
   sí siguen vivas. Hay que leerlas una a una antes de borrarlas.
