from abc import ABC, abstractmethod
from pydantic import BaseModel


class Adapter(ABC):
    class Config(BaseModel):
        pass

    def __init__(self, evolver, config: Config = None):
        self.config = config or self.Config()

    @abstractmethod
    def react(self):
        pass


class NoOpAdapter(Adapter):
    ncalls = 0

    def react(self):
        self.ncalls += 1
