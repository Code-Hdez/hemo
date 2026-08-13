# Cifras oficiales — fuente de verdad del informe

Toda cifra que entre al documento debe estar en esta tabla o traer su propio artefacto.
Si una cifra del `.docx` no aparece aquí y no tiene fichero que la respalde, **no entra**.

Convención heredada de la campaña: **[MEDIDO]** = leído directamente de un artefacto ·
**[DERIVADO]** = calculado a partir de artefactos · **[NO CONSTA]** = no recuperable, y eso
es un resultado, no un vacío.

---

## 1 · Motor de clasificación hematológica — SIN CAMBIOS

Estas cifras están alineadas entre documento y sistema. **No tocar.**

| Cifra | Valor | Marca | Artefacto |
| :--- | ---: | :---: | :--- |
| PR-AUC macro (test, v4) | 0,9529 | MEDIDO | `outputs/final_system_state.json` |
| F1 macro (test, v4) | 0,8727 | MEDIDO | `outputs/final_system_state.json` |
| Recall macro (test, v4) | 0,9205 | MEDIDO | `outputs/final_system_state.json` |
| PR-AUC macro v3 | 0,9577 | MEDIDO | `outputs/metrics_test_v3.json` |
| Estado del sistema | `READY_FOR_PRODUCTION_WITH_LIMITATIONS` | MEDIDO | `outputs/final_system_state.json` |
| Características finales | 43 | MEDIDO | manifiesto de artefactos |
| Etiquetas oficiales de modelo | 7 | MEDIDO | política de etiquetas congelada |
| Etiquetas por regla determinista | 2 | MEDIDO | idem |
| Etiqueta excluida | 1 (`QC_UNIDAD_NO_CONVERTIDA`) | MEDIDO | idem |
| Positivos de `PATRON_ANEMIA_REGENERATIVA` en test | 6 | MEDIDO | idem |
| Latencia de inferencia ML (media) | 28,73 ms | MEDIDO | `outputs/api_bench_predict.json` |
| p50 / p95 / p99 inferencia ML | 27,93 / 33,9 / 137,95 ms | MEDIDO | idem |

## 2 · Validación externa (Dog Aging Project) — SIN CAMBIOS

| Cifra | Valor | Marca | Artefacto |
| :--- | ---: | :---: | :--- |
| Registros DAP | 1 301 | MEDIDO | `outputs/nb06_validation_summary.json` |
| Shift severo | `Monocytes`, `RDW` | MEDIDO | idem |
| F1 / PR-AUC en DAP | **no calculables** (sin etiquetas compatibles) | NO CONSTA | idem |

## 3 · Validación clínica con veterinarios — SIN CAMBIOS

| Cifra | Valor | Marca | Artefacto |
| :--- | ---: | :---: | :--- |
| Casos totales / evaluables | 526 / 509 | MEDIDO | `validacion_clinica/` |
| Evaluadores / semanas | 2 / 4 | MEDIDO | idem |
| κ macro V1 vs V2 | 0,684 | MEDIDO | `outputs/resumen_metricas.csv` |
| κ macro modelo vs V1 | 0,629 | MEDIDO | idem |
| F1 macro modelo vs V1 | 0,704 | MEDIDO | idem |

## 4 · Usabilidad del prototipo — SIN CAMBIOS

| Cifra | Valor | Marca | Artefacto |
| :--- | ---: | :---: | :--- |
| Participantes | 44 | MEDIDO | `validacion_usabilidad/` |
| Media global | 4,37 / 5 | MEDIDO | `usabilidad_por_dimension.csv` |
| Índice de usabilidad | 84,3 / 100 | DERIVADO | idem |
| Favorable / desfavorable | 81,6 % / 0 % | MEDIDO | idem |

---

## 5 · Identidad del runtime conversacional — 🔴 CAMBIA TODO

Sello bajo el que se midió el Capítulo VI nuevo. Fuente:
`06_analisis/fase2_canario_y_ic.json` · `06_analisis/tablas/tab_B1_identidad_sistema.csv`.

| Campo | Valor | Marca |
| :--- | :--- | :---: |
| Modelo | `qwen3.6:27b-q4_K_M` | MEDIDO |
| Digest | `a50eda8ed977ab48…` | MEDIDO |
| Tamaño | 17 420 432 739 B = 16,224 GiB = **17,420 GB** | MEDIDO |
| Servidor | Ollama **0.32.6** | MEDIDO |
| GPU | **NVIDIA A100-SXM4-40GB** (spot) | MEDIDO |
| Driver / CUDA | 580.159.03 / 13.0 | MEDIDO |
| `num_ctx` por petición | 16 384 | MEDIDO |
| `num_ctx` cargable en la A100 | 65 536 | MEDIDO |
| `FLASH_ATTENTION` / `KV_CACHE_TYPE` | 1 / `q8_0` | MEDIDO |
| `NUM_PARALLEL` / `KEEP_ALIVE` | 1 / −1 | MEDIDO |
| Verificación de identidad por respuesta | **115/115 respuestas del modelo sellado**, 0 de otro | MEDIDO (censo) |
| Modelos instalados en el servidor | 2 (el sellado **y el 4B, que sigue presente**) | MEDIDO |

> ⚠️ Dos correcciones que la medición impuso sobre lo que el equipo creía: el peso real es
> 17 420 432 739 B, **no** los 16,93 GB declarados; y Ollama es **0.32.6**, no 0.32.5.
> Si alguna de esas dos cifras antiguas está en el documento o en una lámina, corregirla.

---

## 6 · Rendimiento físico del runtime (caracterización absoluta de la A100)

| Cifra | Valor | IC 95 % | Marca | Artefacto |
| :--- | ---: | :--- | :---: | :--- |
| TPOT p50 | **24,4802 ms/token** | 24,4701–24,5193 | MEDIDO | `tab_C2_tpot_distribucion.csv` |
| CV del TPOT | 0,65 % | — | DERIVADO | idem |
| Decodificación p50 | **40,849 tok/s** | 40,784–40,866 | MEDIDO | `tab_C1_techos_decode.csv` |
| Techo teórico de decodificación | 117,0 tok/s | — | DERIVADO | idem |
| Banda alcanzable (77 % / 86 %) | 90,1 / 100,7 tok/s | — | DERIVADO | idem |
| MBU | **34,90 %** | 34,84–34,91 | DERIVADO | `tab_C4_mbu.csv` |
| Ancho de banda efectivo | 711,6 GB/s (nominal 2 039 GB/s) | — | DERIVADO | idem |
| Prefill p50 | 91,9 tok/s | — | MEDIDO | `tab_C8_prefill_decode.csv` |
| Determinismo intra-máquina | **20 prompts × 5 reps = 100; 0 prompts con más de un hash** | — | MEDIDO | `tab_C7_determinismo_canario.csv` |
| Sobrecarga de gramática (Δ TPOT) | **+0,332 ms/token** (1,33 % del TPOT) | sin IC (crudos no persistidos) | MEDIDO | `tab_C5_ablacion_brazos.csv` |

> **Advertencias que deben viajar con estas cifras.** (a) El techo se calcula con el tamaño en
> GB decimales (17,42), no en GiB (16,22): confundirlos infla el techo un 7,4 %. (b) Un MBU bajo
> **no** indica ineficiencia del despliegue: el MBU baja al subir el ancho de banda porque la
> sobrecarga fija por token no escala. (c) El CV de 0,65 % es la máquina en su mejor caso —100
> generaciones consecutivas, modelo ya cargado, `temperature` 0, `top_k` 1, semilla fija, sin
> concurrencia—, **no** lo que ve el usuario. (d) Prefill y decodificación comparten unidad pero
> no son comparables como rendimiento: el prefill se midió con prompts de 17–22 tokens, donde lo
> domina la sobrecarga fija.

---

## 7 · Comportamiento del asistente sobre A100 — 🔴 SUSTITUYE A LAS CIFRAS DE CPU

### 7.1 Réplica estricta pareada L4 → A100 (n = 64 casos)

| Cifra | Valor | Marca | Artefacto |
| :--- | ---: | :---: | :--- |
| p50 línea base (L4, 7-ago), recalculado desde crudos | **54,4 s** | MEDIDO | `tab_E1_slopegraph_pareado.csv` |
| p50 réplica (A100, 11-ago) | **21,4 s** | MEDIDO | idem |
| Δ mediana pareada | **31,95 s** | IC 95 % 19,06–46,28 s | `tab_E2_diferencias_pareadas.csv` |
| Reducción de p50 | **−60,6 %** | DERIVADO · Wilcoxon pareado por `id_caso` | idem |
| Criterio pre-registrado | «baja ≥ 50 %» → **se cumple** | — | `03_hipotesis/preregistro.md` |

> El p50 de 58,59 s recalculado desde los crudos difiere de los **59,1 s** publicados en los
> informes antiguos. Si el documento cita 59,1 s en algún punto, usar el recalculado y decir por
> qué.

### 7.2 Turnos sin respuesta (n = 70 por corrida)

| Corrida | Fallos | Proporción | IC 95 % Wilson |
| :--- | ---: | ---: | :--- |
| 7-ago (L4) | 17/70 | 24,29 % | 15,75–35,50 % |
| Réplica (A100) | **6/70** | **8,57 %** | 3,99–17,47 % |
| McNemar exacto | 23 discordantes | **p = 0,035** | — |

> ⚠️ **No leer esto como «la GPU arregló los fallos».** Son fenómenos distintos: los 17 antiguos
> son de contrato (`generation_repair_failed`); los 6 nuevos son de transporte (4× HTTP 502,
> 2× HTTP 422). El acuerdo de identificadores entre corridas es **κ = −0,145** —peor que el
> azar— y **0 de los 17 identificadores antiguos coinciden**. Bajo el criterio sellado del
> proyecto («si la cuenta cuadra y los ids no, el aparato no sirve»), aquí ni la cuenta cuadra.

### 7.3 Batería de 45 turnos sobre A100

| Modo | Útil | Calla | Muere | Mediana | Mín | Máx |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| GENERAL | 14 | 0 | 1 | 15,3 s | 8,1 s | 132,6 s |
| HEMOGRAMA | 14 | 0 | 1 | 17,9 s | 12,7 s | 120,5 s |
| HISTÓRICO | 15 | 0 | 0 | 24,2 s | 16,4 s | 59,4 s |
| **Total** | **43** | **0** | **2** | — | — | — |

> Con n = 15 por modo, **estas proporciones no sostienen comparación entre modos**: los
> intervalos se solapan ampliamente. Y solo se reportan mediana y rango — no hay p90 ni p95.
> Los dos turnos «muertos» son cargas en frío (HTTP 504) y se muestran, no se recortan.

### 7.4 Contra la batería de contenido de 45 turnos (instrumento del compañero)

| Métrica | Corrida 9-ago | Ronda 6 (L4) | **A100** |
| :--- | ---: | ---: | ---: |
| Turnos con contenido real | 13/45 | 44/45 | **40/45** |
| Muertes | 1 (+13 vacíos) | 1 | **0** |
| Mediana global | ~46 s | 44 s | **17,6 s** |
| `selected` mediana | 32 s | 68 s | **17,6 s** |
| Historial con datos | 0/15 | 15/15 | **12/15** |
| Peor turno | 118 s | 161 s | **65 s** |

Artefacto: `validacion_llm/resultados/rondas45_2026-08-10/bateria_a100.jsonl`.

### 7.5 Alucinación numérica

| Medición | Observado | Cota superior Wilson 95 % | Artefacto |
| :--- | ---: | ---: | :--- |
| Preguntas verificables de la campaña | **0 / 9** | **29,9 %** | `02_fixtures/verdad.json` |
| Rúbrica veterinaria (batería E) | **0 / 30** | **11,4 %** | `validacion_llm/resultados/evaluador_*.csv` |

> 🔴 **Corrección obligatoria.** El informe interno de la campaña publicó una cota del **16,8 %**
> asumiendo ~20 preguntas verificables. `verdad.json` contiene **9**. La cota correcta es
> **29,9 %**. La cifra publicada subestimaba la incertidumbre. Si esa cota entra al documento,
> entra como 29,9 %.
>
> Y en ambos casos: **cero casos observados no demuestra ausencia**. Acotar al 5 % exigiría del
> orden de 60 observaciones; al 1 %, unas 300.

---

## 8 · Tablero de las diez hipótesis pre-registradas

Hash del pre-registro: `5d6a0a71081e385e…`, **firmado antes de medir**.
Fuente: `06_analisis/tablas/tab_F1_tablero_hipotesis.csv`.

| # | Enunciado (abreviado) | Medido | Veredicto sellado |
| :--- | :--- | :--- | :--- |
| H-1 | Decode más rápido en A100 pero MBU < 73,7 % | MBU 34,90 % | CONSISTENTE, NO CONFIRMADA |
| H-2 | La sobrecarga de gramática es ≥ 10 ms/token | 0,332 ms/token | **REFUTADA** |
| H-3 | La tasa de fallos no cambia apreciablemente | κ = −0,145: poblaciones distintas | NO EVALUADA ▲ |
| H-4 | Los ids de fallo se conservan aunque cambie el recuento | 0 de 17 ids coinciden | NO EVALUADA, EVALUABLE ▲ |
| H-5 | El p50 por turno baja ≥ 50 % | −60,6 % (Wilcoxon, n = 64) | NO EVALUADA ▲ |
| H-6 | En preguntas de frontera el sistema confabula | reporta ventana truncada, no confabula | REFUTADA en su predicción |
| H-7 | El `num_ctx` efectivo cambió por el salto de VRAM | `num_ctx` fijado por petición | REFUTADA POR CONFIGURACIÓN |
| H-8 | `ttft_per_1k_in` crece a lo largo de los 15 turnos | campo no expuesto por la API | NO EVALUABLE por camino B |
| H-9 | La tasa de alucinación numérica es distinta de cero | 0 de 9 · Wilson hasta 29,9 % | NO CONCLUYENTE |
| H-10 | La VM de CPU nueva cambia el tok/s por sí sola | n = 1 máquina | NO EVALUABLE POR DISEÑO |

> ▲ **Encargo pendiente sobre el informe de la campaña, no sobre la tesis.** Las tres filas
> marcadas tienen un veredicto sellado que dice «NO EVALUADA» y una medición que **ya existe**:
> la tabla de veredictos se escribió antes de correr el brazo de réplica estricta y no se
> actualizó. La tesis debe presentar el tablero **tal cual está sellado** y señalar la
> discrepancia; no sustituir el veredicto sellado por el recalculado. Esa honestidad es
> defendible ante un comité; retocarlo, no.

---

## 9 · Potencia del diseño — el límite que hay que declarar

| n disponible | Para qué |
| ---: | :--- |
| 15 | por modo |
| 9 | preguntas verificables |
| 45 | baterías |
| 64 | pareado |
| 70 | réplica |
| **431** | **necesario para distinguir 10 % de 5 % con potencia del 80 %** |

> Ninguno de los tamaños disponibles alcanza los 431 que harían falta. **Este diseño distingue
> un efecto grande de ninguno, y no distingue uno mediano.** Es la razón cuantitativa de que
> H-3 y H-9 no se sostengan y de que H-5 sí, porque su efecto es enorme.

---

## 10 · Comparabilidad — veredicto doble

| Ámbito | Veredicto |
| :--- | :--- |
| Fallos y comportamiento | **COMPARABLE CON RESERVAS** |
| Rendimiento físico | **NO COMPARABLE** |

> La física de la L4 **no es verificable**: el protocolo del 7 de agosto no registró modelo,
> digest, cuantización, versión de Ollama, driver, GPU exacta, `format`/esquema JSON, prompts
> renderizados, warm-up ni concurrencia (11 de 15 preguntas del protocolo: NO CONSTA o PARCIAL).
> **Consecuencia para la redacción:** toda cifra de decode, MBU o TPOT de esta tesis es
> **caracterización absoluta de la A100**, nunca comparación entre GPU. Y la mejora de latencia
> es atribuible **al conjunto de la migración**, no aisladamente a la GPU.

---

## 11 · Ingeniería verificable del sistema

| Cifra | Valor | Artefacto |
| :--- | ---: | :--- |
| Módulos de backend | 12 | `backend/app/modules/` |
| Rutas declaradas bajo `/api/v1` | 40 | idem |
| Migraciones Alembic | 15 | `backend/alembic/versions/` |
| Archivos de prueba de backend | **35** | `backend/tests/` |
| Pruebas que pasan | ⚠️ **RE-MEDIR** (el documento dice 25) | `pytest -q` |
| Documentos del corpus RAG | 1 252 Markdown | `knowledge_base/` |
| Ficheros versionados del frontend activo | 95 (`frontend_4/`) | `git ls-files frontend_4` |
| Figuras de la campaña | 36 + 9 paneles de ausencia | `06_analisis/figuras/MANIFIESTO.json` |
| Tablas de la campaña | 37 | `06_analisis/tablas/INDICE_TABLAS.csv` |
| Aserciones de verificación de la campaña | 11 ejecutadas, **1 falla declarada** | `06_analisis/VERIFICACION_NOTEBOOK.txt` |
| Ficheros de evidencia previa auditados | 208, **208/208 hashes verificados intactos** | `tab_A2_corpus_evidencia.csv` |

---

## 12 · Cifras que NO deben volver a aparecer

| Cifra prohibida | Dónde está hoy | Por qué | Qué poner en su lugar |
| :--- | :--- | :--- | :--- |
| «50/50 adversariales rechazados; 20/20 legítimos» | Tabla 5.9 | Artefacto inválido; contradice §6.4.2 | 31/40 (77,5 %) y 15/20 (75,0 %) |
| «25 passed» | Tablas 5.9 y 6.13 | 35 archivos de test hoy | La salida real de `pytest` |
| «Qwen3 4B» | §1.2, §2.1, §2.5.2, §5.5 | El runtime es 27B | `qwen3.6:27b-q4_K_M` |
| «sin aceleración GPU» | §7.6, §6.8 | Corre sobre A100 | Topología con A100 spot |
| «latencia media 24,1 s» | §6.4.2 | Medida sobre CPU/L4 | 21,4 s p50 pareado sobre A100, fechado |
| «16,93 GB» de tamaño de modelo | informes internos | Peso real 17,420 GB | 17 420 432 739 B |
| «Ollama 0.32.5» | informes internos | Es 0.32.6 | 0.32.6 |
| «cota de alucinación 16,8 %» | informe de la campaña | Asumía ~20 verificables; hay 9 | 29,9 % (Wilson) |
| «latencia < 10 s por caso» | §2.6.3 criterio de éxito | El chat mide 17,6–21,4 s p50 | Criterio separado: ML < 40 ms; chat p50 ≤ 25 s |
