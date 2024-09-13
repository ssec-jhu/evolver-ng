import SensorManager from evolver.sensor_calibration.sensor_manager
import CalibrationStep, InstructionStep, LoopStep, WaitStep, InputReferenceStep, ReadSensorDataStep from evolver.sensor_calibration.calibration_step
import CalibrationProcedure from evolver.sensor_calibration.calibration_procedure
import TempSensor from evolver.sensor_calibration.calibration_data

# A custom step to set the ambient temperature in the calibration procedure context.
class SetAmbientTemperatureStep(CalibrationStep):
    def __init__(self, temperature: float):
        """
        Initialize the SetAmbientTemperatureStep with a target temperature.

        :param temperature: The target ambient temperature to set.
        """
        super().__init__(name=f"Set Ambient Temperature to {temperature}°C", instructions=f"Set the device to {temperature}°C.", input_required=True, global_step=True)
        self.temperature = temperature

    def action(self, context, ambient_temp=None):
        """
        Set the ambient temperature in the calibration procedure context and instruct the user.

        :param context: The calibration procedure's context dictionary.
        :param ambient_temp: The ambient temperature entered by the user, which should match the target temperature.
        """
        if ambient_temp is not None:
            if ambient_temp == self.temperature:
                context['ambient_temperature'] = ambient_temp
                print(f"Ambient temperature set to {ambient_temp}°C.")  # This would be a UI/API message in a real system
                self.mark_complete()
            else:
                print(f"Expected ambient temperature is {self.temperature}°C. Please set the correct temperature.")


class TempSensorCalibrationProcedure(CalibrationProcedure):
    def __init__(self, sensors):
        super().__init__(sensor_type="temperature", sensors=sensors)
        sensor_ids = [sensor.id for sensor in sensors]
        
        # Step 1: Global instruction to fill vials with 15ml water
        self.add_step(InstructionStep(f"Fill the vials associated with sensors {sensor_ids} with 15ml of water.", global_step=True))

        # Step 2: Global wait for 5 minutes
        self.add_step(WaitStep(instructions="Wait for 5 minutes.", max_wait_time=300, exit_condition=lambda sensor, context: False, global_step=True))

        # Step 3: Set ambient temperature to 20°C
        self.add_step(SetAmbientTemperatureStep(temperature=20, global_step=True))

        # Step 4: Loop through the following steps for each sensor
        def sensor_loop_steps():
            steps = []
            steps.append(InstructionStep("Place the thermometer in the water bath."))
            steps.append(InstructionStep("Wait for the temperature to stabilize."))
            steps.append(InputReferenceStep(reference_type="temperature"))
            steps.append(ReadSensorDataStep())

            # Fit the model after gathering sensor data
            steps.append(CalculateFitStep())

            # Show the fit model for the sensor
            steps.append(InstructionStep(f"The fit model for sensor {{sensor.id}} is displayed."))

            # Notify that the calibration for this sensor is complete
            steps.append(InstructionStep(f"Sensor {{sensor.id}} calibration complete. Moving to the next sensor."))

            return steps

        # LoopStep for all selected sensors, stopping once all are calibrated
        self.add_step(LoopStep(
            name="Sensor Calibration Loop - 20°C",
            steps=sensor_loop_steps(),
            exit_condition=lambda sensor, context: all(sensor.calibration_data.fit_model is not None for sensor in sensors)
        ))

        # Step 5: Set ambient temperature to 30°C and repeat loop
        self.add_step(SetAmbientTemperatureStep(temperature=40, global_step=True))
        self.add_step(LoopStep(
            name="Sensor Calibration Loop - 30°C",
            steps=sensor_loop_steps(),
            exit_condition=lambda sensor, context: all(sensor.calibration_data.fit_model is not None for sensor in sensors)
        ))

        # Step 6: Set ambient temperature to 40°C and repeat loop
        self.add_step(SetAmbientTemperatureStep(temperature=50, global_step=True))
        self.add_step(LoopStep(
            name="Sensor Calibration Loop - 40°C",
            steps=sensor_loop_steps(),
            exit_condition=lambda sensor, context: all(sensor.calibration_data.fit_model is not None for sensor in sensors)
        ))

        # Step 7: Global step to display all calibration data for each selected sensor
        self.add_step(InstructionStep("Displaying all calibration data for each selected sensor.", global_step=True))

        # Step 8: Global step to prompt the user to confirm the fits are linear
        self.add_step(InstructionStep("Please confirm if the fits for the sensors you just calibrated are linear.", global_step=True))

        # Step 9: Global step to end the procedure
        self.add_step(InstructionStep("Calibration procedure complete.", global_step=True))

# Example usage of the TempSensorCalibrationProcedure
sensor_manager = SensorManager()
sensor_manager.register_sensor("temp_sensor_1", TempSensor("temp_sensor_1"))
sensor_manager.register_sensor("temp_sensor_2", TempSensor("temp_sensor_2"))

selected_sensors = sensor_manager.select_sensors_for_calibration(["temp_sensor_1", "temp_sensor_2"])

# Initialize the calibration procedure
calibration_procedure = TempSensorCalibrationProcedure(selected_sensors)

# Run the calibration procedure
calibration_procedure.run()
