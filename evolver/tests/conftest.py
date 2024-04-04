import pytest
from evolver.device import Evolver, EvolverConfig


@pytest.fixture
def conf_with_driver():
    return {
        'vials': [0,1,2,3],
        'hardware': {
            'testsensor': {
                'driver':
                'evolver.hardware.demo.NoOpSensorDriver',
                'config': {},
                'calibrator': {
                    'driver': 'evolver.hardware.demo.NoOpCalibrator'
                }
            },
            'testeffector': {'driver': 'evolver.hardware.demo.NoOpEffectorDriver', 'config': {}},
        },
        'adapters': [
            {'driver': 'evolver.adapter.demo.NoOpAdapter'},
        ],
        'serial': { 'driver': 'evolver.serial.EchoSerial' },
    }


@pytest.fixture
def demo_evolver(conf_with_driver):
    return Evolver(EvolverConfig.model_validate(conf_with_driver))
