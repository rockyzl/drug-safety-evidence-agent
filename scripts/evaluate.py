"""Frozen case set. Structural/process checks, not a clinical accuracy benchmark."""
import concurrent.futures
import hashlib
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.agent import EvidenceAgent, check_citations
from app.retrieval import EvidenceStore


def main():
    cases_path=ROOT/'eval/cases.json'
    cases=json.loads(cases_path.read_text())
    raw=ROOT/'reports/raw/evaluation';raw.mkdir(parents=True,exist_ok=True)
    store=EvidenceStore()

    def run(case):
        path=raw/(case['id']+'.json')
        try:
            if path.exists():
                state=json.loads(path.read_text())
            else:
                state=EvidenceAgent(store).run(case['question'],case['as_of'])
                path.write_text(json.dumps(state,indent=2))
            r=state['result'];accepted=[c for c in r['claims'] if c['included_in_brief']]
            raw_claims=state.get('draft',{}).get('claims',[])
            mechanical=[not check_citations(c,state.get('evidence',[]),case['as_of']) for c in raw_claims]
            published_indexes=[c['claim_index'] for c in accepted]
            retrieved_ids={p['source_id'] for p in state.get('evidence',[])}
            metrics={'id':case['id'],'split':case['split'],'category':case['category'],'completed':True,
                'drafted':len(raw_claims),'baseline_mechanical_passes':sum(mechanical),
                'published':len(accepted),'citation_checks_passed':sum(mechanical[i] for i in published_indexes),
                'future_sources':sum(p['published']>case['as_of'] for p in state.get('evidence',[])),
                'expected_source_retrieval':all(x in retrieved_ids for x in case.get('sources',[])) if case.get('sources') else None,
                'expected_abstention_met':not accepted if case.get('abstain') else None,
                'seconds':r['elapsed_seconds']}
            if case['id']=='dev-01':
                (ROOT/'reports/saved-example.json').write_text(json.dumps(r,indent=2)+'\n')
            print(json.dumps(metrics),flush=True)
            return metrics
        except Exception as e:
            row={'id':case['id'],'split':case['split'],'category':case['category'],'completed':False,'error_type':type(e).__name__}
            print(json.dumps(row),flush=True)
            return row

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        rows=list(pool.map(run,cases))
    done=[r for r in rows if r['completed']]
    outside=[r for r in done if r['category']=='out_of_scope']
    report={'created_at':datetime.now(timezone.utc).isoformat(),'provider':'openai','model':'gpt-4.1-mini',
        'case_file_sha256':hashlib.sha256(cases_path.read_bytes()).hexdigest(),
        'corpus_sha256':json.loads((ROOT/'app/data/source-manifest.json').read_text())['corpus_sha256'],
        'total_cases':len(cases),'completed_cases':len(done),'development_cases':6,'held_out_cases':24,
        'published_claims':sum(r['published'] for r in done),'citation_checks_passed':sum(r['citation_checks_passed'] for r in done),
        'drafted_claims':sum(r['drafted'] for r in done),'baseline_mechanical_passes':sum(r['baseline_mechanical_passes'] for r in done),
        'future_source_count':sum(r['future_sources'] for r in done),
        'out_of_scope_cases':sum(c['category']=='out_of_scope' for c in cases),
        'out_of_scope_abstentions':sum(r['expected_abstention_met'] for r in outside),
        'expected_source_retrieval_passes':sum(r['expected_source_retrieval'] is True for r in done),
        'expected_source_retrieval_cases':sum(bool(c.get('sources')) for c in cases),
        'median_seconds':round(statistics.median(r['seconds'] for r in done),2) if done else None,
        'caveat':'30 author-designed cases (6 development, 24 held out). These checks measure citation structure, date filtering and abstention, not clinical correctness. Source expectations were not independently clinician-annotated. The verifier uses the same model family as the drafter.',
        'cases':rows}
    (ROOT/'reports/evaluation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('REPORT',json.dumps({k:v for k,v in report.items() if k!='cases'}),flush=True)

if __name__=='__main__':main()
