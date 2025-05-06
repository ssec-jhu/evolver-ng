from unittest.mock import MagicMock

import pytest

from evolver.calibration.demo import NoOpTransformer
from evolver.calibration.interface import CalibrationStateModel
from evolver.calibration.standard.calibrators.temperature import TemperatureCalibrator


@pytest.fixture
def temperature_calibration_file(tmp_path):
    measured = {
        "0": {"reference": 0, "raw": 1},
        "1": {"reference": 99, "raw": 100},
    }
    CalibrationStateModel(measured=measured).save(tmp_path / "temperature_calibration_file.yaml")
    return tmp_path / "temperature_calibration_file.yaml"


def test_temperature_initialization_refit(temperature_calibration_file):
    calibrator = TemperatureCalibrator(
        calibration_file=temperature_calibration_file,
        default_output_transformer=NoOpTransformer(param1=1.0),
    )
    # we expect the measured raw and reference to be passed to the refit method
    # of transformers as (reference, raw) tuple args.
    assert calibrator.get_output_transformer(0)._refit_args == (1, 0)
    assert calibrator.get_output_transformer(1)._refit_args == (100, 99)


def test_temperature_calibrator_effector_actions():
    mock_hardware = MagicMock()
    calibrator = TemperatureCalibrator(vials=[0])
    calibrator.create_calibration_procedure(selected_hardware=mock_hardware)
    procedure = calibrator.calibration_procedure
    # room temp - turn heaters off
    action = procedure.get_action("vial_sweep_0_turn_off_heaters")
    action.execute(state=None)
    mock_hardware.set.assert_called_with(vial=0, temperature=None, raw=None)
    # temp 1
    state = CalibrationStateModel(measured={0: {"raw": [2000]}})
    action = procedure.get_action("vial_sweep_1_adjust_heaters")
    action.execute(state=state)
    mock_hardware.set.assert_called_with(vial=0, temperature=None, raw=1500)
    # temp 2
    action = procedure.get_action("vial_sweep_2_adjust_heaters")
    action.execute(state=state)
    mock_hardware.set.assert_called_with(vial=0, temperature=None, raw=1000)
