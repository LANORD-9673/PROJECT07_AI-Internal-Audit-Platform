"""In-process adapter: Streamlit calls the unchanged FastAPI routes, no public API server."""
import asyncio
import sys
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'backend'))
from main import app
from models.db import init_db
from services.workflow import setup


class ApiError(RuntimeError):
    pass


def initialize():
    init_db()
    setup()


async def _request(method, path, **kwargs):
    # A separate client per call avoids sharing cookies/state between browser sessions.
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://internal') as client:
        response = await client.request(method, '/api' + path, **kwargs)
    body = response.json()
    if response.is_error or body.get('status') == 'error':
        error = (body.get('errors') or [body.get('detail') or {}])[0]
        raise ApiError(f"{error.get('code', response.status_code)}: {error.get('message', 'Request failed')}")
    return body['data']


def request(method, path, **kwargs):
    return asyncio.run(_request(method, path, **kwargs))
