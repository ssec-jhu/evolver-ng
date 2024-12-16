from abc import ABC
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from evolver.base import BaseInterface
from evolver.calibration.action import CalibrationAction, undoable


class CalibrationStateModel(BaseModel):
    """
    Model to represent the state of a calibration procedure. All procedures record their completed actions in this model.
    Along with the completed actions, the state of the calibration procedure (i.e. the data the actions have gathered) can be stored.
    The shape of this additional data is not fixed and therefore is not included in the model here.
    When considering adding attributes, note this model is shared by the Calibrator.CalibrationData class.

    Attributes:
        completed_actions (List[str]): A list of actions that have been completed during the calibration procedure.
        history: A list of previous states of the calibration procedure. Used to undo actions. Action's execute method must use the @complete decorator to be undoable.
    """

    class Config:
        extra = "allow"

    completed_actions: List[str] = Field(default_factory=list)
    history: List["CalibrationStateModel"] = Field(default_factory=list)


class CalibrationProcedure(BaseInterface, ABC):
    class Config(BaseInterface.Config): ...

    def __init__(self, state=None, *args, **kwargs):
        """
        Initialize the CalibrationProcedure.

        Attributes:
            actions (list): The list of actions that can be executed in the calibration procedure.
                All actions are added to this list in the create_calibration_procedure method.
                Typically, a procedure is complete when all actions have been dispatched in sequence using the HTTP API.
            state (CalibrationStateModel): The state of the calibration procedure updated as actions are executed.
                The state can be saved and reloaded to continue the calibration procedure if interrupted.
                To save the state to the Calibrator.CalibrationData class, decorate an action's execute method with the @save decorator.
                Only state that is explicitly saved will be persisted, so it is important to save the state periodically.
                The @save decorator persists the entire state of the procedure, after @save decorated action has been executed.

        Notes:
            Dispatching an action will update the state of the calibration procedure.

            The measured data that accumulates in procedure state is eventually used by the Calibrator's Transformer class
            to fit a model to the data. This can be done by defining a CalculateFit action in the procedure and dispatching it.
            Data stored in the CalibrationProcedure state should also be periodically saved to the Calibrator's CalibrationData class.
            That way CalibrationProcedure state can be saved and reloaded to continue the calibration procedure if interrupted.
            This can be done by defining a SaveProcedureState action in the procedure and dispatching it.
        """
        super().__init__(*args, **kwargs)
        self.actions = []
        self.state = CalibrationStateModel(**(state or {})).model_dump()

    def add_action(self, action: CalibrationAction):
        if any(existing_action.name == action.name for existing_action in self.actions):
            raise ValueError(
                f"Action with name '{action.name}' already exists. Each action must have a unique name and functionality.  "
                f"If you want to repeat an action, any action can be dispatched multiple times using the HTTP api."
            )
        self.actions.append(action)

    def get_actions(self):
        return self.actions

    def get_state(self, *args, **kwargs):
        return self.state

    def undo(self):
        """
        Undo the last action that was dispatched in the calibration procedure.
        the dispatch method must use the @undoable decorator to be undoable.
        """
        if len(self.state["history"]) > 0:
            self.state = self.state["history"].pop()
        return self.state

    @undoable
    def dispatch(self, action: CalibrationAction, payload: Dict[str, Any]):
        if payload is not None and action.FormModel.model_fields != {}:
            payload = action.FormModel(**payload)
        updated_state = action.execute(self.state, payload)
        self.state = updated_state
        return self.state
