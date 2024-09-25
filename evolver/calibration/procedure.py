class CalibrationProcedure:
    def __init__(self, name: str):
        self.name = name
        self.actions = []
        self.state = {}  # Holds the current state of calibration
        # todo store all previous states in a list

    def add_action(self, step):
        self.actions.append(step)

    def get_actions(self):
        return self.actions

    # Todo, dispatch should accept params...
    def dispatch(self, action):
        # Execute the action and update the state
        self.state = action.execute(self.state, action)
        return self.state
