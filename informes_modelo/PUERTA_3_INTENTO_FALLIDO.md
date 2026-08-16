# Puerta 3 — primer intento: el cambio NO se aplicó

**Fecha:** 2026-08-13 · **Commit medido:** `b15602a0` · **Datos:** `validacion_llm/resultados/puerta3_2026-08-13/puerta_3.jsonl`

## Qué pasó

Se cambió el defecto de `docker-compose.prod.yml` a
`CHAT_STRUCTURED_OUTPUT_ENABLED:-0`, se desplegó en verde y se corrieron las 45
preguntas. **El resultado NO es el de la Fase 3**, y tres señales medidas lo
demuestran:

| Señal | Si el sobre estuviera apagado | Medido |
|---|---|---|
| Ruta `last_resort` | imposible (el interruptor la desactiva) | **9 disparos** |
| Tokens de salida | ~68 % menos | **372 vs 321: SUBIERON un 16 %** |
| Validez de primera pasada | debía subir | 77,78 %, igual que la Puerta 0 |

## Causa raíz

`[MEDIDO]` `.env.production:228` contiene `CHAT_STRUCTURED_OUTPUT_ENABLED=1`.

El compose usa `${CHAT_STRUCTURED_OUTPUT_ENABLED:-0}`, y el `:-` solo aplica
**cuando la variable no está definida**. El fichero de entorno la define, así
que el defecto del compose es código muerto. La variable viaja en
`PRODUCTION_ENV_B64`, no en el repositorio.

## Lo que esta corrida SÍ mide

Es una **segunda observación independiente de la línea base**, con las Fases 0 y
2 desplegadas. Comparada con la Puerta 0 del mismo día:

| | Puerta 0 | Este intento |
|---|---|---|
| `provider_calls` | {1: 36, 3: 9} | {1: 35, 2: 1, 3: 9} |
| Validez 1ª pasada | 77,8 % | **77,78 %** |
| p50 | 17,37 s | 18,32 s |
| Prefijo turnos 2+ | 72-1368 % | **70,6-117,5 %** |

`[MEDIDO]` La reproducibilidad es alta: 77,8 % en ambas.

`[MEDIDO]` **La Fase 2 no mejoró la reutilización de prefijo**: sigue por encima
del 70 % en los tres ámbitos, muy lejos del 25 % que exige la Puerta 2. El
reordenado del prompt y la instrucción fuera del *system* **no bastaron**.
Queda como hipótesis viva qué sigue invalidando el prefijo.

## Cómo se activa de verdad

El interruptor vive en el secreto, no en el repo:

```bash
# desde la VM de produccion, que es donde vive el .env base
bash scripts/actualizar_secreto_produccion.sh
# anadir CHAT_STRUCTURED_OUTPUT_ENABLED=0 al mapa `valores` del script
gh secret set PRODUCTION_ENV_B64 < <(base64 -w0 ...)
git commit --allow-empty -m "redeploy" && git push
```

**No se hizo en esta sesión** porque el único `.env.production` local es del
5-ago y contiene `OLLAMA_NUM_PREDICT=2048`, `OLLAMA_CONTEXT_LENGTH=65536` y
`CHAT_MAX_INPUT_TOKENS=60000` — valores obsoletos. Empujarlo como secreto
revertiría la configuración de producción a un estado anterior sin medirlo.
Hay que partir del `.env` vivo de la VM, leído por IAP.

## Estado del invariante

`provider_calls == 1` sigue **sin cumplirse**: 10 de 45 turnos usan más de una
llamada. La Puerta 3 no se ha medido todavía.
