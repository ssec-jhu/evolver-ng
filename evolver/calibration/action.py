from abc import ABC, abstractmethod
from typing import Dict, Optional

from pydantic import BaseModel


class CalibrationAction(ABC):
    def __init__(self, name: str, description: str, requires_input: bool = False):
        """
        Initialize a CalibrationAction.

        Args:
            name (str): The name of the calibration action, used to identify it within a calibration procedure composed of many actions.
            description (str): A short description of the action's purpose, useful for documentation or display to the person performing a calibration procedure composed of actions.
            requires_input (bool): Indicates whether this action requires user input (default is False) actions that require input should have a FormModel defined to express the shape of the required user input.
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
            state (Dict): The data collected in the course of the calibration process.
            payload (FormModel): Developer-defined input for the action.

        Returns:
            Dict: The updated state after performing the action.
        """
        pass


class DisplayInstructionAction(CalibrationAction):
    class FormModel(BaseModel):
        pass

    def execute(self, state: Dict, payload: Optional[FormModel] = None):
        return state.copy()
