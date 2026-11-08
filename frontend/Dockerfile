FROM node:22-alpine AS frontend-build
WORKDIR /app
ARG NPM_REGISTRY_URL=https://package-mirror.liara.ir/repository/npm/
COPY frontend/package.json ./package.json
# npm has its own registry; never use the Python/PyPI mirror URL here.
# First registry-connected build generates a lockfile; see docs/reproducibility.md.
RUN npm install --registry="$NPM_REGISTRY_URL" \
    --fetch-retries=4 --fetch-retry-mintimeout=15000 \
    --fetch-retry-maxtimeout=120000 --fetch-timeout=180000 \
    --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM nginx:1.27-alpine
# Install gettext from Liara's Alpine mirror, not Alpine's default upstream.
RUN set -eu; \
    ALPINE_VERSION="$(cut -d. -f1-2 /etc/alpine-release)"; \
    printf 'https://linux-mirror.liara.ir/repository/alpine/v%s/main\nhttps://linux-mirror.liara.ir/repository/alpine/v%s/community\n' \
      "$ALPINE_VERSION" "$ALPINE_VERSION" > /etc/apk/repositories; \
    apk add --no-cache gettext; \
    mkdir -p /var/cache/nginx /var/run; \
    chown -R nginx:nginx /var/cache/nginx /var/run /etc/nginx/conf.d
COPY --from=frontend-build /app/dist /usr/share/nginx/html
COPY ops/nginx.conf.template /etc/nginx/nginx.conf.template
COPY ops/start-nginx.sh /start-nginx.sh
RUN chmod +x /start-nginx.sh
USER nginx
EXPOSE 8080
ENTRYPOINT ["/start-nginx.sh"]
