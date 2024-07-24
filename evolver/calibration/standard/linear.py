from evolver.hardware.demo import NoOpSensorDriver
from evolver.calibration.interface import Calibrator, Transformer


class LinearTransformer(Transformer): ...


class SimpleCalibrator(Calibrator):
    class Config(Calibrator.Config):
        conversion_factors: dict[int, float] = 9 / 5
        conversion_constants: dict[int, float] = 32

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_calibrated = False

    @property
    def is_calibrated(self):
        return self._is_calibrated

    def convert_from_raw(self, data: NoOpSensorDriver.Output) -> NoOpSensorDriver.Output:
        """Inplace calibration conversion."""
        data.value = self.conversion_constants[data.vial] + self.data.raw * self.conversion_factors[data.vial]
        return data

    def convert_to_raw(self, data: NoOpSensorDriver.Output) -> NoOpSensorDriver.Output:
        """Inplace calibration conversion."""
        data.raw = self.data.value / self.conversion_factors[data.vial] - self.conversion_constants[data.vial]
        return data

    def run_calibration_procedure(self, *args, **kwargs):
        self._is_calibrated = True
