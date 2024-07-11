from copy import copy

from pydantic import Field

from evolver.hardware.interface import EffectorDriver, VialBaseModel
from evolver.hardware.standard.base import SerialDeviceConfigBase
from evolver.serial import SerialData


class Stir(EffectorDriver):
    class Config(SerialDeviceConfigBase):
        stir_max: int = 98

    class Input(VialBaseModel):
        rate: int = Field(0, description="Stir rate setting")

    @property
    def serial(self):
        return self.serial_conn or self.evolver.serial

    def commit(self):
        inputs = copy(self.committed)
        inputs.update({v: i for v, i in self.proposal.items() if v in self.vials})
        cmd = [b"0"] * self.slots
        for v, i in inputs.items():
            cmd[v] = str(i.rate).encode()
        with self.serial as comm:
            comm.communicate(SerialData(addr=self.addr, data=cmd))
        self.committed = inputs
