# Catálogo de figuras e imágenes — qué hay y qué falta producir

---

## El hallazgo

El documento tiene **47 figuras listadas**. Su reparto:

| Tipo | Cantidad | Ejemplos |
| :--- | ---: | :--- |
| Diagramas de análisis y diseño | 6 | Casos de uso, componentes, flujo, modelo de datos, secuencia LLM/RAG, despliegue |
| Gráficas de resultados de ML | 20 | ROC/PR, SHAP, bootstrap, evolución v3→v4, tasas de activación |
| Gráficas de validación clínica | 8 | Mapas de kappa, métricas por clase, impacto del reentrenamiento |
| Gráficas del asistente conversacional | 9 | Límites de seguridad, batería A, robustez, consistencia, concordancia |
| Gráficas de usabilidad | 6 | Índice por dimensión, media por ítem, perfil de participantes |
| Documentales | 3 | Hemograma IDEXX, diagrama de diseño inicial, calendario de Jira |
| Captura de infraestructura | 1 | Estado de despliegue en la consola de Google Cloud |
| **Capturas del producto funcionando** | **0** | **—** |

**La sección §5.4 «Desarrollo del frontend» no tiene ninguna figura.** Es la sección que describe
la aplicación que el propietario de la mascota usa, y el lector del comité no ve la aplicación en
ningún momento del documento.

### Por qué es un problema y no un detalle

El manual EICT lo pide en tres lugares distintos:

- Capítulo V (p. 12): *«Se sugiere ir presentando imágenes de cómo se va creando/formando el
  proyecto.»*
- Capítulo V, requisitos del producto final (p. 12): el producto debe *«ser estéticamente
  aceptable»*, *«estar rotulado»* y *«presentar información útil y legible al usuario»*. Ninguna de
  las tres es verificable por el comité sin imágenes.
- Capítulo IV, diseño para ICC (p. 11): *«Diseño de ambiente de usuario (Mockups)»* figura entre
  los artefactos de diseño esperados.

Y hay un argumento adicional propio de este proyecto: **§6.7 reporta un índice de usabilidad de
84/100 sobre 44 participantes**, y el lector no puede ver qué fue lo que valoraron. Los aspectos
mejor puntuados —el diccionario, la guía de tres pasos, la corrección de valores extraídos, los
colores semánticos, el aviso de no sustituir al veterinario, el modo invitado— son todos
**visuales**, y ninguno se muestra.

---

## Capturas a producir

Mínimo **8**, recomendado **11**. Todas del sistema real en funcionamiento, con datos de prueba.

### Bloque 1 · Para §5.4 (Desarrollo del frontend) — obligatorias

| # | Captura | Qué debe mostrar | Por qué |
| :---: | :--- | :--- | :--- |
| 1 | **Resumen personal** | Mascotas registradas, análisis recientes, accesos rápidos | Es la primera pantalla; ancla la Tabla 5.6 |
| 2 | **Carga de hemograma** | Zona de arrastre, formatos admitidos, estado de la extracción | Punto de entrada del flujo principal |
| 3 | **Revisión y corrección de valores** | Valores extraídos editables, antes de confirmar | 🔴 **La más importante.** Es el control humano obligatorio del sistema y uno de los aciertos mejor valorados en la encuesta |
| 4 | **Resultado interpretativo** | Patrones activos, probabilidades, valores relevantes, colores semánticos y el aviso de alcance | Es el producto del proyecto: lo que el propietario se lleva |
| 5 | **Historial / evolución** | Serie de análisis de una misma mascota | Sostiene el caso de uso de seguimiento crónico de la Introducción |
| 6 | **Asistente conversacional** | Una pregunta, su respuesta y las fuentes citadas | Sostiene §5.5, §6.4 y §6.8 |

### Bloque 2 · Recomendadas

| # | Captura | Por qué |
| :---: | :--- | :--- |
| 7 | **Rechazo del asistente ante una consulta fuera de alcance** | 🔴 Vale por sí sola: demuestra visualmente el *guardrail* que §6.4 mide en tablas. Es la imagen que mejor defiende la postura ética del proyecto |
| 8 | **Biblioteca / glosario** | Fue el aspecto mejor valorado en la encuesta de usabilidad |
| 9 | **Vigilancia comunitaria** | Con su leyenda interpretativa y la advertencia permanente. Ancla la §6.6 nueva |
| 10 | **Panel técnico / administrativo** | Cierra la Tabla 5.6, que lo lista |
| 11 | **Vista móvil** de la pantalla de resultado | El 77 % de los encuestados nunca había visto un hemograma; el uso probable es desde el teléfono |

---

## Cómo producirlas

### Datos

**Usar exclusivamente datos de prueba.** Ninguna captura puede contener nombre real de mascota,
de propietario, de clínica, correo electrónico ni dirección. Si el sistema muestra un
identificador, difuminarlo o sustituirlo antes de insertar.

El *fixture* de la campaña (una mascota de ensayo con 18 parámetros hematológicos) sirve para las
capturas 3, 4 y 6, y tiene la ventaja de ser el mismo caso que se documenta en el Capítulo VI.

### Técnica

- Navegador **sin barras de marcadores ni extensiones visibles**; ventana limpia.
- Resolución mínima **1920 × 1080**, y capturar en **PNG**. Para el empastado, insertar a una
  anchura que dé al menos 150 ppp efectivos.
- Modo claro, salvo que se quiera mostrar explícitamente el alto contraste.
- **Recortar el cromo del navegador** salvo que la URL sea parte de lo que se quiere mostrar.
- **Rotular** los elementos a los que se refiere el texto, con llamadas numeradas discretas sobre
  la imagen. El manual pide expresamente que el producto esté rotulado.
- Numerar y titular en el mismo estilo que el resto: *Figura 5.6. Pantalla de revisión de valores
  extraídos, previa a la confirmación del análisis.*

### Dónde insertarlas

| Captura | Sección |
| :---: | :--- |
| 1, 2, 3, 4, 5 | §5.4, intercaladas con la Tabla 5.6 |
| 6, 7 | §5.5 (desarrollo del módulo LLM/RAG) |
| 8, 10, 11 | §5.4 o anexo |
| 9 | §6.6 o §5.6 |

Si se producen las 11, el Capítulo V pasa de 5 figuras a 13, y deja de ser el único capítulo
donde el producto no se ve.

---

## Diagramas: revisar los que ya hay

Los seis diagramas del Capítulo IV existen y están bien planteados. Dos necesitan actualización y
uno hay que crearlo:

| Diagrama | Estado | Acción |
| :--- | :---: | :--- |
| Figura 4.1 · Casos de uso | ✅ | Sin cambios |
| Figura 4.2 · Componentes backend | ✅ | Sin cambios |
| Figura 4.3 · Flujo de análisis hematológico | ✅ | Sin cambios |
| Figura 4.4 · Modelo de datos | ✅ | Sin cambios |
| Figura 4.5 · Secuencia del módulo LLM/RAG | 🟡 | **Actualizar**: falta la puerta de contenido, el completado determinista desde la base de datos y la resolución de elipsis (ver `../06_capitulo_iv_analisis_diseno/README.md`) |
| Figura 4.6 · Despliegue | 🔴 | **Rehacer.** Hoy es una captura de consola. Debe ser un **diagrama de despliegue** —que el manual pide nominalmente para ICC— con los dos nodos, la dirección interna estática, la validación de arranque y la rama de apagado ante fallo |
| *(nuevo)* · Mockup o mapa de navegación | 🔴 | El manual lista «Diseño de ambiente de usuario (Mockups)» entre los artefactos de diseño de ICC. Un mapa de navegación de las ocho pantallas cubre el requisito |

> La captura actual de la consola de Google Cloud no se pierde: pasa a ser una figura de
> verificación operativa en §5.7 o en el anexo, que es su lugar natural.

---

## Resumen de lo que hay que producir

| Elemento | Cantidad | Prioridad |
| :--- | ---: | :---: |
| Capturas del producto | 6 obligatorias + 5 recomendadas | 🔴 Alta |
| Diagrama de despliegue rehecho | 1 | 🔴 Alta |
| Mockup o mapa de navegación | 1 | 🟡 Media |
| Actualización del diagrama de secuencia LLM/RAG | 1 | 🟡 Media |
| Figuras de la campaña (ya existen, solo insertar) | 12 | 🔴 Alta |

Las 12 de la campaña ya están listas en
`../08_capitulo_vi_resultados/6.9_recaracterizacion_a100/figuras/`, en PDF, SVG y PNG, con su
versión en escala de grises. Las demás hay que producirlas.
