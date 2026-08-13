FROM node:22-alpine@sha256:c610fcdfb1d5b4740dd70c284ed3cb16bb857e0f7166196e36a5501df7a3aa32 AS build

WORKDIR /app
COPY frontend_4/package.json frontend_4/package-lock.json* ./
RUN npm ci
COPY frontend_4/ ./
COPY shared/ /shared/

ARG VITE_API_BASE_URL=/api/v1
ARG VITE_CHAT_MESSAGE_MAX_CHARS=2000
ARG VITE_MAP_TILE_URL=https://tile.openstreetmap.org/{z}/{x}/{y}.png
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_CHAT_MESSAGE_MAX_CHARS=${VITE_CHAT_MESSAGE_MAX_CHARS}
ENV VITE_MAP_TILE_URL=${VITE_MAP_TILE_URL}
RUN npm run build

FROM nginx:alpine@sha256:4a73073bd557c65b759505da037898b61f1be6cbcc3c2c3aeac22d2a470c1752

ARG HEMOVET_BUILD_REVISION=dev
ARG HEMOVET_BUILD_CREATED=unknown
ARG HEMOVET_SOURCE_URL=https://github.com/xPshycho/hemogramas-proyectoICC

LABEL org.opencontainers.image.title="HemoVet frontend" \
      org.opencontainers.image.description="React static application for HemoVet" \
      org.opencontainers.image.source="${HEMOVET_SOURCE_URL}" \
      org.opencontainers.image.revision="${HEMOVET_BUILD_REVISION}" \
      org.opencontainers.image.created="${HEMOVET_BUILD_CREATED}"

COPY --from=build /app/dist /usr/share/nginx/html
COPY frontend_4/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
