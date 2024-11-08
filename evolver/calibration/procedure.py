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
            actions (list): The list of actions to be executed in the calibration procedure.
            state (dict): The state of the calibration procedure.

        Notes:
            - Dispatching an action will update the state of the calibration procedure.
        """
        super().__init__(*args, **kwargs)
        self.actions = []
        self.state = {}

    def add_action(self, action: CalibrationAction):
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
