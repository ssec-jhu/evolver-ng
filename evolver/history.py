import time
from abc import ABC, abstractmethod
from collections import defaultdict
from pydantic import BaseModel


class History(ABC):
    class Config(BaseModel):
        pass

    @abstractmethod
    def put(self, name, data):
        pass

    @abstractmethod
    def get(self, query):
        pass


class HistoryServer(History):
    def __init__(self, config = None):
        self.history = defaultdict(list)

    def put(self, name, data):
        self.history[name].append((time.time(), data))

    def get(self, name):
        return self.history[name]
