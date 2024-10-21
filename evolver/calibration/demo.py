from pydantic import Field
from evolver.base import ConfigDescriptor
from evolver.calibration.interface import Calibrator, Transformer
from evolver.calibration.procedure import CalibrationProcedure
from evolver.calibration.standard.calibrators.temperature import TempCalibrationProcedureInitialState

from evolver.hardware.interface import HardwareDriver


class NoOpTransformer(Transformer):
    def convert_to(self, data, *args, **kwargs):
        return data

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

    def initialize_calibration_procedure(
        self,
        selected_hardware: HardwareDriver,
        initial_state: TempCalibrationProcedureInitialState,
        *args,
        **kwargs,
    ):
        calibration_procedure = CalibrationProcedure(
            "No Op Calibration Procedure ", initial_state=initial_state.model_dump()
        )
        self.calibration_procedure = calibration_procedure
        pass
