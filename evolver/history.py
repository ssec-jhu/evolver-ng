import time
from abc import abstractmethod
from collections import defaultdict

from evolver.base import BaseInterface


class History(BaseInterface):
    class Config(BaseInterface.Config):
        pass

    @abstractmethod
    def put(self, name, data):
        pass

    @abstractmethod
    def get(self, query):
        pass


class HistoryServer(History):
    class Config(History.Config):
        name: str = "HistoryServer"

    def __init__(self, *args, **kwargs):
        self.history = defaultdict(list)
        super().__init__(*args, **kwargs)

    def put(self, name, data):
        self.history[name].append((time.time(), data))

    def get(self, name):
        return self.history[name]
