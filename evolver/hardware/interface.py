from abc import abstractmethod
from collections import defaultdict
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
    """
        Base Interface class for all device implementations.

        A modular layer for wrapping ``self.connection`` which is the communication layer to the underlying physical
        hardware.

        This interface is intended to be self-similar such that it can be used to implement "conglomerate" devices that
        are themselves a collection of other devices.

        Attributes:
            connection (:obj:`Connection`, :obj:`ConfigDescriptor`, optional): Connection to the underlying physical
                hardware. Note: Only optional when using ``sub_devices``.
            calibrator (:obj:`Calibrator`, :obj:`ConfigDescriptor`, optional): Calibrator used to calibrate data
                returned from the underlying hardware. This also couples the device with the calibration procedure used
                to obtain any required calibration parameters.
            sub_controller (:obj:`Controller`, :obj:`ConfigDescriptor`, optional): This can be used to leverage the
                ``Controller`` interface for orchestrating multiple sub devices, e.g., thermostat control of thermometer
                and heater devices.
            sub_devices (:obj:`dict` of :obj:`Device`, :obj:`dict` of :obj:`ConfigDescriptor`, optional):
                Dictionary of sub devices that this conglomerate device wraps. E.g., thermometer and heater, pressure
                sensors and pressure valves (or pumps), etc.
        Args:
            *args: Passed to super().__init__.
            connect (bool): Call self.connection.open() upon instantiation when True.
            **kwargs: Passed to super().__init__.
    """
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
                 sub_controller: Optional[Controller, ConfigDescriptor] = None,
                 sub_devices: Optional[dict["Device"], dict[ConfigDescriptor]] = defaultdict,
                 connect=settings.OPEN_DEVICE_CONNECTION_UPON_INIT_POLICY_DEFAULT,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.calibrator = calibrator
        self.connection = connection  # Maybe None for conglomerate device.
        self.lock = RLock()
        self.sub_controller = sub_controller
        self.sub_devices = sub_devices  # For conglomerate devices.

        # A connection can only be null when sub devices exist.
        if (not self.connection) and (not self.sub_devices):
            raise ValueError("A connection must be specified when no sub devices are given.")

        # Instantiate objects from config descriptors.
        # Note: When overriding ``__init__``, consider the use of ``evolver.base.init_and_set_vars_from_descriptors``,
        # however, also note that instantiation occurs in the order in which vars are first declared.
        if isinstance(self.connection, ConfigDescriptor):
            self.connection = self.connection.create()
        if isinstance(self.sub_controller, ConfigDescriptor):
            self.sub_controller = self.sub_controller.create()
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
        """ Acquire lock and open connection(s). """
        self.lock.acquire()
        try:
            self.connect()
        except Exception:
            self.lock.release()
            raise
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """ Release lock and close connection(s). """
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
