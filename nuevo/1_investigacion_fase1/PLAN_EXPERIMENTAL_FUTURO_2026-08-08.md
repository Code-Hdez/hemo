# Plan experimental futuro

**Ninguno de estos experimentos se ha ejecutado.** Los que exigen tocar
producción quedan explícitamente fuera de la fase actual. Se ordenan por
información obtenida ÷ coste.

---

## E-1 — Leer la envoltura rechazada · **PRIORIDAD MÁXIMA**

**Cierra:** `H-14` (`NO_OBSERVABLE`) y decide entre `VALIDATOR_FALSE_REJECTION`
y `MODEL_GENERATION_FAILURE`, que es la bifurcación de la que depende toda la
estrategia de mitigación.

**Cómo:** `CHAT_STRUCTURED_DEBUG_DIR` ya existe en el código
(`send_chat_message.py:301`) y vuelca cada envoltura rechazada íntegra con sus
claims. Está vacío en producción.

**Procedimiento:** apuntarlo a un directorio, lanzar **sólo** los 10 casos de la
repetición `REP-PLT`, apagarlo, y recoger los ficheros.

**Riesgo:** escribe texto de paciente en disco. **Encender para un diagnóstico y
apagar después** — es lo que el propio commit `587ef41d` recomienda.

**Criterio de éxito:** para las ~9 generaciones rechazadas, saber si el texto
contenía `290` y la unidad de PLT.

**Es un cambio de entorno en producción: fuera del alcance de esta fase.**

---

## E-2 — Conectar el *salvage* de envoltura en un entorno de prueba

**Cierra:** la mitigación nº 1 de la matriz.

**Cómo:** el commit `bd70e0d8` implementa salvage por claim y dice
explícitamente que **no está conectado a ningún turno**. Activarlo en un entorno
que **no sea producción**, con la batería de 70 preguntas.

**Métrica:** llamadas al modelo por pregunta (hoy 1,9), tasa de
`generation_repair_failed` (hoy 24 %), latencia mediana (hoy 59,1 s).

**Hipótesis falsable:** si el salvage funciona, los turnos con ≥1 claim válido
deberían dejar de regenerar; la reducción esperada está acotada por el 41,6 %
del cómputo que hoy va a reparaciones.

---

## E-3 — Repetición ampliada con `seed` fijo

**Cierra:** `H-03` con intervalo de confianza, y separa muestreo de contrato.

**Cómo:** N = 50 repeticiones de `SEL-08`. Dos brazos: con `seed` fijo y sin él.

**Qué distingue:** si con `seed` fijo el resultado es **siempre el mismo**, la
variabilidad es puramente de muestreo. Si sigue variando, hay no determinismo en
otro punto (orden de contexto, orden de RAG, parser).

**Coste:** ~50 × 75 s ≈ 60 min de producción, sin cambiar configuración salvo el
parámetro `seed` de la petición.

---

## E-4 — Muestreo de GPU sincronizado con la batería

**Cierra:** la correlación temporal GPU↔fase que hoy se infiere pero no se midió.

**Cómo:** `nvidia-smi --query-gpu=utilization.gpu,power.draw --format=csv -l 1`
en la VM de GPU (lectura pura) mientras corre un subconjunto de 10 preguntas,
correlacionando por marca de tiempo.

**Qué demostraría:** el patrón `GPU alta → generación / GPU baja → validación /
GPU alta → reparación` haría **físicamente visible** la segunda inferencia.

**Riesgo:** ninguno. Es sólo lectura.

---

## E-5 — Instrumentar qué regla dispara el rechazo de ámbito

**Cierra:** `H-04` de mecanismo confirmado a regla concreta identificada.

**Cómo:** ejecutar `intent_classifier.py` **en local**, fuera de producción,
contra las 5 preguntas de identidad/cortesía, registrando qué patrón casa.

**Coste:** minutos. No toca producción en absoluto. **Es el más barato de toda
la lista y debería hacerse primero por eso.**

---

## E-6 — Cerrar la identidad del despliegue

**Cierra:** `H-15`, de `EVIDENCIA_FUERTE` a `CONFIRMADO`.

**Cómo:** `docker inspect` de la imagen del backend leyendo labels y build
metadata; comparar con `git log` local y con el remoto.

**Riesgo:** ninguno, es lectura.

---

## E-7 — `llama-bench` sobre la misma L4

**Cierra:** `H-01` con una medida directa en vez de una comparación externa.

**Cómo:** ejecutar `llama-bench` con el mismo gguf y `-c 16384` en la L4,
**fuera de horas de uso**, y comparar con los 13,05 tok/s observados.

**Qué demostraría:** si `llama-bench` da ~13 tok/s, la configuración es óptima y
el techo es el hardware. Si da bastante más, hay margen de configuración.

**Riesgo:** ocupa la GPU mientras corre. Requiere ventana acordada.

---

## E-8 — Modelo pequeño para tareas triviales, en banco de pruebas

**Cierra:** `H-05`.

**Cómo:** cargar un modelo de 3–8 B **fuera de producción** y medir, sobre el
subconjunto de identidad/ámbito/seguridad (22 de las 70 preguntas): latencia y,
sobre todo, **si mantiene 4/4 en los rechazos de seguridad**.

**Criterio de parada:** si falla **una sola** barrera de seguridad, se descarta.

---

## E-9 — Memoria de 10 pares con presupuesto de tokens

**Cierra:** `H-13` y el objetivo de producto.

**Cómo:** en banco de pruebas, conversación de 15 turnos con `history_limit`
elevado, midiendo `prompt_eval_count` por turno **y la tasa de acierto del
context checkpoint**.

**La pregunta que sólo este experimento responde:** ¿un resumen periódico
invalida el checkpoint de 149,6 MiB que hoy sí se reutiliza? Si lo invalida cada
turno, la compactación **empeoraría** el prefill en vez de mejorarlo.

---

## Lo que NO debe hacerse todavía

| No hacer | Por qué |
|---|---|
| Migrar a vLLM/SGLang | Sus beneficios publicados son de **throughput concurrente**; HemoVet es interactivo con `-np 1`. Sin E-7 no se sabe si hay margen |
| Cambiar el modelo por uno menor | Exige revalidación clínica completa. Sólo tras E-8 |
| Activar streaming de tokens | Choca con la garantía de validar antes de mostrar |
| Tocar prefix caching | Ya funciona (§6) y su techo es el 11,3 % |
| Subir `OLLAMA_NUM_PARALLEL` | La cola mide 0 ms. No hay problema que resolver |
| Quitar validadores | Son el aporte diferencial del proyecto |

---

## Objetivos de servicio, para después de medir

No se fijan todavía: primero E-1 y E-2, porque cambian el punto de partida.
Cuando existan, deberían formularse por modo, distinguiendo:

- **TTFT real** (hoy no medible: no hay eventos de token)
- Latencia p50/p90/p95 separada por `general`, `selected_hemogram`,
  `hemogram_history` (hoy: 23,0 / 71,9 / 90,6 s de mediana)
- **Tasa de reparación** (hoy 49 % de los turnos)
- **Tasa de error** (hoy 24 %)
- **Llamadas al modelo por pregunta** (hoy 1,9)

Esa última es probablemente la métrica más honesta del sistema: mientras siga
por encima de 1,0, se está pagando dos veces por la misma respuesta.
