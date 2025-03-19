from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from evolver.calibration.demo import NoOpCalibrator, NoOpTransformer
from evolver.calibration.interface import CalibrationStateModel, IndependentVialBasedCalibrator, Status
from evolver.hardware.demo import NoOpSensorDriver
from evolver.settings import settings

# Note: Functionality not tested here is tested in evolver/calibration/standard/tests/test_fitter.py.


class TestStatus:
    def test_defaults(self):
        obj = Status()
        assert obj.expire
        assert obj.delta < timedelta(seconds=5)
        assert obj.created - datetime.now() < timedelta(seconds=5)
        assert obj.ok

    def test_expire(self):
        obj = Status(created=datetime.now() - timedelta(minutes=60), expire=timedelta(minutes=50))
        assert obj.delta >= timedelta(minutes=10)
        assert not obj.ok


class TestTransformer:
    def test_config_save(self, tmp_path):
        obj = NoOpTransformer(dir=tmp_path)
        filename = obj.config_model.save().stem
        filename_date = filename.split("_", maxsplit=1)[1]
        date = datetime.strptime(filename_date, settings.DATETIME_PATH_FORMAT)
        assert (datetime.now() - date) < timedelta(hours=1)

    def test_status(self):
        t0 = datetime.now()
        obj = NoOpTransformer()
        status = obj.status
        assert isinstance(status, Status)
        assert obj.created == status.created
        assert obj.expire == status.expire
        assert status.ok
        assert status.created > t0


class TestCalibrator:
    def test_conversion(self):
        obj = NoOpCalibrator()
        data = NoOpSensorDriver.Output(vial=1, raw=1, value=2, name="test")
        calibrated_data = obj.output_transformer.convert_to(data)
        assert calibrated_data is data

    def test_creation_timestamp(self):
        t0 = datetime.now()

        hardware = {
            "test_hardware1": NoOpSensorDriver(calibrator=NoOpCalibrator()),
            "test_hardware2": NoOpSensorDriver(calibrator=NoOpCalibrator()),
        }

        for _, device in hardware.items():
            for transformer in ("input_transformer", "output_transformer"):
                assert t0 < getattr(device.calibrator, transformer).created

    def test_calibrator_load_from_file_actions(self, tmp_path, monkeypatch):
        calibrator = NoOpCalibrator()
        # ensure that the parameter value is changed from default
        calibrator.output_transformer.param1 += 1.0
        cal_file = tmp_path / "calibration_state.yaml"

        # save without measurements, default would be to load cached
        CalibrationStateModel(fitted_calibrator=calibrator).save(cal_file)
        new_calibrator = NoOpCalibrator(calibration_file=cal_file)
        assert new_calibrator.output_transformer.param1 == calibrator.output_transformer.param1

        # save with measurements, should not load cached but instead call init_transformers
        CalibrationStateModel(fitted_calibrator=calibrator, measured={0: {"reference": [1.0], "raw": [2.0]}}).save(
            cal_file
        )
        with monkeypatch.context() as m:
            m.setattr(NoOpCalibrator, "init_transformers", MagicMock())
            new_calibrator = NoOpCalibrator(calibration_file=cal_file)
            assert new_calibrator.output_transformer.param1 != calibrator.output_transformer.param1
            assert new_calibrator.init_transformers.called

        # same as above, but set the no_refit flag
        new_calibrator = NoOpCalibrator(calibration_file=cal_file, no_refit=True)
        assert new_calibrator.output_transformer.param1 == calibrator.output_transformer.param1

        CalibrationStateModel().save(cal_file)
        with pytest.raises(ValueError, match="must have a fitted calibrator"):
            new_calibrator = NoOpCalibrator(calibration_file=cal_file)

    def test_default_transformer(self):
        class TestCalibrator(IndependentVialBasedCalibrator):
            def create_calibration_procedure(self, *args, **kwargs):
                pass

        obj = TestCalibrator(
            default_input_transformer=NoOpTransformer(param1=1.0),
            input_transformer={
                0: NoOpTransformer(param1=2.0),
            },
        )
        assert obj.get_input_transformer("0").param1 == 2.0
        assert obj.get_input_transformer(0).param1 == 2.0
        assert obj.get_input_transformer("1").param1 == 1.0
        assert obj.get_input_transformer(1).param1 == 1.0

    def test_error_on_procedure_file_is_calibration_file(self, tmp_path):
        with pytest.raises(ValueError, match="procedure_file must not be set to the same"):
            NoOpCalibrator(procedure_file="x", calibration_file="x")
        # both being unspecified should be OK
        NoOpCalibrator(procedure_file=None, calibration_file=None)
        # procedure file different from cal file, here we need a realistic cal
        # file to avoid error from that.
        cal_file = tmp_path / "calibration_state.yaml"
        CalibrationStateModel(fitted_calibrator=NoOpCalibrator()).save(cal_file)
        NoOpCalibrator(procedure_file="x", calibration_file=cal_file)

    def test_transform_fallback_on_exception(self):
        hw = NoOpSensorDriver(calibrator=NoOpCalibrator())
        class ErrorTX:
            def convert_to(self, *args, **kwargs):
                raise ValueError("test")
        hw.calibrator.output_transformer = ErrorTX()
        hw.read()
        assert hw.get()[0].value is None
