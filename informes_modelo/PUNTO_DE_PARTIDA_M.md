# Punto de partida de la fase M — todo lo que se mida después se compara contra esto

**Fecha:** 2026-08-15 · **GPU: cero** · **VMs:** las tres `TERMINATED`

> GOAL, `I-1`: *«EMPUJA LA RAMA ANTES QUE NADA: `bloque-i-acepcion-colocacion` tiene
> 8 commits que solo existen en local.»* Hecho y verificado **en el remoto**, no
> solo en el disco.

---

## 1. La rama, empujada y comprobada del otro lado

```
origin  https://github.com/xPshycho/hemogramas-proyectoICC.git
rama    bloque-i-acepcion-colocacion  →  [new branch]
```

`[MEDIDO]` **8 commits en `origin/main..origin/bloque-i-acepcion-colocacion`**, y
el SHA local y el remoto son el mismo:

```
local   9bb78b670a20bcfc32f3b856e0f798acb54ce479
remoto  9bb78b670a20bcfc32f3b856e0f798acb54ce479   ✔ idénticos
```

| commit | |
|---|---|
| `9bb78b67` | el arnés guarda `case_facts`, y la medida que sí discrimina |
| `237d0a84` | balance punto por punto de «HECHO CUANDO EXISTEN» |
| `d6c8e938` | J.0 · los reintentos de conexión no se pueden contar — y no hacía falta |
| `fef9cd41` | revisión ciega por daño (I-6) + dos sellos que estaban rotos |
| `060cb627` | G.1 · la ambigüedad medida en 2429 hemogramas reales |
| `b7450a61` | H · las dos condiciones se cumplen, y el dato desaconseja medirlo tal cual |
| `76025465` | ESTADO §4.1 · la petición de firma de I.2 corregida con lo medido |
| `d85f3bd3` | instrumentación de acepción, y la refutación del arreglo por ámbito |

`[MEDIDO]` **Verificado que existen en el remoto**, no en local, con
`git cat-file -e origin/…:<ruta>`:

```
✔ validacion_llm/scripts/atribucion_numerica.py
✔ validacion_llm/scripts/revision_ciega.py
✔ validacion_llm/scripts/verificar_sellos.sh
✔ informes_modelo/SELLOS_REGISTRO.md
✔ informes_modelo/REVISION_CIEGA_PREREGISTRO.md
```

---

## 2. Sellos

`[MEDIDO]` `./validacion_llm/scripts/verificar_sellos.sh` → **código de salida 0**.

```
✔ ABLACION_PREREGISTRO.md
✔ BLOQUE_G_REGLA_DE_DECISION.md          ✔ FIRMA_VETERINARIA_G1.md
✔ BLOQUE_H_REGLA_DE_DECISION.md
✔ BLOQUE_I_REGLA_DE_DECISION.md          ✔ FIRMA_VETERINARIA_I1.md
✔ PUERTAS_v2_PREREGISTRO.md              ~ evaluar_puertas.py   (fallo ESPERADO)
✔ PUERTAS_v3_PREREGISTRO.md              ✔ evaluar_puertas.py
✔ REVISION_CIEGA_PREREGISTRO.md
```

El fallo marcado `~` es el del pre-registro v2 sobre `evaluar_puertas.py`, que
**§0.4 del pre-registro v3 exige que falle** porque el instrumento se extendió de
19 a 42 autocomprobaciones. Está en la lista de excepciones del verificador con su
razón. **Que dejara de fallar sería la señal mala.**

---

## 3. Suite y árbol

```
1377 passed, 1 skipped, 1 warning in 20.84s      exit 0
git status --porcelain                            0 ficheros
```

---

## 4. El estado medido que esta fase hereda

| | |
|---|---|
| Release desplegada | `99c12ff1`, leída **en la VM** |
| Campaña v3 | n = 400 · S **PASA** · D **PASA** · **C RECHAZA 96/400 = 24,00 %** · R no pasa |
| `provider_calls == 1` | **76,05 %** (308 de 405) |
| p95 de latencia | **24,31 s** — ya rozando el criterio de 25 s |
| `requested_parameter_absent` | **0 de 405**: el selector nunca falla |

---

## 5. El presupuesto de esta fase, escrito antes de gastar nada

`[DERIVADO]` De los 96 fallos: **63 atacables por el servidor**, 24 tras la firma
de I.2, 9 de suelo.

```
solo servidor, al 100 %   →  8,25 %   NO PASA   (puerta 3,25 %)
servidor + firma, 100 %   →  2,25 %   PASA
eficacia mínima requerida sobre los 87 removibles: 95,4 %
```

> **Esta fase no hace pasar la Puerta C, y eso está escrito antes de empezar.**
> Su objetivo es eliminar lo eliminable sin permiso de nadie, y dejar el residuo
> en **una** pregunta clínica documentada.
