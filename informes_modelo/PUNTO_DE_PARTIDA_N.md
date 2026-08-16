# Punto de partida N — preflight en frío y las dos frases selladas antes de encender

**Fecha:** 2026-08-15 · **GPU: cero** · **VMs:** las tres `TERMINATED`, verificado en
`project-5b36701c-f44f-4c03-a12`
**Se sella con** `PUNTO_DE_PARTIDA_N.sha256`

> GOAL, N.0: *«sella dos frases antes de encender, porque después ya no valen»*.

---

## 1. El preflight, ejecutado

```
sellos       → exit 0        (verificar_sellos.sh, todas las líneas)
árbol        → 0 ficheros sin commitear
rama         → bloque-i-acepcion-colocacion @ 554c850d
publicada    → SÍ, idéntica al remoto
tests        → 1411 passed, 1 skipped
SONDEOS      → SONDEOS="${SONDEOS:-1}"        ← comprobado, no asumido
VMs          → hemovet-llm-gpu-a100 TERMINATED
                hemovet-rescate      TERMINATED
                hemovet-prod         TERMINATED
```

Todo lo que se mida después se compara contra esto.

---

## 2. FRASE SELLADA #1 — el piloto es **interno**

> **El piloto es interno: sus 45 turnos entran en el análisis final.** El criterio
> de progresión se evalúa sobre una **métrica de proceso** —validez de esquema—
> **ortogonal a los desenlaces clínicos primarios**, y **no se realiza ninguna
> prueba de hipótesis sobre desenlaces clínicos en el piloto**.
>
> **Excepción, declarada ahora:** si el piloto falla y se rehace el stack, esos 45
> turnos **se descartan** —la configuración cambió— y el descarte se reporta
> (CONSORT ítem 3b; DECIDE-AI ítem 11, *«the timing of these modifications»*).

`[DERIVADO]` Piloto externo e interno son ambos legítimos. **Lo ilegítimo es
decidirlo después de ver el resultado**, y por eso está aquí y no en el informe
del piloto.

---

## 3. FRASE SELLADA #2 — el semáforo, con el rojo intacto

```
VERDE   0/45              → lanzar la campaña
ÁMBAR   1-5 fallos        → NO lanzar todavía. Inspección individual de cada log,
                            clasificación por los tres discriminadores, y
                            verificación del stderr. Sólo entonces decidir.
ROJO    >5/45             → apagar las tres máquinas y escribir el diagnóstico.
```

**El rojo no se toca.** Un umbral de `>2/45` sería estadísticamente más
convencional, y **aun así no se cambia**: mover un criterio de progresión ya
escrito es lo que la extensión CONSORT para pilotos (ítem 6c, *«prespecified
criteria used to judge whether, or how, to proceed»*) prohíbe, y la guía de la FDA
sobre diseños adaptativos advierte de que las adaptaciones no planificadas dejan
sin métodos estadísticos apropiados una vez recogidos los datos.

Lo que sí se hace, porque es exactamente lo que esa guía pide, es **convertir el
binario en semáforo** (Avery et al., BMJ Open 2017; MRC Methodology Hubs:
*«Green (go), amber (amend) and red (stop) rather than a stop/go approach»*).

### 3.1 Qué detecta esta regla, y qué no

`[DERIVADO]` Probabilidad de abortar (`X > 5`, `n = 45`) según la tasa real:

| p real | P(abortar) |
|--:|--:|
| 1 % | 0,0 % |
| 2 % | 0,0 % |
| 5 % | 2,4 % |
| 10 % | 29,2 % |
| 50 % | 100 % |

**Dos lecturas, y las dos hay que escribirlas:**

- **No va a costar la campaña por mala suerte.** Con el sistema sano (p ≤ 2 %), la
  probabilidad de abortar por azar es del **0,03 %**.
- **Tolera pasar con un 10 % de fallo** —sólo aborta el 29 % de las veces—, que
  serían **120 respuestas inutilizables en 1200 turnos**. `n = 45` **no puede
  distinguir 1 % de 5 %**: observar 0/45 deja el IC95 % de Wilson en **[0 %, 7,9 %]**.

> **Lo que la regla sí hace, y casi perfecto:** detectar que **la restricción no se
> está aplicando en absoluto** (p ≈ 0,5-1,0 → aborta con probabilidad ≈ 1). Está
> calibrada contra los modos de fallo (a) y (b) del §4. **Ese es su valor, y es
> alto.**

---

## 4. Los tres discriminadores — instrumentados ANTES de contar un fallo

`[DERIVADO]` Sin esto, «5 de 45» es un número sin diagnóstico:

```
finish_reason == "length"              → TRUNCAMIENTO. Sube num_predict o acorta.
                                         NO es fallo de gramática.
error de parseo de gramática en stderr → el servidor FALLA EN ABIERTO. La
                                         gramática NO está puesta (llama.cpp#19051,
                                         cerrado como «not planned»).
prosa envolvente / campos fuera de
esquema                                → la MÁSCARA NO SE APLICÓ
                                         (ollama#14645 / #15260).
```

**Los tres tienen remedios distintos y sólo uno justifica abortar.** Un piloto que
cuenta fallos sin clasificarlos apaga la máquina por un `num_predict` corto.

`[INFERIDO]` El arreglo de (a) es `ollama/ollama PR #15901`, mergeado el
7-jul-2026, cuatro días antes de v0.32.0; la versión desplegada es 0.32.6
(4-ago). **Por inferencia la corrección está dentro. Por evidencia, no se sabe:**
no se pudo confirmar ninguna línea sobre *structured output* en las notas de la
serie 0.32. **Se verifica con un turno, no con un razonamiento.**

---

## 5. La fracción honesta del piloto

```
45 /  400 = 11,2 %  de UNA corrida            ← el número que suena mal
45 / 1200 =  3,8 %  de la campaña completa
11 /  285 =  3,9 %  del presupuesto de GPU    ← EL ARGUMENTO
```

**Se gasta un 3,9 % del cómputo para proteger el 96,1 % restante.** Es un
argumento de valor esperado, no una regla de tamaño muestral.

---

## 6. El objetivo operativo, escrito ANTES de medir

`[DERIVADO]` La eficacia mínima sobre lo removible es **89,25 %** —y **89,2 % no
basta**: 93 × 0,892 = 82,96, uno menos de los 83 que hay que quitar—. Pero eso es
la **estimación puntual**, y la campaña es **un sorteo binomial de 400 turnos**:

| eficacia verdadera | tasa | **P(la puerta acepte)** |
|--:|--:|--:|
| 96 % | 1,68 % | 99,1 % |
| **92 %** | 2,61 % | **83,3 %** |
| 90 % | 3,08 % | 65,1 % |
| **89,25 %** | 3,25 % | **57,3 %** |
| 88 % | 3,54 % | 44,5 % |

```
P(pasar) = 50 %  →  eficacia ≥ 88,5 %
P(pasar) = 80 %  →  eficacia ≥ 91,6 %
P(pasar) = 95 %  →  eficacia ≥ 94,1 %
```

> **El objetivo operativo es 92 %, no 89,25 %.** Si sale 90 % y la puerta rechaza,
> **no habrá fallado el diseño**: habrá salido el 35 % de las veces que esta tabla
> ya predecía. Declararlo ahora es la diferencia entre un resultado interpretable
> y una discusión sobre la mala suerte.

---

## 7. El bloqueante operativo, dicho una vez

`[MEDIDO]` La condición de medida es `CHAT_SERVER_WRITES_ENABLED=1` y **no puede
salir del repositorio**: el job `deploy_prod` (línea 613 de `deploy.yml`)
re-renderiza el entorno con `render_release_environment.py` desde
`PRODUCTION_ENV_B64` **y el manifiesto**, y aborta si el `sha256` no cuadra.
Inyectarlo por `prepare_release.py` desincroniza los dos renderizados y rompe **16
tests** de la tubería de release; se intentó y se revirtió.

**Eso no es un obstáculo: es el control funcionando.** Detalle y las dos vías
legítimas en `VENTANA_2_PLAN.md` §0.
