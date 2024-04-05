import pytest
from evolver.device import Evolver, HardwareDriverDescriptor
from evolver.hardware.demo import NoOpEffectorDriver, NoOpSensorDriver
from evolver.vial import VialView, EvolverVialView


@pytest.fixture
def hardware_map():
    ev = Evolver()
    hw = {'effector': NoOpEffectorDriver(ev), 'sensor': NoOpSensorDriver(ev)}
    hw['sensor'].read()
    return hw


@pytest.mark.parametrize('vial', [1,2])
def test_vial_view_get(hardware_map, vial):
    v = VialView(vial, hardware_map)
    assert v.get('sensor') == NoOpSensorDriver.Output(vial=vial, raw=1, value=2.0)


@pytest.mark.parametrize('vial', [1,2])
def test_vial_view_set(hardware_map, vial):
    v = VialView(vial, hardware_map)
    v.set('effector', {'value': 999})
    assert NoOpEffectorDriver.Input(vial=vial, value=999) == hardware_map['effector'].proposal[vial]


def test_vial_view_for_missing_hardware_raises(hardware_map):
    with pytest.raises(KeyError):
        VialView(1, hardware_map).get('missing')


def test_vial_view_missing_vial_raises(hardware_map):
    v = VialView(100, hardware_map)
    with pytest.raises(KeyError):
        v.get('sensor')


def test_vial_view_hardware_inspect(hardware_map):
    v = VialView(1, hardware_map)
    assert 'sensor' in v.hardware
    assert 'missing' not in v.hardware
    v = VialView(100, hardware_map)
    assert 'sensor' not in v.hardware


def test_evolver_vial_view(demo_evolver):
    v = EvolverVialView(1, demo_evolver)
    assert 'testsensor' in v.hardware
    demo_evolver.read_state()
    assert v.get('testsensor') == NoOpSensorDriver.Output(vial=1, raw=1, value=2)
    # ensure our existing view is still valid after update
    assert 'newsensor' not in v.hardware
    with pytest.raises(KeyError):
        v.get('newsensor')
    demo_evolver.setup_driver(
        'newsensor',
        HardwareDriverDescriptor(driver='evolver.hardware.demo.NoOpSensorDriver', config={'echo_raw': 99}))
    demo_evolver.read_state()
    assert v.get('newsensor') == NoOpSensorDriver.Output(vial=1, raw=99, value=2)
