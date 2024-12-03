import time

import pytest

from evolver.hardware.demo import NoOpSensorDriver
from evolver.history.interface import HistoryResult
from evolver.history.standard import HistoryServer
from evolver.settings import settings


@pytest.fixture(autouse=True)
def patch_storage(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "EXPERIMENT_FILE_STORAGE_PATH", tmp_path)


@pytest.fixture(params=[(1, None, 3), (1, "test", 1), (2, "test2", 0)])
def history_server(request):
    return HistoryServer(
        partition_seconds=request.param[0], experiment=request.param[1], buffer_partitions=request.param[2]
    )


@pytest.fixture
def sensor():
    return NoOpSensorDriver()


def test_history_server(history_server, sensor):
    t0 = time.time()
    sensor_read = sensor.read()
    history_server.put("test", "sensor", sensor_read[0], vial=0)
    result = history_server.get(name="test")
    assert "test" in result.data
    assert result.data["test"][0].timestamp >= t0
    assert result.data["test"][0].data == sensor_read[0].model_dump()
    result = history_server.get(name="test", t_stop=t0)
    assert result == HistoryResult(data={})
    # Add another record in order to test t_start parameter assuring we skip the first record
    t1 = time.time()
    history_server.put("test", "sensor", sensor_read[1], vial=1)
    result = history_server.get(name="test")
    # first sanity check that we have populated multiple records
    assert len(result.data["test"]) == 2
    result = history_server.get(name="test", kinds=["sensor"], t_start=t1)
    assert len(result.data["test"]) == 1
    assert result.data["test"][0].timestamp >= t1
    # filter by vial and property
    result = history_server.get(name="test", vials=[1], properties=["value"])
    assert result.data["test"][0].data == {"value": sensor_read[1].value}
    # filter by vial and property, but no match
    result = history_server.get(name="test", vials=[100])
    assert result == HistoryResult(data={})
    # kinds we don't have
    assert history_server.get(name="test", kinds=["nonexistent"]) == HistoryResult(data={})


def test_history_server_nonexistent_empty_result(history_server, sensor):
    history_server.put("test", "sensor", sensor.read())
    assert history_server.get(name="nonexistent") == HistoryResult(data={})


def test_history_server_empty_history_empty_result(history_server):
    assert history_server.get() == HistoryResult(data={})


def test_history_server_non_json_ok(history_server):
    history_server.put("test", "sensor", "not json")
    result = history_server.get(name="test")
    assert result.data["test"][0].data == "not json"


def test_history_resume_history(sensor):
    HistoryServer(partition_seconds=0).put("test", "sensor", sensor.read())
    # the above should go out of scope, next one would not share file handles
    # so this assures we are appending to existing partition (and setting
    # partition_seconds to 0 ensures we can't cycle during test)
    history = HistoryServer(partition_seconds=0)
    history.put("test", "sensor", sensor.read())
    assert len(history.get(name="test").data["test"]) == 2


def test_history_server_experiment_distinction(sensor):
    ha = HistoryServer(experiment="A")
    ha.put("test", "sensor", sensor.read())
    hb = HistoryServer(experiment="B")
    hb.put("test", "sensor", sensor.read())
    assert len(ha.get().data["test"]) == 1
    assert len(hb.get().data["test"]) == 1
