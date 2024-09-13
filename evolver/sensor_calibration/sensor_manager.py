from typing import List, Dict

"""
The SensorManager class is responsible for tracking, registering, and managing sensors by their unique IDs.

This class provides basic CRUD functionality for managing sensors and their associated CalibrationData on the device.
It allows for the registration of sensors, selecting sensors for calibration, reading data from sensors, and removing or 
listing sensors. Each sensor is expected to implement a 'read()' method for retrieving its current data.


The SensorManager is designed to handle generic Sensor objects, each of which contains a CalibrationData instance
that stores calibration points and fit models. Note, a sensor's calibration data is only set once a CalibrationProcedure has completed.
This ensures that the calibration data is only updated when a calibration procedure for that sensor has been successfully executed.
"""


class SensorManager:
    def __init__(self):
        """
        Initialize the SensorManager with an empty dictionary for storing sensors by their IDs.
        """
        self.sensors: Dict[str, Sensor] = {}  # Dictionary to store sensors by their unique IDs

    def register_sensor(self, sensor_id: str, sensor: Sensor):
        """
        Register a sensor by its ID, but ensure that duplicate registration is avoided unless explicitly intended.
        """
        if sensor_id in self.sensors:
            print(f"Warning: Sensor ID {sensor_id} is already registered. Overwriting the existing sensor.")
        self.sensors[sensor_id] = sensor

    def get_sensor(self, sensor_id: str) -> Sensor:
        """
        Retrieve a sensor by its ID.

        :param sensor_id: The ID of the sensor to retrieve.
        :return: The sensor object if found, None if the sensor ID does not exist.
        """
        return self.sensors.get(sensor_id)

    def select_sensors_for_calibration(self, sensor_ids: List[str]) -> List[Sensor]:
        """
        Select sensors for calibration based on a list of sensor IDs.

        :param sensor_ids: A list of sensor IDs to select.
        :return: A list of sensor objects corresponding to the provided sensor IDs.
        """
        return [self.get_sensor(sensor_id) for sensor_id in sensor_ids if sensor_id in self.sensors]

    def read_sensors(self) -> Dict[str, dict]:
        """
        Read data from all registered sensors. This can be used to retrieve the current state or data
        from all sensors.

        :return: A dictionary mapping sensor IDs to their corresponding sensor data.
        """
        sensor_data = {}
        for sensor_id, sensor in self.sensors.items():
            # Using the read method implemented in Sensor class
            sensor_data[sensor_id] = sensor.read()
        return sensor_data

    def remove_sensor(self, sensor_id: str):
        """
        Remove a sensor from the manager by its ID.
        Raise an error if the sensor is not found.
        """
        if sensor_id in self.sensors:
            del self.sensors[sensor_id]
        else:
            print(f"Warning: Sensor ID {sensor_id} not found. No sensor removed.")

    def list_sensors(self) -> List[str]:
        """
        List all registered sensor IDs.

        :return: A list of all registered sensor IDs.
        """
        return list(self.sensors.keys())
