from abc import abstractmethod
from threading import RLock
from typing import Optional

import pydantic

from evolver.base import BaseConfig, BaseInterface, ConfigDescriptor
from evolver.calibration.interface import Calibrator
from evolver.connection.interface import Connection
from evolver.controller.interface import Controller
from evolver.settings import settings


class VialConfigBaseModel(BaseConfig):
    vials: list[int] | None = None


class VialBaseModel(BaseConfig):
    vial: int


class Device(BaseInterface):
    class Config(BaseConfig):
        ...

    class InputModel(pydantic.BaseModel):
        ...

    class OutputModel(pydantic.BaseModel):
        ...

    def __init__(self,
                 *args,
                 connection: Optional[Connection, ConfigDescriptor] = None,
                 calibrator: Optional[Calibrator, ConfigDescriptor] = None,
                 controller: Optional[Controller, ConfigDescriptor] = None,
                 sub_devices: Optional[dict[ConfigDescriptor]] = None,
                 connect=settings.OPEN_DEVICE_CONNECTION_UPON_INIT_POLICY_DEFAULT,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.calibrator = calibrator
        self.connection = connection  # Maybe None for conglomerate device.
        self.controller = controller
        self.lock = RLock()
        self.sub_devices = sub_devices if sub_devices else {}  # For conglomerate devices.

        # A connection can only be null when sub devices exist.
        if (not self.connection) and (not self.sub_devices):
            raise ValueError("A connection must be specified when no sub devices are given.")

        # Instantiate objects from config descriptors.
        # Note: When overriding ``__init__``, consider the use of ``evolver.base.init_and_set_vars_from_descriptors``,
        # however, also note that instantiation occurs in the order in which vars are first declared.
        if isinstance(self.connection, ConfigDescriptor):
            self.connection = self.connection.create()
        if isinstance(self.controller, ConfigDescriptor):
            self.controller = self.controller.create()
        if isinstance(self.calibrator, ConfigDescriptor):
            self.calibrator = self.calibrator.create()

        if connect:
            self.connect()

    @Calibrator.calibrate
    @abstractmethod
    def get(self, *args, **kwargs) -> "OutputModel":
        """ Implement data retrieval  from ``self.connection.read()`` and conversion to ``self.OutputModel``.
            Note: Concrete implementations are expected to also be decorated with ``@Calibrator.calibrate``.
        """
        ...

    @abstractmethod
    def set(self, *args, **kwargs):
        """ Implement data set calling ``self.connection.write()`` and conversion from ``self.InputModel``. """
        ...

    def connect(self, reuse=True):
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
