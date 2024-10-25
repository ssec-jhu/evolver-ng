from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from evolver.calibration.action import CalibrationAction, CalibrationActionModel
from evolver.calibration.procedure import ProcedureStateModel


class VialCalibrationData(BaseModel):
    reference: List[float] = Field(default_factory=list, description="Reference temperature values.")
    raw: List[float] = Field(default_factory=list, description="Raw temperature readings.")
    fit: Dict = Field(
        default_factory=dict,
        description="Fit parameters for the temperature sensor, calculated from reference and raw values collected in the procedure.",
    )


class TempCalibrationProcedureState(BaseModel):
    """State model for temperature calibration procedure."""

    selected_vials: List[int] = Field(default_factory=list, description="List of vials being calibrated.")
    vial_data: Dict[int, VialCalibrationData] = Field(
        default_factory=dict, description="Calibration data for each vial."
    )


class DisplayInstructionAction(CalibrationAction):
    class FormModel(BaseModel):
        pass

    def __init__(self, name: str, description: str):
        super().__init__(CalibrationActionModel(name=name, description=description, requires_input=False))

    def execute(self, state: ProcedureStateModel, payload: Optional[FormModel] = None) -> ProcedureStateModel:
        return state.model_copy()


class VialTempReferenceValueAction(CalibrationAction):
    class FormModel(BaseModel):
        temperature: float = Field(..., title="Temperature", description="Temperature in degrees Celsius")

    def __init__(self, hardware, description: str, vial_idx: int, name: str):
        super().__init__(CalibrationActionModel(name=name, description=description, requires_input=True))
        self.hardware = hardware
        self.vial_idx = vial_idx

    def execute(
        self, state: TempCalibrationProcedureState, payload: Optional[FormModel] = None
    ) -> TempCalibrationProcedureState:
        reference_value = payload.temperature
        if self.vial_idx not in state.vial_data:
            state.vial_data[self.vial_idx] = VialCalibrationData()
        state.vial_data[self.vial_idx].reference.append(reference_value)
        return state.model_copy()


class VialTempRawVoltageAction(CalibrationAction):
    class FormModel(BaseModel):
        pass

    def __init__(self, hardware, vial_idx: int, description, name):
        super().__init__(CalibrationActionModel(name=name, description=description, requires_input=False))
        self.hardware = hardware
        self.vial_idx = vial_idx

    def execute(
        self, state: TempCalibrationProcedureState, payload: Optional[FormModel] = None
    ) -> TempCalibrationProcedureState:
        if self.vial_idx not in state.vial_data:
            state.vial_data[self.vial_idx] = VialCalibrationData()
        sensor_value = self.hardware.read()[self.vial_idx]
        state.vial_data[self.vial_idx].raw.append(sensor_value)
        calibration_data = self.hardware.calibrator.calibration_data
        calibration_data.save_calibration_procedure_state(calibration_procedure_state=state.model_copy())
        return state.model_copy()


class VialTempCalculateFitAction(CalibrationAction):
    class FormModel(BaseModel):
        pass

    def __init__(self, hardware, vial_idx: int, description: str, name: str):
        super().__init__(CalibrationActionModel(name=name, description=description, requires_input=False))
        self.hardware = hardware
        self.vial_idx = vial_idx

    def execute(
        self, state: TempCalibrationProcedureState, payload: Optional[FormModel] = None
    ) -> TempCalibrationProcedureState:
        if self.vial_idx not in state.vial_data:
            state.vial_data[self.vial_idx] = VialCalibrationData()

        vial_data = state.vial_data[self.vial_idx]
        reference_values = vial_data.reference
        raw_values = vial_data.raw

        if not reference_values or not raw_values:
            raise ValueError(f"Insufficient data to calculate fit for vial {self.vial_idx}")

        if len(reference_values) != len(raw_values):
            raise ValueError(
                f"Reference and raw data lengths do not match for vial {self.vial_idx}. "
                f"Expected equal lengths but got {len(reference_values)} reference values and {len(raw_values)} raw values."
            )

        # Check for output transformer, although the temp hardware has both, we're only interested in the output transformer,
        # since we want to fit the hardware's output (i.e. those it produces rather than receives) values to the reference values.
        if not self.hardware.calibrator.Config.output_transformer:
            raise ValueError(f"No output transformer available for hardware {self.hardware.name}")

        fit_config = self.hardware.calibrator.Config.output_transformer.fit(reference_values, raw_values)
        fit_config.calibration_procedure_state = state.model_copy()

        state.vial_data[self.vial_idx].fit = fit_config.model_dump()

        calibration_data = self.hardware.calibrator.calibration_data
        calibration_data.save_calibration_procedure_state(calibration_procedure_state=state.model_copy())

        return state.model_copy()


class SaveCalibrationProcedureStateAction(CalibrationAction):
    class FormModel(BaseModel):
        pass

    def __init__(self, hardware, description: str, name: str):
        super().__init__(CalibrationActionModel(name=name, description=description, requires_input=False))
        self.hardware = hardware

    def execute(
        self, state: TempCalibrationProcedureState, payload: Optional[FormModel] = None
    ) -> TempCalibrationProcedureState:
        calibration_data = self.hardware.calibrator.calibration_data
        calibration_data.save_calibration_procedure_state(calibration_procedure_state=state.model_copy())
        return state.model_copy()
