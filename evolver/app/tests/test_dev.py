from evolver.app.main import app
from evolver.base import ConfigDescriptor
from evolver.device import Evolver, Experiment
from evolver.history.demo import InMemoryHistoryServer
from evolver.settings import app_settings
from evolver.tests.conftest import tmp_calibration_dir  # noqa: F401


class TestDev:
    def test_dev_loop_once_endpoint(self, app_client, monkeypatch):
        # Set DEV_MODE to True for this test
        monkeypatch.setattr(app_settings, "DEV_MODE", True)

        app.state.evolver = Evolver(
            history=InMemoryHistoryServer(),
            experiments={
                "test": Experiment(controllers=[ConfigDescriptor(classinfo="evolver.controller.demo.NoOpController")])
            },
        )

        # First check no logs exist
        response = app_client.get("/experiment/test/logs")
        assert response.status_code == 200
        assert response.json() == {"data": {}}

        # Trigger loop_once via dev endpoint
        response = app_client.post("/dev/loop_once")
        assert response.status_code == 200
        assert response.json() == {"status": "success", "message": "Loop iteration completed"}

        # Verify logs were created
        response = app_client.get("/experiment/test/logs")
        assert response.status_code == 200
        assert len(response.json()["data"]["NoOpController"]) == 1

    def test_dev_loop_once_endpoint_dev_mode_disabled(self, app_client, monkeypatch):
        # ensure DEV_MODE is False by default
        response = app_client.post("/dev/loop_once")
        assert response.status_code == 403
        assert response.json() == {"detail": "Only available in development mode"}
