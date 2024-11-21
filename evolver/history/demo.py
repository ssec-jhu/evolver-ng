import time
from collections import defaultdict, deque

from evolver.history.interface import HistoricDatum, History, HistoryResult
from evolver.util import filter_vial_data


class InMemoryHistoryServer(History):
    class Config(History.Config):
        name: str = "HistoryServer"
        buffer_size: int = 100

    def __init__(self, *args, **kwargs):
        self.history = defaultdict(lambda: deque(maxlen=self.buffer_size))
        super().__init__(*args, **kwargs)

    def put(self, name, kind, data, vial=None):
        self.history[name].append(HistoricDatum(timestamp=time.time(), data=data, kind=kind, vial=vial))

    def get(
        self,
        name: str = None,
        kinds: list[str] = None,
        t_start: float = None,
        t_stop: float = None,
        vials: list[int] | None = None,
        properties: list[str] | None = None,
        n_max: int = None,
    ):
        names = self.history.keys()
        if name is not None:
            names = [n for n in names if n == name]
        data = {}
        for n in names:
            history = list(self.history[n])[:n_max]
            try:
                history = [filter_vial_data(d, vials, properties) for d in history]
            except Exception:
                pass

            def filter_records(record):
                if kinds and record.kind not in kinds:
                    return False
                if vials and record.vial not in vials:
                    return False
                return True

            data[n] = [i for i in history if filter_records(i)]
        return HistoryResult(data=data)
