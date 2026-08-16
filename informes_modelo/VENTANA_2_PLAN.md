# Ventana 2 — plan sellado, y el bloqueante que impide encenderla hoy

**Fecha:** 2026-08-15 · **GPU usada: cero** · **VMs:** las tres `TERMINATED`
**Se sella con** `VENTANA_2_PLAN.sha256`

> GOAL, M.6: *«Decide y sella el número de factores y de semillas ANTES de
> encender: con una sola semilla el resultado no es interpretable, y eso está
> medido.»*

---

## 0. El bloqueante, primero, porque decide si la ventana se enciende

`[MEDIDO]` La condición de medida es `CHAT_SERVER_WRITES_ENABLED=1`. **No hay
forma de encenderla desde el repositorio**, y no por descuido:

1. El `.env` de producción se compone **entero** desde el secreto de GitHub
   `PRODUCTION_ENV_B64`. `prepare_release.py` solo sustituye cinco claves
   derivadas —imágenes, revisión, URL de Ollama, colección RAG—.
2. **La configuración está ligada por digest.**
   `render_release_environment.py` **re-renderiza el entorno en la VM** desde el
   manifiesto y compara `sha256`; si no cuadra, aborta con
   `release_environment_digest_mismatch`.

`[MEDIDO]` Lo intenté: añadir la clave a `DERIVED_ENVIRONMENT_KEYS` deja el
renderizado del despliegue y el de la VM **desincronizados** y rompe **16 tests**
de la tubería de release. Revertido; el árbol vuelve a 1411 verdes.

> **Eso no es un obstáculo: es el diseño funcionando.** El digest existe para que
> nadie —ni yo— cambie la configuración desplegada por un camino lateral. Meter
> una condición experimental por ahí sería exactamente lo que ese control impide.

### 0.1 Las dos vías legítimas, y las dos son decisión del usuario

| vía | qué exige | riesgo |
|---|---|---|
| **A · añadir `CHAT_SERVER_WRITES_ENABLED=1` a `PRODUCTION_ENV_B64`** | el usuario actualiza el secreto; el despliegue lo propaga solo | bajo. **Recomendada.** Hay que acordarse de volver a `0` al terminar |
| **B · llevar la condición al manifiesto de release** | cambio de esquema en `release_manifest.py` + las dos rutas de renderizado + sus tests | medio-alto: toca la identidad del release. Correcto a largo plazo; no para una ventana |

`[DERIVADO]` **Recomendación:** la **A**, y que el valor quede escrito en este
informe junto al SHA medido, para que la condición sea auditable aunque viva en un
secreto.

---

## 1. El presupuesto, decidido antes de encender

`[MEDIDO]` Coste unitario: **95 min** por campaña de 400 turnos (medido en la
ventana 1, 2 h 16 para 400 turnos más dos experimentos).

| | |
|---|---|
| **Condiciones** | **1** — `TODO-SERVIDOR` (M.2 + M.3 + §3.1, los tres a la vez) |
| **Comparador** | la línea base **ya medida** (96/400 = 24,00 %), **sin gastar GPU nueva** |
| **Semillas** | **3** repeticiones independientes |
| **Coste** | **3 × 95 min = 4 h 45 min** de A100, más ~15 min de arranque y apagado |

`[DERIVADO]` **Por qué una condición y no un factorial:** el GOAL dice *«si no cabe
todo, recorta condiciones, nunca semillas»*. Con la línea base ya medida, la
pregunta primaria —**¿cae `ambiguous_parameter_claim`?**— la responde una celda
contra un comparador que ya existe. El 2³ para atribuir el efecto a cada frente es
la **Fase B** del `ABLACION_PREREGISTRO.md`, y **solo se ejecuta si la Fase A
mueve el número**.

### 1.1 Un piloto de 45 turnos antes de comprometer las 4 h 45

`[DERIVADO]` La primera corrida de 45 turnos (~11 min) responde una pregunta que
puede tirar la ventana entera: **¿emite el modelo JSON de slots válido?** F.1 dice
que `enum` propaga (30/30 dentro), pero eso se midió con un esquema de tres
valores, no con el del turno.

**Regla del piloto, a priori:** si de 45 turnos **más de 5** devuelven texto que no
parsea como JSON, **se apaga todo y no se gastan las 4 h 45**. El fallo se reporta
como lo que es —la premisa mecánica no se sostiene con este esquema— y no se
ajusta sobre la marcha.

---

## 2. La regla de decisión ya está sellada, y no se toca aquí

`BLOQUE_M2_REGLA_DE_DECISION.md` y `BLOQUE_M3_REGLA_DE_DECISION.md`, ambos con
`.sha256`. En resumen:

- `ambiguous_parameter_claim` **< 5 en 400** o **se revierte**;
- primario de M.3: **`mal_atribuida` = 0 y `inventada` = 0** en
  `atribucion_numerica.py`, **no** el contador del validador;
- si una clase cae pero sube otra y el total no mejora, **se revierte**;
- `p50 > 15 s` o `p95 > 25 s`, **se revierte** — `[MEDIDO]` el p95 está en
  **24,31 s**: quedan **0,69 s** de margen;
- si la revisión ciega la califica peor **por daño**, **se revierte**.

---

## 3. El protocolo, literal

```
preflight en frio: verificar_sellos.sh (exit 0) · 1411 tests · arbol limpio
  → push, y ESPERAR a que «Publish deferred GPU release» salga SUCCESS
  → SOLO la GPU · esperar ~6 min SIN SONDEAR NADA
  → verificar `hemovet_gpu_startup=ready` por journal (SSH no ocupa la ranura)
  → SOLO ENTONCES la CPU
  → relanzar el deploy y verificar los jobs UNO A UNO (`skipped` no es despliegue)
  → leer el SHA EN LA VM  ·  y verificar CHAT_SERVER_WRITES_ENABLED=1 EN LA VM
  → piloto de 45 turnos → regla del §1.1
  → 3 × 400 turnos, en SEGUNDO PLANO, sin cortar a mitad
  → apagar las tres y verificar TERMINATED
```

**Dos avisos que la ventana 1 pagó y aquí son gratis:**

- `[MEDIDO]` La espera por defecto del arnés eran **20 min por corrida** —tres
  horas en nueve—. Ya está en `SONDEOS=1`, `PAUSA_SONDA=10`. **Comprobarlo antes
  de encender.**
- `[MEDIDO]` En primer plano la campaña murió a los cinco minutos por el límite de
  la orden. **Segundo plano, siempre.**

Y uno nuevo, de esta fase: **verificar el flag EN LA VM**, no en el workflow. Es
el mismo principio que leer el SHA en la VM y por la misma razón: un run verde no
es un despliegue.

---

## 4. La ortogonalidad sale gratis

`ortogonalidad.py` cruza los cuatro validadores × las condiciones sobre el texto
guardado. **Cero GPU.** `[MEDIDO]` Con n = 400 ya se sabe que **no** es perfecta:
3 de 96 fallos cruzan la frontera de ámbito. Se mide, no se asume.

---

## 5. Qué se publica al terminar

`CAMPANA_M_RESULTADO.md` con los **cuatro denominadores**, Wilson y `pass^6`; la
matriz de ortogonalidad; `ABLACION_A_B_C.md`; `COSTE_DE_QUE_ESCRIBA_EL_SERVIDOR.md`
—sobre-rechazo desde `prosa_oraciones_quitadas`, naturalidad y latencia—;
`ESCALERA_DE_REINTENTOS.md` desde el ledger; y `VENTANAS_MAQUINA.csv` con minutos
e incidencias.

**Y los turnos muertos siguen en el denominador.** Los cuatro, siempre.

---

## 6. Estado

> **La ventana 2 está lista para encenderse y no se enciende hoy.** Falta un dato
> que no está en mi mano: que `CHAT_SERVER_WRITES_ENABLED=1` llegue a la VM. Sin
> él, encender 4 h 45 de A100 mediría **exactamente lo mismo que la campaña v3**,
> que ya está medida y publicada.
