import pytest

from evolver.settings import settings


@pytest.fixture
def testme():
    return "value"


@pytest.fixture
def tmp_calibration_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "ROOT_CALIBRATOR_FILE_STORAGE_PATH", tmp_path)
