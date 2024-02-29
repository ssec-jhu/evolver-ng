from ..main import __version__  # Leave as relative for use in template: ssec-jhu/base-template.


class TestApp:
    def test_root(self, app_client):
        response = app_client.get("/")
        assert response.status_code == 200

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
        data = {'hardware': {'test': {'driver': 'evolver.hardware.NoOpSensorDriver'}}}
        response = app_client.post('/', json=data)
        assert response.status_code == 200
        newconfig = app_client.get('/').json()['config']
        assert newconfig['hardware']['test']['driver'] == 'evolver.hardware.NoOpSensorDriver'

    def test_evolver_app_react_loop_setup(self, app_client):
        with app_client as client:
            response = client.get('/')
            assert response.status_code == 200
