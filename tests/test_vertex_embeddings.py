"""The remote embedding contract must preserve passage order and retrieval task type."""
import httpx
import pytest
from app import cloud_auth
from app.retrieval import EvidenceStore


@pytest.mark.parametrize('task', ['RETRIEVAL_DOCUMENT', 'RETRIEVAL_QUERY'])
def test_vertex_embedding_batches_preserve_input_order_and_task(monkeypatch, task):
    calls = []

    class Response:
        def __init__(self, instances):
            self.instances = instances
        def raise_for_status(self):
            pass
        def json(self):
            return {'predictions': [{'embeddings': {'values': [int(r['content'])]}}
                                    for r in self.instances]}

    class Client:
        def __init__(self, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def post(self, url, headers, json):
            calls.append((url, headers, json))
            return Response(json['instances'])

    monkeypatch.setattr(cloud_auth, 'access_token', lambda: 'test-token')
    monkeypatch.setattr(cloud_auth, 'project_id', lambda: 'test-project')
    monkeypatch.setattr(httpx, 'Client', Client)
    monkeypatch.setenv('VERTEX_EMBEDDING_LOCATION', 'us-central1')
    store = EvidenceStore.__new__(EvidenceStore)
    store.embedding_provider = 'vertex'
    store.embedding_model = 'text-embedding-005'
    assert store.embeddings([str(i) for i in range(7)], task=task) == [[i] for i in range(7)]
    assert [len(c[2]['instances']) for c in calls] == [5, 2]
    assert all(c[0].endswith('/publishers/google/models/text-embedding-005:predict') for c in calls)
    assert all(c[1]['Authorization'] == 'Bearer test-token' for c in calls)
    assert all(r['task_type'] == task for c in calls for r in c[2]['instances'])
