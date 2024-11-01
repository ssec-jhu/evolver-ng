from abc import ABC, abstractmethod
from typing import Dict, Optional

from pydantic import BaseModel


class CalibrationAction(ABC):
    name: str
    description: str
    requires_input: bool

    def __init__(self, name: str, description: str, requires_input: bool = False):
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
