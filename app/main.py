"""Small public portfolio server. Keys and full source text never leave the server."""
import asyncio
import json
import os
import queue
import threading
import time
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from .agent import EvidenceAgent, DEFAULT_QUESTION, PIPELINE_VERSION
from .models import Ask
from .retrieval import EvidenceStore

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT/'app/static'
EXAMPLES = json.loads((ROOT/'app/data/examples.json').read_text())
slots = threading.BoundedSemaphore(2)
rate_lock = threading.Lock()
requests_seen = deque()
store = None


@asynccontextmanager
async def lifespan(app):
    global store
    store = EvidenceStore()
    if store.collection.count() != len(store.passages):
        raise RuntimeError('Index does not match the prepared corpus. Re-index before serving.')
    yield


app = FastAPI(title='Evidence Desk', docs_url=None, redoc_url=None, lifespan=lifespan)
app.mount('/static', StaticFiles(directory=STATIC), name='static')


@app.middleware('http')
async def headers(request: Request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self'; font-src 'self'; img-src 'self' data:; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"
    response.headers['Cache-Control'] = 'no-store' if request.url.path.startswith('/api') else 'no-cache'
    return response


@app.get('/')
def home():
    return FileResponse(STATIC/'index.html')


@app.get('/healthz')
@app.get('/api/health')
def health():
    return {'status': 'ok', 'sources': len(store.sources), 'passages': len(store.passages)}


@app.get('/api/config')
def config():
    return {'pipeline_version':PIPELINE_VERSION, 'default_question':DEFAULT_QUESTION,
            'retrieval_mode':'preloaded_index','snapshot_loaded_at':store.corpus['retrieved_at'],
            'provider': os.getenv('EVIDENCE_PROVIDER', 'openai'),
            'model': os.getenv('BEDROCK_MODEL_ID', '') if os.getenv('EVIDENCE_PROVIDER') == 'bedrock' else os.getenv('EVIDENCE_MODEL', 'google/gemini-3.8-flash' if os.getenv('EVIDENCE_PROVIDER')=='vertex' else 'gpt-4.1-mini'),
            'embedding_provider':store.embedding_provider,'embedding_model':store.embedding_model,
            'sources': list(store.sources.values()), 'passage_count': len(store.passages),
            'bedrock_status': 'Adapter available; not live-verified in this deployment.'}


@app.get('/api/example')
def example():
    path = ROOT/'reports/saved-example.json'
    if not path.exists():
        raise HTTPException(404, 'Saved example is not available yet. Run the agent instead.')
    return json.loads(path.read_text())


@app.get('/api/examples')
def examples():
    return EXAMPLES


@app.get('/api/examples/{example_id}')
def saved_example(example_id: str):
    # Only catalogued IDs may select a public result file.
    if example_id not in {item['id'] for item in EXAMPLES}:
        raise HTTPException(404, 'Unknown example.')
    path = ROOT/'reports/examples'/f'{example_id}.json'
    if not path.exists():
        raise HTTPException(404, 'This recorded example is not available yet.')
    return json.loads(path.read_text())


@app.get('/api/evaluation')
def evaluation():
    path = ROOT/'reports/evaluation.json'
    if not path.exists():
        return {'status':'Not yet evaluated.'}
    report=json.loads(path.read_text())
    report['scope_note']='Regression report for '+report['provider']+' / '+report['model']+'. Results do not automatically transfer to a different model.'
    smoke=ROOT/'reports/vertex-smoke.json'
    if smoke.exists():
        report['runtime_smoke']=json.loads(smoke.read_text())
    return report


@app.post('/api/ask')
async def ask(body: Ask, request: Request):
    if not slots.acquire(blocking=False):
        raise HTTPException(429, 'Two research runs are already active. Please try again shortly.')
    # Global in-process quotas bound anonymous use, including forged client addresses.
    # These counters reset on restart; they are not a billing guarantee.
    with rate_lock:
        now = time.monotonic()
        while requests_seen and requests_seen[0] < now-86400:
            requests_seen.popleft()
        if len(requests_seen) >= int(os.getenv('DAILY_RUN_LIMIT', '80')) or sum(t>now-3600 for t in requests_seen) >= 20:
            slots.release()
            raise HTTPException(429, 'This public demo has reached its research-run limit. Try the saved example.')
        requests_seen.append(now)
    events = queue.Queue()

    def work():
        try:
            state = EvidenceAgent(store, emit=events.put).run(body.question, body.as_of.isoformat(), body.mode)
            events.put({'type': 'result', 'result': state['result']})
        except Exception as error:
            # Never leak provider responses, request headers, credentials, or raw documents.
            message = 'The model provider cannot accept this run because of its quota. Please use the saved example.' if type(error).__name__ == 'RateLimitError' else 'The live run could not finish. Please retry or inspect the saved example. No new brief is available.'
            events.put({'type': 'error', 'message': message})
        finally:
            events.put(None)
            slots.release()

    threading.Thread(target=work, daemon=True).start()

    async def stream():
        while True:
            if await request.is_disconnected():
                return
            try:
                item = events.get_nowait()
            except queue.Empty:
                yield ': keepalive\n\n'
                await asyncio.sleep(0.4)
                continue
            if item is None:
                return
            yield 'data: '+json.dumps(item)+'\n\n'

    return StreamingResponse(stream(), media_type='text/event-stream', headers={'X-Accel-Buffering': 'no'})
