class CalibrationStep:
    def __init__(self, name: str, instructions: str = "", input_required: bool = False):
        """
        Initialize the CalibrationStep with a name, instructions, and a flag indicating whether input is required.

        :param name: The name of the step (e.g., "Read Sensor Data").
        :param instructions: Instructions to be shown to the user, if any.
        :param input_required: Whether user input is required to complete this step.
        """
        self.name = name
        self.instructions = instructions
        self.input_required = input_required
        self.completed = False  # Track if the step has been completed

    def action(self, device, sensor):
        """
        This method should be implemented by each specific step to perform its action.

        :param device: The hardware device that interacts with the sensors.
        :param sensor: The sensor object that this step is operating on.
        """
        raise NotImplementedError()

    def mark_complete(self):
        """
        Mark the step as complete, indicating that it has finished executing.
        """
        self.completed = True

    def is_complete(self) -> bool:
        """
        Check if the step has been marked as complete.

        :return: True if the step is complete, otherwise False.
        """
        return self.completed


class InstructionStep(CalibrationStep):
    def __init__(self, instructions: str):
        super().__init__(name="Instruction", instructions=instructions, input_required=False)

    def action(self, device, sensor):
        """
        Show the instruction and wait for user input to mark the step as complete.
        """
        print(f"Instruction: {self.instructions}")
        print("Waiting for user to mark this step as complete...")
        # The user will mark this step as complete via the UI or API.

class ReadSensorDataStep(CalibrationStep):
    def __init__(self):
        super().__init__(name="Read Sensor Data", instructions="Reading data from sensor...", input_required=False)

    def action(self, device, sensor):
        # Example of reading data from the sensor
        data = device.read_sensor_data(sensor.id)
        sensor.calibration_data.add_calibration_point(data, {"sensor_data": data})
        print(f"Sensor data for {sensor.id}: {data}")
        self.mark_complete()  # Mark the step as complete after data is read


class LoopStep(CalibrationStep):
    def __init__(self, name, steps, exit_condition):
        """
        :param name: Name of the loop step
        :param steps: List of steps to execute inside the loop
        :param exit_condition: Function that returns True when the loop should exit
        """
        super().__init__(name=name, instructions="Looping through steps")
        self.steps = steps
        self.exit_condition = exit_condition
        self.iteration = 0

    def action(self, device, sensor):
        print(f"Starting loop iteration {self.iteration}")
        
        # Execute the steps in the loop
        for step in self.steps:
            step.action(device, sensor)
        
        self.iteration += 1
        # Check the exit condition
        if not self.exit_condition(device, sensor):
            # If the condition isn't met, repeat the loop
            return "repeat"
        else:
            # Exit the loop
            return "exit"

