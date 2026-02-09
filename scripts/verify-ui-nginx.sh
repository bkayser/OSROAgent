#!/usr/bin/env bash
# Verify the UI image has the expected nginx config (regex location for /api/).
# Run from project root. Usage: ./scripts/verify-ui-nginx.sh [image]
# If no image given, uses gcr.io/oregon-referees/osro-agent-ui:latest (pull first).

set -e
IMAGE="${1:-gcr.io/oregon-referees/osro-agent-ui:latest}"
echo "Checking nginx config in image: ${IMAGE} (linux/amd64 = Cloud Run)"
echo "---"
docker run --rm --platform linux/amd64 --entrypoint cat "$IMAGE" /etc/nginx/conf.d/default.conf
echo "---"
echo "Look for: 'location ~ ^/api/' and 'X-Proxied-By'. If missing, image is old or build didn't include frontend/nginx.conf."
