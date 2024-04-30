from evolver.hardware.demo import NoOpSensorDriver
from evolver.history import HistoryServer

import logging
logging.getLogger()


class MySensor(NoOpSensorDriver):
    @HistoryServer.track_history()
    def read(self,  *args, **kwargs):
        return super().read(*args, **kwargs)


class TestHistory:
    def test_history_decorator(self):
        history = HistoryServer()
        sensor = MySensor()

        assert isinstance(history.history, dict)
        assert not history.get(sensor.name)

        sensor.read()
        output = sensor.get()
        assert output

        assert history.history
        assert history.get(sensor.name)[0][1] == output
