from typing import Any, Dict

from evolver.calibration.actions import CalibrationAction


class CalibrationProcedure:
    def __init__(self, name: str):
        """
        Initialize the CalibrationProcedure.

        Args:
            name (str): The name of the calibration procedure.
            calibrator (Calibrator): The calibrator instance that will execute the calibration procedure.

        Attributes:
            name (str): The name of the calibration procedure.
            actions (list): The list of actions to be executed in the calibration procedure. The order of actions is the default order of execution, but the frontend can change this if needed.
            state (dict): The current state of the calibration procedure. This state is updated immutably after each action is dispatched. When the procedure is done, this state is copied to the Calibrator state.

        Notes:
            - Dispatching an action will update the state of the calibration procedure.
            - Actions should be independent of one another with validation and error handling if the state is not as expected (e.g., calculate fit action is called on a vial that doesn't have reference and raw data pairs).
            - The procedure state is updated immutably, ensuring the state of the procedure is always consistent.
            - TODO: Introduce some kind of composition of procedures - so you can have an undoable procedure, and/or one that logs the actions that've been taken. Ditto for a resumable procedure.
        """
        self.name = name
        self.actions = []
        self.state = {}  # Holds the current state of calibration, when the procedure is done this is copied to the Calibrator state.

    def add_action(self, action: CalibrationAction):
        self.actions.append(action)

    def get_actions(self):
        return self.actions

    def dispatch(self, action: CalibrationAction, payload: Dict[str, Any]) -> Dict[str, Any]:
        if payload is not None:
            payload = action.UserInput(**payload)
        self.state = action.execute(self.state, payload)
        return self.state
