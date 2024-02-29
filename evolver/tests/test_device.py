import pytest
from evolver.device import Evolver, EvolverConfig
from evolver.hardware import NoOpSensorDriver


@pytest.fixture
def conf_with_driver():
    return {
        'vials': [0,1,2,3],
        'hardware': {
            'testsensor': {
                'driver':
                'evolver.hardware.NoOpSensorDriver',
                'config': {},
                'calibrator': {
                    'driver': 'evolver.hardware.NoOpCalibrator'
                }
            },
            'testeffector': {'driver': 'evolver.hardware.NoOpEffectorDriver', 'config': {}},
        },
        'adapters': [
            {'driver': 'evolver.adapter.NoOpAdapter'},
        ],
        'serial': { 'driver': 'evolver.serial.EchoSerial' },
    }


@pytest.fixture
def demo_evolver(conf_with_driver):
    return Evolver(EvolverConfig.model_validate(conf_with_driver))


def test_evolver_instantiate_with_default_config():
    conf = EvolverConfig()
    evolver = Evolver()
    evolver.update_config(conf)
    Evolver(conf)


def test_evolver_with_driver(demo_evolver):
    assert isinstance(demo_evolver.hardware['testsensor'], NoOpSensorDriver)


@pytest.mark.parametrize('method', ['read_state', 'loop_once'])
def test_evolver_read_and_get_state(demo_evolver, method):
    state = demo_evolver.state
    assert state['testsensor'] == {}
    getattr(demo_evolver, method)()
    state = demo_evolver.state
    for vial in demo_evolver.config.vials:
        assert state['testsensor'][vial] == NoOpSensorDriver.Output(vial=vial, raw=1, value=2)


@pytest.mark.parametrize('enable_react', [True, False])
def test_evolver_adapter_react_in_loop_if_configured(demo_evolver, enable_react):
    assert demo_evolver.adapters[0].ncalls == 0
    demo_evolver.config.enable_react = enable_react
    demo_evolver.loop_once()
    assert demo_evolver.adapters[0].ncalls == (1 if enable_react else 0)


def test_evolver_remove_driver(demo_evolver, conf_with_driver):
    assert 'testeffector' in demo_evolver.hardware
    del(conf_with_driver['hardware']['testeffector'])
    demo_evolver.update_config(EvolverConfig.model_validate(conf_with_driver))
    assert 'testeffector' not in demo_evolver.hardware
