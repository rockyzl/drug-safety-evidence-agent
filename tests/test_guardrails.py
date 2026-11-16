from copy import deepcopy
import pytest
from app.agent import check_citations, finalize_claims, EvidenceAgent
from app.models import Plan, Draft

EVIDENCE=[{'id':'p1','source_id':'s1','text':'Patients were fifty years or older with a cardiovascular risk factor.','published':'2022-01-27','section':'Methods'}]
CLAIM={'text':'The trial enrolled older patients with a cardiovascular risk factor.','citations':[{'passage_id':'p1','quote':'fifty years or older'}]}
VERIFIED={'judgments':[{'claim_index':0,'verdict':'supported','reason':'Population matches.'}]}

@pytest.mark.parametrize('kind',['fabricated_id','wrong_quote','empty_quote','missing_citation','future_date'])
def test_invalid_references_cannot_be_published_even_if_model_agrees(kind):
    c=deepcopy(CLAIM);cutoff='2026-11-15'
    if kind=='fabricated_id':c['citations'][0]['passage_id']='invented'
    if kind=='wrong_quote':c['citations'][0]['quote']='children aged ten'
    if kind=='empty_quote':c['citations'][0]['quote']=' '
    if kind=='missing_citation':c['citations']=[]
    if kind=='future_date':cutoff='2021-12-31'
    assert not finalize_claims({'claims':[c]},VERIFIED,EVIDENCE,cutoff)[0]['included_in_brief']

@pytest.mark.parametrize('verification',[{}, {'judgments':[]}, {'judgments':VERIFIED['judgments']*2}, {'judgments':[{'claim_index':0,'verdict':'partial','reason':'Too broad'}]}, {'judgments':[{'claim_index':0,'verdict':'unsupported','reason':'Wrong population'}]}])
def test_uncertain_verification_fails_closed(verification):
    assert not finalize_claims({'claims':[CLAIM]},verification,EVIDENCE,'2026-11-15')[0]['included_in_brief']

def test_supported_citation_is_retained():
    assert finalize_claims({'claims':[CLAIM]},VERIFIED,EVIDENCE,'2026-11-15')[0]['included_in_brief']

def test_verifier_outage_does_not_publish_draft():
    class FailingModel:
        def structured(self,*args):raise TimeoutError()
    agent=EvidenceAgent.__new__(EvidenceAgent);agent.model=FailingModel();agent.emit=lambda e:None
    s={'question':'Study population?','draft':{'claims':[CLAIM]},'evidence':EVIDENCE,'trace':[]}
    v=agent.verify(s)['verification']
    assert v['error']
    assert not finalize_claims(s['draft'],v,EVIDENCE,'2026-11-15')[0]['included_in_brief']

def test_out_of_scope_graph_does_not_call_retrieval():
    class Store:
        sources={}
        def search(self,*args):raise AssertionError('Must not search')
    class Model:
        provider='test';model='test';usage=[]
        def structured(self,*args):return Plan(in_scope=False,reason='Personal advice is outside scope.',searches=[])
    r=EvidenceAgent(Store(),Model()).run('Should I change my medication?','2026-11-15')['result']
    assert r['claims']==[] and r['status']=='insufficient_evidence'

def test_public_quote_budget():
    class Store:sources={'s1':{'id':'s1'}}
    class Model:provider='test';model='test';usage=[]
    c=deepcopy(CLAIM);c['citations'][0]['quote']=EVIDENCE[0]['text']
    s={'question':'Population?','as_of':'2026-11-15','evidence':EVIDENCE,'draft':{'claims':[c]*3,'limitations':[]},'verification':{'judgments':[{'claim_index':i,'verdict':'supported','reason':'Matches'} for i in range(3)]},'trace':[],'plan':{'reason':''}}
    r=EvidenceAgent(Store(),Model()).finalize(s)['result']
    assert sum(len(ref['quote'].split()) for claim in r['claims'] for ref in claim['citations'])<=20
