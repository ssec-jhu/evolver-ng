from abc import abstractmethod
from collections import defaultdict
import time

from evolver.base import BaseConfig, BaseInterface


class History(BaseInterface):
    class Config(BaseConfig):
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
