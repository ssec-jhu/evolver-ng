import pytest

from evolver.hardware.standard.pump import GenericPumpCalibrator
from evolver.settings import settings


@pytest.fixture(autouse=True)
def temp_cal_dir(tmp_path):
    settings.ROOT_CALIBRATOR_FILE_STORAGE_PATH = tmp_path


@pytest.fixture
def cal_data():
    return GenericPumpCalibrator.CalibrationData(
        measured={0: (10, 1), 1: (10, 5)},
    )


def test_pump_calibrator(cal_data):
    calibrator = GenericPumpCalibrator()
    # fake a set of measurements
    calibrator.load_calibration(cal_data)
    assert calibrator.input_transformer[0].convert_from(1) == pytest.approx(10)
    assert calibrator.input_transformer[1].convert_from(1) == pytest.approx(2)


def test_pump_calibrator_read_from_file(cal_data):
    cal_data.save("test_cal_data.yaml")
    calibrator = GenericPumpCalibrator(calibration_file="test_cal_data.yaml")
    print(calibrator.calibration_data)
    assert calibrator.calibration_data == cal_data
