import pytest
from evolver.adapter.demo import NoOpVialAdapter
from evolver.vial import Vial


@pytest.mark.parametrize('vials', [range(2), range(4)])
def test_vial_adapter(demo_evolver, vials):
    adapter = NoOpVialAdapter(demo_evolver, NoOpVialAdapter.Config(vials=vials))
    adapter.react()
    assert adapter.ncalls == len(vials)
    assert all(isinstance(i, Vial) for i in adapter.called_vials)
