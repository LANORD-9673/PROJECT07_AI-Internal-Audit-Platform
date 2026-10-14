import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

@pytest.fixture
def client(tmp_path,monkeypatch):
    import models.db as db
    monkeypatch.setattr(db,'DB_PATH',tmp_path/'test.sqlite3')
    with TestClient(__import__('main').app) as api:
        yield api
