import random
from datetime import datetime, timedelta

import pytest

from evolver.calibration.standard.linear import SimpleCalibrator
from evolver.hardware.demo import NoOpSensorDriver
from evolver.settings import settings


class TestCalibrator:
    def test_config_save(self, tmp_path):
        obj = SimpleCalibrator(dir=tmp_path)
        filename = obj.config_model.save().stem
        filename_date = filename.split("_", maxsplit=1)[1]
        date = datetime.strptime(filename_date, settings.DATETIME_PATH_FORMAT)
        assert (datetime.now() - date) < timedelta(hours=1)

    def test_is_calibrated(self):
        obj = SimpleCalibrator()
        assert not obj.is_calibrated
        obj.run_calibration_procedure()
        assert obj.is_calibrated

    def test_conversion(self):
        obj = SimpleCalibrator()
        assert not obj.is_calibrated

        raw = 10
        data = NoOpSensorDriver.Output(raw=raw, vial=1)
        assert data.value is None
        calibrated_data = obj.convert(data)
        assert calibrated_data is data
        assert calibrated_data.raw == raw
        assert calibrated_data.value == pytest.approx(raw * 9 / 5 + 32)

    def test_conversion_dict(self):
        obj = SimpleCalibrator()
        assert not obj.is_calibrated

        length = 16
        data = {i: NoOpSensorDriver.Output(raw=x, vial=i) for i, x in enumerate(random.sample(range(1, 100), length))}
        calibrated_data = obj.convert(data)
        assert calibrated_data is data
        assert len(calibrated_data) == length
        config = obj.config_model
        for v in calibrated_data.values():
            assert v.value == pytest.approx(v.raw * config.conversion_factor + config.conversion_constant)

    def test_calibrate_decorator(self):
        obj = NoOpSensorDriver(calibrator=SimpleCalibrator())
        assert obj.calibrator
        assert not obj.calibrator.is_calibrated
        obj.read()
        data = obj.get()
        assert data is obj.outputs
        assert isinstance(data, dict)
        uncalibrated_value = obj.config_model.echo_val
        for v in data.values():
            assert isinstance(v, NoOpSensorDriver.Output)
            assert v.raw == obj.config_model.echo_raw
            assert v.value == uncalibrated_value

        obj.calibrator.run_calibration_procedure()
        assert obj.calibrator.is_calibrated

        data = obj.get()
        assert data is obj.outputs
        assert isinstance(data, dict)
        config = obj.calibrator.config_model
        for v in data.values():
            assert isinstance(v, NoOpSensorDriver.Output)
            assert v.raw == obj.config_model.echo_raw
            assert v.value == pytest.approx(v.raw * config.conversion_factor + config.conversion_constant)
