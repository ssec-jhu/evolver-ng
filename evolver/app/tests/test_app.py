import json
from datetime import datetime, timedelta

import numpy as np
import pytest
import yaml
from fastapi.openapi.utils import get_openapi

import evolver.util
from evolver import __version__
from evolver.app.main import EvolverConfigWithoutDefaults, SchemaResponse, app
from evolver.base import BaseConfig, BaseInterface, ConfigDescriptor
from evolver.calibration.demo import NoOpCalibrator
from evolver.calibration.interface import Status
from evolver.calibration.standard.polyfit import LinearCalibrator, LinearTransformer
from evolver.device import Evolver, Experiment
from evolver.hardware.demo import NoOpEffectorDriver, NoOpSensorDriver
from evolver.hardware.interface import EffectorDriver, SensorDriver
from evolver.history.demo import InMemoryHistoryServer
from evolver.settings import app_settings
from evolver.tests.conftest import tmp_calibration_dir  # noqa: F401


class TestApp:
    def test_root(self, app_client):
        response = app_client.get("/")
        assert response.status_code == 200

    def test_docs(self, app_client):
        # this test just ensures that everything in our app is json schemafiable
        # for the openapi docs generation. No assertions on the output since we
        # are not testing openapi utilities themselves.
        get_openapi(title="test", version="test", routes=app.routes)

    def test_healthz(self, app_client):
        response = app_client.get("/healthz")
        assert response.status_code == 200
        if __version__:
            assert __version__ in response.json()["message"], response.json()
        assert response.json()["name"]
        assert response.json()["active"]

    def test_evolver_app_default_config_dump_endpoint(self, app_client):
        response = app_client.get("/")
        assert response.status_code == 200
        assert sorted(response.json().keys()) == ["active", "config", "last_read", "state"]

    def test_EvolverConfigWithoutDefaults(self):
        EvolverConfigWithoutDefaults.model_validate(Evolver.Config().model_dump())
        EvolverConfigWithoutDefaults.model_validate_json(Evolver.Config().model_dump_json())

    def test_evolver_update_config_endpoint(self, app_client):
        assert app_settings.CONFIG_FILE.exists()  # Note: app_client generates an default config and saves to file.
        data = {"hardware": {"test": {"classinfo": "evolver.hardware.demo.NoOpSensorDriver"}}}
        response = app_client.post("/", json=data)
        # all config fields are required so the above post failed with an Unprocessable Entity error.
        assert response.status_code == 422
        contents = json.loads(response.content)
        for content in contents["detail"]:
            assert content["msg"] == "Field required"

        new_data = Evolver.Config().copy(update=data)
        response = app_client.post("/", data=new_data.model_dump_json())
        assert response.status_code == 200
        newconfig = app_client.get("/").json()["config"]
        assert newconfig["hardware"]["test"]["classinfo"] == "evolver.hardware.demo.NoOpSensorDriver"
        # check we wrote out a file
        with open(app_settings.CONFIG_FILE) as f:
            saved = yaml.safe_load(f)
        assert saved["hardware"]["test"]["classinfo"] == "evolver.hardware.demo.NoOpSensorDriver"

    def test_evolver_app_control_loop_setup(self, app_client):
        # TODO: check results generated in control() (may require hardware at startup, or forced execution of loop)
        response = app_client.get("/")
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "classinfo",
        (
            None,
            Evolver,
            BaseConfig,
            BaseInterface,
            EffectorDriver,
            SensorDriver,
            NoOpCalibrator,
            NoOpEffectorDriver,
            NoOpSensorDriver,
        ),
    )
    def test_schema_endpoint(self, app_client, classinfo):
        fqn = evolver.util.fully_qualified_name(classinfo) if classinfo else evolver.util.fully_qualified_name(Evolver)
        response = app_client.get("/schema", params=dict(classinfo=fqn) if classinfo else None)
        assert response.status_code == 200
        # There's not much in the default config yet, this will change in future PRs.
        assert json.loads(response.content) == SchemaResponse(classinfo=fqn).model_dump(mode="json")

    @pytest.mark.parametrize("classinfo", ("this.is.not.a.class", "int", ""))
    def test_schema_endpoint_exception(self, app_client, classinfo):
        response = app_client.get("/schema/", params=dict(classinfo=classinfo))
        assert response.status_code == 422

    def test_calibration_status(self, app_client):
        t0 = datetime.now()
        hardware = {
            "test_hardware1": NoOpSensorDriver(calibrator=NoOpCalibrator()),
            "test_hardware2": NoOpSensorDriver(calibrator=NoOpCalibrator()),
        }
        app.state.evolver = Evolver(hardware=hardware)

        response = app_client.get("/calibration_status/", params=dict(name=None))
        assert response.status_code == 200
        contents = json.loads(response.content)

        for device in hardware:
            assert contents[device]
            for transformer in ("input_transformer", "output_transformer"):
                status = Status.model_validate(contents[device][transformer])
                assert getattr(hardware[device].calibrator, transformer).created == status.created
                assert t0 < status.created
                assert status.ok

    def test_calibrate(self, app_client, tmp_calibration_dir):  # noqa: F811
        parameters = [1, 2]
        # Creat calibrator from transformer with stale (expired) config.
        calibrator = LinearCalibrator(
            input_transformer=LinearTransformer(
                parameters=parameters, created=datetime.now() - timedelta(minutes=60), expire=timedelta(minutes=50)
            )
        )
        app.state.evolver = Evolver(hardware={"test_hardware": NoOpSensorDriver(calibrator=calibrator)})
        response = app_client.get("/calibration_status/", params=dict(name="test_hardware"))
        assert response.status_code == 200
        # Assert that status is not ok, is stale.
        assert not Status.model_validate(json.loads(response.content)["input_transformer"]).ok

        # Mock new data to calibrate against.
        new_parameters = [2, 3]
        assert new_parameters != parameters
        x = np.linspace(0, 100, 100)
        y = new_parameters[0] + x * new_parameters[1]

        # Recalibrate.
        response = app_client.post("/calibrate/test_hardware", json=dict(input_transformer=[x.tolist(), y.tolist()]))
        assert response.status_code == 200

        # Assert transformer has new parameters and has been recalibrated.
        assert app.state.evolver.hardware["test_hardware"].calibrator.input_transformer.parameters == pytest.approx(
            new_parameters
        )

        # Assert that new config is no longer stale.
        response = app_client.get("/calibration_status/", params=dict(name="test_hardware"))
        assert response.status_code == 200
        # Assert that status is not ok, is stale.
        assert Status.model_validate(json.loads(response.content)["input_transformer"]).ok

    @pytest.mark.parametrize(
        ("func", "kwargs"),
        (
            ("get", dict(url="/calibration_status/", params=dict(name="non_existent_hardware"))),
            ("post", dict(url="/calibrate/non_existent_hardware")),
        ),
    )
    def test_hardware_not_found_exceptions(self, app_client, func, kwargs):
        response = getattr(app_client, func)(**kwargs)
        assert response.status_code == 404
        contents = json.loads(response.content)
        assert contents["detail"] == "Hardware not found"

    @pytest.mark.parametrize(
        ("func", "kwargs"),
        (
            ("get", dict(url="/calibration_status/", params=dict(name="test_hardware"))),
            ("post", dict(url="/calibrate/test_hardware")),
        ),
    )
    def test_calibrator_not_found_exceptions(self, app_client, func, kwargs):
        app.state.evolver = Evolver(hardware={"test_hardware": NoOpSensorDriver()})
        response = getattr(app_client, func)(**kwargs)
        assert response.status_code == 404
        contents = json.loads(response.content)
        assert contents["detail"] == "Hardware has no calibrator"

    @pytest.mark.parametrize(
        ("query_params", "body"),
        [
            ({}, {}),
            ({"n_max": 1}, {}),
            ({}, {"names": ["nonexistent"]}),
            ({"t_start": 0, "t_stop": 1, "n_max": 1}, {"names": ["test"]}),
            ({}, {"names": ["test"], "vials": [0, 1]}),
            ({}, {"names": ["test"], "properties": ["value"]}),
        ],
    )
    def test_history(self, app_client, query_params, body):
        app.state.evolver = Evolver(history=InMemoryHistoryServer(), hardware={"test": NoOpSensorDriver()})
        response = app_client.post("/history/", params=query_params, json=body)
        assert response.status_code == 200
        assert response.json() == {"data": {}}
        app.state.evolver.loop_once()
        app.state.evolver.loop_once()
        response = app_client.post("/history/", params=query_params, json=body)
        assert response.status_code == 200
        if body.get("names", ["test"]) == ["test"]:
            assert response.json()["data"]["test"][0]["timestamp"] > 0
            assert isinstance(response.json()["data"]["test"][0]["data"], dict)
            if n_max := query_params.get("n_max", None):
                assert len(response.json()["data"]["test"]) <= n_max
        else:
            assert response.json() == {"data": {}}

    def test_abort_endpoint(self, app_client):
        assert app.state.evolver.enable_control
        response = app_client.post("/abort")
        assert response.status_code == 200
        assert not app.state.evolver.enable_control
        saved_config = Evolver.Config.load(app_settings.CONFIG_FILE)
        assert not saved_config.enable_control
        # healthz and state should report inactive state
        for endpoint in ("/healthz", "/state"):
            response = app_client.get(endpoint)
            assert response.status_code == 200
            assert not response.json()["active"]

    def test_start_endpoint(self, app_client):
        _ = app_client.post("/abort")
        assert not app.state.evolver.enable_control
        response = app_client.post("/start")
        assert response.status_code == 200
        assert app.state.evolver.enable_control

    def test_event_endpoint(self, app_client):
        app.state.evolver = Evolver(history=InMemoryHistoryServer())
        response = app_client.post(
            "/event", json={"name": "test", "message": "test_event_api", "vial": 99, "data": {"key": "value"}}
        )
        assert response.status_code == 200
        recorded_event = app.state.evolver.history.get(names=["test"], kinds=["event"]).data["test"][0]
        assert recorded_event.vial == 99
        assert recorded_event.data == {"message": "test_event_api", "key": "value", "vial": 99, "level": "EVENT"}

    def test_state_endpoint_nan_data_becomes_null(self, app_client):
        class NaNDataSensor(SensorDriver):
            class Output(SensorDriver.Output):
                x: float

            def get(self):
                return {0: self.Output(x=np.nan, vial=0)}

            def read(self):
                pass

        app.state.evolver = Evolver(hardware={"test": NaNDataSensor()})
        app.state.evolver.loop_once()
        response = app_client.get("/state")
        assert response.status_code == 200
        assert response.json()["state"]["test"]["0"]["x"] is None

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
                    {
                        "classinfo": "evolver.controller.demo.NoOpController",
                        "config": {
                            "bolus_volume": 2.0,
                            "dilution_rate": 0.1,
                            "min_od": 0.5,
                            "name": "NoOpController",
                            "start_delay": 1,
                            "stir_rate": 8.0,
                            "vial_volume": 20.0,
                        },
                    }
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

        assert len(response.json()["logs"]["data"]["NoOpController"]) == 1
        assert response.json()["config"] == {
            "controllers": [
                {
                    "classinfo": "evolver.controller.demo.NoOpController",
                    "config": {
                        "bolus_volume": 2.0,
                        "dilution_rate": 0.1,
                        "min_od": 0.5,
                        "name": "NoOpController",
                        "start_delay": 1,
                        "stir_rate": 8.0,
                        "vial_volume": 20.0,
                    },
                }
            ],
            "enabled": True,
            "name": None,
        }

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


def test_app_load_file(app_client):
    config = Evolver.Config(
        hardware={"file_test": ConfigDescriptor(classinfo="evolver.hardware.demo.NoOpSensorDriver")}
    )
    config.save(app_settings.CONFIG_FILE)
    app.state.evolver = Evolver.create(Evolver.Config.load(app_settings.CONFIG_FILE))
    response = app_client.get("/")
    assert response.status_code == 200
    assert response.json()["config"]["hardware"]["file_test"]["classinfo"] == "evolver.hardware.demo.NoOpSensorDriver"
