# Guion de las dos secciones nuevas

> Los datos están en `02_HECHOS_VERIFICADOS.md` §3 y §4. Aquí está **la arquitectura narrativa**:
> qué va en cada párrafo y en qué orden, para que las secciones tengan hilo y no sean una lista de
> hechos encadenados.

---

# §5.8 · Cadena de release y contrato de runtime

**Extensión:** ~2 páginas · 900–1 100 palabras · una tabla (5.10) y opcionalmente la 5.11.

## Idea que la sección debe dejar

> El sistema no se despliega copiando ficheros: se despliega aplicando un contrato firmado, y si
> la máquina no coincide con el contrato, no arranca.

## Estructura párrafo a párrafo

**Párrafo 1 — El problema que resuelve.**
Abre con la necesidad, no con la solución. Un sistema con inferencia sobre hardware acelerado
tiene una superficie de fallo que un despliegue convencional no cubre: el modelo servido puede no
ser el previsto, el controlador puede no coincidir, el hardware puede haber cambiado. Ninguna de
esas tres condiciones se manifiesta como un error visible — el servicio **responde igual**, con
otro modelo. De ahí la decisión de construir una cadena de despliegue verificable.

**Párrafo 2 — La topología.**
Dos nodos con responsabilidades separadas *(datos en §3.8)*. Por qué se separan: aislar el
componente caro y frágil del resto, de modo que su indisponibilidad no arrastre al análisis
hematológico. Menciona la dirección interna estática y por qué importa: hace transparente el
reemplazo del hardware.

**Párrafo 3 — El manifiesto como contrato.**
Qué fija y por compendio criptográfico *(datos en §3.1)*. La idea a transmitir: el manifiesto es
el contrato entre lo que se construyó y lo que se ejecuta. Introduce aquí la **Tabla 5.10** con
una frase del tipo «la Tabla 5.10 recoge los campos del contrato correspondiente a una versión
desplegable».

**Párrafo 4 — La validación de arranque.**
Las dos capas independientes, qué comprueban, y la decisión de diseño que las gobierna: si algo
no coincide, **el nodo se apaga**, no opera degradado *(datos en §3.4)*. Explica por qué apagar es
preferible a degradar: un servicio que responde con el modelo equivocado es peor que un servicio
que no responde, porque el error es silencioso.

**Párrafo 5 — La reversión.**
Automatizada, mantiene activa la validación, cubierta por pruebas de contrato *(datos en §3.5)*.
Breve: dos o tres frases.

**Párrafo 6 — La migración como prueba no planificada.**
🔴 **Es el mejor párrafo de la sección y el que el manual pide explícitamente** («si hay alguna
modificación, debe de explicarse y justificar el por qué»). La cadena de validación estaba anclada
al hardware anterior y **apagó la máquina dos veces**, comportándose exactamente como estaba
diseñada. Se amplió el contrato, se regeneró el manifiesto, se instaló el paquete por intervención
sobre el disco fuera de línea, y el backend no requirió ninguna modificación *(datos en §3.6)*.

Escríbelo sin dramatismo y sin disculpa: es la evidencia más directa disponible de que el
mecanismo de protección funciona.

**Párrafo 7 — El incidente de capacidad zonal.**
Declararlo como desviación *(datos en §3.7)*. Dos frases. No lo conviertas en una lamentación ni
en una recomendación — la recomendación va al Capítulo VII.

**Cierre.**
Una frase que enlace con lo que viene: la cadena de despliegue es la que permitió sustituir el
*runtime* conversacional, cuya evolución funcional se describe a continuación.

---

# §5.9 · Evolución del asistente: rondas 4 a 6

**Extensión:** ~2,5 páginas · 1 100–1 400 palabras · una tabla (5.12).

## Idea que la sección debe dejar

> Una respuesta puede pasar todas las validaciones de seguridad y no contener nada. El sistema no
> lo detectaba, una batería externa lo expuso, y las cuatro causas estaban localizadas en el
> código.

## Estructura párrafo a párrafo

**Párrafo 1 — El vacío que ninguna batería medía.**
Las validaciones existentes comprobaban que la respuesta fuera segura, robusta ante errores
ortográficos y consistente en sus fuentes. Ninguna comprobaba que **contuviera algo**. Introduce
el criterio nuevo: descontar la frase de derivación, las cláusulas de incapacidad y el eco de la
pregunta, y verificar que queda contenido verificable.

**Párrafo 2 — Lo que midió la batería.**
13 de 45 turnos con contenido real, 0 de 15 en el modo historial, y turnos con código de éxito que
contenían solo la derivación *(datos en §4.1)*. Menciona que la batería se verificó como válida
antes de aceptar sus conclusiones — es lo que hace defendible actuar sobre ella.

**Párrafos 3 a 6 — Los cuatro mecanismos.**
Uno por párrafo, o una lista numerada introducida por una frase completa *(datos en §4.2)*. Lo
importante: **son mecanismos, no síntomas**. Cada uno explica *por qué* el sistema producía el
comportamiento observado. El primero es el más interesante y conviene desarrollarlo algo más: el
requisito de derivación se satisfacía por construcción precisamente cuando la respuesta era solo
la derivación — una validación que se cumplía sola.

**Párrafo 7 — La puerta de contenido.**
Qué es y qué descuenta *(datos en §4.3)*. Corta.

**Párrafos 8 y 9 — El completado determinista.**
🔴 **Es el aporte de ingeniería más sustantivo de la sección.** Empieza por el principio rector,
que conviene citar como decisión de diseño: *todo lo que la base de datos ya sabe se responde
desde la base de datos, y se arregla solo la parte dañada de la respuesta, nunca se regenera
entera*. Luego enumera qué sale por código *(la lista de §4.3)*. Cierra con la consecuencia: buena
parte de las respuestas se resuelven sin generación, a costo de cómputo nulo, y se verifican con
los mismos comparadores que emplea el validador de salida.

**Párrafo 10 — Elipsis y reparación compacta.**
Los dos mecanismos juntos *(datos en §4.3)*. Destaca la guarda de raíz: negar la derivación o
declarar una incapacidad falsa obliga a reescribir entera, porque completarla enmascararía el
error.

**Párrafo 11 — Instrumentación.**
Telemetría de la verificación de citas y poda de disco por presión *(datos en §4.3)*. Breve. La
segunda se justifica por dos incidentes reales de disco lleno: decláralos.

**Párrafo 12 — La evolución medida.**
Introduce la **Tabla 5.12** *(datos en §4.4)*.
⚠️ **Aquí es donde es más fácil romper la Regla 1.** Presenta la tabla como registro de la
evolución de la construcción. **No calcules porcentajes de mejora, no digas que fue exitosa, no
interpretes.** Cierra remitiendo: «el análisis del comportamiento resultante se presenta en §6.8».

**Párrafo 13 — La clase residual.**
🔴 **No omitir.** Los cuatro o cinco turnos flojos por corrida son una clase de fallo conocida,
documentada y **no resuelta** *(datos en §4.5)*. Añade el matiz que la evidencia sostiene: el
modelo se conservó entre rondas y, cuando responde, es exacto — las fallas eran del sistema.

Una sección que termina declarando lo que no se resolvió es más creíble que una que termina
celebrando. Ese es el efecto que se busca.

---

## Cómo enlazan con lo que ya existe

- §5.7 (pruebas y despliegue) queda **antes** de las dos secciones nuevas. Si contiene material
  que ahora pertenece a §5.8, muévelo y déjalo señalado en el registro de cambios.
- §5.5 (módulo LLM/RAG) describe la **arquitectura** del asistente. §5.9 describe su **evolución**.
  No repitas la arquitectura: remite a §5.5.
- §5.10 (la síntesis, antes 5.8) debe ampliarse para recoger ambas secciones nuevas en una o dos
  frases. Hoy no las menciona porque no existían.
