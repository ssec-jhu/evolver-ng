import pytest

from evolver.calibration.interface import Calibrator, Transformer
from evolver.hardware.standard.led import LED
from evolver.hardware.standard.od_sensor import ODSensor
from evolver.hardware.standard.pump import VialIEPump
from evolver.hardware.standard.stir import Stir
from evolver.hardware.standard.temperature import Temperature
from evolver.hardware.test_utils import SerialVialEffectorHardwareTestSuite, SerialVialSensorHardwareTestSuite
from evolver.settings import settings


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


@pytest.mark.parametrize("response_map", [{b"tempr,4095,4095,_!": b"tempa,2020,2500,end"}])
@pytest.mark.parametrize(
    "config_params, expected",
    [
        (
            {"addr": "temp", "slots": 2},
            {
                0: Temperature.Output(vial=0, raw=2020, temperature=26.03),
                1: Temperature.Output(vial=1, raw=2500, temperature=11.9),
            },
        )
    ],
)
class TestTempSensorMode(SerialVialSensorHardwareTestSuite):
    driver = Temperature


class TestTempSensor:
    def test_default_calibrator(self):
        obj = Temperature(addr="temp", slots=2)
        assert isinstance(obj.calibrator, Calibrator)
        assert isinstance(obj.calibrator.output_transformer, dict)
        assert settings.DEFAULT_NUMBER_OF_VIALS_PER_BOX
        assert len(obj.calibrator.output_transformer) == settings.DEFAULT_NUMBER_OF_VIALS_PER_BOX
        for vial, transformer in obj.calibrator.output_transformer.items():
            assert isinstance(transformer, Transformer)


@pytest.mark.parametrize(
    "config_params, values, serial_out",
    [
        (
            {"addr": "temp", "slots": 2},
            [[Temperature.Input(vial=0, temperature=30.1)], [Temperature.Input(vial=1, temperature=40.5)]],
            [b"tempr,1875,4095,_!", b"tempr,1875,1523,_!"],
        ),
        ({"addr": "temp", "slots": 3}, [[]], [b"tempr,4095,4095,4095,_!"]),
        (
            {"addr": "temp", "vials": [1], "slots": 2},
            [[Temperature.Input(vial=0, temperature=30.1), Temperature.Input(vial=1, temperature=40.5)], []],
            [b"tempr,4095,1523,_!", b"tempr,4095,1523,_!"],
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


def test_vialiepump_input_validation():
    VialIEPump.Input(vial=0, flow_rate_influx=1, flow_rate_efflux=2)
    with pytest.raises(ValueError, match="cannot specify both flow_rate and flow_rate_influx/efflux"):
        VialIEPump.Input(vial=0, flow_rate=1, flow_rate_influx=1)
    with pytest.raises(ValueError, match="must specify either flow_rate or both flow_rate_influx/efflux"):
        VialIEPump.Input(vial=0, flow_rate_influx=1)
    input = VialIEPump.Input(vial=0, flow_rate=1)
    assert input.flow_rate_influx == input.flow_rate_efflux == 1
