# Punto de partida P — y el balance de la fase

**Fecha:** 2026-08-15/16 · **GPU: cero** · **VMs:** las tres `TERMINATED`

---

## 1. El preflight, ejecutado antes de tocar nada

```
sellos       → exit 0        (verificar_sellos.sh, todas las líneas)
árbol        → 0 ficheros sin commitear
rama         → bloque-i-acepcion-colocacion @ 3e5ae759, idéntica al remoto
tests        → 1411 passed, 1 skipped
VMs          → las tres TERMINATED en project-5b36701c-f44f-4c03-a12
```

---

## 2. Lo entregado, y ninguno dependió de nadie

| # | entregable | estado |
|--:|---|---|
| 1 | este documento | **✔** |
| 2 | **el flag en el manifiesto**, con su análisis de impacto en el commit | **✔** |
| 3 | `TAXONOMIA_DE_EVASION.md`, sellada **antes** del banco | **✔** |
| 4 | `BANCO_DE_FRONTERA.md` + su script, n=100 con Wilson y Clopper-Pearson por hoja | **✔** |
| 5 | `AUDITORIA_DE_FRONTERA.md`, los tres registros separados | **✔** |
| 6 | `LIMITACIONES.md` §2.1ter reescrito | **✔** |
| 7 | `ENMIENDA_ESPECIFICACION_I2.md` **v2**, doble dirección | **✔** |
| 8-11 | piloto · campaña · ledger · `VENTANAS_MAQUINA.csv` | **✘** requieren desplegar el flag |
| 12 | `ESTADO_` | **✔** |

`[MEDIDO]` **1415 tests** (+4), sellos **exit 0**, **30 commits** en remoto.

---

## 3. El flag, resuelto por donde correspondía

`[MEDIDO]` El intento de la fase N inyectaba la clave **solo** en
`prepare_release.py`, sin llevarla al manifiesto: el renderizador de la VM no
podía reconstruir el mismo texto y el `sha256` dejaba de cuadrar. **16 tests en
rojo.**

> **El control no estaba de más: señalaba que faltaba la fuente de verdad.**

Ahora `ApplicationRelease.chat_server_writes` **es** esa fuente. Los dos
renderizadores leen de ella, el digest cuadra, y hay un test parametrizado que lo
comprueba **en las dos posiciones**.

`[MEDIDO]` **De los 16 quedó uno**, y era el correcto:
`test_generated_json_schema_is_closed_and_versioned` exige que el esquema
publicado se regenere en el **mismo commit**. Ese test es la especificación de que
un cambio de contrato no entra sin actualizar su artefacto público.

**El argumento del cambio no es de comodidad:** un booleano que decide si el
servidor escribe cifras de la historia clínica **no es un secreto**. No es una
credencial, no se rota, su divulgación no compromete nada, y su valor **debe ser
legible para un auditor**. Guardarlo como secreto es un **error de categoría**.

`[DERIVADO]` **Y la justificación se presenta como composición, no como cita.** No
existe ningún documento que diga, con esas palabras, «configuración versionada
mejor que secretos opacos en contexto regulado». El argumento se compone de
Anexo 11 cl.10, 21 CFR 11.10(e)/(k)(2), MHRA ALCOA §6.1 y §6.11.2, NIST SP
800-128, SSDF PS.2.1/PW.9.2 y Hodgson sobre *release toggles*.

---

## 4. Lo que el banco cambió

`[MEDIDO]` **75/100 desacuerdos**, Wilson **[65,7 % , 82,5 %]** · **74 falsos
negativos, 1 falso positivo**.

Las tres hipótesis pre-registradas —E5, E6, E7— **quedan confirmadas**, y **E6 al
100 %**. El control negativo E8 sale **limpio**, lo que descarta la lectura fácil
de «el validador rechaza todo» — con su techo declarado de 25,9 %, porque n = 10.

**Y las dos propiedades que un banco de solo MFT no habría visto:**

1. `[MEDIDO]` **La paráfrasis cambia el veredicto** en tres de las cinco hojas con
   variantes INV. La regla depende de la **superficie**.
2. `[MEDIDO]` **De cuatro pares dirigidos, tres son ciegos y uno está
   INVERTIDO.** `D1` rechaza el genérico legítimo y acepta el anclado al paciente.

> `[DERIVADO]` **El falso positivo de la etiología y los falsos negativos de la
> directiva son la misma inversión**, vista desde sus dos extremos. La regla no
> está mal calibrada sobre el eje correcto: **está orientada al eje equivocado**.

---

## 5. Lo que se corrigió de la fase anterior

`[MEDIDO]` El informe de la fase N presentaba **«5 desacuerdos de 12»** como una
medida. Su intervalo va del **14 % al 61 %**, y con 12 ítems **ni siquiera 0
fallos sostendría nada** (techo exacto 22,1 %).

**Aquello demostraba existencia. Esto caracteriza el instrumento.** Las dos cosas
son resultados; solo la segunda lleva intervalo. Corregido en `LIMITACIONES` §2.1
ter, en la enmienda v2 y en `AUDITORIA_DE_FRONTERA.md` §5.

---

## 6. Dos defectos de método propios, de esta fase

`[MEDIDO]` **§11 de `DEFECTOS_DE_METODO_PROPIOS.md`:** mi comprobador de pares
dirigidos marcaba **«SENSIBLE»** si las dos etiquetas simplemente **diferían**.
Con eso, `D1` —el peor hallazgo del banco— salía como **acierto**. Van **tres**
comprobaciones en este proyecto que fallan en abierto —`detect_changes`, los
sellos por la primera línea, y ésta—, y las tres dan por bueno lo que no han
mirado.

`[MEDIDO]` **Re-sellado #5:** al terminar la fase, `verificar_sellos.sh` salió con
código **1**. El sello de `ESTUDIO_DE_LECTORES.sha256` cubre también la enmienda
—se sellaron juntas— y yo la había reescrito sin registrarlo. **Es la tercera vez
que el verificador señala un cambio que no había anotado, y las tres tenía razón.**

---

## 7. Lo que falta, y de quién depende

| falta | depende de |
|---|---|
| desplegar el flag y **leer su valor en la VM** | una ejecución del workflow con el input activado |
| piloto, campaña y los cuatro del ledger | lo anterior |
| **dos firmas veterinarias** | dos personas. El documento está escrito y es firmable |
| **participantes del estudio de lectores** | personas. El protocolo está sellado y repartible |

> `[DERIVADO]` El flag **ya no es un bloqueo de diseño**: es un despliegue. El plan
> de la ventana está sellado en `VENTANA_2_PLAN.md` y **no se reabre**.
