import json
import os
import re
from pathlib import Path
import chromadb
from chromadb.config import Settings
from openai import OpenAI

DATA = Path(__file__).parent / "data"


class EvidenceStore:
    def __init__(self):
        self.corpus = json.loads((DATA/'corpus.json').read_text())
        self.passages = {p['id']: p for p in self.corpus['passages']}
        self.sources = {s['id']: s for s in self.corpus['sources']}
        self.client = chromadb.PersistentClient(path=str(DATA/'chroma'), settings=Settings(anonymized_telemetry=False))
        self.collection = self.client.get_or_create_collection('evidence-v1', metadata={"hnsw:space": "cosine"})
        self.embedding_model = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small')

    def embeddings(self, texts):
        response = OpenAI(timeout=40,max_retries=1).embeddings.create(model=self.embedding_model, input=texts)
        return [x.embedding for x in response.data]

    def index(self):
        records = list(self.passages.values())
        vectors = self.embeddings([p['section']+'\n'+p['text'] for p in records])
        old_ids = set(self.collection.get()['ids']) - set(self.passages)
        if old_ids:
            self.collection.delete(ids=list(old_ids))
        self.collection.upsert(ids=[p['id'] for p in records], embeddings=vectors,
            documents=[p['text'] for p in records],
            metadatas=[{'source_id':p['source_id'],'source_type':p['source_type'],'date_int':int(p['published'].replace('-',''))} for p in records])
        (DATA/'index-manifest.json').write_text(json.dumps({'embedding_model':self.embedding_model,'passage_count':len(records),'corpus_sha256':json.loads((DATA/'source-manifest.json').read_text())['corpus_sha256']},indent=2)+'\n')

    def search(self, query, as_of, source_type='all', limit=6):
        eligible = {k:p for k,p in self.passages.items() if p['published']<=as_of and (source_type=='all' or p['source_type']==source_type)}
        if not eligible:
            return []
        if self.collection.count() == 0:
            raise RuntimeError('Evidence index is missing. Run scripts/index.py.')
        where = {'date_int': {'$lte': int(as_of.replace('-',''))}}
        if source_type != 'all':
            where = {'$and': [where, {'source_type': source_type}]}
        result = self.collection.query(query_embeddings=self.embeddings([query]),n_results=min(12,len(eligible)),where=where)
        vector_ids = [pid for pid in result['ids'][0] if pid in eligible]
        tokens = set(re.findall(r'[a-z0-9]+',query.lower()))
        scored = []
        for pid,p in eligible.items():
            pt = set(re.findall(r'[a-z0-9]+',(p['section']+' '+p['text']).lower()))
            score = len(tokens & pt)/max(len(tokens),1)
            scored.append((pid,score))
        lexical_ids = [x[0] for x in sorted(scored,key=lambda x:x[1],reverse=True) if x[1]>0][:12]
        fused={}
        for ranking in [vector_ids,lexical_ids]:
            for i,pid in enumerate(ranking):
                fused[pid]=fused.get(pid,0)+1/(60+i+1)
        ids=sorted(fused,key=fused.get,reverse=True)[:limit]
        return [{**self.passages[pid], 'source':self.sources[self.passages[pid]['source_id']]} for pid in ids]


def public_source(source):
    return {k:v for k,v in source.items() if k!='text'}
