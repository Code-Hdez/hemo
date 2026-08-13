# Modelo de seguridad

## Sesiones conversacionales

- El router convierte `X-HemoVet-Browser-Session-ID` en un HMAC de 64 caracteres;
  el identificador crudo no se persiste.
- El port exige `user_id`, `auth_session_id` y `browser_session_hash` en las
  operaciones de historial y turnos.
- Una conversación que ya posee `browser_session_hash` solo puede consultarse o
  mutarse presentando exactamente ese hash.
- Los registros antiguos con hash nulo continúan sujetos a usuario y sesión
  autenticada; pueden asociarse al navegador durante una restauración
  autorizada mediante `get_or_create()`.
- No existe reintento por `TypeError` que elimine filtros. Un adaptador con firma
  incompatible falla cerrado y debe corregirse.
- Las limpiezas de turnos fallidos o interrumpidos filtran por hash exacto; si
  no existe hash, solo consideran conversaciones legacy con valor nulo.

## Entorno y secretos

- El candidato y el activo deben ser archivos regulares, no symlinks.
- El entorno y su respaldo usan modo `0600`; el directorio de transacción usa
  `0700`.
- El manifiesto contiene estados, nombres de colecciones y digests, nunca
  valores de variables.
- La salida CLI contiene solo estado y nombres de colección.
- Los errores exponen nombres de campos, no secretos.

## Infraestructura

No se alteraron firewall, IAM, IPs, metadata, discos, instancias, GitHub
secrets, variables o environments durante la Etapa 1.

## Frontera de inferencia definida en la Etapa 2

- El port remoto solo transporta inferencia; datos, RAG, autorización,
  persistencia y validación permanecen en producción.
- Health y logs no exponen `OLLAMA_BASE_URL`, IPs privadas ni secretos.
- La correlación usa `X-HemoVet-Correlation-ID`; no contiene el prompt ni un
  identificador clínico y no se persiste como contenido.
- El contrato exige red privada en producción, pero la restricción de firewall
  y su prueba pertenecen a la Etapa 7 y aún no se declaran aplicadas.
- Las imágenes del manifiesto se identifican por digest y el modelo no admite
  `latest`.

Durante la Etapa 2 tampoco se alteraron firewall, IAM, IPs, metadata, discos,
instancias, GitHub Actions, secrets, variables o environments.

## Cadena de suministro e identidades de la Etapa 3

- Construcción, producción y GPU tienen cuentas separadas; la cuenta default de
  Compute Engine no es la identidad definitiva diseñada.
- El writer existe solo en `hemovet-images`; las cuentas runtime solo tienen
  `roles/artifactregistry.reader` en ese repositorio.
- GitHub puede impersonar CI únicamente a través de un `principalSet` de ese
  repositorio y un provider que además exige IDs numéricos inmutables de
  repositorio/propietario, `main`, workflow exacto y environment `production`.
- No se crearon claves JSON ni se concedió `serviceAccountTokenCreator`.
- Los tags `sha-<GITHUB_SHA>` son informativos e inmutables; toda referencia
  desplegable debe usar `@sha256:<digest>`. `latest` falla la validación.
- Las bases de backend, frontend y Ollama quedan fijadas por digest; las imágenes
  publicadas incluyen labels OCI de source, revision y created.
- La política de limpieza solo considera blobs sin tag de más de 30 días y está
  en `dry-run`; no elimina nada en esta etapa.
- El workflow expone únicamente un gate WIF manual. La acción oficial de Google
  está fijada por SHA, cada job declara permisos mínimos y no crea archivos de
  credenciales. Los jobs normales y el despliegue se omiten en el dispatch.
- El caso positivo publicó por digest usando `environment: production`; el
  caso sin environment fue rechazado por la condición de atributos.
- El environment no contiene secrets ni reglas de protección. `main` tampoco
  tiene branch protection o rulesets; esto debe resolverse antes de retirar el
  acceso legado. La condición WIF limita el impacto, pero no sustituye una rama
  protegida.
- WIF ya funciona, pero todavía no sustituye al SSH productivo: retirar esos
  secrets exige la migración gradual y las pruebas posteriores establecidas.

No se modificaron firewall, VPC, IPs, metadata, discos, instancias, service
accounts asociadas a VMs, secrets ni variables. Las únicas mutaciones GitHub
fueron el gate manual versionado, el commit aislado de `main` y la creación
automática del environment vacío `production`; no hubo despliegue.

## Fronteras Compose de la Etapa 4

- El perfil productivo no contiene `ollama`, `ollama_setup`, reserva GPU ni
  publicación de `11434`.
- El perfil GPU admite exactamente `ollama` y `ollama_setup`; rechaza nombres de
  servicios y variables de PostgreSQL, Chroma, RAG o secretos de aplicación.
- `11434` usa un bind obligatorio a una IPv4 privada no loopback/no wildcard.
  Esto es defensa en profundidad y no sustituye el firewall de la Etapa 7.
- Las imágenes externas y los tres artefactos HemoVet se fijan por digest; los
  targets producción/GPU no conservan bloques `build` efectivos.
- La GPU recibe un archivo de ejemplo propio sin secretos. El `.env` productivo
  no se comparte con la VM GPU.
- Las dependencias `depends_on` solo pueden referenciar servicios del mismo
  Compose. Producción no espera a un servicio externo de Ollama para arrancar.

El validador ejecutable falla si estas fronteras se alteran. No se modificaron
firewall, VPC, IPs, metadata, discos, VMs, IAM o GitHub durante la Etapa 4.

## Runtime GPU de la Etapa 6

- La VM utiliza la identidad exclusiva
  `hemovet-gpu-runtime@project-5b36701c-f44f-4c03-a12.iam.gserviceaccount.com`.
  Su único permiso aplicativo es lectura de `hemovet-images`; no posee claves
  administradas por usuario.
- Artifact Registry se autentica con un access token corto obtenido del
  metadata server. El `DOCKER_CONFIG` vive en `/run/hemovet-gpu`, se elimina al
  finalizar y el escaneo de journald no encontró tokens, passwords, secretos o
  claves privadas.
- Imagen, release, bundle y modelo se validan por digest. El runtime rechaza
  `latest`, referencias fuera del paquete, estado distinto de
  `pending_boot_validation`, actualización en caliente y campos extra.
- El Compose ejecutado contiene exclusivamente `ollama` y `ollama_setup`, usa
  `no-new-privileges`, límites de recursos, runtime NVIDIA y volumen propio.
- Ollama escucha en el contenedor sobre wildcard, pero Docker publica únicamente
  `10.128.0.3:11434`. No existen listeners GPU en `80` o `443`; Caddy no está
  instalado en el stack autónomo.
- La IP externa `34.45.75.48:11434` expiró desde Internet. Esto es evidencia de
  no exposición actual, no sustituto de la regla exclusiva origen/destino que
  se implementará y probará en la Etapa 7.
- El acceso SSH temporal de Etapa 6 fue retirado: se restauraron las cuatro
  entradas originales de metadata, la cuenta temporal quedó expirada, la clave
  fue rechazada y el material local fue destruido. La adición accidental de una
  clave a metadata común se revirtió inmediatamente sin alterar las cinco
  entradas preexistentes.
- El servicio host Ollama y los contenedores heredados quedaron detenidos y con
  `restart=no`; no se borraron volúmenes o datos. Esto reduce exposición sin
  convertir la etapa en una eliminación destructiva.
- Los manifiestos y estados operativos usan `0600`; los directorios privados,
  `0700`. La inferencia de aceptación usa un prompt sintético no clínico y no
  registra prompt ni respuesta.

La Etapa 6 no cambió firewall, VPC, subred, tags, IPs, GitHub Actions, secrets,
variables o environments. SSH público, reglas internas amplias, tags públicos
y deletion protection continúan como riesgos explícitos para la Etapa 7.

## Frontera GCP aplicada en la Etapa 7

La autorización de inferencia se implementa con defensa en profundidad:

- Docker publica Ollama únicamente en `10.128.0.3:11434`;
- firewall permite `10.128.0.2/32` hacia la service account GPU a TCP/11434;
- una denegación de prioridad posterior rechaza cualquier otro origen a
  TCP/11434;
- otra denegación específica de la GPU prevalece sobre
  `default-allow-internal`, SSH heredado y tags públicos;
- el navegador y Caddy no tienen ruta directa a la GPU.

Se usa la IP privada exacta de producción porque GCP no admite service accounts
de origen en una regla ingress del mismo modo que permite service accounts de
destino. La IP está ligada a la NIC existente, se verificó y se protege
preservando la instancia. No se creó DNS ni una reserva interna que añadiera
otra pieza operativa sin consumidor múltiple.

La administración GPU usa IAP (`35.235.240.0/20 → tcp:22`) y OS Login. El rol
de túnel está condicionado por puerto y las dos IPs privadas; OS Admin Login se
asigna a nivel de cada instancia y Service Account User solo en las identidades
que debe actuar el administrador. No se creó ninguna clave JSON.

OS Login de producción aún no está activo porque el workflow legado usa claves
SSH de metadata. IAP sí fue probado en producción con una clave temporal que se
retiró. `default-allow-ssh` continúa global solo para preservar ese despliegue;
la GPU no queda expuesta porque su denegación de prioridad 900 lo impide. La
migración de ese último camino es obligatoria en Etapa 8 antes de retirarlo.

Los tags `http-server` y `https-server` se retiraron de la GPU. Las dos VMs
tienen deletion protection y sus boot disks `autoDelete=false`; eso evita que
una eliminación accidental arrastre datos, sin impedir stop/start. El snapshot
pre-Etapa 6 permanece `READY`.

Una revisión GPU inválida falla cerrada y activa una unidad `OnFailure`: deja
evidencia mínima `0600` y solicita poweroff desde el guest. La prueba real
conservó imagen, manifiesto y pesos; no expuso secretos en journald y una
revisión válida posterior volvió a `full_gpu`.

Riesgos residuales explícitos:

- los dos bindings humanos `Owner` preexistentes permiten más que el IAM nuevo;
- producción todavía usa la Default Compute Engine service account;
- SSH público sigue aplicando a producción hasta migrar el workflow;
- la IP `10.128.0.3` no sobreviviría a eliminar/recrear la VM;
- el disco GPU al 74% requiere cleanup posterior con inventario y aprobación,
  nunca un prune destructivo indiscriminado.

La matriz exacta y los procedimientos de emergencia están en
`17-gcp-network-security.md` y `06-rollback-runbook.md`.

## Frontera CI/CD aplicada en la Etapa 8

- GitHub obtiene tokens efímeros por OIDC/WIF; no hay service-account JSON.
- El provider exige repo y owner por nombre e ID, environment `production`,
  `main` y el workflow exacto.
- La identidad CI escribe imágenes solo en `hemovet-images`; runtime conserva
  solo lectura.
- IAP de CI está limitado a la IP privada de producción y TCP/22.
- La publicación de metadata usa un rol de dos permisos condicionado a la VM
  GPU exacta; no permite start/stop/reset.
- Toda mutación de GPU o producción exige `DEPLOY`, `main` y confirmación del
  SHA; `PUBLISH`, validaciones y pushes no alteran runtimes.
- El artefacto release excluye el entorno privado. El candidato `0600` existe
  solo temporalmente en runner/host y los scripts no usan `set -x`.
- Logs representativos no contienen patrones de keys, tokens, API keys,
  credenciales PostgreSQL o el payload de `PRODUCTION_ENV_B64`.

La transición mantiene conscientemente SSH público, secrets SSH y Default
Compute SA en producción porque retirarlos antes del cutover rompería el
workflow vigente. El nuevo código no consume esos secrets y falla cerrado hasta
que `hemovet-prod-runtime` esté asociada. Ver `18-github-actions-immutable-deployment.md`.
