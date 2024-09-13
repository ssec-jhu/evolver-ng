import time
import asyncio
import calculate_linear_fit from evolver.sensor_calibration.linear_fit

# Base class for all calibration steps
class CalibrationStep:
    def __init__(self, name: str, instructions: str = "", input_required: bool = False):
        """
        Initialize the CalibrationStep with a name, instructions, and a flag indicating if user input is required.

        :param name: The name of the step.
        :param instructions: Instructions to be shown to the user.
        :param input_required: Whether user input is required to complete this step.
        """
        self.name = name
        self.instructions = instructions
        self.input_required = input_required

    async def action(self, context=None):
        """
        Perform the action for the step. Must be implemented by subclasses.

        :param context: Optional context dictionary to store shared information between steps.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    def is_complete(self) -> bool:
        """
        Check if the step has been completed. Must be implemented by subclasses.

        :return: True if the step is complete, otherwise False.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    def reset(self):
        """
        Reset the step's completion status. Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement this method.")


# GlobalCalibrationStep applies to all sensors collectively
# GlobalCalibrationStep applies to all sensors collectively
class GlobalCalibrationStep(CalibrationStep):
    def __init__(self, name: str, instructions: str = "", input_required: bool = False):
        """
        Initialize the GlobalCalibrationStep.

        :param name: The name of the step.
        :param instructions: Instructions to be shown to the user.
        :param input_required: Whether user input is required to complete this step.
        """
        super().__init__(name, instructions, input_required)
        self.completed = False  # Tracks if the step is completed

    async def action(self, context=None):
        """
        Perform the global action. To be implemented by subclasses if needed.

        :param context: Optional context dictionary to store shared information between steps.
        """
        pass  # Implement the action logic in subclasses if needed

    def is_complete(self) -> bool:
        """
        Check if the global step has been completed.

        :return: True if the step is complete, otherwise False.
        """
        return self.completed

    def mark_complete(self):
        """
        Mark the global step as complete.
        """
        self.completed = True

    def reset(self):
        """
        Reset the completion status of the global step.
        """
        self.completed = False

# SensorCalibrationStep applies to individual sensors and tracks per-sensor completion
class SensorCalibrationStep(CalibrationStep):
    def __init__(self, name: str, instructions: str = "", input_required: bool = False):
        """
        Initialize the SensorCalibrationStep.

        :param name: The name of the step.
        :param instructions: Instructions to be shown to the user.
        :param input_required: Whether user input is required to complete this step.
        """
        super().__init__(name, instructions, input_required)
        self.completed_sensors = set()  # Set to track sensors that have completed the step

    async def action(self, sensor, context=None):
        """
        Perform the action for a specific sensor. Must be implemented by subclasses.

        :param sensor: The sensor object that this step is operating on.
        :param context: Optional context dictionary to store shared information between steps.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    def mark_complete(self, sensor_id):
        """
        Mark the step as complete for a specific sensor.

        :param sensor_id: The ID of the sensor that has completed the step.
        """
        self.completed_sensors.add(sensor_id)

    def is_complete(self, sensor_id=None) -> bool:
        """
        Check if the step has been completed for a specific sensor.

        :param sensor_id: The ID of the sensor to check.
        :return: True if the step is complete for the sensor, otherwise False.
        """
        if sensor_id:
            return sensor_id in self.completed_sensors
        else:
            return False  # If sensor_id is not provided, return False

    def reset(self):
        """
        Reset the completion status for all sensors.
        """
        self.completed_sensors.clear()

# Example of a GlobalCalibrationStep subclass
class InstructionGlobalStep(GlobalCalibrationStep):
    def __init__(self, instructions: str):
        """
        Initialize the InstructionGlobalStep with given instructions.

        :param instructions: Instructions to be shown to the user.
        """
        super().__init__(name="Global Instruction", instructions=instructions, input_required=True)

    async def action(self, context=None):
        """
        Display instructions to the user. The user will acknowledge and mark the step as complete.

        :param context: Optional context dictionary.
        """
        # Send the instructions to the UI or logging system
        print(self.instructions)
        # Since we can't block, we return control and wait for user acknowledgment
        pass

    def mark_instruction_complete(self):
        """
        Mark the instruction as complete, typically called when the user acknowledges the instruction.
        """
        self.mark_complete()


# SensorInstructionStep provides dynamic, sensor-specific instructions
class InstructionSensorStep(SensorCalibrationStep):
    def __init__(self, instructions_template: str):
        """
        Initialize the InstructionSensorStep with an instructions template.

        :param instructions_template: A template string for the instructions, which can include placeholders for sensor attributes.
        """
        super().__init__(name="Sensor Instruction", instructions="", input_required=True)
        self.instructions_template = instructions_template

    async def action(self, sensor, context=None):
        """
        Display sensor-specific instructions to the user. The user will acknowledge and mark the step as complete for each sensor.

        :param sensor: The sensor object that this step is operating on.
        :param context: Optional context dictionary.
        """
        # Format the instructions using sensor-specific information
        self.instructions = self.instructions_template.format(
            sensor_id=sensor.id,
            sensor_type=sensor.calibration_data.sensor_type
        )
        # Send the instructions to the UI or logging system
        print(f"Instructions for sensor {sensor.id}: {self.instructions}")
        # Since we can't block, we return control and wait for user acknowledgment
        pass

    def mark_instruction_complete(self, sensor_id):
        """
        Mark the instruction as complete for a specific sensor, typically called when the user acknowledges the instruction.

        :param sensor_id: The ID of the sensor that has completed the instruction.
        """
        self.mark_complete(sensor_id)



# Example of a SensorCalibrationStep subclass
class ReadSensorDataStep(SensorCalibrationStep):
    def __init__(self):
        """
        Initialize the ReadSensorDataStep.
        """
        super().__init__(name="Read Sensor Data", instructions="Reading data from sensor...", input_required=False)

    async def action(self, sensor, context=None):
        """
        Read data from the sensor and store it in the procedure's calibration data.

        :param sensor: The sensor object.
        :param context: Context dictionary containing the procedure and other info.
        """
        # Simulate reading data from the sensor
        sensor_data = await sensor.read()
        # Access the procedure's calibration data
        procedure = context['procedure']
        calibration_data = procedure.session_calibration_data[sensor.id]
        # Store the data in the procedure's calibration data
        calibration_data.add_calibration_point(
            reference_data=None,  # Reference data will be added in a separate step
            system_data=sensor_data["data"]
        )
        print(f"Sensor data for {sensor.id}: {sensor_data}")
        # Mark this step as complete for the sensor
        self.mark_complete(sensor.id)


# Another example of a SensorCalibrationStep subclass
class InputReferenceValueStep(SensorCalibrationStep):
    def __init__(self, reference_type: str):
        """
        Initialize the InputReferenceValueStep.

        :param reference_type: The type of reference value expected (e.g., "temperature").
        """
        super().__init__(name=f"Input {reference_type} Reference Value", input_required=True)
        self.reference_type = reference_type
        self.reference_values = {}  # Dictionary to store reference values per sensor ID

    async def action(self, sensor, context=None):
        """
        Request the reference value from the user for a specific sensor.

        :param sensor: The sensor object.
        :param context: Optional context dictionary.
        """
        self.instructions = f"Please input the {self.reference_type} for sensor {sensor.id}."
        # Send the instructions to the UI or logging system
        print(self.instructions)
        # Since we can't block, we return control and wait for user input
        pass

    def set_reference_value(self, sensor_id, value):
        """
        Set the reference value for a specific sensor, called when the user provides the input.

        :param sensor_id: The ID of the sensor.
        :param value: The reference value provided by the user.
        """
        if not isinstance(value, (int, float)):
            raise ValueError("Reference value must be a number.")
        # Access the procedure's calibration data
        calibration_data = self.context['procedure'].session_calibration_data[sensor_id]
        # Update the calibration data within the procedure
        for point in calibration_data.calibration_points:
            if point["reference_data"] is None:
                point["reference_data"] = value
                break  # Update the first point without reference data
        # Mark this step as complete for the sensor
        self.mark_complete(sensor_id)




# Example of a GlobalCalibrationStep subclass for calculating the fit model
# TODO: the CalibrationProcedure should have a method to store the calibration data for each sensor once the procedure reaches the end.
# Right now this step saves the procedure session calibration data to the SensorManager.
class CalculateFitGlobalStep(GlobalCalibrationStep):
    def __init__(self):
        """
        Initialize the CalculateFitGlobalStep.
        """
        super().__init__(name="Calculate Fit", instructions="Calculating fit model...", input_required=False)

    async def action(self, context=None):
        """
        Calculate the fit model for each sensor based on their calibration data within the procedure.

        :param context: Context dictionary containing the procedure and other info.
        """
        procedure = context['procedure']
        sensors = context.get("sensors", [])
        for sensor in sensors:
            # Access the procedure's calibration data
            calibration_data = procedure.session_calibration_data[sensor.id]
            # Extract raw voltages and reference values
            raw_voltages = [
                point["system_data"]["voltage"]
                for point in calibration_data.calibration_points
                if "voltage" in point["system_data"]
            ]
            reference_values = [
                point["reference_data"]
                for point in calibration_data.calibration_points
                if point["reference_data"] is not None
            ]
            # Check if we have enough data points
            if len(raw_voltages) >= 2 and len(reference_values) >= 2:
                # Perform linear fit (assuming calculate_linear_fit is implemented)
                fit_model = calculate_linear_fit(raw_voltages, reference_values)
                calibration_data.set_fit_model(fit_model)
                print(f"Fit model for sensor {sensor.id}: {fit_model}")
                # Update the sensor's calibration data
                sensor.calibration_data = calibration_data
            else:
                print(f"Not enough data to calculate fit for sensor {sensor.id}")
        # Mark the step as complete
        self.mark_complete()


