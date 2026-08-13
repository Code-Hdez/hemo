# Tabla E.4. Manifiesto de las figuras del análisis.

> Tabla lista para pegar. Datos verificados contra el artefacto de origen.
> **Fuente:** `06_analisis/figuras/MANIFIESTO.json`

| Id | Título de la figura | n | Condición | Procedencia | Compendio (PDF) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| A1 | Ventanas de GPU: lo que el log registra y lo que sólo consta en las trazas | 6 | Medido | 99_operacion/log_instancia.md; 04_trazas/turns.ndjson; 04_trazas/turns_replica_estricta.ndjson | 326e75cd37fca3f2… |
| A2 | Composición del corpus de evidencia previa | 208 | Medido | 01_auditoria_previa/inventario.ndjson | dc5df838d74d31b3… |
| A3 | Qué registra cada instrumento: cobertura comparada | 17 | Medido | 01_auditoria_previa/copia/bateria_latencias_2026-08-07.jsonl; 04_trazas/turns.ndjson | b1dc9d1ed44091b7… |
| A4 | Reconstrucción del protocolo del 7-ago: semáforo de las quince preguntas | 15 | Medido | 01_auditoria_previa/protocolo_antiguo_reconstruido.md | 0731502dab4bf3c3… |
| A5 | Veredicto doble de comparabilidad | 2 | Derivado | 01_auditoria_previa/veredicto_comparabilidad.md | 7b7d9acc4bac0bd9… |
| B1 | Ficha de identidad del sistema medido | 8 | Medido | 06_analisis/fase2_canario_y_ic.json | 0bf2e8dbb8bd4b7d… |
| B2 | Las limitaciones declaradas y en qué momento se declararon | 17 | Medido | 07_informes/LIMITACIONES.md | f0c2c582640d66ce… |
| B3 | Verificación de identidad de modelo en cada respuesta | 115 | Medido | 04_trazas/turns.ndjson; 04_trazas/turns_replica_estricta.ndjson | b9e9ba66a16ad9e4… |
| B4 | Modelos presentes en el servidor de producción | 2 | Medido | 06_analisis/fase2_canario_y_ic.json | b725f219dc51d219… |
| C1 | Techos de decodificación y rendimiento medido | 100 | Derivado | 05_derivados/tpot_serie_n100.json | 873530d4eb3ab129… |
| C2 | Distribución del tiempo por token de salida (TPOT) | 100 | Medido | 05_derivados/tpot_serie_n100.json | bd571d5e81eded4a… |
| C3 | Distribución bootstrap de la mediana del TPOT | 100 | Derivado | 05_derivados/tpot_serie_n100.json | 58045bbfe339981f… |
| C4 | Utilización del ancho de banda de memoria (MBU) en contexto | 100 | Derivado | 05_derivados/tpot_serie_n100.json | eb8489c508269181… |
| C5 | Ablación de la gramática: los dos brazos por separado | 60 | Medido | 05_derivados/ablacion_gramatica.json | 61e7fd946cb01dd4… |
| C6 | Lo predicho frente a lo medido: la sobrecarga de gramática | 60 | Medido | 05_derivados/ablacion_gramatica.json | 726da7d70235ac62… |
| C7 | Determinismo intra-máquina: 20 prompts × 5 repeticiones | 100 | Derivado | 06_analisis/fase2_canario_y_ic.json | 5cb29f416299af73… |
| C8 | Prefill y decodificación sobre el mismo eje | 100 | Medido | 06_analisis/fase2_canario_y_ic.json | 6b34594f7a094d7e… |
| D1 | Desenlace de los turnos por modo | 45 | Medido | 04_trazas/turns.ndjson | 3f31459a13edf40a… |
| D2 | Latencia por posición de turno y modo | 45 | Medido | 04_trazas/turns.ndjson | 914ed6dfa8feed02… |
| D3 | Distribución de latencia por modo | 45 | Medido | 04_trazas/turns.ndjson | df30fd2854cf0126… |
| D4 | La frontera de la ventana, turno a turno y modo a modo | 9 | Medido | 04_trazas/turns.ndjson | f2f24f633f336ed3… |
| D5 | Qué responde el sistema al preguntarle por el principio de la conversación | 3 | Medido | 04_trazas/turns.ndjson | 6db9d97261871e9e… |
| D6 | Verificación mecánica contra la tabla de verdad sellada | 9 | Medido | 02_fixtures/verdad.json; 04_trazas/turns.ndjson | d466f091bace2550… |
| D7 | Tasa de alucinación numérica y su intervalo de confianza | 9 | Derivado | 02_fixtures/verdad.json; 04_trazas/turns.ndjson | 9621454522dfa1a5… |
| D8 | Cobertura real de la rúbrica de cinco ejes | 5 | Medido | 07_informes/LIMITACIONES.md; 02_fixtures/criterios.md; 03_hipotesis/preregistro.md | d0746a373c988a06… |
| D9 | El hemograma de referencia | 18 | Medido | 02_fixtures/fixture_hemograma.json | d8c3bc64fe773c40… |
| E1 | Latencia por caso: L4 → A100 | 64 | Medido | 04_trazas/turns_replica_estricta.ndjson | d055a6843f88fc78… |
| E2 | Distribución de las diferencias pareadas | 64 | Derivado | 04_trazas/turns_replica_estricta.ndjson | 60d0b867c7768bfd… |
| E3 | Función de distribución acumulada de la latencia | 64 | Medido | 04_trazas/turns_replica_estricta.ndjson | 3b4e307fb0579f1e… |
| E4 | La puerta de aceptación: coincidencia de identificadores de fallo | 70 | Medido | 04_trazas/turns_replica_estricta.ndjson | 163e0d62b65bfcf7… |
| E5 | Naturaleza de los fallos: dos fenómenos distintos | 23 | Medido | 04_trazas/turns_replica_estricta.ndjson | 2e41c742d60e3cc8… |
| E6 | Proporción de turnos sin respuesta, con intervalo de confianza | 70 | Derivado | 04_trazas/turns_replica_estricta.ndjson | 7d3478e156210252… |
| F1 | Tablero de las diez hipótesis pre-registradas | 10 | Derivado | 03_hipotesis/preregistro.md; 07_informes/INFORME_RECARACTERIZACION_A100.md | 0d99791699381687… |
| F2 | Los cinco efectos medidos, cada uno en su escala | 5 | Derivado | 04_trazas/turns_replica_estricta.ndjson; 05_derivados/ablacion_gramatica.json; 02_fixtures/verdad.json | 0542e6c1f1442579… |
| F3 | Qué niveles del esquema de trazas llegó a poblar la campaña | 115 | Medido | 04_trazas/turns.ndjson; 04_trazas/turns_replica_estricta.ndjson; 07_informes/LIMITACIONES.md | 37ce57c102082874… |
| F4 | Potencia del diseño | 6 | Derivado | 04_trazas/turns.ndjson | 55d63273ca010de3… |
| X1 | Descomposición prefill/decode por turno | None | Ausencia |  | b130a7a00e29aca3… |
| X2 | Crecimiento del prefill a lo largo de los 15 turnos | None | Ausencia |  | 0a87e6e417441b1b… |
| X3 | ttft_per_1k_in por posición de turno | None | Ausencia |  | c386f312f7a4ca7e… |
| X4 | Relojes, temperatura y potencia durante la medición | None | Ausencia |  | 346b179dc196893d… |
| X5 | Comparación de decode, MBU o TPOT entre L4 y A100 | None | Ausencia |  | 30ae98bc0e6a8b4a… |
| X6 | Verificación de identidad de modelo entre corridas | None | Ausencia |  | b2001a99f6a2322e… |
| X7 | Canario de equivalencia inter-máquina | None | Ausencia |  | a3987a7438800cfa… |
| X8 | Tendencia de parámetros en el historial | None | Ausencia |  | 64e4d9195e687b6a… |
| X9 | Radar completo de los cinco ejes de la rúbrica | None | Ausencia |  | e78a185ea72e12a0… |

*Tabla E.4. Manifiesto de las figuras del análisis.*