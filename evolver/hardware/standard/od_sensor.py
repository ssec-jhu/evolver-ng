from pydantic import Field

from evolver.hardware.interface import SensorDriver
from evolver.hardware.standard.base import SerialDeviceConfigBase, SerialDeviceOutputBase
from evolver.serial import SerialData


class ODSensor(SensorDriver):
    """Optical density sensor driver

    This driver represents a family of sensors for turbidity which are read by
    integrating a specified number of ADC readings per vial.
    """

    class Config(SerialDeviceConfigBase):
        integrations: int = Field(500, description="on read, request average of this number of ADC reads")

    class Output(SerialDeviceOutputBase):
        density: float = None

    @property
    def serial(self):
        return self.serial_conn or self.evolver.serial

    def read(self):
        self.outputs = {}
        cmd = SerialData(addr=self.addr, data=[str(self.integrations).encode()], kind="r")
        with self.serial as comm:
            response = comm.communicate(cmd)
        for vial, raw in enumerate(response.data):
            if vial in self.vials:
                self.outputs[vial] = self.Output(vial=vial, raw=raw)
