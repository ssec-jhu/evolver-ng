import pytest

from evolver.device import Evolver
from evolver.hardware.standard.od_sensor import ODSensor
from evolver.serial import create_mock_serial


@pytest.fixture
def serial_mock():
    return create_mock_serial(
        {
            b"od_90r,500,_!": b"od_90a,123,456,end",
            b"od_90r,100,_!": b"od_90a,101,102,end",
        }
    )


@pytest.fixture
def evolver(serial_mock):
    e = Evolver()
    e.serial = serial_mock
    return e


@pytest.mark.parametrize(
    "integs, vials, expect",
    [
        (500, [0, 1], (123, 456)),
        (100, [0, 1], (101, 102)),
        (500, [0], (123, None)),
        (100, [1], (None, 102)),
    ],
)
def test_od_sensor(evolver, integs, vials, expect):
    od = ODSensor(addr="od_90", integrations=integs, vials=vials, evolver=evolver)
    od.read()
    assert set(od.get().keys()) == set(vials)
    for vial in vials:
        assert od.get()[vial] == ODSensor.Output(vial=vial, raw=expect[vial])


def test_od_sensor_vial_update(evolver):
    od = ODSensor(addr="od_90", evolver=evolver)
    od.read()
    assert set(od.get().keys()) == set([0, 1])
    od.vials = [0]
    od.read()
    assert set(od.get().keys()) == set([0])


def test_od_sensor_pass_serial(serial_mock):
    with pytest.raises(AttributeError, match="has no attribute 'serial'"):
        ODSensor(addr="od_90").read()
    od = ODSensor(addr="od_90", serial_conn=serial_mock)
    od.read()
    assert od.get()[0] == ODSensor.Output(vial=0, raw=123)


@pytest.mark.parametrize("integs, expect", [(500, (123, 456)), (100, (101, 102))])
def test_evolver_hookup(serial_mock, integs, expect):
    config = {
        "hardware": {
            "od": {
                "classinfo": "evolver.hardware.standard.od_sensor.ODSensor",
                "config": {
                    "addr": "od_90",
                    "integrations": integs,
                },
            }
        }
    }
    evolver = Evolver.create(config)
    evolver.serial = serial_mock
    assert evolver.state == {"od": {}}
    evolver.loop_once()
    assert evolver.state == {
        "od": {
            0: ODSensor.Output(vial=0, raw=expect[0]),
            1: ODSensor.Output(vial=1, raw=expect[1]),
        }
    }
