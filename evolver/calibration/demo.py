from pydantic import Field

from evolver.base import ConfigDescriptor, BaseConfig
from evolver.calibration.interface import Calibrator, Transformer


class NoOpTransformer(Transformer):
    def convert_to(self, data, *args, **kwargs):
        return data

    convert_from = convert_to


class NoOpCalibrator(Calibrator):
    class Config(Calibrator.Config):
        input_transformer: ConfigDescriptor | Transformer | None = Field(default_factory=NoOpTransformer)
        output_transformer: ConfigDescriptor | Transformer | None = Field(default_factory=NoOpTransformer)

    class State(BaseConfig):
        status: str = Field("not calibrated", description="Calibration status")

    @property
    def State(self):
        return NoOpCalibrator.State  # Return the specific State class

    def __init__(self, *args, state=None, **kwargs):
        super().__init__(*args, **kwargs)
        # If state is provided, use it, otherwise instantiate the default State
        self.state = state if state else self.State()

    def run_calibration_procedure(self, *args, **kwargs):
        # No-op calibration procedure
        pass

    def initialize_calibration_procedure(self, *args, **kwargs):
        # No-op calibration procedure
        pass
