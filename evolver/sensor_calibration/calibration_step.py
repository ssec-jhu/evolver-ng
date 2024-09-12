import time
class CalibrationStep:
    def __init__(self, name: str, instructions: str = "", input_required: bool = False, global_step: bool = False):
        """
        Initialize the CalibrationStep with a name, instructions, and flags indicating whether input is required and whether the step is global.

        :param name: The name of the step (e.g., "Read Sensor Data").
        :param instructions: Instructions to be shown to the user, if any.
        :param input_required: Whether user input is required to complete this step.
        :param global_step: Whether the step is global (applies to all sensors) or sensor-specific.
        """
        self.name = name
        self.instructions = instructions
        self.input_required = input_required
        self.completed = False  # Track if the step has been completed
        self.global_step = global_step  # Whether this step applies to all sensors or specific ones

    def action(self, sensor=None, context=None):
        """
        Perform the action for the step. Should be implemented by specific subclasses.

        :param sensor: The sensor object that this step is operating on. None if it's a global step.
        :param context: Optional context dictionary to store shared information between steps.
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
        """
        Initialize the InstructionStep with the given instructions.

        :param instructions: The instructions to be shown to the user.
        """
        super().__init__(name="Instruction", instructions=instructions, input_required=True)

    def action(self, sensor, context=None):
        """
        The instruction will be reported to the UI via the API.
        The user will mark this step as complete via the UI or API.

        :param sensor: Ignored in this step but kept for interface consistency.
        :param context: Ignored in this step but kept for interface consistency.
        """
        pass

    def mark_instruction_complete(self):
        """
        Manually mark this instruction step as complete, typically triggered by user input via the UI or API.
        """
        self.mark_complete()


class ReadSensorDataStep(CalibrationStep):
    def __init__(self):
        """
        Initialize the ReadSensorDataStep for reading sensor data.
        """
        super().__init__(name="Read Sensor Data", instructions="Reading data from sensor...", input_required=False)

    def action(self, sensor, context=None):
        """
        Read data from the sensor by calling the sensor's read() method.

        :param sensor: The sensor object that will have its data read.
        :param context: Optional context to store or retrieve additional information.
        """
        sensor_data = sensor.read()
        sensor.calibration_data.add_calibration_point(sensor_data, {"sensor_data": sensor_data})
        print(f"Sensor data for {sensor.id}: {sensor_data}")
        self.mark_complete()


class InputReferenceStep(CalibrationStep):
    def __init__(self, reference_type: str):
        """
        Initialize the InputReferenceStep with the type of reference value expected.

        :param reference_type: The type of reference value required (e.g., "temperature", "optical_density").
        """
        super().__init__(name=f"Input {reference_type} Reference", input_required=True)
        self.reference_value = None  # Store the reference value input by the user
        self.reference_type = reference_type

    def action(self, sensor, context=None):
        """
        Update instructions to include the sensor's ID dynamically when the step is executed.

        :param sensor: The sensor object that this step is operating on.
        :param context: Optional context for shared values (not used in this step).
        """
        self.instructions = f"Please input the {self.reference_type} for sensor {sensor.id}."
        print(self.instructions)

    def set_reference_value(self, value):
        """
        Set the reference value, typically triggered by user input via the UI or API.

        :param value: The reference value input by the user.
        """
        if not isinstance(value, (int, float)):
            raise ValueError("Reference value must be a number.")
        
        self.reference_value = value
        self.mark_complete()  # Mark the step as complete once the reference value is set

class CalculateFitStep(CalibrationStep):
    def __init__(self):
        super().__init__(name="Calculate Fit", instructions="Calculate the fit model for the sensor")

    def action(self, sensor, context=None):
        raw_voltages = [point['system_data']['raw_voltage'] for point in sensor.calibration_data.calibration_points if 'raw_voltage' in point['system_data']]
        reference_values = [point['reference_data'] for point in sensor.calibration_data.calibration_points if point['reference_data']]

        # Assuming calculate_linear_fit is already implemented
        fit_model = calculate_linear_fit(raw_voltages, reference_values)
        sensor.calibration_data.set_fit_model(fit_model)
        print(f"Fit model for {sensor.id}: {fit_model}")

class LoopStep(CalibrationStep):
    def __init__(self, name: str, steps: list, exit_condition: callable):
        """
        Initialize the LoopStep to execute a series of steps until an exit condition is met.

        :param name: The name of the loop step.
        :param steps: A list of CalibrationStep objects to execute inside the loop.
        :param exit_condition: A function that returns True when the loop should exit.
        """
        super().__init__(name=name, instructions="Looping through steps")
        self.steps = steps
        self.exit_condition = exit_condition

    def action(self, sensor, context=None):
        """
        Execute the loop steps for each sensor and check the exit condition.

        :param sensor: The sensor object.
        :param context: Optional context for shared values.
        """
        print("Starting a loop iteration")

        # Execute the steps in the loop for each sensor
        for step in self.steps:
            step.action(sensor, context)

        # Check the exit condition
        if self.exit_condition(sensor, context):
            self.mark_complete()
            return "exit"

        return "repeat"


class WaitStep(CalibrationStep):
    def __init__(self, instructions: str, max_wait_time: float, exit_condition: callable):
        """
        Initialize the WaitStep with instructions, a maximum wait time, and an exit condition function.

        :param instructions: Instructions to be displayed to the user.
        :param max_wait_time: Maximum time to wait (in seconds).
        :param exit_condition: A function that, when it evaluates to True, will exit the wait early.
        """
        super().__init__(name="Wait", instructions=instructions, input_required=False)
        self.max_wait_time = max_wait_time  # Max wait time in seconds
        self.exit_condition = exit_condition  # Callable function to evaluate exit condition

    def action(self, sensor, context=None):
        """
        Execute the wait step, waiting either for the max wait time or until the exit condition is met.

        :param sensor: The sensor object that this step is operating on.
        :param context: Optional context for shared values.
        """
        start_time = time.time()

        # Wait until the exit condition is met or the max wait time is exceeded
        while not self.exit_condition(sensor, context) and (time.time() - start_time) < self.max_wait_time:
            print(f"Waiting... {self.instructions}")
            time.sleep(1)

        if self.exit_condition(sensor, context):
            print("Exit condition met, proceeding to the next step.")
        else:
            print(f"Max wait time of {self.max_wait_time} seconds reached, proceeding to the next step.")

        self.mark_complete()
