"""Local-only launcher using the existing gcloud login. Never prints the token."""
import os
import subprocess
import sys

if len(sys.argv)<2 or not os.getenv('GOOGLE_CLOUD_PROJECT'):
    raise SystemExit('Set GOOGLE_CLOUD_PROJECT and pass a Python script or -m module.')
os.environ['VERTEX_ACCESS_TOKEN']=subprocess.check_output(['gcloud','auth','print-access-token'],text=True).strip()
os.environ['EVIDENCE_PROVIDER']='vertex'
os.environ['EVIDENCE_MODEL']=os.getenv('VERTEX_GENERATION_MODEL','google/gemini-3.8-flash')
os.environ['EMBEDDING_PROVIDER']='vertex'
os.environ['EMBEDDING_MODEL']='text-embedding-005'
os.execv(sys.executable,[sys.executable,*sys.argv[1:]])
