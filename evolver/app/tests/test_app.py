import json

import pytest
import yaml
from fastapi.openapi.utils import get_openapi

import evolver.util
from evolver import __version__
from evolver.app.main import EvolverConfigWithoutDefaults, SchemaResponse, app
from evolver.base import BaseConfig, BaseInterface, ConfigDescriptor
from evolver.calibration.demo import NoOpCalibrator
from evolver.calibration.standard.linear import SimpleCalibrator
from evolver.device import Evolver
from evolver.hardware.demo import NoOpEffectorDriver, NoOpSensorDriver
from evolver.hardware.interface import EffectorDriver, SensorDriver
from evolver.settings import app_settings


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

    def test_evolver_app_default_config_dump_endpoint(self, app_client):
        response = app_client.get("/")
        assert response.status_code == 200
        assert sorted(response.json().keys()) == ["config", "last_read", "state"]

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
        app.state.evolver = Evolver(
            hardware={
                "test_hardware1": NoOpSensorDriver(calibrator=NoOpCalibrator()),
                "test_hardware2": NoOpSensorDriver(calibrator=SimpleCalibrator()),
            }
        )

        response = app_client.get("/calibration_status/", params=dict(name=None))
        assert response.status_code == 200
        contents = json.loads(response.content)
        assert contents["test_hardware1"]
        assert not contents["test_hardware2"]

    def test_calibrate(self, app_client):
        app.state.evolver = Evolver(hardware={"test_hardware": NoOpSensorDriver(calibrator=SimpleCalibrator())})
        response = app_client.get("/calibration_status/", params=dict(name="test_hardware"))
        assert response.status_code == 200
        assert json.loads(response.content) is False

        response = app_client.post("/calibrate/test_hardware")
        assert response.status_code == 200

        response = app_client.get("/calibration_status/", params=dict(name="test_hardware"))
        assert response.status_code == 200
        assert json.loads(response.content) is True

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
        # response = app_client.get("/calibration_status/", params=dict(name="test_hardware"))
        assert response.status_code == 404
        contents = json.loads(response.content)
        assert contents["detail"] == "Hardware has no calibrator"


def test_app_load_file(app_client):
    config = Evolver.Config(
        hardware={"file_test": ConfigDescriptor(classinfo="evolver.hardware.demo.NoOpSensorDriver")}
    )
    config.save(app_settings.CONFIG_FILE)
    app.state.evolver = Evolver.create(Evolver.Config.load(app_settings.CONFIG_FILE))
    response = app_client.get("/")
    assert response.status_code == 200
    assert response.json()["config"]["hardware"]["file_test"]["classinfo"] == "evolver.hardware.demo.NoOpSensorDriver"
