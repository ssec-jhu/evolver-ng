from copy import copy

from pydantic import Field

from evolver.hardware.interface import EffectorDriver
from evolver.hardware.standard.base import SerialDeviceConfigBase
from evolver.serial import SerialData


class Stir(EffectorDriver):
    """Stirrer with integer rate settings.

    This implements the stirrer with very simple integer rate setting with no
    calibration. There is a max setting guardrail, which by default corresponds
    to the max rate available in arduino implementation.
    """

    class Config(SerialDeviceConfigBase, EffectorDriver.Config):
        stir_max: int = 98

    class Input(EffectorDriver.Input):
        rate: int = Field(0, description="Stir rate setting")

    @property
    def serial(self):
        return self.serial_conn or self.evolver.serial

    def commit(self):
        inputs = copy(self.committed)
        inputs.update({v: i for v, i in self.proposal.items() if v in self.vials})
        cmd = [b"0"] * self.slots
        for v, i in inputs.items():
            cmd[v] = str(max(0, min(i.rate, self.stir_max))).encode()
        with self.serial as comm:
            comm.communicate(SerialData(addr=self.addr, data=cmd))
        self.committed = inputs

    def off(self):
        cmd = [b"0"] * self.slots
        with self.serial as comm:
            comm.communicate(SerialData(addr=self.addr, data=cmd))
