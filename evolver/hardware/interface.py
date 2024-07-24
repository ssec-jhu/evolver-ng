from abc import abstractmethod

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
    class Config(VialHardwareDriver.Config): ...

    class Output(VialBaseModel): ...

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.outputs: dict[int, self.Output] = {}

    def get(self) -> list[Output]:
        return self.outputs

    @abstractmethod
    def read(self):
        """Communicate with connection to retrieve data. This must return ``self.outputs``.
        The implementation is responsible for calling methods of ``self.output_transformer`` as deemed necessary.
        """
        pass


class EffectorDriver(VialHardwareDriver):
    class Config(VialHardwareDriver.Config):
        pass

    class Input(VialBaseModel): ...

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.proposal: dict[int, self.Input] = {}
        self.committed: dict[int, self.Input] = {}

    def set(self, input: Input):
        """The implementation is responsible for calling methods of ``self.input_transformer`` as deemed necessary."""
        self.proposal[input.vial] = input

    @abstractmethod
    def commit(self):
        pass
