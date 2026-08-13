# Hechos verificados — la única fuente de datos para referencias y anexos

> Toda cifra debe salir de aquí. Cada entrada lleva su marca:
> **[MEDIDO]** leído de un artefacto · **[DERIVADO]** calculado a partir de artefactos ·
> **[PENDIENTE]** no disponible: usar marcador, **nunca** estimar.
>
> Verificado el 12 de agosto de 2026 sobre la rama `main`, commit `f9deedb`.

---

## 1 · Las ocho referencias que faltan 🔴

**Ninguna está en el paquete.** Todas se marcan como pendientes, salvo que las tengas verificadas.

### Para §1.1.3.7 — marco teórico del rendimiento de inferencia (mínimo cinco)

| Marcador | Qué hay que citar | Criticidad |
| :--- | :--- | :---: |
| `[REF-NUEVA-1]` | Análisis *roofline* aplicado a inferencia de transformadores: régimen limitado por ancho de banda de memoria en la fase de decodificación | Alta |
| `[REF-NUEVA-2]` | **La fuente que publica el sobrecosto de la decodificación restringida por gramática** | 🔴 **Crítica** |
| `[REF-NUEVA-3]` | Documentación técnica de la arquitectura NVIDIA A100: ancho de banda nominal de 2 039 GB/s en la variante SXM4 de 40 GB. Una *datasheet* sirve: el manual las acepta como fuente primaria | Media |
| `[REF-NUEVA-4]` | Cuantización de modelos de lenguaje y su efecto en tamaño efectivo y calidad | Media |
| `[REF-NUEVA-5]` | Pre-registro de hipótesis como práctica metodológica contra la reinterpretación posterior de resultados | Media |

### Para §3.11 y §6.8 — métodos estadísticos (mínimo tres)

| Marcador | Qué hay que citar | Nota |
| :--- | :--- | :--- |
| `[REF-NUEVA-6]` | Wilson, sobre el intervalo de confianza para proporciones binomiales, y/o por qué la aproximación normal falla en proporciones próximas a cero | — |
| `[REF-NUEVA-7]` | McNemar, sobre el contraste de proporciones pareadas | — |
| `[REF-NUEVA-8]` | Wilcoxon, sobre el contraste de rangos con signo | ⚠️ **Verificar si ya está citado** a propósito de la validación clínica. Si lo está, **reutilizar la entrada, no duplicarla** |

**Para el coeficiente kappa aplicado al acuerdo entre corridas:** comprobar si la referencia de
Cohen ya empleada en la validación clínica y en la rúbrica veterinaria cubre el uso. **Probablemente
sí. Reutilizarla.**

> 🔴 **Sobre `[REF-NUEVA-2]`.** §6.8 la refuta cuantitativamente: se le atribuían al menos diez
> milisegundos por token y la medición controlada arrojó 0,332. **Refutar una fuente que no está
> citada es indefendible.** La cita tiene que ser exacta, verificable y localizable: autor, título,
> publicación, año y el valor concreto que atribuye. Si no la tienes, el marcador debe describir
> con precisión qué se busca, no quedarse en «una fuente sobre gramáticas».

---

## 2 · La auditoría de la bibliografía

El documento usa **IEEE numérico** con citas `[n]` resueltas por marcador interno. Es lo correcto:
el manual exige formato IEEE (p. 3 y p. 14) y el IEEE numera por orden de aparición.

> ⚠️ **Contradicción en el propio manual.** En la p. 14 pide que las referencias estén «ordenadas
> alfabéticamente», lo cual es incompatible con la numeración por orden de aparición del IEEE.
>
> **Recomendación: mantener IEEE numérico** —es lo que exige la instrucción de formato, que es más
> específica— y confirmarlo con el asesor. Si insistiera en el orden alfabético, la solución de
> menor daño es añadir un índice alfabético de autores como apéndice, **sin renumerar** la lista
> principal: renumerarla rompería todas las citas del cuerpo.
>
> **Para el encargo: no renumeres nada.** Reproduce la lista con sus números actuales y añade las
> entradas nuevas al final, marcadas, para que se integren en Word con referencias cruzadas.

### Checklist de auditoría — se ejecuta DESPUÉS de insertar las secciones nuevas

No es tarea de esta redacción, pero el bloque debe dejarla anotada:

- Cada cita `[n]` del cuerpo resuelve a una entrada existente.
- Cada entrada de la lista está citada al menos una vez en el cuerpo.
- La numeración sigue el orden de primera aparición tras insertar las secciones nuevas.
  **Insertar §1.1.3.7 en el Capítulo I desplaza toda la numeración posterior:** es el cambio de
  mayor riesgo mecánico de toda la revisión. Se hace con la función de referencias cruzadas del
  procesador de textos, **no a mano**.
- Ninguna fuente es Wikipedia ni un blog sin autoría reconocida (el manual lo prohíbe
  explícitamente).
- Las fuentes con DOI lo llevan; las que son en línea llevan fecha de último acceso.
- Los títulos en inglés conservan mayúsculas y cursivas según IEEE.

---

## 3 · Anexo A — Los dos riesgos que faltan

La matriz cubre riesgos técnicos, clínicos, documentales, del módulo conversacional, de usabilidad,
de privacidad, de vigilancia y de despliegue. **No cubre los dos que se materializaron o quedaron
vivos en agosto.**

> **Fila R-14 · Indisponibilidad del nodo de inferencia**
>
> | Campo | Contenido |
> | :--- | :--- |
> | Descripción | El nodo de inferencia opera sobre una instancia interrumpible; el proveedor puede reclamar la capacidad sin previo aviso, y no existe mecanismo automático de rearranque. Durante el desarrollo se registró además un evento real de agotamiento de capacidad zonal. |
> | Probabilidad / Impacto | Alta / Medio |
> | Respuesta | **Mitigar.** La arquitectura aísla el nodo de inferencia, de modo que su caída no afecta al análisis hematológico, la consulta de resultados ni el historial. |
> | Señal de activación | El servicio conversacional deja de responder mientras el resto de la plataforma permanece operativa. |
> | Plan de acción | Rearranque manual del nodo; verificación del estado con antelación a cualquier demostración, dado que el arranque en frío supera los dos minutos; a medio plazo, incorporar un vigilante de rearranque automático. |
> | Responsable | Operación y despliegue |

> **Fila R-15 · Deriva entre el modelo sellado y el instalado**
>
> | Campo | Contenido |
> | :--- | :--- |
> | Descripción | El modelo de lenguaje de la configuración anterior permanece instalado en el nodo de inferencia y la comprobación presente en el código no impide su uso, de modo que una configuración errónea podría servir respuestas de un modelo distinto del declarado. |
> | Probabilidad / Impacto | Baja / Alto |
> | Respuesta | **Mitigar.** Verificación del identificador de modelo en cada respuesta emitida; el arranque a prueba de fallos valida el compendio contra el manifiesto de versión. |
> | Señal de activación | Una respuesta registrada cuyo identificador de modelo difiere del sellado. |
> | Plan de acción | Retirar el modelo obsoleto del nodo; convertir la comprobación de identidad en una guarda bloqueante y no solo en una verificación posterior. |
> | Responsable | Backend y despliegue |

**Adapta el formato al que ya use la matriz.** Si el Anexo A presenta los riesgos como filas de una
tabla con columnas fijas, conviértelos a esa estructura; si los presenta como fichas, mantén las
fichas. **No introduzcas un formato nuevo para dos filas.**

---

## 4 · Anexo C — La evidencia de agosto

El anexo recoge hoy los ficheros de evaluación adversarial, las baterías A–E, robustez, memoria,
consistencia, rúbricas y evaluación veterinaria. **Falta la batería que en la práctica se convirtió
en el instrumento de aceptación del proyecto.**

### Qué añadir

**Un apartado nuevo: batería de contenido sustantivo.** Siete corridas más sondas, con pregunta,
respuesta, etapas atravesadas, razón de reparación y latencia por turno.

**Su aporte, que conviene escribir en una o dos frases:** las baterías A–E miden si la respuesta es
segura, robusta y consistente, pero **una respuesta que solo contiene la frase de derivación al
veterinario pasa todas esas pruebas de forma vacua**. La batería de contenido introduce un criterio
ortogonal: descontar las cláusulas de incapacidad y el eco de la pregunta, y verificar que queda
contenido verificable.

### La evolución medida — Tabla para el anexo [MEDIDO]

| Métrica | Corrida del 9 de agosto | Ronda 6 (configuración anterior) | Configuración vigente |
| :--- | ---: | ---: | ---: |
| Turnos con contenido real | 13/45 | 44/45 | **40/45** |
| Turnos sin respuesta | 1 (más 13 vacíos) | 1 | **0** |
| Mediana global | ~46 s | 44 s | **17,6 s** |
| Historial con datos | 0/15 | 15/15 | **12/15** |
| Peor turno | 118 s | 161 s | **65 s** |

> ⚠️ **Nota de privacidad, obligatoria antes de anexar.** Los ficheros de trazas contienen
> preguntas y respuestas completas. **Verificar que no incluyen identificadores de mascota,
> propietario ni clínica antes de incorporarlos.** El material usado en la campaña es de prueba
> —una mascota ficticia con datos de ensayo—, pero **eso hay que comprobarlo, no suponerlo**, para
> cada fichero que se anexe.
>
> Escribe esa verificación como una frase del anexo, no solo como una tarea: un anexo que declara
> haber comprobado la ausencia de datos personales vale más que uno que lo da por hecho.

---

## 5 · Anexo E — Los datos de cada apartado

La estructura completa está en `04_GUION_SECCIONES_NUEVAS.md`. Aquí van **los datos**.

### E.2 · Pre-registro — Tabla E.1

Compendio del documento de pre-registro: `5d6a0a71081e385e…`, **anterior a la primera medición**
[MEDIDO].

| # | Enunciado (abreviado) | Medido | Veredicto sellado |
| :--- | :--- | :--- | :--- |
| H-1 | Decodificación más rápida en A100 pero aprovechamiento de ancho de banda < 73,7 % | 34,90 % | CONSISTENTE, NO CONFIRMADA |
| H-2 | La sobrecarga de gramática es ≥ 10 ms/token | 0,332 ms/token | **REFUTADA** |
| H-3 | La tasa de fallos no cambia apreciablemente | κ = −0,145: poblaciones distintas | NO EVALUADA ▲ |
| H-4 | Los identificadores de fallo se conservan aunque cambie el recuento | 0 de 17 coinciden | NO EVALUADA, EVALUABLE ▲ |
| H-5 | El p50 por turno baja ≥ 50 % | −60,6 % (Wilcoxon, n = 64) | NO EVALUADA ▲ |
| H-6 | En preguntas de frontera el sistema confabula | reporta ventana truncada, no confabula | REFUTADA en su predicción |
| H-7 | La ventana de contexto efectiva cambió por el salto de memoria | fijada por petición | REFUTADA POR CONFIGURACIÓN |
| H-8 | El tiempo al primer token crece a lo largo de los 15 turnos | campo no expuesto por la interfaz | NO EVALUABLE por el camino B |
| H-9 | La tasa de alucinación numérica es distinta de cero | 0 de 9 · Wilson hasta 29,9 % | NO CONCLUYENTE |
| H-10 | La máquina de aplicación nueva cambia el rendimiento por sí sola | n = 1 máquina | NO EVALUABLE POR DISEÑO |

> ▲ **Instrucción explícita.** Las tres filas marcadas tienen un veredicto sellado que dice «NO
> EVALUADA» y una medición que **ya existe**: la tabla de veredictos se escribió antes de correr el
> brazo de réplica estricta y no se actualizó. **Presenta el tablero tal cual está sellado y señala
> la discrepancia en el texto.** No sustituyas el veredicto sellado por el recalculado. Retocar un
> pre-registro después de medir invalida el pre-registro.

### E.3 · Auditoría de la evidencia previa

| Dato | Valor | Marca |
| :--- | :--- | :---: |
| Ficheros de evidencia previa auditados | **208** | MEDIDO |
| Compendios verificados intactos tras la copia | **208 de 208** | MEDIDO |
| Preguntas del cuestionario de reproducibilidad | **15** | MEDIDO |
| Preguntas que no constan o constan parcialmente | **11 de 15** | MEDIDO |

**Veredicto doble de comparabilidad** (dos filas, puede ir integrado en el texto por su brevedad):

| Ámbito | Veredicto |
| :--- | :--- |
| Fallos y comportamiento | COMPARABLE CON RESERVAS |
| Rendimiento físico | **NO COMPARABLE** |

> **Criterio de tratamiento que hay que declarar:** el directorio con credenciales se contabilizó y
> se resumió por compendio, **nunca se muestreó su contenido**. Ese criterio se mantiene en el
> anexo.

### E.6 · Registro de verificación — Tabla E.5

| Dato | Valor | Marca |
| :--- | :--- | :---: |
| Aserciones de recálculo ejecutadas | **11** | MEDIDO |
| Aserciones que coinciden con el valor publicado | **10** | MEDIDO |
| Aserciones que **no** coinciden | **1** | MEDIDO |

> 🔴 **La fila que falla se muestra, no se esconde.** Motivo del fallo: el número de preguntas
> verificables publicado era de aproximadamente veinte y el fichero de verdad contiene **nueve**,
> lo que motiva la corrección de la cota de fabricación numérica **del 16,8 % al 29,9 %**
> consignada en §6.8.
>
> Es, probablemente, el detalle que mejor distinga este anexo ante el comité: acredita que la
> verificación se ejecutó de verdad y que su resultado se publicó aunque fuera incómodo.

**Tabla E.6 — Comprobaciones de diseño gráfico verificadas**, seis filas: ausencia de ejes dobles;
ausencia de gráficos circulares; nota de lectura o declaración de ausencia en toda figura;
exportación en tres formatos; intervalo de confianza en toda proporción representada; marca de
corte en todo eje truncado.

### E.7 · Lo que no pudo medirse

| Elemento | Estado | Marca |
| :--- | :--- | :---: |
| Ejes de la rúbrica de evaluación | cinco, con estado puntuado / no puntuable / sin definición sellada | MEDIDO |
| Niveles del esquema de trazas poblados | sesión y turno **poblados**; llamada y evento **vacíos** | MEDIDO |
| Paneles de ausencia producidos | **9** | MEDIDO |

**Qué escribir:** la ausencia de dato es un resultado. Los campos de temporización interna que la
interfaz no expone hicieron no evaluable una de las hipótesis; los ejes invocados sin definición
sellada no se puntuaron.

> Selecciona **dos o tres** de los nueve paneles de ausencia para ilustrarlo. Los nueve serían
> redundantes en un anexo.

### E.8 · Ablación de la gramática — Tabla E.9

| Parámetro del diseño | Valor | Marca |
| :--- | :--- | :---: |
| Tamaño por brazo | n = 30 | MEDIDO |
| Orden | intercalado A/B/A/B | MEDIDO |
| Descartes de calentamiento | 5 | MEDIDO |
| Pausa entre generaciones | 500 ms | MEDIDO |
| Tope de tokens de salida | 200 | MEDIDO |
| Sobrecarga medida | +0,332 ms/token (1,33 % del tiempo por token) | MEDIDO |
| Intervalo de confianza | **no disponible**: valores crudos no persistidos | NO CONSTA |

**Las tres limitaciones declaradas, que van en el texto:**

1. Ambos brazos alcanzaron el tope de tokens: se compara en régimen de decodificación pura y **no
   se mide el costo de la gramática en la terminación**.
2. La diferencia en número de tokens es cero por construcción, así que el sesgo «la gramática
   genera menos» no pudo evaluarse.
3. **Solo se conservaron estadísticos resumen, no los valores crudos**, de modo que no hay
   intervalo de confianza. **Es un incumplimiento del propio protocolo, y se declara.**

### Magnitudes generales de la campaña

| Dato | Valor | Marca |
| :--- | ---: | :---: |
| Figuras producidas | 36, más 9 paneles de ausencia | MEDIDO |
| Tablas producidas | 37 | MEDIDO |
| Formatos de exportación por figura | 3, cada uno con compendio propio | MEDIDO |
| Filas de la tabla de procedencia de fuentes | 13 | MEDIDO |
| Filas del manifiesto de figuras | 45 | MEDIDO |
| Filas de la tabla de trazabilidad | 58 | MEDIDO |

---

## 6 · Las tablas que NO tienes que transcribir

Tres tablas del Anexo E ya están generadas y son largas. **No las escribas: deja un marcador.**

| Tabla | Filas | Marcador que debes dejar |
| :--- | ---: | :--- |
| E.3 · Procedencia de los conjuntos de datos | 13 | `[TABLA E.3 — insertar desde tabla_E.3_procedencia_fuentes.md]` |
| E.4 · Manifiesto de las figuras del análisis | 45 | `[TABLA E.4 — insertar desde tabla_E.4_manifiesto_figuras.md]` |
| E.10 · Trazabilidad figura → fuente | 58 | `[TABLA E.10 — insertar desde TRAZABILIDAD.csv]` |

**Sí tienes que escribir el párrafo introductorio de cada una**, que diga qué contiene y qué
columnas tiene. Un marcador sin introducción no le dice nada a quien maquete.

> ⚠️ **E.4 y E.10 se solapan.** El manifiesto de figuras y la tabla de trazabilidad cubren
> parcialmente lo mismo. **Elige una para el anexo impreso y remite a la otra.** Recomendación:
> mantener **E.4** —que incluye tamaño de muestra y condición— y dejar la trazabilidad como anexo
> digital. Decláralo en el texto y en el registro de cambios.

---

## 7 · Lo que NO se toca

| Elemento | Estado |
| :--- | :---: |
| Las entradas actuales de la bibliografía | ✅ **literales, con sus números** |
| Anexo A, todas sus filas actuales | ✅ íntegras; solo se añaden dos |
| Anexo B, validación clínica | ✅ íntegro, sin cambios |
| Anexo C, todo su contenido actual | ✅ íntegro; solo se añade un apartado |
| Anexo D, usabilidad | ✅ íntegro, sin cambios |

---

## 8 · Lo que NO debe aparecer

| Prohibido | Por qué |
| :--- | :--- |
| **Cualquier referencia inventada** | Es el único error verificable en treinta segundos desde la sala |
| Wikipedia, blogs sin autoría, foros | El manual los prohíbe explícitamente |
| Código, ficheros de configuración, volcados JSON | Van al repositorio de control de versiones, que es lo que el manual pide en su Anexo II |
| Datos personales de mascota, propietario o clínica | Verificación obligatoria antes de anexar cualquier traza |
| Análisis o interpretación de los resultados | El anexo respalda; el Capítulo VI analiza |
| Compendios completos de 64 caracteres | Truncar a 16 seguidos de `…`; una tabla de cadenas largas ocupa la página y no aporta |
| Renumeración de las citas existentes | Rompería todas las referencias del cuerpo |
