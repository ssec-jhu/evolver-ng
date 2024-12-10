from abc import ABC
from copy import deepcopy
from typing import Any, Dict

from evolver.base import BaseInterface
from evolver.calibration.action import CalibrationAction


class CalibrationProcedure(BaseInterface, ABC):
    class Config(BaseInterface.Config): ...

    def __init__(self, state=None, *args, **kwargs):
        """
        Initialize the CalibrationProcedure.

        Attributes:
            actions (list): The list of actions that can be executed in the calibration procedure.
                All actions are added to this list in the create_calibration_procedure method.
                Typically, a procedure is complete when all actions have been dispatched in sequence using the HTTP API.
            state (dict): The persisted state of the calibration procedure (from Calibrator.CalibrationData), updated as actions are executed.

        Notes:
            Dispatching an action will update the state of the calibration procedure.

            The measured data that accumulates in procedure state is eventually used by the Calibrator's Transformer class
            to fit a model to the data. This can be done by defining a CalculateFit action in the procedure and dispatching it.
            Data stored in the CalibrationProcedure state should also be periodically saved to the Calibraor's CalibrationData class.
            That way CalibrationProcedure state can be saved and reloaded to continue the calibration procedure if interupted.
            This can be done by defining a SaveProcedureState action in the procedure and dispatching it.
        """
        super().__init__(*args, **kwargs)
        self.actions = []
        self.state = state is not None and state or {}
        self.history = []

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
        if len(self.history) > 0:
            self.state = self.history.pop()
        return self.state

    def dispatch(self, action: CalibrationAction, payload: Dict[str, Any]):
        if payload is not None and action.FormModel.model_fields != {}:
            payload = action.FormModel(**payload)
        previous_state = deepcopy(self.state)
        updated_state = action.execute(self.state, payload)
        self.history.append(previous_state)
        self.state = updated_state
        return self.state
