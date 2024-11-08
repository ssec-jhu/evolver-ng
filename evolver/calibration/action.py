from abc import ABC, abstractmethod
from typing import Dict, Optional

from pydantic import BaseModel


class CalibrationAction(ABC):
    def __init__(self, name: str, description: str, requires_input: bool = False):
        """
        Initialize a CalibrationAction.

        Args:
            name (str): The name of the calibration action.
                Used to identify it within a calibration procedure composed of many actions.
                Must be unique within a procedure.
            description (str): A short description of the action's purpose.
                Useful for documentation or display of instructions to the person performing a calibration procedure action.
            requires_input (bool): Indicates whether this action requires user input.
                Actions that require input should have a FormModel defined to express the model of the required user input.
        """
        self.name = name
        self.description = description
        self.requires_input = requires_input

    class FormModel(BaseModel):
        pass

    @abstractmethod
    def execute(self, state: Dict, payload: Optional[FormModel] = None):
        """
        Execute the calibration action.


        Args:
            state (Dict): The data collected in the course of the calibration procedure.
            payload (FormModel): Input for the action.

        Returns:
            Dict: The updated state after performing the action.

        Notes:
            Ideally this method should be idempotent, or "pure" in functional programming terms.
            This means that it should not have side effects.
            However, in practice this is not always possible, and actions may have side effects,
            such as saving the state of the calibration procedure to the parent
            Calibrator's CalibrationData class (which saves the state to a file).
            or calling the Calibrator's Transformer's refit method to update the calibration model.
        """
        pass


class DisplayInstructionAction(CalibrationAction):
    class FormModel(BaseModel):
        pass

    def execute(self, state: Dict, payload: Optional[FormModel] = None):
        return state.copy()
