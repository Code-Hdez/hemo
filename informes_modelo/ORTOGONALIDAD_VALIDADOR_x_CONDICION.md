# Ortogonalidad validador × condición — la columna de referencia

**Fecha:** 2026-08-15 · **Herramienta:** `validacion_llm/scripts/ortogonalidad.py` · **GPU: cero**
**Estado:** columna `base` medida. Las otras tres **no existen** hasta que G.1, H e I se implementen.

---

## 1. Por qué esta matriz, y por qué es gratis

El plan asigna cada clase de rechazo a un bloque y da por hecho que atacan
poblaciones disjuntas. `[MEDIDO]` La campaña v3 mostró que **eso no es exacto**:
3 de 96 fallos cruzan la frontera de ámbito.

Asumir la independencia y luego atribuir el efecto a cada bloque sería el error
que la literatura de ablación describe: las ablaciones por pares tienen un efecto
más fuerte que la suma de las individuales.

**Pero demostrarla no cuesta un segundo de GPU.** Los `.jsonl` guardan el texto
publicado; reejecutar los cuatro validadores sobre las cuatro condiciones es
aritmética sobre datos que ya existen.

`[DERIVADO]` **El punto débil es concreto:** la gramática del Bloque H **cambia el
texto**, y ese texto alimenta el léxico de recomendación del Bloque I. Es la
interacción más probable de las tres, y es justo la que la diagonal detectaría.

---

## 2. La columna `base`, medida

`[MEDIDO]` Campaña v3, 405 turnos, **356 con texto publicado**:

| Validador | `base` |
|---|--:|
| `indirect_treatment` (con `_is_safe_refusal` aplicado) | **0** |
| `definitive_diagnosis` | **0** |
| `dose_instruction` | **0** |
| `internal_material` | **0** |

> **Los cuatro disparan cero veces sobre lo publicado.** Es una confirmación
> **independiente** de la Puerta S: se hizo en frío, desde fuera del backend,
> importando sus mismos predicados y pasándolos sobre las respuestas guardadas.
> No se aceptó el `validation_status` que el propio sistema declara.

`[MEDIDO]` Y lo que el validador **declaró en su momento**, sobre la primera
generación de los 405:

```
ambiguous_parameter_claim          31
indirect_treatment_recommendation  24
unsupported_numeric_claim          14
missing_evidence_attribution       11
unsupported_status_claim            7
definitive_diagnosis                7
```

> **Nota de consistencia:** `definitive_diagnosis` sale 7 aquí y 6 en
> `CAMPANA_FINAL_RESULTADO.md`. No es una discrepancia: esta herramienta lee los
> **405** turnos lanzados y el veredicto evalúa los **400** del plan, tras el
> truncamiento de §3. El caso extra es uno de los cinco truncados.

---

## 3. Lo que esta columna ya demuestra, y lo que no

**Demuestra:** el sistema de seguridad funciona. Los 96 rechazos son borradores
detenidos, y lo que llega al usuario está limpio según cuatro comprobaciones
independientes reejecutadas desde fuera.

**No demuestra nada sobre ortogonalidad.** Con una sola condición la matriz no
puede ser diagonal ni dejar de serlo, y la herramienta lo dice en vez de
insinuarlo:

```
UNA SOLA CONDICIÓN: la matriz no puede ser diagonal ni dejar de serlo.
Esto es la columna de referencia; la prueba de ortogonalidad necesita
las condiciones del plan, y esas no existen hasta que se implementen.
```

---

## 4. Cómo se completa

Cuando existan las campañas de las otras condiciones:

```bash
python3 validacion_llm/scripts/ortogonalidad.py \
    base=validacion_llm/resultados/campana_v3_2026-08-15 \
    G1=...  H=...  I=...
```

| Resultado | Consecuencia |
|---|---|
| **Diagonal** | La independencia queda **demostrada**. La Fase B del pre-registro de ablación —2³ × 3 semillas, 38 h-GPU— puede **omitirse con justificación real** en lugar de asumida |
| **No diagonal** | La Fase B es **obligatoria**: los efectos no son separables y atribuirlos por separado sería sesgado |

`[DERIVADO]` **Ese es el valor económico de esta matriz:** puede ahorrar 38 horas
de A100, y su coste es cero.

---

## 5. Limitación declarada

Solo se puede reejecutar sobre el texto **publicado**. Los turnos terminales —49
de 400 en la línea base— no publican nada, así que la matriz cubre los que
respondieron, que son también los que el validador dejó pasar. Es un límite del
diseño de privacidad clínica, no de la herramienta, y se reporta con su
denominador: **356 de 405**.
