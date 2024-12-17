from typing import Dict, Optional

from pydantic import BaseModel, Field

from evolver.calibration.action import CalibrationAction, save


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
        return state


class CalculateFitAction(CalibrationAction):
    class FormModel(BaseModel):
        pass

    def __init__(self, hardware, vial_idx: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hardware = hardware
        self.vial_idx = vial_idx

    @save  # This action, when dispatched, will save the procedure state to the Calibrator.CalibrationData class
    def execute(self, state, payload: Optional[FormModel] = None):
        state.setdefault(self.vial_idx, {"reference": [], "raw": []})
        vial_data = state[self.vial_idx]
        # Side effect: refit the output transformer with the new data, store refit in another class.
        # The result of the refit is stored in the output_transformer, accessible via hardware.calibrator.output_transformer
        self.hardware.calibrator.output_transformer[self.vial_idx].refit(vial_data["reference"], vial_data["raw"])
        return state
