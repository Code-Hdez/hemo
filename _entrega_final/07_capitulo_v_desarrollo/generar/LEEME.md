# generar/ — paquete autocontenido para reescribir el Capítulo V

Todo lo necesario para que un LLM produzca el **Capítulo V completo**, corregido y con las dos
secciones nuevas, y te lo devuelva listo para pegar en Word. **No requiere acceso al repositorio:**
los datos están dentro.

---

## Cómo se usa

1. Abre una conversación nueva con un LLM capaz (ventana de contexto amplia).
2. Pega los archivos **en este orden**, cada uno precedido por su nombre en una línea:

```
00_PROMPT_MAESTRO.md          ← quién eres, qué produces, las tres reglas
01_TEXTO_ACTUAL.md            ← el Capítulo V íntegro tal como está hoy
02_HECHOS_VERIFICADOS.md      ← todas las cifras, con marca y fuente
03_ESTILO_Y_FORMATO.md        ← registro, terminología, números, tablas
04_GUION_SECCIONES_NUEVAS.md  ← arquitectura párrafo a párrafo de §5.8 y §5.9
05_CONTRATO_DE_SALIDA.md      ← qué devolver y checklist de verificación
```

3. Cierra con: **«Produce ahora el Capítulo V completo según el contrato de salida.»**

Son ~11 000 palabras en total: entra en una sola petición.

## Qué te devuelve

Un documento continuo en Markdown —el capítulo entero, no parches— más tres bloques: registro de
cambios, marcadores pendientes e inventario de tablas y figuras.

**Para pasarlo a Word:** copia el Markdown, pégalo en un editor que lo renderice (el visor de
Markdown de VS Code, Typora, o cualquier conversor en línea), copia lo renderizado y pégalo en el
`.docx` **con formato**. Las tablas llegan como tablas reales. Después aplica el
`CHECKLIST_FORMATO.md` de la guía general: tipografía, interlineado 1,5 y estilos de título.

---

## Qué contiene el paquete

| Archivo | Palabras aprox. | Contenido |
| :--- | ---: | :--- |
| `00_PROMPT_MAESTRO.md` | 900 | El encargo, el contexto del proyecto y las tres reglas que lo gobiernan |
| `01_TEXTO_ACTUAL.md` | 3 450 | El Capítulo V verbatim del `.docx (4)`, con las cifras erróneas intactas |
| `02_HECHOS_VERIFICADOS.md` | 2 400 | Las tres correcciones obligatorias, la identidad del *runtime*, el material de las dos secciones nuevas y los datos que faltan a las existentes |
| `03_ESTILO_Y_FORMATO.md` | 900 | Registro, tabla de traducción de anglicismos, convenciones numéricas, qué no debe aparecer |
| `04_GUION_SECCIONES_NUEVAS.md` | 1 300 | Arquitectura narrativa párrafo a párrafo de §5.8 y §5.9 |
| `05_CONTRATO_DE_SALIDA.md` | 1 100 | Formato de entrega, tres bloques obligatorios y checklist de 25 puntos |

---

## Las tres reglas, en corto

1. **El Capítulo V construye; el VI analiza.** Cifras que justifican una decisión de construcción,
   sí. Interpretación de resultados, no — se remite a §6.8.
2. **Ninguna cifra sin respaldo.** Todo número sale de `02`. Lo que falta se marca
   `[PENDIENTE: …]`; no se estima.
3. **Lo que no consta, se declara.** La clase de fallo residual, los dos apagados de la máquina,
   el incidente de capacidad zonal y los de disco lleno se cuentan.

---

## Un dato está pendiente a propósito

La cifra de pruebas del backend **no está en el paquete**, porque no se ha medido. El capítulo
actual dice «25 passed» y hoy hay 35 archivos de test. El LLM tiene instrucción explícita de dejar
un marcador en lugar de inventar un número.

Para cerrarlo hay que ejecutar la suite —el proyecto la corre en cinco tandas separadas, con sus
variables de entorno— y copiar la línea de resumen literal con su fecha. **Cuidado:** si tienes
`APP_ENV=dev` exportado en el shell, la configuración lo rechaza y fallan 38 recolecciones; los
valores válidos son `development`, `test`, `staging` y `production`.

---

## Antes de dar por bueno lo que te devuelva

Comprueba tú mismo estas cinco:

1. Busca `50/50` en el resultado. **No puede aparecer.**
2. Busca `25 passed` y `25 pruebas`. **No pueden aparecer.**
3. Busca `Qwen3 4B`. **No puede aparecer.**
4. Busca «exitoso», «demuestra que», «se recomienda». **No deberían aparecer** — serían análisis o
   recomendación, que pertenecen a los capítulos VI y VII.
5. Verifica que el bloque de marcadores pendientes **no esté vacío**. Si lo está, el modelo
   inventó algo.

Si alguna falla, devuélveselo señalando el punto concreto en lugar de corregirlo a mano: es más
rápido y evita que el error se cuele en la siguiente iteración.

---

## Replicar este paquete para otros capítulos

La misma estructura sirve para el Capítulo VI —que es el que más trabajo tiene— y para el III y el
VII. Cambian `01` (el texto actual del capítulo), `02` (sus hechos) y `04` (el guion de sus
secciones nuevas); `00`, `03` y `05` se reutilizan casi tal cual, ajustando la regla de altitud a
lo que corresponda a cada capítulo.

Para el Capítulo VI, las dos secciones nuevas ya están **redactadas**, no solo guionizadas:
`../../08_capitulo_vi_resultados/6.6_vigilancia_poblacional/` y
`../../08_capitulo_vi_resultados/6.9_recaracterizacion_a100/`.
