from evolver.calibration.actions import (
    DisplayInstructionAction,
    SaveCalibrationProcedureStateAction,
    VialTempCalculateFitAction,
    VialTempRawVoltageAction,
    VialTempReferenceValueAction,
)
from evolver.calibration.procedure import CalibrationProcedure
from evolver.calibration.standard.polyfit import LinearCalibrator, LinearTransformer
from evolver.hardware.interface import HardwareDriver


class TemperatureCalibrator(LinearCalibrator):
    def __init__(self, input_transformer=None, output_transformer=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state = {"selected_vials": []}
        self.Config.input_transformer = input_transformer or LinearTransformer()
        self.Config.output_transformer = output_transformer or LinearTransformer()

    def initialize_calibration_procedure(
        self,
        selected_hardware: HardwareDriver,
        selected_vials: list[int],
        *args,
        **kwargs,
    ):
        self.state["selected_vials"] = selected_vials

        calibration_procedure = CalibrationProcedure("Temperature Calibration")
        calibration_procedure.add_action(
            DisplayInstructionAction(description="Fill each vial with 15ml water", name="Fill_Vials_With_Water")
        )
        for vial in self.state["selected_vials"]:
            calibration_procedure.add_action(
                VialTempReferenceValueAction(
                    hardware=selected_hardware,
                    vial_idx=vial,
                    description=f"Use a thermometer to measure the real temperature in the vial {vial}",
                    name=f"Vial_{vial}_Temp_Reference_Value_Action",
                )
            )
            calibration_procedure.add_action(
                VialTempRawVoltageAction(
                    hardware=selected_hardware,
                    vial_idx=vial,
                    description=f"The hardware will now read the raw voltage from the temperature sensor, vial {vial}",
                    name=f"Vial_{vial}_Temp_Raw_Voltage_Action",
                )
            )

        for vial in self.state["selected_vials"]:
            calibration_procedure.add_action(
                VialTempCalculateFitAction(
                    hardware=selected_hardware,
                    vial_idx=vial,
                    description="Use the real and raw values that have been collected to calculate the fit for the temperature sensor",
                    name=f"Vial_{vial}_Temp_Calculate_Fit_Action",
                )
            )

        calibration_procedure.add_action(
            SaveCalibrationProcedureStateAction(
                hardware=selected_hardware,
                description="Save the calibration procedure state",
                name="Save_Calibration_Procedure_State_Action",
            )
        )

        self.calibration_procedure = calibration_procedure
