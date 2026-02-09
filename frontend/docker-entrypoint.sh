#!/bin/sh
set -e
PORT="${PORT:-80}"
BACKEND_URL="${BACKEND_URL:-http://osro-agent-api:8080}"
# On Cloud Run, BACKEND_URL must be set by deploy script. Empty => proxy to self => /api/chat returns index.html.
if [ -z "$BACKEND_URL" ]; then
  echo "Error: BACKEND_URL is empty. Set it to the API URL (e.g. https://osro-agent-api-xxx.run.app)."
  exit 1
fi
sed -i "s|__PORT__|$PORT|g" /etc/nginx/conf.d/default.conf
sed -i "s|__BACKEND_URL__|$BACKEND_URL|g" /etc/nginx/conf.d/default.conf
exec nginx -g "daemon off;"
