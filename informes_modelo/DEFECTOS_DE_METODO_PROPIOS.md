# Defectos de método propios — sesión del 15-ago-2026

> Las tres sesiones anteriores documentaron los suyos y eso me ahorró medio día:
> la trampa del commit vacío, los apagados de la GPU por sondeo propio, y las dos
> cifras de la curva OC escritas de memoria. Esta es mi parte del trato.
>
> Se listan **todos**, incluidos los que corregí antes de que llegaran a un
> informe. Un defecto cazado a tiempo sigue siendo un defecto: la próxima vez
> puede no cazarse.

---

## 1. Inferí una causa de un campo que se rellena DESPUÉS del efecto

**El más grave, y estuvo a punto de producir un arreglo para un problema
inexistente.**

Buscando la causa de `missing_evidence_attribution` (6 de los 48 fallos) crucé la
clase contra `n_fuentes` y salió una tabla preciosa:

| `n_fuentes` | turnos de `general` | fallos | tasa |
|---|--:|--:|--:|
| 0 | 25 | 5 | **20,0 %** |
| 1 | 26 | 1 | 3,8 % |
| 2 | 24 | 0 | 0,0 % |

La lectura se escribía sola: *«se le está exigiendo al modelo que cite evidencia
que el servidor no recuperó»*. Encajaba con el principio del plan entero —«no
darle la ocasión»—, era determinista y era barata de arreglar. **Es falsa.**

`n_fuentes` es `len(cuerpo["sources"])` de la **respuesta publicada**, y
`_attributed_sources` devuelve lista vacía **exactamente cuando la atribución
falla**. Además, los 8 turnos terminales de `general` no tienen cuerpo, así que
su `n_fuentes` es 0 por construcción. Entre los turnos con respuesta publicada,
`n_fuentes = 0` tiene **cero** fallos de esa clase (0 de 17).

**Qué lo cazó:** preguntar *qué mide el campo* antes de creerme la tabla. Nada
más. La correlación era fuerte, la explicación era elegante y el arreglo era
sencillo — que es justo la combinación que hay que desconfiar.

**Regla que me pongo:** antes de explicar un fallo con una variable, comprobar en
el código **cuándo se rellena esa variable**. Si se rellena después del fallo, no
puede explicarlo.

> Este proyecto ya tenía documentada esta trampa en otra forma: clasificar los
> 502 por código HTTP. Es la misma familia de error y volví a caer en ella.

## 2. Escribí una consecuencia en un informe antes de comprobar la taxonomía

En `COMPARABILIDAD_COMMITS.md` §4 escribí que retirar la reparación haría caer la
Puerta D de 0/225 a 21/225 y la suspendería «con holgura». **Es falso**: un fallo
terminal de contrato **no es** una indisponibilidad — lo dice la taxonomía §1 del
pre-registro, que yo mismo había leído una hora antes.

Lo corregí a los pocos minutos, con la tabla real (C no se mueve, D no se mueve,
lo que sube es «turnos sin respuesta publicada» de 12,00 % a 21,33 % y lo que baja
son 0,18 pts de la Puerta S). Pero **lo escribí primero y lo comprobé después**,
que es el orden equivocado.

## 3. Construí sobre una descripción del prompt maestro sin abrir el fichero

El prompt maestro §2.5 describe el orden de bloques de `rag_es.txt` empezando por
`{response_policy_json}` y con `{case_facts_json}` en sexto lugar. **El fichero
dice otra cosa**: `{clinical_context_json}` va primero y `{response_policy_json}`
penúltimo.

Razoné un rato sobre «el primer bloque ya es volátil» antes de abrir el fichero.
El informe `BLOQUES_A_B_C_2026-08-14.md` tenía el orden correcto desde el
14-ago — o sea que la información estaba en el repositorio y no la usé.

**Regla:** el enunciado describe el sistema; el fichero **es** el sistema.

## 4. Asigné una clase a «sin intervención definida» olvidando un bloque del plan

Al calcular si el plan alcanza la Puerta C conté `unsupported_numeric_claim` (6)
como huérfana, cuando el Bloque H la ataca explícitamente «por construcción».
Corregido antes de commitear, pero el borrador ya llevaba escrita la frase
alarmista *«el plan tal y como está no alcanza la Puerta C»*, que con la
asignación correcta es **falsa** — sí la alcanza, con un margen de 0,58 puntos.

**El error importa por su dirección:** una conclusión alarmista se defiende sola
y nadie la audita. Las que hay que revisar dos veces son las que confirman lo que
uno esperaba.

---

# Segunda tanda — la ventana del 15-ago (con las máquinas encendidas)

## 5. Publiqué un veredicto falso y lo salvó un control que puse por otra cosa

**El más grave de la ventana, y habría desviado el plan entero.**

`[MEDIDO]` La primera ejecución de F.1 devolvió **«NO PROPAGA — los Bloques H e I
no son viables en Ollama»** con 30 de 30 violaciones del `enum`. Es **falso**.

La pista estaba en el dato y no la miré: las 33 salidas eran **cadenas vacías**,
no valores erróneos. Qwen3.6 es un modelo de *thinking*; sin `think: false` el
razonamiento consume `num_predict` —mi sonda pedía **24** tokens— y `content`
vuelve vacío. Mi veredicto automático contaba «vacío» como «fuera del enum».

**Qué lo salvó:** la sub-prueba de dos pasadas que había añadido por §3.2 del
prompt maestro —para otra cosa completamente— sí enviaba `think:false`, y obtuvo
`15.20`, dentro del enum, con el mismo modelo y el mismo esquema. El contraste
entre las dos era imposible de ignorar.

**Sin ese control habría publicado que hay que cambiar de motor de inferencia.**

> **La lección no es «pon `think:false`».** Es que un veredicto automático que
> mapea *«no obtuve la respuesta esperada»* a *«el sistema falló»* **no distingue
> un fallo del sistema de un fallo de la sonda**, y por defecto acusa al sistema.
> Corregido: una salida vacía se cuenta aparte y el veredicto lo dice.

## 6. Dejé una espera de veinte minutos multiplicada por nueve

`[MEDIDO]` `correr_puerta_0.py` espera `--sondeos × --pausa-sonda` antes de cada
corrida, con valores por defecto de **40 × 30 s = 20 minutos**. En una campaña de
nueve corridas eso son **tres horas de GPU encendida sin medir un solo turno** —
más que la campaña entera.

Esa espera existe por una razón buena: no tocar al proveedor durante el arranque
de la GPU, que es una de las dos causas medidas de apagado. Pero el protocolo ya
exige verificar `hemovet_gpu_startup=ready` **por journal** antes de llegar ahí, y
en esta ventana además el smoke test del despliegue ya había hecho una petición de
chat real. La espera era pura pérdida.

**Lo descubrí con las máquinas encendidas y la primera corrida esperando**, que
es el peor momento posible. Escribí un preflight de seis comprobaciones
precisamente para no descubrir cosas así con la GPU corriendo, y **ninguna de las
seis miraba cuánto iba a tardar**.

> **La lección:** un preflight que verifica *corrección* y no *coste* deja pasar
> el error más caro. La comprobación que faltaba es de una línea: estimar la
> duración y compararla con el presupuesto escrito.

## 7. Maté mi propia orden con un `pkill` por patrón

`[MEDIDO]` Al intentar detener la campaña usé `pkill -f "campana_v3.sh"`. El
patrón casó también con **mi propio proceso**, que llevaba esa cadena en la línea
de órdenes, y la orden murió con código 144 dejando el parche a medias.

Trivial, pero costó dos minutos de GPU y una orden más. La forma correcta es
resolver los PID primero y matarlos por número.

## 8. Lancé la campaña en primer plano y el timeout la mató a los cinco minutos

`[MEDIDO]` La primera vez lancé `campana_v3.sh` sin `run_in_background`. El
límite de cinco minutos de la orden mató la campaña entera con la GPU encendida.
No perdió datos —no había escrito ninguno— pero perdió cinco minutos de ventana.

---

# Tercera tanda — después de la ventana, con las máquinas ya apagadas

## 9. Verifiqué los sellos mirando solo la primera línea, y dije que estaban bien

`[MEDIDO]` Durante horas usé esta comprobación:

```bash
esp=$(awk '{print $1}' "$s" | head -1)     # ← solo la PRIMERA línea
```

**Cada `.sha256` sella varios ficheros.** `BLOQUE_G_REGLA_DE_DECISION.sha256`
sella la regla **y** `FIRMA_VETERINARIA_G1.md`; el de v2 sella el informe **y**
`evaluar_puertas.py`. Mirando una línea publiqué **«los seis sellos válidos»**
con **dos ya rotos** —los dos rotos por mí, al ampliar las peticiones de firma—.

`[DERIVADO]` Es el mismo modo de fallo que `detect_changes` en este repositorio y
la misma dirección, la peor: **falla en abierto**. Un verificador que dice «todo
bien» sin haber mirado es peor que no tenerlo, porque sustituye la duda por
confianza. Y aquí el afectado era el control de integridad del pre-registro, que
es justo la pieza cuyo valor entero depende de que nadie la toque en silencio.

**Cómo lo pillé:** al sellar la revisión ciega, la misma comprobación casera dio
cuatro ✘ donde antes daba ✔ sin que yo hubiera tocado esos ficheros. La
contradicción entre dos ejecuciones de mi propia herramienta fue la señal.

**Corregido:** `validacion_llm/scripts/verificar_sellos.sh` usa `sha256sum -c`
—que comprueba todas las líneas—, distingue el fallo esperado y documentado de
los reales, y devuelve código de salida 1 ante cualquier otro. Los dos sellos
rotos se anotaron en `SELLOS_REGISTRO.md` con hash viejo, hash nuevo, qué cambió
y por qué, **antes** de volver a sellar.

**Lo que no pasó, y es lo que importa:** las **reglas de decisión** siguen byte a
byte idénticas. Lo roto eran las peticiones de firma, que son documentos vivos
dirigidos a un clínico. La distinción está escrita en `SELLOS_REGISTRO.md` §4.

## 10. Di por buena una hipótesis de falso positivo sin ejecutarla

`[MEDIDO]` Al ver que `definitive_diagnosis` fallaba en «¿Qué es un hemograma?» y
«¿Para qué sirven?» —preguntas educativas puras— escribí que olía al mismo falso
positivo que `plasma`. **Lo ejecuté antes de publicarlo y es falso:** seis
redacciones educativas plausibles no disparan; solo lo hace «Tu perro tiene
anemia».

No llegó a salir de la sesión, así que no es un error publicado. Va en la lista
porque **el patrón sí es un error**: dos casos con la misma forma superficial
—clase de seguridad + pregunta educativa— no comparten mecanismo por eso. Lo que
lo evitó fue la costumbre de ejecutar el predicado en vez de leerlo.

---

# Cuarta tanda — la fase del banco

## 11. Mi comprobador de DIR habría publicado el peor fallo como un acierto

`[MEDIDO]` La primera versión del comprobador de pares dirigidos marcaba
**«SENSIBLE»** cuando las dos etiquetas simplemente **diferían**:

```python
obtenidos = {o for _, o in miembros}
ok = len(obtenidos) == len(esperados) == 2      # ← solo mira que difieran
```

El par `D1` da `['RECHAZAR', 'ACEPTAR']`: **las dos etiquetas difieren**, así que
pasaba como éxito. Pero difieren **en la dirección contraria** — rechaza el
genérico legítimo y acepta el anclado al paciente.

`[DERIVADO]` **Habría publicado como acierto el hallazgo más grave del banco**, y
además habría escondido que el falso positivo de la etiología y los falsos
negativos de la directiva **son la misma inversión** vista desde sus dos extremos.

**Cómo lo pillé:** al leer la salida antes de escribir el informe, `D1` mostraba
`SENSIBLE` junto a un par cuyos veredictos, leídos uno a uno, eran obviamente los
equivocados. La contradicción entre la etiqueta del resumen y el detalle de la
misma línea fue la señal.

**Corregido:** ahora exige que **cada miembro coincida con su etiqueta esperada** y
distingue tres veredictos —`SENSIBLE`, `CIEGO`, `INVERTIDO`—.

`[DERIVADO]` **La lección, y es la de siempre en esta lista:** una comprobación
que verifica «cambió» en vez de «cambió a lo correcto» es una comprobación que
falla en abierto. Van tres en este proyecto —`detect_changes`, la verificación de
sellos por la primera línea, y ésta—, y las tres en la misma dirección: dan por
bueno lo que no han mirado.

---

## Lo que sí hice bien, para que la lista sea utilizable

No por autobombo: si solo se listan los fallos, la próxima sesión no sabe qué
conservar.

- **No acepté un `CRITICAL` de la herramienta sin comprobarlo.**
  `impact(evaluar)` devolvió riesgo CRITICAL con 211 símbolos afectados. Un grep
  bastó para ver que el símbolo tiene **una** definición y **cero** llamadores, y
  que el script no importa nada del backend. Era colisión de nombre con el índice
  desactualizado. Lo declaré en el commit en vez de silenciarlo.
- **No di por buena una cita clínica porque viniera en el enunciado.** La frase
  de eClinPath que justifica G.1 la busqué en la fuente. Está —pero **no** en la
  página del leucograma, que fue la primera que miré: está en la de
  [WBC counts](https://eclinpath.com/hematology/tests/wbc-count/). Poner una cita
  mal atribuida delante de un veterinario habría costado la firma.
- **Paré y pregunté cuando la decisión era del usuario.** El plan de muestreo
  `n=400, c≤8` que pedía el GOAL sostiene la afirmación pero sube α de 0,0386 a
  0,4074. Eso cambia el coste y el veredicto, así que no lo decidí yo.
- **Comprobé la premisa de G.2 antes de implementarla.** Estaba ya implementada.
  Media jornada de trabajo que no hubo que hacer.

---

## Una limitación de esta sesión que no es un error, pero condiciona todo

**No he medido nada nuevo.** Todo lo de esta sesión sale de datos que ya existían
—los 225 turnos del 14-ago, el log de producción, el código— o es aritmética
sobre ellos. Las máquinas no se han encendido ni una vez.

Eso tiene una consecuencia que hay que declarar: **la campaña de 225 turnos midió
el árbol B (con el Bloque D), y el desplegado es el árbol A.** Todas las cifras de
partida que uso —48 fallos, 78,67 %, el reparto por clase, `p_ciego`, `pass^K`—
son del árbol B. Están justificadas como línea base porque el Bloque D quedó
refutado por solape de intervalos, pero **descansan en un n=45 del otro lado**.

La campaña v3 con n=400 sobre el árbol A cierra ese hueco. Hasta entonces,
cualquier comparación «antes/después» lleva esa nota.
