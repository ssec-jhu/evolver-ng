from datetime import datetime, timedelta

from evolver.calibration.demo import NoOpCalibrator, NoOpTransformer
from evolver.calibration.interface import Status
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
