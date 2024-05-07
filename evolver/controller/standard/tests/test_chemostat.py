import pytest
from unittest.mock import MagicMock
from evolver.controller.standard import Chemostat
from evolver.device import Evolver, EvolverConfig


def add_mock_hardware(evolver):
    evolver.hardware = {i: MagicMock() for i in ['od', 'pump', 'stirrer']}
    evolver.hardware['od'].get.return_value = {0: MagicMock(density=0), 1: MagicMock(density=1)}
    # setup mock for enabling assert on set values for effectors. Pulls out all
    # named attributes from the given input and stores in call list upon set
    def setup_hw_mock(mock):
        mock.inputs = []
        mock.Input.side_effect = lambda **a: a
        mock.set.side_effect = lambda a: mock.inputs.append(a)
    setup_hw_mock(evolver.hardware['pump'])
    setup_hw_mock(evolver.hardware['stirrer'])


@pytest.fixture
def mock_hardware():
    evolver = Evolver()
    add_mock_hardware(evolver)
    return evolver


@pytest.mark.parametrize('window', [4,7])
@pytest.mark.parametrize('min_od', [0, 1])
@pytest.mark.parametrize('stir_rate,flow_rate', [(1,2), (9.9, 10.1)])
def test_chemostat_standard_operation(mock_hardware, window, min_od, stir_rate, flow_rate):
    config = Chemostat.Config(
        od_sensor='od',
        pump='pump',
        stirrer='stirrer',
        window=window,
        min_od=min_od,
        stir_rate=stir_rate,
        flow_rate=flow_rate,
    )
    c = Chemostat(mock_hardware, config)
    pump = mock_hardware.hardware['pump']
    stir = mock_hardware.hardware['stirrer']

    # one less control than window to ensure we have not yet made a set
    for i in range(window - 1):
        c.control()

    assert pump.inputs == stir.inputs == []
    # finish filling the buffer up to window size
    c.control()

    # After window is complete, we expect to have started dilutions, where we
    # expect commands to have been sent to pump and stir
    if min_od == 0:
        assert pump.inputs == [{'vial': 0, 'flow_rate': flow_rate}, {'vial': 1, 'flow_rate': flow_rate}]
        assert stir.inputs == [{'vial': 0, 'stir_rate': stir_rate}, {'vial': 1, 'stir_rate': stir_rate}]
    else:
        # only vial 1 meets the mean OD requirements
        assert pump.inputs == [{'vial': 1, 'flow_rate': flow_rate}]
        assert stir.inputs == [{'vial': 1, 'stir_rate': stir_rate}]


def test_evolver_based_setup():  # test to ensure evolver pluggability via config/loop
    config = {
        'controllers': [
            {
                'driver': 'evolver.controller.standard.Chemostat',
                'config': {
                    'od_sensor': 'od',
                    'pump': 'pump',
                    'stirrer': 'stirrer',
                }
            }
        ]
    }
    evolver = Evolver(EvolverConfig.model_validate(config))
    with pytest.raises(AttributeError):
        evolver.loop_once()
    add_mock_hardware(evolver)
    evolver.loop_once()
