from abc import ABC, abstractmethod
from threading import RLock

import pydantic

from evolver.connection.interface import Connection


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

    def __init__(self, connection=None, lock_constructor=RLock, sub_devices=None, connect=False):
        self.sub_devices = sub_devices if sub_devices else {}  # For conglomerate devices.
        self.connection = connection  # Maybe None for conglomerate device.
        self.lock = lock_constructor()

        # Instantiate connection if needed.
        self._instantiate_connection()

        if connect:
            self.connect()

    def connect(self, reuse=False):
        with self.lock:
            if self.connection:
                # Open connection.
                self.connection.open(reuse=reuse)

            for device in self.sub_devices:
                device.connect(reuse=reuse)

    def disconnect(self):
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

    def _instantiate_connection(self):
        if self.connection is None:
            return
        elif isinstance(self.connection, Connection):
            ...
        elif issubclass(self.connection, Connection):
            self.connection = self.connection()
        else:
            raise TypeError(f"Connection must be of type '{Connection.__qualname__}' not '{type(self.connection)}'.")




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
