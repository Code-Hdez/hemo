# Cómo correr las baterías de validación en la VM

Runbook operativo para ejecutar las baterías del asistente LLM/RAG contra el stack
real desplegado en la VM `hemovet-prod` (Google Cloud). La metodología está en
`README.md`; este documento es solo el paso a paso de ejecución.

## Contexto importante

Los scripts corren **dentro del contenedor `hemogramas-proyectoicc-backend-1`**, no
en el host ni en tu laptop, porque ahí están las dependencias de Python y el acceso
de red a Chroma, Ollama y Postgres (sus puertos son internos a la red de Docker).

La imagen del backend **no incluye** `validacion_llm/` (el Dockerfile solo copia
`backend/`, `data/`, `models/`, etc.). Por eso, aunque el merge a `main` ya dejó la
carpeta en el host de la VM (`/home/ubuntu/hemogramas-proyectoICC/validacion_llm`),
hay que copiarla al contenedor con `docker cp` antes de correr.

> Opcional: para que quede dentro de la imagen en futuros deploys y evitar el
> `docker cp`, añadir `COPY validacion_llm ./validacion_llm` al Dockerfile del backend.

## Requisitos

- Stack activo en la VM (los 6 contenedores `healthy`).
- Cambios de `validacion_llm/` mergeados a `main` y presentes en el host de la VM.

## 1. Entrar a la VM

```bash
gcloud compute ssh ubuntu@hemovet-prod --zone=us-central1-a --ssh-key-file=~/.ssh/hemovet_oracle
```

## 2. Meter la carpeta al contenedor

```bash
cd ~/hemogramas-proyectoICC
git pull
sudo docker cp validacion_llm hemogramas-proyectoicc-backend-1:/app/validacion_llm
```

## 3. Correr las baterías

La batería A+B tarda ~30-45 min en CPU (~16.7 tok/s); lánzala dentro de `tmux` para
que sobreviva a un corte de SSH:

```bash
tmux new -s bateria
```

Dentro de `tmux`:

```bash
# Baterías A (ámbito/seguridad) + B (robustez ortográfica)
sudo docker exec -w /app/backend hemogramas-proyectoicc-backend-1 \
     python3 ../validacion_llm/scripts/correr_eval_pipeline_real.py

# Batería D (consistencia)
sudo docker exec -w /app/backend hemogramas-proyectoicc-backend-1 \
     python3 ../validacion_llm/scripts/correr_consistencia.py

# Batería C (memoria multi-turno)
sudo docker exec -w /app/backend hemogramas-proyectoicc-backend-1 \
     python3 ../validacion_llm/scripts/correr_memoria_multiturno.py

# Batería E (exactitud de contenido → genera la rúbrica de veterinarios)
sudo docker exec -w /app/backend hemogramas-proyectoicc-backend-1 \
     python3 ../validacion_llm/scripts/correr_exactitud_contenido.py
```

Salir de `tmux` sin cortar: `Ctrl+B`, luego `D`. Volver: `tmux attach -t bateria`.

Los casos de C y E que dependen de un hemograma cargado se **omiten** si no pasas
`--user-id UID --analysis-id AID`. Para incluirlos, con un análisis real de la base:

```bash
sudo docker exec -w /app/backend hemogramas-proyectoicc-backend-1 \
     python3 ../validacion_llm/scripts/correr_exactitud_contenido.py \
     --user-id UID --analysis-id AID
```

## 4. Sacar los resultados

Dentro de la VM, del contenedor al host:

```bash
sudo docker cp hemogramas-proyectoicc-backend-1:/app/validacion_llm/resultados /tmp/resultados
sudo docker cp hemogramas-proyectoicc-backend-1:/app/validacion_llm/rubrica_veterinarios /tmp/rubrica_veterinarios
exit
```

Desde tu laptop, del host a tu repo local:

```bash
gcloud compute scp --recurse --zone=us-central1-a --ssh-key-file=~/.ssh/hemovet_oracle \
  ubuntu@hemovet-prod:/tmp/resultados \
  ~/tesis/hemogramas-proyectoICC/validacion_llm/resultados

gcloud compute scp --recurse --zone=us-central1-a --ssh-key-file=~/.ssh/hemovet_oracle \
  ubuntu@hemovet-prod:/tmp/rubrica_veterinarios \
  ~/tesis/hemogramas-proyectoICC/validacion_llm/rubrica_veterinarios
```

## 5. Después de correr

- Baterías A-D: revisar `validacion_llm/resultados/*.csv` y `outputs/eval_llm_pipeline_real.json`.
- Batería E: enviar `rubrica_veterinarios/rubrica_contenido_llm.csv` (ya pre-rellenada
  con preguntas, respuestas y fuentes) a los dos veterinarios; cada uno la devuelve
  como `rubrica_contenido_llm_medico1.csv` / `_medico2.csv`.
- Con las rúbricas completas, calcular las tasas y redactar el capítulo de resultados.

## Salidas esperadas

| Archivo | Batería |
|---|---|
| `outputs/eval_llm_pipeline_real.json`, `resultados/eval_ambito_seguridad.csv` | A |
| `resultados/eval_robustez_ortografica.csv` | B |
| `resultados/eval_memoria_multiturno.csv` | C |
| `resultados/eval_consistencia.csv`, `resultados/resumen_consistencia.csv` | D |
| `resultados/exactitud_contenido_crudo.csv`, `rubrica_veterinarios/rubrica_contenido_llm.csv` | E |
