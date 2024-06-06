from copy import copy

from evolver.hardware.interface import BaseCalibrator, EffectorDriver, SensorDriver, VialConfigBaseModel


class NoOpSensorDriver(SensorDriver):
    class Config(VialConfigBaseModel):
        echo_raw: int = 1
        echo_val: int = 2

    def read(self):
        self.outputs = {i: self.Output(vial=i, raw=self.echo_raw, value=self.echo_val) for i in self.vials}

    def get(self):
        return self.outputs


class NoOpEffectorDriver(EffectorDriver):
    def commit(self):
        self.comitted = copy(self.proposal)


class NoOpCalibrator(BaseCalibrator):
    @property
    def status(self):
        return True
