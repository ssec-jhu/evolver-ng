import time
import pydantic
from abc import ABC, abstractmethod
from collections import defaultdict


class History(ABC):
    class Config(pydantic.BaseModel):
        pass

    @abstractmethod
    def put(self, name, data):
        pass

    @abstractmethod
    def get(self, query):
        pass


class HistoryServer(History):
    def __init__(self, evolver=None, config = None):
        self.history = defaultdict(list)

    def put(self, name, data):
        self.history[name].append((time.time(), data))

    def get(self, name):
        return self.history[name]
