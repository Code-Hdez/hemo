# Verificación en vivo de las dos VMs de GCP — 2026-08-02

Pregunta a responder: ¿`hemovet-prod` y `hemovet-llm-gpu` funcionan de manera
independiente (una se encarga de Ollama, la otra de todo lo demás)?

## Método

`gcloud compute instances list/describe` (sin encender la VM GPU — tiene
costo, no se hizo sin confirmar) + `gcloud compute ssh hemovet-prod`
(solo lectura) para inspeccionar contenedores, variables de entorno y logs
reales en producción.

## Resultado

**Sí son independientes, pero no en el sentido que sugiere el diagrama actual
de despliegue (4.2.5).** No es "una VM = Ollama, otra VM = resto"; es más
bien: `hemovet-prod` es autosuficiente y `hemovet-llm-gpu` no participa en
absoluto del sistema en producción hoy.

```text
$ gcloud compute instances list
NAME             ZONE           MACHINE_TYPE   PREEMPTIBLE  STATUS
hemovet-llm-gpu  us-central1-a  g2-standard-4  true         TERMINATED
hemovet-prod     us-central1-a  e2-standard-8               RUNNING
```

- `hemovet-prod` corre **su propio Ollama local** (contenedor
  `hemogramas-proyectoicc-ollama-1`, imagen `ollama/ollama:0.30.10`, CPU-only,
  6 días arriba) junto con backend, frontend, Caddy, PostgreSQL y ChromaDB —
  los 6 servicios del `docker-compose.yml` + `docker-compose.prod.yml`, todos
  en el mismo host.
- `.env` de producción: `OLLAMA_BASE_URL=http://ollama:11434/` (alias de red
  interna de Docker) y `OPENAI_COMPATIBLE_BASE_URL=` vacío. Ningún valor
  apunta a la IP privada de `hemovet-llm-gpu` (`10.128.0.3`).
- `hemovet-llm-gpu` **no aparece en ningún archivo de configuración
  desplegado**: no está en `docker-compose*.yml`, no está en `.env.production.example`,
  no tiene startup-script en su metadata de GCE (`install-nvidia-driver: true`
  es la única entrada — ningún script de arranque que instale Docker/Ollama
  automáticamente), y el workflow de despliegue
  (`.github/workflows/deploy.yml`) solo hace SSH a **un** host
  (`secrets.GCP_HOST`) y solo aplica `docker-compose.yml + docker-compose.prod.yml`
  — nunca `docker-compose.gpu.yml`, nunca toca la VM GPU.
- `docker-compose.gpu.yml` es, según su propio comentario, un "Perfil NVIDIA
  para la VM productiva **existente**" — es decir, fue diseñado para
  añadir GPU al mismo `hemovet-prod` si tuviera GPU, no como manifiesto de
  una VM separada solo-Ollama.

**Conclusión para el diagrama 4.2.5:** describir el sistema como "dos VMs, una
para Ollama y otra para el resto" es engañoso. La realidad verificable hoy es
"una VM autosuficiente en producción (incluye su propio Ollama CPU); una
segunda VM con GPU aprovisionada pero desconectada del despliegue, apagada,
sin automatización que la use". Si se quiere presentar el caso GPU como
arquitectura soportada (no solo aspiracional), hace falta documentar el
procedimiento manual real de activación — hoy no existe en el repo.

## Hallazgo operativo adicional (no arquitectónico, pero verificado en vivo)

Al inspeccionar el estado de los contenedores se encontró que
`hemogramas-proyectoicc-backend-1` llevaba **11 horas en estado `unhealthy`**
(Docker healthcheck, `FailingStreak: 2439`).

Causa raíz confirmada:

1. `/api/v1/chat/health` devolvía `llm_ready: false`,
   `identity_error_code: "ollama_model_identity_unverified"`,
   `runtime.loaded: false`.
2. `ollama ps` (dentro del contenedor Ollama) mostraba **ningún modelo
   cargado en memoria** — Ollama descarga el modelo tras inactividad
   (`OLLAMA_KEEP_ALIVE=30m`; sin tráfico de chat en ese lapso, se descarga).
3. El healthcheck del backend exige no solo que el modelo *exista* en Ollama
   (`/api/tags`), sino que esté **actualmente residente** con el digest y
   cuantización esperados (`/api/ps`, vía `validate_ollama_runtime_identity`
   en `composition.py:196`). Si no está cargado, `llm_ready` se fuerza a
   `False` aunque el resto del sistema esté sano.
4. Se forzó la recarga manualmente: `ollama run qwen3:4b-instruct-2507-q4_K_M`
   (~12 s en CPU). Inmediatamente `/api/v1/chat/health` volvió a
   `status: "ok"`, `llm_ready: true`, y el healthcheck de Docker pasó a
   `healthy` (`FailingStreak` reseteado a 0).

Esto **no es un problema de arquitectura ni de las dos VMs** — es un efecto
esperado del `keep_alive` de Ollama combinado con un healthcheck estricto que
no distingue "listo pero en cold-start" de "roto". Vale la pena citarlo en
Capítulo VI/VII como limitación operativa conocida (posible mejora: un ping de
calentamiento periódico, o relajar el healthcheck para no marcar `unhealthy`
por inactividad normal).
