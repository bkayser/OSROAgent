#!/usr/bin/env bash
set -e
# Build and push OSRO Agent images to gcr.io/oregon-referees.
# Requires: gcloud CLI, Docker, docker compose.
# Run from project root.

TAG="${TAG:-latest}"
PROJECT="${GCP_PROJECT:-oregon-referees}"
REGISTRY="gcr.io/${PROJECT}"

echo "Configuring Docker for GCR (project: ${PROJECT})..."
gcloud auth configure-docker gcr.io --quiet

echo "Building images for linux/amd64 (Cloud Run)..."
DOCKER_DEFAULT_PLATFORM=linux/amd64 docker compose build

echo "Tagging and pushing (tag: ${TAG})..."
docker tag "${REGISTRY}/osro-agent-api:latest" "${REGISTRY}/osro-agent-api:${TAG}"
docker tag "${REGISTRY}/osro-agent-ui:latest" "${REGISTRY}/osro-agent-ui:${TAG}"
docker push "${REGISTRY}/osro-agent-api:${TAG}"
docker push "${REGISTRY}/osro-agent-ui:${TAG}"

echo "Done. Images pushed: ${REGISTRY}/osro-agent-api:${TAG} ${REGISTRY}/osro-agent-ui:${TAG}"
