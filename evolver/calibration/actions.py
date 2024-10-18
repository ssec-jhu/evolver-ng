from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Any, Dict

import pydantic


class CalibrationAction(ABC):
    class UserInput(pydantic.BaseModel): ...

    @abstractmethod
    def execute(self, state: Dict[str, Any], payload: UserInput) -> Dict[str, Any]:
        pass


class DisplayInstructionAction(CalibrationAction):
    class UserInput(pydantic.BaseModel):
        pass

    def __init__(self, description: str, name: str):
        self.description = description
        self.name = name

    def execute(self, state: Dict[str, Any], payload: UserInput = None) -> Dict[str, Any]:
        return state.copy()


class VialTempReferenceValueAction(CalibrationAction):
    class UserInput(pydantic.BaseModel):
        temperature: float = pydantic.Field(title="Temperature", description="Temperature in degrees Celsius")

    def __init__(self, hardware, description: str, vial_idx: int, name: str):
        self.hardware = hardware
        self.description = description
        self.vial_idx = vial_idx
        self.name = name

    def execute(self, state: Dict[str, Any], payload: UserInput) -> Dict[str, Any]:
        reference_value = payload.temperature
        new_state = deepcopy(state)
        vial_key = f"vial_{self.vial_idx}"
        vial_data = new_state.setdefault(self.hardware.name, {}).setdefault(vial_key, {"reference": [], "raw": []})
        vial_data["reference"].append(reference_value)
        return new_state


class VialTempRawVoltageAction(CalibrationAction):
    class UserInput(pydantic.BaseModel):
        pass

    def __init__(self, hardware, vial_idx: int, description, name):
        self.name = name
        self.hardware = hardware
        self.description = description
        self.vial_idx = vial_idx

    def execute(self, state: Dict[str, Any], payload: UserInput) -> Dict[str, Any]:
        sensor_value = self.hardware.read()[self.vial_idx]
        new_state = deepcopy(state)
        vial_key = f"vial_{self.vial_idx}"
        vial_data = new_state.setdefault(self.hardware.name, {}).setdefault(vial_key, {"reference": [], "raw": []})
        vial_data["raw"].append(sensor_value)
        return new_state


class VialTempCalculateFitAction(CalibrationAction):
    class UserInput(pydantic.BaseModel):
        pass

    def __init__(self, hardware, vial_idx: int, description: str, name: str):
        self.hardware = hardware
        self.description = description
        self.name = name
        self.vial_idx = vial_idx

    def execute(self, state: Dict[str, Any], payload: UserInput) -> Dict[str, Any]:
        vial_key = f"vial_{self.vial_idx}"
        hardware_name = self.hardware.name

        vial_data = state.get(hardware_name, {}).get(vial_key)
        if not vial_data:
            raise ValueError(f"No data available for {hardware_name} {vial_key}")

        reference_values = vial_data.get("reference", [])
        raw_values = vial_data.get("raw", [])
        if not reference_values or not raw_values:
            raise ValueError(f"Insufficient data to calculate fit for {hardware_name} {vial_key}")

        # Perform the fit calculation (to be implemented based on actual calibration logic)
        # Perform the fit calculation
        # TODO: Find out how to call the fit calculation method from the hardware
        # fit_parameters = self.hardware.calibrate_transformer.calculate_fit(reference_values, raw_values)
        # TODO: Persist the fit parameters to the Calibrator CalibrationData (see Arik's work) data structure.
        fit_parameters = [0.5, 0.5]

        new_state = deepcopy(state)
        new_state[hardware_name][vial_key]["fit_parameters"] = fit_parameters
        return new_state
