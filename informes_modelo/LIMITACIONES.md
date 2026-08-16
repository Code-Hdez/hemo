# Limitaciones — qué NO se puede afirmar con lo que hay

**Fecha:** 2026-08-15 · **Árbol:** `4cca5683` · **VMs:** las tres `TERMINATED`, verificado.

> Se escribe antes de la campaña y no después, porque una limitación descubierta
> al redactar las conclusiones siempre suena a excusa. Aquí están las que ya se
> conocen, con su tamaño y con lo que costaría cerrar cada una.

Toda cifra va marcada `[MEDIDO]`, `[DERIVADO]` o `[INFERIDO]`.

---

## 1. Del aparato de medida

### 1.1 La línea base mide un árbol que no es el desplegado

`[MEDIDO]` La campaña de 225 turnos —la única con el plan de muestreo completo, y
de la que sale **todo**: los 48 fallos, el 78,67 %, el reparto por clase,
`p_ciego`, `pass^K`, la reutilización de caché— midió la release `8e8fa19e`, que
lleva el Bloque D. El árbol desplegado es `4cca5683`, que lo tiene revertido.

`[MEDIDO]` La equiparación está justificada porque el Bloque D quedó refutado
precisamente por no cambiar nada —los intervalos de Wilson se solapan por
completo, en su clase objetivo y en el total—, pero **descansa en un n = 45 del
otro lado**.

**Cierre:** la campaña v3 con n = 400 sobre el árbol A. Es la primera medición de
esa ventana y elimina la nota entera.

### 1.1 bis El p95 de latencia depende del convenio de percentil, y el margen es de 0,69 s

`[MEDIDO]` Sobre los 405 turnos de la campaña v3, el p95 de `segundos_cliente`:

```
interpolado    24,23 s
nearest-rank   24,31 s      ← el que citan los informes
```

**Los dos son correctos**: son los dos convenios habituales. La diferencia es de
**0,08 s** y normalmente daría igual.

`[DERIVADO]` **Aquí no da igual.** El criterio es `p95 ≤ 25 s` y el margen medido
es de **0,69 s**: un cambio que empeore la latencia menos de un segundo puede
quedar a un lado u otro del criterio **según el convenio que se elija**.

**Cómo se resuelve, y está escrito antes de medir la ventana 2:**
`coste_via_servidor.py` **publica los dos y juzga por el peor**. Elegir el
favorable después de ver los datos sería la misma clase de decisión que los sellos
existen para impedir.

### 1.2 `seed = −1`: la validez es estocástica y no se puede fijar

`[MEDIDO]` El backend no fija semilla. Cada corrida es un sorteo distinto, y dos
corridas de 45 con la misma configuración dieron 68,89 % y 75,56 %: siete puntos
de diferencia sin que nada cambiara.

**Consecuencia:** ninguna afirmación de este proyecto puede descansar en una sola
corrida, y por eso la Puerta R existe. **Coste de cerrarlo:** fijar y registrar
la semilla, ≈ medio día más una ventana. No hecho.

### 1.3 Los denominadores de S y de C se mueven en direcciones opuestas

`[DERIVADO]` La Puerta S se mide sobre lo **publicado**. Cuando el sistema mejora
en C, hay menos reparaciones y por tanto **menos respuestas publicadas**, así que
la afirmación de S se debilita aunque la seguridad no cambie: de 0/198
(≥ 98,4984 %) a 0/177 (≥ 98,3217 %).

No es un defecto: es la consecuencia de medir lo que se entrega. Pero hay que
declararlo, o parecerá un empeoramiento.

### 1.4 Posición y pregunta están confundidas

`[MEDIDO]` El corpus lanza siempre las mismas 45 preguntas en el mismo orden, así
que «turno 5» y «pregunta GEN-05» son la misma variable. El cruce clase × posición
—40 % de fallo en los turnos 1-5 frente al 12 % en los 11-15— **describe**, y no
puede atribuir el efecto a la longitud del historial ni al contenido de la
pregunta.

**Cierre:** aleatorizar el orden dentro de cada ámbito. Es barato pero **rompe la
comparabilidad** con todas las corridas anteriores, así que no se hace sin
decidirlo explícitamente.

---

## 2. De lo que es imposible observar

### 2.1 El texto rechazado no existe

`[MEDIDO]` `_safe_operational_log_payload` recorta toda cadena a 192 caracteres
antes de escribir cualquier log, **por diseño de privacidad clínica**. El primer
candidato, el que el validador rechazó, no se persiste en ningún sitio.

**Es la limitación más cara del proyecto.** Impide, hoy:

- saber si `indirect_treatment_recommendation` es etiología o recomendación real
  —dos cosas opuestas con arreglos opuestos—;
- saber por qué la reparación arregla `GEN-05` 5/5 y `SEL-01` 0/5;
- caracterizar qué escribe el modelo cuando falla.

**Mitigación aplicada, sin tocar la privacidad:** instrumentar los **términos
cerrados** que dispararon cada comprobación (`hierro+puede`, `marker_absent`,
`unsupported_numeric_claim:hct`). Da el mecanismo sin dar el texto.

**Cierre completo:** persistir el candidato rechazado. ≈ 1 día más una ventana, y
**es una decisión de privacidad clínica que no es técnica**.

### 2.1 ter El validador de seguridad es **ciego en una dirección**, y está medido

`[MEDIDO]` `validacion_llm/scripts/banco_de_frontera.py`: **100 frases** contra la
taxonomía sellada en `TAXONOMIA_DE_EVASION.md`, pasadas por
`OutputValidator.validate()` **completo**.

```
75 de 100 desacuerdos   Wilson 95 % [65,7 % , 82,5 %]
                        Clopper-Pearson [65,3 % , 83,1 %]
74 falsos NEGATIVOS · 1 falso POSITIVO
```

| hoja | mecanismo | tasa |
|---|---|--:|
| E6 | elipsis y anáfora | **100,0 %** |
| E3 | **anti-derivación** | **93,3 %** |
| E1 | perífrasis impersonal | 86,7 % |
| E2 · E4 · E7 | imperativo · anclaje · condicional | 80,0 % |
| E5 | morfología clítica | 60,0 % |
| E8 | control negativo | **0,0 %** (techo 25,9 %) |

`[MEDIDO]` **Y dos propiedades que un banco de solo ejemplos base no habría
visto:**

- **La paráfrasis cambia el veredicto** en tres de las cinco hojas con variantes
  INV. La regla depende de la **superficie**, no del contenido.
- **La regla no está orientada al eje general↔específico:** de cuatro pares
  dirigidos, **tres son ciegos y uno está INVERTIDO** — rechaza el genérico
  legítimo y acepta el anclado al paciente.

#### Lo que esto NO cambia, y lo que sí

> **NO cambia:** la Puerta S sigue sin violaciones observadas en 351 respuestas
> publicadas.
>
> **SÍ cambia, y son dos frases que no se fusionan:**
>
> **Límite estadístico.** 0/351 da un techo unilateral del 95 % de **0,85 %**
> (regla de tres; Hanley & Lippman-Hand, JAMA 1983;**249**:1743-5). No es un cero:
> es compatible con hasta una violación cada ~117 respuestas.
>
> **Límite de detectabilidad.** Ese techo acota solo lo **detectable por S**. Para
> las siete familias que S no reconoce, su sensibilidad es **nula** y el intervalo
> **no es informativo**.

`[DERIVADO]` **El banco es adversarial por construcción**: mide cobertura frente a
rutas conocidas, **no** la distribución de lo que el modelo escribe. El 75 % **no
es «la tasa de fallo del sistema»**, y las frases las escribió el equipo, no el
modelo. Desarrollo completo en `AUDITORIA_DE_FRONTERA.md` y `BANCO_DE_FRONTERA.md`.

### 2.1 bis `unsupported_numeric_claim` sub-detecta, y hay que decirlo

`[MEDIDO]` La ruta numérica de `claim_validation` compara **fragmentos** de número
y le basta **una** intersección no vacía con el hecho que aportó el solape de
términos. Dos consecuencias medidas ejecutando la función:

- El tokenizador **parte `4.52` en `4` y `52`**: no se compara la cifra.
- **La fecha aporta números** (`2026`, `01`, `10`), así que una frase que cite la
  fecha del estudio pasa el control **con cualquier valor**. Verificado: `9.99`
  con fecha → SOPORTADO; `9.99` sin fecha → RECHAZADO.

**Lo que NO se puede afirmar:** que las cifras de las 356 respuestas publicadas
sean correctas. Solo que ninguna disparó las comprobaciones **tal como están
implementadas**.

**No afecta a la Puerta S**, que se juega en clases de seguridad —diagnóstico
definitivo, dosis, recomendación— y no en el soporte numérico.

`[DERIVADO]` Y afecta al **Bloque H**: su resultado primario caería a 0 por
construcción sin haber demostrado nada sobre cifras alucinadas. Desarrollado en
`BLOQUE_H_LO_QUE_MIDE_DE_VERDAD.md`. El validador **no se toca** (`I-3`).

### 2.2 β de la reparación es inobservable por construcción

`[MEDIDO]` La reparación **solo** se dispara sobre salidas que ya fallaron. En 225
turnos hay **cero** observaciones del reparador actuando sobre una salida válida,
así que la probabilidad de que estropee una buena no se puede estimar.

**Cierre:** pasar el reparador por los 177 válidos de primera pasada y revalidar.
177 generaciones, ≈ 35 min de GPU. Especificado en
`APORTE_REAL_DE_LA_REPARACION.md` §5, **no ejecutado**.

### 2.3 El log de producción da repartos, nunca tasas

`[MEDIDO]` Los 97 `invalid_output_*` del log del 14-ago son tráfico real sobre el
árbol desplegado, pero **no se conoce el denominador**: el log no permite contar
los turnos que sí respondieron. Sirven para confirmar el reparto por clase y para
nada más. No entran en ninguna puerta.

---

## 3. Del criterio de aceptación

### 3.1 El plan v3 renuncia explícitamente a afirmar ≥ 96,4 %

`[DERIVADO]` Con 13/400 —el límite de aceptación— la cota inferior unilateral al
95 % es **94,88 %**, no 96,4 %. Sostener el 96,4 % **y** conservar los riesgos
α ≤ 5 % / β ≤ 10 % exige **n = 1125**, es decir 25 corridas y ≈ 4,6 h de GPU.

Se eligió el plan barato **declarando la renuncia**. Si la campaña sale con ≤ 8
fallos en 400, la afirmación fuerte llega sola (96,42 %) sin haber movido
ninguna portería — pero no está garantizada.

### 3.2 Un sistema exactamente en el objetivo suspende el 58 % de las veces

`[DERIVADO]` La potencia del plan v3 con validez real del 96,4 % es del **42,01 %**
de aceptación. Es el precio de una puerta cuyo AQL está en el 98 %. **Un rechazo
no demuestra que el sistema no llegue**, y quien lea el informe debe poder
distinguirlo.

### 3.3 `pass^9` sigue sin ser un certificado

`[DERIVADO]` Con K = 9, la Puerta R detecta una pregunta que está al 90 % de
validez el **61,3 %** de las veces, y una que está al 98 % solo el 16,6 %. Mejora
el 41 % de `pass^5`, pero «R pasó» **nunca** significa «no quedan preguntas
frágiles».

### 3.4 `pass^K` empírico depende del corpus, no solo del sistema

`[MEDIDO]` El `pass^6` empírico (31,33 %) supera al i.i.d. (23,70 %) en 7,63
puntos porque los fallos **se agrupan por pregunta**. Ese margen es una propiedad
de **estas** 45 preguntas en **este** orden: una consulta real con otra mezcla de
preguntas daría otro número. Por eso se publican los dos.

---

## 4. De la generalización

### 4.1 Un solo paciente, un solo fixture

`[MEDIDO]` Todas las campañas usan el mismo fixture (`test5@test.com`, un
paciente con HCT 63,6 %). Nada de lo medido dice cómo se comporta el sistema con
otros patrones hematológicos — y `ambiguous_parameter_claim` depende
**exactamente** de que el absoluto y el porcentaje de un parámetro tengan estados
distintos, que es una propiedad **de este paciente**.

> `[INFERIDO]` Es plausible que la tasa de esa clase cambie mucho con otro
> hemograma. **No medido**, y es la limitación de generalización más seria del
> trabajo.

### 4.2 Un solo modelo, una sola cuantización, un solo hardware

Qwen3.6-27B Q4_K_M sobre A100-SXM4-40GB con Ollama 0.32.6. Los resultados de
caché, latencia y validez son de esa combinación. La literatura citada sugiere
que la capacidad del modelo cambia el signo de algunos efectos —*Capacity, Not
Format* mide neutro en Sonnet y −36 pp en Haiku—, así que **nada de esto se
extrapola a otro modelo sin remedirlo**.

### 4.3 Las 45 preguntas no son una muestra aleatoria de nada

Son un corpus construido a mano para cubrir tres ámbitos. `pass^K`, el reparto por
clase y la validez son **de este corpus**. Un corpus con más preguntas causales
—el tipo de `GEN-05`— daría peor; uno con más definicionales, mejor.

---

## 4 bis. De la vía «que escriba el servidor» (fase M)

### 4bis.1 M.2 y M.3 están implementados y **sin medir**

`[MEDIDO]` Hay 28 tests, dos reglas selladas antes de medir, y el mecanismo
verificado contra el validador real. **Nada de eso es una medición de eficacia.**
El flag `CHAT_SERVER_WRITES_ENABLED` está **apagado** y no ha corrido ni un turno
contra el modelo.

**Lo que NO se puede afirmar todavía:** que `ambiguous_parameter_claim` baje. Lo
que sí: que **la frase que la disparaba ya no se puede escribir** —el `enum` no
contiene la familia genérica y el saneado la recorta de la prosa—, y que el texto
que el servidor ensambla **pasa el validador de producción**.

### 4bis.2 El alcance está medido sobre texto **publicado**, no sobre los fallos

`[MEDIDO]` Los 96 fallos ocurrieron en borradores que el backend **no persiste**.
Que caigan en las oraciones que el servidor va a escribir **se infiere de la
definición de cada clase**, no se verifica. La inferencia es sólida
—`ambiguous_parameter_claim` *es* una afirmación de estado sobre una familia
genérica— pero es inferencia, y si una clase no cae en la ventana 2 **lo que falló
fue esto**.

### 4bis.3 `definitive_diagnosis` cambia de columna con una condición

`[MEDIDO]` Sanear la prosa con los predicados de seguridad cuesta **0,00 %** sobre
los 356 textos publicados, así que los 6 fallos pasan de «irreducibles» a
«alcanzables». `[DERIVADO]` **Pero eso vale solo si quitar la oración diagnóstica
deja una respuesta que siga respondiendo**, y eso se mide como sobre-rechazo en la
ventana 2. Hasta entonces la aritmética corregida —6,75 % en vez de 8,25 %— lleva
esa condición pegada.

### 4bis.4 El diseño que el plan proponía no funcionaba

`[MEDIDO]` Desambiguar por el nombre —«el recuento absoluto de neutrófilos»— **no
evita la clase**: `generic_family_mentions` marca cualquier alias del absoluto.
Funciona separar la etiqueta del valor en cláusulas distintas. Se descubrió
**ejecutando el validador**, no leyéndolo, y está fijado con un test para que
nadie lo «arregle» concatenando.

`[DERIVADO]` **Consecuencia de estilo que hay que declarar:** el formato de dos
cláusulas es más rígido que una frase corrida. El servidor escribiría el **25,3 %**
del texto —por debajo del 60 % que se fijó como señal de formulario—, pero la
naturalidad la juzga la revisión ciega, no este número.

---

## 5. De esta sesión en concreto

`[MEDIDO]` **No se ha medido nada nuevo y las máquinas no se han encendido ni una
vez.** Todo sale de datos que ya existían o es aritmética sobre ellos. Los cuatro
defectos de método propios están en `DEFECTOS_DE_METODO_PROPIOS.md`, incluido uno
—inferir una causa de un campo que se rellena después del efecto— que estuvo a
punto de producir un arreglo para un problema inexistente.

**Y tres hallazgos de esta sesión son `[INFERIDO]`, no `[MEDIDO]`**, y conviene no
citarlos como si fueran lo segundo:

1. Que la ventana deslizante de `_select_history` sea **la causa** del 10,6 % de
   reutilización. Que rompe el prefijo es cierto por construcción; que sea la
   causa lo decide F.2b.
2. Que los 6 `missing_evidence_attribution` vengan de un marcador inválido y no
   de un marcador ausente. Lo decide la instrumentación, en la próxima campaña.
3. Que los 12 `indirect_treatment_recommendation` sean etiología y no
   recomendación real. Lo decide la instrumentación **y** la firma veterinaria.
