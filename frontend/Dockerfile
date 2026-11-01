FROM node:22-alpine AS frontend-build
WORKDIR /app
COPY frontend/package.json ./package.json
# First registry-connected build generates a lockfile; see docs/reproducibility.md.
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM nginx:1.27-alpine
RUN apk add --no-cache gettext \
    && mkdir -p /var/cache/nginx /var/run \
    && chown -R nginx:nginx /var/cache/nginx /var/run /etc/nginx/conf.d
COPY --from=frontend-build /app/dist /usr/share/nginx/html
COPY ops/nginx.conf.template /etc/nginx/nginx.conf.template
COPY ops/start-nginx.sh /start-nginx.sh
RUN chmod +x /start-nginx.sh
USER nginx
EXPOSE 8080
ENTRYPOINT ["/start-nginx.sh"]
