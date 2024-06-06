import json
import yaml

from fastapi.openapi.utils import get_openapi

from evolver import __version__
from evolver.app.main import app, EvolverConfigWithoutDefaults
from evolver.base import ConfigDescriptor
from evolver.settings import app_settings
from evolver.device import Evolver


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
        EvolverConfigWithoutDefaults.model_validate(Evolver.Config().model_dump())
        EvolverConfigWithoutDefaults.model_validate_json(Evolver.Config().model_dump_json())

    def test_evolver_update_config_endpoint(self, app_client):
        assert app_settings.CONFIG_FILE.exists()  # Note: app_client generates an default config and saves to file.
        data = {'hardware': {'test': {'classinfo': 'evolver.hardware.demo.NoOpSensorDriver'}}}
        response = app_client.post('/', json=data)
        # all config fields are required so the above post failed with an Unprocessable Entity error.
        assert response.status_code == 422
        contents = json.loads(response.content)
        for content in contents["detail"]:
            assert content["msg"] == "Field required"

        new_data = Evolver.Config().copy(update=data)
        response = app_client.post('/', data=new_data.model_dump_json())
        assert response.status_code == 200
        newconfig = app_client.get('/').json()['config']
        assert newconfig['hardware']['test']['classinfo'] == 'evolver.hardware.demo.NoOpSensorDriver'
        # check we wrote out a file
        with open(app_settings.CONFIG_FILE) as f:
            saved = yaml.safe_load(f)
        assert saved['hardware']['test']['classinfo'] == 'evolver.hardware.demo.NoOpSensorDriver'

    def test_evolver_app_control_loop_setup(self, app_client):
        # TODO: check results generated in control() (may require hardware at startup, or forced execution of loop)
        response = app_client.get('/')
        assert response.status_code == 200

    def test_schema_endpoint(self, app_client):
        response = app_client.get('/schema')
        assert response.status_code == 200
        # There's not much in the default config yet, this will change in future PRs.
        assert json.loads(response.content) == dict(hardware=[], controllers=[])


def test_app_load_file(app_client):
    config = Evolver.Config(hardware={
        'file_test': ConfigDescriptor(classinfo='evolver.hardware.demo.NoOpSensorDriver')
    })
    config.save(app_settings.CONFIG_FILE)
    app.state.evolver = Evolver.create(Evolver.Config.load(app_settings.CONFIG_FILE))
    response = app_client.get('/')
    assert response.status_code == 200
    assert response.json()['config']['hardware']['file_test']['classinfo'] == 'evolver.hardware.demo.NoOpSensorDriver'
