import pytest

from evolver.hardware.standard.led import LED
from evolver.hardware.standard.od_sensor import ODSensor
from evolver.hardware.standard.pump import VialIEPump
from evolver.hardware.standard.stir import Stir
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


@pytest.mark.parametrize(
    "config_params, values, serial_out",
    [
        (
            {"addr": "od_led", "slots": 2},
            [[LED.Input(vial=0, brightness=1), LED.Input(vial=1, brightness=0.5)], [LED.Input(vial=1, brightness=0)]],
            [b"od_ledr,4095,2047,_!", b"od_ledr,4095,0,_!"],
        ),
        (
            {"addr": "od_led", "vials": [0], "slots": 2},
            [[LED.Input(vial=0, brightness=0), LED.Input(vial=1, brightness=0.5)], []],
            [b"od_ledr,0,4095,_!", b"od_ledr,0,4095,_!"],
        ),
        (
            {"addr": "od_led", "slots": 3},
            [[]],
            [b"od_ledr,4095,4095,4095,_!"],
        ),
    ],
)
class TestLED(SerialVialEffectorHardwareTestSuite):
    driver = LED


@pytest.mark.parametrize(
    "config_params, values, serial_out",
    [
        (
            {"addr": "stir", "slots": 2},
            [[Stir.Input(vial=0, rate=8)], [Stir.Input(vial=1, rate=9)]],
            [b"stirr,8,0,_!", b"stirr,8,9,_!"],
        ),
        (
            {"addr": "stir", "vials": [1], "slots": 2},
            [[Stir.Input(vial=0, rate=8)], [Stir.Input(vial=1, rate=9)]],
            [b"stirr,0,0,_!", b"stirr,0,9,_!"],
        ),
    ],
)
class TestStir(SerialVialEffectorHardwareTestSuite):
    driver = Stir


@pytest.mark.parametrize(
    "config_params, values, serial_out",
    [
        (
            {"addr": "pump", "slots": 2},
            [[VialIEPump.Input(vial=0, flow_rate_influx=1, flow_rate_efflux=2)]],
            [b"pumpr,1.0|1,--,2.0|2,--,--,--,_!"],
        ),
        (
            {"addr": "pump", "slots": 2},
            [
                [
                    VialIEPump.Input(vial=0, flow_rate_influx=1, flow_rate_efflux=1),
                    VialIEPump.Input(vial=1, flow_rate_influx=8, flow_rate_efflux=9),
                ]
            ],
            [b"pumpr,1.0|1,8.0|8,1.0|1,9.0|9,--,--,_!"],
        ),
        (
            {"addr": "pump", "ipp_pumps": [0, 1], "slots": 2, "influx_map": {0: 0}, "efflux_map": {0: 1}},
            [[VialIEPump.Input(vial=0, flow_rate_influx=1, flow_rate_efflux=2)]],
            [b"pumpr,1.0|0|1,1.0|0|2,1.0|0|3,2.0|1|1,2.0|1|2,2.0|1|3,_!"],
        ),
    ],
)
class TestPump(SerialVialEffectorHardwareTestSuite):
    driver = VialIEPump
