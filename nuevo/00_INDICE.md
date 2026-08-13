# Archivo HemoVet — informes, logs y datos

Copiado el 9-ago-2026. **Este directorio ya tenia contenido previo** (carpetas
`1_investigacion_fase1/` … `7_auditoria_logs/`, tokenizers): no se sobrescribio
nada, las carpetas nuevas van en paralelo. Hay duplicacion deliberada entre
`04_auditoria_2026-08-08/` y `7_auditoria_logs/`, y entre `03_resultados_bateria/`
y `6_datos_bateria/`.

## Lo nuevo de estas sesiones

| carpeta | que hay |
|---|---|
| `01_salidas_fase21/` | **los JSON que importan**: `00_contexto` (relevo), `01_aceptacion` (criterio sellado, sha256 `797b4865e85a8332`), `02_m15` (el poller), `07_hallazgos_pendientes`, `08_h02` |
| `02_informes_md/` | 33 informes en markdown, incluido el documento de tesis |
| `03_resultados_bateria/` | la bateria del 7-ago (`bateria_latencias_2026-08-07.jsonl`, 70 turnos) y la referencia de entradas |
| `04_auditoria_2026-08-08/` | telemetria cruda del backend, timings de Ollama, correlacion |
| `05_casos_y_verdad_terreno/` | los 70 casos y las verdades de terreno (21 con valor esperado) |
| `06_esquemas/` | esquemas JSON de la fase 21 |
| `07_logs_y_scripts_de_sesion/` | salidas de los experimentos de esta sesion y los scripts que los produjeron |
| `_CONTIENE_SECRETOS/` | **no compartir**. Ver su LEEME.txt |

## Por donde empezar

1. `01_salidas_fase21/00_contexto.json` — estado paso a paso y que falta
2. `01_salidas_fase21/01_aceptacion.json` — el criterio pre-registrado, cinco NO_MEDIDO
3. `03_resultados_bateria/bateria_latencias_2026-08-07.jsonl` — la unica medicion de comportamiento que existe

## Aviso sobre las cifras

Varias cifras que circulan en los informes `.md` antiguos estan **corregidas** en
los JSON de `01_salidas_fase21/`: el p50 honesto es 59,1 s (no 32,8), son 70
turnos y 133 llamadas (no 73 y 138), y el reparto es 36/8/23/3. Cuando discrepen,
manda el JSON.
