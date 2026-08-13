# Reunión en General — Transcripción

**Título original:** Reunión en General-20260803_161452-Grabación de la reunión
**Fecha y hora:** August 3, 2026, 8:14PM
**Duración:** 43m 7s

> Transcripción automática convertida desde el documento de Word. Se conserva el contenido original, incluidos posibles errores de reconocimiento.

---

*LISIBONNY EUSTINA BEATO inició la transcripción.*

**CARLOS DAVID HERNANDEZ COLLADO — 0:05**

Bueno, pues.  
Hemos estado trabajando teniendo dificultades a partir del jueves es que y yo pudimos estar libres porque tenemos presentación de otra materia, la cual se nos fue bien y ya este bueno del jueves en adelante está hoy, hemos estado migrando todo porque como nos hemos comentado.  
que teníamos una máquina.  
solamente para GPU pues entonces el enfoque ahora mismo era como que hacer una doble despliegue una parte del sistema iba a estar solamente desplegado en una máquina la cual no tendría GPU y la máquina que tendrá GPU solamente sería para lo que sería el chat LLM porque así  
Porque perdón que está enfermo. el.  
no habría necesidad de tener todo desplegado solamente en la máquina donde está la GPU porque entonces si la si la máquina de GPU no está disponible debido a cualquier razón que pueda ocurrir por ejemplo que los servidores estén llenos que en esa ubicación exacta donde está alojado el servidor no se puede encender etcétera pues no habría necesidad  
de tumbar todo el sistema solamente tumbar el chat LLM y listo entonces el se centró en eso en lo que sea la migración del doble despliegue que ahora mismo ya se está haciendo eso ya las instancias están separadas totalmente  
Y.  
Se ejecutamos test para ver los tipos de respuestas del LLM con respecto a la máquina de la distancia de la GPU.  
Y también se añadió una parte de mapa.  
¿Dónde se ¿Dónde está como?

**LISIBONNY EUSTINA BEATO — 1:53**

Lo que es malo, padre.

**CARLOS DAVID HERNANDEZ COLLADO — 1:56**

Perdón, es que yo tengo la defensa muy bajita, entonces yo he estado trabajando con los que yo puedo. entonces.

**LISIBONNY EUSTINA BEATO — 2:02**

Pero.

**CARLOS DAVID HERNANDEZ COLLADO — 2:05**

Hey.  
¿Qué más en la parte del mapa?  
Se añadió algo que se estaba comentando la semana pasada, que era como que mostrar las veterinarias cercanas al punto de ubicación de este se registró la mascota.

**LISIBONNY EUSTINA BEATO — 2:20**

Sí.

**CARLOS DAVID HERNANDEZ COLLADO — 2:21**

y ya otro detalle sería que si la GPU está apagada el único módulo que no está disponible en el programa es el asistente del chat del LL pero ya todo estaría funcionando solamente no estaría el  
Échate leve.  
Voy a presentar, pero.

**LISIBONNY EUSTINA BEATO — 2:44**

Okey, entonces, pero a ver, ese el principal problema que nosotros teníamos, recuerdo, no era ese.

**CARLOS DAVID HERNANDEZ COLLADO — 2:51**

No, sí, el principal problema era simplemente.  
Sí.  
Perdón, era lo las respuestas que estaba dando, el contexto que estaba recibiendo y todo, o sea, todo con respecto a XNLM. Pero es que hay que tomar en cuenta que al nosotros no haber hecho esta separación en sí, entonces todo se está ejecutando en esta instancia que tenemos acá.  
que si uno entra a ver las especificaciones de esta máquina, esta máquina no tiene nada de GPU entonces tuvimos que centrarnos en esta separación obligatoria para no depender solamente de una máquina para todo el sistema, no sé si me doy a entender, es cierto  
And a second.  
Perdón es cierto de que sí debemos de seguir trabajando con respecto a lo que está respondiendo el LLM que ya con esta migración ya podemos seguir trabajando trabajando tranquilos pero esta era primordial  
Por lo que le estaba comentando, la otra era esto de, por ejemplo, si ya no estamos como tal en un radio de tanto kilómetros, puede buscar un centro de atención veterinaria cercana a este.  
Okay.

**LISIBONNY EUSTINA BEATO — 4:17**

O K, pero a ver a ver.

**CARLOS DAVID HERNANDEZ COLLADO — 4:18**

August.

**LISIBONNY EUSTINA BEATO — 4:20**

Otra vez, otra vez. El problema principal que teníamos era con el asistente, no a nivel de performance, que tengo que ser un tema, pero a nivel de, digamos, no de infraestructura era la prioridad, prioridad, sino de que el chat no estaba dando lo que había que dar.

**CARLOS DAVID HERNANDEZ COLLADO — 4:27**

But.  
Mhm.  
Mhm.

**LISIBONNY EUSTINA BEATO — 4:39**

De que no estaba tomando recordando contexto, se salía de para mí. Yo quiero ver eso primero. ¿Qué se ha hecho en ese sentido?

**CARLOS DAVID HERNANDEZ COLLADO — 4:39**

Yes.  
En ese sentido del jueves hasta hoy, no nos podemos avanzar esa parte, sino que se va a usar en la parte de infraestructura, porque de nada nos valía simplemente estar haciendo todas las mejoras posibles para una máquina en la cual no iba a estar desplegado el modelo o en el chat, porque.  
no va a dar si acaso no va a dar ni el mismo rendimiento y tampoco iba a estar configurado de la misma forma porque si no hubiésemos estado configurando todo con respecto a la instancia que solamente tenía la CPU no iba a ser lo mismo que estar configurando la estudios en la GPU y yo solo puedo comentar eso porque  
Las veces que yo he estado comentando.  
estoy configurando no comentando configurando el LLM máquina local no era lo mismo cuando se estaba desplegando porque máquina local he llegado a funcionar bien pero desplegado no entonces debemos de primero centrarnos en lo que es la prueba de infraestructura para luego sí centrarnos en eso y ya que no tenemos ninguna carga  
Académica en lo absoluto, ya eso ya estaría viendo un poco, vamos, donde yo voy a centrarnos solamente en el problema estructural que teníamos.

**LISIBONNY EUSTINA BEATO — 6:07**

Okey, entonces ustedes vieron que empezaron a trabajar el jueves, no hay grandes avances en este sentido.  
Que las máquinas es lo que entiendo, o sea, olvidado lo otro que ahora ustedes me dirán para cuándo lo vamos a trabajar. Cuéntenme entonces de esta segunda parte.

**CARLOS DAVID HERNANDEZ COLLADO — 6:28**

Con lo respecto al asistente, ya o sea, cerramos este seguimos en este porque es cierto de que vamos a decir que estamos un poco atrasados, pero ya con la.  
No.  
Guau, estoy la esto, la separación que tenemos, ajá.

**LISIBONNY EUSTINA BEATO — 6:52**

Vale, el hombre va a correr en un lado y el resto de cosas va a correr en otro lado.

**CARLOS DAVID HERNANDEZ COLLADO — 6:54**

Sí, pero pero si me perro si me pierde, que yo siento que ni me estoy escuchando guiño con él.

**LISIBONNY EUSTINA BEATO — 7:03**

Y no te puede ayudar ahí, no le puede echar la mano ahí a Carlos.

**CARLOS DAVID HERNANDEZ COLLADO — 7:06**

No, claro, sí, el de hecho fue que avanzó en esta parte de lo que sería la atención veterinaria y yo de mi parte estaba encargándome lo que sería esta separación que de hecho acá.  
Él bueno, vamos a mostrar porque cuando uno entra al chat acá, verdad, él puede funcionar y todo, pero como yo llego a pagar esta instancia.

**EDWIN ANDRÉS BALBUENA BISONÓ — 7:19**

And.

**CARLOS DAVID HERNANDEZ COLLADO — 7:29**

Tenemos esta dirección de la API en donde, bueno, muestra que el chat está ready, probable y demás, pero ya cuando la distancia se apague.

**EDWIN ANDRÉS BALBUENA BISONÓ — 7:32**

So.

**CARLOS DAVID HERNANDEZ COLLADO — 7:39**

Y para que se pague.

**EDWIN ANDRÉS BALBUENA BISONÓ — 7:39**

Entonces, yo tengo que ir a Carlos, sí, estoy aquí en el trabajo, entonces me estaba complicando. No, yo lo quería mencionar es que, por ejemplo, a lo que Carlos se refiere con el tema del modelo, nosotros si aplicamos y si agregamos, por ejemplo, la etiqueta de que si no hay diagnóstico.  
No me lo encuentres, pero tenemos un temita que hay que editarnos los Carlos, o sea, el system prom, en este caso del LN lo editamos y él ahora ahora mismo.  
Está tan sensible que yo, por ejemplo, le pregunto cualquier cosa ahora mismo de, okay, ¿qué patrón autónico tiene esto, que tiene el hemograma? Anteriormente, él podía responder exactamente, dando una respuesta, digamos, concreta diciendo, por ejemplo, tiene... Me llama Héctor.  
Tienes este valor un poquito alto, puede significar que el otro, ya solo habíamos visto, ¿verdad? El problema del contexto. Ahora mismo existen prontas en un punto que cualquier cosa se le encuentra delicada. Ahora mismo tenemos la proporción de que venir a respuestas.  
muchísimo, o sea bastante grave realmente ahora mismo si tu puedes poder prender la máquina acá lo voy a probar. Estábamos haciendo pruebas desde el domingo en este caso con ese system y realmente nos está tomando todo, entonces lo que tenemos que cambiar es justamente ese system prompt para realmente adecuar  
De que si la respuesta del ML está llegando.

**CARLOS DAVID HERNANDEZ COLLADO — 9:15**

y también, disculpa que se interrumpa y también sumándole a eso que está diciendo. yo llegué a meter como que una limitación, pues de una vez, yo llegué a meter una limitación en donde sí está bien pero es que el problema es que tampoco  
Hemos investigado más fuentes en el sentido de que la alimentación que se le puso fue que él no te quiere dar respuestas, él se va a abstener a darte respuestas a menos de que tenga una fuente confiable de para responderte. O sea, cuando uno le preguntaba algo sobre.  
Bueno vamos a limpiar este esto que mide un demograma canina al no tener una fuente confiable el antes él te respondía con respecto a todo lo que sabía el modelo en Sí ahora si no le pregunta esto él simplemente va  
abstener sino decir que ah que no no tengo una fuente confiable para responderte algo por el estilo sí lo veo bien pero por ejemplo para este tipo de preguntas no se recuperó ese documental suficiente para responder esta pregunta Pero él sabe si yo le quitas esa restricción que él tiene con respecto a las fuentes documentales él la podía responder esta pregunta sin ningún problema  
Pero entonces habría que ver o hacer que él filtrase qué preguntas y qué preguntas y cuáles, cuáles y cuáles no, él puede.  
Responder con o sin fuentes, pero bueno, esa es una limitación que se le puso ahora mismo. que.

**LISIBONNY EUSTINA BEATO — 10:51**

Okay, pero es que el problema no era ese. Déjame compartir pantalla. Vamos a ver si nosotros podemos encontrar esa grabación para yo mostrarles que me estoy refiriendo, porque el problema principal que nosotros teníamos era era el tema de cuando ellos estaban analizando.

**EDWIN ANDRÉS BALBUENA BISONÓ — 11:04**

Sí, que no se guardaba la etiqueta.

**LISIBONNY EUSTINA BEATO — 11:12**

Pero ya hemogramas concretos específicos.  
Okay.  
Ok.  
¿Qué pasó aquí ahora?  
Es necesario esto.  
Recordings.  
A ver, yo lo vi a ustedes.  
¿El 27 ustedes son de qué horario? ¿Ustedes son los primeros, verdad?

**EDWIN ANDRÉS BALBUENA BISONÓ — 12:00**

Sí.

**CARLOS DAVID HERNANDEZ COLLADO — 12:01**

Siri.

**LISIBONNY EUSTINA BEATO — 12:01**

Sí.  
Vamos a buscarlo, a ver si recordamos de.  
ya ahí.  
En un segundito chicos, que no tengo mi teléfono cerca.  
Empezar.  
Yo lo voy a dejar a ustedes que me comenten lo que recibí último de ustedes que nos vamos para incompleto o yo voy a estar notificando dicha situación a la profesora Arlin.  
Programa trabaja porque ya lo detallamos un poquito más aquí abajo.  
Hay que avanzar con esto, realmente hay que avanzar con esto para yo poder saber bien el estatus.

**EDWIN ANDRÉS BALBUENA BISONÓ — 13:10**

Realmente, profe, la de la semana antepasada, que habían hablado.

**LISIBONNY EUSTINA BEATO — 13:11**

Sí, una disculpa por eso me dije fue tema.  
De la parte de que el LM se documenta justamente con el.  
Con el Email, lo que sí.  
Creo que no se acuerdo de la batería realmente, entonces lo que lo digo.  
Este.  
Tomás de.  
Logramos en adelante y que tengan consentimiento.  
Esto no se ha procesado, lo último, entiendo, o sea, no hay nada. Eso que por la zona. Exacto, 3 más. Bien, vamos a aprender yo.

**EDWIN ANDRÉS BALBUENA BISONÓ — 14:08**

No, profe, le va a que me escucho.

**CARLOS DAVID HERNANDEZ COLLADO — 14:13**

Profe, Eduel está queriendo decir algo.

**LISIBONNY EUSTINA BEATO — 14:16**

Okay, disculpen, disculpen, vamos a escuchar esta parte, ¿tú me quieres preguntar algo, Edwin?

**EDWIN ANDRÉS BALBUENA BISONÓ — 14:21**

No, está bien, ya me dijo, no le iba a decir que realmente paga esa grabación.

**LISIBONNY EUSTINA BEATO — 14:25**

Sí, se escucha ahí la grabación.

**EDWIN ANDRÉS BALBUENA BISONÓ — 14:30**

Sí, se escucha.

**CARLOS DAVID HERNANDEZ COLLADO — 14:30**

So.

**LISIBONNY EUSTINA BEATO — 14:31**

Vamos a escuchar, vamos a ver esto porque a esto que yo me estoy refiriendo.  
Vamos a preguntarle sobre el historial, vámonos ahí.  
Vamos a ponerle lo como que puedes observar.  
Sobre mi perro.  
En los últimos hemogramas que analizaste.  
Si él tarda en responder, creo que él está en frío. Déjame confirmarlo porque lo había encendido antes de entrar a la llamada.  
Se observa una disminución significativa en el valor de hemoglobina. Este cambio puede ser compatible con una reducción en la capacidad del perro para transportar oxígeno, aunque no confirme una informa específica. Recomiendo que se evalúe este hallazgo con un veterinario para determinar su causa y significado clínico en el contexto general de salud del perro.  
Fundamental, aproximadamente lo veas el resultado es un texto clero completo para una interpretación adecuada.  
Mhm.  
Dice que no confirma una enfermedad específica, okey.  
En los 3 hemogramas.  
2.  
De los 3 en gramos.  
¿Qué?  
So bale.  
Se observa o se diagnósticó.  
Diagnóstico.  
Una condición similar.  
Esto es preocupa porque básicamente lo que noto es que él está viendo.  
O sea, lo quiero entender, los diagnósticos que se le ha dado, él los usa aquí o simplemente los valores sueltos de cada cosa que él mide.  
Él ve todos los valores, él ve los ternásticos per se que tiene cada demograma. Él ve incluso yo creo que la fecha, o sea, él ve muchas informaciones, no tan solo delmograma, sino también de su corpus y demás. Ajá.  
In.  
Los 3 hemogramas.  
Hm, pero solamente en 2, en uno de ellos no se detectó nada, creo recordar.  
Con informatorio, una respuesta al estrés, realmente en el más reciente o también aparecen en menos regenerativo, aunque la condición específica no se diagnostica.  
Los hallazgos son compatibles con el post inflamatorio o estresante sistema evidencia de enfermedad pesca por sí solo.  
Hay posiblemente que ya ha alucinado, creo que si le pregunta cuál es 3 en cada uno era posible que él mismo diga que no.  
Y.  
Le pre que le pregunto, dices, discúlpame.  
No, que entiendo que alucinó ahí, seguramente, entonces lista, me lo voy a decir que me liste los hemogramas. Alítame los patrones en este caso.  
¿Los patrones, sí, porque lo que tiene activamente la las etiquetas bien cuáles?  
En cada uno de los que logramos.  
De los 3 morados con él.  
No se proporcionan fechas específicas para cada estudio. Los hechos clínicos autorizados se registran 3 con valores de hemoglobina, hematocritos y ozinófilos.  
Pero las fechas exactas no está disponible en este turno, no se pueden estar los patrones por fecha, se recomienda que un veterinario.  
Interprete los cambios junto con la colección clínica.  
Lístame entonces o en vez de eso, las condiciones detectadas en cada.  
Déjame ver qué pasó en el servidor.  
Problema ahí.  
Dime las condiciones detectadas.  
Ariel se quedó.

**EDWIN ANDRÉS BALBUENA BISONÓ — 20:32**

Por.

**LISIBONNY EUSTINA BEATO — 20:33**

Vamos a seleccionar.  
Ajá, porque esto es lo que yo digo. Fíjense que sí, o sea, en 2 hay patrones inflamatorios, pero en este no hay nada. Vamos a hacerle una pregunta de este.  
¿En este hemograma ves algún problema con mi perro?  
Sí.  
Se recomienda una valoración veterinaria completa con los signos.  
Clínicos y antecedentes del perro para interpretar estos resultados. Él está viendo unos rangos altos aquí. Entonces, lo que me lo que me da a entender esta respuesta.  
Es que él no está viendo el diagnóstico, aunque ustedes me dicen que se lo están pasando.  
El diagnóstico él no lo está viendo.  
Porque dice que no hay patrones hematológicos fuera de rango y que o sea como que está todo bien, pero en realidad él sí está viendo algo que está mal.  
O sea, lo que sucede es que los patrones se detectan a través de la expresión de los valores, aunque hayan valores altos o rangos, dentro de las etiquetas que nosotros manejamos no apareció un patrón específico. Sí, yo lo entiendo perfectamente, pero entonces lo que estoy diciendo es que él no está viendo esta etiqueta de aquí.  
Porque él sí, lo que a mí me está diciendo, el lo que él me sugiere, lo que él está diciendo es que hay un problema.  
Porque yo lo que le estoy preguntando.  
¿O puedo hacerlo más sencillo, cuál es el diagnóstico?  
¿Los ¿Cuáles diagnósticos ves el temorama? ¿Cuáles diagnósticos?  
Este.  
Se observan en este hemograma.  
O sea, si ustedes le estuvieran pasando el diagnóstico per se rápidamente lo conseguiría, pero parece que no el estar viendo simplemente los valores aislados.  
Ya porque yo lo que pienso es si ya se analizó y aunque haya valores fuera de rango como esto que él me está diciendo aquí, pero ya se dijo que no hay problema, es lo que debería decir, no observo ningún problema.  
No dame esto porque esto lo consigo yo visualmente yéndome al hemograma en el historial. No sé si me explico. Sí, prueba, sí, prueba con uno que tenga.  
Claro, entonces confirmen esa parte por porque yo lo que veo es que el diagnóstico per se él no lo está viendo, o para mí tendría mucho interés si él ve el diagnóstico y quizás sí se alimenta un poco de información sobre ese tipo de diagnóstico y ya si haga.  
digamos cruces con los datos aquí específicos. Pero si el hemograma me dice que no hay un problema, yo debería decirlo, aunque él me diga esto, mira, aunque estos valores están fuera de rango, el modelo cuando analizó indica que no ve nada de peligro, porque ahora mismo lo que yo veo o lo que yo pensaría  
Mira, el modelo me dijo que está bien, que no ve nada raro, pero entonces aquí este me está asustando y me está diciendo que sí hay algo. Entonces, por ninguna parte él menciona el hecho de que ustedes mismos en el modelo dijeron que no había nada preocupante.  
No sé si eso queda claro, sí queda claro lo que.  
No entiendo por qué la está alucinando, porque incluso en el historial demograma, o sea, el sí saca el.  
O sea, la opción de historial es y sacar a el diagnóstico de lo del contexto de lo que sea los hemogramos, pero.  
Sí, claro, eso hay que revisarlo, eso debería revisarlo. Él pierde el historial, es lo que yo estoy viendo, verdad? Después que yo me voy de aquí, el pierde el historial de conversación que yo tenía. Ah, claro, cada vez que usted inicia o se recarga la página o le da o selecciona otro otro modo, el directamente borra lo anterior.  
¿Cómo ustedes ven eso? Es viable que le han dicho a los usuarios al respecto.  
¿Han dicho alguna respecto? De la encuesta, no voy a ver si alguien no, voy a ver si alguien más lleno, pero de los datos que teníamos antes no.  
Déjenme ver, obligación usabilidad.  
Mm.  
Okay, yo creo que eso entiende la idea a que yo me refiero, ¿verdad que sí?

**CARLOS DAVID HERNANDEZ COLLADO — 26:03**

Claro, sí, sí.

**EDWIN ANDRÉS BALBUENA BISONÓ — 26:05**

¿Qué es Santiana?

**LISIBONNY EUSTINA BEATO — 26:05**

O K, entonces en relación, esa es mi pregunta.

**EDWIN ANDRÉS BALBUENA BISONÓ — 26:12**

Bien, le va a comentar, va a pesar los últimos cambios que hicieron. Al parecer, por culpa de ambos fuimos un cambiecito, que estoy a ver si lo he abierto un momento, que es que la respuesta.  
Del modelo tiene que estar sí o sí relacionada a un diccionario a un Corpus, lo cual pensando en ahora no siempre debería ser así, por eso que ahora mismo el.  
Prácticamente no lo quieren responder nada, entonces estoy viendo ciertos de cambio de una vez ahora mismo, eso por una parte.  
Pero sí, la parte de cosas que habíamos hablado ahí en la reunión de que realmente uno estaba manteniendo el histórico, manteniendo el contexto, ahora mismo no podemos demostrarle de que funciona un canal o mencionado, ni siquiera quiere responder el amiguito.

**LISIBONNY EUSTINA BEATO — 27:10**

Pero ustedes no, o sea, ustedes no se acordaban que habíamos hablado de esto o lo tienen pendiente.

**EDWIN ANDRÉS BALBUENA BISONÓ — 27:16**

No, nosotros tenemos la parte de del contexto solucionado.  
Porque como le dije, agregamos la variable de que si no tiene primero, si no tiene una etiqueta, no lo mencionas. Y segundo, le aumentamos el contexto, lo que guarda la el modelo y aparte también lo tenemos guardamos en una base de datos, aquel cual leer esa conversación y tener el histórico.

**LISIBONNY EUSTINA BEATO — 27:39**

O sea que se confirma, se confirma que ustedes no le estaban pasando al asistente lo que el modelo estaba diciendo.

**EDWIN ANDRÉS BALBUENA BISONÓ — 27:40**

Um.  
Sí.  
Exactamente, si esa si se la puedo confirmar 100% no la teníamos realmente. Incluso tampoco teníamos el tema ese de una clasificación de que si no aparecía lo clasificará como que no tenía nada. Eso sí lo puedo confirmar.

**LISIBONNY EUSTINA BEATO — 27:56**

Claro, porque digamos que su alimentación no es el PDF del hemograma, debe ser los resultados del modelo.

**EDWIN ANDRÉS BALBUENA BISONÓ — 28:01**

No.  
Except.

**LISIBONNY EUSTINA BEATO — 28:08**

Que es obviamente si hay alto bajo, pero también el diagnóstico y cualquier cosa que el modelo haya dicho.

**EDWIN ANDRÉS BALBUENA BISONÓ — 28:14**

Sí, eso sí se lo confirmo de que no era problema de del LLM como tal, sino problema nuestro por nunca realmente haberle pasado esa información. Entonces déjenme ver si la máquina no dura 10 minutos subir.  
Get up.  
¿Qué?  
Bien.  
Y a ver si no la vida Australia.  
A.  
Ok, ahí está subiendo la máquina entonces en lo que sube vamos a pasar realmente a los documentos por lo menos que vayan a motivar  
Ajá.  
No.  
Me avisan.  
No.  
Sure.  
Sí.  
Llamar.  
Set a minute.

**LISIBONNY EUSTINA BEATO — 30:07**

Seven.

**EDWIN ANDRÉS BALBUENA BISONÓ — 30:09**

Ok, en lo que la máquina sube, que está aquí, ya se está calentando por lo menos GCP cuatro mirados, nosotros también tenemos que haber cambiado el documento.  
Por lo menos la parte de la arquitectura, es decir, el diseño como tal.  
No sé, profe, si usted nos pudo confirmar el tema de.  
¿Cómo se llama?  
Oh.  
El tema profe de colemia por WhatsApp, ayer, no me pongo diagramas.

**LISIBONNY EUSTINA BEATO — 30:46**

Hablé ayer con ellos, los bueno, yo estoy en un grupo de los el comité de proyectos y nadie me dijo a mí nada de que sabía de ese tema. O sea, como que nadie había hecho ese comentario. Fue lo que yo entendí. O sea, que yo les diría que sí, manténganlo así, no tiene ningún sentido no hacerlo.

**EDWIN ANDRÉS BALBUENA BISONÓ — 30:53**

Mhm.  
Okay.  
Okay, vamos.

**LISIBONNY EUSTINA BEATO — 31:10**

No veo, o sea, si es como ustedes me explican, eso es correcto, se puede hacer. De hecho, por eso existe la opción de hacerlo, que tú puedes hacer secciones en el documento y alguna página ponerla horizontal.

**EDWIN ANDRÉS BALBUENA BISONÓ — 31:23**

No.  
Pues.  
Bueno, tendríamos que cambiar esto nuevamente, pero lo que hicimos fue que lo habíamos colocado un poquito más el lenguaje ya, por tanto, técnico, por ejemplo, cambiamos este en el diagrama funcional, cambiamos también el flujo, es decir, la ingesta, porque por ejemplo, anteriormente no tendríamos que este de la ingesta, o sea, lo que extrae los valores PDF en este caso.  
del análisis nosotros teníamos que él realmente primero hacer una extracción con PF plumber  
que eso sí era en el proyecto, pero ahora realmente lo primero que le extrae con Gemini, si no funciona con Gemini, él usa auto en router por otros modelos, que por qué pasamos de ocr normal a un modelo, por la sencilla razón de que en este caso se habilitó que el usuario pueda subir algo más componente.  
si yo subo una foto no lo voy a tener lo mismo con el tema de los datos lo pusimos un poquito más sencillo vamos a tener conversación el mensaje intercambio o sea nos llevamos algunos de los comentarios porque no había mencionado hace tiempo de no poner todo tan técnico  
no todo tan complejo y que fuese fácil de plantar algo  
Por ejemplo, aquí he tomado lo mismo con caso de uso.  
¿Cómo realmente el modelo funciona? La parte te lo pidió documentarlo, qué tipo de consulta permiten, cuáles no permiten, cuáles son los rechazos, si quieren el modelo no.  
De la arquitectura también quedó un poquito más simple.  
Como le dije, todos están en el tema de dictar y yo posiblemente los otros cables yo lo vamos a editar para que sean más explicativos, pero si llegan a ocupar la página completa cuando tengamos ante el proyecto, se entienden un poquito más. ¿Qué nosotros tenemos que cambiar el documento todavía?  
Cuando si el modelo realmente esté completamente seguro, no hay problema con su bien. Cuando si el modelo esté completamente seguro, nuestra idea se va a ejecutar, que ya eso se va a tener esta semana. Entre esta semana es la siguiente.  
Aparte de una batería automática que simplemente va a volar el tiempo de respuesta, hacer nuevamente lo que teníamos con los médicos, que era lo de los CSV, en este caso, creo que está aquí abajo, o sea, esta este.  
Ajá.  
Bueno, por ejemplo, estas tablas que teníamos de Pro Injection que pasan automática, hacerlas nuevamente y las cuotas que teníamos con los médicos de los evaluadores de lo que ya nos comentaron a esos mismos de cuáles son positivos, cuáles son negativos, que realmente el modelo está diciendo bien, que está encima mal. Nuestra idea es hacerlo nuevo ya con esta versión final del LLM.  
Pero con una mucha menor cantidad, por ejemplo, esta fue hecha con aproximadamente.  
Así como 400 muestras, no me acuerdo como 200 300, pero la idea es hacerlo por tema de tiempo, realmente una versión reducida, pero la idea válida realmente los productos finales que tengamos.  
Er.  
Realmente es eso, según leyendo algo de azul, se acostado loco.  
Pero lo que nos falta, lo que nos falta sería principalmente son los resultados de las conclusiones, una vez realmente sí se estrena la velocidad.

**LISIBONNY EUSTINA BEATO — 35:01**

Okay.  
Okey, mire, ese documento yo lo quiero listo.

**EDWIN ANDRÉS BALBUENA BISONÓ — 35:13**

Yeah.

**LISIBONNY EUSTINA BEATO — 35:14**

Para el día.  
14 como tarde para yo tener el tiempo de revisarlo y que ustedes lo puedan subir. Yo llegué hasta el 12, miércoles 12, pero eso no me preocupa, ahora me preocupa como les digo.  
El asistente que no veo que, o sea, no veo que se le haya hecho ningún cambio. ¿Cuándo ustedes planifican meterse con esto? Porque si ponemos el 12 porque se lo puse a otro grupo como fecha de entrega del documento.

**EDWIN ANDRÉS BALBUENA BISONÓ — 35:34**

Mhm.  
O.  
Can.

**LISIBONNY EUSTINA BEATO — 35:50**

Yo no puedo esperar el lunes para verlo a ustedes.  
Porque lo va a poner incompleto si sigo viendo en incompleto transferido, lo va a mandar transferido si sigo viendo que no hay avance. Yo quiero ver esta semana otra vez verlo a ustedes y que ustedes me muestren por lo menos que ya es existente. Puede identificar cosas básicas que no identificaba como lo que nosotros acabamos de ver en el video.

**EDWIN ANDRÉS BALBUENA BISONÓ — 36:05**

Ya.

**LISIBONNY EUSTINA BEATO — 36:14**

O sea, en el top de prioridad, yo entiendo que la parte esta de.  
Infraestructura es importante, pero es que si ese, o sea, ahora mismo ese asistente es mejor que ni este. Si les digo la verdad, ustedes se beneficiarían de quitarlo.  
Sin embargo, es uno de sus objetivos según lo que ustedes plasman, pero ahora mismo no, él no está dando nada significativo. Entonces la pregunta es, ¿qué prioridad ustedes le van a dar en eso que ahora mismo está en un estado que no es aceptable para proyectar?

**EDWIN ANDRÉS BALBUENA BISONÓ — 36:48**

Yes.  
De una vez no le iba a comentar como dijo Carlos, que salimos generalmente de todo, pues ya que tenemos también la estructura correcta para poder probar el modelo de que sí es rápido.

**LISIBONNY EUSTINA BEATO — 36:52**

Okay.

**EDWIN ANDRÉS BALBUENA BISONÓ — 37:04**

Prácticamente, como le dije, arreglar el system prompt y ya así probar y formalizar. O sea, ya realmente si le tengo que poner fecha y no tiene problema, yo no te diría, podemos lo mismo y ya veredicto.  
Sí.  
A.  
O.

**LISIBONNY EUSTINA BEATO — 37:20**

Hay que darle prioridad número uno a esa parte. Chicos, no quiero esperar al lunes a verlo, no quiero esperar al lunes a verlo porque es que si es para el lunes siento que no voy a ver avances porque siento que no le han dado la importancia que se merece esta parte. Y como les digo, si esto no mejora, yo no le voy a decir presente, por mi parte no va a tener la aprobación. O sea, para mí eso es.

**EDWIN ANDRÉS BALBUENA BISONÓ — 37:23**

I said.

**LISIBONNY EUSTINA BEATO — 37:42**

Bastante significativo que yo pueda tener por lo menos esas mínimas conversaciones que yo estoy, estoy intentando tener desde hace 2 semanas con el asistente de dime qué pasó con todo estos 3 cómo tuve el la evolución.  
Y no puedo, no he podido tenerlo.  
¿Entonces díganme ustedes cuando yo lo vuelvo a ver esta semana para yo realmente ver avance en esa parte?

**EDWIN ANDRÉS BALBUENA BISONÓ — 38:16**

Le comenté si no tenía problemas del viernes.

**LISIBONNY EUSTINA BEATO — 38:20**

El viernes no viernes muy tarde.

**EDWIN ANDRÉS BALBUENA BISONÓ — 38:21**

What?  
A.  
Jueves en 2.

**LISIBONNY EUSTINA BEATO — 38:27**

Bueno, ustedes escríbanme el miércoles ustedes.

**EDWIN ANDRÉS BALBUENA BISONÓ — 38:27**

a hacer arroz.

**LISIBONNY EUSTINA BEATO — 38:34**

Escríbanme el miércoles y yo les digo la hora del jueves.  
Y disculpa que es que yo casi no te escucho Edwin porque tú no sé si te pasa a ti Carlos, pero yo te escucho como lejos Edwin, no sé y hay como que mucho ruido detrás, no sé si el micrófono no sé exactamente.

**EDWIN ANDRÉS BALBUENA BISONÓ — 38:53**

Sí, le iba a comentar que es que aquí andan en obras.  
por eso está hablando un poquito bajito de parte no no sé si somos de economía o computadora pero si el primer fondo ganamos en otra

**LISIBONNY EUSTINA BEATO — 38:58**

Es.  
Okey, entonces, ¿cuál jueves que yo voy a tener en ese sentido?

**EDWIN ANDRÉS BALBUENA BISONÓ — 39:13**

como mínimo un modelo funcional como mínimo porque es la opción  
O sea, es lo que estamos esperando realmente, como mínimo el modelo funcional en este caso, que como ya hemos prometido y hemos hablado durante todo el ciclo, para el contexto, tenga las etiquetas del ML y sepa diferenciar realmente entre una pregunta.  
Clínica orientativa informativa a un diagnóstico, porque es el último problema que estamos teniendo que es el último system prompt, pues está hablando todo como si fuese una un diagnóstico, cuando no debería ser así. entonces.

**LISIBONNY EUSTINA BEATO — 39:55**

Okay.

**EDWIN ANDRÉS BALBUENA BISONÓ — 39:58**

Yeah.

**LISIBONNY EUSTINA BEATO — 40:02**

A ver, no vamos a hacer eso. Yo le yo quiero volverlo a ver esta semana, no lo quiero ver el lunes porque es que me es mucho tiempo y yo quiero ver realmente algún avance en ese sentido, porque como le digo, vengo el lunes y seguimos así, lo voy a mandar a IT y no quiero hacerlo, no quiero hacerlo porque ustedes han avanzado en otras partes bien, pero es como le digo, este es un objetivo muy importante que ustedes se plantearon.

**EDWIN ANDRÉS BALBUENA BISONÓ — 40:03**

Y.  
Ya.

**LISIBONNY EUSTINA BEATO — 40:24**

Y de manera mínima no me está cumpliendo con nada. O sea, ahora mismo lo que él da lo puedo yo ir a ver a cada hemograma directamente. No tengo que tener una LLM para eso.

**EDWIN ANDRÉS BALBUENA BISONÓ — 40:39**

Hola.

**LISIBONNY EUSTINA BEATO — 40:42**

Entonces tenemos que dar algo que vaya más allá, que realmente va a haber trabajo. Yo en un momento en lo que comenté a ustedes que hablaran con el grupo de los estudiantes de sus compañeros que ya presentaron. No sé si ustedes tuvieron oportunidad de conversar con ellos.

**EDWIN ANDRÉS BALBUENA BISONÓ — 40:54**

The llamas.  
Hola.  
No pregunto.  
Mhm.

**LISIBONNY EUSTINA BEATO — 41:05**

No sé si ellos están disponibles ahora, ya quizás complicado, pero.  
No sé, no estaría mal que ustedes a lo mejor no, obviamente que ellos le hagan el trabajo, pero les mostraran un poco lo que ustedes quieren hacer y ver si ellos le pueden dar orientar un poquito de por la línea por la que ustedes pudiesen quizá explorar soluciones, aunque ustedes me dijeron que ya ustedes tienen un poquito más de estructura en la data que le están alimentando a los LLM.  
Entonces, por lo menos ya que ustedes tienen eso más claro.  
Hacerlo y que yo pueda ver.  
Hi.  
Okay.  
¿Queda claro?

**EDWIN ANDRÉS BALBUENA BISONÓ — 41:52**

Say super claro.

**LISIBONNY EUSTINA BEATO — 41:56**

Yeah.  
Claro, Carlos.

**CARLOS DAVID HERNANDEZ COLLADO — 42:00**

Sega, sega column.

**LISIBONNY EUSTINA BEATO — 42:02**

Entonces van, vamos a enfocarnos ahí esta semana, quiero verlos, quiero ver avance ahí, quiero que poder por lo menos preguntarle cosas básicas y que me diga algo, porque si no lo que nosotros, o sea fácil, una persona coge y se entra en Google a buscar una definición, para eso no necesito una LL.  
Lo que sí necesita es.  
Poder.  
Conversar de manera natural sobre hemogramas reales concretos de su perro, de su mascotas, que ahora mismo no pasa.  
Entonces vamos a darle ahí. Evalúan la posibilidad de ver si sus compañeros pueden darle quizás alguna orientación sobre cómo mejorar algún aspecto. Pero hay que ponerse a mano la obra, me escriben el miércoles y yo.  
Le reservo hora para el voa y si estamos listos.

**CARLOS DAVID HERNANDEZ COLLADO — 42:59**

Entendido.

**EDWIN ANDRÉS BALBUENA BISONÓ — 43:00**

A ver.

**LISIBONNY EUSTINA BEATO — 43:00**

Yeah.  
Se le antes, me van dejando saber ahora.

*LISIBONNY EUSTINA BEATO detuvo la transcripción.*
