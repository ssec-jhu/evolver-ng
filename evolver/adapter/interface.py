import pydantic
from abc import ABC, abstractmethod
from evolver.hardware.interface import VialConfigBaseModel
from evolver.vial import Vial


class Adapter(ABC):
    class Config(pydantic.BaseModel):
        pass

    def __init__(self, evolver, config: Config = None):
        self.config = config or self.Config()
        self.evolver = evolver

    @abstractmethod
    def react(self):
        pass


class VialAdapter(Adapter):
    class Config(VialConfigBaseModel):
        pass

    def react(self):
        for vial_n in self.config.vials:
            self.react_vial(self.evolver.get_vial(vial_n))

    @abstractmethod
    def react_vial(self, vial: Vial):
        pass
