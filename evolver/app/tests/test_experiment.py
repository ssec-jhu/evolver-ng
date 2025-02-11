from evolver.app.main import app
from evolver.base import ConfigDescriptor
from evolver.device import Evolver, Experiment
from evolver.history.demo import InMemoryHistoryServer
from evolver.tests.conftest import tmp_calibration_dir  # noqa: F401


class TestExperiment:
    def test_experiments_list(self, app_client):
        response = app_client.get("/experiment/")
        assert response.status_code == 200
        assert response.json() == {}
        app.state.evolver = Evolver(
            experiments={
                "test": Experiment(controllers=[ConfigDescriptor(classinfo="evolver.controller.demo.NoOpController")])
            }
        )
        response = app_client.get("/experiment/")
        assert response.status_code == 200
        assert response.json() == {
            "test": {
                "controllers": [
                    {"classinfo": "evolver.controller.demo.NoOpController", "config": {"name": "NoOpController"}}
                ],
                "enabled": True,
                "name": None,
            }
        }

    def test_experiment_details_endpoint(self, app_client):
        app.state.evolver = Evolver(
            history=InMemoryHistoryServer(),
            experiments={
                "test": Experiment(controllers=[ConfigDescriptor(classinfo="evolver.controller.demo.NoOpController")])
            },
        )
        app.state.evolver.loop_once()
        response = app_client.get("/experiment/test")
        assert response.status_code == 200
        assert response.json()["config"] == {
            "controllers": [
                {"classinfo": "evolver.controller.demo.NoOpController", "config": {"name": "NoOpController"}}
            ],
            "enabled": True,
            "name": None,
        }
        assert len(response.json()["logs"]["data"]["NoOpController"]) == 1

    def test_experiment_log_endpoint(self, app_client):
        app.state.evolver = Evolver(
            history=InMemoryHistoryServer(),
            experiments={
                "test": Experiment(
                    controllers=[
                        ConfigDescriptor(
                            classinfo="evolver.controller.demo.NoOpController", config={"name": "NoOpController1"}
                        ),
                        ConfigDescriptor(
                            classinfo="evolver.controller.demo.NoOpController", config={"name": "NoOpController2"}
                        ),
                    ]
                )
            },
        )
        response = app_client.get("/experiment/test/logs")
        assert response.status_code == 200
        assert response.json() == {"data": {}}
        app.state.evolver.loop_once()
        response = app_client.get("/experiment/test/logs")
        assert len(response.json()["data"]["NoOpController1"]) == 1
        assert len(response.json()["data"]["NoOpController2"]) == 1
