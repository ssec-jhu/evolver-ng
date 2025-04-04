from pathlib import Path

from evolver.calibration.action import DisplayInstructionAction
from evolver.calibration.interface import (
    CalibrationStateModel,
    IndependentVialBasedCalibrator,
    root_calibrator_file_storage_path,
)
from evolver.calibration.procedure import CalibrationProcedure
from evolver.calibration.standard.actions.temperature import (
    CalculateFitAction,
    RawValueAction,
    ReferenceValueAction,
)
from evolver.hardware.interface import HardwareDriver


class TemperatureCalibrator(IndependentVialBasedCalibrator):
    """
    A calibrator for each vial's temperature sensor.
    """

    def init_transformers(self, calibration_data: CalibrationStateModel):
        for vial, data in calibration_data.measured.items():
            self.get_output_transformer(vial).refit(data["reference"], data["raw"])

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
            # Check if procedure_file is an absolute path
            if Path(self.procedure_file).is_absolute():
                procedure_file_path = self.procedure_file
            else:
                # Use self.dir if defined, otherwise use the default storage path
                procedure_dir = getattr(self, "dir", root_calibrator_file_storage_path())
                procedure_file_path = procedure_dir / self.procedure_file

            procedure_state = CalibrationStateModel.load(procedure_file_path)

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

        for vial in self.vials:
            calibration_procedure.add_action(
                CalculateFitAction(
                    hardware=selected_hardware,
                    vial_idx=vial,
                    description=f"Calculate the fit for the vial: {vial}'s temperature sensor",
                    name=f"calculate_vial_{vial}_fit",
                )
            )

        self.calibration_procedure = calibration_procedure
