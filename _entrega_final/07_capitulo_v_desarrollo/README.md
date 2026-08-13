# 07 · Capítulo V — Desarrollo del proyecto

**Estado: 🔴 dos bloqueantes.** Uno de corrección —sobrevive una cifra que ya se declaró
inválida y que contradice al Capítulo VI— y uno de omisión: **el capítulo se cierra en julio y
buena parte de la ingeniería del proyecto se construyó en agosto**.

Acciones: `A-V-01` … `A-V-08`.

---

## A-V-01 · 🔴 La cifra inválida «50/50» sigue en la Tabla 5.9

**Localización:** §5.7, Tabla 5.9 «Evidencias técnicas de verificación del sistema desarrollado»,
tercera fila.

> **Fila actual:** `Guardrails LLM/RAG | 50/50 adversariales rechazados; 20/20 legítimos
> aceptados | Validación de alcance conversacional.`

Este dato procede de `outputs/llm_guardrails_eval.json`, **se declaró inválido en la revisión de
julio de 2026** y contradice frontalmente lo que el propio documento reporta cuatro capítulos
después:

| | Tabla 5.9 (Cap. V) | §6.4.2 (Cap. VI) |
| :--- | :--- | :--- |
| Adversariales rechazados | 50/50 = **100 %** | 31/40 = **77,5 %** |
| Legítimos aceptados | 20/20 = **100 %** | 15/20 = **75,0 %** |

Un lector que compare ambos capítulos encuentra la contradicción de inmediato, y la lectura
natural es que las cifras del proyecto no son fiables. Es el hallazgo de mayor daño reputacional
por unidad de esfuerzo de corrección.

> **Reemplazo propuesto:**
>
> | Ámbito y seguridad del asistente | 31/40 solicitudes adversariales rechazadas (77,5 %); 15/20 consultas legítimas aceptadas (75,0 %) | Validación de alcance conversacional sobre el flujo de producción. El análisis detallado se desarrolla en §6.4.2. |

Evidencia correcta: `validacion_llm/resultados/eval_ambito_seguridad.csv`.

---

## A-V-02 · 🔴 «25 pruebas backend» — hay que volver a medir

Aparece en la Tabla 5.9 (`25 passed, 114 warnings in 1.45s`) y se repite en la Tabla 6.13.
El directorio `backend/tests/` contiene hoy **35 archivos de prueba**, incluidos varios que no
existían cuando se escribió esa cifra:

`test_release_rollback.py` · `test_release_manifest_contract.py` · `test_gpu_runtime_bootstrap.py`
· `test_compose_topology.py` · `test_deploy_env.py` · `test_artifact_registry_contract.py` ·
`test_runtime_artifact_manifest.py` · `test_stage10_release_evidence.py` ·
`test_stage10_acceptance_runner.py` · `test_stage8_release_pipeline.py` · `test_chat_retention.py`
· `test_chat_smoke.py`

**No estimar la cifra. Medirla:**

```bash
cd backend && python -m pytest -q 2>&1 | tail -5
```

Copiar la línea de resumen literal al documento, con la fecha de ejecución. Si alguna prueba
falla, **decirlo**: una prueba en rojo declarada vale más ante un comité que un número redondo
sin fecha.

---

## A-V-03 · 🔴 Sección nueva §5.10 — Evolución del asistente: rondas 4 a 6

**Localización:** después de §5.7, antes de §5.8 «Síntesis del desarrollo implementado».
Extensión estimada: 2–3 páginas.

### Por qué es la mejor sección de desarrollo que puede tener esta tesis

El manual (p. 12) dice, textual: *«En este acápite, debe ir explicando el trabajo que se va
realizando para lograr los objetivos estipulados para cada etapa. **Si hay alguna modificación,
debe de explicarse y justificar el por qué.**»*

Aquí hay un ciclo completo de ingeniería basada en evidencia —medición → diagnóstico de mecanismo
→ corrección → nueva medición— documentado, fechado y con cifras a ambos lados. Es exactamente lo
que el manual pide y hoy no está en el documento.

### Guion

**a) El instrumento que expuso el problema.** Una batería externa de 45 turnos midió algo que las
baterías A–E no medían: si la respuesta contiene contenido sustantivo **después de descontar el
andamiaje**. Resultado inicial: **13 de 45 turnos con contenido real, 0 de 15 en el modo
historial**, y turnos que devolvían un código de éxito con únicamente la frase de derivación. La
batería se verificó como válida antes de aceptar sus conclusiones.

**b) Los cuatro mecanismos exactos del fallo.** Esto es lo que da valor a la sección: no fueron
cuatro síntomas, fueron cuatro causas localizadas en el código.

1. **Ninguna validación exigía sustancia.** Una respuesta con una sola afirmación de tipo
   conversacional superaba todas las comprobaciones de forma vacua, y el requisito de derivación
   quedaba satisfecho por construcción justamente cuando la respuesta **era** solo la derivación.
2. **El clasificador de ámbito operaba sobre el fragmento, no sobre el enunciado expandido.** Las
   preguntas elípticas («¿de qué está compuesto?», «¿para qué sirven?») caían al rechazo por
   omisión y se descartaban, aunque la validación de seguridad se aplicaba sobre la forma
   expandida.
3. **El hallazgo del historial correspondía al estudio equivocado.** Los estudios llegan en orden
   cronológico ascendente y el mecanismo de respaldo tomaba la primera observación no cubierta, de
   modo que un estudio antiguo sin patrones sombreaba el hallazgo del estudio más reciente.
4. **Instrucciones en conflicto.** La instrucción para consultas con estudio seleccionado o
   historial presuponía la existencia de un parámetro solicitado y terminaba induciendo la
   derivación; para preguntas sin parámetro, el modelo emitía únicamente la frase de cierre.

**c) Qué se construyó.** Los cuatro componentes ya descritos en el diseño (§4.2.4): puerta de
contenido, completado determinista desde la base de datos, resolución de elipsis y seguimientos,
y reparación compacta con guardas de raíz —negar la derivación o declarar una incapacidad falsa
obliga a reescribir la respuesta entera, porque completarla enmascararía el error—. Añadir aquí
lo que en el diseño no cabe: **el principio rector fue que todo lo que la base de datos ya sabe
se responde desde la base de datos, y se arregla solo la parte dañada de la respuesta, nunca se
regenera entera**. La consecuencia práctica es que buena parte de las respuestas salen por
código, a costo de cómputo cero.

**d) La medición de cierre.** Tabla comparativa a tres columnas (corrida inicial · ronda 6 sobre
la configuración anterior · configuración vigente), tomada de
`../99_trazabilidad/CIFRAS_OFICIALES.md` §7.4:

| Métrica | Corrida inicial | Ronda 6 | Configuración vigente |
| :--- | ---: | ---: | ---: |
| Turnos con contenido real | 13/45 | 44/45 | 40/45 |
| Turnos sin respuesta | 1 (+13 vacíos) | 1 | **0** |
| Mediana global | ~46 s | 44 s | **17,6 s** |
| Historial con datos | 0/15 | 15/15 | 12/15 |
| Peor turno | 118 s | 161 s | **65 s** |

**e) La clase residual, declarada.** Los cuatro o cinco turnos flojos por corrida son la
variabilidad de las reparaciones que agotan los intentos y caen al último recurso. **Es una clase
de fallo conocida, documentada y no resuelta**, y así debe presentarse. El modelo se conservó
entre rondas: cuando responde, es exacto — todas las fallas eran del sistema, no del modelo.

**f) Instrumentación añadida.** Registro de la puntuación y los tiempos de espera de la
verificación de implicación textual de cada cita —la evidencia que faltaba para calibrar el
umbral— y poda de disco activada por presión de ocupación, tras dos incidentes reales de disco
lleno.

Evidencia: `RESUMEN_PARA_EQUIPO_2026-08-11.md`,
`validacion_llm/resultados/rondas45_2026-08-10/`, commits `663094b`…`2c082c5`.

---

## A-V-04 · 🔴 Sección nueva §5.9 — Cadena de release y contrato de runtime

**Localización:** después de §5.7, antes de §5.10. Extensión estimada: 2 páginas.

### Guion

**a) El manifiesto de versión como contrato.** Cada estado desplegable se materializa en un
manifiesto firmado que fija por compendio criptográfico: imágenes del backend y del frontend,
imagen del servidor de modelos, identidad y cuantización del modelo, configuración del proxy,
paquete de arranque del nodo de inferencia, y huella del índice vectorial junto a la revisión del
corpus que lo generó. Ficheros: `deploy/releases/release-manifest-*.json`,
`gpu-runtime-*.json`, `artifact-set-*.json`, `rag-summary-*.json`.

**b) La validación de arranque.** Dos capas independientes comprueban el modelo de unidad
gráfica, el controlador, la versión del servidor y el compendio del modelo. Si algo no coincide,
el servicio **no arranca degradado: la máquina se apaga**
(`hemovet-gpu-failure-shutdown.service`).

**c) Reversión verificada.** `rollback-release.sh` y `reconcile-release.sh` restauran la versión
anterior manteniendo activa la validación. Está cubierto por pruebas automatizadas
(`test_release_rollback.py`, `test_release_manifest_contract.py`, `test_gpu_runtime_bootstrap.py`).

**d) La migración de hardware como prueba del diseño.** Contarla como lo que fue —el manual pide
justificar las modificaciones—:

> «La cadena de validación estaba anclada al modelo de unidad gráfica anterior en sus dos capas,
> de modo que al sustituir el hardware apagó la máquina en dos ocasiones, comportándose
> exactamente como estaba diseñada. Se amplió el contrato para admitir ambos modelos manteniendo
> la validación de la reversión, se regeneró el manifiesto y el paquete de arranque se instaló
> mediante intervención sobre el disco fuera de línea. La dirección interna del nodo de inferencia
> se promovió a estática y se heredó en el nodo nuevo, de modo que **el backend no requirió
> ninguna modificación.**»

**e) El incidente de capacidad zonal.** Durante la migración se produjo un agotamiento real de
capacidad en la zona que impidió el arranque de varias familias de máquinas; el nodo de aplicación
quedó temporalmente en una configuración reducida. Declararlo: es un riesgo materializado, y el
manual valora que se expliquen las desviaciones.

> 📊 **Tabla ya generada** a partir de un contrato real:
> [`tablas/tabla_5.10_contrato_runtime_gpu.csv`](tablas/tabla_5.10_contrato_runtime_gpu.csv)
> · [versión para pegar](tablas/tabla_5.10_contrato_runtime_gpu.md). Muestra los campos del
> contrato con los compendios truncados a 16 caracteres. Los JSON crudos quedan en `fuentes/`
> y **no se imprimen**.
>
> Complementariamente, **Tabla 5.11 — Contratos y artefactos de la cadena de despliegue**
>
> | Contrato | Qué fija | Artefacto |
> | :--- | :--- | :--- |
> | `hemovet.release/v1` | Estado desplegable completo por compendio | `release-manifest-*.json` |
> | `hemovet.gpu-startup/v1` | Paquete y secuencia de arranque del nodo de inferencia | `gpu-runtime-*.json` |
> | `hemovet.availability/v1` | Contrato de disponibilidad de los servicios | — |
> | `hemovet.llm-provider/v1` | Contrato del proveedor de generación | — |
> | Conjunto de artefactos de modelo | Artefactos de aprendizaje automático por versión | `artifact-set-*.json` |
> | Resumen de corpus RAG | Huella del índice y revisión del corpus | `rag-summary-*.json` |

---

## A-V-05 · §5.2 — Una frase con la causalidad invertida

> **Texto actual:** «Se incluyó la etiqueta `PATRON_ANEMIA_REGENERATIVA` **porque** solo había
> seis casos positivos en el conjunto de prueba; por ello se consideró un resultado exploratorio
> con escaso respaldo.»

Dice literalmente que la etiqueta se incluyó *a causa de* tener pocos casos. Lo que el proyecto
hizo, y lo que §7.3 explica correctamente, es lo contrario.

> **Reemplazo:** «Se mantuvo la etiqueta `PATRON_ANEMIA_REGENERATIVA` entre las salidas oficiales
> **pese a** contar únicamente con seis casos positivos en el conjunto de prueba, dada su
> relevancia clínica; por esa razón se declara como resultado exploratorio con escaso respaldo
> estadístico.»

---

## A-V-06 · §5.5 — El corpus RAG sin magnitud

La sección describe correctamente la ingesta *offline* pero no dice cuánto corpus hay. Añadir:

> «La base de conocimiento reúne **1 252 documentos Markdown** curados y aprobados, organizados en
> material de origen, micro-fichas, políticas y revisiones expertas. Cada versión desplegada
> registra la huella del índice vectorial resultante y la revisión exacta del corpus que lo
> originó, de modo que un índice puede reconstruirse y verificarse contra su origen.»

Evidencia: `knowledge_base/` (subdirectorios `raw_md`, `microcards`, `policies`,
`expert_review`, `manifests`), `deploy/releases/rag-summary-*.json`.

---

## A-V-07 · §5.4 — Consolidación del frontend

Añadir una frase de cierre a la sección, que documenta una decisión de desarrollo real:

> «Durante el desarrollo coexistieron dos implementaciones del portal. La duplicación se resolvió
> consolidando una única implementación activa y retirando la obsoleta del control de versiones,
> con el fin de eliminar la ambigüedad sobre qué código se despliega.»

---

## A-V-08 · 🔴 Falta el manual de usuario

El manual EICT (p. 12) enumera lo que debe cumplir el producto final e incluye, textual:
**«Contener un manual de usuario»**, y lo repite en la lista de sub-ítems sugeridos: «Manual de
usuario (anexo o guía en línea)».

**No existe.** Es un requisito explícito, no una recomendación.

### Estructura mínima propuesta

Ocho apartados, con capturas del sistema real. Puede ir como anexo o como guía en línea enlazada
desde el portal —el manual admite ambas—:

1. Qué es HemoVet y qué **no** es (la advertencia de alcance clínico va primero, no al final).
2. Registro, inicio de sesión y modo invitado.
3. Registrar una mascota.
4. Cargar un hemograma: formatos admitidos y qué hacer si la extracción falla.
5. **Revisar y corregir los valores extraídos** — es el control humano obligatorio del sistema, y
   la encuesta de usabilidad lo señaló como uno de los aciertos mejor valorados.
6. Leer el resultado: patrones, probabilidades, colores semánticos y el significado de cada
   advertencia.
7. Usar el asistente: qué puede preguntar, qué no va a responder y por qué.
8. Historial, biblioteca y vigilancia comunitaria.

Las mejoras solicitadas por los participantes de la encuesta (leyenda de colores fija, glosario de
unidades, mini-tutorial) se cubren en parte con este manual: vale la pena decirlo en §7.5.

---

## Lo que NO hay que tocar del Capítulo V

- §5.1 Construcción del *pipeline* de datos y Tabla 5.1. ✅
- §5.2 Motor de aprendizaje automático, Tablas 5.2 y 5.3, Figuras 5.1–5.5. ✅ (salvo la frase de
  A-V-05)
- §5.3 Backend, Tablas 5.4 y 5.5. ✅ Los 12 módulos coinciden con el código.
- §5.6 Vigilancia poblacional y Tabla 5.8. ✅
- §5.7 salvo las dos filas corregidas de la Tabla 5.9. ✅
- §5.8 Síntesis — solo ampliar media frase para recoger §5.9 y §5.10.

## Checklist de cierre de este bloque

- [ ] Fila «50/50» de la Tabla 5.9 sustituida.
- [ ] `pytest` re-ejecutado y cifra literal copiada, con fecha.
- [ ] §5.9 redactada (cadena de release, ~2 páginas) + Tabla 5.10.
- [ ] §5.10 redactada (rondas 4-6, ~2-3 páginas) + tabla comparativa.
- [ ] Frase de §5.2 corregida.
- [ ] Magnitud del corpus RAG añadida a §5.5.
- [ ] Nota de consolidación del frontend en §5.4.
- [ ] **Manual de usuario producido** y referenciado desde §5.7 o desde los anexos.
- [ ] §5.8 ampliada para cubrir las dos secciones nuevas.
- [ ] Verificado que ninguna sección nueva adelanta análisis de resultados: **el Capítulo V
      construye, el VI analiza.**
