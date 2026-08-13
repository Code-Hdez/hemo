# Estado final de la migración

Estado global: `IN_PROGRESS`; Etapas 0–10 `COMPLETED`; el cutover de Etapa 11
está aplicado y su validación live final está diferida; Etapa 12 pendiente.

La implementación, rollback y aceptación técnica aislada están completos. La
nueva revisión aún no está desplegada públicamente y no se declara puesta en
servicio.

## Estado acumulado al cierre de Etapa 10

- Revisión final aceptada:
  `e7713a72369bb9365f6d5323e165fbf84488bfb4`.
- Backend, frontend y runtime GPU están publicados y fijados por digest en
  `hemovet.release/v1`.
- La revisión anterior completa `af5ab60b…` está preservada como rollback.
- Los 19 casos automatizados de aceptación pasaron en un namespace Compose sin
  puertos públicos ni datos productivos.
- Qwen `qwen3:4b-instruct-2507-q4_K_M` fue validado por identidad,
  cuantización e inferencia `full_gpu` sobre la NVIDIA L4.
- El núcleo, historial y frontend aislados permanecieron disponibles con la
  GPU apagada y el proveedor degradado; la recuperación no reinició backend.
- Producción conserva exactamente sus contenedores anteriores, Ollama local,
  tráfico, base de datos, Chroma y colección RAG.
- La GPU quedó apagada, el snapshot `READY` y la metadata deseada previa
  restaurada.

No se declara la migración operativa: Etapa 11 debe ejecutar el cutover
controlado y Etapa 12 cerrar la documentación posterior a puesta en servicio.

## Estado acumulado después del cutover de Etapa 11

- Producción ejecuta `069df45f7becbf1bf698a3ee6a8a9305e3aa4d1f` con backend
  `sha256:1d27af…` y frontend `sha256:1681df…`.
- El entorno activo coincide con el digest del manifiesto, usa modo `0600` y
  selecciona la colección RAG inmutable aprobada con 4,696 chunks.
- Core, PostgreSQL, Chroma, RAG, frontend y Caddy están saludables. Con la GPU
  apagada, el estado es `degraded` y no `fail`.
- Los conteos de usuarios, mascotas, análisis, parámetros y conversaciones no
  cambiaron durante el cutover.
- Producción usa la service account `hemovet-prod-runtime`; la GPU conserva la
  identidad runtime separada.
- Ollama local sigue disponible como rollback/orphan, pero no pertenece al
  Compose de producción activo.
- La GPU quedó `TERMINATED` con la revisión `069df45f…` deseada en
  `pending_boot_validation`.
- El snapshot GPU de Etapa 6 y el snapshot productivo inmediato de Etapa 11
  están `READY`.
- SSH y secrets antiguos continúan disponibles: no se retirarán sin dos
  accesos IAP/OS Login y recuperación administrativa verificados.

Por instrucción del usuario no se ejecutaron las validaciones live restantes.
La aplicación principal sí está puesta en servicio; la disponibilidad del chat
con la revisión GPU actual, el cutover administrativo final y la retirada del
acceso heredado quedan `NO VERIFICADO`. El detalle está en
`22-stage11-controlled-service.md`.

## Hito histórico: cierre de Etapa 1

- Contrato de sesión uniforme y sin fallbacks inseguros.
- `turn_history()` autorizado por usuario, sesión autenticada y navegador.
- Candidato RAG derivado de staging sin mutar colecciones anteriores.
- Instalación y rollback completos disponibles como CLI versionada.
- Producción, GCP, GPU y GitHub Actions sin cambios.
- En ese hito, Etapa 2 aún no se había iniciado.

## Estado acumulado al cierre de Etapa 8

Estado global: `IN_PROGRESS`; Etapas 0–8 `COMPLETED`; Etapas 9–12 pendientes.

- Arquitectura, disponibilidad, proveedor y release tienen contratos
  versionados.
- Compose local, producción y GPU están separados y validados.
- Backend/frontend degradables y runtime GPU reconciliable están implementados.
- Red privada, firewall GPU, IAP GPU y protecciones GCP están aplicados.
- GitHub Actions usa WIF, imágenes por digest, SBOM/provenance y
  `hemovet.release/v1`.
- La revisión `af5ab60b…` está publicada, pero no desplegada.
- Producción continúa con el stack anterior, Ollama local, Default Compute SA,
  OS Login sin activar y SSH de emergencia preservado.
- GPU permanece apagada y conserva la revisión validada en Etapa 7; Etapa 8 no
  cambió su metadata.
- PostgreSQL, Chroma, RAG productivo y datos clínicos no fueron modificados.

No se declara la migración completa: faltan rollback integral probado con la
nueva release, aceptación E2E, cutover administrativo/productivo y puesta en
servicio. Etapa 9 requiere autorización explícita.
