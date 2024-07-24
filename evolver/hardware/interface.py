from abc import abstractmethod

from evolver.base import BaseConfig, BaseInterface
from evolver.settings import settings


class VialConfigBaseModel(BaseConfig):
    vials: list[int] | None = list(range(settings.DEFAULT_NUMBER_OF_VIALS_PER_BOX))


class VialBaseModel(BaseConfig):
    vial: int


class BaseCalibrator(BaseInterface):
    class Config(BaseInterface.Config):
        calibfile: str = None

    def __init__(self, *args, evolver=None, **kwargs):
        self.evolver = evolver
        super().__init__(*args, **kwargs)

    @property
    @abstractmethod
    def status(self):
        pass


class HardwareDriver(BaseInterface):
    class Config(BaseInterface.Config):
        pass

    calibrator = None

    def __init__(self, *args, evolver=None, calibrator=None, **kwargs):
        self.evolver = evolver
        if calibrator:
            self.calibrator = calibrator
        super().__init__(*args, **kwargs)


class VialHardwareDriver(HardwareDriver):
    class Config(VialConfigBaseModel, HardwareDriver.Config): ...


class SensorDriver(VialHardwareDriver):
    class Config(VialHardwareDriver.Config):
        pass

    class Output(VialBaseModel):
        raw: int
        value: float

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.outputs: dict[int, self.Output] = {}

    def get(self) -> list[Output]:
        return self.outputs

    @abstractmethod
    def read(self):
        pass


class EffectorDriver(VialHardwareDriver):
    class Config(VialHardwareDriver.Config):
        pass

    class Input(VialBaseModel):
        value: float

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.proposal: dict[int, self.Input] = {}
        self.committed: dict[int, self.Input] = {}

    def set(self, input: Input):
        self.proposal[input.vial] = input

    @abstractmethod
    def commit(self):
        pass
