import pytest
from evolver.device import Evolver, EvolverConfig
from evolver.serial import PySerialEmulator, EvolverSerialUART
from evolver.hardware.standard.od_sensor import ODSensor


@pytest.fixture
def serial_mock():
    class ResponseBackendEmulator(PySerialEmulator):
        raw_response_map = {
            b'od_90r,500,_!': b'od_90a,123,456,end',
            b'od_90r,100,_!': b'od_90a,101,102,end',
        }
    class SerialEmulator(EvolverSerialUART):
        backend = ResponseBackendEmulator

    return SerialEmulator()


@pytest.fixture
def evolver_mock(serial_mock):
    e = Evolver()
    e.serial = serial_mock
    return e


@pytest.mark.parametrize("integs, expect", [(500, (123, 456)), (100, (101, 102))])
def test_od_sensor(evolver_mock, integs, expect):
    od = ODSensor(evolver_mock, ODSensor.Config(addr='od_90', integrations=integs))
    od.read()
    for vial in range(len(expect)):
        assert od.get()[vial] == ODSensor.Output(vial=vial, raw=expect[vial])



@pytest.mark.parametrize("integs, expect", [(500, (123, 456)), (100, (101, 102))])
def test_evolver_hookup(evolver_mock, serial_mock, integs, expect):
    config = {
        'hardware': {
            'od': {
                'driver': 'evolver.hardware.standard.od_sensor.ODSensor',
                'config': {
                    'addr': 'od_90',
                    'integrations': integs,
                }
            }
        }
    }
    evolver_mock.update_config(EvolverConfig.model_validate(config))
    evolver_mock.serial = serial_mock
    assert evolver_mock.state == {'od': {}}
    evolver_mock.loop_once()
    assert evolver_mock.state == {
        'od': {
            0: ODSensor.Output(vial=0, raw=expect[0]),
            1: ODSensor.Output(vial=1, raw=expect[1]),
        }
    }


