# Revision de tesis por capitulo — pasada de agosto

Mesa de trabajo paralela a [`../revision_tesis_por_capitulo/`](../revision_tesis_por_capitulo/)
para la pasada de revision de **agosto 2026**. No reemplaza esa carpeta — la
carpeta de julio queda como registro de esa pasada; esta es la siguiente.

Mismo formato que la carpeta original:

- `README.md`: que cambiar, donde reforzar y que contenido agregar.
- `evidencia/`: CSV, JSON, documentacion o artefactos que respaldan el texto.
- `imagenes/`: figuras listas para insertar cuando aplica.

## Por que una carpeta nueva y no seguir en la de julio

La carpeta de julio (`cambios_2026-07-11/`) marcó el Capítulo IV como
**"completo, alineado con la arquitectura actual"** el 11 de julio. Desde
entonces:

- Se eliminó el `frontend/` legado (`clean: eliminando frontend legacy`,
  2026-08-01) — `frontend_4/` es la única implementación.
- Se resolvió gran parte del hallazgo de la reunión del 20 de julio
  (incoherencia ML→LLM, ver `Minuta_analitica_corregida_HemoVet_2026-07-20 (1).md`).
- Se agregó el módulo de veterinarias cercanas y su conexión al chat.
- Se re-corrió la batería técnica del LLM contra el pipeline real (2026-08-01).
- Se verificó en vivo, por primera vez, la topología GCP real (ver
  `06_capitulo_iv_analisis_diseno/README.md`).

Es decir: el veredicto "completo" de julio ya no describe el sistema actual.
Esta carpeta parte de cero la verificación, capítulo por capítulo, y solo
declara algo "vigente" si se volvió a comprobar contra código/infra real esta
pasada — no por arrastre del veredicto anterior.

## Estado verificado — los 10 capítulos + preliminares + anexos (revisado 2026-08-02)

Cada capítulo fue releído completo contra el `.md (1)` y contrastado con el
código (`backend/`, `frontend_4/`) y, para arquitectura/despliegue, con la
infraestructura real por SSH. Ningún capítulo quedó como "sin revisar esta
pasada" — el detalle punto por punto está en cada subcarpeta.

Hallazgos, en orden de severidad para la defensa:

1. **Batería veterinaria E desactualizada**: Cap VI/VII citan 83.3 %
   correcto/parcial y κ=0.841 de una evaluación veterinaria de julio, previa
   a los arreglos de la reunión del 20/7 y a la re-corrida del pipeline del
   1/8. Hay una plantilla de rúbrica nueva sin llenar para una segunda ronda.
   Es el bloqueante que más afecta la validez de las cifras presentadas como
   vigentes. Ver `08_capitulo_vi_resultados/README.md`.
2. **Tres figuras del Capítulo IV desactualizadas o incompletas** frente al
   código y la infraestructura real. Reemplazos ya generados y verificados
   en `06_capitulo_iv_analisis_diseno/imagenes/`. Ver
   `06_capitulo_iv_analisis_diseno/README.md`.
3. **Las dos VMs de GCP sí son independientes**, pero `hemovet-llm-gpu` está
   completamente desconectada del despliegue real (no aparece en ningún
   compose, `.env`, ni en el pipeline de CI/CD) — el diagrama de despliegue
   no refleja esto. Ver
   `06_capitulo_iv_analisis_diseno/evidencia/verificacion_vms_2026-08-02.md`.
4. **Hallazgo operativo en vivo**: el backend de producción llevaba 11 horas
   `unhealthy` por descarga de memoria de Ollama tras inactividad — ya
   resuelto (se recargó el modelo manualmente). Mismo archivo de evidencia.
5. **Cuatro errores factuales puntuales**, cada uno de bajo esfuerzo de
   corrección: modelo LLM incorrecto citado como "Llama 3-2B" en 3 lugares
   (real: qwen3:4b), orden de la cadena de extracción invertido en Cap II,
   ruta de endpoint inexistente (`/api/v1/hematology/analyze`) en Cap II, y
   la cifra de guardrails "50/50" de código huérfano todavía en Cap V Tabla
   5.9 (julio ya lo había marcado, sigue sin corregir).
6. **v3→v4 no documentado en Cap II ni Cap III**: ambos describen solo v3
   como modelo final, pero Cap V y VI dejan claro que v4 (reentrenado tras
   discrepancias clínicas) es el que realmente se desplegó y evaluó.

Buenas noticias confirmadas esta pasada — bloqueantes de julio ya resueltos:
Capítulo VII **ya no está vacío** (era el bloqueante más grave de julio),
contradicción 38-vs-43 características resuelta, listas de tablas/figuras/
anexos agregadas, metodología LLM/RAG y de usabilidad ya pegadas al
documento, introducción ya tiene el párrafo de cierre que julio sugería.

## Orden sugerido de trabajo

1. `08_capitulo_vi_resultados` — cerrar la segunda ronda de la batería E con
   los veterinarios; es lo que más tiempo humano toma y bloquea la validez
   de Cap VI y Cap VII tal como están redactados hoy.
2. `04_capitulo_ii_solucion_propuesta` y `07_capitulo_v_desarrollo` — errores
   factuales rápidos de corregir (extracción, endpoint, modelo LLM, cifra de
   guardrails).
3. `05_capitulo_iii_metodologia` — agregar la subsección de metodología
   v3→v4.
4. `06_capitulo_iv_analisis_diseno` — reemplazar las 3 figuras desactualizadas
   (los reemplazos ya están generados).
5. `10_referencias_anexos` — decidir sobre el manual de usuario faltante.
6. `01_preliminares`, `02_introduccion`, `03_capitulo_i_marco_teorico`,
   `09_capitulo_vii_conclusiones` — solo ajustes menores señalados en cada
   README, sin bloqueantes de fondo.
