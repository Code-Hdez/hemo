# Ventana 1 — registro, con el presupuesto escrito ANTES de encender

**Fecha:** 2026-08-15 · **Autorización:** explícita del usuario, con el protocolo de §4
**Rama medida:** `main` tras mezclar `puertas-v3` · **Estado al abrir:** las tres VMs `TERMINATED`

> §4.4 exige escribir el presupuesto antes de encender y parar si se desvía más
> del 30 %. Esta primera mitad se rellena en frío; la segunda, durante y después.

---

## 1. Presupuesto declarado (antes de encender)

| Trabajo | GPU estimada | Acumulado |
|---|--:|--:|
| Arranque en frío de la GPU | 6 min | 6 |
| Despliegue verificado + lectura del SHA en la VM | 10 min | 16 |
| **F.1** · gramática + el conteo de pasadas de §3.2 | 15 min | 31 |
| **F.2b** · caché multi-turno, tres brazos + búsqueda en el log | 15 min | 46 |
| **Campaña v3** · 9 corridas × 45 = 400 turnos | 110 min | **156** |
| Apagado y verificación | 5 min | **161** |

**Presupuesto total: ~2 h 41.** Umbral de parada del 130 %: **3 h 30**.
β local de la reparación (~35 min) queda **fuera** de esta ventana: es opcional y
el presupuesto ya está ajustado.

## 2. Reglas de parada, copiadas de §4.5 para tenerlas a mano

| Condición | Acción |
|---|---|
| La primera corrida supera un 25 % de no-respuesta | parar, capturar journal, apagar, analizar en frío |
| El SHA de la VM no es el que creo | parar antes del primer turno |
| El preflight de `campana_v3.sh` falla | parar; para eso existe |
| Una VM se apaga sola | registrar hora, leer el journal del arranque **anterior** (`-b -1`), no reintentar a ciegas |
| Se supera el 130 % (3 h 30) | terminar la corrida en curso, apagar, entregar lo medido con el hueco declarado |

## 3. Preflight en frío — hecho antes de tocar nada

```
sellos v3 / G / H / I .................. OK (4/4)
evaluar_puertas.py --autocomprobar ..... OK 42/42
git status --porcelain ................. vacío
pytest backend/tests ................... 1374 passed, 1 skipped
VMs .................................... las tres TERMINATED
```

`[MEDIDO]` Y se leyó `.github/workflows/deploy.yml` como manda §4.2: el job
`Publish deferred GPU release` deja la release en `pending_boot_validation`
reportando el estado de la VM, y `Deploy production through IAP` depende de él y
necesita la CPU encendida. **El orden del protocolo se confirma contra el
workflow, no se asume.**

## 4. Cambio en frío antes de la ventana

`[DERIVADO]` §3.2 del prompt maestro obliga a añadir a F.1 un experimento que no
existía: **contar si Ollama hace una o dos llamadas a `llama-server`** cuando se
envía `format` a un modelo con capacidad de *thinking*.

No se puede leer el log de `llama-server` desde el arnés, así que el
discriminante es **el residuo de reloj**:

```
residuo = segundos_de_reloj − total_duration que reporta Ollama
```

Ollama informa las duraciones **de la llamada que devuelve**. Si hubo una pasada
previa, su coste está en el reloj y **no** en esas cifras. Tres condiciones, para
que el contraste sea interpretable y no una cifra suelta:

| Condición | Qué prueba |
|---|---|
| `sin_format` | línea base del residuo: red y serialización |
| `format` + `think` **nulo** | el caso peligroso de `routes.go` |
| `format` + `think: false` | el caso que §3.2 dice que lo evita |

Y de paso comprueba si con `think:false` el `format` **se sigue respetando** — el
modo de fallo de `ollama#14645` / `#15260`, que se daba por cerrado antes de
0.32.6 y que §3.2 manda comprobar en vez de asumir.

---

## 5. Ejecución (se rellena durante la ventana)

| Hito | Hora UTC | Notas |
|---|---|---|
| push de `main` (merge `58cc7b20`) | 20:12 | Build ✓ · Publish GPU release ✓ · **Deploy IAP ✗ (CPU apagada, esperado)** |
| push de `main` (`99c12ff1`) | 20:26 | mismo patrón. Es el commit que arregla el runner |
| `start` GPU | **20:47:37** | solo la GPU |
| `hemovet_gpu_startup=ready` | **20:52:41** | `release=applied id=99c12ff1 state=validated` · `latency_ms=207502` · arranque **5 min 04 s** |
| `start` CPU | **20:55:17** | solo después de que la GPU validara |
| despliegue relanzado (`workflow_dispatch` DEPLOY) | 20:57 | run `31908017791` |
| SHA leído en la VM (lado GPU) | 20:52:41 | **`99c12ff1f310906d2e9b89f20ae08035ab66d528`** = HEAD |
| despliegue verificado job a job | **21:10:35** | Build ✓ · Publish GPU ✓ · **Deploy IAP ✓** · **Smoke ✓** — ninguno `skipped` |
| SHA leído en la VM (lado CPU) | **21:11** | `99c12ff1f310906d2e9b89f20ae08035ab66d528` · `CHAT_STRUCTURED_OUTPUT_ENABLED=0` · 1280/16384/12000 · `CHAT_HISTORY_LIMIT=12` · `OLLAMA_MAX_RETRIES=1` |
| **F.1** (1.ª, defectuosa) | 20:59-21:00 | veredicto FALSO por sonda sin `think:false`; ver §6 |
| **F.1** (2.ª, buena) | **21:02-21:03** | **PROPAGA** · 3/3 parejas · 30/30 en el enum · `pattern` casa · fuzz sin crash |
| **F.2b** | **21:04-21:07** | **APPEND reutiliza, VENTANA no** · la culpa es nuestra y es arreglable |
| campaña v3 · corrida 1 | 21:24:50 → 21:35:54 | 10 fallos · **11 min** |
| campaña v3 · corrida 2 | 21:35:54 → 21:46:19 | 23 acumulados · 10,5 min |
| campaña v3 · corridas 3-9 | 21:46 → 23:01:36 | **95 min en total**, ~10,6 min por corrida |
| `stop` de las tres | **23:02:00** | |
| **`TERMINATED` verificado** | **23:03:54** | las tres |

## 6. Incidencias

1. **F.1 dio un veredicto FALSO en su primera ejecución** y hubo que repetirlo.
   Coste: 2 min de GPU. Causa y lección en `DEFECTOS_DE_METODO_PROPIOS.md` §5.
2. **La espera por defecto del arnés eran 20 min por corrida** —tres horas en
   nueve—. Detectado con las máquinas encendidas y la primera corrida esperando.
   Coste: ~6 min entre detectarlo, parchear y relanzar. Ver §6 de ese informe.
3. **La campaña se lanzó primero en primer plano** y el límite de cinco minutos
   la mató. Sin pérdida de datos —no había escrito ninguno—, ~5 min perdidos.
4. **Un `pkill` por patrón mató mi propia orden.** ~2 min.
5. **Los dos primeros runs del workflow fallaron en `Deploy production through
   IAP`**, que es **lo esperado y está documentado**: la CPU estaba apagada. Los
   jobs que importaban —`Build` y `Publish deferred GPU release`— salieron en
   `success` los dos.

**Ninguna incidencia costó una corrida ni obligó a repetir la campaña.**

## 7. Minutos reales y desviación

| | previsto | real |
|---|--:|--:|
| arranque en frío de la GPU | 6 min | **5 min 04 s** |
| despliegue verificado + SHA en la VM | 10 min | ~23 min (dos runs en cola + `workflow_dispatch`) |
| F.1 (dos ejecuciones) | 15 min | **4 min** |
| F.2b | 15 min | **3 min** |
| campaña v3 | 110 min | **95 min** |
| apagado y verificación | 5 min | 2 min |
| **ventana total** | **2 h 41** | **2 h 16 min** (20:47:37 → 23:03:54) |

**Desviación: −16 % sobre el presupuesto.** El umbral de parada del 130 % (3 h 30)
no llegó a acercarse.

`[DERIVADO]` Lo que más se desvió al alza fue el despliegue —23 min frente a 10—
porque dos runs quedaron en cola por la concurrencia y hubo que lanzar un tercero
por `workflow_dispatch` con la CPU ya encendida. Es coste de CI, no de GPU: la
GPU estuvo esos minutos encendida sin medir, y es el hueco a optimizar en la
próxima ventana **empujando antes de encender nada**.
