from typing import Dict, List

from evolver.calibration.action import DisplayInstructionAction
from evolver.calibration.interface import IndependentVialBasedCalibrator, Transformer
from evolver.calibration.procedure import CalibrationProcedure
from evolver.calibration.standard.actions.temperature import (
    CalculateFitAction,
    RawValueAction,
    ReferenceValueAction,
    SaveProcedureStateAction,
)
from evolver.hardware.interface import HardwareDriver


class TemperatureCalibrator(IndependentVialBasedCalibrator):
    """
    A calibrator for each vial's temperature sensor.
    """

    class CalibrationData(Transformer.Config):
        measured: Dict[int, Dict[str, List[float]]] = {}  # {vial_index: {"reference": [], "raw": []}}
        completed_actions: List[str] = []

    def create_calibration_procedure(
        self,
        selected_hardware: HardwareDriver,
        # Resume by default
        resume: bool = True,
        *args,
        **kwargs,
    ):
        # Cherrypick data persisted to Calibrator.CalibrationData, to resume the CalibrationProcedure from the last saved state.
        persisted_state = {
            **self.calibration_data.measured,
            "completed_actions": self.calibration_data.completed_actions,
        }

        calibration_procedure = (
            CalibrationProcedure(persisted_state) if resume and persisted_state else CalibrationProcedure()
        )

        calibration_procedure.add_action(
            DisplayInstructionAction(description="Fill each vial with 15ml water", name="fill_vials_instruction")
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

        calibration_procedure.add_action(
            SaveProcedureStateAction(
                hardware=selected_hardware,
                description="Save the calibration procedure state",
                name="save_calibration_procedure_state",
            )
        )

        self.calibration_procedure = calibration_procedure
