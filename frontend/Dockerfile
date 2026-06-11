FROM node:22-alpine AS build

WORKDIR /app

ARG VITE_API_BASE_URL=""
ARG VITE_API_KEY=""
ARG VITE_SENTRY_DSN=""

ENV VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    VITE_API_KEY=${VITE_API_KEY} \
    VITE_SENTRY_DSN=${VITE_SENTRY_DSN}

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://127.0.0.1/health || exit 1
