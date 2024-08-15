import time
from collections import defaultdict, deque

from evolver.history.interface import HistoricDatum, History, HistoryResult


class InMemoryHistoryServer(History):
    class Config(History.Config):
        name: str = "HistoryServer"
        buffer_size: int = 100

    def __init__(self, *args, **kwargs):
        self.history = defaultdict(lambda: deque(maxlen=self.buffer_size))
        super().__init__(*args, **kwargs)

    def put(self, name, data):
        self.history[name].append(HistoricDatum(timestamp=time.time(), data=data))

    def get(self, name: str = None, t_start: float = None, t_stop: float = None, n_max: int = None):
        names = self.history.keys()
        if name is not None:
            names = [n for n in names if n == name]
        data = {n: list(self.history[n])[:n_max] for n in names}
        return HistoryResult(data=data)
