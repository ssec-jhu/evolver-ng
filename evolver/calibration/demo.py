from evolver.base import ConfigDescriptor
from evolver.calibration.interface import Calibrator, Transformer


class NoOpTransformer(Transformer):
    def convert_to(self, data, *args, **kwargs):
        return data

    convert_from = convert_to


class NoOpCalibrator(Calibrator):
    class Config(Calibrator.Config):
        input_transformer: ConfigDescriptor | Transformer | None = NoOpTransformer()
        output_transformer: ConfigDescriptor | Transformer | None = NoOpTransformer()

    def run_calibration_procedure(self, *args, **kwargs): ...
