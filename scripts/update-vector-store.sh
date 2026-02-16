#!/usr/bin/env bash
set -e
# Sync local ./vector_store to GCS only. Run from project root after task ingest.
# When you sync to the cloud you will update the UI and API server separately; this script does not deploy.
# Normally run via: task update-vector-store. Requires: gcloud CLI. Uses GCP_PROJECT and VECTOR_STORE_BUCKET.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

PROJECT="${GCP_PROJECT:-oregon-referees}"
BUCKET="${VECTOR_STORE_BUCKET:-${PROJECT}-osro-vector-store}"

cd "${ROOT_DIR}"

if [[ ! -d ./vector_store ]]; then
  echo "Error: ./vector_store not found. Run task ingest first."
  exit 1
fi

echo "Syncing ./vector_store to gs://${BUCKET}/..."
gcloud storage rsync ./vector_store "gs://${BUCKET}/" --delete-unmatched-destination-objects

echo "Done. Vector store synced to gs://${BUCKET}/. Update and deploy the API server separately to use it."
