class Sensor:
    """
    A generic Sensor class that contains a sensor_id and CalibrationData.
    """

    def __init__(self, sensor_id):
        self.id = sensor_id
        self.calibration_data = CalibrationData()

    async def read_async(self) -> dict:
        """
        Mock async method to simulate reading the raw voltage from the sensor.
        This would be replaced by actual sensor reading logic depending on the sensor type.

        :return: A dictionary containing the sensor data.
        """
        # Simulate I/O delay
        await asyncio.sleep(0.1)
        # Return mocked sensor data
        return {
            "sensor_id": self.id,
            "data": {"voltage": 0.75, "time": "2024-09-11T10:15:30"},
        }


class CalibrationData:
    """
    The CalibrationData class stores calibration points and the fit model, derived from those points.
    It fundamentally it pairs reference and system data points together to allow fitting a model for each sensor.
    """

    def __init__(self):
        self.calibration_points = []  # Store multiple real-world and system data points
        self.fit_model = None  # Store the computed fit model

    def add_calibration_point(self, reference_data, system_data):
        """
        Add a calibration point that pairs reference data (e.g., temperature, pressure) with system data
        (e.g., raw voltage).

        :param reference_data: Known reference values (e.g., temperature, optical density).
        :param system_data: Measured sensor values (e.g., raw voltage, system time).
        """
        self.calibration_points.append(
            {
                "reference_data": reference_data,
                "system_data": system_data,
            }
        )

    def set_fit_model(self, model):
        self.fit_model = model