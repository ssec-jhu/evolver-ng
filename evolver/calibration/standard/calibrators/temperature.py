from evolver.calibration.actions import (
    DisplayInstructionAction,
    VialTempReferenceValueAction,
    VialTempRawVoltageAction,
    VialTempCalculateFitAction,
)
from evolver.calibration.interface import Calibrator
from evolver.calibration.procedure import CalibrationProcedure
from evolver.hardware.interface import HardwareDriver


class TemperatureCalibrator(Calibrator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state = {"selected_vials": []}

    def initialize_calibration_procedure(
        self,
        selected_hardware: HardwareDriver,
        selected_vials: list[int],
        evolver=None,
        *args,
        **kwargs,
    ):
        # TODO: integrate self.state with self.CalibrationData, see Arik & Iain for context.
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

        # Add a final step to calculate the fit.
        for vial in self.state["selected_vials"]:
            calibration_procedure.add_action(
                VialTempCalculateFitAction(
                    hardware=selected_hardware,
                    vial_idx=vial,
                    description="Use the real and raw values that have been collected to calculate the fit for the temperature sensor",
                    name=f"Vial_{vial}_Temp_Calculate_Fit_Action",
                )
            )
        self.calibration_procedure = calibration_procedure
