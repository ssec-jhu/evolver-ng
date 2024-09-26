import pytest

from evolver.hardware.standard.pump import GenericPumpCalibrator
from evolver.settings import settings


@pytest.fixture(autouse=True)
def temp_cal_dir(tmp_path):
    settings.ROOT_CALIBRATOR_FILE_STORAGE_PATH = tmp_path


@pytest.fixture
def cal_data():
    return GenericPumpCalibrator.CalibrationData(
        time_to_pump=10.0, measured={0: ([1, 2, 3], [1, 2, 3]), 1: ([4, 5, 6], [7, 8, 9])}
    )


def test_pump_calibrator(cal_data):
    calibrator = GenericPumpCalibrator()
    # fake a set of measurements
    calibrator.load_calibration(cal_data)
    assert calibrator.input_transformer[0].convert_from(2) == pytest.approx(2)
    assert calibrator.input_transformer[1].convert_from(8) == pytest.approx(5)
    assert calibrator.time_to_pump == cal_data.time_to_pump


def test_pump_calibrator_read_from_file(cal_data):
    cal_data.save("test_cal_data.yaml")
    calibrator = GenericPumpCalibrator(calibration_file="test_cal_data.yaml")
    assert calibrator.cal_data == cal_data
