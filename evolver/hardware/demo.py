from copy import copy

from evolver.hardware.interface import EffectorDriver, SensorDriver


class NoOpSensorDriver(SensorDriver):
    class Config(SensorDriver.Config):
        echo_raw: int = 1
        echo_val: int = 2

    class Output(SensorDriver.Output):
        raw: int
        value: int

    def read(self):
        self.outputs = {i: self.Output(vial=i, raw=self.echo_raw, value=self.echo_val) for i in self.vials}
        return self.outputs

    def get(self):
        return self.outputs


class NoOpEffectorDriver(EffectorDriver):
    def commit(self):
        self.comitted = copy(self.proposal)
