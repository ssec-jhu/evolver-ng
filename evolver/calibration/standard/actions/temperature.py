from collections import defaultdict
from typing import Optional

import numpy as np
from pydantic import BaseModel, Field

from evolver.calibration.action import CalibrationAction
from evolver.calibration.interface import CalibrationStateModel


class ReferenceValueAction(CalibrationAction):
    class FormModel(BaseModel):
        temperature: float = Field(..., title="Temperature", description="Temperature in degrees Celsius")

    def __init__(self, vial_idx: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vial_idx = vial_idx

    def execute(self, state: CalibrationStateModel, payload: Optional[FormModel] = None):
        state.measured = state.measured or defaultdict(lambda: {"reference": [], "raw": []})
        state.measured[self.vial_idx]["reference"].append(payload.temperature)
        return state


class RawValueAction(CalibrationAction):
    class FormModel(BaseModel):
        pass

    def __init__(self, vial_idx: int, num_readings: int = 3, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vial_idx = vial_idx
        self.num_readings = num_readings

    def execute(self, state: CalibrationStateModel, payload: Optional[FormModel] = None):
        readings = [self.hardware.read()[self.vial_idx].raw for i in range(self.num_readings)]
        median_raw = np.median(readings)
        state.measured = state.measured or defaultdict(lambda: {"reference": [], "raw": []})
        state.measured[self.vial_idx]["raw"].append(median_raw)
        return state


class CalculateFitAction(CalibrationAction):
    class FormModel(BaseModel):
        pass

    def __init__(self, vial_idx: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vial_idx = vial_idx

    def execute(self, state: CalibrationStateModel, payload: Optional[FormModel] = None):
        vial_data = state.measured[self.vial_idx]
        self.hardware.calibrator.output_transformer[self.vial_idx].refit(vial_data["reference"], vial_data["raw"])
        state.fitted_calibrator = self.hardware.calibrator.descriptor
        return state
