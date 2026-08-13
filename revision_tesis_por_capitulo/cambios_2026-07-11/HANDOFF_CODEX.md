# Handoff para continuar (11/7/2026)

Estado del trabajo de hoy sobre la validación del LLM y la tesis, para que otro agente
(Codex) continúe sin perder contexto.

## Qué se hizo hoy

1. **Se corrieron las 5 baterías de `validacion_llm/` en la VM de producción** (`hemovet-prod`,
   modelo `llama3.2:3b`). Resultados en `validacion_llm/resultados/`:
   - A (ámbito/seguridad, 90 casos): adversariales 31/40 (77.5%), legítimos 15/20 (75%),
     fuera de ámbito claro 17/30 (56.7%). → `eval_ambito_seguridad.csv`, `eval_llm_pipeline_real.json`
   - B (robustez typos, 20): 20/20 sustantivas. → `eval_robustez_ortografica.csv`
   - C (memoria, 17 turnos): 15 ok, 2 timeouts. → `eval_memoria_multiturno.csv`
   - D (consistencia, 25 ejec): Jaccard medio 0.84, 3/5 consistentes. → `eval_consistencia.csv`, `resumen_consistencia.csv`
   - E (exactitud, 30): 29 respondidas, 1 timeout (CA-028). → `exactitud_contenido_crudo.csv` + rúbrica.

2. **Se arreglaron 4 bugs del harness** (solo en local + contenedor; FALTA COMMITEAR):
   - `_comun.py`: `import app.db.base` para registrar modelos ORM (FK chat_sessions→pets).
   - `correr_consistencia.py`: agregado flag `--user-id`.
   - `correr_eval_pipeline_real.py`: agregado `--user-id` + salida JSON a `RESULTADOS_DIR` (antes `/app/outputs` era solo-lectura).
   - Nuevo `smoke_test.py` para verificar el pipeline antes de corridas largas.

3. **Documentos de redacción** en `revision_tesis_por_capitulo/cambios_2026-07-11/`:
   - `METODOLOGIA_VALIDACION_LLM_LITERATURA.md` — respaldo bibliográfico (QUEST, Med-PaLM, red-teaming, RAG).
   - `cambios_2026-07-11/capitulo_iii_3.7_metodologia/3.7_metodologia_validacion.md`, `cambios_2026-07-11/capitulo_vi_6.4_resultados_llm/6.4_resultados_llm.md`, `cambios_2026-07-11/capitulo_vii_7.3_limitaciones/7.3_limitaciones.md`.
   - `CAMBIOS_DOCUMENTO_DE_GRADO.md`, `VALIDACION_LLM_2_PENDIENTE.md`.

## Actualización 12/7/2026 — validación de exactitud COMPLETADA

Los **dos veterinarios reales ya llenaron la rúbrica**. Sus juicios están en
`validacion_llm/resultados/evaluador_1.csv` y `evaluador_2.csv` (30 casos cada uno,
columnas `correctitud`, `cita_apropiada`, `seguridad_clinica`, `comentario`). Con eso:

- **Notebook nuevo:** `notebooks/validacion/14_validacion_llm_exactitud.ipynb` (estilo del
  notebook 13). Ejecutado; genera 3 figuras en `validacion_llm/resultados/figuras/`
  (`fig1_correctitud.png`, `fig2_seguridad_citas.png`, `fig3_concordancia.png`), también
  ahora en `cambios_2026-07-11/capitulo_vi_6.4_resultados_llm/6.4.5_*.png`.
- **Resultados:** 30/30 seguras (ambos), 83.3 % correctas/parciales (IC95 70–97 %), 0
  alucinadas, citas apropiadas 63.3 %. 5 respuestas incorrectas (errores de CONTENIDO, no
  de seguridad): CA-001, CA-003, CA-007, CA-010, CA-016.
- **Concordancia:** acuerdo obs. 90–100 %, κ Cohen 0.841, κ ponderado (cuad.) 0.904.
  Refuerzo con **PABAK y AC1 de Gwet** (robustos a la *paradoja de kappa*, aplicable aquí
  porque seguridad = 100 % anula la varianza y deja κ indefinido).
- **Redacción actualizada:** `cambios_2026-07-11/capitulo_vi_6.4_resultados_llm/6.4_resultados_llm.md` §6.4.4 (Tablas 6.10 y 6.11),
  `cambios_2026-07-11/capitulo_iii_3.7_metodologia/3.7_metodologia_validacion.md` (métodos de concordancia), `cambios_2026-07-11/capitulo_vii_7.3_limitaciones/7.3_limitaciones.md`,
  y `METODOLOGIA_VALIDACION_LLM_LITERATURA.md` §5b (respaldo bibliográfico de PABAK/Gwet).

## Pendiente (en orden)

1. **Commitear los 4 arreglos del harness** (ver arriba).
2. **Aplicar las redacciones** al `.docx (4)`: pegar 3.7, 6.4 (reemplazando el 50/50 de
   P1432 y P1916/Tabla 6.9) incluyendo la 6.4.4 ya completa con Tablas 6.10/6.11 y
   figuras `fig64_*.png`, y 7.3.
3. **Redactar el Capítulo VII completo** (sigue vacío en el docx).
4. **Corregir 43 vs 38 características** (P322/P734 = 43; P326 = 38 → cambiar a 43).
5. Opcional: relanzar el caso E con timeout transitorio (CA-028).

## Acceso a la VM (para relanzar baterías o el notebook)

- `gcloud compute ssh ubuntu@hemovet-prod --zone=us-central1-a --ssh-key-file=~/.ssh/hemovet_oracle`
- Contenedor backend: `hemogramas-proyectoicc-backend-1` (uvicorn :8000).
- IDs reales usados: `user_id=62980eea-e2c7-42d3-bb24-26de8e7bd24e`, `analysis_id=aabbaa43`.
- Correr batería (dentro del contenedor): `docker exec -d -w /app/backend <B> python3 ../validacion_llm/scripts/<script>.py --user-id <UID> --analysis-id <AID>`.
- Antes de correr, `docker cp validacion_llm <B>:/app/validacion_llm` (la imagen no la incluye).
- Smoke test primero: `python3 ../validacion_llm/scripts/smoke_test.py --user-id <UID> --analysis-id <AID>`.
