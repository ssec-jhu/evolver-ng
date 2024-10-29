from typing import Dict, Optional

from pydantic import BaseModel, Field

from evolver.calibration.action import CalibrationAction


class ReferenceValueAction(CalibrationAction):
    class FormModel(BaseModel):
        temperature: float = Field(..., title="Temperature", description="Temperature in degrees Celsius")

    def __init__(self, hardware, description: str, vial_idx: int, name: str):
        super().__init__(name=name, description=description, requires_input=True)
        self.hardware = hardware
        self.vial_idx = vial_idx

    def execute(self, state: Dict, payload: Optional[FormModel] = None):
        state.setdefault(self.vial_idx, {"reference": [], "raw": []})
        state[self.vial_idx]["reference"].append(payload.temperature)
        return state


class RawValueAction(CalibrationAction):
    class FormModel(BaseModel):
        pass

    def __init__(self, hardware, vial_idx: int, description, name):
        super().__init__(name=name, description=description, requires_input=False)
        self.hardware = hardware
        self.vial_idx = vial_idx

    def execute(self, state, payload: Optional[FormModel] = None):
        state.setdefault(self.vial_idx, {"reference": [], "raw": []})
        sensor_value = self.hardware.read()[self.vial_idx]
        state[self.vial_idx]["raw"].append(sensor_value)
        return state


class CalculateFitAction(CalibrationAction):
    class FormModel(BaseModel):
        pass

    def __init__(self, hardware, vial_idx: int, description: str, name: str):
        super().__init__(name=name, description=description, requires_input=False)
        self.hardware = hardware
        self.vial_idx = vial_idx

    def execute(self, state, payload: Optional[FormModel] = None):
        state.setdefault(self.vial_idx, {"reference": [], "raw": []})
        vial_data = state[self.vial_idx]
        self.hardware.calibrator.output_transformer[self.vial_idx].refit(vial_data["reference"], vial_data["raw"])
        # The result of the refit is stored in the output_transformer, accessible via hardware.calibrator.output_transformer
        return state


class SaveProcedureStateAction(CalibrationAction):
    class FormModel(BaseModel):
        pass

    def __init__(self, hardware, description: str, name: str):
        super().__init__(name=name, description=description, requires_input=False)
        self.hardware = hardware

    def execute(self, state, payload: Optional[FormModel] = None):
        self.hardware.calibrator.calibration_data.measured = state
        return state
