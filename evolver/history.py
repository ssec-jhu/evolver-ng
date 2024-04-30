import datetime
from abc import abstractmethod
from collections import defaultdict

from evolver.base import BaseConfig, BaseInterface


class History(BaseInterface):
    class Config(BaseConfig):
        pass

    @abstractmethod
    def set(self, name, data):
        pass

    @abstractmethod
    def get(self, query):
        pass

    @classmethod
    def track_history(cls, name: str = None):
        """ Decorator for convenient tracking of data history.
            E.g., decorate ``Device.get()`` to automatically track the data returned by the device.

            Args:
                name str: The name of the history stream to add data to.
        """
        def decorator(func):
            def wrapper(self, *args, **kwargs):
                nonlocal name
                ret = func(self, *args, **kwargs)

                if name is None:
                    name = getattr(self, "name")

                # Track history.
                cls.getHistory().set(name=name, data=ret)

                return ret
            return wrapper
        return decorator

    @classmethod
    def getHistory(cls, name: str = None):
        """ Functions similarly to ``logging.getLogger``. """
        ...


class HistoryServer(History):
    class Config(History.Config):
        name: str = "HistoryServer"

    def __init__(self, *args, **kwargs):
        self.history = defaultdict(list)
        super().__init__(*args, **kwargs)

    def set(self, name, data):
        self.history[name].append((datetime.datetime.now(), data))

    def get(self, name):
        return self.history.get(name)
