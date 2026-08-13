# Etapa 4 — Separación de Docker Compose

Fecha: 2026-08-02. Estado: **COMPLETADA Y VALIDADA EN RAMA; NO DESPLEGADA**.

## Objetivo

Separar la topología de aplicación de los runtimes Ollama sin mover
`llm_chat`, RAG, ChromaDB, PostgreSQL ni datos clínicos fuera del monolito de
producción. La composición debe fallar cerrada si producción incorpora Ollama,
si GPU incorpora servicios de aplicación o si una imagen desplegable no está
fijada por digest.

## Estado inicial

- `docker-compose.yml` contenía aplicación, Ollama y `ollama_setup`.
- `docker-compose.prod.yml` heredaba esos servicios y mantenía Ollama local.
- `docker-compose.gpu.yml` era un overlay; combinado con la base arrastraba
  backend, frontend, PostgreSQL, ChromaDB y RAG a la VM GPU.
- backend dependía de `ollama_setup` en toda topología.
- varias imágenes externas usaban tags mutables.

## Alcance aplicado

| Destino | Archivos | Servicios efectivos |
| --- | --- | --- |
| Desarrollo | `docker-compose.yml` + `docker-compose.local.yml` | `backend`, `frontend`, `db`, `chroma`, `rag_ingest`, `ollama`, `ollama_setup` |
| Producción | `docker-compose.yml` + `docker-compose.prod.yml` | `backend`, `frontend`, `db`, `chroma`, `rag_ingest`, `volume_permissions`, `caddy` |
| GPU | `docker-compose.gpu.yml` únicamente | `ollama`, `ollama_setup` |

`docker-compose.local-caddy.yml` continúa siendo un tercer overlay opcional
para desarrollo. `docker-compose.qa.yml` continúa combinándose solo con la base
de aplicación.

## Elementos fuera de alcance

- No se ejecutó `docker compose up`, `pull`, `build`, `run`, `down` ni `restart`.
- No se modificaron contenedores, volúmenes o servicios productivos.
- No se modificó GitHub Actions; su rediseño continúa en la Etapa 8.
- No se modificaron VMs, GCP, red, firewall, IAM, discos, IPs o metadata.
- No se encendió `hemovet-llm-gpu`.
- La degradación funcional del backend y frontend con la GPU apagada pertenece
  a la Etapa 5.
- La reconciliación, identidad real del modelo y arranque GPU pertenecen a la
  Etapa 6.

## Decisiones

### D-010 — Base de aplicación sin runtime LLM

**Alternativas consideradas:** duplicar un Compose completo por destino;
intentar eliminar servicios heredados con overrides; convertir la base en la
aplicación común y añadir Ollama solo localmente.

**Opción seleccionada:** `docker-compose.yml` contiene la aplicación compartida
y `docker-compose.local.yml` añade el runtime local.

**Motivo:** minimiza duplicación y hace imposible que producción herede Ollama
por usar base + overlay productivo.

**Consecuencias:** desarrollo debe usar el overlay local; `.env.example` ya lo
selecciona mediante `COMPOSE_FILE`.

**Rollback:** revertir los archivos Compose en un commit normal. El volumen
local conserva la clave histórica `ollama-data`; no fue eliminado ni recreado.

### D-011 — Compose GPU autónomo y fail-closed

**Alternativas consideradas:** overlay NVIDIA sobre la aplicación o archivo
independiente.

**Opción seleccionada:** `docker-compose.gpu.yml` se renderiza solo y admite
exactamente `ollama` y `ollama_setup`.

**Motivo:** evita que la VM GPU reciba código, secretos, datos o servicios de
aplicación.

**Consecuencias:** combinar el archivo GPU con base/prod es una operación no
soportada y el validador nunca lo hace. El workflow vigente aún no integra este
contrato y no debe interpretarse como listo para despliegue.

**Rollback:** revertir el Compose. Como no se inició, el volumen
`hemovet_gpu_ollama_models` no fue creado ni requiere eliminación.

### D-012 — Bind privado explícito, no publicación implícita

**Alternativas consideradas:** `0.0.0.0:11434`, loopback o IP privada requerida.

**Opción seleccionada:** publicar `11434` con sintaxis larga y
`OLLAMA_BIND_ADDRESS` obligatorio. La plantilla usa `10.128.0.3`, verificada en
la línea base, y el validador exige una IP privada no loopback/no wildcard.

**Motivo:** `OLLAMA_HOST=0.0.0.0:11434` solo abre el listener dentro del
contenedor; el bind del host decide la interfaz accesible entre VMs.

**Consecuencias:** la IP debe revalidarse antes del primer arranque. Esta medida
no sustituye el firewall restrictivo de la Etapa 7.

**Rollback:** detener el stack futuro y volver al archivo anterior; no cambiar
la NIC ni la reserva de IP.

### D-013 — Imágenes desplegables por digest

**Alternativas consideradas:** tags semánticos, tags por SHA o referencias
canónicas por digest.

**Opción seleccionada:** todas las imágenes externas se declaran con
`tag@sha256` o `repository@sha256`; backend, frontend y runtime GPU usan los
digests reales publicados en la Etapa 3.

**Motivo:** el tag conserva legibilidad, pero solo el digest determina bytes.

**Consecuencias:** producción elimina `build` del resultado efectivo con
`!reset null`; `rag_ingest` usa exactamente la imagen backend. Cada release
futura debe sustituir ambas referencias desde `hemovet.release/v1`.

**Rollback:** seleccionar de forma conjunta los digests de un manifiesto
anterior. No reconstruir imágenes durante rollback.

## Digests fijados

| Componente | Referencia/digest |
| --- | --- |
| backend | `sha256:c20b932993c97d6078d04033f72d2de132381f6a6a06580dc65be74d52b5191f` |
| frontend | `sha256:55b82e9e868247fc71d764f932610f0849db93fbe88b60261683f7894d305d7f` |
| ollama-runtime | `sha256:b526b1d4bc30d0cc641e0d2a186034b327c97de0171b1a47ce1c917d79604e5f` |
| Ollama upstream local | `sha256:bfc9c6d53cc6989aa5131a6fde6b162b2802d4d337657f3253b5f69579bddeee` |
| PostgreSQL 16 Alpine | `sha256:57c72fd2a128e416c7fcc499958864df5301e940bca0a56f58fddf30ffc07777` |
| ChromaDB 1.5.9 | `sha256:1e0b73a187a28757c572acba508c46f48c9e8b0acaf5c20e6d95cdedce1acdf6` |
| Caddy 2.11.4 Alpine | `sha256:5f5c8640aae01df9654968d946d8f1a56c497f1dd5c5cda4cf95ab7c14d58648` |
| Alpine 3.22.1 | `sha256:4bcff63911fcb4448bd4fdacec207030997caf25e9bea4045fa6c8c44de311d1` |

Los cuatro últimos digests se resolvieron en modo lectura con
`docker buildx imagetools inspect`. No se descargaron ni iniciaron imágenes.

## Contratos de entorno

- Producción exige `HEMOVET_BACKEND_IMAGE` y `HEMOVET_FRONTEND_IMAGE` con el
  paquete correcto de Artifact Registry y referencia `@sha256`.
- Producción rechaza `OLLAMA_BASE_URL=http://ollama:11434/`; exige una IP privada
  o DNS interno y no contiene variables de bootstrap/servidor Ollama.
- La GPU usa `deploy/gpu/compose.env.example`, que contiene solo configuración
  no sensible de runtime. No contiene credenciales, DB, Chroma o RAG.
- Desarrollo conserva `OLLAMA_AUTO_PULL`, límites de servidor y el volumen
  local. Ninguno de esos valores se vuelve requisito del entorno productivo.

## Validador ejecutable

```bash
PYTHONPATH=backend python backend/scripts/validate_compose_topology.py
```

El validador renderiza cada destino mediante `docker compose config --format
json` sin imprimir el entorno y comprueba:

- conjunto exacto de servicios;
- dependencias solo dentro del mismo proyecto Compose;
- ausencia de Ollama y de puerto `11434` en producción;
- ausencia de aplicación/configuración clínica en GPU;
- bind privado de GPU y reserva NVIDIA;
- volumen persistente `/root/.ollama`;
- imágenes por digest y ausencia de builds productivos/GPU;
- igualdad de imagen entre backend/RAG y entre Ollama/bootstrap.

## Validaciones ejecutadas

```text
validate_compose_topology.py
valid local: backend,chroma,db,frontend,ollama,ollama_setup,rag_ingest
valid production: backend,caddy,chroma,db,frontend,rag_ingest,volume_permissions
valid gpu: ollama,ollama_setup

pytest test_compose_topology.py test_deploy_env.py test_environment_contract.py
77 passed

ruff check <archivos focales>
All checks passed!
```

También renderizaron sin error local + Caddy y QA. La regresión completa y sus
conteos finales se registran en `09-test-evidence.md` al cerrar la etapa.

## Riesgos pendientes

1. **ALTO — disponibilidad aún acoplada:** el health/readiness vigente puede
   seguir fallando con la GPU apagada. Se resuelve y prueba en la Etapa 5.
2. **ALTO — red todavía amplia:** el bind privado evita exposición por NIC
   externa, pero falta aplicar y probar el firewall exclusivo en la Etapa 7.
3. **ALTO — workflow legado:** GitHub Actions no consume todavía los nuevos
   comandos/digests. La rama no debe fusionarse como si el despliegue estuviera
   migrado; Etapa 8.
4. **MEDIO — runtime no validado:** NVIDIA Toolkit, modelo persistido e
   inferencia real siguen `NO VERIFICADO` porque la VM permaneció apagada.
5. **MEDIO — digest base futuro:** actualizar un tag semántico exige resolver y
   revisar explícitamente un digest nuevo; no se permite deriva automática.

## Confirmación de no mutación operativa

Solo se editaron archivos versionados de la rama. No se ejecutó ninguna acción
contra producción, GitHub Actions o GCP y no se inició ningún servicio Docker.
