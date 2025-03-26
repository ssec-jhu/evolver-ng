from pydantic import BaseModel, Field

from evolver.calibration.action import CalibrationAction, DisplayInstructionAction
from evolver.calibration.interface import CalibrationStateModel, IndependentVialBasedCalibrator, Transformer
from evolver.calibration.procedure import CalibrationProcedure


class RateTransformer(Transformer):
    class Config(Transformer.Config):
        rate: float

    def convert_to(self, time):  # convert to volume from time
        return self.rate * time

    def convert_from(self, volume):  # convert to time from volume
        return volume / self.rate


class PumpAction(CalibrationAction):
    """Run the pump for the configured time.

    The action takes as input a flag for running in fast mode, the times of
    which are configured in the constructor fast/slow args (in seconds).
    """

    def __init__(self, *args, fast, slow, **kwargs):
        super().__init__(*args, **kwargs)
        self.pump_speeds = (slow, fast)

    class FormModel(BaseModel):
        use_fast_mode: bool = Field(False, description="Use fast mode for calibration?")

    def execute(self, state, payload):
        state.time_pumped = self.pump_speeds[payload.use_fast_mode]
        for pump_id in self.hardware.pump_ids:
            self.hardware.set(pump_id=pump_id, time=state.time_pumped)
        self.hardware.commit()
        return state


class RecordVolumeAction(CalibrationAction):
    """Record volume pumped in mL for a given pump."""

    class FormModel(BaseModel):
        volume: float = Field(description="Volume pumped in mL")

    def __init__(self, *args, pump_id, **kwargs):
        super().__init__(*args, **kwargs)
        self.pump_id = pump_id

    def execute(self, state, payload):
        state.measured[self.pump_id] = (state.time_pumped, payload.volume)
        return state


class GenericPumpCalibrator(IndependentVialBasedCalibrator):
    class Config(IndependentVialBasedCalibrator.Config):
        time_to_pump_fast: float = 10.0
        time_to_pump_slow: float = 100.0

    def init_transformers(self, calibration_data):
        self.input_transformer = {}
        for vial, (time, volume) in calibration_data.measured.items():
            self.input_transformer[vial] = RateTransformer(rate=volume / time)

    def create_calibration_procedure(self, selected_hardware, resume, *args, **kwargs):
        procedure_state = CalibrationStateModel.load(self.procedure_file) if resume else None
        procedure = CalibrationProcedure(
            state=procedure_state.model_dump() if procedure_state else None, hardware=selected_hardware
        )
        procedure.add_action(
            DisplayInstructionAction(
                description="Fill a large beaker with water. Submerge pump lines ensuring ends are below the surface",
                name="fill_beaker",
                hardware=selected_hardware,
            )
        )
        procedure.add_action(
            DisplayInstructionAction(
                description=(
                    "For each pump, set a vial in a rack and place line in vial. Note that to prevent damage"
                    "from overrun, vials should not be placed on the evolver in this procedure"
                ),
                name="place_vials",
                hardware=selected_hardware,
            )
        )
        procedure.add_action(
            PumpAction(
                fast=self.time_to_pump_fast,
                slow=self.time_to_pump_slow,
                name="pump_run",
                description="Run pumps",
                hardware=selected_hardware,
            )
        )
        procedure.add_action(
            DisplayInstructionAction(
                description="Wait for pumps to finish", name="wait_pumps", hardware=selected_hardware
            )
        )
        for pump_id in selected_hardware.pump_ids:
            procedure.add_action(
                RecordVolumeAction(
                    name=f"record_pump_{pump_id}",
                    description=f"Record volume for pump {pump_id}",
                    hardware=selected_hardware,
                    pump_id=pump_id,
                )
            )
        self.calibration_procedure = procedure
