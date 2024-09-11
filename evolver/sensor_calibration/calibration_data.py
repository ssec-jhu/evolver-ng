"""
Each sensor registered with the SensorManager has a unique ID and a CalibrationData object associated with it.
The CalibrationData object stores calibration points that are later used to fit a model to the data.
"""


class TempSensor:
    def __init__(self, sensor_id):
        self.id = sensor_id
        self.calibration_data = CalibrationData(sensor_type="temperature")


class ODSensor:
    def __init__(self, sensor_id):
        self.id = sensor_id
        self.calibration_data = CalibrationData(sensor_type="optical_density")


"""
The CalibrationData class pairs sets of reference and on-board data points together for each sensor.
This is used to fit a model to the data points and store the model for future use.
TODO: the fit_model should be named... so users can fit metadata, e.g. "name", "last_calibrated".
"""


class CalibrationData:
    def __init__(self, sensor_type):
        self.sensor_type = sensor_type
        self.calibration_points = []  # List to store multiple real-world and system data points
        self.fit_model = None  # Store the computed fit model

    def add_calibration_point(self, real_world_data, system_data):
        # real_world_data and system_data are dictionaries with flexible key-value pairs
        self.calibration_points.append(
            {
                "real_world_data": real_world_data,  # Real-world values like temp, pressure, etc.
                "system_data": system_data,  # System values like raw voltage, time, etc.
            }
        )

    def set_fit_model(self, model):
        self.fit_model = model


"""
Example.
{
  "sensor_id": "complex_sensor_1",
  "calibration_points": [
    {
      "real_world_data": {
        "temperature": 25.0,
        "air_pressure": 1013.25,
        "altitude": 100
      },
      "system_data": {
        "raw_voltage": 0.75,
        "system_voltage": 5.0,
        "current_time": "2024-09-11T10:15:30"
      }
    }
  ],
  "fit_model": {
    "type": "linear",
    "slope": 50.0,
    "intercept": -12.5,
    "name": "Temperature Sensor Fit",
    "date_calibrated": "2024-09-11T10:15:30"
  }
}

"""
