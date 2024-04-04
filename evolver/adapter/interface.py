import pydantic
from abc import ABC, abstractmethod


class Adapter(ABC):
    class Config(pydantic.BaseModel):
        pass

    def __init__(self, evolver, config: Config = None):
        self.config = config or self.Config()

    @abstractmethod
    def react(self):
        pass
