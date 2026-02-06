#!/bin/sh
set -e
BACKEND_URL="${BACKEND_URL:-http://osro-agent-api:8000}"
sed -i "s|__BACKEND_URL__|$BACKEND_URL|g" /etc/nginx/conf.d/default.conf
exec nginx -g "daemon off;"
