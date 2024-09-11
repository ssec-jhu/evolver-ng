"""
A SensorManager class is used to track and register and manage sensors by their unique IDs.

I'm aware the Evolver SDK likely provides similar functionality, this is a simplified version to show the minimal requirements for managing sensors.

The SensorManager class provides CRUD functionality for CalibrationData associated with each sensor on the device.

Example usage.
# Initialize the SensorManager
sensor_manager = SensorManager()

# Register sensors

# in this example a sensor for vials 1 and 2 is registered, the key is a concatenation of the sensor type and the vial number.
sensor_manager.register_sensor("temp_sensor_1", temp_sensor)
sensor_manager.register_sensor("temp_sensor_2", temp_sensor)

# Select sensors for calibration
selected_sensors = sensor_manager.select_sensors_for_calibration(["temp_sensor_1", "temp_sensor_2"])

# Read data from all sensors
sensor_data = sensor_manager.read_sensors()

# List all sensors
sensor_ids = sensor_manager.list_sensors()

"""


class SensorManager:
    def __init__(self):
        """
        Initialize the SensorManager with an empty dictionary for storing sensors by their IDs.
        """
        self.sensors = {}  # Dictionary to store sensors by their unique IDs

    def register_sensor(self, sensor_id: str, sensor: Any):
        """
        Register a sensor by its ID.

        :param sensor_id: A unique identifier for the sensor (e.g., "temp_sensor_1").
        :param sensor: The sensor object that contains sensor-specific methods and data.
        """
        self.sensors[sensor_id] = sensor

    def get_sensor(self, sensor_id: str) -> Any:
        """
        Retrieve a sensor by its ID.

        :param sensor_id: The ID of the sensor to retrieve.
        :return: The sensor object if found, None if the sensor ID does not exist.
        """
        return self.sensors.get(sensor_id)

    def select_sensors_for_calibration(self, sensor_ids: list[str]) -> list[Any]:
        """
        Select sensors for calibration based on a list of sensor IDs.

        :param sensor_ids: A list of sensor IDs to select.
        :return: A list of sensor objects corresponding to the provided sensor IDs.
        """
        return [self.get_sensor(sensor_id) for sensor_id in sensor_ids if sensor_id in self.sensors]

    def read_sensors(self) -> dict[str, Any]:
        """
        Read data from all registered sensors. This can be used to retrieve the current state or data
        from all sensors.

        :return: A dictionary mapping sensor IDs to their corresponding sensor data.
        """
        sensor_data = {}
        for sensor_id, sensor in self.sensors.items():
            # Assuming each sensor has a 'read' method that retrieves its current data
            sensor_data[sensor_id] = sensor.read()
        return sensor_data

    def remove_sensor(self, sensor_id: str):
        """
        Remove a sensor from the manager by its ID.

        :param sensor_id: The ID of the sensor to remove.
        """
        if sensor_id in self.sensors:
            del self.sensors[sensor_id]

    def list_sensors(self) -> list[str]:
        """
        List all registered sensor IDs.

        :return: A list of all registered sensor IDs.
        """
        return list(self.sensors.keys())
