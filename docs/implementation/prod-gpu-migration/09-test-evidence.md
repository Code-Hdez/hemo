# Evidencia de pruebas

Fecha: 2026-08-02. Todas las pruebas usan archivos temporales, SQLite efímero o
fakes; no leen ni modifican datos productivos.

## Lint focalizado

```text
.venv/bin/python -m ruff check <archivos modificados>
All checks passed!
```

Resultado: `PASS`.

## Pruebas focalizadas iniciales

```text
PYTHONPATH=backend .venv/bin/python -m pytest -q \
  backend/tests/test_deploy_env.py \
  backend/tests/llm_chat/test_repositories.py::<pruebas de sesión> \
  backend/tests/llm_chat/test_chat_api.py::<pruebas de propagación> \
  backend/tests/llm_chat/test_send_chat_message.py::<contrato>

42 passed in 2.35s
```

Resultado: `PASS`. No se registraron secretos ni prompts clínicos.

## Incidencia del runner local

El repositorio fija Python 3.11, pero `.venv/bin/python --version` devolvió
Python 3.14.4. En ese intérprete, la siguiente prueba mínima ajena al proyecto
agotó cinco segundos (`exit 124`):

```text
asyncio.run(asyncio.to_thread(lambda: 1))
```

Esto dejó detenidas pruebas preexistentes que usan el executor. Se reprodujo
también con el test BM25 aislado y un límite de 120 segundos. Los archivos de
retrieval y executor no tienen diferencias respecto de `origin/dev/agosto`.

Para completar la regresión se cargó como plugin de pytest un harness temporal
en `/tmp/hemovet_pytest_asyncio_compat.py`. El harness conserva `contextvars`,
ejecuta trabajo en threads reales y mantiene activo el event loop sin usar el
puente defectuoso de Python 3.14. No forma parte del repositorio ni del producto.
Los cinco casos previamente detenidos pasaron con él:

```text
5 passed in 0.79s
```

## Suite completa de chat

```text
PYTHONPATH=/tmp:backend .venv/bin/python -m pytest -q \
  -p hemovet_pytest_asyncio_compat backend/tests/llm_chat

575 passed, 1 skipped in 6.22s
```

El skip corresponde a la aceptación real de Ollama/Qwen, que exige un runtime
activo. No se encendió la GPU ni se inició un servicio para forzarla.

## Entorno, promoción y migraciones

```text
PYTHONPATH=backend .venv/bin/python -m pytest -q \
  backend/tests/test_deploy_env.py \
  backend/tests/test_environment_contract.py \
  backend/tests/test_migrations.py

68 passed in 8.07s
```

## Regresión completa del backend

```text
PYTHONPATH=/tmp:backend .venv/bin/python -m pytest -q \
  -p hemovet_pytest_asyncio_compat backend/tests

862 passed, 1 skipped, 1 warning, 4 subtests passed in 19.33s
```

El warning es un `DeprecationWarning` de `google.genai` bajo Python 3.14.4 y no
está relacionado con los cambios. No hubo pruebas fallidas.

## Comprobaciones de alcance

```text
git diff --check                         -> PASS
git diff --quiet -- .github              -> PASS (sin diferencias)
ruff check backend                       -> PASS
manage_deploy_env.py                     -> modo 0755
```

## Gate inicial de la Etapa 2 en Python 3.11

Se utilizó una imagen local ya disponible, identificada por el ID inmutable
`d13a834dbb24`, con Python 3.11.15. El repositorio se montó en modo solo lectura
y las dependencias de desarrollo se instalaron únicamente dentro del contenedor
efímero. No se utilizó el plugin temporal de compatibilidad de Python 3.14.

Antes de implementar la etapa:

```text
PYTHONPATH=backend python -m pytest -q backend/tests/llm_chat
576 passed, 1 skipped, 1 warning in 7.44s

PYTHONPATH=backend python -m pytest -q \
  backend/tests/test_deploy_env.py \
  backend/tests/test_environment_contract.py \
  backend/tests/test_migrations.py
68 passed in 11.30s

PYTHONPATH=backend python -m pytest -q backend/tests
862 passed, 1 skipped, 1 warning, 4 subtests passed in 27.05s

python -m ruff check --no-cache backend
All checks passed!
```

No apareció una regresión real en la versión oficial del proyecto.

### Incidencias de preparación del runner

- Un primer intento con UID no privilegiado no pudo leer el `.env` local con
  modo `0600`; pytest no llegó a ejecutar pruebas.
- El primer intento de regresión completa sobre el mount de solo lectura
  produjo 55 fallos de entorno: la imagen mínima no incluía `git` y algunas
  pruebas escriben artefactos locales. No fueron fallos del producto.
- Se instaló `git` solo en el contenedor efímero y se clonó el commit en un
  directorio temporal escribible, excluyendo `dips.md`. La misma suite pasó en
  ese entorno. No se añadió ningún harness a `/tmp` ni al repositorio.

## Validación final de la Etapa 2

Commit probado: `9d92e7952fb77caec4a8c209e0483f45cf91ac96`.
Intérprete: Python 3.11.15. El checkout de prueba estaba limpio antes de la
ejecución y solo enlazaba el `.env` local de forma legible dentro del contenedor;
las pruebas no utilizaron datos productivos.

### Contratos focales

```text
PYTHONPATH=backend python -m pytest -q \
  backend/tests/llm_chat/test_availability_contract.py \
  backend/tests/llm_chat/test_provider_contract.py \
  backend/tests/llm_chat/test_health.py \
  backend/tests/llm_chat/test_openai_compatible_client.py \
  backend/tests/llm_chat/test_send_chat_message.py::test_clinical_turn_becomes_database_only_when_all_rag_evidence_is_dropped \
  backend/tests/test_release_manifest_contract.py

50 passed, 1 warning in 1.95s
```

### Suite completa de chat

```text
PYTHONPATH=backend python -m pytest -q backend/tests/llm_chat
596 passed, 1 skipped, 1 warning in 8.03s
```

El único skip exige `RUN_OLLAMA_ACCEPTANCE=1` y un Ollama/Qwen real. No se
encendió la GPU ni se inició Ollama para forzarlo.

### Entorno, RAG y migraciones

```text
PYTHONPATH=backend python -m pytest -q \
  backend/tests/test_deploy_env.py \
  backend/tests/test_environment_contract.py \
  backend/tests/test_migrations.py

68 passed in 12.16s
```

### Regresión completa del backend

```text
PYTHONPATH=backend python -m pytest -q backend/tests
888 passed, 1 skipped, 1 warning, 4 subtests passed in 27.30s
```

El warning único es `DeprecationWarning` de `passlib` por el módulo estándar
`crypt`, previsto para retirarse después de Python 3.12. No está causado por la
Etapa 2 y no bloquea Python 3.11.

### Calidad y alcance

```text
python -m ruff check --no-cache backend  -> All checks passed!
git diff --check                         -> PASS
git diff --quiet -- .github              -> PASS
git diff --quiet -- docker-compose*.yml  -> PASS
```

No se ejecutaron despliegues, reinicios, comandos `gcloud` ni mutaciones de
GitHub Actions. La única operación remota fue publicar la rama autorizada como
respaldo antes de comenzar los cambios de Etapa 2.

## Evidencia de la Etapa 3

Revisión funcional final probada y publicada:

```text
515d343ac805779f94be9277376bdadf5516154d
```

La imagen de pruebas fue `hemovet-stage3-test:py311-git`, ID local
`sha256:220c0e4841d57d1df685d3ac491825556639285ecca805394d3dd046c6320601`,
con Python 3.11.15 y Git instalado. La regresión se ejecutó sobre el clon limpio
y escribible `/tmp/hemovet-stage3-final-regression.HPqgL6`; su `HEAD` fue el SHA
anterior. No se utilizó el harness temporal de Python 3.14.

### Regresión completa del backend

```text
PYTHONPATH=backend python -m pytest -q backend/tests
897 passed, 1 skipped, 1 warning, 4 subtests passed in 14.10s
```

El único skip es la aceptación que exige Ollama real. No se arrancó Ollama ni se
encendió la GPU. El warning es el `DeprecationWarning` preexistente de `passlib`
por `crypt` en Python 3.11.

### Contratos focales, inventario y lint

```text
PYTHONPATH=backend python -m pytest -q \
  backend/tests/test_artifact_registry_contract.py \
  backend/tests/test_release_manifest_contract.py \
  backend/tests/test_environment_contract.py::test_repository_declares_pinned_python_node_nginx_and_ollama_bases

16 passed in 0.10s

PYTHONPATH=backend python backend/scripts/validate_artifact_set.py \
  deploy/releases/artifact-set-515d343ac805779f94be9277376bdadf5516154d.json

valid hemovet.artifacts/v1: 515d343ac805779f94be9277376bdadf5516154d (3 images)

python -m ruff check --no-cache backend
All checks passed!
```

La última validación del inventario se montó de solo lectura dentro del mismo
runner. Antes, un intento directo sobre el worktree protegido no llegó a
recolectar pruebas: el usuario no privilegiado del contenedor recibió
`PermissionError` al leer el `.env` local modo `0600`. Un segundo intento usó el
clon modo `0700` con el UID incorrecto y tampoco llegó a pytest. Se corrigió
únicamente el contexto del runner ejecutándolo con el UID propietario del clon;
no se cambiaron permisos, contenido del `.env` ni código para hacer pasar las
pruebas.

### Frontend y construcción OCI

```text
npm run build
tsc -b && vite build
PASS
```

El build emitió únicamente el warning de Vite por un chunk superior a 500 kB.
No hubo error de TypeScript ni de Vite.

Backend, frontend y runtime se construyeron para `linux/amd64` desde el SHA
exacto con `--sbom=true`, `--provenance=mode=max` y `--push`. La metadata local
de Buildx y el `describe` remoto coincidieron en los índices:

```text
backend        sha256:c20b932993c97d6078d04033f72d2de132381f6a6a06580dc65be74d52b5191f
frontend       sha256:55b82e9e868247fc71d764f932610f0849db93fbe88b60261683f7894d305d7f
ollama-runtime sha256:b526b1d4bc30d0cc641e0d2a186034b327c97de0171b1a47ce1c917d79604e5f
```

Se inspeccionaron remotamente labels, manifiestos y attestations. Cada imagen
posee un predicado SPDX y uno de provenance. No se atribuye un nivel SLSA:
Artifact Registry lo reporta como `unknown`.

### Incidencias de construcción y corrección

Una primera regresión sobre la revisión intermedia produjo 31 fallos: 30 se
debían a que el runner mínimo no incluía Git y uno era una expectativa real que
aún permitía la base mutable `node:22-alpine`. Se corrigió la prueba para exigir
bases por digest. Los intentos posteriores que fallaron por `safe.directory` o
propiedad del fixture fueron fallos del runner; el clon fresco ejecutado como
UID 1000 eliminó esas condiciones y la regresión completa pasó.

La primera publicación inmutable quedó supersedida al detectarse que la imagen
Ollama heredaba `org.opencontainers.image.version=24.04`. Se añadió el label OCI
explícito `0.30.10`, se reconstruyeron las tres imágenes con un único SHA y se
validó de nuevo la cadena completa. Los artefactos bootstrap no fueron
desplegados ni eliminados.

### Validación read-only posterior en GCP

```text
APIs requeridas              PASS: exactamente las cinco habilitadas en la etapa
Repositorio                  PASS: DOCKER, STANDARD, immutableTags=true
Cleanup                      PASS: dry-run=true; solo untagged >30d; keep 20
IAM de repositorio           PASS: 1 writer CI, 2 readers runtime
Claves SA administradas      PASS: 0 para las tres cuentas
Pool/provider WIF            PASS: ACTIVE y condición exacta leída de vuelta
Binding de impersonación     PASS: solo roles/iam.workloadIdentityUser
Bindings de proyecto nuevos  PASS: ninguno para hemovet-*
VM producción                PASS: RUNNING, identidad/IP/disco sin cambio
VM GPU                       PASS: TERMINATED, identidad/IP/disco sin cambio
Tags latest                  PASS: ninguno
```

### Gate WIF inicialmente pendiente

Después del primer cierre, el intercambio OIDC real permanecía `NO VERIFICADO`
porque el workflow aún no podía solicitar un token. La etapa se declaró
`BLOCKED` en lugar de presentar como válida la publicación bootstrap realizada
con la identidad humana.

## Resolución autorizada del gate WIF

El usuario autorizó explícitamente todo lo restante de la Etapa 3 sin avanzar a
la Etapa 4. Se verificaron mediante la API autenticada de GitHub:

```text
repository_id       1148021152
repository_owner_id 115911218
main protection     ninguna
rulesets             ninguno
environments         ninguno antes del run
```

Los IDs se añadieron a la condición GCP. La operación asíncrona se consideró
aplicada únicamente cuando `describe` devolvió ambos IDs junto con repo,
propietario, `main`, workflow y environment exactos.

### Workflow y ausencia de despliegue

`actionlint 1.7.12`, descargado del release oficial y validado contra su
checksum, aprobó `.github/workflows/deploy.yml`. La acción de autenticación usa
el commit verificado:

```text
google-github-actions/auth@7c6bc770dae815cd3e89ee6cdf493a5fab2cc093
```

El workflow se instaló en `main` mediante:

```text
e30c422445e6c2e096b851895ea495858e6cc531
ci: add manual WIF stage 3 validation [skip ci]
```

La consulta inmediata encontró `0` runs de evento `push` para ese SHA. No se
ejecutó el pipeline productivo. Después se lanzó manualmente:

```text
workflow run 30762294120
event        workflow_dispatch
head SHA     e30c422445e6c2e096b851895ea495858e6cc531
conclusion   success
```

URL de evidencia:
<https://github.com/xPshycho/hemogramas-proyectoICC/actions/runs/30762294120>.

Estados por job:

```text
WIF rejects missing environment          success
WIF authenticates and publishes proof    success
Backend Tests                            skipped
Frontend Tests                           skipped
Deployment Configuration                 skipped
Deploy to Production                     skipped
```

El caso negativo recibió del STS:

```text
unauthorized_client: The given credential is rejected by the attribute condition.
PASS: provider rejected the missing environment claim.
```

El caso positivo usó `environment: production`, obtuvo un access token de 600
segundos para `hemovet-github-cicd`, no creó un archivo de credenciales, inició
sesión Docker mediante stdin, publicó y leyó de vuelta:

```text
wif-validation:run-30762294120-1
sha256:0998efbb07674eeb14b282c60bca44651feae2a6b83b632d9c650dce9cfaf989
```

El environment `production` fue creado automáticamente sin secrets ni reglas.
El intento REST previo de crearlo/configurarlo devolvió `404` por falta de
permisos administrativos y no produjo una mutación parcial.

### Regresión posterior al gate

Commit probado:

```text
7b9cd4daddfca4617f93306fb4079cb04960888a
```

Runner: Python 3.11.15, clon limpio e independiente, sin harness temporal.

```text
PYTHONPATH=backend python -m pytest -q backend/tests
898 passed, 1 skipped, 1 warning, 4 subtests passed in 14.60s

python -m ruff check --no-cache backend
All checks passed!

actionlint .github/workflows/deploy.yml
PASS
```

El skip continúa siendo la aceptación que exige Ollama real; la GPU no fue
encendida. El warning continúa siendo la deprecación preexistente de `crypt` en
`passlib`.

La verificación final mantuvo `hemovet-prod` `RUNNING` y
`hemovet-llm-gpu` `TERMINATED`, con service accounts, IPs y discos sin cambios.
La Etapa 3 queda completada; no se inicia la Etapa 4 sin nueva aprobación.

## Evidencia de la Etapa 4

Fecha: 2026-08-02. Todas las operaciones fueron locales. No se ejecutó
`docker compose up`, build/pull de imágenes de aplicación, despliegue, SSH,
`gcloud` ni mutación de GitHub.

### Resolución read-only de imágenes externas

`docker buildx imagetools inspect` resolvió los índices actuales sin descargar
o iniciar contenedores:

```text
postgres:16-alpine       sha256:57c72fd2a128e416c7fcc499958864df5301e940bca0a56f58fddf30ffc07777
chromadb/chroma:1.5.9    sha256:1e0b73a187a28757c572acba508c46f48c9e8b0acaf5c20e6d95cdedce1acdf6
caddy:2.11.4-alpine      sha256:5f5c8640aae01df9654968d946d8f1a56c497f1dd5c5cda4cf95ab7c14d58648
alpine:3.22.1            sha256:4bcff63911fcb4448bd4fdacec207030997caf25e9bea4045fa6c8c44de311d1
ollama/ollama:0.30.10    sha256:bfc9c6d53cc6989aa5131a6fde6b162b2802d4d337657f3253b5f69579bddeee
```

### Configuración efectiva y servicios

```text
PYTHONPATH=backend python backend/scripts/validate_compose_topology.py

valid local: backend,chroma,db,frontend,ollama,ollama_setup,rag_ingest
valid production: backend,caddy,chroma,db,frontend,rag_ingest,volume_permissions
valid gpu: ollama,ollama_setup
```

Se ejecutó además `docker compose ... config --quiet` y `config --services`
para los cinco conjuntos versionados:

```text
local         chroma db ollama ollama_setup rag_ingest backend frontend
production    db chroma volume_permissions rag_ingest backend frontend caddy
gpu           ollama ollama_setup
local+caddy   chroma db ollama ollama_setup rag_ingest backend frontend caddy
qa            chroma db rag_ingest backend frontend
```

La inspección selectiva del JSON efectivo confirmó:

- backend y `rag_ingest` productivos comparten el mismo digest y no tienen
  bloque `build`;
- frontend productivo usa el digest de la Etapa 3;
- producción solo publica `80/443` mediante Caddy;
- GPU publica `11434` con `host_ip=10.128.0.3`, reserva una NVIDIA y monta un
  volumen nombrado en `/root/.ollama`;
- GPU no contiene servicios o dependencias de aplicación.

### Pruebas focales y lint

```text
PYTHONPATH=backend python -m pytest -q \
  backend/tests/test_compose_topology.py \
  backend/tests/test_deploy_env.py \
  backend/tests/test_environment_contract.py

77 passed in 0.38s

python -m ruff check <archivos focales>
All checks passed!
```

Los casos de mutación rechazan un backend o configuración clínica en GPU,
bind wildcard/loopback/público, `latest`, paquete OCI incorrecto, Ollama en
producción y `depends_on` hacia un servicio externo.

### Regresión completa oficial

Runner: imagen local inmutable `hemovet-stage3-test:py311-git`, Python 3.11.15.
El worktree se copió a
`/tmp/hemovet-stage4-regression.nIVMFH/repo`, excluyendo `.env`, archivos de
entorno privados, `.venv`, `node_modules` y `dips.md`. No se utilizó el harness
temporal de Python 3.14.

La copia temporal no contenía secretos y fue eliminada de forma segura después
de conservar los resultados. Commit funcional probado:

```text
b2169408c6baa5b109bbf235907c5cf3658959b1
```

```text
PYTHONPATH=backend python -m pytest -q backend/tests
912 passed, 1 skipped, 1 warning, 4 subtests passed in 12.92s

python -m ruff check --no-cache backend
All checks passed!
```

El skip sigue siendo la aceptación que exige Ollama real; no se encendió la GPU
ni se inició Ollama. El único warning es la deprecación preexistente de `crypt`
en `passlib` bajo Python 3.11.

Tres invocaciones de preparación no constituyeron pruebas del producto: la
primera fue rechazada antes de ejecutar por incluir limpieza automática del
temporal; la segunda no llegó a pytest porque el runner no podía escribir
`/app/.gitconfig`; una tercera llegó a colección sin las variables mínimas
`DATABASE_URL`/`SECRET_KEY`. Se corrigió únicamente la invocación usando
`HOME=/tmp`, UID propietario y el entorno SQLite de test; después pasó la suite
completa sin cambiar código para ocultar fallos.

### Frontend

```text
npm test -- --run     14 archivos, 103 tests passed
npm run check         Biome 86 archivos + TypeScript: PASS
npm run build         Vite: PASS
```

El único aviso fue el tamaño preexistente de `mapStyle` superior a 500 kB; no
bloquea la separación Compose.

## Evidencia de la Etapa 5

Fecha: 2026-08-02. Commits funcionales probados:

```text
1c234329a948d433b3968233b5d176fe3e0830d0
105e8aa105795356d67a1f682849799033e8cd98
```

No se desplegó, no se inició ningún stack y no se realizaron mutaciones en GCP.
La única mutación de GitHub fue el push inicial de respaldo de los commits de
Etapa 4, exigido y autorizado antes de modificar código; no creó PR, merge,
workflow run ni despliegue. El runner backend fue la imagen local
`hemovet-stage3-test:py311-git` (`sha256:220c0e4841d5…`), con Python 3.11.15.
El entorno de pruebas usó SQLite en memoria y secretos sintéticos; el clon
temporal no incluyó `.env` privado ni `dips.md`.

### Backend focal y completo

```text
PYTHONPATH=backend python -m pytest -q <contratos focales Etapa 5>
83 passed in 1.07s

PYTHONPATH=backend python -m pytest -q backend/tests/llm_chat
608 passed, 1 skipped, 1 warning in 3.94s

PYTHONPATH=backend python -m pytest -q backend/tests
924 passed, 1 skipped, 1 warning, 4 subtests passed in 13.76s

python -m ruff check --no-cache backend
All checks passed!
```

El único skip exige un Ollama real. No se encendió la VM GPU ni se inició
Ollama. El warning único es la deprecación preexistente de `passlib` por
`crypt` bajo Python 3.11.

Un primer intento de regresión montó deliberadamente el worktree como solo
lectura: `899 passed`, `1 skipped` y 25 casos no pudieron crear fixtures en
`outputs/`, todos con `OSError: Read-only file system`. No se consideró una
prueba del producto. Se repitió sin cambiar código en un clon temporal
escribible, aislado y sin secretos; allí pasaron las 924 pruebas. El temporal se
eliminó después de la ejecución.

Los casos nuevos demuestran:

- warmup bloqueado no retrasa la construcción del contenedor y repositorios;
- proveedor ausente devuelve 503 genérico y no oculta historial persistido;
- timeout de identidad se clasifica como indisponibilidad reintentable;
- un proveedor se recupera en el siguiente probe sin reconstruir FastAPI;
- `/api/ps` fallido no invalida una identidad instalada;
- digest/cuantización incorrectos continúan fallando cerrados;
- códigos internos del adaptador nunca cruzan el envelope público;
- el camino SSE real normaliza `technical_error` y elimina mensajes internos
  antes de emitirlos;
- provider health y RAG health se consultan por separado.

### Frontend y E2E

```text
npm test -- --run
14 archivos, 108 tests passed

npm run check
Biome: 86 archivos; TypeScript: PASS

npm run build
Vite: PASS

npx playwright test tests/e2e/dashboard.spec.ts --project=desktop-1440
22 passed in 1.3m
```

Playwright incluyó el escenario proveedor degradado → recuperación por polling
→ generación posterior, sin recargar la página. Las pruebas unitarias cubren
intervalo normativo de 15 segundos, probe fallido, RAG requerido degradado e
historial conservado. El servidor E2E reduce únicamente su intervalo a un
segundo mediante una variable de build de pruebas.

Vite conserva el warning preexistente por el chunk `mapStyle` superior a 500
kB. Node/Playwright emitieron warnings no bloqueantes por la interacción entre
`NO_COLOR` y `FORCE_COLOR`.

### Compose y protección de alcance

```text
validate_compose_topology.py
valid local: backend,chroma,db,frontend,ollama,ollama_setup,rag_ingest
valid production: backend,caddy,chroma,db,frontend,rag_ingest,volume_permissions
valid gpu: ollama,ollama_setup

docker compose ... config --quiet
PASS para local, producción y GPU
```

Los servicios renderizados coincidieron con esas tres topologías. Además:

```text
git diff --check                                      PASS
git diff --quiet -- .github docker-compose*.yml      PASS
sha256sum dips.md                                     22ef723e…e145da
```

No se modificaron workflow, Compose, secretos, variables, environments,
producción, VMs, red, firewall, IAM, IPs, discos, metadata o datos persistentes.

## Evidencia de la Etapa 6

Fecha: 2026-08-02. Commits funcionales probados:

```text
ce8a82ea4715e220da4b63cd82064768dd6bd0e2
4d96835d4e069747c5e3a595140a526054dd99fb
52dfa378 — instalación CDI atómica
70c32b38 — releases históricas y rollback entre bundles
58a1c15 — inferencia de residencia obligatoria en cada boot
```

La rama permaneció separada de `main`; `dips.md` siguió sin seguimiento con
SHA-256 `22ef723ec15957e215ef5dadc207572b8dc11b9e8b715b41dc89d9b8e0e145da`.
No se modificó `hemovet-prod`, datos clínicos, PostgreSQL, Chroma, RAG,
firewall, VPC, GitHub Actions, secrets, variables o environments.

### Gate local del bundle

```text
python3 -m pytest -q backend/tests/test_gpu_runtime_bootstrap.py
17 passed

sha256sum --check deploy/gpu/bundle-manifest.sha256
14 archivos: OK

bash -n deploy/gpu/*.sh
PASS

ShellCheck
PASS con `koalaman/shellcheck:v0.11.0@sha256:61862eba…925a8d`

runtime_contract.py validate --manifest gpu-runtime-515d343….json
valid hemovet.gpu-runtime-release/v1: 515d343ac805779f94be9277376bdadf5516154d
```

La topología renderizada en local y en la VM produjo exclusivamente:

```text
ollama
ollama_setup
```

### Inventario y respaldo

La VM se inspeccionó primero apagada y se creó
`hemovet-llm-gpu-pre-stage6-20260802`. El snapshot terminó `READY` en
`us-central1`, con source disk ID `574351621454120040` y
58,891,150,336 bytes reportados. Solo después se inició la VM.

El inventario en ejecución confirmó Ubuntu 24.04, driver `580.159.03`, Docker
`29.6.2`, Compose `5.3.1`, containerd `2.2.6`, NVIDIA Container Toolkit
`1.17.8` y una NVIDIA L4 de 23,034 MiB.

Se hallaron dos stacks completos heredados y un Ollama host. La cuarentena los
dejó detenidos, `restart=no`, sin eliminar sus 17 contenedores ni volúmenes. Al
final solo estaba corriendo `hemovet-gpu-ollama-1`.

### Fallos cerrados durante el bootstrap

El primer intento real detectó que la unidad `systemd` no podía preparar
`/etc/cdi` dentro de su namespace (`status=226`). Se corrigió el instalador para
crear la ruta antes de habilitar el servicio y se añadió una prueba.

El siguiente stop/start detectó specs CDI duplicadas porque `nvidia-ctk`
añadía `.yaml` al temporal dentro del directorio de discovery. El servicio
falló antes de aplicar la nueva revisión; la revisión `6e2969d6…`, el
contenedor y el hash de pesos permanecieron intactos. La generación pasó a un
temporal fuera de discovery y el rename final quedó atómico.

Otro boot detectó que el manifiesto aplicado histórico conservaba el digest de
su bundle original. El reconciliador lo trataba incorrectamente como manifiesto
deseado y fallaba al compararlo con el bundle nuevo. Se separó la validación
histórica de la validación deseada y se implementó una proyección temporal
revalidada para rollback. La evidencia histórica original no se muta.

Un último stop/start reprodujo un cuarto fallo cerrado: con la revisión ya
aplicada, Docker restauró el contenedor saludable pero `/api/ps` todavía no
contenía el modelo. El bundle anterior intentaba validar residencia sin cargar
antes el modelo y `systemd` terminó con rc distinto de cero, conservando
revisión, contenedor y 2,497,296,445 bytes de pesos. El reconciliador ahora
espera health y ejecuta una inferencia mínima en cada boot; una reejecución en
ese mismo boot mantiene `action=validate_only`.

Ninguno de esos intentos se contabilizó como éxito. En todos los casos el
runtime previo siguió disponible y no se corrompieron pesos.

### Arranque final e identidad

```text
systemd: ActiveState=active, SubState=exited, Result=success
release: 515d343ac805779f94be9277376bdadf5516154d
runtime: sha256:b526b1d4bc30d0cc641e0d2a186034b327c97de0171b1a47ce1c917d79604e5f
bundle:  sha256:5e2a5eb03f9fcdf5a1373447f3d6da13a16617a599db697e515d4039396a2c26
```

La imagen leída de Docker mostró el mismo repo digest y labels OCI con revisión
`515d343a…`, versión `0.30.10` y base Ollama fijada por digest.

```text
/api/tags digest: 0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0
/api/show family: qwen3
/api/show parameters: 4,022,468,096
/api/show quantization: Q4_K_M
/api/ps size: 2,895,118,335
/api/ps size_vram: 2,895,118,335
ollama ps: 100% GPU
nvidia-smi host/container: NVIDIA L4, driver 580.159.03
```

El primer cold load de la revisión final tardó 93,088 ms, alcanzó 2,980 MiB de
VRAM y 38% de utilización muestreada. El prompt y la respuesta sintéticos no se
registraron.

El boot de aceptación repetido
`307e64cd-6e20-444a-af69-54a749c00145` produjo
`action=boot_inference`, 18,989 ms, 2,988 MiB de VRAM y un pico de 43% de GPU.
`systemd` terminó con `Result=success`. La reejecución posterior en el mismo
boot produjo `action=validate_only`, `latency_ms=0` y conservó el mismo ID y
`StartedAt` del contenedor.

### Persistencia, idempotencia y fallo inválido

El volumen conservó exactamente:

```text
files:     9
bytes:     2,497,296,445
tree hash: 56a69d7f542435eee19b0265d8185e9eddbddef8256bbb7e3c13c29697559dbd
```

Ese resultado fue idéntico antes/después de stop/start, reinicio del contenedor,
segunda ejecución del bootstrap y rollback. El restart del contenedor produjo
otra inferencia `full_gpu` en 4,840 ms sin descargar el modelo.

La ejecución idempotente conservó el mismo container ID, `StartedAt`, hash del
manifiesto y hash del modelo; registró:

```text
boot_authorized=false
nvidia_cdi=unchanged
release=already_applied ... action=validate_only
```

Una revisión alterada a un estado no permitido devolvió rc `1` y
`ERROR: only pending_boot_validation may be applied`. Contenedor, revisión y
pesos fueron idénticos antes/después.

### Rollback probado

```text
515d343a… / b526b1d4… -> 6e2969d6… / f2a4fc8d…
runtime=valid inference_device=full_gpu latency_ms=77993

6e2969d6… / f2a4fc8d… -> 515d343a… / b526b1d4…
runtime=valid inference_device=full_gpu latency_ms=77135
```

El estado final volvió a `515d343a…`; `previous-release.json` conserva
`6e2969d6…` y ambas imágenes permanecen disponibles por digest.

### Seguridad, apagado y costo

El listener fue solo `10.128.0.3:11434`; `curl` contra
`34.45.75.48:11434` terminó por timeout (`rc=28`, HTTP `000`). El firewall no se
modificó. El scan de journald no encontró claves, tokens, authorization headers,
passwords o secrets, y `/run/hemovet-gpu/docker-config` no existía al terminar.

La clave SSH temporal se retiró, la metadata volvió a sus cuatro entradas
originales y una conexión posterior falló con `Permission denied`. El material
temporal local fue destruido. La VM terminó `TERMINATED` a las
`2026-08-02T15:28:08.659-07:00`.

Las operaciones GCP sumaron 3,386.448 segundos de VM encendida. El techo
on-demand calculado fue `USD 0.6649`; el importe Spot real es variable. El
snapshot usa 54.847 GiB: ~`USD 0.0038` por hora, ~`USD 0.0075` durante las
primeras dos horas y ~`USD 2.74` por 730 horas si se conserva.

### Gate final de repositorio

```text
Python 3.11: 941 passed, 1 skipped, 1 warning, 4 subtests passed
GPU focal:   17 passed
Ruff:        All checks passed!
ShellCheck:  PASS, imagen fijada sha256:61862eba…925a8d
Compose:     PASS, local/production/GPU exactos
checksums:   14 archivos del bundle OK
git diff:    --check PASS
```

El warning único es la deprecación preexistente de `passlib` por `crypt`; el
skip único exige un Ollama real y quedó cubierto por la aceptación en la VM.

Un primer comando de regresión configuró erróneamente
`HEMOVET_ENABLE_LOCAL_EXTRACTION=0`: obtuvo `939 passed`, pero falló en dos casos
que verifican precisamente el extractor CSV local. No fue una regresión de
Etapa 6 ni se contó como gate. Se repitió desde otro clon limpio, escribible,
con Python 3.11.15 y el extractor habilitado; allí pasaron las 941 pruebas.

Durante el cierre posterior a la corrección de arranque se repitió el gate en
otro clon limpio. La primera invocación omitió `PYTHONPATH` y la segunda omitió
`DATABASE_URL`/`SECRET_KEY`; ambas abortaron durante colección y no ejecutaron
casos. La tercera usó explícitamente el entorno de test documentado, Python
3.11.15 y extracción local habilitada: `941 passed, 1 skipped, 1 warning, 4
subtests passed in 14.24s`. Esos dos errores de invocación no son regresiones y
no se contabilizan como gates superados.

## Evidencia de la Etapa 7

Commit funcional probado:

```text
cf0f4c5f31f952f02a0227a050e2be84ffcabc3d
```

Antes de mutar se verificó la rama dedicada, ausencia de diferencias rastreadas,
`dips.md` no rastreado, GPU `TERMINATED` y snapshot
`hemovet-llm-gpu-pre-stage6-20260802` en `READY`. Se guardaron inventarios
privados de firewall, rutas, VPC/subred, direcciones, VMs, discos, metadata,
IAM, APIs y snapshot. No se versionaron claves o tokens.

### Contratos locales, lint y supply chain

El runner oficial fue Python 3.11.15. La validación final obtuvo:

```text
backend/tests/test_gpu_runtime_bootstrap.py y contratos GPU: 18 passed
backend/tests: 942 passed, 1 skipped, 1 warning, 4 subtests passed
python -m ruff check --no-cache backend: All checks passed!
ShellCheck: PASS
sha256sum --check deploy/gpu/bundle-manifest.sha256: 16 archivos OK
manifiestos gpu-runtime: PASS
```

ShellCheck usó la imagen fijada
`koalaman/shellcheck:v0.11.0@sha256:61862eba1fcf09a484ebcc6feea46f1782532571a34ed51fedf90dd25f925a8d`.
El bundle validado fue
`sha256:b781a68bd132c7c29ddd5def3c1309c933b55026a3782ecd27494372476aaf65`.
El warning único es la deprecación preexistente de `passlib`/`crypt`; el skip
único corresponde a la aceptación externa cubierta por la VM real.

La primera preparación del runner omitió `aiosqlite` y abortó durante
colección. Una segunda invocación deshabilitó por error el extractor local y
obtuvo `940 passed` más dos fallos esperables de extracción CSV. Ninguno se
contó como gate. El entorno corregido incluyó las dependencias oficiales,
Python 3.11 y extracción habilitada; allí pasaron las 942 pruebas. No se cambió
código para acomodar el runner y no se usó el harness temporal de `/tmp`.

No hubo cambios Compose o GitHub Actions en el commit de Etapa 7. Las tres
topologías siguieron cubiertas por la regresión de contratos de Compose.

Durante el cierre documental se intentó invocar
`backend/scripts/validate_release_manifest.py`, ruta que no existe; el comando
terminó con rc `2` después de que los checksums ya habían pasado y no produjo
ninguna mutación. Se sustituyó por los contratos ejecutables reales
`test_release_manifest_contract.py` y `test_runtime_artifact_manifest.py`: `7
passed`. El intento con ruta incorrecta no se contabiliza como validación.

### Firewall y conectividad

Con la GPU encendida exclusivamente durante la prueba, el camino real desde
producción devolvió:

```text
authorized_path=success
source=10.128.0.2
destination=10.128.0.3
port=11434
http=200
```

Network Intelligence Center reprodujo las decisiones efectivas:

```text
10.128.0.2 -> 10.128.0.3:11434       REACHABLE   allow priority 700
10.128.0.4 -> 10.128.0.3:11434       UNREACHABLE deny priority 800
198.51.100.10 -> 34.45.75.48:11434   UNREACHABLE deny priority 800
35.235.240.1 -> 10.128.0.3:22        REACHABLE   allow priority 700
Internet -> GPU 22/80/443/3389        UNREACHABLE
```

Además, sondas TCP reales desde Internet hacia 22, 80, 443, 3000, 3389 y
11434 fueron rechazadas o filtradas. Los ocho Connectivity Tests temporales se
eliminaron después de preservar resultados sanitizados; el listado final tuvo
cero recursos con prefijo `hemovet-stage7-`.

### IAP, OS Login y recuperación

Se completaron dos accesos IAP/OS Login independientes a la GPU; el segundo
validó `sudo -n true`. Tras activar la denegación total se completó un tercer
acceso. Producción también se alcanzó por IAP mediante una clave de metadata
efímera que fue retirada sin reiniciar servicios.

Una conexión IAP coincidió con una preempción Spot. Como rollback preventivo se
deshabilitó temporalmente la regla deny-all, se consultaron las operaciones GCP
y se confirmó `compute.instances.preempted`. La regla se reactivó y el acceso
IAP volvió a pasar con ella activa. Esto valida la recuperación sin dejar una
exposición abierta.

La clave OS Login efímera se eliminó. La herramienta omitió una clave pública
preexistente durante ese cleanup; la comparación con la línea base lo detectó
y se restauró el mismo material. El conjunto normalizado final fue de dos
claves y su hash fue
`e59ad7d19abd82e6bcba9a64f975a4130e4110b31bdcf433899022ef8f054f11`.
No se conservó ninguna clave privada temporal.

### Apagado automático y recuperación válida

El bundle Etapa 7 fue instalado por IAP después de verificar sus checksums. La
VM conservó Ubuntu 24.04, driver NVIDIA `580.159.03`, Docker `29.6.2`, Compose
`5.3.1`, NVIDIA Container Toolkit `1.17.8` y una NVIDIA L4.

Se publicó temporalmente una proyección con
`revision_state=invalid_stage7_probe`. El reconciliador falló cerrado:

```text
ERROR: only pending_boot_validation may be applied
bootstrap-failure.json mode=0600
state=shutdown_requested
unit=hemovet-gpu.service
failed_at=2026-08-02T23:18:58Z
```

Compute Engine registró `compute.instances.guestTerminate`, demostrando que el
apagado procedió del guest y no de un stop administrativo o una preempción. La
revisión, imagen, modelo y pesos anteriores permanecieron intactos.

Con la VM apagada se restauró el manifiesto aprobado y el siguiente boot
terminó:

```text
release=515d343ac805779f94be9277376bdadf5516154d
runtime=sha256:b526b1d4bc30d0cc641e0d2a186034b327c97de0171b1a47ce1c917d79604e5f
model=qwen3:4b-instruct-2507-q4_K_M
inference_device=full_gpu
latency_ms=19044
systemd Result=success
```

La reinstalación del mismo bundle fue idempotente. La evidencia del fallo se
conservó para diagnóstico, journald tuvo cero coincidencias sensibles y el
directorio de autenticación Docker efímero no existía al terminar.

### Protecciones, snapshot, aplicación y cierre

El read-back final confirmó `deletionProtection=true` y `autoDelete=false` en
ambas VMs/boot disks. El snapshot siguió `READY`, con 58,891,150,336 bytes
almacenados. Las IPs continuaron `136.64.136.49`/`10.128.0.2` y
`34.45.75.48`/`10.128.0.3`.

La aplicación productiva no se desplegó ni reinició. Su
`lastStartTimestamp=2026-07-02T06:45:52.411-07:00` no cambió. Con la GPU apagada:

```text
https://hemovet.app/                 HTTP 200
/api/v1/chat/health                 HTTP 200
status                              degraded
rag_ready/chroma_ready              true/true
llm_ready/gpu_active                false/false
```

Los campos Etapa 5 `core_ready`/`chat_ready` aún no aparecen públicamente
porque desplegar ese código estaba prohibido; no se presenta el runtime antiguo
como si ya contuviera la nueva versión.

La GPU quedó `TERMINATED`, con último stop
`2026-08-02T16:24:53.277-07:00`. El tiempo encendida atribuible a Etapa 7 fue
`916.241 s`; el techo on-demand estimado fue `USD 0.1799`, con precio Spot real
variable. No se borró ningún contenedor, imagen, volumen o dato pese al 74% de
uso de disco.

## Evidencia de la Etapa 8

### Regresión y configuración

```text
Python 3.11.15
backend/tests                         958 passed, 1 skipped, 4 subtests
Ruff backend                          PASS
run final: migrations                 6 passed
run final: llm_chat                   609 passed, 1 skipped
run final: release/GPU contracts      48 passed
run final: evaluation                 24 passed
run final: backend restante           295 passed, 4 subtests
frontend                              108 passed / 14 archivos
Playwright crítico                    8 passed
Compose local/prod/GPU                PASS
Caddy / Bash / actionlint             PASS
```

El dry-run real produjo 1,250 fuentes, 4,696 chunks, 0 cuarentena,
`schema_version=markdown-v5`, `corpus_schema_version=hemovet-rag-v2` y
fingerprint `6832f37d428731520ce903de60d0781df543df3a10c84f1fcdbf27056bef9b60`.

### WIF e IAP

- `30774662155`: success, WIF sin key + IAP a producción.
- `30774700108`: segundo success consecutivo.
- `30776824293`: fallo esperado tras restaurar provider a `main`; el job sin
  environment pasó porque exigía y observó el rechazo.
- La primera prueba IAP `30774595816` falló antes de propagación IAM y no se
  contó como éxito.

### Publicación final

Run `30776245995`: `success`.

```text
backend        sha256:c710984c1c3d42959bf54ef387490903a06aa9eb92a4c00acdeb6c26ee5c72ae
frontend       sha256:8feb146ec8092fc4df480331015a71e5271eaa255daa8cb3b5454d97aedbb296
ollama-runtime sha256:de0833bd3afd746a50281ba867b1504a836bcde54b493bf9c65c3d9c2a389179
release        af5ab60b418bc931c4c4cabc8b8ef92893325fb6
artifact       hemovet-release-30776245995-1 (2,995 bytes)
```

Los cuatro archivos fueron descargados y revalidados; artefactos, release y
proyección GPU coincidieron. No se subió el entorno privado. Cada imagen tiene
attestations SPDX y SLSA v1.

Tres runs de publicación previos fallaron cerrados antes del manifiesto por:
expresión `jq`, URL local heredada y distinción chunk/corpus RAG. Ninguno
ejecutó metadata GPU, deploy o smoke. Las tres causas quedaron corregidas y con
pruebas específicas.

### Estado y ausencia de pérdida de datos

```text
hemovet-prod status                 RUNNING
hemovet-prod lastStartTimestamp     2026-07-02T06:45:52.411-07:00
hemovet-llm-gpu                     TERMINATED
snapshot                            READY
https://hemovet.app/                HTTP 200
chat health                         degraded esperado
RAG / Chroma / chunks               true / true / 4696
```

No se ejecutó ningún job de despliegue, comando contra PostgreSQL/Chroma ni
promoción productiva. Por ello no hubo escritura sobre datos clínicos; la
comprobación pública posterior fue saludable. No se presenta un conteo de filas
como prueba, porque acceder a datos productivos no era necesario ni autorizado.

Runtime total medido de jobs Stage 8: 2,696 segundos (`44m56s`). Artifact
Registry terminó en 7,190.672 MB. GPU no se encendió y su costo atribuible fue
USD 0.

## Evidencia de la Etapa 9

### Artefactos y manifiestos

El candidato real `af5ab60b418bc931c4c4cabc8b8ef92893325fb6` quedó versionado y
revalidado contra Artifact Registry:

```text
backend        sha256:c710984c1c3d42959bf54ef387490903a06aa9eb92a4c00acdeb6c26ee5c72ae
frontend       sha256:8feb146ec8092fc4df480331015a71e5271eaa255daa8cb3b5454d97aedbb296
GPU runtime    sha256:de0833bd3afd746a50281ba867b1504a836bcde54b493bf9c65c3d9c2a389179
release JSON   e2549674c4f5fac43b5cabf797ff31e1862454c8c7191da6b0448e51fdd6f5a1
artifact JSON  ee0ed04b4d54c1630d23157dad3d0ab801dae3b4deb0acf63f82b44114bcbc4f
GPU JSON       3b69141b878e68951cbe42a198b1736610cc4ad1ce0ace244c5c31f788b88338
source archive 1d5ed0bdc7827d3491207ef909d3ee4ed3c75cbfc5b8368353c4bb80ca63ca90
config digest  becb662cb473747e02648af015b308a242265e3641029c80159cefe98dbdbc6f
```

El validador coordinado confirmó un único SHA, referencias OCI por digest,
Qwen `0edcdef3…`/`Q4_K_M`, colección
`hemovet_canine_hematology_v2__6832f37d4287` y 4,696 chunks. No imprimió
valores del entorno.

### Instalación, fallo y restauración aislados

La imagen backend publicada arrancó en un proyecto Compose temporal, aplicó
migraciones `0001` a `0012` y devolvió núcleo/base listos. No se publicaron
puertos ni Caddy. El proyecto, red, contenedores y volúmenes temporales quedaron
en cero al limpiar.

Se provocó un fallo controlado después de instalar el entorno candidato. Dos
intentos consecutivos devolvieron el rc original `42` y registraron
`ROLLED_BACK`. Después de cada intento se comprobaron:

```text
.env anterior                      byte-identical
RAG_COLLECTION_NAME                anterior
current / previous                 symlinks anteriores exactos
backend / frontend                 digests anteriores
SQLite clínico sintético           hash y conteos sin cambios
colecciones Chroma sintéticas      ambos hashes sin cambios
tags mutables / secretos en log    cero
```

### Revisión GPU

Con `hemovet-llm-gpu=TERMINATED`, la metadata hizo:

```text
515d343a…/b526b1d4… -> af5ab60…/de0833bd… -> 515d343a…/b526b1d4…
```

El valor final coincidió byte por byte con el inicial, SHA-256
`5bf601f00844b4276de21f7932256dc39e9274d1ec4a99127f717502c6f7e57e`.
La VM no cambió timestamps; el snapshot permaneció `READY`.

### Hallazgo de health y corrección

La imagen `af5…` mantuvo `core_ready=true`, pero el health tardó ~10.006 s con
GPU inaccesible, frente al timeout Docker de 5 s. La Etapa 9 acotó el probe del
proveedor a 1.5 s y el presupuesto identidad/residencia a 2 s. La prueba nueva
exige respuesta menor de 2.5 s, proveedor degradado/reintentable y RAG evaluado
independientemente.

### Gates finales

```text
Python 3.11 / backend/tests          966 passed, 1 skipped, 4 subtests
rollback + health focales            37 passed
Ruff                                 PASS
Bash / ShellCheck                    PASS
bundle GPU                           checksums PASS
Compose local/prod/GPU               PASS
git diff --check                     PASS
```

El run `30778878989` pasó backend, frontend y configuración, y fue rechazado en
WIF por ejecutar desde la rama de trabajo. Publicación, metadata GPU, deploy y
smoke quedaron `skipped`; Artifact Registry no contiene un tag
`sha-ee9fa759…`. Este fallo es la evidencia positiva del control de referencia,
no un artefacto ausente presentado como éxito.

Cuatro preparaciones locales no se contaron como pruebas: el Python 3.11 global
no tenía dependencias; una referencia ShellCheck fue transcrita con digest
incorrecto; pytest se invocó sin path/entorno; y una corrida desde `backend/`
dejó cinco fallos Alembic por cwd (`961 passed`). La referencia ShellCheck
completa y pytest desde la raíz con el entorno CI explícito produjeron los gates
PASS mostrados arriba. No hubo corrección de producto para hacer pasar esos
errores del runner.

### Estado final y costos

```text
hemovet-prod                         RUNNING; sin restart desde 2026-07-02
https://hemovet.app/                 HTTP 200, 1,167 bytes
chat                                degraded; Chroma/RAG true; 4,696 chunks
hemovet-llm-gpu                      TERMINATED
revisión GPU                         515d343a… / b526b1d4…
snapshot                             READY, 58,891,150,336 bytes
```

No se leyó ni escribió la base productiva; no hubo cutover ni pérdida de datos.
GPU y Compute incremental fueron USD 0. El run negativo consumió
aproximadamente seis minutos Linux; el cargo depende de la cuota y no se
verificó una factura. No se crearon objetos OCI ni snapshots nuevos.

## Evidencia de la Etapa 10

### Revisión y CI

PR 29 produjo el SHA final
e7713a72369bb9365f6d5323e165fbf84488bfb4. Contiene ee9fa759 y los fixes
0b41fd95, fbeec829, 8a24cdf5, 8b0666fa y c81950b3. El run 30794470808
terminó success:

- migraciones: 6 passed;
- llm_chat: 632 passed, 1 skipped;
- release/contratos: 48 passed;
- evaluación LLM: 24 passed;
- backend restante: 304 passed, 4 subtests;
- Ruff: PASS;
- frontend: 108 passed en 14 archivos;
- Biome, TypeScript y build: PASS;
- Playwright crítico: 8 passed;
- deploy y smoke productivo: skipped.

### Artefactos

| Componente | Digest |
| --- | --- |
| Backend | sha256:cf1dcab600cb880dbc07820896fd7816dac48956a4b9e6388df2f293a21b1826 |
| Frontend | sha256:66cf329d1dce2f544454876b97433cf621fe4769d5d6a086ae9ca3074a489faf |
| GPU runtime | sha256:aed77e3c668587c12ac32751d484d1a287e2853b3ffb56760fe8222a5fd3cd0c |
| Modelo | sha256:0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0 |

Los tres digests se verificaron contra Artifact Registry. El manifiesto,
artifact set, proyección GPU y RAG usan el mismo SHA y ninguna referencia
latest.

### Aceptación funcional

El runner sanitizado registró 19 casos PASS y cero fallos. Cubrió
registro/login, autorización, mascotas, hemogramas, chat
general/seleccionado/histórico, memoria, RAG, guardrails, SSE,
browser_session_hash, reinicio, proveedor apagado y recuperación automática. El
informe versionado tiene SHA-256
1db7a73e62e0b836b6c4765ca3b562a1d947e964be68b706283354ae5044a15a y
no contiene credenciales, prompts ni respuestas.

### NVIDIA L4

| Métrica | Valor |
| --- | --- |
| Driver | 580.159.03 |
| Docker | 29.6.2 |
| NVIDIA Container Toolkit | 1.17.8 |
| Modelo | qwen3:4b-instruct-2507-q4_K_M |
| Cuantización | Q4_K_M |
| inference_device | full_gpu |
| Modelo / VRAM | 2,895,118,335 / 2,895,118,335 bytes |
| VRAM observada | 2,996 MiB |
| Utilización máxima | 32 % |
| Latencia de revalidación | 514 ms |

La VM estuvo encendida 449.523 segundos y quedó TERMINATED. La metadata deseada
volvió exactamente al hash previo
a4e9f60b8138553707291b247424a1bc7de8f369f74faa6048ec42176d2c1b71. El
snapshot permaneció READY.

### Ausencia de cutover y limpieza

Los IDs públicos backend/caddy/chroma/db/frontend/ollama coincidieron antes y
después; hemovet-prod conservó su timestamp de arranque. La web respondió HTTP
200 y RAG público mantuvo 4,696 chunks. La metadata SSH temporal se restauró al
hash anterior. Se eliminaron solo recursos Compose, volúmenes y directorios de
prueba con nombre hemovet-stage10-*; no se borró ningún dato, volumen, imagen o
colección productiva.

La evidencia detallada, incidencias transparentes, costos y rollback están en
20-stage10-final-acceptance.md.

## Evidencia de la Etapa 11

### Cutover productivo

El workflow manual `30827420990` ejecutó con `operation=DEPLOY`, referencia
`main` y confirmación exacta del SHA
`069df45f7becbf1bf698a3ee6a8a9305e3aa4d1f`. Finalizó `success` entre
2026-08-03T15:25:29Z y 15:38:16Z. La transacción remota fue
`20260803T153601.245677433Z-73024`.

```text
backend       sha256:1d27af423b399f3328311271e6929100de3083c37d71f75b6d9288e0769fe57c
frontend      sha256:1681df1c434c2373d981817460a522b902762e3107f1068f7098a06f1ec6cf7f
GPU runtime   sha256:e85e87e1fdd596307cda6a9e2871af3cdef74a3f164c5cc13c0d64fe2f0dd154
modelo        sha256:0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0
entorno       sha256:29eda538e8c77ea2e774e9c0d02abd37ed7d00c23fb57f984e130cdd23a92d16
RAG           hemovet_canine_hematology_v2__6832f37d4287 / 4,696 chunks
```

La aplicación pública respondió HTTP 200. Backend, frontend, Caddy,
PostgreSQL y Chroma quedaron saludables; `rag_ingest` terminó 0. El endpoint
operacional devolvió `core_ready=true`, `database_ready=true`,
`chroma_ready=true`, `rag_ready=true`, `chat_ready=false` y
`status=degraded`, que es el contrato esperado con GPU apagada.

### Rollbacks automáticos previos al éxito

Tres fallos reales abortaron de forma cerrada antes de dejar un estado
inconsistente: ausencia de `python`, ausencia de Pydantic en el host y permisos
`0700/0600` del corpus extraído. Se corrigieron en `1be07112`, `cbf61217` y
`44b9fbf0`. El último fallo registró `rollback=completed`; los bytes del entorno
anterior, el puntero RAG y los seis conteos de datos coincidieron con la línea
base. La regresión nueva verificó directorios `0755`, corpus `0644` y entorno
privado `0600`; 21 pruebas focales, Ruff y sintaxis Bash pasaron antes de PR 32.

### Integridad de datos

Antes y después del cutover:

```text
users=46 pets=81 analyses=140 analysis_parameters=2575
chat_sessions=313 chat_turns=351 chat_messages=683
alembic=0012_chat_browser_session (head)
```

No se eliminó ni sobrescribió colección Chroma, dato clínico o volumen. Se
conservaron Ollama local, snapshots y backup inmediato.

### Validaciones detenidas por instrucción del usuario

La GPU se encendió a 15:39:39Z y se detuvo a 15:42:07Z, aproximadamente
147.878 segundos. El usuario ordenó no ejecutar más pruebas y apagarla. Por
ello, la reconciliación aplicada, identidad live, cuantización live,
`/api/ps`, `full_gpu`, chat, memoria, SSE, recuperación y dos accesos
IAP/OS Login se registran como `NO VERIFICADO` para Etapa 11. No se reutiliza
la evidencia de Etapa 10 como si perteneciera a este arranque.

El costo exacto facturado es `NO VERIFICADO`; se documenta el tiempo de VM y no
se inventa una cifra. La GPU terminó `TERMINATED`; ambos snapshots permanecen
`READY`.
