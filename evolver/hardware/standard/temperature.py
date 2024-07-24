from copy import copy

from pydantic import Field

from evolver.hardware.interface import (
    EffectorDriver,
    SensorDriver,
    VialBaseModel,
)
from evolver.hardware.standard.base import SerialDeviceConfigBase, SerialDeviceOutputBase
from evolver.serial import SerialData


class Temperature(SensorDriver, EffectorDriver):
    """Temperature sensor and heater package.

    Goes over the evolver serial protocol and is capable of both reading the current
    temperature value as well as setting a target for heating. A particular raw value
    stands in for off (HEAT_OFF property of this class).
    """

    HEAT_OFF = b"4095"

    class Config(SerialDeviceConfigBase, EffectorDriver.Config):
        pass

    class Output(SerialDeviceOutputBase):
        temperature: float = Field(None, description="Sensor temperature in degrees celcius")

    class Input(VialBaseModel):
        temperature: float = Field(None, description="Target temperature in degrees celcius")

    @property
    def serial(self):
        return self.serial_conn or self.evolver.serial

    def _do_serial(self, from_proposal=False):
        data = [self.HEAT_OFF] * self.slots
        # since a read is also a send, we load all committed values as a base and
        # in the case of proposals overwrite with new data.
        inputs = copy(self.committed)
        if from_proposal:
            inputs.update({k: v for k, v in self.proposal.items() if k in self.vials})
        for vial, input in inputs.items():
            # calibration from real to raw should go here
            raw = int(input.temperature)
            data[vial] = str(raw).encode()
        with self.serial as comm:
            response = comm.communicate(SerialData(addr=self.addr, data=data))
        self.committed = inputs
        return response

    def read(self):
        self.outputs.clear()
        response = self._do_serial()
        for vial, raw in enumerate(response.data):
            if vial in self.vials:
                # calibration should happen here to populate temperature field from raw
                self.outputs[vial] = self.Output(vial=vial, raw=int(raw))

    def commit(self):
        self._do_serial(from_proposal=True)
