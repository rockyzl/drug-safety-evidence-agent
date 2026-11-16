from copy import deepcopy
import pytest
from app.agent import check_citations, finalize_claims, EvidenceAgent, brief_searches, source_coverage, personal_request
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

@pytest.mark.parametrize('section',['regulatory','label','synthesis'])
def test_paper_cannot_substitute_for_regulator_or_label(section):
    evidence=[{**EVIDENCE[0],'source_type':'research'}]
    c={**CLAIM,'section':section}
    assert not finalize_claims({'claims':[c]},VERIFIED,evidence,'2026-11-15')[0]['included_in_brief']

def test_synthesis_requires_two_source_perspectives():
    evidence=[{**EVIDENCE[0],'source_type':'research'},
              {**EVIDENCE[0],'id':'fda1','source_type':'regulatory'}]
    c={**CLAIM,'section':'synthesis','citations':[CLAIM['citations'][0],{'passage_id':'fda1','quote':'fifty years or older'}]}
    assert finalize_claims({'claims':[c]},VERIFIED,evidence,'2026-11-15')[0]['included_in_brief']

def test_brief_policy_preserves_model_queries_and_fills_missing_categories():
    p={'in_scope':True,'searches':[{'query':'cardiovascular study cohorts','source_type':'research'}]}
    searches=brief_searches(p,'A safety briefing question')
    assert [x['source_type'] for x in searches]==['research','regulatory','label']
    assert searches[0]['query']=='cardiovascular study cohorts'
    assert searches[1]['query']=='A safety briefing question'
    assert brief_searches({**p,'in_scope':False},'question')==[]

def test_retrieved_source_does_not_imply_a_supported_section():
    coverage=source_coverage([{**EVIDENCE[0],'source_type':'regulatory'}],[])
    fda=next(row for row in coverage if row['source_type']=='regulatory')
    assert fda['retrieved_sources']==1 and fda['supported_claims']==0

@pytest.mark.parametrize('question',[
    'Estimate my personal risk of a stroke on this medication.',
    'Tell me whether to stop taking my treatment.',
    'Prepare a brief telling me exactly whether I should stop my Xeljanz treatment.',
    'What dose of tofacitinib should I take?',
    'Calculate my exact personal probability of a heart attack.'])
def test_personal_requests_are_stopped_before_model_or_retrieval(question):
    class Store:sources={}
    class NeverCall:
        provider='test';model='test';usage=[]
        def structured(self,*args):raise AssertionError('Must not call the model')
    result=EvidenceAgent(Store(),NeverCall()).run(question,'2026-11-15','safety_brief')['result']
    assert result['claims']==[] and result['trace'][0]['tool']=='scope_gate'

@pytest.mark.parametrize('question',[
    'What does FDA state about cardiovascular risk in patients?',
    'I want a comparison of the published study populations.',
    'Describe the dose groups studied in ORAL Surveillance.'])
def test_research_questions_are_not_blocked_by_personal_gate(question):
    assert not personal_request(question)
