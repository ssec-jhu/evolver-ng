import pytest

from evolver.hardware.standard.od_sensor import ODSensor
from evolver.hardware.standard.temperature import Temperature
from evolver.hardware.test_utils import SerialVialEffectorHardwareTestSuite, SerialVialSensorHardwareTestSuite


@pytest.mark.parametrize(
    "response_map",
    [
        {
            b"od_90r,500,_!": b"od_90a,123,456,end",
            b"od_90r,100,_!": b"od_90a,101,102,end",
        }
    ],
)
@pytest.mark.parametrize(
    "config_params, expected",
    [
        ({"addr": "od_90"}, {0: ODSensor.Output(vial=0, raw=123), 1: ODSensor.Output(vial=1, raw=456)}),
        ({"addr": "od_90", "vials": [0]}, {0: ODSensor.Output(vial=0, raw=123)}),
        ({"addr": "od_90", "vials": [1], "integrations": 100}, {1: ODSensor.Output(vial=1, raw=102)}),
    ],
)
class TestOD(SerialVialSensorHardwareTestSuite):
    driver = ODSensor


@pytest.mark.parametrize("response_map", [{b"tempr,4095,4095,_!": b"tempa,1,2,end"}])
@pytest.mark.parametrize(
    "config_params, expected",
    [({"addr": "temp", "slots": 2}, {0: Temperature.Output(vial=0, raw=1), 1: Temperature.Output(vial=1, raw=2)})],
)
class TestTempSensorMode(SerialVialSensorHardwareTestSuite):
    driver = Temperature


@pytest.mark.parametrize(
    "config_params, values, serial_out",
    [
        (
            {"addr": "temp", "slots": 2},
            [[Temperature.Input(vial=0, temperature=30.1)], [Temperature.Input(vial=1, temperature=40.5)]],
            [b"tempr,30,4095,_!", b"tempr,30,40,_!"],
        ),
        ({"addr": "temp", "slots": 3}, [[]], [b"tempr,4095,4095,4095,_!"]),
        (
            {"addr": "temp", "vials": [1], "slots": 2},
            [[Temperature.Input(vial=0, temperature=30.1), Temperature.Input(vial=1, temperature=40.5)], []],
            [b"tempr,4095,40,_!", b"tempr,4095,40,_!"],
        ),
    ],
)
class TestTempEffectorMode(SerialVialEffectorHardwareTestSuite):
    driver = Temperature
