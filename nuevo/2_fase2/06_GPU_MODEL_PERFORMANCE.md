# 06 — GPU, modelo y rendimiento de decode

## La pregunta: ¿13 tok/s es razonable para *esta* combinación?

La Fase 1 respondió por comparación con una RTX 4090, lo cual es débil. Aquí se
responde por **aritmética de ancho de banda**, que es el mecanismo físico real, y
se contrasta con una **medida directa contra el modelo**, fuera del pipeline.

---

## 1. Medida directa (experimento nuevo de Fase 2)

Se llamó a `/api/generate` de Ollama **saltándose todo HemoVet**, con
`seed=42`, `temperature=0.3`, `top_k=20`, `top_p=0.8`:

| Configuración | `eval_count` | tok/s |
|---|---:|---:|
| Sin `format`, `think` por defecto | 400 | **13,61** |
| Con `format` (JSON Schema tipo sobre) | 200 | **13,04** |
| `think=False` | 115 | **13,70** |
| `think=True` | 400 | **13,71** |

**Rango: 13,04 – 13,71 tok/s.** El pipeline de HemoVet mide **13,05** de mediana
sobre 133 llamadas.

> **Conclusión falsable:** el pipeline de HemoVet **no añade coste de decode
> medible**. La velocidad que ve el usuario es la del modelo en esa GPU.
> `CONFIRMADO`.

### Coste de la gramática

Ratio con gramática / sin gramática = **0,951** → la decodificación restringida
cuesta **~5 % de velocidad**. Es real pero **no es una causa**: no explica una
latencia de 59 s de mediana. `DESCARTADO` como causa.

---

## 2. El techo físico

Decode autoregresivo con batch 1 es **memory-bound**: para producir cada token
hay que leer **todos los pesos** desde VRAM.

| Magnitud | Valor | Fuente |
|---|---|---|
| Ancho de banda L4 | **300 GB/s** (GDDR6, bus 192-bit) | Especificación NVIDIA |
| Modelo en VRAM | **16.926.501.764 B = 16,93 GB** | `/api/ps` (`size_vram`) |

```
techo teórico = 300 GB/s ÷ 16,93 GB = 17,7 tokens/s
observado     = 13,7 tokens/s
eficiencia    = 13,7 / 17,7 = 77,4 %
```

**77 % del máximo teórico.** La eficiencia real habitual en inferencia
memory-bound se sitúa entre el 60 % y el 80 %: HemoVet está en la parte alta.

> **Esto es lo más importante de todo el informe sobre hardware:** no existe
> configuración, flag ni tuning que recupere un factor relevante. Flash Attention
> ya está activo, el KV está cuantizado a q8_0, el modelo está 100 % en VRAM y no
> hay offload. **El sistema ya está exprimiendo la L4.**

### Por qué la comparación con una 4090 era correcta pero por la razón equivocada

Una RTX 4090 tiene ~1.008 GB/s. Su techo para el mismo modelo sería
1.008 ÷ 16,93 ≈ **59,5 tok/s**, y se reportan ~40 tok/s reales (67 % de
eficiencia). La proporción observada 13,7/40 ≈ 0,34 coincide con la de anchos de
banda 300/1.008 ≈ 0,30. **La causa no es «la 4090 es mejor»: es que el decode
escala con el ancho de banda de memoria.**

---

## 3. Qué mueve realmente esta cifra

Sólo tres palancas, y sólo una no toca calidad:

| Palanca | Efecto sobre el techo | Coste |
|---|---|---|
| **GPU con más ancho de banda** (L40S ~864 GB/s, A100 ~2.039 GB/s) | Proporcional: L40S ≈ 2,9× | Coste de infraestructura. **Cero riesgo clínico** |
| **Modelo más pequeño** (9-14 B) | Proporcional al tamaño: un 9B Q4 (~5,5 GB) daría ~3× | **Exige revalidación clínica completa** |
| **Speculative decoding / MTP** | Rompe la relación 1 token = 1 lectura completa | Cambio de motor + experimento |

### Cuantización

`Q4_K_M` ocupa 16,93 GB. Bajar a Q3_K_M reduciría tamaño y por tanto subiría
tok/s, pero **degrada la fidelidad numérica**, que es justo lo que HemoVet no
puede permitirse: el sistema debe copiar `PLT 290` sin equivocarse. Subir a Q5/Q6
lo empeoraría en velocidad. **La cuantización actual es una elección razonable y
no es una restricción a corregir.** `DESCARTADO` como palanca.

---

## 4. Speculative decoding / MTP — la única técnica que ataca la causa dominante

**Evidencia externa directamente aplicable** (mismo modelo, misma familia):

| Fuente | Modelo | GPU | Antes | Después | Ganancia |
|---|---|---|---:|---:|---|
| Comunidad (nivel C) | **Qwen3.6 27B** | RTX 3090 | 38 tok/s | 65 tok/s | **1,71×** |
| Comunidad (nivel C) | Gemma 2 27B | — | 67 tok/s | 120 tok/s | 1,8× |
| Blogs de ingeniería | genérico | — | — | — | 20-50 % en latencia de petición única |

**Condición crítica documentada:** si la tasa de aceptación del borrador cae por
debajo del 50 %, **speculative decoding ralentiza en vez de acelerar**.

### Aplicabilidad a HemoVet, con sus limitaciones declaradas

| A favor | En contra |
|---|---|
| Ataca **decode**, que es el 88,4 % del tiempo | Los benchmarks son de RTX 3090 y M2 Max, **no de L4** |
| El modelo de HemoVet es exactamente Qwen3.6 27B | La L4 tiene menos cómputo libre para verificar el borrador |
| Mejora **latencia de petición única**, que es el workload real | Interacción con `format`/gramática **no verificada** |
| No cambia el modelo principal ni sus respuestas | Exige un modelo borrador y probablemente cambiar de motor |

> **No se recomienda adoptarlo. Se recomienda medirlo** (experimento E-7 del
> backlog), porque es la única técnica con evidencia de atacar la causa nº 1.

---

## 5. Lo que queda descartado sobre hardware

| Hipótesis | Estado | Evidencia |
|---|---|---|
| CPU fallback | `DESCARTADO` | `inference_device=full_gpu` en 133/133 |
| Offload parcial | `DESCARTADO` | `size_vram == size` |
| Presión de VRAM | `DESCARTADO` | 17.418 de 23.034 MiB → 5,6 GB libres |
| Arranque en frío | `DESCARTADO` | `load_duration` mediana 554 ms; `expires_at` año 2318 |
| GPU throttling | `NO_OBSERVABLE` | No se muestreó durante la batería (E-3). Temperatura en reposo 69 °C, 32,7 W de 72 W TDP: no sugiere throttling |
| Cola / concurrencia | `DESCARTADO` | `queue_duration_ms` mediana 0, máx 1 |
| La gramática ralentiza | `DESCARTADO` como causa | −5 % medido |
| Thinking consume decode | `DESCARTADO` por experimento | `think=False` → 0 chars de thinking |
