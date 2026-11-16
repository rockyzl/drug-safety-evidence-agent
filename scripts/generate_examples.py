"""Prepare public example results from actual runs; never author an answer by hand."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.agent import EvidenceAgent, PIPELINE_VERSION
from app.providers import Model
from app.retrieval import EvidenceStore

store = EvidenceStore()
model = Model()
catalog = json.loads((ROOT/'app/data/examples.json').read_text())
output = ROOT/'reports/examples'
output.mkdir(exist_ok=True)
(ROOT/'reports/raw').mkdir(exist_ok=True)
candidates = []
for path in [ROOT/'reports/saved-example.json', *output.glob('*.json'), *sorted((ROOT/'reports/raw').glob('vertex-*.json'))]:
    record = json.loads(path.read_text())
    candidates.append(record.get('result', record))

rows = []
for item in catalog:
    def matches(r):
        return (r.get('question') == item['question'] and r.get('as_of') == item['as_of']
                and r.get('provider') == model.provider and r.get('model') == model.model
                and r.get('pipeline_version') == PIPELINE_VERSION
                and r.get('mode') == 'safety_brief'
                and all(s == store.sources.get(s['id']) for s in r.get('sources', []))
                and (any(c['included_in_brief'] for c in r.get('claims', [])) or item['id'] == 'no-evidence'))

    result = next((r for r in candidates if matches(r)), None)
    reused = result is not None
    if result is None:
        state = EvidenceAgent(store).run(item['question'], item['as_of'], 'safety_brief')
        (ROOT/'reports/raw'/f"example-{item['id']}.json").write_text(json.dumps(state, indent=2)+'\n')
        result = state['result']
    assert result['usage'], 'A recorded example must come from a real model invocation.'
    assert not any(s['published'] > item['as_of'] for s in result['sources'])
    if item['id'] == 'no-evidence':
        assert not result['sources'] and not result['claims']
    else:
        assert any(c['included_in_brief'] for c in result['claims']), item['id']
    if item['id'] == 'history-2021':
        assert all(s['source_type'] == 'regulatory' for s in result['sources'])
    if item['id'] == 'label-review':
        assert any(c['section'] == 'label' and c['included_in_brief'] for c in result['claims'])
    (output/f"{item['id']}.json").write_text(json.dumps(result, indent=2)+'\n')
    row = {'id':item['id'], 'run_id':result['run_id'], 'recorded_at':result['created_at'],
           'provider':result['provider'], 'model':result['model'], 'reused_recorded_run':reused,
           'model_calls':len(result['usage']), 'published_claims':sum(c['included_in_brief'] for c in result['claims']),
           'source_count':len(result['sources']), 'as_of':item['as_of']}
    rows.append(row)
    print(json.dumps(row), flush=True)

report = {'created_at':datetime.now(timezone.utc).isoformat(), 'examples':rows,
          'corpus_sha256':json.loads((ROOT/'app/data/source-manifest.json').read_text())['corpus_sha256'],
          'note':'Six recorded real model runs for exploration, not six independent accuracy tests. Existing matching Vertex runs are reused with their original IDs and timestamps.'}
(ROOT/'reports/examples-manifest.json').write_text(json.dumps(report, indent=2)+'\n')
