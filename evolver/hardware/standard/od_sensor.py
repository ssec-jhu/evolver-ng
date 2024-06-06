from pydantic import Field
from evolver.hardware.interface import SensorDriver, VialBaseModel, VialConfigBaseModel
from evolver.serial import SerialData


class ODSensor(SensorDriver):
    """Optical density sensor driver

    This driver represents a family of sensors for turbidity which are read by
    integrating a specified number of ADC readings per vial.
    """
    class Config(VialConfigBaseModel):
        addr: str = Field(description="Address of od sensor on serial bus (e.g. od_90)")
        integrations: int = Field(500, description="on read, request average of this number of ADC reads")

    class Output(VialBaseModel):
        raw: int
        od: float = None

    def read(self):
        self.outputs = {}
        cmd_data = str(self.integrations).encode()
        cmd = SerialData(addr=self.addr, data=[cmd_data], kind='r')
        with self.evolver.serial as comm:
            response = comm.communicate(cmd)
        for vial, raw in enumerate(response.data):
            self.outputs[vial] = self.Output(vial=vial, raw=raw)
