# Anexo D — Instrumento y resultados de la validación de usabilidad

> Respaldo de la sección **6.7**. Contiene el cuestionario aplicado a los 44 participantes y la
> referencia a los resultados tabulados. Datos fuente: `Respuestas - Validación HemoVet.xlsx`;
> resultados en `anexos/outputs/usabilidad_por_item.csv` y `usabilidad_por_dimension.csv`.

## D.1. Instrumento (cuestionario "Validación de usabilidad del prototipo HemoVet")

### Sección 1 — Perfil del participante
1. ¿Cuál describe mejor tu perfil? (Dueño/a de mascota · Estudiante o profesional de veterinaria ·
   Estudiante o profesional de tecnología · Otro)
2. ¿Has visto antes un hemograma o análisis de sangre de una mascota? (Sí · No · No estoy seguro/a)

### Secciones 2–5 — Afirmaciones (escala 1 = muy en desacuerdo … 5 = muy de acuerdo)

**Uso general de la aplicación**
3. La pantalla principal de HemoVet me pareció clara y fácil de entender.
4. Pude identificar fácilmente dónde subir o analizar un hemograma.
5. El diseño visual de la aplicación se siente ordenado y no sobrecargado.

**Proceso de análisis del hemograma**
6. El proceso para subir o iniciar el análisis del hemograma fue fácil de seguir.
7. La pantalla para revisar los valores detectados del hemograma me pareció clara.
8. Entendí que debía revisar los valores antes de confirmar el análisis.

**Resultados y comprensión**
9. Los resultados del análisis fueron fáciles de entender.
10. El lenguaje utilizado en los hallazgos fue claro para una persona no experta.
11. La aplicación deja claro que HemoVet es una herramienta de apoyo y no reemplaza al veterinario.
12. Después de ver los resultados, entendí mejor qué información puede aportar un hemograma.

**Ayuda, confianza y utilidad**
13. Las secciones de ayuda, diccionario o asistente serían útiles para entender mejor los resultados.
14. Usaría HemoVet como apoyo antes o después de una consulta veterinaria.
15. En general, la aplicación me parece útil para dueños de mascotas.

### Sección 6 — Preguntas abiertas
16. ¿Qué fue lo más fácil de usar en HemoVet?
17. ¿Qué parte te pareció más confusa o difícil de entender?
18. ¿Qué mejorarías de la aplicación o agregarías a la misma?

*(Además, cada sección de afirmaciones incluyó un campo opcional de comentario libre.)*

## D.2. Muestra

44 participantes. Perfil: 22 dueños de mascota (50 %), 11 "otro" (25 %), 7 de tecnología (16 %),
4 de veterinaria (9 %). El 77 % (34/44) nunca había visto un hemograma → público mayoritariamente
lego, coincidente con el usuario objetivo.

## D.3. Resultados cuantitativos

- Media global **4.37/5**, índice de usabilidad **84.3/100**, **81.6 %** de respuestas favorables
  (4–5), **0 %** desfavorables (no se registró ningún 1 ni 2 en los 13 ítems).
- Detalle por ítem: `anexos/outputs/usabilidad_por_item.csv`.
- Detalle por dimensión: `anexos/outputs/usabilidad_por_dimension.csv`.

## D.4. Resultados cualitativos (síntesis temática)

- **Aciertos más citados:** diccionario/glosario, guía de 3 pasos, corregir valores mal leídos,
  resumen final, colores semánticos, aviso de no reemplazar al veterinario, modo invitado.
- **Confusiones:** formato de archivo, si las ediciones se guardan, propósito del mapa/zona,
  diferencia de contexto del chat, ubicación del tema oscuro, unidades (µL, fL).
- **Mejoras pedidas:** velocidad y memoria del chat, leyenda de colores fija, compartir por
  WhatsApp/correo, alto contraste, corregir el *tour* (no arrancaba), rangos normales junto a los
  valores.

## D.5. Limitación del instrumento

Es una medición de **usabilidad percibida** con muestra de conveniencia y un cuestionario propio
(no un SUS estandarizado); el índice 0–100 es una normalización de las medias Likert
`(media−1)/4×100`. No incluye medición cronometrada de tareas ni tasa de error observada.
Análisis reproducible: `notebooks/validacion/16_validacion_usabilidad.ipynb`.
