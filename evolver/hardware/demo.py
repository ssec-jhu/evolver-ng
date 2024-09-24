from copy import copy

from evolver.hardware.interface import EffectorDriver, SensorDriver


class NoOpSensorDriver(SensorDriver):
    class Config(SensorDriver.Config):
        name: str = "NoOpSensorDriver"

    echo_raw: int = 1  # Default value for raw sensor output
    echo_val: int = 2  # Default value for calibrated sensor output

    class Output(SensorDriver.Output):
        name: str  # Set by BaseConfig normally, NoOpSensorDriver skips BaseConfig initialization so we set it in read(
        vial: int  # Set by VialBaseModel
        raw: int
        value: int

    def __init__(self, *args, name=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name if name else "no_op_sensor_driver_hardware_default_name"
        self.outputs: dict[int, self.Output] = {}  # Initialize outputs

    def read(self):
        """Simulate reading data from sensors, applying transformations if a calibrator is present."""
        # Check if a calibrator is attached and handle accordingly
        for i in self.vials:
            raw_value = self.echo_raw
            calibrated_value = self.echo_val

            # Apply transformation if calibrator and output_transformer are defined
            if self.calibrator and hasattr(self.calibrator, "output_transformer"):
                raw_value = self._transform("output_transformer", "convert_to", self.echo_raw, i)
                calibrated_value = self._transform("output_transformer", "convert_to", self.echo_val, i)

            self.outputs[i] = self.Output(name=self.name, vial=i, raw=raw_value, value=calibrated_value)

        return self.outputs

    def get(self):
        return self.outputs


class NoOpEffectorDriver(EffectorDriver):
    def commit(self):
        self.comitted = copy(self.proposal)
