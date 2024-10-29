from abc import ABC
from typing import Any, Dict

from evolver.base import BaseInterface
from evolver.calibration.action import CalibrationAction


class CalibrationProcedure(BaseInterface, ABC):
    class Config(BaseInterface.Config): ...

    def __init__(self, name: str, *args, **kwargs):
        """
        Initialize the CalibrationProcedure.

        Args:
            name (str): The name of the calibration procedure.

        Attributes:
            name (str): The name of the calibration procedure.
            actions (list): The list of actions to be executed in the calibration procedure. The order of actions is the default order of execution, but the frontend can change this if needed.

        Notes:
            - Dispatching an action will update the state of the calibration procedure.
            - Actions should be independent of one another with validation and error handling if the state is not as expected (e.g., calculate fit action is called on a vial that doesn't have reference and raw data pairs).
            - The procedure state is updated immutably, ensuring the state of the procedure is always consistent.
            - TODO: Introduce some kind of composition of procedures - so you can have an undoable procedure, and/or one that logs the actions that've been taken.
        """
        super().__init__(*args, **kwargs)
        self.name = name
        self.actions = []
        self.state = {}

    def add_action(self, action: CalibrationAction):
        self.actions.append(action)

    def get_actions(self):
        return self.actions

    def get_state(self, *args, **kwargs):
        return self.state

    def dispatch(self, action: CalibrationAction, payload: Dict[str, Any]):
        if payload is not None and action.model.requires_input:
            payload = action.FormModel(**payload)
        self.state = action.execute(self.state, payload)
        return self.state
