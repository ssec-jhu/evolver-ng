import pytest
from fastapi.testclient import TestClient

from evolver.app.main import app


@pytest.fixture
def app_client(tmp_path, monkeypatch):
    with TestClient(app) as client:
        yield client
