"""Vertex uses ADC in Cloud Run; a short-lived local token can be supplied for testing."""
import os
import threading

_credentials = None
_lock = threading.Lock()


def access_token():
    if os.getenv('VERTEX_ACCESS_TOKEN'):
        return os.environ['VERTEX_ACCESS_TOKEN']
    import google.auth
    from google.auth.transport.requests import Request
    global _credentials
    with _lock:
        if _credentials is None:
            _credentials, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
        if not _credentials.valid:
            _credentials.refresh(Request())
        return _credentials.token


def project_id():
    value=os.getenv('GOOGLE_CLOUD_PROJECT')
    if not value:
        raise ValueError('Set GOOGLE_CLOUD_PROJECT for Vertex AI.')
    return value
