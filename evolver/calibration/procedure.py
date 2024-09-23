class CalibrationProcedure:
    def __init__(self, name: str):
        self.name = name
        self.steps = []
        self.current_step_index = 0
        self.state = {}  # Holds the current state of calibration

    def add_step(self, step):
        self.steps.append(step)

    def get_current_step(self):
        if self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    def dispatch(self, action):
        """Executes the current step with the given action."""
        current_step = self.get_current_step()
        if current_step is None:
            print("Calibration procedure is complete.")
            return self.state

        # Execute the step's action and update the state
        self.state = current_step.execute(self.state, action)
        self.current_step_index += 1
        return self.state
