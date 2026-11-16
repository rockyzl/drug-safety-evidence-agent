"""Request/response contract only. This is deliberately not a live AWS test."""
from app.providers import Model
from app.models import Plan

def test_bedrock_converse_request_contract():
    class Client:
        def converse(self,**kwargs):
            assert kwargs['modelId']=='test-profile'
            assert kwargs['messages'][0]['role']=='user'
            assert kwargs['inferenceConfig']['temperature']==0
            assert 'system' in kwargs
            return {'output':{'message':{'content':[{'text':'{"in_scope":false,"reason":"No evidence","searches":[]}'}]}},'usage':{'inputTokens':10,'outputTokens':8}}
    m=Model.__new__(Model);m.provider='bedrock';m.model='test-profile';m.client=Client();m.usage=[]
    assert m.structured('Research only',{'question':'Test question'},Plan).in_scope is False
    assert m.usage[0]['input_tokens']==10
