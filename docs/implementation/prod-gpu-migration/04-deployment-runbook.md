# Runbook de despliegue

Estado: **NO HABILITADO PARA PRODUCCIÓN**. La Etapa 1 entrega y prueba el
mecanismo local, pero no modifica GitHub Actions ni ejecuta despliegues.

## Transacción de entorno preparada para integración futura

1. Preparar `.env.next` desde el resultado validado de staging:

   ```bash
   python3 backend/scripts/prepare_rag_promotion.py \
     --promotion-json promotion.json \
     --source-env .env \
     --target-env .env.next
   ```

2. Validar el archivo completo:

   ```bash
   python3 backend/scripts/validate_deploy_env.py .env.next
   ```

3. Instalarlo con un directorio de transacción único y privado:

   ```bash
   python3 backend/scripts/manage_deploy_env.py install \
     --candidate-env .env.next \
     --active-env .env \
     --transaction-dir /var/lib/hemovet/deploy-transactions/<release-id> \
     --expected-collection <coleccion-validada>
   ```

El instalador valida antes de cambiar estado, respalda el entorno completo con
modo `0600`, usa `os.replace()` en el mismo filesystem, sincroniza archivo y
directorio, vuelve a validar y revierte automáticamente ante un fallo. No
imprime valores del entorno.

La integración del paso 3 en CI/CD queda pendiente de la etapa autorizada para
GitHub Actions. Hasta entonces, este runbook no autoriza su ejecución contra
producción.

## Validación contractual de una release candidata

La Etapa 2 añadió el esquema `hemovet.release/v1`, pero no lo conectó a ningún
workflow ni destino. Un operador puede validar únicamente un archivo local con:

```bash
PYTHONPATH=backend python -c \
  "from app.core.release_manifest import load_release_manifest; load_release_manifest('deploy/releases/release-manifest.example.json')"
```

El ejemplo contiene identidades ilustrativas y no debe publicarse ni aplicarse.
La publicación inmutable, el estado deseado de GPU y el consumo del manifiesto
pertenecen a etapas posteriores.

## Convención OCI preparada en la Etapa 3

Repositorio:

```text
us-central1-docker.pkg.dev/project-5b36701c-f44f-4c03-a12/hemovet-images
```

Paquetes: `backend`, `frontend` y `ollama-runtime`. Una compilación autorizada
publica una única vez `sha-<GITHUB_SHA completo>` y registra la resolución:

```text
<repositorio>/<paquete>:sha-<GITHUB_SHA>
  -> <repositorio>/<paquete>@sha256:<digest real>
```

El tag no se usa como selector desplegable. `docker pull`, Compose futuro y el
manifiesto de release deben consumir la forma por digest. El validador local es:

```bash
PYTHONPATH=backend python backend/scripts/validate_artifact_set.py \
  deploy/releases/artifact-set-<GITHUB_SHA>.json
```

`backend/scripts/bind_release_artifacts.py` incorpora esos digests a un
`hemovet.release/v1` completo y valida que el SHA coincida. No publica ni
despliega. WIF ya fue validado para publicación aislada; Compose ya exige estas
referencias por digest, mientras el build/publicación automatizados y el
despliegue continúan pendientes de la Etapa 8.

## Renderizado de Compose de la Etapa 4

La separación está versionada, pero **no está desplegada**. El gate local
reproducible es:

```bash
PYTHONPATH=backend python backend/scripts/validate_compose_topology.py
```

Comandos soportados por destino:

```bash
# Desarrollo
docker compose --env-file .env.example \
  -f docker-compose.yml -f docker-compose.local.yml config --quiet

# Producción (solo renderizado en esta etapa)
docker compose --env-file .env.production.example \
  -f docker-compose.yml -f docker-compose.prod.yml config --quiet

# GPU autónoma (solo renderizado en esta etapa)
docker compose --env-file deploy/gpu/compose.env.example \
  -f docker-compose.gpu.yml config --quiet
```

No combinar GPU con base o producción. Un despliegue futuro de producción debe
resolver `HEMOVET_BACKEND_IMAGE` y `HEMOVET_FRONTEND_IMAGE` desde un manifiesto
validado, ejecutar `pull` y `up --no-build`. La integración corresponde a la
Etapa 8 y estos comandos no autorizan ejecutarla ahora.

## Gate manual WIF de la Etapa 3

El workflow productivo acepta `workflow_dispatch` con el input
`stage3_wif_validation`. Su valor por defecto es `DENY`; únicamente `VALIDATE`
habilita los dos jobs de prueba. Los jobs de backend, frontend, configuración y
despliegue quedan excluidos del evento manual.

Ejecución autorizada:

```bash
gh workflow run deploy.yml \
  --ref main \
  -f stage3_wif_validation=VALIDATE
```

El gate:

1. verifica que un job sin environment sea rechazado por WIF;
2. usa `environment: production` para el caso positivo;
3. obtiene un token de acceso de 600 segundos sin clave JSON;
4. publica una imagen `scratch` en el paquete `wif-validation`;
5. comprueba la referencia remota por digest;
6. elimina el login Docker del runner al terminar.

Esto no es un despliegue y no sustituye el workflow inmutable final de la
Etapa 8. No debe ejecutarse sin autorización porque cada run válido crea un tag
inmutable de evidencia.

## Flujo inmutable de la Etapa 8

El workflow versionado tiene tres operaciones manuales:

```bash
gh workflow run deploy.yml --ref main -f operation=VALIDATE_WIF_IAP
gh workflow run deploy.yml --ref main -f operation=PUBLISH
gh workflow run deploy.yml --ref main -f operation=DEPLOY \
  -f confirm_sha=<GITHUB_SHA-completo>
```

`VALIDATE_WIF_IAP` no construye ni muta. `PUBLISH` prueba, construye y genera
evidencia, pero no cambia GPU o producción. Solo `DEPLOY`, desde `main` y con el
SHA exacto, puede publicar metadata GPU y ejecutar el script transaccional por
IAP. El environment `production` se aplica a los jobs con identidad cloud.

Un push no documental a `main` ejecuta tests y publica artefactos OCI; nunca
cambia metadata GPU o la aplicación sin el dispatch `DEPLOY`. Un push solo
documental evita el build.

Antes del primer `DEPLOY` real se debe:

1. asociar `hemovet-prod-runtime` a producción en una ventana aprobada;
2. habilitar y probar OS Login/IAP dos veces, incluido `sudo`;
3. confirmar acceso de emergencia;
4. verificar backup PostgreSQL/Chroma y rollback anterior;
5. comprobar que el manifiesto descargado coincide con `confirm_sha`;
6. mantener Ollama local y SSH legado hasta completar rollback.

El script remoto acepta únicamente archive, manifiesto y entorno candidato
privado; valida antes de hacer pull, usa `pull`/`up --no-build`, promociona RAG
de forma inmutable y restaura el estado anterior si readiness falla. Ver
`18-github-actions-immutable-deployment.md`.

Antes del primer uso productivo debe ejecutarse el preflight coordinado de
`06-rollback-runbook.md`: validar release, artifact set, entorno, source y GPU
con `validate_rollback_bundle.py`, registrar el intento transaccional y
confirmar que la revisión anterior continúa disponible. La evidencia aislada y
sus limitaciones están en `19-integral-rollback-validation.md`.
