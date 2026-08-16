# Comparabilidad de las corridas — qué se puede comparar con qué, y por qué

**Fecha:** 2026-08-15 · **Rango clasificado:** `c0b88548..4cca5683` (11 commits)
**Estado de las VMs al escribir:** las tres `TERMINATED`, verificado.

> Existe porque la sesión anterior midió una campaña de 225 turnos contra un
> árbol que **ya no es el de `main`**, y sin esta tabla esa cifra se seguiría
> citando como si fuese la línea base del código actual. No lo es.

Toda cifra va marcada `[MEDIDO]`, `[DERIVADO]` o `[INFERIDO]`.

---

## 0. La corrección que abre este documento: producción NO está desalineada

El prompt maestro §4.1 y el GOAL I-8 parten de que `main 4cca5683` y producción
`8e8fa19e` son árboles distintos, y ordenan alinear producción como **primer acto
de la primera ventana de máquinas**. `[MEDIDO]` **Eso ya no es cierto**, y hay
tres pruebas independientes:

| Prueba | Dónde | Qué dice |
|---|---|---|
| Jobs del run `31768073341` | `gh run view --json jobs` | `Build`, `Deploy production through IAP` y `Production smoke tests` los tres en **`success`**, ninguno `skipped` |
| Log del propio job de despliegue | `Deploy production through IAP` | `deployment=success release=4cca5683b1276adbb726820c2c8af897aa76dff9`, con `backend-1` y `frontend-1` recreados desde digests nuevos y `Healthy` |
| Journal **de la VM** | `informes_modelo/diagnostico_gpu_2026-08-14/gpu_hemovet-llm-gpu-a100.log` | `runtime=valid release=4cca5683b1276adbb726820c2c8af897aa76dff9 … hemovet_gpu_startup=ready` |

La tercera es la que vale, porque es la única leída **en la máquina** y no en
GitHub — que es exactamente lo que `TRAMPA_COMMIT_VACIO.md` §«La regla que queda»
exige.

`[DERIVADO]` **Por qué la sesión anterior creyó lo contrario:** predijo que el
despliegue del revert fallaría en IAP «porque las VMs están apagadas» y **cerró
sin comprobarlo**. `[MEDIDO]` El registro de operaciones de GCP muestra
`start hemovet-prod` a las `2026-08-14T04:53:42Z`, un minuto antes de que
arrancase el job de despliegue (`04:54:43Z`). La máquina estaba encendida cuando
el deploy la necesitó.

> **Defecto de método heredado, y es nuevo:** *predecir* el resultado de un
> despliegue y anotar la predicción como si fuera una medición. La regla del
> proyecto —«verifica los jobs uno a uno»— existía y no se aplicó, porque el
> autor ya «sabía» lo que iba a pasar. Una predicción no lleva marca `[MEDIDO]`.

**Consecuencia operativa:** el bloque E.3 no consume ventana de máquinas. Queda
como **confirmación** —leer el SHA en `hemovet-prod` la próxima vez que esté
encendida por otro motivo—, no como acción de alineación.

---

## 1. Clasificación de los 11 commits

Las categorías son las que decide la comparabilidad: solo lo que **cambia el
comportamiento de generación o de validación** rompe la comparación entre dos
corridas.

| Commit | Asunto | Categoría | ¿Rompe comparabilidad? |
|---|---|---|:--:|
| `855566ff` | el error terminal dice qué comprobación lo rechazó | **instrumentación** (contrato de error) | no |
| `100849a7` | pre-registro sellado de las puertas S/C/R/D | **docs + aparato de medida** | no |
| `d9629bcf` | arnés sin sondeo durante el arranque y sin reintentos | **aparato de medida** (cliente) | **sí, del lado del arnés** |
| `43b9c528` | protocolo A/B/C de caché | **aparato de medida** | no |
| `2e9a0296` | merge Puertas v2 | merge de los cuatro anteriores | no |
| `ccb05746` | bloques A, B y C cerrados | **docs + resultados** | no |
| `5f637000` | desambigua absoluto/porcentaje ANTES de generar | **PROMPT** (instrucción derivada de datos) | **SÍ** |
| `af4ddb41` | regla de decisión de la campaña pass^5 | **docs** | no |
| `8e8fa19e` | merge Bloque D | **PROMPT** | **SÍ** |
| `bd0da4e1` | Revert del merge Bloque D | **PROMPT** (deshace) | **SÍ** |
| `4cca5683` | campaña pass^5 de 225 turnos | **docs + resultados** | no |

`[MEDIDO]` Verificación mecánica de la clasificación, por igualdad de árbol en
`backend/` (`git diff --name-only … -- backend/`):

```
backend/ de 2e9a0296  ==  backend/ de 4cca5683      0 ficheros distintos
backend/ de ccb05746  ==  backend/ de 4cca5683      0 ficheros distintos
backend/ de bd0da4e1  ==  backend/ de 4cca5683      0 ficheros distintos
backend/ de 8e8fa19e  !=  backend/ de 4cca5683      3 ficheros distintos
backend/ de c0b88548  !=  backend/ de 4cca5683      3 ficheros distintos
```

**Solo hay dos árboles de backend en todo el rango**, y el Bloque D es la única
frontera:

```
ÁRBOL A  (sin Bloque D)   c0b88548 … 5f637000⁻ ,  bd0da4e1 , 4cca5683   ← EL DESPLEGADO HOY
ÁRBOL B  (con Bloque D)   5f637000 , 8e8fa19e
```

> Matiz: `c0b88548` está en el árbol A por lo que toca el Bloque D, pero **le
> falta** `855566ff` (el motivo del error terminal). Es instrumentación del sobre
> de error, no del generador: no cambia lo que el modelo escribe, cambia lo que
> el arnés puede *ver*. Por eso no rompe la comparabilidad de la validez, pero sí
> la del **desglose por clase**: antes de `855566ff` los fallos terminales
> llegaban sin nombre.

---

## 2. Qué corrida mide qué árbol — y la consecuencia incómoda

| Corrida | n | Release medida | Árbol | Instrumentación del motivo |
|---|--:|---|:--:|:--:|
| `puerta3j_2026-08-13` | 45 | `b83cb379` | pre-A | parcial |
| `puerta3k_2026-08-13` | 45 | `6547cdb8` + prompt | otro | parcial |
| `diag_general_2026-08-13` | 15 | `b83cb379` | pre-A | parcial |
| **`diag_terminal_2026-08-14`** | **45** | **`2e9a0296`** | **A** | **completa** |
| **`campana_r_2026-08-14`** | **225** | **`8e8fa19e`** | **B** | **completa** |

`[DERIVADO]` **La consecuencia que hay que tener delante todo el tiempo:**

> **La campaña de 225 turnos —la única con el plan de muestreo completo, y la que
> produce el 78,67 % y los 48 fallos— midió el árbol B, que NO es el desplegado.**
> El único dato del árbol A con instrumentación completa es
> `diag_terminal_2026-08-14`, y son **n = 45**.

No es un desastre: el Bloque D quedó refutado precisamente porque **no cambiaba
nada** —los intervalos de Wilson se solapaban por completo—, así que tratar las
dos corridas como comparables está justificado *por la medición misma*, no por
conveniencia. Pero es una decisión que se declara, no que se asume:

| | árbol A (n=45) | árbol B (n=225) |
|---|---|---|
| fallos de contrato | 14 = 31,11 % · Wilson [19,53 · 45,67] | 48 = 21,33 % · Wilson [16,49 · 27,14] |
| `ambiguous_parameter_claim` | 4 = 8,89 % · Wilson [3,51 · 20,73] | 14 = 6,22 % · Wilson [3,74 · 10,17] |

`[DERIVADO]` Los intervalos se solapan en las dos filas. **Se declara que A y B
son intercambiables a efectos de línea base**, y se declara también que esa
afirmación descansa en un n=45 de un lado. La campaña v3 medirá el árbol A con
n=400 y cerrará el hueco.

---

## 3. Un tercer conjunto de datos que nadie había contado: producción real

`[MEDIDO]` `informes_modelo/diagnostico_gpu_2026-08-14/prod_backend.log` contiene
el log del backend corriendo **el árbol A** (release `4cca5683`) con tráfico real,
no de batería. Recuento propio sobre el fichero:

```
97 ChatRuntimeUnavailable  ==  97 códigos invalid_output_*

invalid_output_ambiguous_parameter_claim            57   58,8 %
invalid_output_indirect_treatment_recommendation    17   17,5 %
invalid_output_missing_evidence_attribution         13   13,4 %
invalid_output_unsupported_status_claim              5    5,2 %
invalid_output_unsupported_numeric_claim             4    4,1 %
invalid_output_intent_mismatch_capabilities          1    1,0 %
```

`[DERIVADO]` Tres cosas que aporta y que la batería no puede dar:

1. **Es el árbol desplegado**, no el B. Confirma el reparto de clases sin el
   Bloque D de por medio.
2. **Es tráfico real**, con preguntas que nadie escribió para una batería.
3. `[DERIVADO]` **Es el denominador de los fallos TERMINALES**, no el de los
   fallos de primera generación: cuentan solo los turnos donde falló la
   generación **y** la reparación. Por eso `ambiguous_parameter_claim` pesa aquí
   el 58,8 % y en la campaña el 29,2 % de los fallos de contrato: **es la clase
   que la reparación casi nunca arregla.** Ver §4.

> **Limitación declarada:** no se conoce el denominador. El log no permite contar
> los turnos que sí respondieron, así que estas 97 dan un **reparto**, nunca una
> tasa. No entran en ninguna puerta. El README de esa carpeta cuenta 93; mi
> recuento sobre el mismo fichero da 97 y añade
> `intent_mismatch_capabilities`, que allí no figura.

**Reproducibilidad, con su pega.** `.gitignore` excluye `*.log`, así que los
ficheros crudos **no están versionados** y se quedan en local. La orden que
produce el recuento, para quien los tenga:

```bash
grep -oE 'invalid_output_[a-z_]+' informes_modelo/diagnostico_gpu_2026-08-14/prod_backend.log \
  | sort | uniq -c | sort -rn
```

`[MEDIDO]` Comprobación cruzada que sí se puede hacer sin el fichero: el número
de `ChatRuntimeUnavailable` y el de códigos `invalid_output_*` coinciden
exactamente (97 = 97), así que ningún fallo terminal quedó sin clasificar.

---

## 4. Lo que el cruce clase × desenlace hace visible

`[MEDIDO]` Sobre los 48 fallos de contrato de `campana_r_2026-08-14`:

| Clase | REPARADO | TERMINAL | total | % que la reparación salva |
|---|--:|--:|--:|--:|
| `ambiguous_parameter_claim` | 2 | **12** | 14 | **14,3 %** |
| `indirect_treatment_recommendation` | 9 | 3 | 12 | 75,0 % |
| `unsupported_status_claim` | 5 | 2 | 7 | 71,4 % |
| `missing_evidence_attribution` | 1 | **5** | 6 | **16,7 %** |
| `unsupported_numeric_claim` | 1 | **5** | 6 | **16,7 %** |
| `definitive_diagnosis` | 3 | 0 | 3 | 100,0 % |
| **TOTAL** | **21** | **27** | **48** | 43,8 % |

`[DERIVADO]` **La reparación no es una red uniforme: es buena en lo clínico y
mala en lo numérico.** Salva el 75-100 % de las capturas clínicas (donde basta
reescribir la frase) y el 14-17 % de la atribución de parámetros (donde haría
falta un dato que el modelo no tiene). Eso explica por qué el reparto de clases
del log de producción —que solo ve terminales— está tan escorado a
`ambiguous_parameter_claim`.

**Consecuencia para el Bloque J:** retirar la reparación no cuesta lo mismo en
todas las clases. `[DERIVADO]` Si se retirase hoy sin ningún otro cambio, sobre
los mismos 225 turnos:

| | con reparación | sin reparación |
|---|---|---|
| **Puerta C** validez 1.ª pasada | 177/225 = 78,67 % | 177/225 = **78,67 %** — sin cambio |
| **Puerta D** indisponibilidad | 0/225 | 0/225 — **sin cambio** |
| turnos **sin respuesta publicada** | 27/225 = 12,00 % | 48/225 = **21,33 %** |
| **Puerta S** afirmación | ≥ 98,4984 % (0 en 198) | ≥ **98,3217 %** (0 en 177) |

> **C no se mueve** porque ya cuenta `RESPONDIDO_REPARADO` como fallo, y **D
> tampoco**, porque un fallo terminal de contrato no es una indisponibilidad: lo
> dice la taxonomía §1 del pre-registro y clasificar de otro modo sería
> exactamente el error de la sesión que contaba por HTTP.
>
> Lo que sí se paga son dos cosas que ninguna puerta vigila hoy: **uno de cada
> cinco turnos se quedaría sin respuesta** (hoy uno de cada ocho), y la Puerta S
> **pierde 0,18 pts de afirmación** porque su denominador es lo publicado y
> encogería de 198 a 177. Es un intercambio que se declara antes de hacerlo.

---

## 5. Reglas de comparabilidad que se aplican a partir de ahora

1. **Ninguna cifra de validez se compara entre árboles A y B sin decirlo.**
2. **Una corrida anterior a `855566ff` no aporta desglose por clase**, solo
   agregados: sus fallos terminales no llevan motivo.
3. **Una corrida anterior a `d9629bcf` no aporta Puerta D**: el arnés reintentaba
   hasta tres veces y borraba de los datos la no-respuesta que D cuenta.
4. **El árbol se verifica en la VM**, no en GitHub, y la verificación se anota con
   su fuente. Una predicción sobre un despliegue no es una verificación.
5. **Un run verde no es un despliegue.** Los tres jobs, uno a uno. Y si dicen
   `success`, tampoco se supone lo contrario: se lee el log.

---

## Hipótesis vivas que abre este documento

1. **Quién encendió `hemovet-prod` a las 04:53:42Z del 14-ago.** El workflow no
   lo hace (`deploy.yml` no tiene `instances start` para producción). Sin
   explicar, y conviene saberlo porque es coste que corre solo.
2. **Si el árbol A y el B son de verdad intercambiables** más allá del solape de
   intervalos con n=45 de un lado. La campaña v3 lo resuelve por construcción.
3. **Por qué `intent_mismatch_capabilities` aparece en producción real y nunca en
   la batería.** Una clase que el corpus no ejercita.
