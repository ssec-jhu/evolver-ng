from abc import ABC, abstractmethod
from threading import RLock
from typing import Optional

import pydantic

from evolver.adapter.interface import Adapter
from evolver.connection.interface import Connection
from evolver.device import ConfigDescriptor


class VialConfigBaseModel(pydantic.BaseModel):
    vials: list[int] | None = None


class VialBaseModel(pydantic.BaseModel):
    vial: int


class BaseCalibrator(ABC):
    class Config(pydantic.BaseModel):
        calibfile: str = None

    def __init__(self, evovler = None, config: Config = Config()):
        self.config = config

    @property
    @abstractmethod
    def status(self):
        pass


class Device(ABC):
    class Config(pydantic.BaseModel):
        ...

    def __init__(self,
                 *args,
                 connection: Optional[Connection, ConfigDescriptor] = None,
                 controller: Optional[Adapter, ConfigDescriptor] = None,
                 sub_devices: Optional[dict[ConfigDescriptor]] = None,
                 connect=False,
                 **kwargs):
        self.connection = connection  # Maybe None for conglomerate device.
        self.controller = controller
        self.lock = RLock()
        self.sub_devices = sub_devices if sub_devices else {}  # For conglomerate devices.

        # A connection can only be null when sub devices exist.
        if (not self.connection) and (not self.sub_devices):
            raise ValueError("A connection must be specified when no sub devices are given.")

        # Instantiate objects from config descriptors.
        if isinstance(self.connection, ConfigDescriptor):
            self.connection = self.connection.create()
        if isinstance(self.controller, ConfigDescriptor):
            self.controller = self.controller.create()


        if connect:
            self.connect()

    @abstractmethod
    def get(self, *args, **kwargs):
        ...

    @abstractmethod
    def set(self, *args, **kwargs):
        ...

    def connect(self, reuse=False):
        """ Open all connections. """
        with self.lock:
            if self.connection:
                # Open connection.
                self.connection.open(reuse=reuse)

            for device in self.sub_devices:
                device.connect(reuse=reuse)

    def disconnect(self):
        """ Close all connections. """
        with self.lock:
            if self.connection:
                # Close connection.
                self.connection.close()

            for device in self.sub_devices:
                device.disconnect()

    def __enter__(self):
        self.lock.acquire()
        try:
            self.connect()
        except Exception:
            self.lock.release()
            raise
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.disconnect()
        finally:
            self.lock.release()




class VialHardwareDriver(HardwareDriver):
    def reconfigure(self, config):
        super().reconfigure(config)
        if config.vials is None:
            config.vials = self.evolver.config.vials
        else:
            if not set(config.vials).issubset(self.evolver.all_vials):
                raise ValueError('invalid vials found in config')


class SensorDriver(VialHardwareDriver):
    class Config(VialConfigBaseModel):
        pass
    class Output(VialBaseModel):
        raw: int
        value: float
    outputs: dict[int, Output] = {}

    def get(self) -> list[Output]:
        return self.outputs

    @abstractmethod
    def read(self):
        pass


class EffectorDriver(VialHardwareDriver):
    class Config(VialConfigBaseModel):
        pass
    class Input(VialBaseModel):
        value: float
    proposal: dict[int, Input] = {}
    committed: dict[int, Input] = {}

    def set(self, input: Input):
        self.proposal[input.vial] = input

    @abstractmethod
    def commit(self):
        pass
