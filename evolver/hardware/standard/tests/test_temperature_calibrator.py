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
