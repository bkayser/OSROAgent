#!/bin/sh
set -e
PORT="${PORT:-80}"
BACKEND_URL="${BACKEND_URL:-http://osro-agent-api:8080}"
sed -i "s|__PORT__|$PORT|g" /etc/nginx/conf.d/default.conf
sed -i "s|__BACKEND_URL__|$BACKEND_URL|g" /etc/nginx/conf.d/default.conf
exec nginx -g "daemon off;"
