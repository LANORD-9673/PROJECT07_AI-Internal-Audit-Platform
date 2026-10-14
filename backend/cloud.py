"""Serve the compiled React UI and existing API from one public origin."""
import os
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from main import app

frontend_dist = Path(os.environ.get(
    'PROJECT07_FRONTEND_DIST',
    str(Path(__file__).resolve().parents[1] / 'frontend' / 'dist'),
))
if not (frontend_dist / 'index.html').is_file():
    raise RuntimeError('Build frontend first: cd frontend && npm ci && npm run build')

# Register last, so /api and /docs keep their original handlers.
app.mount('/', StaticFiles(directory=frontend_dist, html=True), name='frontend')
