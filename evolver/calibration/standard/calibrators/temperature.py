from typing import Dict

from evolver.calibration.action import DisplayInstructionAction
from evolver.calibration.interface import IndependentVialBasedCalibrator
from evolver.calibration.procedure import CalibrationProcedure
from evolver.calibration.standard.actions.temperature import (
    CalculateFitAction,
    ProcedureState,
    RawValueAction,
    ReferenceValueAction,
    SaveProcedureStateAction,
)
from evolver.calibration.standard.polyfit import LinearTransformer
from evolver.hardware.interface import HardwareDriver


class TemperatureCalibrator(IndependentVialBasedCalibrator):
    def __init__(self, input_transformer=None, output_transformer=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.input_transformer = {}
        self.output_transformer = {}
        self.default_input_transformer = input_transformer or LinearTransformer()
        self.default_output_transformer = output_transformer or LinearTransformer()

    def initialize_calibration_procedure(
        self,
        selected_hardware: HardwareDriver,
        initial_state: Dict,
        *args,
        **kwargs,
    ):
        try:
            initial_state = ProcedureState.model_validate(initial_state)
        except TypeError:
            raise ValueError(
                "Calibration procedure initial state is invalid, procedure must be initialized with a list of vials that the procedure will run on"
            )

        selected_vials = initial_state.selected_vials

        for vial in selected_vials:
            self.input_transformer[vial] = self.default_input_transformer
            self.output_transformer[vial] = self.default_output_transformer

        calibration_procedure = CalibrationProcedure("Temperature Calibration", initial_state=initial_state)
        calibration_procedure.add_action(
            DisplayInstructionAction(description="Fill each vial with 15ml water", name="Fill_Vials_With_Water")
        )
        for vial in selected_vials:
            calibration_procedure.add_action(
                ReferenceValueAction(
                    hardware=selected_hardware,
                    vial_idx=vial,
                    description=f"Use a thermometer to measure the real temperature in the vial {vial}",
                    name=f"Vial_{vial}_Temp_Reference_Value_Action",
                )
            )
            calibration_procedure.add_action(
                RawValueAction(
                    hardware=selected_hardware,
                    vial_idx=vial,
                    description=f"The hardware will now read the raw voltage from the temperature sensor, vial {vial}",
                    name=f"Vial_{vial}_Temp_Raw_Voltage_Action",
                )
            )

        for vial in selected_vials:
            calibration_procedure.add_action(
                CalculateFitAction(
                    hardware=selected_hardware,
                    vial_idx=vial,
                    description="Use the real and raw values that have been collected to calculate the fit for the temperature sensor",
                    name=f"Vial_{vial}_Temp_Calculate_Fit_Action",
                )
            )

        calibration_procedure.add_action(
            SaveProcedureStateAction(
                hardware=selected_hardware,
                description="Save the calibration procedure state",
                name="Save_Calibration_Procedure_State_Action",
            )
        )

        self.calibration_procedure = calibration_procedure
