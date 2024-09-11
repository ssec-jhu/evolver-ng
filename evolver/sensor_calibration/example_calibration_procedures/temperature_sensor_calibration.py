import SensorManager from evolver.sensor_calibration.sensor_manager
import CalibrationStep, InstructionStep, MultiSensorCalibrationProcedure from evolver.sensor_calibration.calibration_step
import MultiSensorCalibrationProcedure from evolver.sensor_calibration.calibration_procedure
import TempSensor from evolver.sensor_calibration.calibration_data

# Behind the scenes: Register the sensors the procedure will available to be run on by default this is done automatically (for each sensor on each vial) by the framework.
# I'm ignoring the wider context here, I am presuming Sensor Manager is a stand-in for the Hardware class and if not the hardware class can be extended to do the same thing as the sensor manager.

# Step 1: Define the calibration steps
class InputReferenceTemperatureStep(CalibrationStep):
    def __init__(self):
        super().__init__(name="Prompt user to input real-world Values", instructions="Enter the temperature you measured", input_required=True)

    def action(self, device, sensor, real_world_values=None):
        if real_world_values is not None:
            # real_world_values is a dictionary with multiple real-world data points
            # Example: {'temperature': 25.0, 'air_pressure': 1013.25, 'altitude': 100}
            sensor.calibration_data.add_calibration_point(real_world_data=real_world_values, system_data={})

class CollectVoltageStep(CalibrationStep):
    def __init__(self):
        super().__init__(name="Collect Sensor voltage Data", instructions="Collect raw voltage reading from the sensor")

    def action(self, device, sensor):
        # Collect system data points - TODO use the Evolver SDK to do this
        raw_voltage = device.collect_voltage(sensor.id)

        # Store these system data points in the calibration data
        system_data = {
            'raw_voltage': raw_voltage,
        }
        sensor.calibration_data.add_calibration_point(real_world_data={}, system_data=system_data)
        
class CalculateFitStep(CalibrationStep):
    def __init__(self):
        super().__init__(name="Calculate Fit", instructions="Calculate the fit model for the sensor")

    def action(self, device, sensor):
        # Get raw voltage and real-world values
        raw_voltages = [point['raw_voltage'] for point in sensor.calibration_data.calibration_points if point['raw_voltage'] is not None]
        real_values = [point['real_value'] for point in sensor.calibration_data.calibration_points if point['real_value'] is not None]
        
        # Calculate the fit (linear fit in this example)
        fit_model = calculate_linear_fit(raw_voltages, real_values)
        # Store the fit model in the sensor's calibration data
        sensor.calibration_data.set_fit_model(fit_model)
        print(f"Fit model for {sensor.id}: {fit_model}")

# Step 2: Define the calibration procedure
class TemperatureCalibrationProcedure(MultiSensorCalibrationProcedure):
    def __init__(self, sensors):
        super().__init__(sensor_type="temperature", sensors=sensors)
        # Add the steps to the calibration procedure
        self.add_step(InstructionStep("Fill each vial with 15ml water"))
        self.add_step(InstructionStep("Turn on the 5v power and wait 5 minutes"))
        self.add_step(InstructionStep("Please input the reference temperature for each sensor."))
        self.add_step(InputReferenceTemperatureStep())
        self.add_step(InputRealTemperatureStep())
        self.add_step(CollectVoltageStep())
        self.add_step(CalculateFitStep())

# Step 3: Register sensors with the SensorManager which keeps track of all available sensors, and the calibration points recorded
# Register temperature sensors with their IDs, id is a concatenation of the sensor type and the vial number, this step is done automatically by the framework

sensor_manager = SensorManager()
sensor_manager.register_sensor("temp_sensor_2", TempSensor("temp_sensor_2"))
sensor_manager.register_sensor("temp_sensor_7", TempSensor("temp_sensor_7"))

# Step 4: Select sensors for calibration
selected_sensors = sensor_manager.select_sensors_for_calibration(["temp_sensor_2", "temp_sensor_7"])

# Step 5: Initialize the calibration procedure for the selected sensors
calibration_procedure = TemperatureCalibrationProcedure(selected_sensors)

# Step 6: Run the calibration procedure, these steps will be controlled by the UI, via API calls.
# The user inputs 25.0°C for sensor 2 and 30.0°C for sensor 7
calibration_procedure.steps[0].action(device=None, sensor=sensor_manager.get_sensor("temp_sensor_2"), real_value=25.0)
calibration_procedure.steps[0].action(device=None, sensor=sensor_manager.get_sensor("temp_sensor_7"), real_value=30.0)
# Collect Voltage Step: The system collects raw voltage readings from both sensors.
calibration_procedure.steps[1].action(device=device, sensor=sensor_manager.get_sensor("temp_sensor_2"))
calibration_procedure.steps[1].action(device=device, sensor=sensor_manager.get_sensor("temp_sensor_7"))
# Calculate Fit Step: The system calculates the fit model for each sensor based on the collected data.
calibration_procedure.steps[2].action(device=device, sensor=sensor_manager.get_sensor("temp_sensor_2"))
calibration_procedure.steps[2].action(device=device, sensor=sensor_manager.get_sensor("temp_sensor_7"))
# Complete Calibration and Store Fit Model
print(sensor_manager.get_sensor("temp_sensor_2").calibration_data.fit_model)
# Output: {'slope': 50.0, 'intercept': -12.5}
print(sensor_manager.get_sensor("temp_sensor_7").calibration_data.fit_model)
# Output: {'slope': 62.5, 'intercept': -20.0}

# Use the fit model for future measurements
def apply_calibration(raw_voltage, fit_model):
    return fit_model["slope"] * raw_voltage + fit_model["intercept"]
# e.g. Sensor 2 new voltage reading
new_voltage_2 = 0.78
calibrated_temp_2 = apply_calibration(new_voltage_2, sensor_manager.get_sensor("temp_sensor_2").calibration_data.fit_model)
print(f"Calibrated temperature for sensor 2: {calibrated_temp_2}°C")
# Output: Calibrated temperature for sensor 2: 26.5°C


