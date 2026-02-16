#!/usr/bin/env bash
set -e
# Deploy OSRO Agent API and UI to Google Cloud Run (us-west1, project oregon-referees).
# Normally run via: task deploy. Run task build-push first. One-time: task setup-storage to create bucket and IAM.
# Requires: gcloud CLI. Set GOOGLE_API_KEY (Task loads .env from project root).

# Verify API key is set before deploying
if [ -z "${GOOGLE_API_KEY}" ]; then
  echo "Error: GOOGLE_API_KEY is not set. Either:"
  echo "  1. Set it in .env file in the project root"
  echo "  2. Export it: export GOOGLE_API_KEY=your-key"
  exit 1
fi

PROJECT="${GCP_PROJECT:-oregon-referees}"
REGION="${GCP_REGION:-us-west1}"
TAG="${TAG:-latest}"
BUCKET="${VECTOR_STORE_BUCKET:-${PROJECT}-osro-vector-store}"
IMAGE_API="gcr.io/${PROJECT}/osro-agent-api:${TAG}"
IMAGE_UI="gcr.io/${PROJECT}/osro-agent-ui:${TAG}"

# Ensure vector store bucket exists (create if not)
if ! gcloud storage buckets describe "gs://${BUCKET}" --project "${PROJECT}" &>/dev/null; then
  echo "Creating bucket gs://${BUCKET} (run task setup-storage to grant IAM)..."
  gcloud storage buckets create "gs://${BUCKET}" --project "${PROJECT}" --location "${REGION}"
fi

echo "Deploying API to Cloud Run (${REGION})..."
# Deploy without volume first to verify container starts (volume mount can block startup).
# To attach vector store bucket, run: gcloud run services update osro-agent-api --region ${REGION} --add-volume=... --add-volume-mount=...
# min-instances 1 keeps one container warm so first request is fast (no cold start), like Docker Desktop.
# max-instances 1 keeps in-memory rate limit consistent and avoids surprise scaling cost during beta.
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
  --min-instances 1 \
  --max-instances 1 \
  --timeout 60

API_URL=$(gcloud run services describe osro-agent-api --region "${REGION}" --project "${PROJECT}" --format 'value(status.url)')
echo "API URL: ${API_URL}"

if [ -z "${API_URL}" ]; then
  echo "Error: Could not get API URL (osro-agent-api in ${REGION}). Fix API deploy or region/project."
  exit 1
fi
if [[ "${API_URL}" != *"osro-agent-api"* ]]; then
  echo "Error: API URL does not contain 'osro-agent-api': ${API_URL}"
  exit 1
fi

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
echo "Vector store is mounted from gs://${BUCKET} at /app/vector_store. To update it only: task update-vector-store"
