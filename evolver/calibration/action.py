from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel, Field

from evolver.calibration.interface import ProcedureStateModel


class CalibrationActionModel(BaseModel):
    name: str = Field(..., description="The name of the action")
    description: str = Field(..., description="Description of the action's purpose")
    requires_input: bool = Field(
        False, description="Flag indicating if user input is needed, FormModel defines the input shape"
    )


class CalibrationAction(ABC):
    def __init__(self, model: CalibrationActionModel):
        self.model = model

    class FormModel(BaseModel):
        pass

    @abstractmethod
    def execute(self, state: ProcedureStateModel, payload: Optional[FormModel] = None) -> ProcedureStateModel:
        """
        Execute the calibration action.
        Args:
            state (ProcedureStateModel): The current state of the calibration process.
            payload (FormModel): Developer-defined input for the action.

        Returns:
            ProcedureStateModel: The updated state after performing the action.
        """
        pass


class DisplayInstructionAction(CalibrationAction):
    class FormModel(BaseModel):
        pass

    def __init__(self, name: str, description: str):
        super().__init__(CalibrationActionModel(name=name, description=description, requires_input=False))

    def execute(self, state: ProcedureStateModel, payload: Optional[FormModel] = None) -> ProcedureStateModel:
        return state.model_copy()
