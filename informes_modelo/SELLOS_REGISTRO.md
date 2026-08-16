# Registro de sellos — qué se volvió a sellar, cuándo y por qué

**Verificador:** `validacion_llm/scripts/verificar_sellos.sh` (usa `sha256sum -c`,
que comprueba **todas** las líneas de cada `.sha256`)

> Un sello roto **no se regenera en silencio**. Se anota aquí con el hash viejo,
> el nuevo, qué cambió y por qué, y **solo entonces** se vuelve a sellar. Si no,
> el sello no vale nada: sería un ritual, no un control.

---

## 0. Un fallo de método propio, del 15-ago-2026

`[MEDIDO]` Durante horas de esta sesión la comprobación de sellos que usé fue:

```bash
esp=$(awk '{print $1}' "$s" | head -1)          # ← solo la PRIMERA línea
act=$(sha256sum "$b" | awk '{print $1}')
```

**Cada `.sha256` sella varios ficheros** —el informe y, según el caso, el script
que lo instrumenta o la petición de firma que lo acompaña—. Mirar solo la primera
línea da un **✔ falso**: dio «los seis sellos válidos» con **dos ya rotos**.

`[DERIVADO]` **La dirección del fallo es la peor**: un verificador que falla en
abierto da tranquilidad sin haber mirado. Es el mismo modo de fallo que
`detect_changes` en este repositorio, y esta vez el afectado era el control de
integridad del propio pre-registro.

**Corregido** con `verificar_sellos.sh`, que usa `sha256sum -c` y devuelve código
de salida 1 ante cualquier fallo no documentado.

---

## 1. Fallo ESPERADO y permanente

| sello | fichero | estado |
|---|---|---|
| `PUERTAS_v2_PREREGISTRO.sha256` | `validacion_llm/scripts/evaluar_puertas.py` | **FAILED, a propósito** |

`[MEDIDO]` El pre-registro v2 selló el script en su versión de entonces. El script
se extendió para el plan v3 —de 19 a 42 autocomprobaciones—, y **§0.4 de
`PUERTAS_v3_PREREGISTRO.md` dice explícitamente que esa línea debe fallar**. El
mismo script está sellado y **correcto** bajo `PUERTAS_v3_PREREGISTRO.sha256`.

> **Que este fallo desapareciera sería la señal mala**, no al revés: querría decir
> que alguien revirtió el instrumento a la versión v2 o regeneró el sello v2.

`verificar_sellos.sh` lo lleva en su lista de excepciones, con esta razón.

---

## 2. Re-sellado #1 · `FIRMA_VETERINARIA_G1.md`

**Fecha:** 2026-08-15 · **Commit que lo cambió:** `060cb627`

```
antes   569dbb197e0d1ee76f723dd9bb7154958162fbea1f725f28b738d719b7af9732
después 5683306c2f509dcdcada6e11e8148b79cb3931d59884e931fb12c071b2f4fa0f
```

**Qué cambió:** se añadieron **§2 bis** (anexo con los datos de la campaña v3 y la
prevalencia medida en 2429 hemogramas) y la pregunta **P4** (sobre el rango
`60–80 %` del porcentaje de neutrófilos).

**Por qué es legítimo:** es una **petición de firma**, no una regla de decisión. Su
función es que un clínico pueda responder con información; añadirle mediciones la
mejora. Las dos adiciones van **fechadas y marcadas como anexo**, así que se ve
qué había antes de medir y qué se añadió después.

**Lo que NO cambió:** `BLOQUE_G_REGLA_DE_DECISION.md` — la regla — sigue **byte a
byte idéntica** y su línea del sello nunca falló.

---

## 3. Re-sellado #2 · `FIRMA_VETERINARIA_I1.md`

**Fecha:** 2026-08-15 · **Commit que lo cambió:** `d85f3bd3`

```
antes   845b86359e1d8c329e872b7d0b4d08d240ea37b1d6cc156c21c423b6f32a0df0
después 8bcf9bbc301f0138af1e5c26e6ee1c753345d620008c5003a7fa6b3965f3bd05
```

**Qué cambió:** **§2 bis** (anexo con el desglose `hierro` 15 / `plasma` 8 /
`corticoides` 1, los 11 usos anatómicos de «plasma» y el caso de la frase que
prohíbe tratar) y una **corrección del §4**: la propuesta original —exigir que
sustantivo y verbo estuvieran en la misma frase— **se midió y no servía**, y se
sustituyó por la restricción de colocación.

**Por qué es legítimo, y por qué era necesario:** el §4 prometía al clínico una
corrección concreta a cambio de su firma. **Esa corrección resultó no tener
efecto medible.** Dejarla escrita habría sido pedir una firma para un cambio que
no hace nada. Corregirla es obligatorio, no opcional.

**Lo que NO cambió:** `BLOQUE_I_REGLA_DE_DECISION.md` — la regla sellada, cuya
premisa quedó refutada— sigue **byte a byte idéntica**. La refutación vive en
`BLOQUE_I_AMBITO_DEL_VALIDADOR.md`, **fuera** del documento sellado. Reescribir
una regla después de medir es exactamente lo que el sello impide, y no se hizo.

---

## 3 bis. Re-sellado #3 · `FIRMA_VETERINARIA_I1.md` — la demostración de autorrechazo

**Fecha:** 2026-08-15 (fase M) · **Bloque:** M.4

```
antes   8bcf9bbc301f0138af1e5c26e6ee1c753345d620008c5003a7fa6b3965f3bd05
después ce18f420a87a1bcd532e71565a11c48dc2f50a02f3c327fab7bfdccc781a617e
```

**Qué cambió:** se añadió **§2 ter**, con las cuatro plantillas etiológicas que
escribimos nosotros y que el validador rechaza las cuatro, más el brazo de
contraste de tres recomendaciones reales que rechaza correctamente.

**Por qué:** hasta ahora la petición decía «creemos que hay falsos positivos»
sobre texto **que no se persiste**. Ahora aporta texto **propio, curado y
verificable**, y demuestra que el predicado **no está roto** —atrapa las tres
recomendaciones reales— sino que **sub-especifica**. Es el argumento más fuerte
construible sin pedirle nada al veterinario.

**Lo que NO cambió:** `BLOQUE_I_REGLA_DE_DECISION.md` sigue **byte a byte
idéntica**, y su línea del sello nunca ha fallado.

---

## 3 ter. Re-sellado #4 · `slot_rendering.py` — M.3 extiende el módulo de M.2

**Fecha:** 2026-08-15 (fase M) · **Bloque:** M.3

```
antes   24d5dac3be831cb209da2fd9fb00ffe633787f70fa00aa425b11e66ec0bc1513
después 9cc8e3c6737d682f74e0d42c7e7e56b6a54afb1aea4f7ad0a2ee60e9fa5e9224
```

**Qué cambió:** se añadió `sanear_prosa()` —el saneado del borrador propio que
autoriza el Anexo A §5— y el guardián `_SOLO_MARCADOR`.

**Por qué es legítimo, y por qué no es lo mismo que reescribir una regla:** M.2 y
M.3 son **dos bloques distintos que comparten módulo**, y **ninguno de los dos se
ha medido todavía**. Un sello impide cambiar la regla *después* de ver el
resultado; aquí no hay resultado que ver. Las **reglas de decisión** de M.2 y M.3
siguen intactas, y la de M.3 se sella en este mismo commit, también antes de medir.

`[DERIVADO]` **Lección de diseño:** poner un `.sha256` sobre un módulo que otro
bloque va a extender genera esta fricción. A partir de aquí, un sello por bloque
cubre **su documento** y solo el código que ese bloque congela.

**Lo que NO cambió:** `BLOQUE_M2_REGLA_DE_DECISION.md` sigue **byte a byte
idéntico**.

---

## 3 quater. Sello nuevo · `PUNTO_DE_PARTIDA_N.md` — las dos frases del piloto

**Fecha:** 2026-08-15 (fase N) · **Bloque:** N.0 · **No es un re-sellado: es nuevo.**

Contiene las **dos frases que dejan de valer en cuanto se enciende la máquina**:

1. **El piloto es interno** — sus 45 turnos entran en el análisis final, con la
   excepción declarada de que se descartan si el stack se rehace.
2. **El semáforo verde/ámbar/rojo**, con el **rojo intacto en >5/45**.

`[DERIVADO]` Van selladas porque decidir cualquiera de las dos **después** de ver
el resultado es exactamente lo que CONSORT 6c prohíbe. Que existan a priori pone
este piloto en el quintil superior de la práctica publicada: solo **45 de 227
protocolos piloto (19,8 %)** reportan criterios de progresión explícitos.

---

## 3 quinquies. Dos sellos nuevos de la fase P

**Fecha:** 2026-08-15/16 · **Bloques:** P.1 y P.2

### `TAXONOMIA_DE_EVASION.md` — sellada ANTES de generar una frase

`[DERIVADO]` El orden **es** el método aquí. Una taxonomía escrita después de ver
las frases describe las frases que se encontraron; escrita antes, define qué se
busca y hace medible la cobertura. El sello es la prueba del orden, y por eso el
documento dice explícitamente que **no se había generado ninguna frase nueva**
cuando se selló.

Lleva su **regla de parada** —(a) ninguna rama nueva, (b) ninguna hoja que dividir
o fusionar, (c) toda instancia a exactamente una hoja— y el **n = 100 declarado
antes** de construir el banco.

### El flag al manifiesto — no es un sello, es un cambio de contrato

`ApplicationRelease.chat_server_writes`, aditivo y con valor por defecto. El
contrato sigue en `hemovet.release/v1` **a propósito**: subir a v2 invalidaría el
`Literal` de todos los manifiestos ya emitidos, incluidos los de rollback.

`[MEDIDO]` El esquema publicado en `deploy/releases/` se regeneró **en el mismo
commit**, porque `test_generated_json_schema_is_closed_and_versioned` lo exige — y
ese test es la especificación de que un cambio de contrato no puede entrar sin
actualizar su artefacto público.

---

## 3 sexies. Re-sellado #5 · `ENMIENDA_ESPECIFICACION_I2.md` → v2

**Fecha:** 2026-08-16 (fase P) · **Bloque:** P.5

```
antes   e3888d84972ec727ddacfbc262b1240031a6bd99b425870a9b15dfec294170e4
después 9899c8578fa5bb64254ef8dc4f387507a441a49b32efb223952536510ad6e446
```

**Qué cambió:** el §5 (análisis de impacto) se reescribió entero con el banco de
100, y el §7 pasó de «cuatro huecos» a «siete familias». Cabecera a **v2**.

**Por qué es legítimo:** es una **petición de firma**, no una regla de decisión.
Su función es que dos clínicos puedan decidir con información, y la v1 presentaba
«5 de 12» como si fuera una tasa cuando su intervalo iba del 14 % al 61 %.
**Dejarla así habría sido pedir una firma sobre una cifra que no se sostiene.**

`[DERIVADO]` **Y esto lo pilló el propio control, no yo.** El sello de
`ESTUDIO_DE_LECTORES.sha256` cubre también la enmienda —se sellaron juntas—, así
que `verificar_sellos.sh` salió con código 1 al terminar la fase. Es la tercera
vez que el verificador señala un cambio que yo no había registrado, y las tres
veces tenía razón.

**Lo que NO cambió:** `ESTUDIO_DE_LECTORES.md` sigue **byte a byte idéntico**.

---

## 4. La distinción que gobierna todo esto

| tipo de documento | ¿se puede cambiar tras medir? |
|---|---|
| **Regla de decisión / pre-registro** | **NO.** Ni una coma. Si la premisa se refuta, se publica la refutación **aparte** y la regla se queda como testimonio de lo que se creía antes |
| **Petición de firma clínica** | **Sí**, con anexo fechado y entrada en este registro. Es un documento vivo dirigido a una persona |
| **Instrumento (script) sellado** | Solo con un pre-registro nuevo que lo selle, como hizo v3 con `evaluar_puertas.py` |

---

## 5. Estado tras el re-sellado

```
✔ ABLACION_PREREGISTRO.md
✔ BLOQUE_G_REGLA_DE_DECISION.md          ✔ FIRMA_VETERINARIA_G1.md      (re-sellado #1)
✔ BLOQUE_H_REGLA_DE_DECISION.md
✔ BLOQUE_I_REGLA_DE_DECISION.md          ✔ FIRMA_VETERINARIA_I1.md      (re-sellado #2)
✔ PUERTAS_v2_PREREGISTRO.md              ~ evaluar_puertas.py           (fallo esperado, §1)
✔ PUERTAS_v3_PREREGISTRO.md              ✔ evaluar_puertas.py
✔ REVISION_CIEGA_PREREGISTRO.md
```
