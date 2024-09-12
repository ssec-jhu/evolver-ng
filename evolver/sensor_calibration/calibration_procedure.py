# TODO consider Calibration pre-flight checks. For example by default we should check sensor manager for selected sensors.
# by extension the SensorManager should have a method to check if all selected sensors are ready for calibration or similar.
# I feel like Hardware class likely already manages this stuff.

class CalibrationProcedure:
    def __init__(self, sensor_type: str, sensors):
        """
        Initialize the CalibrationProcedure with a sensor type, an empty list of steps, and selected sensors.

        :param sensor_type: The type of sensor being calibrated (e.g., "temperature", "optical_density").
        :param sensors: List of sensors involved in the calibration procedure.
        """
        self.sensor_type = sensor_type
        self.sensors = sensors # TODO: Refactor or add validation to make sure all sensors are of the same type, then consider deriving self.sensor_type from sensors
        self.steps = []  # List to hold the sequence of calibration steps
        self.current_step = 0  # Track the current step in the procedure

    def add_step(self, step: CalibrationStep):
        """
        Add a calibration step to the procedure.

        :param step: A CalibrationStep object to be added to the procedure.
        """
        self.steps.append(step)

    def execute_step(self):
        """
        Execute the current calibration step, handling global and sensor-specific steps.

        :param sensors: List of selected sensor objects (used for sensor-specific steps).
        """
        if self.current_step < len(self.steps):
            step = self.steps[self.current_step]

            if step.global_step:
                # Execute global step (only once, without any sensor-specific logic)
                step.action()
                self.current_step += 1
            else:
                # Execute sensor-specific step for each selected sensor
                for sensor in self.sensors:
                    step.action(sensor)

                # Move to next step only when all sensors have completed the step
                if all(step.is_complete() for sensor in self.sensors):
                    self.current_step += 1
            print(f"Completed step {self.current_step}")
        else:
            print("All steps completed.")

    def is_complete(self):
        return self.current_step >= len(self.steps)

    def run(self):
        """
        Run all the calibration steps in sequence, handling global and sensor-specific steps.
        """
        while not self.is_complete():
            self.execute_step()
