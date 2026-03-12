#!/bin/bash
# PitWall Live — Build & Deploy Script
# Usage: ./deploy.sh <PROJECT_ID> [REGION]

set -euo pipefail

PROJECT_ID="${1:?Usage: ./deploy.sh <PROJECT_ID> [REGION]}"
REGION="${2:-us-central1}"
BACKEND_IMAGE="gcr.io/${PROJECT_ID}/pitwall-backend:latest"
WEB_IMAGE="gcr.io/${PROJECT_ID}/pitwall-web:latest"

echo "=== PitWall Live Deploy ==="
echo "Project: ${PROJECT_ID}"
echo "Region:  ${REGION}"
echo ""

# 1. Build and push backend image
echo ">>> Building backend image..."
cd backend
gcloud builds submit --tag "${BACKEND_IMAGE}" --project "${PROJECT_ID}"
cd ..

# 2. Build and push web image
echo ">>> Building web image..."
cd web
gcloud builds submit --tag "${WEB_IMAGE}" --project "${PROJECT_ID}"
cd ..

# 3. Terraform apply
echo ">>> Running terraform apply..."
cd infra
terraform init
terraform apply \
  -var="project_id=${PROJECT_ID}" \
  -var="region=${REGION}" \
  -var="backend_image=${BACKEND_IMAGE}" \
  -var="web_image=${WEB_IMAGE}" \
  -auto-approve
cd ..

echo ""
echo "=== Deployment Complete ==="
terraform -chdir=infra output
