#!/usr/bin/env bash
set -e
# Update production vector store only: sync local ./vector_store to GCS, then deploy a new API revision.
# Run from project root after ./ingest.py. Requires: gcloud CLI.
# If you changed the Dockerfile or backend code, run ./scripts/build-push.sh first.
# Uses same env vars as deploy-cloudrun.sh (GCP_PROJECT, GCP_REGION, VECTOR_STORE_BUCKET, TAG).

PROJECT="${GCP_PROJECT:-oregon-referees}"
REGION="${GCP_REGION:-us-west1}"
TAG="${TAG:-latest}"
BUCKET="${VECTOR_STORE_BUCKET:-${PROJECT}-osro-vector-store}"
IMAGE_API="gcr.io/${PROJECT}/osro-agent-api:${TAG}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

if [[ ! -d ./vector_store ]]; then
  echo "Error: ./vector_store not found. Run ./ingest.py first."
  exit 1
fi

echo "Syncing ./vector_store to gs://${BUCKET}/..."
gcloud storage rsync ./vector_store "gs://${BUCKET}/" --delete-unmatched-destination-objects

echo "Deploying new API revision (same image) so new instances load the updated index..."
# Use same options as deploy-cloudrun.sh so ingress/env/min-instances are not reverted (ingress all required for UI→API).
# Note: volume mount omitted here; if you use a volume, add --add-volume and --add-volume-mount
gcloud run deploy osro-agent-api \
  --image "${IMAGE_API}" \
  --region "${REGION}" \
  --platform managed \
  --project "${PROJECT}" \
  --execution-environment gen2 \
  --ingress all \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_API_KEY=${GOOGLE_API_KEY}" \
  --memory 1Gi \
  --min-instances 1

echo "Done. New API revision is live; traffic will shift to it and new instances will use the updated vector store."
