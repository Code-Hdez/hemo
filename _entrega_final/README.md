# Entrega final — HemoVet · Mesa de trabajo por capítulo

**Proyecto:** *Plataforma Inteligente de Interpretación Hematológica en la Especie Canina
para Orientación Diagnóstica, Control de Calidad y Vigilancia Poblacional* (P1 ICC 1910).
**Autores:** Carlos David Hernández Collado · Edwin Andrés Balbuena Bisonó.
**Documento vigente:** `P1 ICC 1910 — … (4).docx` (y su exportación `.md`, contenido equivalente,
incluye ya el Capítulo VII).
**Guía institucional:** *Manual para la realización del Informe final de proyecto*, EICT-PUCMM,
Rev. Septiembre 2025 → copia en `00_guia_general/manual_eict/`.
**Fecha de esta revisión:** 12 de agosto de 2026.

---

## Qué es esta carpeta

Una mesa de trabajo, una subcarpeta por bloque del informe, que responde tres preguntas para
cada capítulo:

1. **Qué contradice al sistema real** — afirmaciones del documento que ya no son ciertas.
2. **Qué hay que modificar** — con el texto de reemplazo redactado y la cifra verificada.
3. **Qué falta por incorporar** — secciones, tablas, figuras y anexos que el sistema ya produjo
   y el documento todavía no recoge.

Cada subcarpeta sigue la misma convención:

```
<capítulo>/
├── README.md      ← qué cambiar, con el texto de reemplazo
├── generar/       ← 📦 PAQUETE PARA UN LLM. Devuelve el capítulo entero, reescrito
├── tablas/        ← ✅ VA AL DOCUMENTO. Tablas numeradas: CSV + versión lista para pegar
├── figuras/       ← ✅ VA AL DOCUMENTO. PDF + SVG + PNG, y versión en gris para revisar impresión
└── fuentes/       ← ❌ NO VA AL DOCUMENTO. Artefactos crudos, solo para verificar cifras
```

**Un JSON no es material de tesis.** No se numera, no se lista, no se referencia y no se lee en
papel. Es el *origen* de la evidencia, no la evidencia. Todo dato que el documento necesita está
convertido a tabla numerada en `tablas/`; el artefacto crudo queda en `fuentes/` para poder
verificarlo. El criterio completo está en
[`00_guia_general/COMO_PRESENTAR_LA_EVIDENCIA.md`](00_guia_general/COMO_PRESENTAR_LA_EVIDENCIA.md).

Documentos transversales:

| Documento | Para qué |
| :--- | :--- |
| [`00_guia_general/MATRIZ_HALLAZGOS.csv`](00_guia_general/MATRIZ_HALLAZGOS.csv) | Los 61 hallazgos con id, severidad, acción y evidencia. Filtrar por `P0` para empezar |
| [`99_trazabilidad/CIFRAS_OFICIALES.md`](99_trazabilidad/CIFRAS_OFICIALES.md) | La fuente de verdad: toda cifra que entre al documento debe estar aquí |
| [`00_guia_general/COMO_PRESENTAR_LA_EVIDENCIA.md`](00_guia_general/COMO_PRESENTAR_LA_EVIDENCIA.md) | Qué formato va al documento y cuál no; convenciones de tablas, figuras y números |
| [`00_guia_general/CATALOGO_DE_FIGURAS_E_IMAGENES.md`](00_guia_general/CATALOGO_DE_FIGURAS_E_IMAGENES.md) | Las figuras que hay, las que faltan y cómo producirlas |
| [`00_guia_general/CHECKLIST_FORMATO.md`](00_guia_general/CHECKLIST_FORMATO.md) | Tipografía, márgenes, paginación, IEEE, empastado |
| [`99_trazabilidad/INVENTARIO_EVIDENCIA.md`](99_trazabilidad/INVENTARIO_EVIDENCIA.md) | Dónde vive cada artefacto en el repositorio |

---

## Las carpetas `generar/` — un paquete por capítulo

Cada bloque tiene una subcarpeta `generar/` con **seis archivos autocontenidos** que se pegan en
una conversación con un LLM y devuelven **el capítulo entero reescrito**, listo para seleccionar,
copiar y pegar sobre el `.docx`. No requieren acceso al repositorio: los datos están dentro.

```
generar/
├── LEEME.md                     ← cómo se usa, qué verificar en el resultado
├── 00_PROMPT_MAESTRO.md         ← el encargo y las tres reglas del capítulo
├── 01_TEXTO_ACTUAL.md           ← el capítulo verbatim del .docx (4), con sus errores intactos
├── 02_HECHOS_VERIFICADOS.md     ← todas las cifras, con marca MEDIDO/DERIVADO/PENDIENTE
├── 03_ESTILO_Y_FORMATO.md       ← registro, anglicismos, números, tablas
├── 04_GUION_SECCIONES_NUEVAS.md ← arquitectura párrafo a párrafo de lo que hay que escribir
└── 05_CONTRATO_DE_SALIDA.md     ← qué devolver, y checklist de verificación
```

| Paquete | Palabras | Regla de altitud propia | Riesgo que vigila |
| :--- | ---: | :--- | :--- |
| 01 · Preliminares | 10 100 | El resumen sintetiza, no aporta | Pasarse de 400 palabras; escribir los agradecimientos |
| 02 · Introducción | 7 600 | Plantea el problema, no lo mide | **Mejorarlo**: es el único donde el error probable es pasarse |
| 03 · Capítulo I | 14 300 | Presenta la literatura, no la contrasta | **Inventar la cita que §6.8 refuta** |
| 04 · Capítulo II | 12 800 | Propone y planifica, no reporta | **Rellenar el presupuesto** con cifras plausibles |
| 05 · Capítulo III | 15 000 | Describe cómo se midió, no qué salió | Escribir el Capítulo VI por error |
| 06 · Capítulo IV | 10 500 | Describe diseño, no construcción | Escribir el Capítulo V por error |
| 07 · Capítulo V | 11 100 | Construye; el VI analiza | Calcular porcentajes de mejora |
| 08 · Capítulo VI | 18 800 | Reporta y analiza; el VII concluye | Leer la bajada de fallos como corrección |
| 09 · Capítulo VII | 11 800 | Resume el VI, no lo amplía | Cifras sin su `(§6.N)` |
| 10 · Referencias y anexos | 14 400 | Un anexo presenta evidencia, no la analiza | **Inventar las ocho referencias** |

**Los tres paquetes en negrita son los que más hay que verificar a mano.** En los tres, el riesgo
es el mismo: se le pide al modelo un dato que el paquete no contiene, y un modelo ante un hueco
tiende a rellenarlo con algo verosímil. Cada `LEEME.md` termina con las comprobaciones concretas
que hay que hacer sobre el resultado antes de darlo por bueno.

**Dos paquetes son distintos de los demás.** El del Capítulo VI no lleva guion sino
`04_SECCIONES_YA_REDACTADAS.md`, porque §6.6 y §6.8 ya están escritas y verificadas: el trabajo es
integrarlas sin estropearlas. Y el de preliminares **no produce los agradecimientos ni las
dedicatorias**: son textos personales, un agradecimiento generado se nota, y el paquete entrega un
guion de estructura en su lugar.

---

## Diagnóstico en una frase

> El documento describe con fidelidad el HemoVet de julio de 2026. El HemoVet que hoy corre en
> producción es otro sistema en su capa conversacional: **otro modelo, otra GPU, otras
> latencias, otra tasa de fallos, y una campaña de medición pre-registrada que es, con
> diferencia, el resultado metodológicamente más fuerte del proyecto — y no aparece en la
> tesis.**

Todo lo demás —motor de clasificación, validación externa DAP, validación clínica con dos
veterinarios, usabilidad n = 44— está alineado y **no hay que tocarlo**. El trabajo se
concentra en la capa LLM/RAG, el despliegue y los capítulos que la describen.

---

## Semáforo por capítulo

| Bloque | Estado | Bloqueantes | Trabajo estimado |
| :--- | :---: | :---: | :--- |
| 01 · Preliminares (portada, TOC, listas, resumen/abstract) | 🟡 | 1 | Renumerar listas, añadir páginas, actualizar resumen/abstract con la cifra de latencia |
| 02 · Introducción, objetivos, justificación, limitaciones | 🟢 | 0 | Añadir una limitación (runtime spot) |
| 03 · Capítulo I — Marco teórico | 🟡 | 0 | Añadir §1.1.3.7 (rendimiento de inferencia) y ~12 términos al glosario |
| 04 · Capítulo II — Solución propuesta | 🔴 | 3 | Presupuesto, entorno de demostración y criterios de éxito quedaron falsos |
| 05 · Capítulo III — Metodología | 🔴 | 1 | Falta la metodología de la campaña pre-registrada (§3.11) |
| 06 · Capítulo IV — Análisis y diseño | 🟡 | 1 | Diseño de despliegue GPU + contrato de release; error de referencia cruzada |
| 07 · Capítulo V — Desarrollo | 🔴 | 2 | Cifra inválida 50/50 sobreviviente; falta media ingeniería de agosto |
| 08 · Capítulo VI — Resultados | 🔴 | 3 | Falta §6.6 completa, falta §6.9 (recaracterización), cifras CPU obsoletas |
| 09 · Capítulo VII — Conclusiones | 🟡 | 1 | §7.6 afirma «sin aceleración GPU»; faltan 5 limitaciones y 3 hallazgos inesperados |
| 10 · Referencias y anexos | 🟡 | 0 | Falta Anexo E; verificar orden y formato IEEE |

🔴 bloqueante · 🟡 requiere trabajo · 🟢 alineado

---

## Los seis bloqueantes, en orden de ejecución

### B1 · El runtime conversacional documentado no es el desplegado

El documento dice **Qwen3 4B cuantizado sobre CPU** en siete lugares (glosario §1.2 C, §2.1,
Tabla 5 de §2.5.2, §2.6.1, §5.5, §6.5, §7.6). Lo que corre en producción, sellado y verificado
respuesta a respuesta, es:

| Campo | Valor medido |
| :--- | :--- |
| Modelo | `qwen3.6:27b-q4_K_M` |
| Digest | `a50eda8ed977ab48…` |
| Tamaño | 17 420 432 739 B (16,224 GiB / 17,420 GB) |
| Servidor | Ollama **0.32.6** |
| GPU | **NVIDIA A100-SXM4-40GB** (spot) |
| Driver / CUDA | 580.159.03 / 13.0 |
| `num_ctx` por petición | 16 384 (la A100 admite 65 536) |

Evidencia: `06_analisis/fase2_canario_y_ic.json`, `06_analisis/tablas/tab_B1_identidad_sistema.csv`,
`deploy/gpu/compose.env.example`, `deploy/releases/gpu-runtime-*.json`.
Verificación de identidad respuesta a respuesta: `tab_B3_identidad_por_respuesta.csv`,
**n = 115, cero respuestas de un modelo distinto al sellado** (censo, no muestra).

> Matiz que debe quedar escrito: el 4B **sigue instalado** en el servidor
> (`tab_B4_modelos_instalados.csv`). No se usó —está verificado— pero la guarda del código no
> lo impide. Es una limitación operativa real, no un detalle.

**Dónde se corrige:** `04_capitulo_ii_…`, `07_capitulo_v_…`, `08_capitulo_vi_…`,
`09_capitulo_vii_…`, `03_capitulo_i_…` (glosario).

### B2 · Toda afirmación de «sin GPU» y toda latencia de chat quedaron falsas

§6.4.2 (24,1 s), §6.4.3 («fallo transitorio de la infraestructura de la CPU»), §6.8 y §7.6
(«el modelo de lenguaje se ejecuta sin aceleración GPU») describen un sistema que dejó de
existir la madrugada del 11 de agosto de 2026. Medido, pareado por caso, n = 64:

| | L4 (7-ago) | A100 (11-ago) |
| :--- | ---: | ---: |
| p50 por turno | 54,4 s | **21,4 s** |
| Reducción | — | **−60,6 %** (Wilcoxon pareado; IC 95 % 19,06–46,28 s) |
| Turnos sin respuesta | 17/70 (24,3 %) | **6/70 (8,6 %)** — McNemar exacto p = 0,035 |
| Muertes en la batería de 45 turnos | 1 (+13 vacíos) | **0** |

**Dónde se corrige:** `08_capitulo_vi_…` (§6.4, §6.5), `09_capitulo_vii_…` (§7.6).

### B3 · El Capítulo VI perdió la sección 6.6 completa

La numeración del cuerpo salta **6.5 → 6.7**. La *Lista de Tablas* sigue anunciando
«Tabla 6.14 — Señales del reporte de vigilancia poblacional», que no existe en el cuerpo, y el
cuerpo usa el número 6.14 para la tabla de usabilidad que la lista llama 6.15. La vigilancia
poblacional se construye en §5.6 y se promete en la entradilla del Capítulo VI, pero nunca se
analiza.

**Solución:** redacción completa de §6.6 lista para pegar en
[`08_capitulo_vi_resultados/6.6_vigilancia_poblacional/`](08_capitulo_vi_resultados/6.6_vigilancia_poblacional/6.6_vigilancia_poblacional.md).

### B4 · Sobrevive la cifra inválida «50/50» en el Capítulo V

Tabla 5.9 todavía reporta *«Guardrails LLM/RAG: 50/50 adversariales rechazados; 20/20 legítimos
aceptados»*. Ese dato viene de `outputs/llm_guardrails_eval.json`, se declaró inválido en la
revisión de julio, y **contradice frontalmente al propio Capítulo VI** (§6.4.2: 31/40 = 77,5 %
adversariales; 15/20 = 75 % legítimos). Un lector del comité que compare ambos capítulos
encuentra la contradicción en dos minutos.

**Dónde se corrige:** `07_capitulo_v_desarrollo/README.md`, acción A-V-01.

### B5 · «25 pruebas backend» ya no es cierto

Tablas 5.9 y 6.13 reportan *25 passed in 1.45 s*. Hoy `backend/tests/` contiene **35 archivos
de prueba**, incluidos los que no existían en julio: contrato de manifiesto de release,
bundle GPU, topología de compose, rollback, contrato de entorno de despliegue y aceptación de
etapa 10. La cifra hay que **medirla de nuevo**, no estimarla.

```bash
cd backend && python -m pytest -q --junitxml=/tmp/hemovet_tests.xml | tail -3
```

**Dónde se corrige:** `07_capitulo_v_desarrollo/README.md` y `08_capitulo_vi_resultados/README.md`.

### B6 · El documento nunca muestra el producto

La tesis tiene **47 figuras y ninguna es una captura de la plataforma funcionando**. §5.4, la
sección que describe el desarrollo del frontend, **no tiene una sola imagen**. El comité leerá 200
páginas sobre una aplicación web sin llegar a verla.

El reparto actual: 6 diagramas, 20 gráficas de resultados de ML, 8 de validación clínica, 9 del
asistente, 6 de usabilidad, 3 documentales y 1 captura de la consola de Google Cloud.

Es contradictorio con el propio documento: §6.7 reporta un índice de usabilidad de 84/100 sobre 44
participantes, y los aspectos que esos participantes mejor valoraron —el diccionario, la guía de
tres pasos, la corrección de valores extraídos, los colores semánticos, el aviso de no sustituir al
veterinario— son **todos visuales**, y ninguno se muestra. El manual EICT lo pide en tres lugares
distintos, incluido el requisito de que el producto final «sea estéticamente aceptable» y «esté
rotulado», que no es verificable sin imágenes.

**Solución:** catálogo de 11 capturas con especificaciones de producción, más el diagrama de
despliegue a rehacer y el mockup ausente, en
[`00_guia_general/CATALOGO_DE_FIGURAS_E_IMAGENES.md`](00_guia_general/CATALOGO_DE_FIGURAS_E_IMAGENES.md).

---

## Lo que falta por incorporar (no es corrección: es contenido nuevo)

| # | Contenido | Dónde va | Estado del material |
| :---: | :--- | :--- | :--- |
| N1 | **§6.9 Recaracterización del runtime conversacional sobre A100** — campaña pre-registrada, 10 hipótesis, 36 figuras, 37 tablas, procedencia SHA-256 | Capítulo VI (sección nueva) | **Redacción lista** + figuras y tablas copiadas en `08_…/6.9_recaracterizacion_a100/` |
| N2 | **§6.6 Resultados de vigilancia poblacional** | Capítulo VI (sección perdida) | **Redacción lista** en `08_…/6.6_vigilancia_poblacional/` |
| N3 | **§3.11 Metodología de recaracterización y pre-registro** | Capítulo III | Guion detallado en `05_capitulo_iii_metodologia/README.md` |
| N4 | **§5.9 Cadena de release, contrato GPU y fail-closed** + **§5.10 Rondas 4-6 del asistente** | Capítulo V | Guion detallado en `07_capitulo_v_desarrollo/README.md` |
| N5 | **§1.1.3.7 Rendimiento de inferencia de modelos de lenguaje** (roofline, MBU, TPOT, decodificación restringida) | Capítulo I | Guion + fuentes en `03_capitulo_i_marco_teorico/README.md` |
| N6 | **Anexo E — Evidencia de la campaña de recaracterización** | Anexos | Estructura y manifiesto en `10_referencias_anexos/anexo_E_recaracterizacion/` |
| N7 | **Manual de usuario** (lo exige el manual EICT en el Capítulo V, textual) | Anexo o guía en línea | ⚠️ **No existe.** Hay que producirlo |
| N8 | ~12 términos nuevos de glosario (TPOT, MBU, prefill/decode, GBNF, spot, entailment, fail-closed, pre-registro, Wilson, McNemar, Wilcoxon, κ entre corridas) | §1.2 | Definiciones redactadas en `03_capitulo_i_marco_teorico/README.md` |
| **N9** | **Capturas del producto funcionando** — 6 obligatorias, 5 recomendadas | §5.4, §5.5, §6.6 | ⚠️ **No existe ninguna.** Catálogo y especificaciones en `00_guia_general/CATALOGO_DE_FIGURAS_E_IMAGENES.md` |
| N10 | Diagrama de despliegue rehecho (hoy es una captura de consola) + mockup o mapa de navegación | §4.2.5, §4.2 | Especificado en el mismo catálogo |

---

## Ruta crítica sugerida

El orden importa: los capítulos de atrás fijan las cifras que los de adelante resumen.

```
1. 08_capitulo_vi_resultados     ← aquí viven las cifras. Empezar SIEMPRE por aquí.
      ├─ §6.4 reescrita con las cifras de A100
      ├─ §6.5 con pytest re-medido
      ├─ §6.6 insertada (vigilancia)
      └─ §6.9 insertada (recaracterización)
2. 07_capitulo_v_desarrollo      ← quitar 50/50, añadir §5.9 y §5.10
3. 05_capitulo_iii_metodologia   ← añadir §3.11 (cómo se midió lo del punto 1)
4. 09_capitulo_vii_conclusiones  ← recoger limitaciones y hallazgos nuevos
5. 04_capitulo_ii_solucion       ← presupuesto y demostración con el sistema real
6. 06_capitulo_iv_analisis       ← despliegue GPU en el diseño
7. 03_capitulo_i_marco_teorico   ← marco del resultado nuevo + glosario
8. 10_referencias_anexos         ← Anexo E, IEEE, manual de usuario
9. 01_preliminares               ← TOC, listas y resumen AL FINAL (dependen de todo)
```

---

## Reglas de trabajo (no negociables)

1. **Ninguna cifra sin artefacto.** Cada número que entre al documento debe poder señalarse a un
   fichero con hash en `99_trazabilidad/CIFRAS_OFICIALES.md`. Si no hay artefacto, no entra.
2. **Toda proporción lleva intervalo de confianza.** «0 alucinadas» sin intervalo es una
   afirmación no sostenida: 0/30 significa «hasta 11,4 % con 95 % de confianza» (Wilson), y
   0/9 significa «hasta 29,9 %». Escribir el cero solo es el error que esta carpeta existe para
   evitar.
3. **Marcar MEDIDO vs. DERIVADO.** La campaña ya lo hace en cada figura; el documento debe
   heredarlo.
4. **Lo que no consta, se declara.** «NO CONSTA» es un resultado, no un vacío que rellenar.
   La física de la L4 no es verificable y eso debe quedar escrito, no maquillado.
5. **Capítulo V construye, Capítulo VI analiza, Capítulo VII cierra.** No mover resultados al V
   ni construcción al VI: el manual EICT es explícito en que el apartado de resultados «no
   incluye conclusiones ni sugerencias».
6. **No repintar el pasado.** El documento describía un sistema sobre L4/CPU y eso era cierto
   cuando se escribió. La redacción correcta no es borrarlo: es fechar la migración y presentar
   el antes/después, que es justamente lo que la §7.4 (resultados inesperados) pide.
