# 05 — Margen de serving: RETRACTACIÓN de la conclusión de Fase 2

## Lo que dije y por qué era demasiado categórico

Fase 2 afirmó: *«300 ÷ 16,93 = 17,7 tok/s de techo; 13,7 = 77 %; no hay margen
de configuración que recuperar»*.

**La primera parte es una aproximación roofline útil. La última frase no está
demostrada** y se retira, por tres razones:

1. **El roofline es una simplificación.** Qwen3.6-27B tiene 64 capas y
   arquitectura **híbrida** (Gated DeltaNet + Gated Attention). Hay
   dequantización, estados recurrentes, tráfico de activaciones, lanzamientos de
   kernel y eficiencia efectiva de memoria que `bandwidth ÷ model_size` no
   modela. Esa división da un orden de magnitud, no un máximo práctico.
2. **Existe evidencia upstream de margen entre engines.** Issues de Ollama
   (#15771 sobre Qwen3.6-35B-A3B, #14861 sobre Qwen3.5:35b) reportan a Ollama
   sensiblemente más lento que llama.cpp con el mismo modelo y GPU. Benchmarks
   independientes sitúan a **Ollama entre un 8 % y un 14 % por detrás** de
   llama.cpp por categoría, atribuido a la capa Go que envuelve al llama.cpp
   embebido.
3. **No he medido llama.cpp directamente en esta L4.** Sin esa medida, decir
   «no hay margen» es inferencia, no evidencia.

## Lo que sí puede afirmarse

| Afirmación | Estado |
|---|---|
| El baseline medido es **13,04–13,71 tok/s** (4 pruebas directas contra el modelo) | `CONFIRMADO` |
| El pipeline de HemoVet **no añade coste de decode** (13,05 vs 13,04–13,71) | `CONFIRMADO` |
| 13,7 tok/s está **en el orden de magnitud** de una estimación memory-bandwidth-limited para L4 + 16,93 GB | `EVIDENCIA_FUERTE` |
| **No existe margen de serving** | **RETIRADO** → `NO_OBSERVABLE` sin el experimento E-10 |

## Margen plausible, acotado

Si el 8-14 % reportado se reprodujera en esta L4: 13,7 → **14,8-15,6 tok/s**.
Sobre una mediana de 59,1 s eso sería **~53-55 s**. Real, pero **no es la
solución**: no cambia el orden de magnitud del problema.

**Experimento requerido (E-10):** ejecutar `llama-bench` o un `llama-server`
independiente con el **mismo gguf, mismo `-c 16384`, mismos flags** en la misma
L4, fuera de horas de uso, y comparar contra los 13,7 tok/s. Sólo eso convierte
«hay margen» o «no lo hay» en evidencia.
