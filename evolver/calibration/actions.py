from typing import Dict, Any
from copy import deepcopy


class DisplayInstructionAction:
    def __init__(self, description: str, name: str):
        self.description = description
        self.name = name

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return state.copy()


class VialTempReferenceValueAction:
    def __init__(self, hardware, description: str, vial_idx: int, name: str):
        self.hardware = hardware
        self.description = description
        self.vial_idx = vial_idx
        self.name = name

    def execute(self, state: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
        # Validate payload
        reference_value = payload.get("reference_value")
        if reference_value is None:
            raise ValueError("Payload must include 'reference_value'")

        new_state = deepcopy(state)
        vial_key = f"vial_{self.vial_idx}"
        # Initialize nested dicts if they don't exist, otherwise leave them intact
        vial_data = new_state.setdefault(self.hardware.name, {}).setdefault(vial_key, {"reference": [], "raw": []})
        # Append new reference value without touching the existing raw data
        vial_data["reference"].append(reference_value)
        return new_state


class VialTempRawVoltageAction:
    def __init__(self, hardware, vial_idx: int, description, name):
        self.name = name
        self.hardware = hardware
        self.description = description
        self.vial_idx = vial_idx

    def execute(self, state, payload):
        # This step doesn't require any action input
        # Read sensor value from hardware
        # Beware the serial read has latency associated with it, e.g. 1.5s... and the best way is to do read once
        # (goes to buffer) and get on that.
        # so think about hoisting all reads to the procedure state, periodically update it.
        sensor_value = self.hardware.read()[self.vial_idx]
        new_state = deepcopy(state)
        vial_key = f"vial_{self.vial_idx}"
        vial_data = new_state.setdefault(self.hardware.name, {}).setdefault(vial_key, {"reference": [], "raw": []})
        vial_data["raw"].append(sensor_value)
        return new_state


class VialTempCalculateFitAction:
    def __init__(self, hardware, vial_idx: int, description: str, name: str):
        self.hardware = hardware
        self.description = description
        self.name = name
        self.vial_idx = vial_idx

    def execute(self, state: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
        vial_key = f"vial_{self.vial_idx}"
        hardware_name = self.hardware.name

        # Check for necessary data
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

        # Update state immutably with fit parameters
        new_state = deepcopy(state)
        new_state[hardware_name][vial_key]["fit_parameters"] = fit_parameters
        return new_state
