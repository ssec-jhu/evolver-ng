class CalibrationProcedure:
    def __init__(self, sensor_type: str):
        """
        Initialize the CalibrationProcedure with a sensor type and an empty list of steps.
        
        :param sensor_type: The type of sensor being calibrated (e.g., "temperature", "optical_density").
        """
        self.sensor_type = sensor_type
        self.steps = []  # List to hold the sequence of calibration steps
        self.current_step = 0  # Track the current step in the procedure

    def add_step(self, step):
        """
        Add a calibration step to the procedure.
        
        :param step: A CalibrationStep object to be added to the procedure.
        """
        self.steps.append(step)

    def execute_step(self, device, sensors):
        """
        Execute the current calibration step for all selected sensors.
        
        :param device: The hardware device that interacts with the sensors.
        :param sensors: A list of sensor objects to execute the step on.
        """
        if self.current_step < len(self.steps):
            step = self.steps[self.current_step]
            for sensor in sensors:
                step.action(device, sensor)

            # Check if the step is complete before moving to the next one
            if all(step.is_complete() for sensor in sensors):
                self.current_step += 1  # Advance to the next step only when all sensors complete the step
            else:
                print("Waiting for all sensors to complete the current step.")
        else:
            print("All steps completed.")

    def is_complete(self) -> bool:
        """
        Check if the procedure has completed all steps.
        
        :return: True if all steps have been executed, False otherwise.
        """
        return self.current_step >= len(self.steps)

    def reset(self):
        """
        Reset the procedure to the beginning (first step).
        """
        self.current_step = 0

    def run(self, device, sensors):
        """
        Run all the calibration steps in sequence for the selected sensors.
        
        :param device: The hardware device that interacts with the sensors.
        :param sensors: A list of sensor objects to execute the steps on.
        """
        while not self.is_complete():
            self.execute_step(device, sensors)


# Step through the calibration procedure for multiple sensors at a time.
class MultiSensorCalibrationProcedure(CalibrationProcedure):
    def __init__(self, sensor_type, sensors):
        super().__init__(sensor_type)
        self.sensors = sensors  # List of selected sensors

    def execute_step(self, device):
        """
        Execute the current calibration step for all sensors. Wait for user input if required.
        
        :param device: The hardware device that interacts with the sensors.
        """
        if self.current_step < len(self.steps):
            step = self.steps[self.current_step]
            for sensor in self.sensors:
                step.action(device, sensor)

            # If user input is required, wait for input per sensor before moving forward
            if all(step.is_complete() for sensor in self.sensors):
                self.current_step += 1  # Advance only when all sensors complete the current step
            else:
                print("Waiting for all sensors to complete the current step.")
        else:
            print("All steps completed.")
