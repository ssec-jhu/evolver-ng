import pytest
from fastapi.testclient import TestClient

from evolver.app.main import app
from evolver.device import Evolver
from evolver.settings import app_settings, settings


@pytest.fixture
def app_client(tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "CONFIG_FILE", tmp_path / app_settings.CONFIG_FILE)
    monkeypatch.setattr(settings, "EXPERIMENT_FILE_STORAGE_PATH", tmp_path / settings.EXPERIMENT_FILE_STORAGE_PATH)

    # Create and save a default config file to be read upon app startup.
    Evolver.Config().save(app_settings.CONFIG_FILE)

    with TestClient(app) as client:
        yield client
