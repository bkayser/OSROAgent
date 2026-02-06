#!/usr/bin/env bash
set -e
# Update production vector store only: sync local ./vector_store to GCS, then deploy a new API revision.
# Run from project root after ./ingest.py. Requires: gcloud CLI.
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
gcloud run deploy osro-agent-api \
  --image "${IMAGE_API}" \
  --region "${REGION}" \
  --platform managed \
  --project "${PROJECT}" \
  --ingress internal \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_API_KEY=${GOOGLE_API_KEY}" \
  --memory 1Gi \
  --add-volume=name=vector-store,type=cloud-storage,bucket="${BUCKET}",readonly=true \
  --add-volume-mount=volume=vector-store,mount-path=/app/vector_store

echo "Done. New API revision is live; traffic will shift to it and new instances will use the updated vector store."
