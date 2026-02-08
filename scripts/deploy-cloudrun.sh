#!/usr/bin/env bash
set -e
# Deploy OSRO Agent API and UI to Google Cloud Run (us-west1, project oregon-referees).
# Run scripts/build-push.sh first. One-time: run scripts/setup-cloudrun-storage.sh to create bucket and IAM.
# Requires: gcloud CLI. Set GOOGLE_API_KEY (or use Secret Manager) for the API service.

PROJECT="${GCP_PROJECT:-oregon-referees}"
REGION="${GCP_REGION:-us-west1}"
TAG="${TAG:-latest}"
BUCKET="${VECTOR_STORE_BUCKET:-${PROJECT}-osro-vector-store}"
IMAGE_API="gcr.io/${PROJECT}/osro-agent-api:${TAG}"
IMAGE_UI="gcr.io/${PROJECT}/osro-agent-ui:${TAG}"

# Ensure vector store bucket exists (create if not)
if ! gcloud storage buckets describe "gs://${BUCKET}" --project "${PROJECT}" &>/dev/null; then
  echo "Creating bucket gs://${BUCKET} (run scripts/setup-cloudrun-storage.sh to grant IAM)..."
  gcloud storage buckets create "gs://${BUCKET}" --project "${PROJECT}" --location "${REGION}"
fi

echo "Deploying API to Cloud Run (${REGION})..."
# Deploy without volume first to verify container starts (volume mount can block startup).
# To attach vector store bucket, run: gcloud run services update osro-agent-api --region ${REGION} --add-volume=... --add-volume-mount=...
# min-instances 1 keeps one container warm so first request is fast (no cold start), like Docker Desktop.
gcloud run deploy osro-agent-api \
  --image "${IMAGE_API}" \
  --region "${REGION}" \
  --platform managed \
  --project "${PROJECT}" \
  --execution-environment gen2 \
  --ingress internal \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_API_KEY=${GOOGLE_API_KEY}" \
  --memory 1Gi \
  --min-instances 1

API_URL=$(gcloud run services describe osro-agent-api --region "${REGION}" --project "${PROJECT}" --format 'value(status.url)')
echo "API URL: ${API_URL}"

echo "Deploying UI to Cloud Run (${REGION}) with BACKEND_URL=${API_URL}..."
gcloud run deploy osro-agent-ui \
  --image "${IMAGE_UI}" \
  --region "${REGION}" \
  --platform managed \
  --project "${PROJECT}" \
  --allow-unauthenticated \
  --set-env-vars "BACKEND_URL=${API_URL}" \
  --memory 256Mi \
  --timeout 300

UI_URL=$(gcloud run services describe osro-agent-ui --region "${REGION}" --project "${PROJECT}" --format 'value(status.url)')
echo "Done. UI: ${UI_URL}  API: ${API_URL}"
echo "Vector store is mounted from gs://${BUCKET} at /app/vector_store. To update it only: ./scripts/update-vector-store.sh"
