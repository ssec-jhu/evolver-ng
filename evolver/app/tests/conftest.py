import pytest
from fastapi.testclient import TestClient

from evolver.app.main import app
from evolver.device import EvolverConfig
from evolver.settings import app_settings


@pytest.fixture
def app_client(tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "CONFIG_FILE", tmp_path / app_settings.CONFIG_FILE)

    # Create and save a default config file to be read upon app startup.
    EvolverConfig().save(app_settings.CONFIG_FILE)

    with TestClient(app) as client:
        yield client
