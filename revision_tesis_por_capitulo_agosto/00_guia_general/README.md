# 00 - Guía general (pasada de agosto)

## Estado general del documento tras revisar los 10 capítulos (2026-08-02)

Los 10 capítulos + preliminares + anexos se releyeron completos contra el
`.md (1)` y se contrastaron los puntos verificables contra el código actual
(`backend/`, `frontend_4/`) y la infraestructura en vivo (SSH a
`hemovet-prod`). Resumen ejecutivo de esta pasada:

**Resueltos desde julio** (no requieren más trabajo):
- Contradicción 38 vs 43 características → ahora consistentemente 43 en todo
  el documento.
- Lista de tablas/figuras/anexos → ya existen.
- Capítulo VII (conclusiones) → **ya no está vacío**, completo 7.1-7.7. Era
  el bloqueante más grave de julio.
- Metodología LLM/RAG (3.7) y metodología de usabilidad (3.8) → ya pegadas
  al documento.
- Introducción → párrafo de cierre ya incorporado tal como julio sugirió.

**Nuevos, encontrados en esta pasada** (ver cada carpeta de capítulo para
evidencia detallada):
1. **Modelo LLM incorrecto en 3 lugares** (Cap I glosario ×2, Cap II tabla de
   software): dice "Llama 3-2B", producción corre `qwen3:4b-instruct-2507-q4_K_M`.
2. **Orden de extracción invertido** (Cap II 2.1): dice que Gemma es
   principal y Gemini respaldo; el código hace lo opuesto.
3. **Ruta de endpoint incorrecta** (Cap II 2.6.3): `/api/v1/hematology/analyze`
   no existe; la ruta real es `/api/v1/analyze`.
4. **v3→v4 no documentado en Cap II ni Cap III**: ambos describen solo v3
   como modelo final; Cap V y VI dejan claro que v4 (reentrenado tras
   discrepancias clínicas S1-S3) es el que realmente se desplegó.
5. **Guardrails 50/50 sin corregir** (Cap V Tabla 5.9): sigue el mismo error
   que julio marcó el 11/7 — cifra de código huérfano, no del pipeline real.
6. **Batería E (exactitud de contenido) desactualizada**: los números que
   cita Cap VI/VII (83.3 % correcto/parcial, κ=0.841) son de una evaluación
   veterinaria de julio sobre respuestas del asistente anteriores a los
   arreglos de la reunión del 20/7 y a la re-corrida del pipeline del 1/8.
   Existe una plantilla de rúbrica nueva sin llenar para una segunda ronda.
7. **Anexo "Manual de usuario"** que julio pedía nunca se agregó — decisión a
   confirmar, no necesariamente un error.
8. **Diagramas de Capítulo IV**: 3 de 6 figuras de diseño desactualizadas o
   incompletas frente al código/infraestructura real (detalle completo en
   `06_capitulo_iv_analisis_diseno/`).

**Verificado con infraestructura real**: las dos VMs de GCP (`hemovet-prod`,
`hemovet-llm-gpu`) sí operan de forma independiente, pero no como sugiere el
diagrama de despliegue — `hemovet-prod` es autosuficiente (incluye su propio
Ollama CPU) y `hemovet-llm-gpu` está completamente desconectada del
despliegue automatizado, no solo apagada. De paso se encontró y resolvió un
problema operativo real: el backend de producción llevaba 11 horas
`unhealthy` por descarga de memoria de Ollama en inactividad.

## Orden de prioridad para cerrar antes de la defensa

1. Completar la segunda ronda de la Batería E con los veterinarios (bloquea
   la validez de las cifras citadas en Cap VI/VII).
2. Corregir Cap II (orden de extracción, ruta de endpoint, modelo LLM) y Cap V
   (cifra de guardrails) — son errores factuales rápidos de arreglar.
3. Agregar la subsección de metodología v3→v4 en Cap III.
4. Reemplazar las 3 figuras desactualizadas de Cap IV (ya hay reemplazos
   generados en `06_capitulo_iv_analisis_diseno/imagenes/`).
5. Decidir sobre el manual de usuario (Anexo).
