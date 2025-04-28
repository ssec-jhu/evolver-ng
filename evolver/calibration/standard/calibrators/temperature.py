from pydantic import Field

from evolver.calibration.action import DisplayInstructionAction
from evolver.calibration.interface import (
    CalibrationStateModel,
    IndependentVialBasedCalibrator,
    Transformer,
)
from evolver.calibration.procedure import CalibrationProcedure
from evolver.calibration.standard.actions.temperature import (
    RawValueAction,
    ReferenceValueAction,
)
from evolver.calibration.standard.polyfit import LinearTransformer
from evolver.hardware.interface import HardwareDriver


class TemperatureCalibrator(IndependentVialBasedCalibrator):
    """
    A calibrator for each vial's temperature sensor.
    """

    class Config(IndependentVialBasedCalibrator.Config):
        default_output_transformer: Transformer = Field(default_factory=LinearTransformer)

    def init_transformers(self, calibration_data: CalibrationStateModel):
        for vial, data in calibration_data.measured.items():
            # temperature uses convert_to so raw should be left-hand-side of transfomer
            self.get_output_transformer(vial).refit(data["raw"], data["reference"])

    def create_calibration_procedure(
        self,
        selected_hardware: HardwareDriver,
        # Resume by default
        resume: bool = True,
        *args,
        **kwargs,
    ):
        procedure_state = None
        if resume and self.procedure_file:
            procedure_state = CalibrationStateModel.load(self.procedure_file)

        calibration_procedure = CalibrationProcedure(
            state=procedure_state.model_dump() if procedure_state else None, hardware=selected_hardware
        )

        calibration_procedure.add_action(
            DisplayInstructionAction(
                description="Fill each vial with 15ml water", name="fill_vials_instruction", hardware=selected_hardware
            )
        )

        calibration_procedure.add_action(
            DisplayInstructionAction(
                description="Wait 25 mins for equilibrium",
                name="wait_for_equilibrium_instruction",
                hardware=selected_hardware,
            )
        )

        for vial in self.vials:
            calibration_procedure.add_action(
                ReferenceValueAction(
                    hardware=selected_hardware,
                    vial_idx=vial,
                    description=f"Use a thermometer to measure the real temperature in vial: {vial}.",
                    name=f"measure_vial_{vial}_temperature",
                )
            )
            calibration_procedure.add_action(
                RawValueAction(
                    hardware=selected_hardware,
                    vial_idx=vial,
                    description=f"The hardware will now read the raw output values of vial: {vial}'s temperature sensor.",
                    name=f"read_vial_{vial}_raw_output",
                )
            )

        self.calibration_procedure = calibration_procedure
