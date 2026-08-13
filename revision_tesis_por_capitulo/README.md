# Revision de tesis por capitulo

Esta carpeta es una mesa de trabajo para actualizar el informe final sin mezclar todo en un solo bloque.

Cada subcarpeta contiene:

- `README.md`: que cambiar, donde reforzar y que contenido agregar.
- `evidencia/`: CSV, JSON, documentacion o artefactos que respaldan el texto.
- `imagenes/`: figuras listas para insertar cuando aplica.

Orden sugerido de trabajo:

1. `01_preliminares`
2. `05_capitulo_iii_metodologia`
3. `07_capitulo_v_desarrollo`
4. `08_capitulo_vi_resultados`
5. `09_capitulo_vii_conclusiones`
6. `10_referencias_anexos`

Los capitulos I, II y IV no estan vacios, pero deben actualizarse para que no contradigan el sistema actual. La prioridad alta esta en metodologia, desarrollo, resultados y conclusiones.

## Estado actual (revisado 11 jul 2026)

Version vigente del documento: **`.docx (4)`**. El `.md (1)` es una exportacion mas
antigua en contenido (le falta el Capitulo VII). Trabajar sobre el `.docx`.

Bloqueantes abiertos, en orden:

1. **Capitulo VII (Conclusiones) VACIO** en ambas versiones — solo esta el encabezado.
   Redactarlo completo con la estructura de `09_capitulo_vii_conclusiones/README.md`.
2. **Seccion 6.4 con cifras invalidas** (50/50 de `llm_guardrails_eval.json`, codigo
   huerfano). Sustituir por: 6.4.A seguridad/alcance (LISTO — ver
   `08_.../cambios_2026-07-11/capitulo_vi_6.4_resultados_llm/6.4_resultados_llm.md` y notebook `13_validacion_llm_chat.ipynb`)
   y 6.4.B exactitud de contenido (PENDIENTE — correr `validacion_llm/` en la VM).
3. **Validacion LLM formal sin correr:** `validacion_llm/resultados/` vacio, rubricas
   veterinarias sin llenar.
4. **Revisar manualmente los 14 FAIL** de `diagnostico_directo` de la evaluacion del
   companero: son de politica de alcance, no de seguridad (respuestas seguras que el
   validador marca por definicion). Confirmar y decidir el criterio de alcance.

Importantes: reconciliar cifras (38 vs 43 features; 2,454 vs 2,721 dataset) en todos
los capitulos; actualizar TOC + listas de tablas/figuras/anexos.

La duplicacion historica del frontend fue resuelta: `frontend_4/` es la unica
implementacion activa y la carpeta obsoleta `frontend/` fue retirada.
