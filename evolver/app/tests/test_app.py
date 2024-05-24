import os
import json
import yaml
from fastapi.openapi.utils import get_openapi
from fastapi.testclient import TestClient
from evolver.settings import settings
from evolver.device import EvolverConfig, HardwareDriverDescriptor
from evolver.util import load_config_for_evolver, save_evolver_config
from ..main import app, evolver, __version__, EvolverConfigWithoutDefaults


class TestApp:
    def test_root(self, app_client):
        response = app_client.get("/")
        assert response.status_code == 200

    def test_docs(self, app_client):
        # this test just ensures that everything in our app is json schemafiable
        # for the openapi docs generation. No assertions on the output since we
        # are not testing openapi utilities themselves.
        get_openapi(title='test', version='test', routes=app.routes)

    def test_healthz(self, app_client):
        response = app_client.get("/healthz")
        assert response.status_code == 200
        if __version__:
            assert __version__ in response.json()["message"], response.json()

    def test_evolver_app_default_config_dump_endpoint(self, app_client):
        response = app_client.get('/')
        assert response.status_code == 200
        assert sorted(response.json().keys()) == ['config', 'last_read', 'state']

    def test_EvolverConfigWithoutDefaults(self):
        EvolverConfigWithoutDefaults.model_validate(EvolverConfig().model_dump())
        EvolverConfigWithoutDefaults.model_validate_json(EvolverConfig().model_dump_json())

    def test_evolver_update_config_endpoint(self, app_client):
        assert not settings.CONFIG_FILE.exists()  # in these test we do not have a stored config at load time
        data = {'hardware': {'test': {'driver': 'evolver.hardware.demo.NoOpSensorDriver'}}}
        response = app_client.post('/', json=data)
        # all config fields are required so the above post failed with an Unprocessable Entity error.
        assert response.status_code == 422
        contents = json.loads(response.content)
        for content in contents["detail"]:
            assert content["msg"] == "Field required"

        new_data = EvolverConfig().copy(update=data)
        response = app_client.post('/', data=new_data.model_dump_json())
        assert response.status_code == 200
        newconfig = app_client.get('/').json()['config']
        assert newconfig['hardware']['test']['driver'] == 'evolver.hardware.demo.NoOpSensorDriver'
        # check we wrote out a file
        with open(settings.CONFIG_FILE) as f:
            saved = yaml.load(f, yaml.SafeLoader)
        assert saved['hardware']['test']['driver'] == 'evolver.hardware.demo.NoOpSensorDriver'

    def test_evolver_app_control_loop_setup(self, app_client):
        # The context manager ensures that startup event loop is called
        # TODO: check results generated in control() (may require hardware at startup, or forced execution of loop)
        with app_client as client:
            response = client.get('/')
            assert response.status_code == 200


def test_app_load_file(tmp_path):
    os.chdir(tmp_path)
    config = EvolverConfig(hardware={
        'file_test': HardwareDriverDescriptor(driver='evolver.hardware.demo.NoOpSensorDriver')
    })
    save_evolver_config(config, settings.CONFIG_FILE)
    load_config_for_evolver(evolver, settings.CONFIG_FILE)
    client = TestClient(app)
    client.get('/').json()['config']['hardware']['file_test']['driver'] == 'evolver.hardware.demo.NoOpSensorDriver'
