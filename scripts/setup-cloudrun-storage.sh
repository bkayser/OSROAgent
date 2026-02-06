#!/usr/bin/env bash
set -e
# One-time setup: create GCS bucket for vector store and grant Cloud Run API access.
# Run from project root. Requires: gcloud CLI.

PROJECT="${GCP_PROJECT:-oregon-referees}"
REGION="${GCP_REGION:-us-west1}"
BUCKET="${VECTOR_STORE_BUCKET:-${PROJECT}-osro-vector-store}"

echo "Project: ${PROJECT}  Region: ${REGION}  Bucket: gs://${BUCKET}"

# Create bucket if it does not exist
if ! gcloud storage buckets describe "gs://${BUCKET}" --project "${PROJECT}" &>/dev/null; then
  echo "Creating bucket gs://${BUCKET}..."
  gcloud storage buckets create "gs://${BUCKET}" \
    --project "${PROJECT}" \
    --location "${REGION}"
else
  echo "Bucket gs://${BUCKET} already exists."
fi

# Grant the default Cloud Run service identity Storage Object Viewer
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT}" --format='value(projectNumber)')
SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
echo "Granting ${SA} Storage Object Viewer on gs://${BUCKET}..."
gsutil iam ch "serviceAccount:${SA}:objectViewer" "gs://${BUCKET}"

echo "Done. Run ./scripts/deploy-cloudrun.sh to deploy with the vector store mount."
