FROM ollama/ollama:0.32.6@sha256:b88c73ace3e115f8ec53dc8761ae1c0aabfa675406e3681786b98757ce050f42

ARG HEMOVET_BUILD_REVISION=dev
ARG HEMOVET_BUILD_CREATED=unknown
ARG HEMOVET_SOURCE_URL=https://github.com/xPshycho/hemogramas-proyectoICC

LABEL org.opencontainers.image.title="HemoVet Ollama runtime" \
      org.opencontainers.image.description="Pinned Ollama inference runtime for HemoVet" \
      org.opencontainers.image.source="${HEMOVET_SOURCE_URL}" \
      org.opencontainers.image.revision="${HEMOVET_BUILD_REVISION}" \
      org.opencontainers.image.created="${HEMOVET_BUILD_CREATED}" \
      org.opencontainers.image.version="0.32.6" \
      org.opencontainers.image.base.name="docker.io/ollama/ollama:0.32.6@sha256:b88c73ace3e115f8ec53dc8761ae1c0aabfa675406e3681786b98757ce050f42" \
      io.hemovet.ollama.version="0.32.6"
