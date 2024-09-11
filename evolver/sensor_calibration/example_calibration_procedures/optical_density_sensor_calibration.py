import SensorManager from evolver.sensor_calibration.sensor_manager
import CalibrationStep, MultiSensorCalibrationProcedure from evolver.sensor_calibration.calibration_step
import MultiSensorCalibrationProcedure from evolver.sensor_calibration.calibration_procedure

class ReadOpticalDensityStep(CalibrationStep):
    def __init__(self):
        super().__init__(name="Read Optical Density", instructions="Read optical density from sensor")
    
    def action(self, device, sensor, reference_plate):
        # read from the sensor 
        optical_density = device.read_optical_density(sensor.id)
        # Store the optical density and corresponding reference plate value
        sensor.calibration_data.add_calibration_point(
            real_world_data={"optical_density": reference_plate},
            system_data={"raw_voltage": optical_density}
        )

class MoveReferencePlateStep(CalibrationStep):
    def __init__(self):
        super().__init__(name="Move Reference Plate", instructions="Move reference plate to the next sensor")

    def action(self, device, sensors):
        # Assuming the user manually moves the plates and marks this step complete
        print("Please move the reference plates forward by one position.")

def all_reference_plates_processed(device, sensor_manager):
    # Check if we've done 16 iterations (i.e., each sensor has seen each reference plate)
    return sensor_manager.get_sensor("od_sensor_1").calibration_data.iterations >= 16

class OpticalDensityCalibrationProcedure(MultiSensorCalibrationProcedure):
    def __init__(self, sensors, reference_plates):
        super().__init__(sensor_type="optical_density", sensors=sensors)
        
        # Define loop steps: Read OD, then move plates
        loop_steps = [
            ReadOpticalDensityStep(),  # Read OD for each sensor
            MoveReferencePlateStep()  # Move reference plates to the next sensor
        ]

        # Define the loop with exit condition (after 16 iterations)
        self.add_step(LoopStep(
            name="Optical Density Calibration Loop",
            steps=loop_steps,
            exit_condition=all_reference_plates_processed
        ))

        # Final step: Calculate fit for each sensor
        self.add_step(CalculateFitStep())
