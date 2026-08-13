# 13 — Preguntas abiertas

| # | Pregunta | Estado | Qué la cerraría |
|---|---|---|---|
| 1 | ¿La generación descartada era clínicamente correcta? | `NO_OBSERVABLE` | **E-1**: volcado controlado. Es la incógnita de mayor valor: decide entre `VALIDATOR_FALSE_POSITIVE` y `VALIDATOR_TRUE_POSITIVE` |
| 2 | ¿Qué contiene exactamente el repair prompt frente al primario? | `NO_OBSERVABLE` | E-1. Sólo se conocen tamaños: 3.871 → 3.966 tokens (+2,5 %) |
| 3 | ¿Qué chunks de RAG se inyectan? | `NO_OBSERVABLE` | La telemetría da recuentos y scores, no `chunk_id` ni texto |
| 4 | ¿Hay GPU throttling durante la generación? | `NO_OBSERVABLE` | **E-3**: muestreo de `nvidia-smi` sincronizado. En reposo: 69 °C y 32,7 W de 72 W TDP, que no sugiere throttling |
| 5 | ¿Qué regla regex concreta dispara el rechazo de ámbito? | `HIPOTESIS` | **E-5**: ejecutar `intent_classifier.py` en local sobre las 5 preguntas |
| 6 | ¿La tasa 0/9 de la reparación se mantiene con N grande? | `CONFIRMADO` con n=9 | **E-6**: N≥50 para acotar el intervalo |
| 7 | ¿Speculative decoding rinde 1,71× en una **L4**? | `HIPOTESIS` | **E-7**. Los benchmarks son de RTX 3090 y M2 Max |
| 8 | ¿Un resumen periódico invalidaría el context checkpoint? | `HIPOTESIS` | **E-9**. Es el riesgo no obvio de la memoria de 10 pares |
| 9 | ¿El salvage llega a salvar algo alguna vez? | `HIPOTESIS` | Instrumentar cuántos claims sobreviven por turno. Está activo pero en el caso PLT `materialized_fact_count=1` |
