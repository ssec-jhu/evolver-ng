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


class AllVialsAdjustHeaterAction(CalibrationAction):
    def __init__(self, vials: list[int], raw_adjustment: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vials = vials
        self.raw_adjustment = raw_adjustment

    def execute(self, state: CalibrationStateModel, payload=None):
        for vial in self.vials:
            raw = int(state.roomTempRawValues[vial] + self.raw_adjustment)
            self.hardware.set(vial=vial, temperature=None, raw=raw)
        self.hardware.commit()
        return state


class AllVialsHeaterOffAction(CalibrationAction):
    def __init__(self, vials: list[int], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vials = vials

    def execute(self, state: CalibrationStateModel, payload=None):
        for vial in self.vials:
            self.hardware.set(vial=vial, temperature=None, raw=None)
        self.hardware.commit()
        return state


class AllVialsReadRoomTempAction(CalibrationAction):
    def __init__(self, vials: list[int], num_readings=3, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vials = vials
        self.num_readings = num_readings

    def execute(self, state: CalibrationStateModel, payload=None):
        readings = [self.hardware.read() for _ in range(self.num_readings)]
        # unpack the readings into per-vial set of raw values
        per_vial_raw = {vial: [readings[i][vial].raw for i in range(self.num_readings)] for vial in self.vials}
        state.roomTempRawValues = {vial: int(np.median(per_vial_raw[vial])) for vial in self.vials}
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
