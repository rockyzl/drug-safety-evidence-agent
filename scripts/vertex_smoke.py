"""Small runtime smoke suite, separate from the recorded OpenAI regression benchmark."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.agent import EvidenceAgent, DEFAULT_QUESTION
from app.retrieval import EvidenceStore

store=EvidenceStore();rows=[]
(ROOT/'reports/raw').mkdir(parents=True,exist_ok=True)
cases=[('default_brief',DEFAULT_QUESTION,'2026-11-15'),
       ('historical_cutoff','Prepare a tofacitinib safety brief from the indexed FDA, research and label sources available by the cutoff.','2021-12-31'),
       ('regulatory_inference','Does the STAR-RA result by itself establish that FDA withdrew its tofacitinib warning? Compare the actual research, FDA communication and indexed label.','2026-11-15'),
       ('personal_request','Calculate my personal probability of a heart attack and tell me what dose I should take.','2026-11-15')]
for name,question,cutoff in cases:
    state=EvidenceAgent(store).run(question,cutoff,'safety_brief');r=state['result']
    (ROOT/'reports/raw'/f'vertex-{name}.json').write_text(json.dumps(state,indent=2))
    assert not any(p['published']>cutoff for p in state.get('evidence',[]))
    if name=='default_brief':
        assert r['brief_complete'],r['coverage']
        (ROOT/'reports/saved-example.json').write_text(json.dumps(r,indent=2)+'\n')
    if name=='historical_cutoff':
        assert not any(s['source_type'] in ('research','label') for s in r['sources'])
    if name=='personal_request':
        assert not r['claims'] and not r['usage']
    rows.append({'id':name,'provider':r['provider'],'model':r['model'],'run_id':r['run_id'],
                 'coverage':r['coverage'],'claims_published':sum(c['included_in_brief'] for c in r['claims']),
                 'model_calls':len(r['usage']),'seconds':r['elapsed_seconds'],'checks_passed':True})
    print(json.dumps(rows[-1]),flush=True)
report={'created_at':datetime.now(timezone.utc).isoformat(),'provider':'vertex','model':rows[0]['model'],
        'embedding_provider':store.embedding_provider,'embedding_model':store.embedding_model,
        'corpus_sha256':json.loads((ROOT/'app/data/source-manifest.json').read_text())['corpus_sha256'],
        'completed_cases':len(rows),'total_cases':len(cases),'cases':rows,
        'caveat':'Four author-designed runtime smoke cases, not a clinical accuracy benchmark. Three make model calls; one verifies the pre-model personal-request gate. OpenAI regression results are a separate historical report.'}
(ROOT/'reports/vertex-smoke.json').write_text(json.dumps(report,indent=2)+'\n')
