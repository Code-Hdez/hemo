# Estudio de lectores — convertir la coherencia normativa en evidencia

**Fecha:** 2026-08-15 · **Estado:** **protocolo sellado, sin ejecutar**
**GPU: cero** · **Se sella con** `ESTUDIO_DE_LECTORES.sha256`

> GOAL, I-4: *«El §4.3 se defiende MIDIENDO AL LECTOR. Separar componente y clase
> de cantidad es **coherencia, no conformidad** — ningún estándar rige la sintaxis
> de la prosa. La evidencia es el estudio.»*

---

## 0. Qué está en juego, dicho sin rodeos

La construcción en dos cláusulas quita la clase `ambiguous_parameter_claim`. La
pregunta que hará el tribunal es la obvia:

> *«¿Arreglaron el problema, o aprendieron a esquivar el detector?»*

Esa pregunta tiene nombre técnico —**Adversarial Misalignment Goodhart**, Manheim
& Garrabrant (arXiv:1803.04585)— y **conviene nombrarla nosotros primero**. Tiene
además precedente empírico: Krishna et al. (NeurIPS 2023) hunden la detección de
DetectGPT **del 70,3 % al 4,6 %** solo parafraseando, *«without appreciably
modifying the input semantics»*. Un detector léxico **se puede invertir por
reescritura**. Negarlo sería insostenible.

**La defensa correcta no es negarlo: es demostrar que aquí el proxy y el objetivo
convergen.** Y eso solo lo demuestra medir al lector.

---

## 1. El criterio, preestablecido y prestado de un regulador

La guía de legibilidad **Comisión Europea / EMA** para prospectos (Rev.1, 2009)
fija el criterio **90/90**:

> *«a satisfactory test outcome… is when the information requested within the
> package leaflet can be **found by 90 % of test participants, of whom 90 % can
> show that they understand it**.»*

**Se adopta como umbral a priori.** No es un número inventado después: es el
criterio de un regulador para exactamente esta clase de pregunta.

Metodología que la guía especifica, y que se sigue: **mínimo 20 participantes**
(piloto 3-6, ronda 1 con 10, validación con 10 más) · **12-15 preguntas** ·
máximo 45 min · entrevistas uno a uno · **preguntas en orden aleatorio,
deliberadamente distinto del orden del texto** —para impedir emparejar por
posición en vez de comprender— · diseño iterativo entre rondas.

---

## 2. El diseño

**Precedente metodológico:** Zikmund-Fisher, Exe & Witteman (*J Med Internet Res*
2014;16(8):e187), **n = 1817**: resultados de laboratorio en formato tabular,
elección forzada *«¿está este valor fuera del intervalo de referencia?»*.
Resultado: **77 %** de aciertos con alta numeracidad frente a **38 %** con baja.

**La adaptación:**

| | |
|---|---|
| **Estímulo** | una frase generada por el sistema |
| **Ítem** | *«¿Qué cantidad de neutrófilos reporta esta frase?»* |
| **Opciones** | `(a) el recuento absoluto` · `(b) el porcentaje` · **`(c) no puedo saberlo con esta frase`** |
| **Diseño** | **intra-sujeto pareado**: el **mismo hecho** en redacción vieja y nueva |
| **Población** | **los usuarios previstos del sistema** (DECIDE-AI ítem 2) |
| **Cegamiento** | el participante no sabe cuál es «la nueva». Orden aleatorizado |

> **La opción (c) es obligatoria.** Sin ella el acierto se contamina con
> adivinación 50/50, y un 50 % de aciertos por azar arruinaría la lectura del
> 90/90.

`[DERIVADO]` **El pareado no es un detalle:** hace que la comparación no dependa
de la muestra de participantes, y obliga a **McNemar** en vez de dos proporciones
independientes.

---

## 3. El banco de ítems — generado del sistema real

`[MEDIDO]` Producido con `slot_rendering.renderizar_afirmaciones()`, no redactado
a mano:

| par | redacción **vieja** | redacción **nueva** |
|---|---|---|
| NEU abs | «Los neutrófilos están dentro del rango (8.4 ×10³/µL).» | «Neutrófilos, recuento absoluto.⏎Valor medido: 8.4 ×10³/µL, dentro del rango de referencia.» |
| NEU % | «Los neutrófilos están altos (85.0 %).» | «Porcentaje de neutrófilos.⏎Valor medido: 85.0 %, por encima del rango de referencia.» |
| LYM abs | «Los linfocitos están dentro del rango (1.2 ×10³/µL).» | «Linfocitos, recuento absoluto.⏎Valor medido: 1.2 ×10³/µL, dentro del rango de referencia.» |
| LYM % | «Los linfocitos están bajos (9.8 %).» | «Porcentaje de linfocitos.⏎Valor medido: 9.8 %, por debajo del rango de referencia.» |
| MONO abs | «Los monocitos están dentro del rango (0.9 ×10³/µL).» | «Monocitos, recuento absoluto.⏎Valor medido: 0.9 ×10³/µL, dentro del rango de referencia.» |
| MONO % | «Los monocitos están dentro del rango (7.3 %).» | «Porcentaje de monocitos.⏎Valor medido: 7.3 %, dentro del rango de referencia.» |

### 3.1 Una trampa de diseño que apareció al generar el banco, y hay que declararla

`[MEDIDO]` La redacción vieja **con la unidad entre paréntesis** ya desambigua
bastante: un lector que sepa que `%` es porcentaje puede acertar sin entender la
frase. **Si se usa solo esa variante, el efecto medido saldrá pequeño y el estudio
parecerá refutar la mejora cuando en realidad ha medido otra cosa.**

`[MEDIDO]` **La frase que de verdad falló en la campaña no llevaba valor.** `SEL-01`
—«¿qué valores aparecen fuera del rango?»— disparó la clase **9 de 9** con
construcciones del tipo *«los neutrófilos están altos»*, **sin cifra ni unidad**.

**Por eso el banco lleva DOS variantes de la redacción vieja, y se analizan
separadas:**

```
VIEJA-A  «Los neutrofilos estan altos.»                    ← la que fallo de verdad
VIEJA-B  «Los neutrofilos estan altos (85.0 %).»           ← con unidad, mas facil
NUEVA    «Porcentaje de neutrofilos. Valor medido: 85.0 %, por encima del rango.»
```

**El contraste primario es NUEVA vs VIEJA-A.** VIEJA-B va como **secundario**, y
su función es honesta: **acotar por arriba cuánto de la mejora se debe a la
separación de cláusulas y cuánto a haber añadido la unidad**. Declararlo antes
evita el reproche de haber elegido el comparador fácil.

---

## 4. La estadística — y las fuentes se contradicen, así que se declara

### 4.1 Primario

**Proporción cruda de aciertos con IC exacto de Clopper-Pearson.** Es lo que hacen
tanto el 90/90 de la EMA como Zikmund-Fisher. Comparación vieja-vs-nueva con
**McNemar**, por el diseño pareado.

### 4.2 Acuerdo entre lectores — dos coeficientes, y la disputa escrita

- **κ de Cohen** tiene dos paradojas conocidas (Feinstein & Cicchetti, *J Clin
  Epidemiol* 1990;43(6):543-549; Cicchetti & Feinstein, ibíd. 551-558): con
  marginales muy desbalanceadas **κ se hunde aunque el acuerdo observado sea
  altísimo**.
- `[DERIVADO]` **Y eso va a pasar aquí, justo si funciona.** Si la redacción nueva
  desambigua, casi todos acertarán → marginales sesgadas → **κ colapsa cuando el
  resultado es máximo**. Reportar κ solo sería sabotear el propio hallazgo.
- `[MEDIDO]` **Ya está verificado en simulación en este proyecto**
  (`revision_ciega.py`): acuerdo **97 %**, **κ = 0,000**, **AC1 = 0,970**.
- **Gwet AC1 se propone como remedio, pero está impugnado:** Vach & Gerke
  (*MethodsX* 2023;10:102212) — *«Gwet's AC1 should not be seen as a substitute
  for Cohen's kappa»*—, y las categorías verbales de Landis & Koch **no** son
  trasladables a AC1.
- **Tercera posición:** Shankar & Bangdiwala (*BMC Med Res Methodol* 2014;14:100)
  recomiendan el **B-statistic** con su gráfico de acuerdo *«as an alternative to
  kappa»* en tablas 2×2.

> **No se elige un coeficiente en silencio.** Se reportan **dos**, y se escribe que
> la falta de consenso es un hecho de la literatura. **Exhibirlo es más sólido que
> ocultarlo.**

---

## 5. Dos avisos de diseño

- **No se usa *cloze*.** Mide comprensión global del pasaje, no *«¿qué cantidad se
  reportó?»*, y tiene efectos de edad documentados que confunden la medida. Un
  tribunal puede sugerirlo por familiaridad: la respuesta está preparada.
- **No se copia el diseño de Battah et al.** (*Sci Rep* 2025;15:27702), aunque sea
  el precedente más cercano de «frases clínicas leídas de forma discordante» —49
  patólogos, 91 clínicos, 8 frases diagnósticas—. Usó escala continua, solo
  descriptiva y χ², **sin elección forzada y sin fiabilidad entre observadores**.
  Es buen precedente del fenómeno y mal modelo estadístico. **El nuestro debe ser
  mejor que ése, y decirlo es una contribución.**

---

## 6. Por qué la separación no la inventamos nosotros

`[VERIFICADO]` **LOINC no tiene un código para «neutrófilos». Tiene dos:**

| código | Long Common Name | Property |
|---|---|---|
| **751-8** | Neutrophils **[#/volume]** in Blood by Automated count | **NCnc** (number concentration) |
| **770-8** | Neutrophils**/100 leukocytes** in Blood by Automated count | **NFr** (number fraction) |

Un nombre de cantidad bien formado en LOINC exige **Component *más* Property**.
«Neutrófilos» a secas **no es un nombre de cantidad**: es un componente sin clase
de cantidad. Y el detalle que remata: **LOINC resuelve la ambigüedad metiendo el
denominador dentro de la etiqueta** —*Neutrophils/100 leukocytes*—, **no pegándolo
al valor**. Es un precedente casi literal de la construcción en dos cláusulas.

`[VERIFICADO]` **IUPAC–IFCC / NPU** («Silver Book») lo dice con sintaxis formal:
`Sistema—Componente; clase-de-propiedad = valor unidad`, distinguiendo **`num.c.`**
de **`num.fr.`**. **La clase-de-propiedad es un campo obligatorio y separado.**

**Y la primacía clínica del absoluto, con sus límites de alcance declarados:**

| fuente | qué dice | aviso |
|---|---|---|
| **CLSI H20-A2** (2007), Foreword | *«Absolute concentrations of circulating WBC are the preferable method of reporting, since those are the medically important values, rather than percentages.»* | **Contradicción interna**: el título del propio estándar es *«…Differential Count (Proportional)»*. Citar como «CLSI reconoce que los absolutos son los valores médicamente importantes», **nunca** «CLSI recomienda absolutos» |
| **ICSH — Brereton et al.**, Int J Lab Hematol 2016;38(5), DOI 10.1111/ijlh.12563 | *«The reporting of white cell differentials in percentages should be discouraged as this only has meaning when compared to the total white cell count.»* | **`[POR VERIFICAR]`** El verbatim procede de una copia en academia.edu porque Wiley devolvió 403. **Es la cita más potente del bloque: verificarla contra el PDF original antes del tribunal** |
| **ASVCP — Nabity et al.**, Vet Clin Pathol 2018 | recomendaciones *«considering automated absolute counts, not differential percentages»* | Sus tablas listan «Neutrophils» **sin sufijo**: respalda la **primacía clínica**, no una convención de nomenclatura |
| **Merck Veterinary Manual** (Wood) | *«Interpretations should be made only by considering the absolute numbers.»* | — |
| **eClinpath (Cornell)**, `/hematology/tests/wbc-count/` | *«A differential count should never be interpreted in percentages…»* | La página hermana del leucograma **no** trae la advertencia: citar la correcta |
| **Doig & Thompson**, Am Soc Clin Lab Sci 2017;30(3):186-193 | *«It is this risk of misinterpretation of the relative differential that limits its value.»* | Su Caso 1 describe **exactamente** el disparador del validador: linfopenia relativa con absoluto normal |

### 6.1 El 43,5 % es dato nuevo, y se dice con la fórmula prudente

`[DERIVADO]` No se identificaron estudios previos —humanos ni veterinarios— que
**cuantifiquen** la discordancia de clasificación normal/anormal entre el
diferencial relativo y el absoluto en una cohorte real. La literatura lo afirma
**cualitativamente y por unanimidad**; nadie parece haberlo medido.

`[MEDIDO]` Los **2429 hemogramas caninos** con **43,5 %** (NEU), **35,8 %** (LYM) y
**29,8 %** (MONO) son, por tanto, una **contribución empírica original**.

> Se escribe *«no identificamos estudios previos que cuantifiquen esta
> discordancia»*. **Nunca** *«es el primero»*.

---

## 7. El límite honesto — va en LIMITACIONES, literal

**Ningún estándar prescribe la estructura sintáctica de la prosa narrativa.** Todos
gobiernan informes estructurados y nombres de elementos de datos. **No existe
ninguna cita que diga «separe la etiqueta y el valor en cláusulas distintas».**
Afirmar lo contrario sería inventar una fuente.

El argumento es de **coherencia, no de conformidad**: la construcción en dos
cláusulas es **una realización textual del requisito Component + Property**, no el
cumplimiento literal de un documento. Y el validador sigue siendo **a la vez
deficiente y contaminado**: no detecta ambigüedad por pronombres, elipsis o
anáfora, y marca como ambiguas construcciones que un lector desambigua sin
esfuerzo.

**Ninguna cita arregla eso. Solo lo arregla este estudio.**

---

## 8. La frase para el tribunal — y cuándo se puede decir

> *No reescribimos para pasar el validador; adoptamos la separación entre
> componente y clase de cantidad que LOINC e IUPAC-IFCC exigen para nombrar una
> magnitud de laboratorio, y que CLSI, ICSH, ASVCP y la literatura veterinaria de
> referencia justifican clínicamente. Que el validador deje de disparar es una
> consecuencia, no el objetivo — y lo demostramos midiendo la comprensión del
> lector con un criterio preestablecido, independiente del validador.*

> **Solo es cierta si el estudio se corre.** Si no se corre, la frase honesta es la
> del §7 y punto. **Un criterio a priori que solo se respeta cuando favorece no es
> un criterio** — y por eso queda escrito aquí que **si el estudio sale mal, se
> publica igual** y el §4.3 de la memoria pasa a LIMITACIONES con la redacción
> del §7.

---

## 9. Estado

`[DERIVADO]` **El protocolo está sellado y es repartible.** Lo que falta son
**participantes**, y eso no está en mi mano.

**Pero es el único estudio de la lista que no depende de los dos veterinarios
firmantes:** si los usuarios previstos son estudiantes de veterinaria, reclutar
estudiantes de veterinaria **sí** está al alcance de un grupo de estudiantes.

> **Un protocolo sellado sin ejecutar es un entregable honesto. Un §4.3 defendido
> sin datos, no.**
