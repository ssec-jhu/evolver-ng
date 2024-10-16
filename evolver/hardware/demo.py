from copy import copy

from evolver.hardware.interface import EffectorDriver, SensorDriver


class NoOpSensorDriver(SensorDriver):
    class Config(SensorDriver.Config):
        name: str = "NoOpSensorDriver"
        echo_raw: int = 1  # Default value for raw sensor output
        echo_val: int = 2  # Default value for calibrated sensor output

    class Output(SensorDriver.Output):
        raw: int
        value: int

    def read(self):
        """Simulate reading data from sensors, applying transformations if a calibrator is present."""
        self.outputs = {
            i: self.Output(
                name=self.name,
                vial=i,
                raw=self.echo_raw,
                value=self._transform("output_transformer", "convert_to", self.echo_val, i),
            )
            for i in self.vials
        }
        return self.outputs

    def get(self):
        return self.outputs


class NoOpEffectorDriver(EffectorDriver):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aborted = False

    def commit(self):
        self.committed = copy(self.proposal)

    def off(self):
        pass