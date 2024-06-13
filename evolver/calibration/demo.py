from typing import Any

from evolver.calibration.interface import Calibrator
from evolver.hardware.demo import NoOpSensorDriver


class NoOpCalibrator(Calibrator):
    @property
    def is_calibrated(self):
        return True

    def convert(self, data):
        return data

    def run_calibration_procedure(self, *args, **kwargs): ...


class SimpleCalibrator(Calibrator):
    class Config(Calibrator.Config):
        conversion_factor: float = 9 / 5
        conversion_constant: float = 32

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_calibrated = False

    @property
    def is_calibrated(self):
        return self._is_calibrated

    def convert(
        self, data: NoOpSensorDriver.Output | dict[Any, NoOpSensorDriver.Output]
    ) -> NoOpSensorDriver.Output | dict[int, NoOpSensorDriver.Output]:
        """Inplace calibration conversion."""

        def _convert(x):
            return x * self.conversion_factor + self.conversion_constant

        if isinstance(data, dict):
            for k, v in data.items():
                data[k].value = _convert(v.raw)
        else:
            data.value = _convert(data.raw)

        return data

    def run_calibration_procedure(self, *args, **kwargs):
        self._is_calibrated = True
