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
test -f reports/vertex-smoke.json
python - <<'PY'
import json
from pathlib import Path
for item in json.loads(Path('app/data/examples.json').read_text()):
    result = json.loads((Path('reports/examples') / (item['id'] + '.json')).read_text())
    assert result['question'] == item['question'] and result['as_of'] == item['as_of'], item['id']
PY
gcloud builds submit --project "$CLOUD_PROJECT" --tag "$IMAGE" --quiet
gcloud run deploy "$SERVICE" --project "$CLOUD_PROJECT" --region "$DEPLOY_REGION" \
  --image "$IMAGE" --service-account "evidence-desk@$CLOUD_PROJECT.iam.gserviceaccount.com" \
  --remove-secrets OPENAI_API_KEY \
  --set-env-vars "EVIDENCE_PROVIDER=vertex,EVIDENCE_MODEL=google/gemini-3.8-flash,EMBEDDING_PROVIDER=vertex,EMBEDDING_MODEL=text-embedding-005,GOOGLE_CLOUD_PROJECT=$CLOUD_PROJECT,GOOGLE_CLOUD_LOCATION=global,DAILY_RUN_LIMIT=80" \
  --allow-unauthenticated --min-instances 0 --max-instances 1 --memory 1Gi --cpu 1 \
  --concurrency 8 --timeout 300 --port 8080 --quiet
