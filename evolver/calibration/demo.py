from pydantic import Field

from evolver.base import ConfigDescriptor
from evolver.calibration.interface import Calibrator, Transformer
from evolver.calibration.procedure import CalibrationProcedure
from evolver.hardware.interface import HardwareDriver


class NoOpTransformer(Transformer):
    class Config(Transformer.Config):
        param1: float = Field(default=1.0)

    def convert_to(self, data, *args, **kwargs):
        return data

    def refit(self, *args, **kwargs):
        self._refit_args = args
        self._refit_kwargs = kwargs

    convert_from = convert_to


class NoOpCalibrator(Calibrator):
    class Config(Calibrator.Config):
        input_transformer: ConfigDescriptor | Transformer | None = Field(default_factory=NoOpTransformer)
        output_transformer: ConfigDescriptor | Transformer | None = Field(default_factory=NoOpTransformer)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def run_calibration_procedure(self, *args, **kwargs):
        # No-op calibration procedure
        pass

    def create_calibration_procedure(
        self,
        selected_hardware: HardwareDriver,
        resume: bool = False,
        *args,
        **kwargs,
    ):
        calibration_procedure = CalibrationProcedure(hardware=selected_hardware)
        self.calibration_procedure = calibration_procedure
        pass
