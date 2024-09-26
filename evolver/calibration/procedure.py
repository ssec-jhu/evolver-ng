class CalibrationProcedure:
    def __init__(self, name: str):
        self.name = name
        # The order of actions is the default order of execution, the frontend can change this if it likes
        # Dispatching an action will update the state of the calibration procedure.
        # Actions should be independent of one another with validation and error handling if state is not as expected.
        # e.g. calculate fit action is called on a vial that doesn't have reference and raw data pairs.
        # The procedure state is updated immutably, so that the state of the procedure is always consistent.
        self.actions = []
        self.state = {}  # Holds the current state of calibration, when the procedure is done this is copied to the Calibrator state.
        # TODO: undo/redo stack of states. This allows undo/redo functionality
        # TODO: persist state to after each action to the Calibrator.CalibrationData data structure.(see Arik for details)

    def add_action(self, step):
        self.actions.append(step)

    def get_actions(self):
        return self.actions

    def dispatch(self, action, payload):
        # Execute the action and update the state
        self.state = action.execute(self.state, payload)
        return self.state
