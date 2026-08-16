# El commit vacío no despliega — tres «éxitos» que no enviaron nada

**Fecha:** 13-ago-2026 · **Naturaleza:** defecto de método, no del sistema

---

## Qué pasó

Para forzar un redespliegue tras un desalojo de la GPU spot usé **commits vacíos**
(`git commit --allow-empty`). El workflow los aceptó, corrió los tests, y terminó
en **verde**. Yo lo leí como «desplegado».

`[MEDIDO]` Desglose de los tres runs, vía `gh run view --json jobs`:

| Commit | Resultado | Build | Deploy | Smoke |
|---|---|---|---|---|
| `4c3c0558` | success | **skipped** | **skipped** | **skipped** |
| `0b471aaa` | success | **skipped** | **skipped** | **skipped** |
| `aa3d6532` | success | **skipped** | **skipped** | **skipped** |

`[MEDIDO]` Los tres tienen `git show --stat` **vacío**: cero ficheros cambiados.
El job `Resolve revision scope` calcula `publish_release` por rutas tocadas, no
encuentra ninguna, y salta build, deploy y smoke. **El workflow hizo lo
correcto.** El error fue mío: pedí un redespliegue con un commit que, por
definición, no cambia nada que desplegar.

## Por qué importa: contamina una medición

`[MEDIDO]` Cronología en UTC:

```
18:37→18:59  38864178  «first_validation_reason da el codigo real»   FAILURE
19:03→19:06  4c3c0558  commit vacío                                  success (nada enviado)
19:30→19:33  0b471aaa  commit vacío                                  success (nada enviado)
19:41        ← se corre la batería puerta3h
```

La instrumentación que da el **código real** del validador se desplegó en
`38864178`, y **ese despliegue falló**. Los dos «éxitos» posteriores no enviaron
nada. Luego, cuando corrí `puerta3h`, producción seguía ejecutando `6547cdb8`,
que lleva la instrumentación **anterior**:

```python
_validation_detail_code(initial_candidate.validation) or initial_candidate.validation.disposition
```

`[DERIVADO]` Eso explica el dato que no cuadraba, y lo explica entero:

| Turnos | Valor observado | Rama que lo produce |
|---|---|---|
| 34 válidos | `valid` | `detail_code` es `None` → cae al **disposition** |
| GEN-03/12/13 | `invalid` | `detail_code` es `None` → cae al **disposition** |
| HIS-15 | `unsupported_numeric_claim:plt` | `detail_code` **sí** proyecta ese motivo |

`[MEDIDO]` `_validation_detail_code` solo devuelve algo para una lista cerrada de
motivos; `unsupported_numeric_claim` está en ella y compone
`f"{reason}:{parameter_code}"`. Para todo lo demás devuelve `None`.

> **Los tres `invalid` nunca fueron un misterio del validador. Eran el
> `disposition` a secas, porque el arreglo que ponía el motivo real jamás llegó a
> producción.** Pasé una sesión buscando un fallo clínico donde solo había un
> despliegue que no ocurrió.

## Lo que sí quedó descartado por el camino

`[MEDIDO]` Antes de encontrar la causa, dos comprobaciones que conservan valor:

1. **Ningún sitio de construcción produce un `reason` vacío.** Barrido AST de los
   18 `OutputValidation(...)` de `send_chat_message.py` más los 12 de
   `output_validator.py`: todos fijan un motivo, y el valor por defecto del campo
   es `"ok"`, no `""`.
2. **Las respuestas publicadas de los 12 turnos `general` pasan el validador en
   local**, con `case_facts=[]` y `patient_in_scope=False`. Es decir: lo que se
   rechazó fue el **primer** candidato, cuyo texto no se persiste.

## La regla que queda

**Un redespliegue se fuerza con `workflow_dispatch`, no con un commit vacío.**
Y antes de dar por buena cualquier medición, se comprueba que el run que la
precede tiene `Build`, `Deploy` y `Smoke` en **success**, no solo el run entero
en verde.

`[MEDIDO]` Verificación aplicada a la única cadena que sí envió código:

| Commit | Build | Deploy | Smoke |
|---|---|---|---|
| `b83cb379` | success | success | **failure** (GPU caída → `LLM_PROVIDER_UNAVAILABLE`) |

Un smoke rojo por proveedor caído **no impide** que el código ya esté en la VM:
build, publish y deploy se completaron antes. Producción corre `b83cb379`, que sí
lleva la instrumentación cruda `r=…|safe=…|intent=…|d=…`.

## Consecuencia colateral que hubo que reparar

`[MEDIDO]` El «revert de seguridad» del secreto a
`CHAT_STRUCTURED_OUTPUT_ENABLED=1` viajaba en `aa3d6532`, uno de los commits
vacíos. **Nunca se aplicó a la VM.** El secreto de GitHub sí quedó a `1`, pero el
fichero de entorno de la máquina sigue a `0` hasta el próximo despliegue real.

Es el mismo modo de fallo que la trampa de `${VAR:-default}` documentada en
`PUERTA_3_INTENTO_FALLIDO.md`: **creer que un cambio de configuración está activo
porque se escribió, sin comprobar dónde aterrizó.** Dos veces la misma lección en
una sesión.

---

Relacionado: `PUERTA_3_INTENTO_FALLIDO.md`, `PUERTA_3_CAUSA_IDENTIFICADA.md`.
