import pytest
from evolver.device import Evolver, EvolverConfig
from evolver.hardware import NoOpSensorDriver


@pytest.fixture
def conf_with_driver():
    return {
        'vials': [0,1,2,3],
        'hardware': {
            'testsensor': {'driver': 'evolver.hardware.NoOpSensorDriver', 'config': {}},
            'testeffector': {'driver': 'evolver.hardware.NoOpEffectorDriver', 'config': {}},
        }
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
    state = demo_evolver.get_state()
    assert state['testsensor'] == {}
    getattr(demo_evolver, method)()
    state = demo_evolver.get_state()
    for vial in demo_evolver.config.vials:
        assert state['testsensor'][vial] == NoOpSensorDriver.Output(vial=vial, raw=1, value=2)
