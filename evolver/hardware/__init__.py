from abc import ABC, abstractmethod
from copy import copy
from pydantic import BaseModel


class VialConfigBaseModel(BaseModel):
    vials: list[int] | None = None


class VialBaseModel(BaseModel):
    vial: int


class BaseCalibrator(ABC):
    class Config(BaseModel):
        calibfile: str = None

    def __init__(self, evovler = None, config: Config = Config()):
        self.config = config

    @property
    @abstractmethod
    def status(self):
        pass


class NoOpCalibrator(BaseCalibrator):
    @property
    def status(self):
        return True


class HardwareDriver(ABC):
    class Config(BaseModel):
        pass
    calibrator = NoOpCalibrator()

    def __init__(self, evolver, config = None, calibrator = None):
        self.evolver = evolver
        self.reconfigure(config or self.Config())
        if calibrator:
            self.calibrator = calibrator

    def reconfigure(self, config):
        self.config = config


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


class NoOpSensorDriver(SensorDriver):
    class Config(VialConfigBaseModel):
        echo_raw: int = 1
        echo_val: int = 2

    def read(self):
        self.outputs = {
            i: self.Output(vial=i, raw=self.config.echo_raw, value=self.config.echo_val)
            for i in self.config.vials
        }

    def get(self):
        return self.outputs


class NoOpEffectorDriver(EffectorDriver):
    def commit(self):
        self.comitted = copy(self.proposal)
