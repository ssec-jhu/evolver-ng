class CalibrationProcedure:
    def __init__(self, sensor_type: str, sensors):
        """
        Initialize the CalibrationProcedure with a sensor type and selected sensors.

        :param sensor_type: The type of sensor being calibrated.
        :param sensors: List of sensors involved in the calibration procedure.
        """
        self.sensor_type = sensor_type
        self.sensors = sensors  # List of Sensor objects
        self.steps = []  # List to hold the sequence of calibration steps
        self.current_step_index = 0  # Track the current step index
        self.context = {"sensors": sensors}  # Context to share data between steps

    def add_step(self, step: CalibrationStep):
        """
        Add a calibration step to the procedure.

        :param step: A CalibrationStep object to be added to the procedure.
        """
        self.steps.append(step)

    def execute_step(self):
        """
        Execute the current calibration step, handling global and sensor-specific steps.
        """
        if self.current_step_index < len(self.steps):
            step = self.steps[self.current_step_index]
            print(f"Executing step: {step.name}")

            if isinstance(step, GlobalCalibrationStep):
                # Execute global step
                step.action(context=self.context)
                if step.is_complete():
                    self.current_step_index += 1
            elif isinstance(step, SensorCalibrationStep):
                # Execute sensor-specific step
                for sensor in self.sensors:
                    if not step.is_complete(sensor.id):
                        step.action(sensor, context=self.context)
                # Move to next step if all sensors have completed the step
                if all(step.is_complete(sensor.id) for sensor in self.sensors):
                    self.current_step_index += 1
            else:
                # Handle other types of steps if any
                pass
        else:
            print("All steps completed.")

    def is_complete(self) -> bool:
        """
        Check if all steps in the procedure have been completed.

        :return: True if all steps are completed, otherwise False.
        """
        return self.current_step_index >= len(self.steps)

    def run(self):
        """
        Run all the calibration steps in sequence.
        """
        while not self.is_complete():
            self.execute_step()
            # In a real application, you might wait for user input or other events here
            # For this example, we'll just proceed to the next step
            # Remove the following line in a real application
            input("Press Enter to proceed to the next step...")
