# generar/ — paquete autocontenido para reescribir el Capítulo IV

Todo lo necesario para que un LLM produzca el **Capítulo IV completo**, con el diseño de
despliegue y el del módulo conversacional al día, y te lo devuelva listo para pegar en Word.
**No requiere acceso al repositorio:** los datos están dentro.

---

## Cómo se usa

1. Abre una conversación nueva con un LLM capaz (ventana de contexto amplia).
2. Pega los archivos **en este orden**, cada uno precedido por su nombre en una línea:

```
00_PROMPT_MAESTRO.md          ← quién eres, qué produces, las tres reglas
01_TEXTO_ACTUAL.md            ← el Capítulo IV íntegro tal como está hoy
02_HECHOS_VERIFICADOS.md      ← los párrafos de diseño ya redactados
03_ESTILO_Y_FORMATO.md        ← registro, terminología, números, figuras
04_GUION_SECCIONES_NUEVAS.md  ← dónde encaja cada pieza y la prueba de altitud
05_CONTRATO_DE_SALIDA.md      ← qué devolver y checklist de verificación
```

3. Cierra con: **«Produce ahora el Capítulo IV completo según el contrato de salida.»**

Son ~8 500 palabras en total: entra en una sola petición. Es el paquete más pequeño de los nueve.

## Qué te devuelve

Un documento continuo en Markdown —el capítulo entero, no parches— más cuatro bloques: registro de
cambios, marcadores pendientes, inventario de figuras e inconsistencias detectadas.

**Para pasarlo a Word:** copia el Markdown, pégalo en un editor que lo renderice (el visor de
Markdown de VS Code, Typora, o cualquier conversor en línea), copia lo renderizado y pégalo en el
`.docx` **con formato**. Después aplica el `CHECKLIST_FORMATO.md` de la guía general.

---

## Qué contiene el paquete

| Archivo | Palabras aprox. | Contenido |
| :--- | ---: | :--- |
| `00_PROMPT_MAESTRO.md` | 1 000 | El encargo, el diagnóstico del capítulo y las tres reglas |
| `01_TEXTO_ACTUAL.md` | 2 990 | El Capítulo IV verbatim del `.docx (4)` |
| `02_HECHOS_VERIFICADOS.md` | 1 800 | Los siete párrafos de diseño ya redactados, las filas de tabla y la corrección de la figura |
| `03_ESTILO_Y_FORMATO.md` | 880 | Registro, traducción de anglicismos, referencias de figura |
| `04_GUION_SECCIONES_NUEVAS.md` | 1 200 | Dónde encaja cada pieza, en qué orden, y la prueba de altitud |
| `05_CONTRATO_DE_SALIDA.md` | 1 000 | Formato de entrega, cuatro bloques y checklist de 31 puntos |

---

## El diagnóstico, en una frase

**El análisis está sano; al diseño le falta lo que se construyó en agosto.**

§4.1 —actores, casos de uso, requerimientos— describe el sistema real y no se toca. §4.2 tiene un
hueco importante: **el despliegue en dos nodos, el manifiesto de versión y el arranque a prueba de
fallos existen en el código y no en el papel.** Y el diseño del módulo conversacional se quedó en
la cadena de julio, sin las tres piezas que en agosto cambiaron su comportamiento de forma
sustantiva.

Hay además una referencia cruzada rota con **tres versiones distintas del mismo título de figura**:
una en el cuerpo, otra en el pie y otra en la Lista de Figuras.

---

## Las tres reglas, en corto

1. **El Capítulo IV describe diseño; el V describe construcción.** Cada párrafo nuevo debe poder
   leerse como una decisión de diseño con su razón, no como el relato de cómo se llegó a ella.
2. **Ninguna cifra sin respaldo.** Este capítulo apenas necesita cifras, y esa escasez es correcta.
3. **El diseño no tiene fechas.** Nada de «en agosto se incorporó». Presente y estado.

---

## El riesgo real de este encargo

**Que el modelo escriba el Capítulo V.**

El material de las cuatro piezas del módulo conversacional viene de una historia de desarrollo:
hubo baterías, hubo rondas, hubo problemas detectados y corregidos. Es material narrativo y se
cuenta solo. Pero **esa narración es §5.10**, y duplicarla aquí no solo rompe la altitud del
capítulo: hace que el documento cuente lo mismo dos veces con dos niveles de detalle distintos, y
el comité lo lee como descuido.

Los párrafos de `02` **ya están escritos en clave de diseño** —propiedades e invariantes, no
episodios— precisamente para eliminar ese riesgo. El trabajo del modelo es colocarlos sin
«enriquecerlos».

**Hay una excepción autorizada y solo una:** los dos apagados de la máquina durante la migración,
en §4.2.5. Están en pasado porque son la evidencia de que la política de arranque a prueba de
fallos opera. Un mecanismo de protección que nunca se ha disparado es una declaración de
intenciones.

---

## Antes de dar por bueno lo que te devuelva

1. Busca «se detectó», «ronda», «posteriormente», «en agosto». **No pueden aparecer**, salvo en el
   párrafo del apagado.
2. Busca cualquier latencia o porcentaje. **No debe haber ninguno**: son del Capítulo VI.
3. Verifica que la referencia del cuerpo de §4.2.5 dice **Figura 4.6**, no 4.5.
4. Verifica que la cifra de módulos de §4.2.6 **coincide** con la de §4.2.1. Son doce en ambas, y
   una discrepancia dentro del mismo capítulo es de lo que más fácil encuentra un lector atento.
5. Comprueba que la Tabla 4.4 conserva **todas** sus filas anteriores además de RNF-07 y RNF-08.
6. Lee los párrafos nuevos preguntándote si describen cómo es el sistema o cómo llegó a serlo. Si
   cuentan una historia, devuélveselo.

Si alguna falla, devuélveselo señalando el punto concreto en lugar de corregirlo a mano.

---

## Lo que este paquete NO cubre

**El diagrama de despliegue.** El manual pide explícitamente un diagrama de despliegue para esta
titulación, y la figura actual es una captura de pantalla. El resultado traerá el marcador
`[FIGURA PENDIENTE 4.7]` con su pie redactado, pero **dibujarlo es trabajo aparte**. Debe mostrar
los dos nodos, la dirección interna estática, el flujo de validación de arranque y la rama de
apagado ante fallo.

**La unificación del título de figura en la Lista de Figuras.** El paquete corrige el cuerpo y el
pie; el tercer sitio —la Lista de Figuras— se arregla al final, con los preliminares. Ver
[`../../01_preliminares/generar/`](../../01_preliminares/generar/).

---

## Coordinación con el Capítulo V

§4.2.4 y §5.10 describen **lo mismo a dos alturas distintas**: aquí, las cuatro piezas de diseño
como propiedades del sistema; allí, la evolución del asistente que las produjo.

Hazlos con esa división en mente. Si al leer los dos capítulos seguidos te encuentras la misma
explicación dos veces, la que sobra es la de aquí: el Capítulo IV es el que tiene que ser breve.
