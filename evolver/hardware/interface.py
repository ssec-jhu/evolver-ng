from abc import abstractmethod

from evolver.base import BaseConfig, BaseInterface


class VialConfigBaseModel(BaseConfig):
    vials: list[int] | None = None


class VialBaseModel(BaseConfig):
    vial: int


class BaseCalibrator(BaseInterface):
    class Config(BaseConfig):
        calibfile: str = None

    def __init__(self, *args, evovler=None, **kwargs):
        self.evovler = evovler
        super().__init__(*args, **kwargs)

    @property
    @abstractmethod
    def status(self):
        pass


class HardwareDriver(BaseInterface):
    class Config(BaseConfig):
        pass
    calibrator = None

    def __init__(self, *args, evolver=None, calibrator=None, **kwargs):
        self.evolver = evolver
        if calibrator:
            self.calibrator = calibrator
        super().__init__(*args, **kwargs)


class VialHardwareDriver(HardwareDriver):
    def __init__(self, *args, vials=None, **kwargs):
        self.vials = vials if vials else list(range(16))
        super().__init__(*args, **kwargs)


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
