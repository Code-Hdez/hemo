# 09 - Capítulo VII - Conclusiones y recomendaciones (pasada de agosto)

## Corrección importante sobre el veredicto de julio

La carpeta de julio marcó este capítulo como **"BLOQUEANTE — CAPÍTULO VACÍO"**
("el encabezado va directo a Referencias, P1995–P2003 vacíos"). **Esto ya no es
cierto.** En el `.md (1)` actual, el Capítulo VII (líneas 2157-2254) está
completo: 7.1 Conclusiones, 7.2 Cumplimiento de objetivos (tabla con 5 OE),
7.3 Limitaciones (7 puntos), 7.4 Resultados inesperados (5 hallazgos),
7.5 Recomendaciones, 7.6 Puesta en funcionamiento, 7.7 Sostenibilidad — con la
misma estructura de 7 subsecciones que julio recomendó. Es el mayor cambio
positivo detectado en esta pasada.

## Qué falta ajustar

### 7.1 y Tabla 7.1 (OE5) — heredan la salvedad de la Batería E

7.1 dice: *"el módulo LLM/RAG se probó... en un conjunto de 30 respuestas
clínicamente seguras... el 83.3 % de las respuestas fueron correctas o
parcialmente correctas, y no se detectaron alucinaciones"*. Tabla 7.1 (OE5)
repite la cifra y añade *"concordancia veterinaria de kappa 0.841"*.

Como se documenta en `08_capitulo_vi_resultados/README.md`, esa cifra es real
pero corresponde a una evaluación veterinaria de julio (7-9/7) sobre respuestas
del asistente **anteriores** a los arreglos de la reunión del 20 de julio y a la
re-corrida del pipeline del 1 de agosto. Existe una plantilla de rúbrica nueva
(`validacion_llm/rubrica_veterinarios/rubrica_contenido_llm_medico{1,2}.csv`)
generada para una segunda ronda sobre las respuestas actuales, todavía sin
llenar. No es necesariamente un error de redacción — pero conviene decidir
conscientemente si se declara la fecha de corte de esa validación o si se
completa la segunda ronda antes de la defensa, en vez de presentarla como si
fuera contra el sistema de hoy sin matiz.

### 7.3 Limitaciones — ya cubre el punto correcto, sin necesidad de cambios de fondo

El punto sexto ("el módulo conversacional se ha sometido a una validación
piloto... dos evaluadores y 30 preguntas... es importante contar con un
conjunto más amplio") ya declara la naturaleza piloto de la validación E. Sería
más preciso si además dijera explícitamente que las 30 respuestas evaluadas no
son las que genera el sistema hoy — pero la limitación de fondo (n pequeño, 2
evaluadores) ya está bien planteada.

### 7.5 Recomendaciones — coherente, sin contradicciones detectadas

Las 8 mejoras de UX listadas coinciden exactamente con los hallazgos
cualitativos de 6.7.2 (velocidad del chat, memoria conversacional, leyenda de
colores, rangos normales, exportación, alto contraste, tour de bienvenida,
glosario). No se detectaron promesas que excedan lo implementado.

## Lo que no se verificó en esta pasada

No se contrastó línea por línea el resto de 7.6 (puesta en funcionamiento) ni
7.7 (sostenibilidad) contra el estado operativo real más allá de lo ya cubierto
en `06_capitulo_iv_analisis_diseno` (las dos VMs, el hallazgo del healthcheck).
7.6 dice *"la arquitectura se ha implementado mediante contenedores Docker que
ejecutan... Ollama... y el frontend web basado en React"* — esto es correcto y
coincide con lo verificado por SSH en vivo el 2026-08-02.

## Evidencia incluida

- No se copiaron archivos nuevos aquí — la evidencia de fondo (batería E,
  verificación de VMs) vive en `06_capitulo_iv_analisis_diseno/` y
  `08_capitulo_vi_resultados/`.
