import pydantic
from abc import ABC, abstractmethod


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


class HardwareDriver(ABC):
    class Config(pydantic.BaseModel):
        pass
    calibrator = None

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
