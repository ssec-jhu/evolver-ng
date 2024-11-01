from abc import ABC, abstractmethod
from typing import Dict, Optional

from pydantic import BaseModel, Field


class CalibrationActionModel(BaseModel):
    name: str = Field(description="The name of the action")
    description: str = Field(description="Description of the action's purpose")
    requires_input: bool = Field(
        False, description="Flag indicating if user input is needed, FormModel defines the input shape"
    )


class CalibrationAction(ABC):
    model: CalibrationActionModel

    def __init__(self, name: str, description: str, requires_input: bool = False):
        self.model = CalibrationActionModel(name=name, description=description, requires_input=requires_input)

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
