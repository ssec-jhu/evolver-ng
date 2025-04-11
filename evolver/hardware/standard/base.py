from pydantic import Field

from evolver.base import ConfigDescriptor
from evolver.hardware.interface import VialBaseModel, VialConfigBaseModel


class SerialDeviceConfigBase(VialConfigBaseModel):
    addr: str = Field(description="Address of od sensor on serial bus (e.g. od_90)")
    slots: int = Field(16, description="Total slots expected irrespective of attached vials")
    serial_conn: ConfigDescriptor | None = Field(None, description="serial connection, default is that on evolver")


class SerialDeviceOutputBase(VialBaseModel):
    raw: int | bytes | None
