from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from evolver.calibration.action import CalibrationAction, CalibrationActionModel
from evolver.calibration.interface import ProcedureStateModel


class VialData(BaseModel):
    reference: List[float] = Field(default_factory=list, description="Reference temperature values.")
    raw: List[float] = Field(default_factory=list, description="Raw temperature readings.")
    fit: Dict = Field(
        default_factory=dict,
        description="Fit parameters for the temperature sensor, calculated using the output transformer defined "
        "for the vial and the reference and raw values collected in the procedure.",
    )


class ProcedureState(ProcedureStateModel):
    """State model for the temperature calibration procedure."""

    selected_vials: List[int] = Field(
        default_factory=list, description="List of vials identified by their index being calibrated."
    )
    vial_data: Dict[int, VialData] = Field(
        default_factory=dict, description="Calibration data for each vial, keyed by vial index."
    )


class ReferenceValueAction(CalibrationAction):
    class FormModel(BaseModel):
        temperature: float = Field(..., title="Temperature", description="Temperature in degrees Celsius")

    def __init__(self, hardware, description: str, vial_idx: int, name: str):
        super().__init__(CalibrationActionModel(name=name, description=description, requires_input=True))
        self.hardware = hardware
        self.vial_idx = vial_idx

    def execute(self, state: ProcedureState, payload: Optional[FormModel] = None) -> ProcedureState:
        reference_value = payload.temperature
        if self.vial_idx not in state.vial_data:
            state.vial_data[self.vial_idx] = VialData()
        state.vial_data[self.vial_idx].reference.append(reference_value)
        return state.model_copy()


class RawValueAction(CalibrationAction):
    class FormModel(BaseModel):
        pass

    def __init__(self, hardware, vial_idx: int, description, name):
        super().__init__(CalibrationActionModel(name=name, description=description, requires_input=False))
        self.hardware = hardware
        self.vial_idx = vial_idx

    def execute(self, state: ProcedureState, payload: Optional[FormModel] = None) -> ProcedureState:
        if self.vial_idx not in state.vial_data:
            state.vial_data[self.vial_idx] = VialData()
        sensor_value = self.hardware.read()[self.vial_idx]
        state.vial_data[self.vial_idx].raw.append(sensor_value)
        self.hardware.calibrator.calibration_data.save()
        return state.model_copy()


class CalculateFitAction(CalibrationAction):
    class FormModel(BaseModel):
        pass

    def __init__(self, hardware, vial_idx: int, description: str, name: str):
        super().__init__(CalibrationActionModel(name=name, description=description, requires_input=False))
        self.hardware = hardware
        self.vial_idx = vial_idx

    def execute(self, state: ProcedureState, payload: Optional[FormModel] = None) -> ProcedureState:
        if self.vial_idx not in state.vial_data:
            state.vial_data[self.vial_idx] = VialData()

        vial_data = state.vial_data[self.vial_idx]
        reference_values = vial_data.reference
        raw_values = vial_data.raw
        output_transformer = self.hardware.calibrator.output_transformer[self.vial_idx]

        fit_config = output_transformer.fit(reference_values, raw_values)
        fit_config.calibration_procedure_state = state.model_copy()

        state.vial_data[self.vial_idx].fit["parameters"] = fit_config.model_dump()["parameters"]
        state.vial_data[self.vial_idx].fit["degree"] = fit_config.model_dump()["degree"]
        self.hardware.calibrator.calibration_data.calibration_procedure_state = state.model_copy()
        self.hardware.calibrator.calibration_data.save()

        return state.model_copy()


class SaveProcedureStateAction(CalibrationAction):
    class FormModel(BaseModel):
        pass

    def __init__(self, hardware, description: str, name: str):
        super().__init__(CalibrationActionModel(name=name, description=description, requires_input=False))
        self.hardware = hardware

    def execute(self, state: ProcedureState, payload: Optional[FormModel] = None) -> ProcedureState:
        self.hardware.calibrator.calibration_data.save()
        return state.model_copy()
