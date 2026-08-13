# 02 — Arquitectura real observada

Todo verificado en el sistema desplegado, no deducido del repositorio.

## VMs (GCP `project-5b36701c-f44f-4c03-a12`, zona `us-central1-a`)

| | `hemovet-prod` | `hemovet-llm-gpu` |
|---|---|---|
| Máquina | `e2-standard-8` | `g2-standard-4` |
| GPU | — | **NVIDIA L4**, driver 580.159.03, 23.034 MiB, 300 GB/s |
| Contenedores | backend, caddy, frontend, db, chroma (5, healthy) | `hemovet-gpu-ollama-1` |
| Red | 10.128.0.2 / 136.64.136.49 | 10.128.0.3 / 34.45.75.48 |

Ollama escucha en **`10.128.0.3:11434`** (no responde en `127.0.0.1`: está
publicado por `docker-proxy` sobre la IP interna).

## Identidad del despliegue — CONFIRMADO

```
HEMOVET_BUILD_REVISION = 21f18fd8889541dbd947c3692ccbdc0fc6ee0660   (dentro del contenedor)
git rev-parse HEAD     = 21f18fd8889541dbd947c3692ccbdc0fc6ee0660   (local)
backend image          = backend@sha256:86833576b609be8268f5c0bf29fd07b96d6967e29db0c9edb9d5f224ff9bf6d6
ollama image           = ollama-runtime@sha256:96367c0305543e7ea17ecb30f7589602ebfc1ee48be3e3769333ce11d4d05a0e
release                = /opt/hemovet-prod/releases/c1193ae29dc95275606acd7b5c5abafb8170aa02/source/
env file               = /var/lib/hemovet-prod/.env
contenedor creado      = 2026-08-06T19:13:03Z   (batería: 2026-08-07T23:49Z)
```

**El código leído es exactamente el que produjo las 70 respuestas.** Esto cierra
la incógnita que la Fase 1 dejó como `NO_OBSERVABLE`.

## Runtime del modelo

- Ollama **0.32.5**
- `qwen3.6:27b-q4_K_M`, digest `a50eda8ed977ab48a12431878896b27ffd5cef552c17af3317d9623b939a7f1e`
- familia `qwen35`, **27,8 B**, Q4_K_M, gguf, 16,93 GB, **100 % en VRAM**
- **Plantilla del modelo: `{{ .Prompt }}`** — paso directo. Ollama NO aplica chat
  template; el prompt lo construye entero el backend. Los `parameters` del
  Modelfile (temp 1, top_p 0.95) **quedan sobreescritos** por los que envía la
  petición (temp 0.3, top_p 0.8)
- `llama-server`: `-c 16384 -np 1 --cache-type-k q8_0 --cache-type-v q8_0
  --flash-attn on -b 512 -ub 512 --context-shift --keep 4 --no-mmap
  --chat-template chatml`
- Env del servicio: `OLLAMA_CONTEXT_LENGTH=16384`, `OLLAMA_KEEP_ALIVE=30m`,
  `OLLAMA_MAX_LOADED_MODELS=1`; la petición envía `keep_alive: -1`, y `/api/ps`
  confirma `expires_at` en el año **2318**
