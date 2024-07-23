from abc import abstractmethod

from pydantic import Field

from evolver.base import BaseConfig, BaseInterface, ConfigDescriptor
from evolver.calibration.interface import Calibrator
from evolver.settings import settings


class VialConfigBaseModel(BaseConfig):
    vials: list[int] | None = list(range(settings.DEFAULT_NUMBER_OF_VIALS_PER_BOX))


class VialBaseModel(BaseConfig):
    vial: int


class HardwareDriver(BaseInterface):
    class Config(BaseInterface.Config):
        calibrator: ConfigDescriptor | Calibrator | None = None

    def __init__(self, *args, evolver=None, **kwargs):
        self.evolver = evolver
        super().__init__(*args, **kwargs)


class VialHardwareDriver(HardwareDriver):
    class Config(VialConfigBaseModel, HardwareDriver.Config): ...


class SensorDriver(VialHardwareDriver):
    class Config(VialHardwareDriver.Config):
        pass

    class Output(VialBaseModel): ...

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.outputs: dict[int, self.Output] = {}

    def get(self) -> list[Output]:
        return self.outputs

    @Calibrator.calibrate_output
    @abstractmethod
    def read(self):
        """Communicate with connection to retrieve data. This must return ``self.outputs``."""
        pass


class EffectorDriver(VialHardwareDriver):
    class Config(VialHardwareDriver.Config):
        pass

    class Input(VialBaseModel): ...

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.proposal: dict[int, self.Input] = {}
        self.committed: dict[int, self.Input] = {}

    @Calibrator.calibrate_input
    def set(self, input: Input):
        self.proposal[input.vial] = input

    @abstractmethod
    def commit(self):
        pass
