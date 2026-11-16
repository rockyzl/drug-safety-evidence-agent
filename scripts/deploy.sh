#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${CLOUD_PROJECT:?Set CLOUD_PROJECT}"
DEPLOY_REGION="${DEPLOY_REGION:-us-central1}"
SERVICE="${SERVICE:-drug-safety-evidence-agent}"
REPOSITORY="${REPOSITORY:-evidence-desk}"
IMAGE="$DEPLOY_REGION-docker.pkg.dev/$CLOUD_PROJECT/$REPOSITORY/$SERVICE:$(date -u +%Y%m%d%H%M%S)"
test -f app/data/corpus.json
test -f reports/evaluation.json
test -f reports/saved-example.json
gcloud builds submit --project "$CLOUD_PROJECT" --tag "$IMAGE" --quiet
gcloud run deploy "$SERVICE" --project "$CLOUD_PROJECT" --region "$DEPLOY_REGION" \
  --image "$IMAGE" --service-account "evidence-desk@$CLOUD_PROJECT.iam.gserviceaccount.com" \
  --set-secrets OPENAI_API_KEY=evidence-desk-openai-key:latest \
  --set-env-vars EVIDENCE_PROVIDER=openai,EVIDENCE_MODEL=gpt-4.1-mini,DAILY_RUN_LIMIT=80 \
  --allow-unauthenticated --min-instances 0 --max-instances 1 --memory 1Gi --cpu 1 \
  --concurrency 8 --timeout 300 --port 8080 --quiet
