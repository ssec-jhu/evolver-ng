from pydantic import Field

from evolver.connection.interface import Connection
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
        serial_conn: Connection | None = Field(None, description="serial connection, default is that on evolver")

    class Output(VialBaseModel):
        raw: int
        density: float = None

    @property
    def serial(self):
        return self.serial_conn or self.evolver.serial

    def read(self):
        self.outputs = {}
        cmd_data = str(self.integrations).encode()
        cmd = SerialData(addr=self.addr, data=[cmd_data], kind="r")
        with self.serial as comm:
            response = comm.communicate(cmd)
        for vial, raw in enumerate(response.data):
            if vial in self.vials:
                self.outputs[vial] = self.Output(vial=vial, raw=raw)
