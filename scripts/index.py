import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.retrieval import EvidenceStore
if __name__ == '__main__':
    store=EvidenceStore()
    store.index()
    print(f'Indexed {store.collection.count()} real source passages in Chroma.')
