from unittest.mock import MagicMock

import pytest

from evolver.calibration.interface import CalibrationStateModel
from evolver.calibration.standard.calibrators.pump import GenericPumpCalibrator
from evolver.hardware.standard.pump import GenericPump
from evolver.serial import SerialData
from evolver.settings import settings


@pytest.fixture(autouse=True)
def temp_cal_dir(tmp_path):
    settings.ROOT_CALIBRATOR_FILE_STORAGE_PATH = tmp_path


@pytest.fixture
def cal_data():
    return CalibrationStateModel(measured={"0": [10, 1], "1": [10, 5]})


def test_pump_calibrator(cal_data):
    calibrator = GenericPumpCalibrator()
    calibrator.load_calibration(cal_data)
    assert calibrator.input_transformer[str(0)].convert_from(1) == pytest.approx(10)
    assert calibrator.input_transformer[str(1)].convert_from(1) == pytest.approx(2)


def test_pump_calibrator_read_from_file(cal_data):
    cal_data.save("test_cal_data.yaml")
    calibrator = GenericPumpCalibrator(calibration_file="test_cal_data.yaml")
    assert calibrator.calibration_data == cal_data


@pytest.mark.parametrize("active_pumps", [None, [0, 2]])
def test_pump_calibration_procedure(active_pumps):
    calibrator = GenericPumpCalibrator()
    hardware = GenericPump(addr="pump", calibrator=calibrator, active_pumps=active_pumps)
    hardware.calibrator.create_calibration_procedure(selected_hardware=hardware, resume=False)
    procedure = hardware.calibrator.calibration_procedure

    procedure.dispatch("fill_beaker", {})
    procedure.dispatch("place_vials", {})

    hardware.serial_conn = MagicMock()
    procedure.dispatch("pump_run", {})
    # We expect the pump run to have sent the command with by default the slow
    # pump rate set on calibrator. For those pumps not active we expect the null
    # command (--) to be set for the relevant slot.
    per_pump_bytes = f"{calibrator.time_to_pump_slow}|0".encode()
    expected_cmd = SerialData(addr="pump", data=[per_pump_bytes] * hardware.slots)
    if active_pumps:
        for i in range(hardware.slots):
            if i not in active_pumps:
                expected_cmd.data[i] = b"--"
    hardware.serial_conn.__enter__().communicate.assert_called_with(expected_cmd)

    procedure.dispatch("wait_pumps", {})

    measured = 2.0
    procedure.dispatch("record_pump_0", {"volume": measured})
    assert procedure.state.measured == ({0: (calibrator.time_to_pump_slow, measured)})

    procedure.dispatch("pump_run", {"use_fast_mode": True})
    measured = 4.0
    procedure.dispatch("record_pump_2", {"volume": measured})
    assert procedure.state.measured[2] == (calibrator.time_to_pump_fast, measured)
