from typing import Dict, Optional

from pydantic import BaseModel, Field

from evolver.calibration.action import CalibrationAction


class ReferenceValueAction(CalibrationAction):
    class FormModel(BaseModel):
        """
        Because this action requires manual user input, we define a Pydantic model for the input to the action.
        This is used by the frontend to generate a form for the user to fill out.
        """

        temperature: float = Field(..., title="Temperature", description="Temperature in degrees Celsius")

    def __init__(self, hardware, vial_idx: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hardware = hardware
        self.vial_idx = vial_idx

    def execute(self, state: Dict, payload: Optional[FormModel] = None):
        state.setdefault(self.vial_idx, {"reference": [], "raw": []})
        state[self.vial_idx]["reference"].append(payload.temperature)
        state.setdefault("completed_actions", []).append(self.name)
        return state


class RawValueAction(CalibrationAction):
    class FormModel(BaseModel):
        pass

    def __init__(self, hardware, vial_idx: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hardware = hardware
        self.vial_idx = vial_idx

    def execute(self, state, payload: Optional[FormModel] = None):
        state.setdefault(self.vial_idx, {"reference": [], "raw": []})
        sensor_value = self.hardware.read()[self.vial_idx]
        state[self.vial_idx]["raw"].append(sensor_value)
        state.setdefault("completed_actions", []).append(self.name)
        return state


class CalculateFitAction(CalibrationAction):
    class FormModel(BaseModel):
        pass

    def __init__(self, hardware, vial_idx: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hardware = hardware
        self.vial_idx = vial_idx

    def execute(self, state, payload: Optional[FormModel] = None):
        state.setdefault(self.vial_idx, {"reference": [], "raw": []})
        vial_data = state[self.vial_idx]
        # The result of the refit is stored in the output_transformer, accessible via hardware.calibrator.output_transformer
        self.hardware.calibrator.output_transformer[self.vial_idx].refit(vial_data["reference"], vial_data["raw"])
        state.setdefault("completed_actions", []).append(self.name)
        return state


class SaveProcedureStateAction(CalibrationAction):
    class FormModel(BaseModel):
        pass

    def __init__(self, hardware, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hardware = hardware

    def execute(self, state, payload: Optional[FormModel] = None):
        # Note this is a side effect, but it is necessary to save the state of the calibration procedure
        state.setdefault("completed_actions", []).append(self.name)
        # Note this is a side effect, but it is necessary to save the state of the calibration procedure
        self.hardware.calibrator.calibration_data.measured = state
        return state
