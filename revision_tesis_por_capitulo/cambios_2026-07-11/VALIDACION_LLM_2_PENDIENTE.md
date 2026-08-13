# Segunda validación del LLM (exactitud de contenido) — ✅ COMPLETADA (12/7/2026)

> **ESTADO: HECHA.** La batería se corrió en la VM y **los dos veterinarios reales ya
> llenaron la rúbrica** (`validacion_llm/resultados/evaluador_1.csv` y `evaluador_2.csv`).
> El análisis, las tasas, la concordancia (κ + PABAK + AC1 de Gwet) y las figuras están en
> `notebooks/validacion/14_validacion_llm_exactitud.ipynb`, y la redacción en la
> subsección **6.4.4** (`cambios_2026-07-11/capitulo_vi_6.4_resultados_llm/6.4_resultados_llm.md`, Tablas 6.10 y 6.11).
> Resultado: **30/30 seguras, 83.3 % correctas/parciales, 0 alucinadas, κ = 0.841.**
> El checklist de abajo se conserva como registro histórico del procedimiento seguido.

**11/7/2026.** Esta es la validación formal del asistente (`validacion_llm/`). Es distinta
de la del compañero (`tools/llm_cbc_eval/`, que mide seguridad/alcance y ya está lista).
Esta mide la **corrección clínica del contenido** con juicio de dos veterinarios — la
prioridad declarada por la asesora.

Va en la subsección **6.4.4** del documento.

## Estado verificado

- Scripts: compilan sin errores, listos para correr.
- Bancos de preguntas: completos (A: 90, B: 20, C: 17 turnos, D: 5×5, E: 30).
- Rúbrica veterinaria: las 30 preguntas están cargadas, pero **respuesta del asistente,
  fuentes y las tres columnas de juicio están VACÍAS**. Se llenan al correr la batería
  (respuesta/fuentes) y con los médicos (juicio).
- Carpeta `resultados/`: vacía. No hay ninguna corrida aún.

## Lo que hay que hacer (en orden)

- [ ] **1. Levantar el stack en la VM** (`hemovet-prod`): los 6 contenedores `healthy`
  (Postgres, Chroma, Ollama, backend...). Ver `validacion_llm/COMO_CORRER_EN_VM.md`.

- [ ] **2. Conseguir un `analysis_id` real.** Cargar un hemograma como usuario en la app
  y anotar su `analysis_id` y `user_id`. Lo necesitan las baterías C (memoria) y E
  (exactitud) para los casos que dependen de un hemograma cargado; sin él, esos casos
  se **omiten** (no fallan, pero pierdes esa evidencia).

- [ ] **2.5. Smoke test (verificar ANTES de la corrida larga).** Correr
  `validacion_llm/scripts/smoke_test.py`: en ~30 s prueba 3 casos (uno legítimo, uno
  de dosis adversarial y —si pasas `--analysis-id`— uno con hemograma) y dice ✓/✗ si
  el pipeline responde. Si falla aquí, arréglalo antes de gastar 45 min. Comando dentro
  del contenedor:
  `docker exec -w /app/backend <backend> python3 ../validacion_llm/scripts/smoke_test.py`

- [ ] **3. Copiar la carpeta al contenedor y correr las 4 baterías** (en `tmux`, ~30-45
  min por el modelo en CPU). Comandos exactos en `COMO_CORRER_EN_VM.md`:
  - A+B: `correr_eval_pipeline_real.py`
  - D: `correr_consistencia.py`
  - C: `correr_memoria_multiturno.py --user-id UID --analysis-id AID`
  - E: `correr_exactitud_contenido.py --user-id UID --analysis-id AID`

- [ ] **4. Sacar los resultados** del contenedor al host y del host a tu repo
  (`docker cp` + `gcloud scp`). Quedan en `validacion_llm/resultados/`.

- [ ] **5. Enviar la rúbrica a los 2 veterinarios.** Cada uno recibe
  `rubrica_contenido_llm.csv` (ya con pregunta, respuesta del asistente y fuentes) y
  llena tres columnas por pregunta: `correctitud` (correcto / parcialmente_correcto /
  incorrecto / alucinado), `cita_apropiada` (si/no), `seguridad_clinica` (si/no).
  Devuelven `rubrica_contenido_llm_medico1.csv` y `_medico2.csv`.

- [ ] **6. Calcular las métricas** con las rúbricas completas:
  - % correcto / parcial / incorrecto / alucinado
  - % de citas apropiadas
  - % de seguridad clínica
  - (opcional) kappa de Cohen entre los dos médicos
  - Baterías A-D: tasas de rechazo/aceptación, robustez ante typos, retención de
    contexto multi-turno, consistencia de citas.

- [ ] **7. Redactar la subsección 6.4.3** con esas cifras.

## Qué se puede preparar ahora (antes de correr)

- Cuando tengas `validacion_llm/resultados/` con datos, puedo generar el **notebook de
  análisis** (equivalente al `13_validacion_llm_chat.ipynb`) que consuma esos CSV,
  calcule las tasas y produzca las figuras y la tabla para 6.4.3.
- Mientras tanto, este checklist y el borrador `cambios_2026-07-11/capitulo_vi_6.4_resultados_llm/6.4_resultados_llm.md`
  (subsección 6.4.3 marcada como pendiente) ya dejan el hueco listo en el documento.

## Riesgo a vigilar

La corrida completa es larga en CPU; **córrela dentro de `tmux`** para que sobreviva a
un corte de SSH. Es el mismo patrón donde la evaluación del compañero se cayó por token
expirado; aquí el harness corre dentro del contenedor (no por HTTP con token), así que
ese problema puntual no aplica, pero el tiempo largo sigue siendo el riesgo.
