from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Any, Dict

import pydantic


class CalibrationAction(ABC):
    def __init__(self, name: str, description: str):
        self.description = description
        self.name = name

    class UserInput(pydantic.BaseModel):
        pass

    @abstractmethod
    def execute(self, state: Dict[str, Any], payload: UserInput) -> Dict[str, Any]:
        """
        Execute the calibration action.

        This method should be implemented by subclasses to perform specific calibration actions.
        It takes the current state of the calibration procedure, and an optional payload, it processes them and
        returns the updated state.

        The payload is a pydantic model that is validated in the dispatch method of the CalibrationProcedure.

        Args:
            state (Dict[str, Any]): The current state of the calibration process.
            payload (UserInput): The user input required to perform the action.

        Returns:
            Dict[str, Any]: The updated state after performing the action.
        """
        pass


class DisplayInstructionAction(CalibrationAction):
    class UserInput(pydantic.BaseModel):
        pass

    def __init__(self, name: str, description: str):
        super().__init__(name, description)

    def execute(self, state: Dict[str, Any], payload: UserInput = None) -> Dict[str, Any]:
        return state.copy()


class VialTempReferenceValueAction(CalibrationAction):
    class UserInput(pydantic.BaseModel):
        temperature: float = pydantic.Field(title="Temperature", description="Temperature in degrees Celsius")

    def __init__(self, hardware, description: str, vial_idx: int, name: str):
        super().__init__(name, description)
        self.hardware = hardware
        self.vial_idx = vial_idx

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
        super().__init__(name, description)
        self.hardware = hardware
        self.vial_idx = vial_idx

    def execute(self, state: Dict[str, Any], payload: UserInput) -> Dict[str, Any]:
        sensor_value = self.hardware.read()[self.vial_idx]
        new_state = deepcopy(state)
        vial_key = f"vial_{self.vial_idx}"
        vial_data = new_state.setdefault(self.hardware.name, {}).setdefault(vial_key, {"reference": [], "raw": []})
        vial_data["raw"].append(sensor_value)
        calibration_data = self.hardware.calibrator.CalibrationData()
        calibration_data.save_calibration_procedure_state(calibration_procedure_state=new_state)
        return new_state


class VialTempCalculateFitAction(CalibrationAction):
    class UserInput(pydantic.BaseModel):
        pass

    def __init__(self, hardware, vial_idx: int, description: str, name: str):
        super().__init__(name, description)
        self.hardware = hardware
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

        if len(reference_values) != len(raw_values):
            raise ValueError(
                f"Reference and raw data lengths do not match for {hardware_name} {vial_key}, "
                f"Procedure state has {len(reference_values)} reference_values and {len(raw_values)} raw_values recorded so far"
                f"Unable to calculate fit, you must dispatch the appropriate actions to collect the required data"
            )

        if not self.hardware.calibrator.Config.output_transformer:
            raise ValueError(f"No output transformer available for {hardware_name}")

        fit_config = self.hardware.calibrator.Config.output_transformer.fit(reference_values, raw_values)

        new_state = deepcopy(state)
        new_state[hardware_name][vial_key]["output_fit_parameters"] = fit_config.dict()
        calibration_data = self.hardware.calibrator.CalibrationData()
        calibration_data.save_calibration_procedure_state(calibration_procedure_state=new_state)
        return new_state


class SaveCalibrationProcedureStateAction(CalibrationAction):
    class UserInput(pydantic.BaseModel):
        pass

    def __init__(self, hardware, description: str, name: str):
        super().__init__(name, description)
        self.hardware = hardware

    def execute(self, state: Dict[str, Any], payload: UserInput) -> Dict[str, Any]:
        calibration_data = self.hardware.calibrator.calibration_data
        calibration_data.save_calibration_procedure_state(calibration_procedure_state=state.copy())
        return state.copy()
