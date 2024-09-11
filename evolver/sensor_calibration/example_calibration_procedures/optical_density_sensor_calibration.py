from evolver.sensor_calibration.sensor_manager import SensorManager
from evolver.sensor_calibration.calibration_step import CalibrationStep, LoopStep
from evolver.sensor_calibration.calibration_procedure import MultiSensorCalibrationProcedure

class ReadOpticalDensityStep(CalibrationStep):
    def __init__(self):
        super().__init__(name="Read Optical Density", instructions="Read optical density from sensor")

    def action(self, device, sensor, reference_plate):
        # Read the optical density from the sensor
        optical_density = device.read_optical_density(sensor.id)
        # Store the optical density and the corresponding reference plate value
        sensor.calibration_data.add_calibration_point(
            real_world_data={"optical_density": reference_plate},
            system_data={"raw_voltage": optical_density}
        )
        self.mark_complete()  # Mark the step as complete

class MoveReferencePlateStep(CalibrationStep):
    def __init__(self):
        super().__init__(name="Move Reference Plate", instructions="Move reference plate to the next sensor")

    def action(self, device, sensors):
        # This step assumes the user manually moves the plates and marks the step complete
        print("Please move the reference plates forward by one position.")
        self.mark_complete()  # The user marks this step as complete via the UI or API

def all_reference_plates_processed(device, sensors):
    """
    Exit condition: Check if each sensor has 16 calibration points.
    
    :param device: The hardware device.
    :param sensors: List of sensor objects.
    :return: True if all sensors have 16 calibration points, False otherwise.
    """
    return all(len(sensor.calibration_data.calibration_points) >= 16 for sensor in sensors)

class OpticalDensityCalibrationProcedure(MultiSensorCalibrationProcedure):
    def __init__(self, sensors, reference_plates):
        super().__init__(sensor_type="optical_density", sensors=sensors)

        # Define loop steps: Read optical density and then move reference plates
        loop_steps = [
            ReadOpticalDensityStep(),  # Read OD for each sensor
            MoveReferencePlateStep()  # Move reference plates to the next sensor
        ]

        # Add a looping step that repeats until all sensors have 16 calibration points
        self.add_step(LoopStep(
            name="Optical Density Calibration Loop",
            steps=loop_steps,
            exit_condition=all_reference_plates_processed  # Exit the loop when each sensor has 16 points
        ))

        # Add a final step for calculating the fit for each sensor
        self.add_step(CalculateFitStep())
