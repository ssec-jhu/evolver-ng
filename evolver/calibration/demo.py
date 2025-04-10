from pydantic import Field

from evolver.base import ConfigDescriptor
from evolver.calibration.interface import CalibrationStateModel, Calibrator, Transformer
from evolver.calibration.procedure import CalibrationProcedure
from evolver.hardware.interface import HardwareDriver


class NoOpTransformer(Transformer):
    class Config(Transformer.Config):
        param1: float = Field(default=1.0)

    def convert_to(self, data, *args, **kwargs):
        return data

    def convert_from(self, data, *args, **kwargs):
        return data

    def refit(self, *args, **kwargs):
        self._refit_args = args
        self._refit_kwargs = kwargs


class NoOpCalibrator(Calibrator):
    class Config(Calibrator.Config):
        input_transformer: ConfigDescriptor | Transformer | None = Field(default_factory=NoOpTransformer)
        output_transformer: ConfigDescriptor | Transformer | None = Field(default_factory=NoOpTransformer)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Ensure transformers are properly initialized instances of NoOpTransformer
        if isinstance(self.input_transformer, dict):
            # Handle the case where input_transformer is a dictionary for vial-based calibrators
            for vial, transformer in self.input_transformer.items():
                if isinstance(transformer, NoOpTransformer.Config):
                    self.input_transformer[vial] = NoOpTransformer(**transformer.model_dump())
                elif transformer is None:
                    self.input_transformer[vial] = NoOpTransformer()
        elif isinstance(self.input_transformer, NoOpTransformer.Config):
            self.input_transformer = NoOpTransformer(**self.input_transformer.model_dump())
        elif self.input_transformer is None:
            self.input_transformer = NoOpTransformer()

        if isinstance(self.output_transformer, dict):
            # Handle the case where output_transformer is a dictionary for vial-based calibrators
            for vial, transformer in self.output_transformer.items():
                if isinstance(transformer, NoOpTransformer.Config):
                    self.output_transformer[vial] = NoOpTransformer(**transformer.model_dump())
                elif transformer is None:
                    self.output_transformer[vial] = NoOpTransformer()
        elif isinstance(self.output_transformer, NoOpTransformer.Config):
            self.output_transformer = NoOpTransformer(**self.output_transformer.model_dump())
        elif self.output_transformer is None:
            self.output_transformer = NoOpTransformer()

    def init_transformers(self, calibration_data: CalibrationStateModel):
        """Initialize transformers from calibration data."""
        # For testing, we'll create a new transformer with a different param1 value
        # This simulates what would happen in a real calibrator's init_transformers method
        self.input_transformer = NoOpTransformer()
        self.output_transformer = NoOpTransformer()

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
