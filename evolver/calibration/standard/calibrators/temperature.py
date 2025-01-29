from typing import Dict, List

from evolver.calibration.action import DisplayInstructionAction
from evolver.calibration.interface import Calibrator, IndependentVialBasedCalibrator
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

    class CalibrationData(Calibrator.CalibrationData):
        measured: Dict[int, Dict[str, List[float]]] = {}  # {vial_index: {"reference": [], "raw": []}}

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
            CalibrationProcedure(state=persisted_state, hardware=selected_hardware)
            if resume and persisted_state
            else CalibrationProcedure(hardware=selected_hardware)
        )

        calibration_procedure.add_action(
            DisplayInstructionAction(
                description="Fill each vial with 15ml water", name="fill_vials_instruction", hardware=selected_hardware
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
