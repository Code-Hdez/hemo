La capacidad que faltaba ya quedó identificada: el modelo exacto admite **262,144 tokens de contexto nativo**, pero HemoVet sólo utiliza **16,384 tokens por solicitud**, es decir, **6.25 % de la capacidad nativa**. Los 65,536 tokens observados pertenecen a la configuración de carga de Ollama, no al máximo del modelo.

Además, Qwen declara que puede extenderse hasta **1,010,000 tokens usando YaRN**, pero esa ampliación no está configurada en el despliegue actual y no forma parte del límite nativo declarado por el artefacto de Ollama. No encendí la GPU ni modifiqué código, infraestructura o configuración.

## 1. Identidad comprobada del modelo

El SHA-256 del manifiesto oficial coincide exactamente con el digest completo de la [auditoría adjunta](sandbox:/workspace/scratch/ad9b52113ddf/upload/Pasted%20text%2820260811-215450%29.txt):

`a50eda8ed977ab48a12431878896b27ffd5cef552c17af3317d9623b939a7f1e`

Por tanto, no estamos extrapolando desde otro Qwen parecido: es exactamente el artefacto desplegado.

| Propiedad                 |                            Valor comprobado |
| ------------------------- | ------------------------------------------: |
| Modelo                    |                        `qwen3.6:27b-q4_K_M` |
| Familia interna de Ollama |                                    `qwen35` |
| Tipo                      |      Modelo causal denso con encoder visual |
| Parámetros                |                           27.8 mil millones |
| Cuantización              |                `Q4_K_M`, de precisión mixta |
| Tamaño del blob principal |         17,420,420,832 bytes, unos 17.42 GB |
| Arquitectura              | Híbrida: Gated DeltaNet + atención completa |
| Licencia                  |                                  Apache 2.0 |
| Formato                   |                                        GGUF |
| Capacidades publicadas    |      Texto, visión, herramientas y thinking |
| Digest                    |         Coincide exactamente con producción |

La denominación interna `qwen35` no significa que se haya descargado Qwen 3.5 por error: Qwen 3.6 conserva esa familia arquitectónica y Ollama emplea el renderer/parser `qwen3.5`. La identidad, tamaño, cuantización y digest aparecen en la [ficha exacta de Ollama](https://ollama.com/library/qwen3.6%3A27b-q4_K_M), y la estructura completa está en los [metadatos inmutables del GGUF](https://ollama.com/library/qwen3.6%3A27b-q4_K_M/blobs/83c54730a5fe).

## 2. Capacidad máxima frente a lo utilizado

| Dimensión                                |               Valor |            Relación con el máximo nativo |
| ---------------------------------------- | ------------------: | ---------------------------------------: |
| Contexto nativo del modelo               |  **262,144 tokens** |                                    100 % |
| Extensión con YaRN                       | Hasta **1,010,000** |              No está activa ni es nativa |
| Contexto con que arranca Ollama          |              65,536 |                                     25 % |
| Contexto efectivo por solicitud          |          **16,384** |                               **6.25 %** |
| Entrada máxima configurada               |              12,000 |  4.58 % del nativo; 73.24 % del efectivo |
| Salida normal máxima                     |               1,280 |   0.49 % del nativo; 7.81 % del efectivo |
| Salida de reparación                     |               1,024 |   0.39 % del nativo; 6.25 % del efectivo |
| Reserva interna                          |                 256 |                      1.56 % del efectivo |
| Holgura no asignada                      |               2,848 |                     17.38 % del efectivo |
| Entrada que permitiría la fórmula actual |              14,848 | La aplicación la limita antes, en 12,000 |

Qwen confirma **262,144 tokens nativos** y hasta **1,010,000 con escalado YaRN**. También advierte que YaRN estático puede afectar tareas cortas, por lo que no debe tratarse como una ampliación gratuita. El artefacto concreto de Ollama declara exactamente 262,144. [Modelo oficial de Qwen](https://huggingface.co/Qwen/Qwen3.6-27B), [configuración oficial](https://huggingface.co/Qwen/Qwen3.6-27B/blob/main/config.json).

La conclusión operativa es clara:

* La nueva GPU no hace que el modelo utilice automáticamente más contexto.
* El límite dominante sigue siendo `options.num_ctx=16384` enviado por FastAPI.
* El servidor carga 65,536, pero la primera solicitud lo obliga a realinearse en 16,384.
* El modelo dispone nativamente de **16 veces más contexto** que el utilizado por HemoVet.

### Capacidad de salida

El modelo no publica un máximo de salida independiente del contexto. Entrada, plantilla, memoria, RAG y salida comparten la misma ventana.

Qwen recomienda:

| Uso                             | Salida recomendada por Qwen | HemoVet actual |
| ------------------------------- | --------------------------: | -------------: |
| Consulta normal                 |               32,768 tokens |          1,280 |
| Problema complejo o benchmark   |               81,920 tokens |          1,280 |
| Reparación estructurada HemoVet |                   No aplica |          1,024 |

Los 32,768 y 81,920 son recomendaciones, no cantidades que el modelo siempre generará. El modelo puede detenerse antes al producir un token EOS, completar el JSON, alcanzar el timeout o llegar al `num_predict`. [Recomendaciones oficiales de generación](https://huggingface.co/Qwen/Qwen3.6-27B#best-practices).

Con la ventana nativa completa, los presupuestos matemáticos serían:

| Escenario hipotético                           | Contexto | Salida reservada |                      Entrada restante |
| ---------------------------------------------- | -------: | ---------------: | ------------------------------------: |
| HemoVet actual                                 |   16,384 |      1,280 + 256 | 14,848, aunque la app limita a 12,000 |
| Contexto nativo conservando la política actual |  262,144 |      1,280 + 256 |                               260,608 |
| Recomendación normal de Qwen                   |  262,144 |           32,768 |                               229,376 |
| Recomendación compleja                         |  262,144 |           81,920 |                               180,224 |

Esto sólo cuantifica capacidad; no constituye una recomendación de cambio.

## 3. Arquitectura que faltaba en la auditoría

| Componente                      |                                                        Valor |
| ------------------------------- | -----------------------------------------------------------: |
| Capas del lenguaje              |                                                           64 |
| Distribución                    | 16 grupos de 3 capas Gated DeltaNet y 1 de atención completa |
| Capas de atención lineal        |                                                           48 |
| Capas de atención completa      |                                                           16 |
| Dimensión oculta                |                                                        5,120 |
| Dimensión FFN                   |                                                       17,408 |
| Cabezas de atención completa    |                                                  24 Q / 4 KV |
| Dimensión por cabeza completa   |                                                          256 |
| Cabezas lineales                |                                                 48 V / 16 QK |
| Dimensión por cabeza lineal     |                                                          128 |
| Vocabulario/embedding acolchado |                                                      248,320 |
| Dimensión RoPE                  |                                                           64 |
| Base RoPE                       |                                                   10,000,000 |
| Secciones mRoPE                 |                                               `[11, 11, 10]` |
| RMS epsilon                     |                                                       `1e-6` |
| Estado SSM                      |                                                          128 |
| Dimensión interna SSM           |                                                        6,144 |
| Kernel convolucional SSM        |                                                            4 |
| Encoder visual                  |                     27 bloques, dimensión 1,152 y 16 cabezas |
| Patch visual                    |                              16; temporal 2; spatial merge 2 |
| MTP                             |                         Entrenado e incluido en el artefacto |

No es un Transformer convencional puro. Combina atención lineal recurrente con una capa de atención completa cada cuatro capas. Esto explica que el modelo soporte contextos grandes con un crecimiento de memoria más moderado.

`Q4_K_M` tampoco significa que absolutamente todos los tensores sean de cuatro bits. El artefacto mezcla:

* Q4_K para gran parte de las matrices.
* Q6_K para proyecciones sensibles, como varias capas de salida y reducción.
* F32 para normalizaciones y estados.
* F16/F32 en buena parte del encoder visual.

## 4. Parámetros efectivos exactos de generación

La auditoría no podía conocer los valores heredados porque la GPU estaba apagada. Sin embargo, el manifiesto oficial contiene los parámetros propios del modelo y la fuente exacta de Ollama 0.32.6 muestra el resto.

La precedencia real es:

`defaults de Ollama → parámetros del modelo → opciones de la solicitud`

Esto está implementado en la [fuente versionada de Ollama 0.32.6](https://github.com/ollama/ollama/blob/c82ebbd5bfb9ec7d94d3894e9023db0fb224ff50/server/routes.go#L129-L158). Los defaults están en [`DefaultOptions`](https://github.com/ollama/ollama/blob/c82ebbd5bfb9ec7d94d3894e9023db0fb224ff50/api/types.go#L1094-L1123), y los parámetros propios del modelo aparecen en el [blob oficial de parámetros](https://ollama.com/library/qwen3.6%3A27b-q4_K_M/blobs/86eff881e8d2).

| Parámetro                          |                    Valor efectivo | Procedencia    | Efecto                                                |
| ---------------------------------- | --------------------------------: | -------------- | ----------------------------------------------------- |
| `num_ctx`                          |                            16,384 | FastAPI        | Ventana real de cada solicitud                        |
| `num_predict`                      |                             1,280 | FastAPI        | Techo normal de salida                                |
| Reparación                         |                             1,024 | FastAPI        | Techo de la segunda generación correctiva             |
| Temperatura general                |                              0.30 | FastAPI        | Generación conservadora                               |
| Temperatura seleccionada/historial |                              0.15 | FastAPI        | Aún más estable                                       |
| Temperatura de reparación          |                              0.10 | FastAPI        | Máxima rigidez                                        |
| `top_p`                            |                              0.80 | FastAPI        | Limita la masa probabilística considerada             |
| `top_k`                            |                                20 | FastAPI/modelo | Considera como máximo 20 candidatos principales       |
| `min_p`                            |                           **0.0** | Modelo         | Filtro desactivado                                    |
| `presence_penalty`                 |                           **1.5** | Modelo         | Desincentiva reutilizar tokens ya presentes           |
| `repeat_penalty` normal            |                               1.0 | FastAPI/modelo | Penalización neutral                                  |
| `repeat_penalty` reparación        |                               1.1 | FastAPI        | Reduce repeticiones durante reparación                |
| `frequency_penalty`                |                           **0.0** | Ollama         | Desactivado                                           |
| `typical_p`                        |                           **1.0** | Ollama         | Filtro neutral/desactivado                            |
| `repeat_last_n`                    |                            **64** | Ollama         | Ventana de repetición; neutral cuando penalty=1       |
| `seed`                             |                            **-1** | Ollama         | Semilla aleatoria                                     |
| `num_keep`                         |                                 4 | Ollama         | Tokens conservados ante un desplazamiento de contexto |
| `logprobs`                         |                           `false` | API            | No devuelve probabilidades por token                  |
| `top_logprobs`                     |                                 0 | API            | Inactivo                                              |
| Mirostat                           | No disponible en `Options` 0.32.6 | Ollama         | No se está usando                                     |
| `think`                            |                           `false` | HemoVet        | Sin razonamiento visible ni tokens de thinking        |
| MTP especulativo                   |                          Inactivo | Ollama/HemoVet | Véase la observación siguiente                        |

### Cómo genera cualitativamente

El perfil es deliberadamente frío:

* La configuración oficial recomendada por Qwen para modo no-thinking es temperatura `0.7`, `top_p=0.8`, `top_k=20`, `min_p=0`, `presence_penalty=1.5` y `repeat_penalty=1`.
* HemoVet coincide en todos esos valores salvo la temperatura, que baja a `0.30`, `0.15` o `0.10`.
* Eso favorece respuestas consistentes, menos creativas y con menor diversidad.
* No es completamente determinista porque `seed=-1` elige una semilla variable y las temperaturas siguen siendo mayores que cero.
* `presence_penalty=1.5` sí está activo aunque la aplicación no lo envíe: se hereda del artefacto oficial.
* Qwen advierte que aumentar demasiado esa penalización puede ocasionar mezcla de idiomas; `1.5` es, no obstante, su valor recomendado para no-thinking.

## 5. Plantilla, SYSTEM y adaptadores

El [manifiesto oficial de Ollama](https://registry.ollama.ai/v2/library/qwen3.6/manifests/27b-q4_K_M) contiene únicamente:

1. Blob del modelo.
2. Licencia.
3. Parámetros.

No contiene capas de:

* Adaptadores LoRA.
* Plantilla personalizada.
* Mensaje `SYSTEM` propio del modelo.
* Modelo draft separado.

La configuración del artefacto selecciona el renderer y parser integrados `qwen3.5`. Por tanto:

* No hay un SYSTEM oculto dentro del modelo de Ollama.
* El prompt de sistema real procede del backend de HemoVet.
* No hay ajustes finos o adaptadores externos aplicados al modelo.
* Cuando HemoVet envía `think:false`, el renderer inserta una sección vacía:

```text
<think>

</think>
```

y comienza directamente la respuesta. Ese comportamiento puede comprobarse en el [renderer exacto de Ollama 0.32.6](https://github.com/ollama/ollama/blob/c82ebbd5bfb9ec7d94d3894e9023db0fb224ff50/model/renderers/qwen35.go#L186-L197).

Los tokens naturales de terminación del artefacto son:

* `248046`, correspondiente a `<|im_end|>`.
* `248044`, correspondiente a `<|endoftext|>` y usado también como padding.

Por eso `num_predict=1280` es sólo un techo: una respuesta puede terminar antes al emitir uno de esos tokens.

## 6. Capacidades disponibles versus capacidades usadas

| Capacidad                     |                  La tiene el modelo |                       La usa HemoVet |
| ----------------------------- | ----------------------------------: | -----------------------------------: |
| Texto                         |                                  Sí |                                   Sí |
| Imágenes                      |                                  Sí |              No en el flujo auditado |
| Video                         |                      Modelo base sí | No está expuesto por el flujo actual |
| Thinking                      |                                  Sí |                    No, `think:false` |
| Herramientas/function calling |                                  Sí |       No durante salida estructurada |
| Salida JSON estructurada      |                   Ollama la soporta |                                   Sí |
| MTP/especulación              |                     Pesos incluidos |                          No activada |
| RAG veterinario               |           No forma parte del modelo |              Sí, añadido por HemoVet |
| Memoria de conversación       | No es memoria permanente del modelo |           Sí, gestionada por backend |

Un hallazgo nuevo es que el GGUF incluye tensores MTP para predicción multitoken. Sin embargo, Ollama 0.32.6 pone `draft_num_predict=0` cuando no existe un draft separado y ni el modelo ni la solicitud especifican ese parámetro. Por ello, en la configuración auditada, el modelo **no está usando generación especulativa MTP**, aunque el artefacto contiene esa capacidad. La lógica está en la [ruta de opciones](https://github.com/ollama/ollama/blob/c82ebbd5bfb9ec7d94d3894e9023db0fb224ff50/server/routes.go#L135-L156) y en el [arranque MTP](https://github.com/ollama/ollama/blob/c82ebbd5bfb9ec7d94d3894e9023db0fb224ff50/llm/llama_server.go#L798-L830).

## 7. Capacidad práctica estimada

Usando las dos mediciones del estimador del propio proyecto:

* 16,384 tokens: 16,926,501,764 bytes.
* 65,536 tokens: 18,889,436,036 bytes.

El crecimiento calculado es exactamente:

`39,936 bytes por token de contexto`

Extrapolado a 262,144 tokens, el estimador produce aproximadamente:

* **26,741,173,124 bytes**
* **26.74 GB**
* **24.91 GiB**

La observación real a 65,536 fue unos 190.7 MB superior al estimador, por lo que una estimación práctica aproximada rondaría **26.9 GB**. Esto indica que el contexto nativo completo parece plausible en memoria con el artefacto cuantizado, pero sigue siendo una extrapolación: no demuestra tiempo de carga, latencia, estabilidad ni compatibilidad completa a 262,144.

El mayor riesgo práctico no es la memoria, sino el timeout:

* La realineación 65,536 → 16,384 ya tarda alrededor de 101 segundos.
* El timeout de la llamada a Ollama es 120 segundos.
* Esa recarga consume aproximadamente **84 % del timeout**, dejando unos 19 segundos antes de que intervenga la generación.

Por tanto, “el modelo soporta 262K” no significa que el despliegue actual pueda empezar a utilizarlos sin revisar tiempos, presupuestos y realineación.

## 8. Lo que continúa sin poder conocerse externamente

| Dato                                         | Estado                      | Motivo                                               |
| -------------------------------------------- | --------------------------- | ---------------------------------------------------- |
| Fecha exacta de corte del conocimiento       | Desconocida                 | Qwen no la publica en la ficha ni configuración      |
| Tokens reales generados por respuesta        | Desconocidos                | Faltan `eval_count` históricos                       |
| Tokens reales del prompt                     | Desconocidos                | Faltan `prompt_eval_count` por solicitud             |
| Velocidad tokens/s                           | Desconocida                 | Requiere `eval_duration` y `eval_count`              |
| Tiempo hasta el primer token                 | Desconocido                 | No está instrumentado en la auditoría                |
| Motivo real de parada por respuesta          | Desconocido                 | Requiere conservar `done_reason`                     |
| Porcentaje de respuestas que agotan 1,280    | Desconocido                 | Requiere métricas de producción                      |
| Calidad real a 65K/262K                      | No probada                  | Requiere una prueba controlada                       |
| Residencia actual en VRAM                    | No comprobada ahora         | La GPU estaba apagada                                |
| Texto literal completo del SYSTEM de HemoVet | No incluido en la auditoría | El modelo no trae uno propio; corresponde al backend |

En resumen: **el modelo exacto tiene 262,144 tokens nativos, HemoVet usa 16,384, la salida está limitada a 1,280 y la configuración genera respuestas muy conservadoras, no-thinking, estructuradas y no totalmente deterministas**. La capacidad extendida de 1,010,000 tokens existe sólo mediante YaRN y no está habilitada en esta instalación. El limitante actual continúa siendo la aplicación y su contrato de runtime, no el modelo ni la potencia de la nueva GPU.
