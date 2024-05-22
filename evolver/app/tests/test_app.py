from fastapi.openapi.utils import get_openapi
from ..main import __version__  # Leave as relative for use in template: ssec-jhu/base-template.
from ..main import app


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

    def test_evolver_update_config_endpoint(self, app_client):
        data = {'hardware': {'test': {'driver': 'evolver.hardware.demo.NoOpSensorDriver'}}}
        response = app_client.post('/', json=data)
        assert response.status_code == 200
        newconfig = app_client.get('/').json()['config']
        assert newconfig['hardware']['test']['driver'] == 'evolver.hardware.demo.NoOpSensorDriver'

        data = {'history': {'driver': 'evolver.history.HistoryServer'}}
        response = app_client.post('/', json=data)
        assert response.status_code == 200

        newconfig = app_client.get('/').json()['config']
        assert newconfig["history"]["driver"] == 'evolver.history.HistoryServer'
        assert newconfig['hardware']['test']['driver'] == 'evolver.hardware.demo.NoOpSensorDriver'

    def test_evolver_app_control_loop_setup(self, app_client):
        # The context manager ensures that startup event loop is called
        # TODO: check results generated in control() (may require hardware at startup, or forced execution of loop)
        with app_client as client:
            response = client.get('/')
            assert response.status_code == 200
