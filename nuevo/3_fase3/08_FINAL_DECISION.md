# 08 — ¿Por qué HemoVet tarda tanto?

## De los 59,1 s medianos

| Componente | Segundos | Naturaleza |
|---|---:|---|
| Decode de la 1.ª generación | **~34 s** | **INEVITABLE** con este stack |
| Regeneraciones (2.ª/3.ª/4.ª) | **+63,4 s** cuando ocurren (48,6 % de los turnos) | **EVITABLE** |
| Prefill | ~6 s | parcialmente evitable (techo 8,7 %) |
| Backend, red, validación, cola | **~0,3 s** | irrelevante |

Sobre el total de la batería: **56,8 % suelo físico · 40,3 % amplificación
evitable · 3,0 % coste secundario.**

## ¿Cuáles son inevitables con el stack actual?

Los **~34 s de la primera generación**. El modelo produce 13,04-13,71 tok/s
—medido llamándolo directamente, sin HemoVet— y una respuesta mediana son 375
tokens. Eso es aritmética, no configuración.

**Matiz que retiro de la Fase 2:** que sea *inevitable con este stack* no
significa que sea el máximo físico posible. Hay evidencia upstream de 8-14 % de
margen entre Ollama y llama.cpp, y no lo he medido en esta L4. Con ese margen,
34 s → ~30 s. `NO_OBSERVABLE` hasta E-10.

## ¿Cuáles son evitables?

**1.989 s de 4.940 (40,3 %)**: todo el decode y prefill de las generaciones
segunda, tercera y cuarta. Y **35.502 de 55.562 tokens generados (63,9 %) nunca
llegaron al usuario.**

## ¿Qué mecanismo exacto genera los segundos evitables?

Tres mecanismos encadenados, los tres `CONFIRMADO`:

**1. Un contrato que el artefacto que restringe la generación no expresa.**
El JSON Schema enviado como `format` declara
`GeneratedClaim.required = [claim_id, text, claim_type]`. `policy_rule_ids` y
`fact_ids` llevan `default_factory=list` y **no son required**. La gramática, por
tanto, **permite** un claim sin ellos. La obligación real vive en
`structured_response.py:140`, es **condicional al `claim_type`**, y se evalúa
**después** de parsear. El modelo cumple el contrato que se le impone y falla el
que se le juzga.

**2. Un salvage que no cubre el caso frecuente.** `if not kept: raise
first_rejection`: si todos los claims fallan, no hay nada que salvar. En
`SEL-08`, `materialized_fact_count = 1` — un único claim, y es el que falla.

**3. Un repair que no aporta información nueva.** El prompt de reparación crece
sólo **+2,48 %** de mediana (min +1,2 %, máx +7,4 %). En 11 de 19 turnos vuelve
a fallar **con el mismo detalle**. En el experimento controlado: **0 de 9**.
Qué contiene exactamente ese prompt: `NO_OBSERVABLE`.

## ¿Qué todavía no puede demostrarse?

| Incógnita | Estado |
|---|---|
| Si la generación descartada era clínicamente correcta | `NO_OBSERVABLE` — decide entre «el validador protege» y «el validador desperdicia» |
| Qué información concreta añade el repair prompt | `NO_OBSERVABLE` — sólo se conoce su tamaño |
| Si existe margen real de engine en esta L4 | `NO_OBSERVABLE` — requiere E-10 |
| Si MTP rinde en L4 con salida JSON | `HIPÓTESIS` — upstream reporta desde 1,35× hasta peor que baseline según workload |
