#!/bin/sh
set -eu
: "${APP_ENV:=development}"
: "${API_TOKEN:=}"
if [ "$APP_ENV" = production ]; then
  if [ "${#API_TOKEN}" -lt 32 ]; then echo 'Production requires API_TOKEN >=32 chars' >&2; exit 1; fi
fi
# Tokens must not introduce Nginx directives during envsubst.
case "$API_TOKEN" in *[!a-zA-Z0-9_-]*) echo 'API_TOKEN must contain only letters, digits, underscore or hyphen' >&2; exit 1 ;; esac
envsubst '${API_TOKEN}' </etc/nginx/nginx.conf.template >/etc/nginx/conf.d/default.conf
exec nginx -c /etc/nginx/conf.d/default.conf -g 'daemon off;'
