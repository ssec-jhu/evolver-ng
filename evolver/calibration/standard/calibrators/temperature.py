from pydantic import Field

from evolver.calibration.action import DisplayInstructionAction
from evolver.calibration.interface import (
    CalibrationStateModel,
    IndependentVialBasedCalibrator,
    Transformer,
)
from evolver.calibration.procedure import CalibrationProcedure
from evolver.calibration.standard.actions.temperature import (
    AllVialsAdjustHeaterAction,
    AllVialsHeaterOffAction,
    AllVialsReadRoomTempAction,
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
        num_temp_readings: int = Field(
            3, description="Number of times reference temperature readings are taken from each vial."
        )
        heater_boundary_low: int = Field(0, description="Lower bound for heater adjustment range in raw units.")
        heater_boundary_high: int = Field(1000, description="Upper bound for heater adjustment range in raw units.")
        heater_slope_init: float = Field(
            0.02, description="Initial slope approximation for heater in (degrees C)/(raw unit)"
        )

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

        for i in range(self.num_temp_readings):
            if i == 0:
                calibration_procedure.add_action(
                    AllVialsHeaterOffAction(
                        name="vial_sweep_0_turn_off_heaters",
                        vials=self.vials,
                        description="Begin sweep for room temperature. Heaters for calibrating vials will be turned off.",
                        hardware=selected_hardware,
                    )
                )
            else:
                # We adjust heaters relative to room temperature evenly in the
                # configured range per step.
                adjustment = (
                    -1 * i * (self.heater_boundary_high - self.heater_boundary_low) / (self.num_temp_readings - 1)
                )
                approx_delta = -1 * self.heater_slope_init * adjustment  # This is just for display purposes
                calibration_procedure.add_action(
                    AllVialsAdjustHeaterAction(
                        name=f"vial_sweep_{i}_adjust_heaters",
                        vials=self.vials,
                        raw_adjustment=adjustment,
                        description=(
                            f"Begin sweep for temperature wave {i + 1}/{self.num_temp_readings}."
                            f"Will set heaters to approximately room temp +{approx_delta:0.2f} C"
                        ),
                        hardware=selected_hardware,
                    )
                )

            calibration_procedure.add_action(
                DisplayInstructionAction(
                    description="Wait for global equilibrium. This may take several hours. Proceed when reached.",
                    name=f"vial_sweep_{i}_wait_for_equilibrium_instruction",
                    hardware=selected_hardware,
                )
            )

            if i == 0:
                calibration_procedure.add_action(
                    AllVialsReadRoomTempAction(
                        name="vial_sweep_0_read_room_temp",
                        vials=self.vials,
                        description="The hardware will now read the raw output values of the room temperature sensor.",
                        hardware=selected_hardware,
                    )
                )

            for vial in self.vials:
                calibration_procedure.add_action(
                    ReferenceValueAction(
                        hardware=selected_hardware,
                        vial_idx=vial,
                        description=f"Use a thermometer to measure the real temperature in vial: {vial}.",
                        name=f"vial_sweep_{i}_measure_vial_{vial}_temperature",
                    )
                )
                calibration_procedure.add_action(
                    RawValueAction(
                        hardware=selected_hardware,
                        vial_idx=vial,
                        description=f"The hardware will now read the raw output values of vial: {vial}'s temperature sensor.",
                        name=f"vial_sweep_{i}_read_vial_{vial}_raw_output",
                    )
                )

        self.calibration_procedure = calibration_procedure
