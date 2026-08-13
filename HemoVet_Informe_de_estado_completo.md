# HemoVet — Informe de estado completo

**9 de agosto de 2026** · `main` = **`2cf21876`**, desplegado · 23 sesiones de trabajo

---

# 0 · Dónde está el proyecto, en una frase

> ## Se pasó de «no se puede medir» a «se puede medir mañana». Pero no se ha medido.

El diagnóstico está cerrado, la infraestructura está reparada de punta a punta, y hay cinco mitigaciones escritas y probadas en local — **pero ninguna se ha medido nunca contra la realidad**. El proyecto está a un experimento de 84 minutos de saber si veintitrés sesiones de trabajo sirvieron para algo.

**Y lo único que separa de ese veredicto es tiempo de reloj: no falta conocimiento ni falta infraestructura.** Eso es distinto de dónde se estaba hace dos sesiones, y es el cambio real de estas jornadas.

---

# 1 · El mapa de progreso

El trabajo tiene dos vías, y están en puntos muy distintos.

```
VÍA A — INFRAESTRUCTURA
diagnosticar ──► arreglar ──► probar ──► desplegar ──► verificar en producción
  ██████████     ██████████   ████████   ██████████     ██████████     COMPLETA ✔

VÍA B — MITIGACIONES CLÍNICAS
diagnosticar ──► escribir ──► validar ──► desplegar ──► medir en producción
  ██████████     ████████░░   ░░░░░░░░    ░░░░░░░░       ░░░░░░░░
     100 %        5 de 7        0 %          0 %            0 %
                              ▲
                     ═════════╪═════════  LA LÍNEA DE FRENTE
                     nunca ha pasado de aquí
```

**La vía A está terminada.** La máquina arranca, el driver está clavado, la CI está verde, el despliegue es automático y tarda cuatro minutos, y el último cambio llegó a producción hoy. Eso no existía hace tres días.

**La vía B está atascada en el mismo sitio desde el principio.** No por falta de código: el código está escrito y pasa 1 304 tests. Está atascada porque **validar cuesta 76 minutos de GPU y escribir cuesta una tarde**, y el proyecto ha ido eligiendo, sesión tras sesión, lo que era más fácil de producir.

---

# 2 · Lo que está HECHO — los logros, uno por uno

## 2.1 · La máquina, rescatada sin perder la evidencia

El 7 de agosto `unattended-upgrades` cambió el driver de NVIDIA en una VM cuyo contrato de arranque (`validate-host.sh:5`) lo fija en `580.159.03` **sin ningún `apt-mark hold`**. La VM dejó de pasar su propia validación.

Lo que se hizo, y por qué cada paso importa:

1. Se creó `hemovet-rescate` — una **e2-medium sin GPU**, deliberadamente, para no arriesgar un STOCKOUT de L4 al reiniciar. Las L4 escasean en `us-central1-a`.
2. Se desacopló el disco de arranque de la VM de GPU y se montó en la de rescate.
3. Por `chroot`: driver a **580.159.03**, purga del **kernel 1022**, conservación del **1021**.
4. **19 `apt-mark hold`** + lista negra del módulo, para que no se repita.
5. Un solo arranque, verificado.

**Resultado:** `host_runtime=valid`, driver 580.159.03, kernel 1021 — **la configuración exacta del 7 de agosto**. Eso último es lo importante: significa que **la línea base medida ese día sigue siendo comparable**. Un rescate que hubiera dejado la máquina «igual de buena pero distinta» habría destruido el único activo del proyecto.

Snapshot `hemovet-llm-gpu-k1021-driver580159-20260808` tomado. `hemovet-rescate` **parada, no borrada**.

## 2.2 · El arnés de aceptación, resucitado

Estaba roto **desde antes de que existiera ninguna mitigación**, en `21f18fd8`:

```
TypeError: OllamaNativeLLMClient.__init__() got an unexpected keyword argument 'temperature'
```

Ocho kwargs habían migrado del cliente al perfil en un refactor. **Nadie lo vio en meses porque el test vive tras `RUN_OLLAMA_ACCEPTANCE=1` y la CI nunca pasa esa variable.** Un test que no se ejecuta no es un test: es un comentario.

Se reparó **enrutando los ocho a `generation_settings`, no filtrándolos** — filtrarlos habría descartado en silencio temperatura, presupuesto y contexto, produciendo una tabla creíble y falsa. Se alineó además `max_input_tokens` de 3 200 a 12 000.

**Y se verificó en el cable:** el cuerpo JSON real hacia Ollama lleva `num_ctx: 16384`, `keep_alive: -1`, `thinking: false` y los cuatro parámetros de muestreo. No se confió en la configuración; se leyó el tráfico.

## 2.3 · `main` verde y desplegando — por primera vez

Este hito no aparece en ninguna tabla de métricas y es probablemente el segundo más importante del proyecto. **`main` llevaba rojo desde antes de `21f18fd8`, por dos causas independientes que nadie había separado** (un `F401` y el test clínico del dígito).

| commit | qué llevó | pipeline |
|---|---|---|
| `21f18fd8` | base de todas las ramas | **rojo** (F401 + test clínico) |
| `59e51657` | oleada 1 — quitar el F401 + el test del dígito corregido | **8/8 verde, desplegado** |
| `157a389a` | oleada 2 — el poller de M-15 | falló CI (`pytest-asyncio`) |
| `55d5e599` | tests del poller al estilo de la casa + variable documentada | **8/8 verde, desplegado** |
| `8c9a2c6a` | observabilidad del poller | **8/8 verde, desplegado** |
| **`2cf21876`** | **poller apagado, observabilidad conservada** | **desplegado — es lo que corre ahora** |

Los 8 jobs incluyen *Deploy production through IAP* y *Production smoke tests*.

Antes de esto, la única forma de probar cualquier cosa era montar un aparato local de tres horas con diecisiete divergencias que vigilar. **Ahora se despliega en cuatro minutos y se revierte en cuatro.** Eso es lo que convirtió el plan de 13 horas en un plan de 4.

En el camino se corrigió un fallo de higiene: se usó `@pytest.mark.asyncio` cuando `pytest-asyncio` no está en `requirements-dev` y 0 de 22 ficheros lo usan. Dejó `main` rojo. Se arregló convirtiendo a `asyncio.run` y verificando con **`-p no:asyncio`**, que es ahora la forma obligatoria de correr las suites.

## 2.4 · El tokenizador correcto, y la trampa que evitó

Se descargó el de `Qwen/Qwen3.6-27B` (12,8 MB, Apache-2.0, `sha256 5f9e4d49…`). El repositorio tenía el de **Qwen3** (151 669 tokens), **que es otro modelo**.

**Vocabulario real medido: 248 070.** La ficha del modelo declara 248 320, pero está marcado *(padded)*: es la dimensión de la matriz de embeddings, no el recuento de tokens. Una instrucción anterior fijaba 248 320 como valor esperado — se habría auto-invalidado.

Y quedó un aviso vigente que evita un desastre futuro: **la distribución del factor de estimación es trimodal** (cúmulos en 1,4-1,5 con n=49, en 1,7 con n=37, en 2,5-2,6 con n=39). Ajustar `max_input_tokens` a la mediana metería un 26 % por encima del límite en el modo bajo. **La corrección correcta es el tokenizador real, no un factor de escala.**

## 2.5 · H-02 resuelto — la regla del dígito está intacta

`test_transition_claim_cannot_carry_a_number` llevaba en rojo desde `bd70e0d8`, localizado con **`git bisect` sobre 15 commits**. La pregunta era si la regla clínica estaba rota o si el test miraba mal.

**Veredicto: el test vigilaba el mecanismo de entrega, no la regla.** La regla sigue intacta en `send_chat_message.py:4848`. Lo que cambió fue **la consecuencia**: `671483f9` y `bd70e0d8` sustituyeron «claim rechazado → muere el turno» por «se descarta y se entrega el resto».

| sonda · claim `TRANSITION` | ¿sobrevive? | ¿fuga la cifra? |
|---|---|---|
| cifra real (40,2) | no | — |
| cifra inventada (99,9) | no | **no** |
| inventada de otro analito (45,7) | no | **no** |
| sin cifra | sí, encabeza | — |

El test nuevo es **estrictamente más fuerte** — los dos casos inventados no estaban cubiertos — y está falsificado en los dos sentidos: con `if False and …` fallan los tres; restaurada la guarda, pasan.

## 2.6 · M-15, cerrado hoy — apagado, no revertido

Ésta es la historia más instructiva del proyecto, porque es la que enseña a parar.

**El problema real:** `validate-runtime.sh` carga el modelo al arrancar la VM con `OLLAMA_CONTEXT_LENGTH=65536`, mientras el backend pide 16 384. Con `keep_alive: -1` el runner se queda a 65536 hasta que un turno real lo expulsa. **Coste medido: 101,0 s de mediana (n=5). Una llamada concordante cuesta 0,55 s — 184× más barato.** Y hoy ese primer turno **falla**, no tarda: con `CHAT_MAX_CONCURRENT_GENERATIONS=1` la petición se bloquea y expira. **M-15 es fiabilidad, no latencia.**

El discriminador tuvo que medirse porque `/api/ps` **no expone `num_ctx`** — expone `size_vram`:

```
16384  →  16 926 501 764  (15,76 GiB)
65536  →  18 889 436 036  (17,59 GiB)     separación 11,6 %, umbral al 5 %
```

**Lo que pasó después:** el poller se desplegó y **no funcionó**.

| | |
|---|---|
| recarga forzada a 65536 | **101 s** — reproduce la mediana de n=5 |
| deriva verificada | 16 926 501 764 → 18 889 436 036 = **11,6 %** |
| observación | **170 s · 34 muestras · 0 rearmados · 0 eventos** |

Se desplegó observabilidad, y **convirtió dos sesiones de silencio en un error con nombre, hora y periodicidad en diez minutos**: `runner_realign_failed error_type=TypeError` cada 60 s desde la vuelta 2.

Y entonces **cayeron cinco hipótesis, dos mías y tres del agente**, todas por medición: el recolector de basura, la línea nueva de log, el `capture_runner_baseline` devolviendo `None`, el reproductor de tres llamadas, y **mi eliminación estricta que apuntaba a `warmup()`** — el agente llamó a `warmup()` directamente con el perfil real y funcionó.

**Decisión ejecutada, en `2cf21876`:** apagar, no revertir.

| se apaga | se queda |
|---|---|
| el poll, con `OLLAMA_RUNNER_REALIGN_SECONDS=0` (`ge=0`) y un `runner_realign_disabled` que lo declara | **`exc_info=True`** en el `except` — registrar sólo `type(exc).__name__` es lo que obligó a adivinar tres veces |
| | **la rama `vram is None`**, que recargaba el modelo y se iba sin registrar nada. Ahora emite `runner_realigned` con `motivo=sin_runner_residente` |

**Por qué apagar y no revertir:** un `revert` habría borrado también los tres eventos de observabilidad que costaron dos sesiones conseguir. Reencender es cambiar un número. El `TypeError` queda **NO_DETERMINADO** con su reproductor escrito en `02_m15.json` para quien vuelva.

> **Y la rama silenciosa es un hallazgo por sí sola.** Si estaba realineando el runner sin decirlo, explica el `NO_DETERMINADO` de ayer: el runner volvió a 16 384 sin evento. Es la duodécima instancia del patrón (§7) y se resolvió hoy.

## 2.7 · El preflight de paridad — construido, falsificado y enganchado

El riesgo que elimina: **el arnés podía correr seis horas contra un backend que no envía lo que envía producción y devolver una tabla completa, creíble y falsa.**

`validacion_llm/scripts/preflight_paridad.py` compara el arnés contra producción **leyendo el cable y el `printenv` del contenedor desplegado, no ningún `.env` del repositorio**, que es donde vivían las mentiras. Aborta, no avisa.

- **Divergencias reales: 17, no 12.** El recuento inicial coincidía numéricamente con los campos vigilados y **eso mismo lo escondía**: eran dos conjuntos de doce **distintos**, con solape de diez.
- **24 campos falsificados uno a uno → 24 abortos.** Y uno con los 24 mal a la vez: los reporta todos.
- **Bloque ENTRADAS:** corpus (`chunk_count`, `index_fingerprint`, `embedding_model`), hash del CSV y revisión. Sin él, dos aparatos con los 17 parámetros idénticos **y otro corpus** pasaban como equivalentes.
- **33 tests**, `main` verde con ellos.

Y la lección de diseño, que es la mejor frase técnica que ha producido el proyecto:

> **El test que protege no es el recuento, sino la cobertura.** Enumera las divergencias por reflexión sobre `Settings` y exige que el preflight mire **cada una**. *Un recuento se cumple solo; una igualdad no.*

**Hallazgo colateral grave, encontrado en el camino:**

```python
def validate_ollama_runtime_identity(...):
    if not expected_digest and not expected_quantization:
        return None          # ← en local los pines no están puestos
```

**No comprobaba ni el dígito, ni la cuantización, ni el nombre del modelo.** Sumado a que el `qwen3:4b-instruct-2507-q4_K_M` **está instalado en el Ollama de producción**, no quedaba **ninguna** guarda capaz de cazar una corrida que usara el modelo equivocado — y esa corrida habría sido más rápida, así que se habría leído como mejora.

---

# 3 · Lo que está MEDIDO — la línea base

**Éste es el activo más valioso del proyecto.** Sin él, ninguna mitigación puede aceptarse ni rechazarse; con él, cualquiera se decide en 84 minutos.

## 3.1 · El censo de utilidad — de 63 preguntas en alcance

```
25  (39,7 %)   respondió algo útil
23  (36,5 %)   funcionó bien y decidió callarse     IC95 [25,7 – 48,9]
15  (23,8 %)   el turno murió: la respuesta nunca llegó
```

Hecho **a mano, caso por caso**, porque el detector automático tenía sensibilidad 1,000 pero **especificidad 0,480**: veía 36 negativas donde hay 23.

## 3.2 · Los fallos y la latencia — 70 turnos, 133 llamadas

```
fallos terminales     17/70        los 17 de contrato · CERO timeouts, verificado por tres vías
reparto de llamadas   36/8/23/3    (1, 2, 3 y 4 llamadas por turno)

                        p50        p90        máx
sin reparar (n=36)    34,8 s     59,1 s     89,0 s
reparando   (n=34)    98,1 s    151,9 s    212,3 s
LOS 70                59,1 s    129,4 s    212,3 s
```

**Validación cruzada del instrumento:** el servidor cuenta lo mismo — 39 completed + 14 refused + 17 failed = 70.

## 3.3 · Las tres causas, cada una con su número

**1 · Que se cae (23,8 %).** `send_chat_message.py:4283` construye la política de último recurso con `use_clinical_context=False` y `facts=[]` —quitando las reglas— y acto seguido pide un claim `SAFETY_GUIDANCE`, que `structured_response.py:137-141` **exige** que lleve `policy_rule_ids`. Contradicción directa en el mismo fichero. `policy_rule_id_missing` al 3,0 % en prompt completo y **43,3 % en truncado** (OR 24,9 · χ² 25,8 · p<0,001). **13 de 17 fallos terminales.**

**2 · Que calla (36,5 %).** El contrato es asimétrico: **afirmar atraviesa 6 puertas de validación, declinar atraviesa 1.** Medido sobre oportunidades reales: **6,50× más rechazos al afirmar** (50/107 = 0,467 frente a 21/292 = 0,072). El sistema toma el camino barato. Lo refuerza un prompt de sistema con proporción **3,5:1** de lenguaje prohibitivo frente a habilitante.

**3 · Que tarda.** El 87 % del turno es decode a **13,05 tok/s**, el **73,7 %** del techo físico de la L4 (300 GB/s ÷ 16,93 GB = 17,7 tok/s). Y el sobre impone un **suelo de 204 tokens = 15,6 s** antes de una sola palabra clínica. Ninguna de las 133 llamadas bajó de ahí.

## 3.4 · El modelo está exculpado

Tres mediciones, mismo modelo, mismo hardware, misma pregunta. Lo único que cambia es cuánto contrato hay en medio:

```
en arnés aislado, sin contrato ....  60 %  de utilidad
en producción, con el contrato ....  39,7 %
sin contrato, pregunta directa ....  responde "París." al instante
```

> **No hay un problema de modelo. Hay un problema de contrato.** Ésa es la conclusión que cambió la dirección del proyecto entero.

## 3.5 · Las demás cifras firmes

| | valor | cómo se sabe |
|---|---|---|
| reutilización de caché | **91,8 %** (5,58 s → 0,47 s) | medida · mató M-16 |
| suelo del sobre | **204 tok = 15,6 s** | ninguna de 133 baja |
| lo que quita M-4 | **74 tok = 5,7 s** = 36 % del suelo | medida |
| recarga por deriva del runner | **101,0 s** (n=5) vs 0,55 s | **184×** |
| saturación del techo de salida | **1,4 %** (2 de 133) | `finish_reason=length` |
| `num_predict` real | **1 280**, no 384 | 384 era el default de `config.py` |
| margen de timeout por llamada | 120 s vs máx 107,5 s → **12,5 s** | |
| margen de timeout por turno | 240 s vs máx 212,3 s → **27,7 s** | |
| divergencias arnés/producción | **17**, de las cuales **4 deciden qué texto sale** | reflexión sobre el objeto real |

---

# 4 · Lo que está ESCRITO y sin validar

**Corrección de inventario.** He venido diciendo «siete mitigaciones escritas». Es inexacto y lo arrastré yo: **son siete *commits*, sobre seis ramas, que contienen cinco mitigaciones en código.** M-9 tiene la premisa confirmada pero no implementación, y M-10 no está escrita.

| rama | commit | qué es | tamaño |
|---|---|---|---|
| `fix/last-resort-policy-rule-id` | `c187ed4a` | **M-1** · `materialize_sole_policy_rule` | 3 fich · +237 −4 |
| `fix/unambiguous-fact-id` | `f72272dc` | **M-2** · `materialize_unambiguous_fact_id` | 2 fich · +160 |
| `perf/envelope-field-aliases` | `019e2149` | **M-4** · alias cortos en `GeneratedSafety` | 2 fich · +174 −8 |
| `fix/repair-budget-after-truncation` | `048b3971` | **M-5** · invariante de presupuesto de reparación | 4 fich · +233 −4 |
| `fix/deterministic-support-fill` | `5517c431` | **M-1 + M-2 fundidas** | 4 fich · +548 −13 |
| `tooling/preflight-paridad` | `d9dfb46c` | el preflight + arnés + JSON | 158 líneas |

Base de todas: **`21f18fd8`**.

**Lo que hacen, y lo que expresamente NO hacen:**

- **M-1 y M-2** rellenan un dato que el backend **ya conoce con certeza** cuando es inequívoco. **No relajan ninguna validación** — el validador sigue exigiendo exactamente lo mismo; se le da por la vía correcta lo que antes se le quitaba por error.
- **M-4** son alias cortos (`dx`, `med`, `dose`, `freq`, `dur`, `pers`, `urgent`) con `populate_by_name=True`. Puro ahorro de tokens: **5,7 s por llamada**.
- **M-5** garantiza que el perfil de reparación reciba `truncated=True` cuando corresponde. Es el mecanismo mismo que está bajo prueba.
- **M-15** está desplegada y apagada (§2.6).

**Estado de validación de las cinco: cero.** Ninguna ha visto un caso real.

---

# 5 · Lo que está DIAGNOSTICADO y sin escribir

| # | qué | efecto | por qué no está hecho |
|---|---|---|---|
| **M-10** | reequilibrar el contrato y el prompt de sistema para los 23 turnos que callan | utilidad **63 % → ~81 %** | **es el mayor problema que queda.** Requiere revisión veterinaria, no sólo código |
| **Streaming** | el backend nunca emite texto incremental | espera percibida **34,8 s → ~1 s** | choca con el contrato: validar exige el sobre completo |
| **4.1.d** | pintar las etapas que el backend **ya emite** | barra muda → progreso visible | **frontend, sin asignar desde hace cinco sesiones** |

Sobre el streaming, el veredicto técnico está cerrado y es limpio: **el proxy es inocente.** Caddy 2.11.4 tiene `flush_interval -1` y excluye el endpoint de la compresión — alguien lo configuró a propósito y lo hizo bien. En 70 turnos: 279 heartbeat, 112 status, 70 start, 70 final, **0 eventos delta**. El TTFB de 0,134 s es el evento `start`, no texto.

---

# 6 · Lo que se ha FALSIFICADO — y por qué cuenta como logro

En este proyecto se han desmentido **más de veinte cifras y afirmaciones**, la mayoría propias. Eso no es ruido: es el motivo por el que las cifras del §3 se pueden creer.

## 6.1 · Instrumentos que fallaron — y su dirección

Siete instrumentos rotos. **Seis de los siete inflaban**, es decir, habrían hecho parecer que el sistema estaba mejor de lo que está:

| instrumento | fallo | dirección |
|---|---|---|
| contador de fallo terminal por longitud cero | 0 de 70 donde había 17 | ocultaba |
| detector `adecuad` en la coda de derivación | 0 de 0 presentado como 0 de 7 | **inflaba** |
| detector declinó/respondió (`q0 = 0,48`) | 36 negativas donde hay 23 | **inflaba** |
| `inspect.signature` contando opcionales | «20 parámetros de deriva» donde eran 2 | **inflaba** |
| arnés con `max_input_tokens = 3 200` | presupuesto ficticio | habría inflado |
| `llm.health()` con el 4B instalado | no protege | **habría inflado** |
| el preflight, firmando con 10 de 12 campos | sin comprobar ≠ igual | habría inflado |

> **De ahí sale la regla que no se negocia: antes de reportar cualquier cifra, di qué instrumento la produjo y cómo sabes que funciona.** Los siete habrían producido una tabla perfectamente creíble.

## 6.2 · Cifras del registro que resultaron falsas

| | era | es |
|---|---|---|
| latencia p50 | 32,8 s | **59,1 s** sobre los 70 — 34,8 s es la mediana de los que **no** repararon |
| latencia máxima | 126 s | **212,3 s** |
| turnos y llamadas | 73 · 138 | **70 · 133** · reparto 36/8/23/3 — tres grupos eran humo manual **anterior a la batería** |
| `num_predict` | 384 | **1 280** |
| saturación del techo | 99,5 % | **1,4 %** |
| divergencias arnés/producción | 6 → 12 | **17** — el 12 coincidía con los campos vigilados, y esa coincidencia lo escondía |
| «la combinada» | M-1+M-2+M-4+M-5 | **sólo M-1+M-2.** Faltan M-4 y M-5: hay que crearla |
| `vocab_size` de Qwen3.6 | 248 320 | **248 070** (la ficha está *padded*) |
| «la cartera no mueve el p50» | — | **lo mueve un 41 %** |
| rechazos por metadato «dominantes» | — | **41 %**, no mayoría |

Y una que **subió** de categoría en vez de bajar: que los cinco brazos corrieron con el 27B pasó de NO_DETERMINADA a **MEDIDA**, por el reloj — 135 s por corrida frente a los 20-39 s que habría costado el 4B.

## 6.3 · Confusiones conceptuales corregidas

- **`policy_rule_id_missing` es el 76 % de los FALLOS TERMINALES y el 18 % de los RECHAZOS.** No son la misma población: un rechazo dispara una regeneración; un fallo terminal mata el turno.
- **Hay dos relojes de timeout y no se mezclan.** 120 s **por llamada**, 240 s **por turno**.
- **La corrección de Rogan–Gladen no aplica a un censo.**
- **La puerta de calibración de ±3 estaba mal calculada:** σ = 3,59, así que ±3 es 0,84 σ — falsa alarma un tercio de las veces. Sustituida por **kappa ≥ 0,75 y ≥14 ids coincidentes**, con el recuento como criterio secundario.
- **El *Constraint Tax* no aplica limpiamente:** mide respuestas **incorrectas**; HemoVet produce respuestas **ausentes**. Modos de fallo opuestos.
- **Tres fuentes web se estiraron** más de lo que sostenían, y las tres se detectaron tarde. De ahí: *ninguna fuente entra en un informe con el verbo «es»*.

---

# 7 · El hallazgo que probablemente vale más que todo lo demás

Doce instancias del mismo hábito de diseño, en doce subsistemas que no se conocen entre sí:

> ## Se comprueba una condición necesaria y se trata como suficiente.

| se comprueba | no impide que… | |
|---|---|---|
| el driver *es* 580.159.03 | `apt` lo cambie | |
| el test codifica los criterios | la CI no lo ejecute | |
| existe `CHAT_TOKENIZER_REQUIRED` | esté a `False` | |
| el validador exige la regla | el llamante la quite | |
| el modelo está instalado | se use el otro | |
| los campos presentes coinciden | falten campos por comprobar | |
| el test del dígito pasa | vigile el mecanismo y no la regla | |
| el verde local pasa | el instrumento no sea el de CI | |
| siete tests del poller pasan | el poll de fondo no arranque | |
| el warmup registra que ocurrió | una rama silenciosa realinee sin decirlo | **resuelta hoy** |
| el código llegó al repositorio | el despliegue terminara en verde | |
| «no muevas el criterio» | alguien lo mueva | **resuelta con el sello `sha256`** |

**No es una lista de descuidos: es un hábito de diseño.** Y las dos filas resueltas enseñan el patrón de arreglo — las dos con la misma forma: **convertir algo que dependía de que alguien se acordara en algo que habla solo.**

- El **sello `sha256 797b4865e85a8332`** del criterio de aceptación: una frase que decía «no lo muevas» convertida en un hash que lo detecta si se mueve.
- La **observabilidad del poller**: un `except` que sólo registraba `type(exc).__name__` convertido en uno que registra el traceback, más la rama silenciosa que ahora dice lo que hace.

Y el dato que más peso le da al hallazgo, dicho por el propio agente:

> **Cuatro de las doce las cometí yo, dentro del instrumento escrito para atajarlas.**

Es decir: el patrón no lo produce el descuido de un autor concreto. Lo reproduce **cualquiera que esté trabajando deprisa sobre un sistema con muchas capas** — incluido quien acaba de nombrarlo. Por eso el arreglo tiene que ser mecánico y no cultural.

Este hallazgo es transferible fuera de HemoVet y probablemente vale más, a largo plazo, que cualquiera de las cinco mitigaciones.

---

# 8 · Hasta qué punto se ha llegado, tramo por tramo

La escalera a producción tenía cinco tramos. Éste es el corte exacto:

| tramo | qué es | estado |
|---|---|---|
| **0 — Local** | iterar código, suite verde, verificar que `format` compila a GBNF | ✅ **completo** · GBNF verificado (`SIN format → 'París.'` · `CON format → '{"zzz":"QQQ"}'`) |
| **1 — Batería completa** | 70 casos por brazo contra la GPU | ⬜ **el brazo base está medido; ningún brazo de mitigación se ha corrido** |
| **2 — Sombra** | petición duplicada, respuesta descartada y registrada | ⬜ sin empezar |
| **3 — Canario** | 0,1 % → 1 % → 5 % → 20 % → 50 % | ⬜ sin empezar |
| **4 — 100 %** | — | ⬜ sin empezar |

**Se ha llegado al final del tramo 0 y a la mitad del tramo 1.** La mitad medida es la base; falta la mitad que compara.

Y por bloques del plan de ejecución:

```
Bloque 0 · cerrar M-15               ████████████  CERRADO (apagado · causa NO_DETERMINADA)
Bloque 1 · rama combinada de cuatro  ░░░░░░░░░░░░  NO EMPEZADO
Bloque 2 · brazo contra producción   ░░░░░░░░░░░░  NO EMPEZADO
Bloque 3 · el veredicto              ░░░░░░░░░░░░  cinco NO_MEDIDO
Bloque 4 · M-10, streaming, frontend ░░░░░░░░░░░░  NO EMPEZADO
```

**Ni una sola observación de M-1, M-2, M-4, M-5 o la combinada.** La línea base del 7 de agosto sigue siendo **la única medición de comportamiento que existe**.

## 8.1 · Artefactos emitidos

```
salidas_fase21/00_contexto.json                 relevo completo, llaves SSH, bloqueos
salidas_fase21/01_aceptacion.json               criterio PRE-REGISTRADO y sellado
salidas_fase21/02_m15.json                      veredicto del poller (3 revisiones)
salidas_fase21/07_hallazgos_pendientes.json     H-01 .. H-06
salidas_fase21/08_h02.json                      veredicto del test clínico
validacion_llm/resultados/entradas_produccion_2026-08-09.json
validacion_llm/resultados/paridad_desplegado_2026-08-08.txt   (recorte sin secretos)
```

`01_aceptacion.json` lleva **sello `sha256 = 797b4865e85a8332`**. Hay que **recalcularlo antes de escribir el veredicto** — si no coincide, el criterio se movió.

Y en paralelo, lo que sí llegó al final:

| | estado |
|---|---|
| infraestructura de máquina y driver | ✅ desplegado y verificado |
| CI y despliegue automático | ✅ 8/8 jobs, 4 minutos |
| observabilidad del runner | ✅ desplegado hoy en `2cf21876` |
| M-15 (el poller) | ✅ cerrado — apagado, con el código conservado |
| criterio de aceptación | ✅ pre-registrado y **sellado** |

---

# 9 · Lo que falta

| | horas | acumulado |
|---|---|---:|
| **Bloque 1** — la rama combinada de las cuatro (`5517c431` + `019e2149` + `048b3971`) | 1,0 | 1,0 |
| **Bloque 2** — el brazo contra producción · *84 min medidos* | 1,4 | 2,4 |
| **Bloque 3** — el veredicto contra `797b4865e85a8332` | 0,5 | **2,9** |
| ↑ **aquí se sabe si veintitrés sesiones sirvieron** ↑ | | |
| 4.1.d — las etapas en el frontend | 3 | 5,9 |
| M-10 — escribirla y correr su brazo | 6 | 11,9 |
| las once instancias vivas del patrón | 6 | 17,9 |
| streaming — backend, validación incremental, brazo | 10 | **27,9** |

**≈ 28 horas si la cartera funciona · ≈ 41 si sale no concluyente** y hay que montar el aparato local para atribuir mitigación por mitigación.

**La predicción pre-registrada, que es lo que se va a poner a prueba:**

```
fallos terminales   17/70  →  ~4/70      Fisher 1 cola:  p = 0,0018
utilidad            39,7 % →  ~63 %
p50                 59,1 s →  34,8 s     −41 %
p90                129,4 s →  59,1 s     −54 %
máximo             212,3 s →  89,0 s     −58 %
```

Y el límite honesto del instrumento, dicho de antemano: **la batería distingue un efecto grande de ninguno; no distingue uno mediano.** Si sale 11/70, el veredicto es **no concluyente**, no «no funciona».

---

# 10 · La respuesta a las tres preguntas del principio

**«¿Por qué tarda tanto en responder?»**
Porque **el 58 % de los turnos repara**, y un turno que repara tarda 98,1 s de mediana frente a 34,8 s. El motor de la latencia no es el modelo: es el contrato rechazando su propia salida y volviéndola a pedir. **Arreglar la generación es arreglar la latencia — no son dos proyectos.** Eso es lo que mide el brazo del Bloque 2.

**«¿Por qué a veces no responde nada?»**
Porque el sistema pide un claim de seguridad después de haberle quitado las reglas de política que ese mismo claim exige. Contradicción directa, 13 de 17 fallos terminales, y es exactamente lo que M-1 arregla.

**«¿Cuándo va a responder en 10 segundos?»**
**Con este modelo, en esta GPU, con este contrato: nunca.** A 13,05 tok/s, diez segundos compran 130 tokens de salida — y el suelo obligatorio del sobre, **después** de M-4, son exactamente 130 tokens. Cero para la respuesta clínica. Las únicas salidas son el streaming (cambia qué mide el reloj: ~1 s percibido), cambiar a un modelo MoE (~4,4 s reales, pero destruye la línea base) o adelgazar el contrato clínico. **La primera es la honesta, y su versión barata y sin riesgo es el 4.1.d.**

---

# En una tabla

| | |
|---|---|
| **Lo que funciona hoy** | la máquina, el driver clavado, la CI, el despliegue en 4 min, el arnés, el tokenizador, el preflight, la observabilidad |
| **Lo que se sabe con números** | por qué se cae, por qué calla, por qué tarda — las tres con su cifra, su instrumento y su n |
| **Lo que está listo y sin probar** | cinco mitigaciones, 1 304 tests en verde, cero mediciones contra la realidad |
| **Lo que falta por escribir** | M-10, el streaming, el 4.1.d |
| **Lo que decide todo** | 84 minutos de batería contra producción |
| **Lo que no se alcanza sin cambiar de modelo** | 10 segundos reales |