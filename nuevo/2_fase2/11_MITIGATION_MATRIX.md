# 11 — Matriz de mitigaciones (corregida tras Fase 2)

**Ninguna aplicada.** Tres mitigaciones de la Fase 1 quedan **invalidadas** por
evidencia primaria nueva; se marcan explícitamente en vez de borrarlas.

---

## Invalidadas por la Fase 2

| Mitigación de Fase 1 | Por qué cae |
|---|---|
| **P0 · «Conectar el salvage por claim»** | **Ya está conectado.** `_claim_rejection` se invoca en `send_chat_message.py:4941` en HEAD, y HEAD **es** producción (`HEMOVET_BUILD_REVISION` = `21f18fd8…`). Los 17 fallos ocurrieron con él activo |
| **P1 · «Generación con gramática/JSON Schema»** | **Ya está.** `openai_compatible_client.py:751` envía `payload["format"] = request.response_schema` |
| **P2 · «Prefix caching»** | Ya opera y ahorra el 24,2 % de tokens de entrada. Techo restante: **8,7 % de la latencia total** |

> **La consecuencia conceptual es mayor que las tres correcciones:** si la
> gramática ya garantiza la forma del sobre, los rechazos
> (`policy_rule_id_missing`, `PLT:value,PLT:unit`) son **semánticos**, no
> estructurales. Ninguna técnica de *constrained decoding* puede resolverlos,
> porque una gramática no sabe qué identificador de política existe ni qué
> analito pedía la pregunta.

---

## Matriz vigente

### P0-1 · Reparación dirigida al campo, sin nueva inferencia

| Campo | Contenido |
|---|---|
| **Causa atacada** | C-2/C-4: fallo semántico concreto + reparación inútil |
| **Evidencia interna** | El backend **ya sabe qué falta**: lo publica en `validation_detail_code` (`PLT:value,PLT:unit`, `policy_rule_id_missing`). La reparación regenera ~300 tokens (23 s) para añadir un identificador que el propio backend conoce. Tasa de éxito medida: **0 de 9** |
| **Evidencia externa** | Literatura de *field-level repair* y *deterministic post-processing*: reparar un campo conocido fuera del modelo es la práctica estándar frente a regenerar |
| **Mecanismo** | Si falta `PLT:unit` y el backend tiene el panel, completarlo es una operación determinista, no generativa |
| **Latencia atacada** | **decode de la 2.ª llamada** (41,6 % del cómputo) |
| **Ganancia estimada** | Acotada por los 2.046 s de reparaciones; el reparto exacto **NO ESTIMABLE CON LA EVIDENCIA ACTUAL** hasta E-1 |
| **Riesgo clínico** | **MEDIO**: rellenar campos fuera del modelo cambia quién afirma el dato. Debe provenir de la BD, nunca inferirse |
| **Riesgo técnico** | Bajo | **Complejidad** Media | **Cambio de modelo** No | **Cambio backend** Sí |
| **Validación necesaria** | E-1 (ver qué faltaba realmente) + E-2 |
| **Confianza** | `EVIDENCIA_FUERTE` · **Prioridad P0** · **Investigar y experimentar** |

### P0-2 · Suprimir la segunda llamada tal como está hoy

| Campo | Contenido |
|---|---|
| **Causa atacada** | C-4: la reparación no repara |
| **Evidencia interna** | 0/9 correcciones; las 9 fallan con **el mismo detalle**; bajar la temperatura a 0,1 no cambió nada; ~23 s de GPU por intento. El último recurso salva 4/9 **sin** ella |
| **Mecanismo** | Eliminar un paso cuya tasa de éxito medida es cero |
| **Latencia atacada** | ~23 s por turno reparado (34 de 70 turnos) |
| **Ganancia estimada** | ~780 s de los 4.940 s de la batería (**~16 %**), si el último recurso mantiene su 4/9 |
| **Riesgo clínico** | **BAJO**: no se relaja ninguna validación |
| **Riesgo técnico** | Medio: hay que comprobar que el último recurso cubre lo que hoy cubre la reparación |
| **Confianza** | `CONFIRMADO` (n=9, muestra pequeña) · **P0** · **Experimentar con N≥50** |

### P1-1 · Revisar la exigencia de `policy_rule_id`

Detalle que más rechazos causa (**15**) y que mata al último recurso **5 de 9**
veces. Es un identificador de regla, no contenido clínico → riesgo clínico
**BAJO**. `CONFIRMADO` · **P1**.

### P1-2 · Modelo pequeño para ámbito, identidad y guardarraíles

Hoy una pregunta de identidad cuesta 19-23 s a 13 tok/s con un 27B. Socratic
Tutor usa `gemma-4-E4B` exactamente para esto. **VRAM disponible: 5,6 GB.**
Riesgo clínico **MEDIO** (la barrera de seguridad pasaría a un modelo menor, y
hoy funciona 4/4). `EVIDENCIA_FUERTE` · **P1** · exige E-8 con criterio de
parada: **si falla una sola barrera, se descarta**.

### P1-3 · Corregir el clasificador de ámbito

Regex con confianzas fijas; rechaza *«¿en qué puedes ayudarme con un hemograma
canino?»*. No mejora latencia; **sí** la primera impresión. `CONFIRMADO` · **P1**.

### P2-1 · Speculative decoding / MTP

| Campo | Contenido |
|---|---|
| **Causa atacada** | C-1: decode (88,4 %) |
| **Evidencia externa** | **Qwen3.6 27B, RTX 3090: 38 → 65 tok/s (1,71×)**. Gemma 2 27B: 1,8×. Latencia de petición única: +20-50 % |
| **Limitaciones declaradas** | Benchmarks en RTX 3090 y M2 Max, **no en L4**; la L4 tiene menos cómputo libre para verificar; interacción con `format` **no verificada**; si la aceptación cae del 50 % **ralentiza** |
| **Riesgo clínico** | Bajo si se preserva la distribución del modelo objetivo |
| **Complejidad** | **Alta**: modelo borrador + probable cambio de motor |
| **Confianza** | `HIPOTESIS` · **P2** · **Medir antes de decidir (E-7)** |

### P2-2 · GPU con más ancho de banda

Única palanca que sube el techo **sin tocar calidad ni contrato**. L40S
(~864 GB/s) ≈ 2,9× el techo de la L4. Riesgo clínico **NULO**. Es una decisión de
coste, no de ingeniería. `CONFIRMADO` el mecanismo · **P2**.

### P3 · Memoria de 10 pares con presupuesto por tokens

`history_limit = 12` **mensajes** = 6 pares, frente a los 10 requeridos. Coste:
~500 tokens por par, dentro del 11,5 % del prefill y amortiguado por el caché.
**Advertencia propia:** un resumen recalculado cada turno **invalidaría el
context checkpoint** de 149,6 MiB que hoy sí se reutiliza. `CONFIRMADO` el
diagnóstico · **P3** · exige E-9.

---

## Descartadas

| Mitigación | Por qué |
|---|---|
| Migrar a vLLM/SGLang **por throughput** | Sus ventajas publicadas son de **concurrencia**; HemoVet corre `-np 1` con cola de 0 ms. Podría entrar por MTP, no por batching |
| Otra cuantización | Q4_K_M es un equilibrio razonable; bajar degrada fidelidad numérica, que es justo lo que no se puede perder |
| Flash Attention / KV quantization | **Ya activos** (`--flash-attn on`, `q8_0`) |
| Reducir RAG | 8 de 70 preguntas, 183-655 ms. No es una causa |
| `OLLAMA_NUM_PARALLEL` | Cola de 0 ms. No hay problema que resolver |
| Constrained decoding | **Ya está** (C-2) |

---

## Escenarios combinados (aritmética sobre datos reales)

Base: 4.940 s totales, 4.865 s de cómputo del modelo, mediana 59,1 s.

| Escenario | Cambio | Mediana estimada | Nota |
|---|---|---|---|
| **Baseline** | — | 59,1 s | 1,9 llamadas/pregunta |
| **A** · sin 2.ª llamada inútil | −23 s en 34 turnos | ~**43 s** | P0-2 |
| **B** · reparación dirigida por campo | evita la mayoría de 2.ª y 3.ª llamadas | ~**35 s** | P0-1, techo si funciona |
| **C** · decode 1,71× (MTP) | 13,7 → 23,4 tok/s | ~**35 s** | P2-1, sin tocar el pipeline |
| **D** · prefill perfecto | −8,7 % | ~**54 s** | techo de todo el caching |
| **E** · A+B+C | pipeline arreglado **y** decode 1,71× | ~**21 s** | los dos ejes se multiplican |

> El escenario D existe en la tabla para dejar constancia de por qué **no** es la
> vía: la optimización de prefill más perfecta imaginable recorta 5 segundos de
> 59. Los escenarios A/B y C son ortogonales y **se multiplican**: arreglar el
> pipeline sin tocar hardware da tanto como duplicar el hardware sin arreglar el
> pipeline.
