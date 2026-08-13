# HemoVet — estado a `2cf21876`

**9 de agosto de 2026** · sustituye a `hemovet/estado-fase-22.md` · documento completo: `INFORME_ESTADO_HEMOVET.md`

> ## Se pasó de «no se puede medir» a «se puede medir mañana». Pero no se ha medido.

Lo único que separa del veredicto es **tiempo de reloj**: no falta conocimiento ni infraestructura.

---

## El mapa

```
VÍA A — INFRAESTRUCTURA
diagnosticar ─► arreglar ─► probar ─► desplegar ─► verificar     COMPLETA ✔

VÍA B — MITIGACIONES CLÍNICAS
diagnosticar ─► escribir ─► validar ─► desplegar ─► medir
  100 %          5 de 7      0 %        0 %          0 %
                          ▲ la línea de frente, nunca superada
```

**Bloque 0 CERRADO** (M-15 apagado, causa NO_DETERMINADA) · Bloques 1–4 **no empezados**.

## Cadena de despliegue

`21f18fd8` (rojo, dos causas independientes) → `59e51657` (verde, desplegado) → `157a389a` (falló CI, pytest-asyncio) → `55d5e599` (verde) → `8c9a2c6a` (observabilidad) → **`2cf21876`** (poller apagado, observabilidad conservada). **`main` verde y desplegando solo por primera vez en el proyecto.**

## Lo medido — la línea base del 7 de agosto, única medición de comportamiento que existe

```
63 en alcance:  25 útiles (39,7 %) · 23 callan (36,5 %) · 15 mueren (23,8 %)
70 turnos · 133 llamadas · reparto 36/8/23/3 · 17/70 fallos terminales, cero timeouts

                       p50       p90       máx
sin reparar (n=36)   34,8 s    59,1 s    89,0 s
reparando   (n=34)   98,1 s   151,9 s   212,3 s
LOS 70               59,1 s   129,4 s   212,3 s
```

**Las tres causas:** (1) `_last_resort_candidate` quita las reglas y luego pide un claim que las exige — 13 de 17 fallos, `policy_rule_id_missing` 3,0 % completo vs **43,3 % truncado** (OR 24,9 · p<0,001). (2) Contrato asimétrico: **6 puertas al afirmar : 1 al declinar**, **6,50×** más rechazos (50/107 vs 21/292), prompt 3,5:1 prohibitivo. (3) Decode 13,05 tok/s = 73,7 % del techo, y **suelo de sobre de 204 tok = 15,6 s**.

**El modelo está exculpado:** 60 % de utilidad sin contrato, 39,7 % con él, «París.» al instante sin contrato. No hay problema de modelo, hay problema de contrato.

## Correcciones de esta jornada

| circulaba | es |
|---|---|
| p50 32,8 s · máx 126 s | **59,1 s · 212,3 s** (32,8 era la mediana de los que no repararon) |
| 73 turnos, 138 llamadas, 38/8/24/3 | **70, 133, 36/8/23/3** — tres grupos eran humo manual previo |
| 12 divergencias arnés/producción | **17** — el 12 coincidía con los campos vigilados y esa coincidencia lo escondía |
| «la combinada» = las cuatro | **sólo M-1+M-2.** Hay que crear la de cuatro |
| «siete mitigaciones escritas» | **siete commits, seis ramas, cinco mitigaciones en código** |

## Logros de infraestructura

Máquina rescatada sin contaminar la evidencia (driver 580.159.03, kernel 1021, 19 `apt-mark hold`, snapshot) · arnés resucitado (ocho kwargs enrutados, no filtrados; verificado en el cable) · tokenizador real de Qwen3.6 (**vocab 248 070**, la ficha dice 248 320 *padded*) · H-02 cerrado por `git bisect` sobre 15 commits, regla intacta en `:4848`, cuatro sondas, test estrictamente más fuerte · **preflight con 33 tests**, 24 campos falsificados uno a uno, bloque ENTRADAS (corpus + hash del CSV).

**Hallazgo colateral grave:** `validate_ollama_runtime_identity` empieza con `if not expected_digest and not expected_quantization: return None`. En local no comprobaba **ni dígito, ni cuantización, ni nombre del modelo** — y el 4B está instalado en el Ollama de producción. No quedaba ninguna guarda capaz de cazarlo.

## El patrón — doce instancias, dos resueltas

> **Se comprueba una condición necesaria y se trata como suficiente.**

Resueltas: el **sello `sha256 797b4865e85a8332`** del criterio, y la **observabilidad del poller**. Las dos con la misma forma: convertir algo que dependía de que alguien se acordara en algo que habla solo. **Cuatro de las doce se cometieron dentro del instrumento escrito para atajarlas** — el patrón no es descuido de un autor, es lo que produce trabajar deprisa sobre un sistema de muchas capas.

Y la mejor frase técnica del proyecto, del test de cobertura del preflight: **«un recuento se cumple solo; una igualdad no».**

## Lo que falta

**Bloque 1** rama combinada de cuatro (1 h) · **Bloque 2** brazo contra producción (**84 min medidos**) · **Bloque 3** veredicto, recalculando el sello antes de escribir (0,5 h) → **≈ 3 h al veredicto**. Después: 4.1.d (3 h), M-10 (6 h), las once instancias vivas (6 h), streaming (10 h) → **≈ 28 h** en total, **≈ 41 h** si sale no concluyente.

**Predicción pre-registrada:** 17/70 → ~4/70 (Fisher 1 cola **p = 0,0018**), utilidad 39,7 % → ~63 %, p50 −41 %. **La batería distingue un efecto grande de ninguno; no distingue uno mediano** — 11/70 es «no concluyente», no «no funciona». Y **comparar los ids, no sólo el recuento**: si baja el número pero cambian los ids, no se arregló nada.

## Los 10 segundos

A 13,05 tok/s, diez segundos compran **130 tokens** — y el suelo obligatorio del sobre **después de M-4** son exactamente 130 tokens. Cero para la respuesta clínica. **Con este modelo, en esta GPU, con este contrato, es imposible.** Salidas: streaming (~1 s percibido), modelo MoE (~4,4 s reales, destruye la línea base), o adelgazar el contrato. La barata y sin riesgo clínico es el **4.1.d**, sin asignar desde hace cinco sesiones.