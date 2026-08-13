# Etapa 9 — Validación integral de rollback

## Objetivo

Demostrar, sin cutover productivo, que una revisión completa puede instalarse y
restaurarse como una unidad coherente: código, imágenes backend/frontend,
entorno completo, puntero RAG y revisión GPU. La prueba se limita a un entorno
Compose aislado y a una selección reversible de metadata con la GPU apagada.

## Estado inicial

| Elemento | Estado comprobado |
| --- | --- |
| Rama | `dev-agosto/feat-gpu-deployment-separation` |
| HEAD local/remoto autorizado | `feec38f6d72bdcc887f0cd4ed0c2a7263ac29ee2` |
| `origin/main` | `e30c422445e6c2e096b851895ea495858e6cc531` |
| Working tree rastreado | limpio |
| Archivo ajeno | `dips.md`, no rastreado, 68,340 bytes, SHA-256 `22ef723ec15957e215ef5dadc207572b8dc11b9e8b715b41dc89d9b8e0e145da` |
| Producción | `RUNNING`, sin restart desde 2026-07-02 |
| GPU | `TERMINATED` |
| Snapshot | `hemovet-llm-gpu-pre-stage6-20260802`, `READY` |
| Revisión GPU deseada | `515d343ac805779f94be9277376bdadf5516154d`, `pending_boot_validation` |

## Alcance ejecutado

- validación cerrada de manifiesto, inventario OCI, entorno, source archive,
  proyección GPU y bundle de arranque;
- instalación/rollback transaccional en un directorio temporal seguro;
- restauración de bytes de `.env`, puntero RAG y symlinks `current`/`previous`;
- rollback por referencias OCI inmutables de backend y frontend;
- conservación de colecciones Chroma y datos clínicos sintéticos;
- selección y restauración real de metadata GPU mientras la VM estaba apagada;
- arranque aislado de la imagen backend publicada para comprobar migraciones y
  compatibilidad básica con la revisión anterior;
- regresión completa y documentación reproducible.

## Elementos fuera de alcance

- ningún deploy, restart o cambio de tráfico productivo;
- ninguna lectura o escritura directa de PostgreSQL/Chroma productivos;
- encender la GPU, cambiar runtime/modelo o restaurar destructivamente el
  snapshot;
- retirar Ollama local, SSH legado o reglas de firewall;
- fusionar o modificar `main`;
- publicar artefactos desde una referencia que WIF no autoriza.

## Revisiones y digests inventariados

### Revisión anterior disponible

La revisión `515d343ac805779f94be9277376bdadf5516154d` conserva tres imágenes
publicadas:

| Componente | Digest |
| --- | --- |
| Backend | `sha256:c20b932993c97d6078d04033f72d2de132381f6a6a06580dc65be74d52b5191f` |
| Frontend | `sha256:55b82e9e868247fc71d764f932610f0849db93fbe88b60261683f7894d305d7f` |
| Runtime GPU | `sha256:b526b1d4bc30d0cc641e0d2a186034b327c97de0171b1a47ce1c917d79604e5f` |

Es una revisión operativa GPU y un inventario OCI válidos, pero precede a la
generación del contrato completo `hemovet.release/v1`. No se presenta como un
manifiesto de aplicación completo que no existe.

### Candidato completo publicado

La revisión real `af5ab60b418bc931c4c4cabc8b8ef92893325fb6`, publicada por el run
GitHub `30776245995`, contiene:

| Componente | Digest |
| --- | --- |
| Backend | `sha256:c710984c1c3d42959bf54ef387490903a06aa9eb92a4c00acdeb6c26ee5c72ae` |
| Frontend | `sha256:8feb146ec8092fc4df480331015a71e5271eaa255daa8cb3b5454d97aedbb296` |
| Runtime GPU | `sha256:de0833bd3afd746a50281ba867b1504a836bcde54b493bf9c65c3d9c2a389179` |
| Modelo | `sha256:0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0` |

Identidades adicionales:

```text
release-manifest SHA-256  e2549674c4f5fac43b5cabf797ff31e1862454c8c7191da6b0448e51fdd6f5a1
artifact-set SHA-256      ee0ed04b4d54c1630d23157dad3d0ab801dae3b4deb0acf63f82b44114bcbc4f
GPU projection SHA-256    3b69141b878e68951cbe42a198b1736610cc4ad1ce0ace244c5c31f788b88338
source archive SHA-256    1d5ed0bdc7827d3491207ef909d3ee4ed3c75cbfc5b8368353c4bb80ca63ca90
private config digest     becb662cb473747e02648af015b308a242265e3641029c80159cefe98dbdbc6f
RAG collection            hemovet_canine_hematology_v2__6832f37d4287
RAG fingerprint           6832f37d428731520ce903de60d0781df543df3a10c84f1fcdbf27056bef9b60
RAG chunks                4696
```

El entorno privado se reconstruyó localmente y coincidió con el digest del
manifiesto. Sus valores nunca se imprimieron ni se versionaron.

## Cambios realizados

### Validador coordinado

`backend/scripts/validate_rollback_bundle.py` valida antes de cualquier
mutación que:

1. release, artifact set, source, entorno y GPU usan un único SHA;
2. backend, frontend y runtime coinciden por referencia canónica y digest;
3. modelo, cuantización, bundle de arranque y estado GPU son los autorizados;
4. entorno, configuración Caddy y RAG coinciden con el manifiesto;
5. la salida contiene solo identidades no sensibles.

### Despliegue transaccional y prueba aislada

`deploy/prod/deploy-release.sh` ahora:

- admite un modo de prueba explícito únicamente bajo un directorio
  `/tmp/hemovet-stage9-rollback.*`, propiedad del usuario, modo `0700` y con un
  sentinel exacto;
- utiliza proyecto, paths, lock y Docker config exclusivos del namespace;
- crea una transacción distinta por intento, permitiendo repetir el rollback;
- conserva y restaura los dos enlaces `current` y `previous`;
- restaura el entorno completo con verificación de digest;
- vuelve a levantar la revisión anterior por digest y `--no-build`;
- devuelve `70` si falla el propio rollback, en lugar de ocultarlo.

El modo aislado no acepta una raíz arbitraria ni puede apuntar a los paths de
producción. La autenticación simulada no usa credenciales.

### Selección GPU detenida

`deploy/gpu/select-desired-release.sh` valida la proyección y el bundle, exige
que `hemovet-llm-gpu` esté `TERMINATED`, conserva los bytes anteriores, instala
la metadata candidata y realiza read-back byte por byte. Si cualquier paso
falla, restaura la metadata previa; nunca inicia la VM.

### Readiness del proveedor

La prueba con la imagen publicada reveló que el health podía consumir unos 10
segundos con la GPU inaccesible, aunque `core_ready=true`. Se acotó el request
de health del proveedor a 1.5 segundos y la combinación identidad/residencia a
2 segundos. RAG sigue evaluándose de forma independiente. Esto mantiene la
frontera del monolito: health de infraestructura no bloquea persistencia ni
readiness del núcleo.

## Escenarios ejecutados

### 1. Instalación válida aislada

Se creó un namespace Compose temporal sin Caddy ni puertos públicos. El
candidato validó el manifiesto, instaló el entorno, seleccionó la colección RAG
y registró exactamente los digests backend/frontend esperados. La imagen real
backend `af5…@sha256:c710…` arrancó, aplicó migraciones `0001` a `0012` y
respondió con `core_ready=true` y `database_ready=true`.

### 2. Fallo controlado después de instalar el entorno

Un adaptador Docker de prueba devolvió `42` al ejecutar `up` del candidato. El
trap ejecutó el rollback acotado y conservó el código original del fallo. Se
repitió el mismo escenario dos veces para demostrar idempotencia.

En ambos intentos:

```text
transaction state       ROLLED_BACK
original return code    42
rollback result         completed
active .env             byte-identical al anterior
RAG_COLLECTION_NAME     colección anterior
current/previous links  valores anteriores exactos
backend/frontend refs   digests anteriores
mutable tags            ninguno
```

### 3. Colecciones y datos

Se conservaron sin cambios los hashes de dos árboles Chroma sintéticos,
representando colección anterior y candidata. No se ejecutó delete/reset ni se
reescribió una colección.

Una base SQLite de evidencia conservó el hash completo y los conteos de las
tablas sintéticas `users`, `owners`, `pets`, `hemograms`,
`chat_conversations` y `chat_turns`. La prueba demuestra que el orquestador no
toca datos; producción no fue consultada ni modificada.

### 4. Compatibilidad de migraciones

El árbol `backend/alembic` del candidato publicado `af5…` coincide con el árbol
anterior, SHA-1 Git `1f6c11fdb4f301534e63f98cd0f7ce012ee4a312`. La imagen candidata
aplicó todas las migraciones en la base aislada. No existe una migración
destructiva nueva que impida volver a la revisión anterior.

### 5. Rollback GPU diferido

Con la VM apagada se ejecutó el ciclo real:

```text
515d343a… / sha256:b526b1d4…
  -> af5ab60… / sha256:de0833bd…
  -> 515d343a… / sha256:b526b1d4…
```

Ambos cambios pasaron validación contractual y comparación exacta. El hash del
valor completo de metadata volvió a
`5bf601f00844b4276de21f7932256dc39e9274d1ec4a99127f717502c6f7e57e`. La
VM permaneció `TERMINATED`, sus timestamps de start/stop no cambiaron y el
snapshot continuó `READY`.

### 6. Referencia no autorizada

El run `30778878989` ejecutó correctamente backend, frontend y configuración,
pero WIF rechazó el build desde esta rama con `unauthorized_client`. Build/push,
metadata GPU, deploy y smoke quedaron sin ejecutar. No existe tag OCI
`sha-ee9fa759…`. Es el comportamiento fail-closed esperado; no se relajó el
provider restringido a `main` para fabricar evidencia.

## Pruebas y resultados

```text
Python                              3.11
backend/tests                       966 passed, 1 skipped, 4 subtests
rollback/health/provider focales    37 passed
Ruff                               PASS
Bash syntax                        PASS
ShellCheck                         PASS
GPU bundle checksums               PASS
Compose local                      PASS: app + ollama/ollama_setup
Compose production                 PASS: app, sin Ollama
Compose GPU                        PASS: ollama + ollama_setup
git diff --check                   PASS
frontend CI run 30778878989         PASS
backend CI run 30778878989          PASS
deployment config run 30778878989  PASS
WIF branch rejection               PASS esperado
```

Incidencias transparentes del harness final:

- el `python3.11` global carecía de pytest/Ruff y no ejecutó casos;
- una primera referencia ShellCheck tenía un digest transcrito incorrectamente;
  la referencia completa versionada sí pasó;
- dos invocaciones pytest omitieron primero `PYTHONPATH` y luego las variables
  mínimas; abortaron en colección;
- una invocación desde `backend/` ejecutó 966 casos, pero cinco tests Alembic
  resolvieron el cwd transitorio incorrecto (`961 passed`, 5 failed). El gate
  oficial desde la raíz con `PYTHONPATH=backend` pasó los 966 casos.

No se cambió código para ocultar estos errores de preparación y ninguno se
contabiliza como gate exitoso.

## Estado final comprobado

| Elemento | Estado restaurado |
| --- | --- |
| Producción | `RUNNING`; mismo start `2026-07-02T06:45:52.411-07:00` |
| Sitio público | HTTP 200, 1,167 bytes |
| Chat público | degradado esperado; Chroma/RAG listos; 4,696 chunks |
| GPU | `TERMINATED`; no se inició en Etapa 9 |
| Revisión GPU | `515d343a…`, runtime `sha256:b526b1d4…`, `pending_boot_validation` |
| Snapshot | `READY`, 58,891,150,336 bytes, no eliminado |
| IPs | producción `136.64.136.49`; GPU `34.45.75.48`, sin cambios |
| Recursos temporales | Compose/containers/volúmenes/red aislados eliminados |
| Artifact Registry | sin tag para `ee9fa759…`; ningún objeto eliminado |

## Riesgos y limitaciones conocidas

1. **MEDIO — solo existe un `hemovet.release/v1` real completo.** `515d…`
   conserva digests y revisión GPU, pero no un manifiesto completo histórico.
   Por ello la prueba anterior se reconstruyó contractualmente en el entorno
   aislado; una prueba viva entre dos manifiestos completos queda pendiente de
   publicar una segunda revisión autorizada desde `main`.
2. **MEDIO — health de la imagen publicada.** `af5…` arranca y mantiene el
   núcleo listo, pero su probe previo puede tardar ~10 segundos con GPU
   inaccesible y exceder el healthcheck interno de 5 segundos. El fix está en
   el commit funcional de Etapa 9 y requiere una futura publicación autorizada.
3. **MEDIO — no hubo rollback productivo.** Fue una restricción explícita para
   evitar cutover. La equivalencia viva de PostgreSQL/Chroma y smoke público de
   ambas revisiones corresponde a la ventana de aceptación posterior.
4. **BAJO — limpieza del namespace de prueba.** El modo aislado usa eliminación
   recursiva solo dentro de una raíz temporal con patrón, propietario, modo y
   sentinel verificados; las pruebas comprueban el rechazo de roots inseguros.

Ninguna limitación implica una pérdida o inconsistencia actual. Sí impiden
afirmar que el rollback productivo ya fue ejecutado.

## Procedimiento manual de emergencia

1. detener nuevos deploys y adquirir el lock productivo;
2. registrar `current`, `previous`, transaction ID, manifiesto activo y estado
   de PostgreSQL/Chroma;
3. seleccionar un `hemovet.release/v1` completo y validarlo con
   `validate_rollback_bundle.py`; no editar digests individualmente;
4. si el deploy candidato falla, dejar que `deploy-release.sh` restaure entorno,
   RAG, enlaces y Compose; si devuelve `70`, no continuar y restaurar
   manualmente desde `previous.env`/`transaction.json` tras verificar digests;
5. comprobar core/database/RAG readiness y datos antes de reabrir tráfico;
6. con GPU `TERMINATED`, seleccionar la proyección anterior mediante
   `select-desired-release.sh --previous-output <archivo-0600>`; no encenderla
   hasta validar el read-back;
7. si el boot disk GPU estuviera dañado, crear un disco nuevo desde
   `hemovet-llm-gpu-pre-stage6-20260802`; no restaurar sobre el disco existente;
8. conservar evidencia y no eliminar imágenes, colecciones, snapshot o revisión
   fallida hasta cerrar el incidente.

## Costos

- GPU: USD 0 atribuible; nunca se encendió.
- Compute Engine/metadata: sin costo incremental de cómputo.
- Artifact Registry: no se publicó ni eliminó una imagen; continúa el costo de
  almacenamiento ya existente.
- Snapshot: continúa su costo recurrente previo; no se creó otro snapshot.
- GitHub Actions: el run negativo consumió aproximadamente seis minutos Linux;
  el cargo efectivo depende de la cuota del repositorio y no se verificó una
  factura.
- El pull local de imágenes puede generar transferencia facturable según la
  ruta y tarifa aplicable; no se atribuye un importe no verificado.

## Rollback de la Etapa 9

Crear un commit normal que revierta primero el cierre documental y después el
commit funcional `ee9fa759670caa56eaceadc40b6561516ab9949f`. No usar reset,
clean, force push ni modificar `dips.md`. La metadata GPU ya quedó restaurada;
producción y datos no requieren reversión.

## Decisión de avance

El mecanismo coordinado queda validado en aislamiento y la revisión GPU quedó
restaurada. No se autoriza Etapa 10 ni un deploy; antes de aceptación E2E debe
publicarse desde una referencia WIF autorizada una revisión que incluya el fix
de health, conservando el manifiesto `af5…` como rollback completo.
