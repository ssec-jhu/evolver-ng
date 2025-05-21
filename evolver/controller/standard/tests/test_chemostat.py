from unittest.mock import MagicMock

import pytest

from evolver.controller.standard import Chemostat
from evolver.device import Evolver, Experiment
from evolver.hardware.interface import EffectorDriver
from evolver.hardware.standard.pump import VialIEPump
from evolver.hardware.standard.stir import Stir


def add_mock_hardware(evolver):
    evolver.hardware = {i: MagicMock() for i in ["od", "pump", "stirrer"]}
    evolver.hardware["od"].get.return_value = {0: MagicMock(density=0), 1: MagicMock(density=1)}

    # setup mock for enabling assert on set values for effectors. Pulls out all
    # named attributes from the given input, validates against cls's Input model
    # and stores in call list upon set
    def setup_hw_mock(mock, cls):
        mock.inputs = []
        mock.Input.side_effect = lambda **a: cls.Input(**a)
        mock.set.side_effect = lambda *args, **kwargs: mock.inputs.append(
            EffectorDriver._get_input_from_args(cls, *args, **kwargs)
        )

    setup_hw_mock(evolver.hardware["pump"], VialIEPump)
    setup_hw_mock(evolver.hardware["stirrer"], Stir)


@pytest.fixture
def mock_hardware():
    evolver = Evolver()
    add_mock_hardware(evolver)
    return evolver


@pytest.mark.parametrize("window", [4, 7])
@pytest.mark.parametrize("min_od", [0, 1])
@pytest.mark.parametrize("stir_rate", [8, 9])
def test_chemostat_standard_operation(mock_hardware, window, min_od, stir_rate):
    config = Chemostat.Config(
        od_sensor="od",
        pump="pump",
        stirrer="stirrer",
        window=window,
        min_od=min_od,
        stir_rate=stir_rate,
        vial_volume=25,
        bolus_volume=0.5,
        dilution_rate=0.5,
        vials=[0, 1],
    )
    c = Chemostat(evolver=mock_hardware, **config.model_dump())
    pump = mock_hardware.hardware["pump"]
    stir = mock_hardware.hardware["stirrer"]

    # one less control than window to ensure we have not yet made a set
    for i in range(window - 1):
        c.control()

    assert pump.inputs == stir.inputs == []
    # finish filling the buffer up to window size
    c.control()

    # After window is complete, we expect to have started dilutions, where we
    # expect commands to have been sent to pump and stir
    if min_od == 0:
        assert pump.inputs == [
            VialIEPump.Input(vial=v, influx_volume=0.5, influx_rate=25.0, efflux_volume=0.5, efflux_rate=25.0)
            for v in [0, 1]
        ]
        assert stir.inputs == [Stir.Input(vial=v, stir_rate=stir_rate) for v in [0, 1]]
    else:
        # only vial 1 meets the mean OD requirements
        assert pump.inputs == [
            VialIEPump.Input(vial=1, influx_volume=0.5, influx_rate=25.0, efflux_volume=0.5, efflux_rate=25.0)
        ]
        assert stir.inputs == [Stir.Input(vial=1, stir_rate=stir_rate)]


def test_evolver_based_setup():  # test to ensure evolver pluggability via config/loop
    config = {
        "experiments": {
            "test": {
                "controllers": [
                    {
                        "classinfo": "evolver.controller.standard.Chemostat",
                        "config": {"od_sensor": "od", "pump": "pump", "stirrer": "stirrer", "vials": [0, 1]},
                    }
                ],
            }
        },
        "raise_loop_exceptions": True,
    }
    evolver = Evolver.create(config)
    with pytest.raises(KeyError):
        evolver.loop_once()
    add_mock_hardware(evolver)
    evolver.loop_once()


def test_serialize_in_experiment():
    controller = Chemostat(od_sensor="od", pump="pump", stirrer="stirrer")
    experiment = Experiment(controllers=[controller])
    experiment_dumped = experiment.model_dump()
    Chemostat.Config.model_validate(experiment_dumped["controllers"][0])
