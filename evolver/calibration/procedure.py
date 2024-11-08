from abc import ABC
from typing import Any, Dict

from evolver.base import BaseInterface
from evolver.calibration.action import CalibrationAction


class CalibrationProcedure(BaseInterface, ABC):
    class Config(BaseInterface.Config): ...

    def __init__(self, *args, **kwargs):
        """
        Initialize the CalibrationProcedure.

        Attributes:
            actions (list): The list of actions that can be executed in the calibration procedure.
                All actions are added to this list in the create_calibration_procedure method.
                Typically a procedure is complete when all actions have been dispatched in sequence using the HTTP api.
            state (dict): The state of the calibration procedure, updated as actions are executed.
                It eventually passes the measured data to the transformer(s) for calibration,
                This can be done by defining a CalculateFit action in the procedure and dispatching it.
                Data stored here should also be saved to the CalibrationData on the Calibrator. That way
                calibration procedure state can be saved and reloaded to continue the calibration procedure if interupted.
                This can be done by defining a SaveProcedureState action in the procedure and dispatching it.

        Notes:
            Dispatching an action will update the state of the calibration procedure.
        """
        super().__init__(*args, **kwargs)
        self.actions = []
        self.state = {}

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

    def dispatch(self, action: CalibrationAction, payload: Dict[str, Any]):
        if payload is not None and action.requires_input:
            payload = action.FormModel(**payload)
        self.state = action.execute(self.state, payload)
        return self.state
